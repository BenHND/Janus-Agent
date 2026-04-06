"""
Whisper STT - Audio Recording Module
Handles audio recording with energy-based silence detection

CRITICAL: No VAD filtering is applied to audio.
Whisper works best with raw, unfiltered audio containing natural pauses, breathing, and background sounds.
Only energy-based silence detection is used to determine when to stop recording.

Architecture:
- Single persistent PyAudio stream opened once
- Background reader thread continuously fills ring buffer (pre-roll) and recording queue
- record_audio() consumes from queue without touching stream directly
"""

import asyncio
import queue
import tempfile
import threading
import time
import wave
from math import gcd
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import pyaudio
from scipy import signal

from janus.logging import get_logger

logger = get_logger("whisper_recorder")

# Recording constants
MIN_FRAMES_REQUIRED = 10  # Minimum number of chunks for a valid recording
QUEUE_PUT_TIMEOUT = 0.01  # Seconds to wait when queue is full (backpressure handling)
QUEUE_TIMEOUT_MULTIPLIER = 25  # Multiplier for chunk duration to calculate queue read timeout
WARMUP_DURATION_MS = 400  # Duration to warm up microphone stream before first recording
WARMUP_TIMEOUT_SEC = 0.5  # Maximum time to wait for warm-up in record_audio
OVERFLOW_LOG_FREQUENCY = 10  # Log every Nth overflow event to avoid spam


class _RingBuffer:
    """Circular buffer for pre-roll audio chunks"""

    def __init__(self, capacity: int):
        """
        Initialize ring buffer

        Args:
            capacity: Maximum number of chunks to store
        """
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.index = 0
        self.filled = False

    def append(self, chunk: bytes):
        """Add a chunk to the buffer (overwrites oldest if full)"""
        self.buffer[self.index] = chunk
        self.index = (self.index + 1) % self.capacity
        if self.index == 0:
            self.filled = True

    def get_snapshot(self) -> list:
        """Get all chunks in chronological order"""
        if not self.filled:
            # Buffer not yet full, return only what we have
            return [c for c in self.buffer[: self.index] if c is not None]
        else:
            # Buffer is full, return from oldest to newest
            return self.buffer[self.index :] + self.buffer[: self.index]

    def clear(self):
        """Clear the buffer"""
        self.buffer = [None] * self.capacity
        self.index = 0
        self.filled = False


class WhisperRecorder:
    """
    Audio recording with energy-based silence detection (no VAD filtering).
    
    TICKET: Zero-Latency Audio Pipeline
    - Supports TTS gating (Neural Gatekeeper) to prevent echo/self-listening
    - Continues wake word detection during TTS playback
    - Drops transcription packets when TTS is speaking
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 20,
        silence_threshold: int = 60,
        calibration_manager=None,
        context_buffer=None,
        preroll_duration_ms: int = 400,
        tts_service=None,  # Neural Gatekeeper: TTS service for anti-echo
    ):
        """
        Initialize audio recorder with persistent PyAudio stream and reader thread

        Args:
            sample_rate: Audio sample rate in Hz
            chunk_duration_ms: Duration of each audio chunk in milliseconds
            silence_threshold: Threshold for silence detection (in chunks)
            calibration_manager: Optional calibration manager
            context_buffer: Optional context buffer for audio history
            preroll_duration_ms: Pre-roll buffer duration in milliseconds (default 400ms)
            tts_service: Optional TTS service for anti-echo (Neural Gatekeeper)
        """
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.silence_threshold = silence_threshold
        self.calibration_manager = calibration_manager
        self.context_buffer = context_buffer
        self.tts_service = tts_service  # Neural Gatekeeper
        self.audio = pyaudio.PyAudio()
        
        # Detect native sample rate
        try:
            default_device = self.audio.get_default_input_device_info()
            self.native_rate = int(default_device['defaultSampleRate'])
            logger.info(f"Detected native microphone sample rate: {self.native_rate}Hz")
        except Exception as e:
            logger.warning(f"Could not detect native sample rate: {e}. Defaulting to 16000Hz")
            self.native_rate = 16000

        # We capture at native rate, but process at requested sample_rate (usually 16000)
        self.target_rate = self.sample_rate
        
        # Calculate chunk size for native rate to match duration
        self.chunk_size = int(self.native_rate * self.chunk_duration_ms / 1000)
        
        self._stop_listening = False
        self._recording_count = 0
        self._last_calibration_check = 0

        # Ring buffer for pre-roll (stores audio before recording starts)
        # Memory impact: ~128KB constant (acceptable for better UX)
        # Calculation: 20 chunks * 16000 Hz * 20ms/chunk * 2 bytes/sample = 20 * 640 bytes = ~12.8KB
        # (actual varies by preroll_duration_ms, typical range 10-30KB)
        # Alternative: Lazy initialization would save memory but complicate logic
        preroll_chunks = int(preroll_duration_ms / chunk_duration_ms)
        self._ring_buffer = _RingBuffer(preroll_chunks)

        # Queue for active recording chunks
        self._recording_queue = queue.Queue()
        self._recording_active = False
        self._recording_lock = threading.Lock()
        
        # Passive listeners (e.g. Wake Word Detector)
        self._passive_listeners = []
        self._listeners_lock = threading.Lock()

        # Thread control
        self._stop_thread = threading.Event()
        self._reader_thread = None
        
        # Track audio overflows for diagnostics
        self._overflow_count = 0
        
        # Pause mechanism to reduce CPU when idle
        self._pause_reading = threading.Event()
        self._pause_reading.clear()  # Start unpaused

        # Warm-up mechanism to ensure stream is stable before first recording
        self._warmed_up = False
        self._warmup_chunks_target = int(WARMUP_DURATION_MS / self.chunk_duration_ms)
        self._chunks_read = 0

        # Persistent stream - opened once
        self.stream = None
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.native_rate,  # Use native rate
                input=True,
                frames_per_buffer=self.chunk_size,
                start=True,
            )
            logger.info(f"Persistent microphone stream initialized at {self.native_rate}Hz")

            # Start reader thread
            self._reader_thread = threading.Thread(
                target=self._audio_reader_thread, daemon=True, name="AudioReaderThread"
            )
            self._reader_thread.start()
            logger.info("Audio reader thread started")

        except Exception as e:
            logger.error(f"Failed to initialize persistent microphone stream: {e}")
            self.stream = None

    def register_listener(self, callback: Callable[[bytes], None]):
        """Register a passive listener for raw audio chunks"""
        with self._listeners_lock:
            if callback not in self._passive_listeners:
                self._passive_listeners.append(callback)
                logger.debug("Passive audio listener registered")
        
        # Wake up the reader thread if it was paused
        self._pause_reading.set()

    def unregister_listener(self, callback: Callable[[bytes], None]):
        """Unregister a passive listener"""
        with self._listeners_lock:
            if callback in self._passive_listeners:
                self._passive_listeners.remove(callback)
                logger.debug("Passive audio listener unregistered")

    def _should_pause_reading(self) -> bool:
        """
        Determine if audio reading should pause to save CPU.
        Pause when:
        - No active recording
        - No passive listeners registered
        
        Returns:
            True if reading should pause, False otherwise
        """
        with self._recording_lock:
            has_active_recording = self._recording_active
        
        with self._listeners_lock:
            has_listeners = len(self._passive_listeners) > 0
        
        return not has_active_recording and not has_listeners
    
    def _audio_reader_thread(self):
        """
        Background thread that continuously reads from the audio stream.
        Fills the ring buffer for pre-roll and the recording queue when active.
        Pauses when no active recording and no listeners to save CPU.
        """
        logger.info("Audio reader thread running")
        chunks_read_count = 0

        while not self._stop_thread.is_set():
            # Check if we should pause reading to save CPU
            if self._should_pause_reading():
                if chunks_read_count > 0:  # Only log on first pause
                    logger.info("Audio reader thread paused (no active recording or listeners)")
                    chunks_read_count = 0
                # Wait for wake-up signal (with timeout to check stop_thread)
                self._pause_reading.wait(timeout=1.0)
                self._pause_reading.clear()  # Reset for next pause
                if not self._stop_thread.is_set():
                    logger.info("Audio reader thread resumed")
                continue
            
            if self.stream is None or not self.stream.is_active():
                # Stream not available, wait a bit and retry
                self._stop_thread.wait(0.1)
                continue

            try:
                # Read one chunk from the stream
                # Note: exception_on_overflow=False means overflows are silent
                # We should monitor for these and log them
                try:
                    chunk = self.stream.read(self.chunk_size, exception_on_overflow=True)
                except IOError as e:
                    # Handle overflow (input overflowed)
                    # PyAudio overflow errors typically show up in exception message, not errno
                    error_msg = str(e).lower()
                    if 'overflow' in error_msg or 'input overflowed' in error_msg:
                        self._overflow_count += 1
                        if self._overflow_count % OVERFLOW_LOG_FREQUENCY == 1:  # Log every Nth overflow
                            logger.warning(f"Audio input overflow detected (count: {self._overflow_count}). "
                                         "System may be overloaded or buffer too small.")
                    # Read with exception_on_overflow=False to get partial data
                    chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                chunks_read_count += 1
                
                if chunks_read_count % 50 == 0:
                    # print(f"🎤 Audio Thread Alive: {chunks_read_count} chunks read", flush=True)
                    pass
                
                # Resample if necessary (native rate -> target rate)
                if self.native_rate != self.target_rate:
                    audio_array = np.frombuffer(chunk, dtype=np.int16)
                    
                    # Calculate upsampling and downsampling factors
                    # For example: 48000 -> 16000 = downsample by 3 (48000/16000 = 3)
                    # Use resample_poly which is much faster than FFT-based resample
                    common = gcd(self.native_rate, self.target_rate)
                    up = self.target_rate // common
                    down = self.native_rate // common
                    
                    try:
                        # resample_poly is ~10x faster than FFT-based resample
                        resampled_array = signal.resample_poly(audio_array, up, down).astype(np.int16)
                    except Exception as e:
                        # Fallback to linear interpolation if resample_poly fails
                        logger.warning(f"Resampling error: {e}, falling back to linear interpolation")
                        target_samples = int(len(audio_array) * self.target_rate / self.native_rate)
                        indices = np.linspace(0, len(audio_array) - 1, target_samples)
                        resampled_array = np.interp(indices, np.arange(len(audio_array)), audio_array).astype(np.int16)
                    
                    chunk = resampled_array.tobytes()
                
                # Ensure chunk size is exactly what we expect (16kHz * 20ms = 320 samples * 2 bytes = 640 bytes)
                # If resampling produced slightly different size, pad or trim
                expected_size = int(self.target_rate * self.chunk_duration_ms / 1000) * 2
                if len(chunk) != expected_size:
                    # logger.warning(f"Chunk size mismatch: {len(chunk)} vs {expected_size}. Adjusting...")
                    if len(chunk) > expected_size:
                        chunk = chunk[:expected_size]
                    else:
                        chunk = chunk + b'\0' * (expected_size - len(chunk))

                # Broadcast to passive listeners (e.g. Wake Word)
                with self._listeners_lock:
                    if chunks_read_count % 100 == 0 and self._passive_listeners:
                        logger.debug(f"Broadcasting to {len(self._passive_listeners)} listeners")
                        
                    for listener in self._passive_listeners:
                        try:
                            listener(chunk)
                        except Exception as e:
                            logger.error(f"Error in passive listener: {e}")

                # Always add to ring buffer for pre-roll
                self._ring_buffer.append(chunk)

                # Track chunks read for warm-up
                if not self._warmed_up:
                    self._chunks_read += 1
                    if self._chunks_read >= self._warmup_chunks_target:
                        self._warmed_up = True
                        logger.info(
                            f"Microphone stream warmed up after {self._chunks_read} chunks "
                            f"(~{self._chunks_read * self.chunk_duration_ms}ms)"
                        )

                # If recording is active, also add to recording queue
                with self._recording_lock:
                    if self._recording_active:
                        try:
                            # Use small timeout to allow brief backpressure handling
                            self._recording_queue.put(chunk, block=True, timeout=QUEUE_PUT_TIMEOUT)
                        except queue.Full:
                            logger.warning("Recording queue full, dropping chunk")

            except Exception as e:
                logger.error(f"Error reading audio chunk: {e}")
                self._stop_thread.wait(0.1)
                continue

        logger.info("Audio reader thread stopped")

    def _get_preroll_snapshot(self) -> list:
        """Get a snapshot of the pre-roll buffer"""
        return self._ring_buffer.get_snapshot()

    def _calculate_energy(self, audio_chunk: bytes) -> float:
        """Calculate energy level of audio chunk"""
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
        mean_square = np.mean(audio_data**2)
        # Handle edge cases: NaN, inf, or negative values (though mathematically shouldn't occur)
        if not np.isfinite(mean_square) or mean_square < 0:
            return 0.0
        return np.sqrt(mean_square)

    async def record_audio_async(
        self,
        max_duration: int = 10,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Async wrapper around record_audio"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.record_audio, max_duration, on_audio_chunk)

    def record_audio(
        self,
        max_duration: int = 8,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Record audio from microphone using queue and pre-roll buffer.
        Does NOT touch the stream directly - only consumes from recording_queue.

        Args:
            max_duration: Maximum recording duration in seconds
            on_audio_chunk: Optional callback for audio chunk processing

        Returns:
            Tuple of (audio_file_path, error_message)
        """
        logger.info("Recording started...")

        # Check if stream is available
        if self.stream is None or not self.stream.is_active():
            return None, "Microphone stream not available"

        # Wait for microphone warm-up if needed (first recording after startup)
        if not self._warmed_up:
            logger.info("Waiting for microphone warm-up...")
            start = time.time()
            # Wait max WARMUP_TIMEOUT_SEC for warm-up
            while not self._warmed_up and (time.time() - start) < WARMUP_TIMEOUT_SEC:
                time.sleep(0.01)
            
            if self._warmed_up:
                logger.info("Microphone warm-up complete")
            else:
                logger.warning("Warm-up timeout - proceeding with recording anyway")

        # Start recording: clear queue and get pre-roll snapshot
        with self._recording_lock:
            # Clear any stale data from queue
            while not self._recording_queue.empty():
                try:
                    self._recording_queue.get_nowait()
                except queue.Empty:
                    break

            # Get pre-roll snapshot (audio from before we started recording)
            preroll_frames = self._get_preroll_snapshot()
            logger.info(f"Pre-roll captured: {len(preroll_frames)} chunks")

            # Activate recording mode
            self._recording_active = True
        
        # Wake up the reader thread if it was paused
        self._pause_reading.set()

        try:
            # Initialize frames with pre-roll
            frames = list(preroll_frames)
            silent_chunks = 0
            max_chunks = int(max_duration * 1000 / self.chunk_duration_ms)
            chunks_processed = 0
            speech_detected = False

            # Timeout for queue reads - use multiplier of chunk duration to allow for processing delays
            # For 20ms chunks with 25x multiplier, this gives 500ms timeout which is reasonable
            queue_timeout = (self.chunk_duration_ms * QUEUE_TIMEOUT_MULTIPLIER) / 1000.0

            while chunks_processed < max_chunks:
                if self._stop_listening:
                    logger.info("Listening interrupted by user.")
                    break

                try:
                    # Get chunk from queue (with timeout)
                    chunk = self._recording_queue.get(timeout=queue_timeout)
                    chunks_processed += 1
                    
                    # Neural Gatekeeper: Drop chunks if TTS is speaking (anti-echo)
                    # This prevents the agent from transcribing its own voice
                    if self.tts_service and self.tts_service.is_speaking():
                        # Still count the chunk but don't add it to frames
                        # This prevents echo/self-listening
                        logger.debug("TTS speaking - dropping audio chunk (anti-echo)")
                        continue
                    
                    frames.append(chunk)

                    # Calculate energy for silence detection
                    energy = self._calculate_energy(chunk)

                    if self.calibration_manager:
                        self.calibration_manager.update_noise_stats(energy)

                    # Speech detection threshold
                    speech_threshold = 70.0
                    if energy > speech_threshold:
                        speech_detected = True

                    # Silence detection
                    silence_energy_threshold = 40.0
                    if energy > silence_energy_threshold:
                        silent_chunks = 0
                    else:
                        silent_chunks += 1

                    # Stop on prolonged silence (use configured silence_threshold)
                    if silent_chunks >= self.silence_threshold:
                        logger.info(
                            f"True silence detected after {silent_chunks * self.chunk_duration_ms / 1000:.1f}s. Stopping recording."
                        )
                        break

                    # Callback for UI feedback
                    if on_audio_chunk:
                        on_audio_chunk(energy, speech_detected)

                except queue.Empty:
                    # No chunk received within timeout - treat as silence
                    silent_chunks += 1
                    if silent_chunks >= self.silence_threshold:
                        logger.info("No audio received (timeout), stopping recording.")
                        break

            # Check minimum length
            if not frames or len(frames) < MIN_FRAMES_REQUIRED:
                if frames:
                    return (
                        None,
                        f"Recording too short ({len(frames)} chunks). Please speak for at least 0.3 second.",
                    )
                return None, f"No audio captured within {max_duration}s"

            # Save to temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", mode="wb")
            temp_path = temp_file.name
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b"".join(frames))

            # Debug WAV
            debug_dir = Path("audio_logs")
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_path = debug_dir / "debug_recording.wav"
            try:
                import shutil

                shutil.copy2(temp_path, str(debug_path))
                logger.info(f"Debug WAV saved to {debug_path}")
            except Exception as e:
                logger.warning(f"Failed to save debug WAV: {e}")

            # Context buffer
            if self.context_buffer:
                audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)
                self.context_buffer.add_audio_segment(audio_data)

            # Recalibration
            self._recording_count += 1
            if self._recording_count % 10 == 0 and self.calibration_manager:
                if self.calibration_manager.should_recalibrate():
                    logger.info("Environment changed detected. Auto-adjusting calibration...")

            logger.info(f"Recording saved to {temp_path}")
            return temp_path, None

        except Exception as e:
            logger.error(f"Recording error: {str(e)}")
            return None, f"Recording error: {str(e)}"

        finally:
            # Always deactivate recording mode
            with self._recording_lock:
                self._recording_active = False

    def stop_listening(self):
        """Stop the current listening operation"""
        self._stop_listening = True
        logger.debug("Stop listening flag set")

    def start_listening(self):
        """Reset the stop listening flag for new listening operation"""
        self._stop_listening = False
        logger.debug("Stop listening flag reset")

    def close(self):
        """
        Cleanup resources and stop background thread.
        Safe to call multiple times.
        """
        try:
            # Stop the reader thread
            if hasattr(self, "_stop_thread"):
                self._stop_thread.set()

            if hasattr(self, "_reader_thread") and self._reader_thread:
                if self._reader_thread.is_alive():
                    self._reader_thread.join(timeout=2.0)
                    logger.debug("Audio reader thread joined")

            # Close stream
            if getattr(self, "stream", None):
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                    logger.debug("Audio stream closed")
                except Exception as e:
                    logger.debug(f"Error closing stream: {e}")

            # Terminate PyAudio
            if hasattr(self, "audio"):
                self.audio.terminate()
                logger.debug("PyAudio terminated")

        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup PyAudio and stop thread"""
        self.close()
