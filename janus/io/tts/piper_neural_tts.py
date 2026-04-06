"""
Piper Neural TTS Adapter - High-quality neural text-to-speech
Uses Piper TTS with ONNX models for natural-sounding voices.
100% offline, cross-platform (Windows, macOS, Linux), lightweight and fast.

Ticket TICKET-04: Non-blocking async operations
- speak() is now async to avoid blocking the event loop
- Blocking I/O operations wrapped in asyncio.to_thread()
"""

import asyncio
import logging
import os
import queue
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from piper import PiperVoice

    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

from janus.constants import (
    DEFAULT_TTS_RATE,
    DEFAULT_TTS_VOLUME,
    QUEUE_POLL_TIMEOUT,
    WORKER_THREAD_JOIN_TIMEOUT,
    clamp_volume,
)
from .adapter import TTSAdapter


@dataclass(order=True)
class TTSMessage:
    """Message to be spoken by TTS"""

    priority: int = field(compare=True)
    timestamp: float = field(compare=True)
    text: str = field(compare=False)
    lang: str = field(compare=False)


class PiperNeuralTTSAdapter(TTSAdapter):
    """
    Piper Neural TTS adapter - lightweight, fast, high-quality voices

    Features:
    - Neural voice models for natural speech
    - 100% offline - no internet required after model download
    - Cross-platform (Windows, macOS, Linux)
    - Fast inference with ONNX Runtime
    - High-quality French voices
    - Lightweight (much faster than Coqui)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: int = DEFAULT_TTS_RATE,
        volume: float = DEFAULT_TTS_VOLUME,
        lang: str = "fr-FR",
        enable_queue: bool = True,
    ):
        """Initialize Piper Neural TTS adapter"""
        if not PIPER_AVAILABLE:
            raise ImportError("Piper TTS is required. Install with: pip install piper-tts")

        # Initialize all instance variables
        self.model_path = model_path
        self.voice = voice
        self.rate = rate
        self.volume = clamp_volume(volume)
        self.default_lang = lang
        self.enable_queue = enable_queue

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # Auto-detect model path if not provided
        if not self.model_path:
            self.model_path = self._find_model_path()

        # Initialize Piper engine
        self._piper_voice = None
        self._engine_lock = threading.Lock()
        self._engine_ready = threading.Event()
        self._init_engine_async()

        # Mute state
        self._is_muted = False
        self._volume_before_mute = self.volume

        # Message queue
        self._queue = queue.PriorityQueue() if enable_queue else None
        self._worker_thread = None
        self._stop_flag = threading.Event()
        self._speaking_flag = threading.Event()

        # Timing tracking
        self._current_speech_start_time = None
        self._total_speech_time = 0.0
        self._speech_count = 0

        # Start worker thread if queue enabled
        if self.enable_queue:
            self._start_worker()

    def _find_model_path(self) -> str:
        """Find Piper model in models directory"""
        # Look for French model in models/piper/
        base_dir = Path(__file__).parent.parent.parent / "models" / "piper"

        if base_dir.exists():
            # Look for French models
            for model_file in base_dir.glob("fr_*.onnx"):
                self.logger.info(f"Found Piper model: {model_file}")
                return str(model_file)

        # Fallback: return expected path (will be downloaded if needed)
        default_path = base_dir / "fr_FR-siwis-medium.onnx"
        self.logger.warning(f"No model found, using default path: {default_path}")
        return str(default_path)

    def _init_engine_async(self):
        """Initialize Piper engine in background"""

        def init_engine():
            try:
                with self._engine_lock:
                    self.logger.info(f"Loading Piper voice model: {self.model_path}")

                    if not os.path.exists(self.model_path):
                        raise FileNotFoundError(f"Piper model not found: {self.model_path}")

                    # Load Piper voice
                    self._piper_voice = PiperVoice.load(self.model_path)

                    self.logger.info("✓ Piper Neural TTS initialized successfully")
                    self._engine_ready.set()

            except Exception as e:
                self.logger.error(f"Failed to initialize Piper TTS: {e}")
                self._piper_voice = None
                self._engine_ready.set()

        threading.Thread(target=init_engine, daemon=True).start()

    def _start_worker(self):
        """Start TTS worker thread"""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        """Worker loop processing TTS messages"""
        self._engine_ready.wait(timeout=10)

        while not self._stop_flag.is_set():
            try:
                message = self._queue.get(timeout=QUEUE_POLL_TIMEOUT)
                try:
                    self._speak_sync(message.text, message.lang)
                finally:
                    self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in TTS worker: {e}")

    def _generate_and_play_audio(self, text: str) -> None:
        """
        Generate and play audio (blocking I/O operations)

        This method contains all the blocking operations that should be
        run in a separate thread via asyncio.to_thread().

        Args:
            text: Text to synthesize and play
        """
        import os
        import tempfile
        import wave

        import pyaudio

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate WAV file (blocking I/O)
            with wave.open(temp_path, "wb") as wav_file:
                self._piper_voice.synthesize_wav(text, wav_file)

            # Play WAV file with PyAudio (blocking I/O)
            wf = wave.open(temp_path, "rb")
            p = pyaudio.PyAudio()

            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )

            # Read and play audio in chunks (blocking I/O)
            chunk_size = 1024
            data = wf.readframes(chunk_size)
            while data:
                stream.write(data)
                data = wf.readframes(chunk_size)

            # Cleanup
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()

        finally:
            # Delete temp file
            try:
                os.unlink(temp_path)
            except OSError as e:
                # File may already be deleted or not exist
                self.logger.debug(f"Failed to delete temp file {temp_path}: {e}")

    def _speak_sync(self, text: str, lang: str):
        """Speak text synchronously using Piper"""
        if self._is_muted:
            self.logger.debug(f"TTS muted, skipping: '{text[:50]}...'")
            return

        if not self._piper_voice:
            self.logger.error("Piper voice not initialized")
            return

        try:
            self._speaking_flag.set()
            self._current_speech_start_time = time.time()

            self.logger.debug(f"Generating speech: '{text[:50]}...'")

            with self._engine_lock:
                # Call the blocking I/O operations
                self._generate_and_play_audio(text)

            # Log timing
            duration = time.time() - self._current_speech_start_time
            self._total_speech_time += duration
            self._speech_count += 1
            self.logger.info(f"Speech completed in {duration:.2f}s: '{text[:50]}...'")

        except Exception as e:
            import traceback

            self.logger.error(f"Error generating speech: {e}\n{traceback.format_exc()}")
        finally:
            self._speaking_flag.clear()
            self._current_speech_start_time = None

    async def _speak_async(self, text: str, lang: str):
        """
        Speak text asynchronously using Piper (TICKET-04)

        This method wraps blocking I/O operations in asyncio.to_thread()
        to avoid freezing the event loop during speech synthesis.

        Args:
            text: Text to speak
            lang: Language code
        """
        if self._is_muted:
            self.logger.debug(f"TTS muted, skipping: '{text[:50]}...'")
            return

        if not self._piper_voice:
            self.logger.error("Piper voice not initialized")
            return

        try:
            self._speaking_flag.set()
            self._current_speech_start_time = time.time()

            self.logger.debug(f"Generating speech (async): '{text[:50]}...'")

            # Run blocking I/O operations in a separate thread (TICKET-04)
            # This prevents the event loop from being blocked
            await asyncio.to_thread(
                lambda: (
                    self._engine_lock.acquire(),
                    self._generate_and_play_audio(text),
                    self._engine_lock.release(),
                )[
                    -1
                ]  # Return the result of the last operation
            )

            # Log timing
            duration = time.time() - self._current_speech_start_time
            self._total_speech_time += duration
            self._speech_count += 1
            self.logger.info(f"Speech completed in {duration:.2f}s: '{text[:50]}...'")

        except Exception as e:
            import traceback

            self.logger.error(f"Error generating speech: {e}\n{traceback.format_exc()}")
        finally:
            self._speaking_flag.clear()
            self._current_speech_start_time = None

    async def speak(self, text: str, lang: str = "fr", priority: int = 0) -> bool:
        """
        Speak text (async, non-blocking - TICKET-04)

        This method is now async to avoid blocking the event loop.
        When queue is enabled, messages are queued and processed by worker thread.
        When queue is disabled, speech is generated asynchronously.

        Args:
            text: Text to speak
            lang: Language code
            priority: Message priority (higher = more important)

        Returns:
            True if speech was queued/started successfully
        """
        if not text or not text.strip():
            return False

        if self._is_muted:
            return False

        if not self._engine_ready.wait(timeout=10):
            self.logger.error("Piper TTS not ready")
            return False

        if not self._piper_voice:
            self.logger.error("Piper voice not available")
            return False

        try:
            if self.enable_queue:
                # Queue mode: add to queue for worker thread processing
                message = TTSMessage(
                    priority=-priority, timestamp=time.time(), text=text, lang=lang
                )

                if priority > 5:
                    self._clear_low_priority_messages()

                self._queue.put(message)
                return True
            else:
                # Direct mode: speak immediately using async method (TICKET-04)
                await self._speak_async(text, lang)
                return True
        except Exception as e:
            self.logger.error(f"Error queuing speech: {e}")
            return False

    def _clear_low_priority_messages(self):
        """Clear low-priority messages"""
        try:
            new_queue = queue.PriorityQueue()
            while not self._queue.empty():
                try:
                    message = self._queue.get_nowait()
                    if message.priority < -5:
                        new_queue.put(message)
                except queue.Empty:
                    break
            self._queue = new_queue
        except Exception as e:
            self.logger.error(f"Error clearing messages: {e}")

    def stop(self) -> None:
        """Stop current speech"""
        try:
            if self.enable_queue:
                while not self._queue.empty():
                    try:
                        self._queue.get_nowait()
                        self._queue.task_done()
                    except queue.Empty:
                        break
            self._speaking_flag.clear()
        except Exception as e:
            self.logger.error(f"Error stopping TTS: {e}")

    def is_speaking(self) -> bool:
        """Check if speaking"""
        return self._speaking_flag.is_set()

    def set_voice(self, voice: Optional[str]) -> None:
        """Set voice (model path)"""
        self.voice = voice

    def set_rate(self, rate: int) -> None:
        """Set speech rate"""
        self.rate = max(100, min(300, rate))

    def set_volume(self, volume: float) -> None:
        """Set volume"""
        self.volume = max(0.0, min(1.0, volume))
        if not self._is_muted:
            self._volume_before_mute = self.volume

    def get_volume(self) -> float:
        """Get volume"""
        return self.volume

    def mute(self) -> None:
        """Mute TTS"""
        if not self._is_muted:
            self._volume_before_mute = self.volume
            self._is_muted = True
            self.stop()

    def unmute(self) -> None:
        """Unmute TTS"""
        if self._is_muted:
            self._is_muted = False
            self.volume = self._volume_before_mute

    def is_muted(self) -> bool:
        """Check if muted"""
        return self._is_muted

    def get_timing_stats(self) -> dict:
        """Get timing stats"""
        avg = self._total_speech_time / self._speech_count if self._speech_count > 0 else 0.0
        return {
            "total_speech_time": self._total_speech_time,
            "speech_count": self._speech_count,
            "average_duration": avg,
            "is_speaking": self.is_speaking(),
            "current_duration": (
                time.time() - self._current_speech_start_time
                if self._current_speech_start_time
                else 0.0
            ),
        }

    def get_available_voices(self) -> list:
        """Get available voices (models)"""
        voices = []
        base_dir = Path(__file__).parent.parent.parent / "models" / "piper"
        if base_dir.exists():
            for model in base_dir.glob("*.onnx"):
                voices.append(str(model))
        return voices

    def shutdown(self):
        """Shutdown TTS"""
        self.stop()
        self._stop_flag.set()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=WORKER_THREAD_JOIN_TIMEOUT)

        if self._piper_voice:
            with self._engine_lock:
                self._piper_voice = None

    def __del__(self):
        """Cleanup"""
        try:
            self.shutdown()
        except Exception as e:
            # Avoid exceptions during cleanup in __del__
            # Using getattr to safely access logger if it exists
            if hasattr(self, "logger") and self.logger:
                self.logger.debug(f"Failed to shutdown in __del__: {e}")
