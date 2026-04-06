"""
Wake Word Detector Module
TICKET-P3-02: Mode "Mains Libres" (Wake Word)

This module provides lightweight wake word detection for hands-free operation.
It listens passively with low power consumption and triggers Whisper recording
only when the wake word is detected.

Wake words supported:
- French: "Hey Janus" / "Eh Janus"
- English: "Hey Janus"

Architecture:
- Uses openWakeWord for efficient on-device detection
- Runs in separate thread to avoid blocking
- Low CPU usage (~1-5% idle)
- Integrates with existing Whisper STT pipeline
"""

import logging
import threading
import time
from math import gcd
from typing import Any, Callable, Optional

import numpy as np
import pyaudio
from scipy import signal

from janus.logging import get_logger

logger = get_logger("wake_word_detector")

# Check for openWakeWord availability
try:
    from openwakeword.model import Model as WakeWordModel
    HAS_OPENWAKEWORD = True
except ImportError:
    HAS_OPENWAKEWORD = False
    logger.warning("openWakeWord not available. Install with: pip install openwakeword")


class WakeWordDetector:
    """
    Lightweight wake word detector for hands-free operation.
    
    Uses openWakeWord for efficient detection with minimal CPU usage.
    Runs in background thread and triggers callback when wake word detected.
    """
    
    def __init__(
        self,
        recorder: Any = None,
        model: str = "hey_janus",
        threshold: float = 0.5,
        cooldown_ms: int = 1000,
        chunk_duration_ms: int = 80,
        sample_rate: int = 16000,
        inference_framework: str = "onnx",
    ):
        """
        Initialize wake word detector.
        
        Args:
            recorder: WhisperRecorder instance (optional but recommended)
            model: Model name (e.g. "hey_janus") or path to custom model file (.onnx/.tflite)
            threshold: Detection threshold (0.0-1.0). Lower = more sensitive, higher = more accurate.
            cooldown_ms: Cooldown period after detection to avoid multiple triggers (milliseconds)
            chunk_duration_ms: Duration of audio chunks in milliseconds
            sample_rate: Audio sample rate (16000 Hz recommended for wake word detection)
            inference_framework: Framework for inference ("onnx" or "tflite")
        """
        if not HAS_OPENWAKEWORD:
            raise ImportError(
                "openWakeWord is required for wake word detection. "
                "Install with: pip install openwakeword"
            )
        
        self.recorder = recorder
        self.model = model
        self.threshold = threshold
        self.cooldown_ms = cooldown_ms
        self.chunk_duration_ms = chunk_duration_ms
        self.sample_rate = sample_rate
        self.inference_framework = inference_framework
        
        # Audio parameters
        self.audio = None
        self.stream = None
        
        if self.recorder:
            # Use shared recorder (RECOMMENDED for performance and reliability)
            self.native_rate = self.recorder.native_rate
            logger.info(f"Using shared recorder with native rate: {self.native_rate}Hz")
        else:
            # Fallback to own audio stream (NOT RECOMMENDED - may cause device conflicts)
            # STRONGLY DISCOURAGED: Multiple PyAudio streams can cause "Device busy" errors
            logger.warning(
                "WakeWordDetector initialized without recorder. "
                "This may cause 'Device busy' errors if another stream is active. "
                "RECOMMENDATION: Pass a WhisperRecorder instance via recorder parameter."
            )
            # Consider raising an error in production:
            # raise ValueError("recorder parameter is required to avoid audio device conflicts")
            
            self.audio = pyaudio.PyAudio()
            try:
                default_device = self.audio.get_default_input_device_info()
                self.native_rate = int(default_device['defaultSampleRate'])
                logger.info(f"Detected native microphone sample rate: {self.native_rate}Hz")
            except Exception as e:
                logger.warning(f"Could not detect native sample rate: {e}. Defaulting to 16000Hz")
                self.native_rate = 16000

        # We capture at native rate, but process at 16000Hz
        self.target_rate = 16000
        
        # Calculate chunk size for native rate to match duration
        self.chunk_size = int(self.native_rate * self.chunk_duration_ms / 1000)
        
        # Buffer for accumulating audio chunks
        self.audio_buffer = bytearray()
        # Target chunk size for openWakeWord (16kHz * 80ms = 1280 samples * 2 bytes = 2560 bytes)
        # openWakeWord expects chunks of 1280 samples
        self.target_chunk_size = 1280 * 2 # Fixed to exactly what openWakeWord expects (1280 samples)
        
        # Ensure chunk_duration_ms matches what we expect (80ms)
        if self.chunk_duration_ms != 80:
            logger.warning(f"Adjusting chunk_duration_ms from {self.chunk_duration_ms} to 80ms for openWakeWord compatibility")
            self.chunk_duration_ms = 80
            
        self.stream = None
        
        # State tracking
        self._last_detection_time = 0
        
        # Debug: Recording buffer
        self._debug_audio_buffer = []
        self._debug_start_time = time.time()
        self._debug_saved = False
        
        # Threading
        self._stop_event = threading.Event()
        self._detector_thread = None
        self._callback = None
        
        # Wake word model
        self._model = None
        self._model_name = None  # Track the actual model name for predictions
        self._initialize_model()
        
        logger.info(f"WakeWordDetector initialized with model: {self.model}")
        logger.info(f"Detection threshold: {self.threshold}, chunk: {self.chunk_duration_ms}ms")
    
    def _initialize_model(self):
        """Initialize the wake word detection model."""
        import os
        from pathlib import Path
        
        try:
            logger.info("Loading wake word model...")
            logger.info(f"Requested model: {self.model}")
            
            # Determine if this is a path or a model name using robust path detection
            model_path = Path(self.model)
            is_path = model_path.exists() or model_path.is_absolute() or len(model_path.parts) > 1
            
            # Check for infrastructure models in models/wakeword
            # We need to pass these explicitly because openwakeword expects them in its package dir by default
            base_model_dir = Path("models/wakeword")
            melspec_path = base_model_dir / "melspectrogram.onnx"
            embedding_path = base_model_dir / "embedding_model.onnx"
            
            kwargs = {}
            if melspec_path.exists() and embedding_path.exists():
                logger.info(f"Using local infrastructure models from {base_model_dir}")
                kwargs["melspec_model_path"] = str(melspec_path)
                kwargs["embedding_model_path"] = str(embedding_path)
            
            if is_path:
                # Custom model path
                logger.info(f"Loading custom model from path: {self.model}")
                self._model = WakeWordModel(
                    inference_framework=self.inference_framework,
                    wakeword_models=[self.model],
                    **kwargs
                )
                # Extract model name from path for predictions (remove extension)
                # CRITICAL: openWakeWord uses the filename without extension as the key
                # BUT if the model was trained with a specific name, it might be different.
                # We should inspect the model keys to be sure.
                self._model_name = model_path.stem
                
                # Verify the key exists
                if hasattr(self._model, 'models'):
                    keys = list(self._model.models.keys())
                    # Force use of the first key if we only loaded one model
                    if len(keys) == 1:
                        logger.info(f"Forcing use of single available model key: {keys[0]}")
                        self._model_name = keys[0]
                    elif self._model_name not in keys:
                        logger.warning(f"Model name '{self._model_name}' not found in loaded models: {keys}")
                        if len(keys) > 0:
                            logger.info(f"Using first available model key: {keys[0]}")
                            self._model_name = keys[0]
            else:
                # Pre-trained model name
                logger.info(f"Loading pre-trained model: {self.model}")
                self._model = WakeWordModel(
                    inference_framework=self.inference_framework,
                    wakeword_models=[self.model],
                    **kwargs
                )
                self._model_name = self.model
            
            logger.info(f"✓ Wake word model loaded: {self.model}")
            logger.info(f"Model name for predictions: {self._model_name}")
            
            if hasattr(self._model, 'models'):
                logger.info(f"Available models in instance: {list(self._model.models.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize wake word model: {e}")
            logger.error(f"Requested model: {self.model}")
            logger.error(f"Common pre-trained models: hey_mycroft, alexa")
            logger.error(f"For custom 'Hey Janus': train model and place in models/wakeword/hey_janus.onnx")
            raise
    
    def start(self, callback: Callable[[], None]):
        """
        Start wake word detection.
        
        Args:
            callback: Function to call when wake word is detected
        """
        self._callback = callback
        
        if self.recorder:
            # Register as listener to WhisperRecorder
            self.recorder.register_listener(self._process_audio_chunk)
            logger.info("✓ Wake word detector attached to audio stream")
        else:
            # Start standalone detection thread (NOT RECOMMENDED)
            logger.warning("Starting standalone wake word thread - may conflict with other audio streams")
            if self.stream is None:
                self.audio = pyaudio.PyAudio()
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.native_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
            
            self._stop_event.clear()
            self._detector_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True
            )
            self._detector_thread.start()
            logger.info("✓ Wake word detector thread started")
    
    def stop(self):
        """Stop wake word detection."""
        # Method 1: Unregister from recorder
        if self.recorder:
            self.recorder.unregister_listener(self._process_audio_chunk)
            logger.info("✓ Wake word detector detached")
            
        # Method 2: Stop standalone thread
        if self._detector_thread and self._detector_thread.is_alive():
            logger.info("Stopping wake word detector thread...")
            self._stop_event.set()
            self._detector_thread.join(timeout=2.0)
            
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.debug(f"Error closing stream: {e}")
                finally:
                    self.stream = None
            logger.info("✓ Wake word detector thread stopped")
    
    def _process_audio_chunk(self, chunk: bytes):
        """Process audio chunk from recorder"""
        try:
            # Accumulate audio in buffer
            self.audio_buffer.extend(chunk)
            
            # Process when we have enough data (80ms worth)
            while len(self.audio_buffer) >= self.target_chunk_size:
                # Extract one chunk
                chunk_data = self.audio_buffer[:self.target_chunk_size]
                self.audio_buffer = self.audio_buffer[self.target_chunk_size:]
                
                # Convert to numpy array
                audio_array = np.frombuffer(chunk_data, dtype=np.int16)
                
                # Run wake word detection
                # Ensure we pass exactly 1280 samples
                if len(audio_array) == 1280:
                    prediction = self._model.predict(audio_array)
                    
                    # Check if the wake word exceeded threshold
                    score = prediction.get(self._model_name, 0.0)
                    
                    # Log score for debugging (debug level to avoid spam)
                    if score > 0.001:
                        logger.debug(f"Wake word score: {score:.4f} (Threshold: {self.threshold})")

                    # Check cooldown
                    current_time = time.time() * 1000
                    if score >= self.threshold:
                        if (current_time - self._last_detection_time) > self.cooldown_ms:
                            logger.info(f"✓ Wake word detected: {self._model_name} (score: {score:.3f})")
                            self._last_detection_time = current_time
                            
                            # Trigger callback
                            if self._callback:
                                try:
                                    self._callback()
                                except Exception as e:
                                    logger.error(f"Error in wake word callback: {e}")
                        else:
                            logger.info("Ignored due to cooldown")
                else:
                    pass

        except Exception as e:
            logger.error(f"Error processing wake word chunk: {e}")
    
    def _detection_loop(self):
        """Main detection loop running in background thread."""
        logger.info("Wake word detection loop started")
        
        # Debug: print available models in prediction once
        first_run = True
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Read audio chunk
                    audio_data = self.stream.read(
                        self.chunk_size,
                        exception_on_overflow=False
                    )
                    
                    # Convert to numpy array
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Resample if necessary (native rate -> 16000Hz)
                    if self.native_rate != self.target_rate:
                        # Calculate upsampling and downsampling factors for resample_poly
                        common = gcd(self.native_rate, self.target_rate)
                        up = self.target_rate // common
                        down = self.native_rate // common
                        
                        # Use resample_poly which is ~10x faster than FFT-based resample
                        audio_array = signal.resample_poly(audio_array, up, down).astype(np.int16)

                    # Debug: Check audio levels
                    rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
                    if first_run:
                        logger.info(f"DEBUG: Initial audio RMS: {rms:.2f}")
                    
                    if rms < 100 and not first_run:
                        # Only log silence occasionally
                        pass
                    elif rms > 1000 and first_run:
                         logger.info(f"DEBUG: Audio signal detected (RMS: {rms:.2f})")

                    # Run wake word detection
                    prediction = self._model.predict(audio_array)
                    
                    if first_run:
                        logger.info(f"DEBUG: Model prediction keys: {list(prediction.keys())}")
                        logger.info(f"DEBUG: Expected model name: {self._model_name}")
                        first_run = False
                    
                    # Check if the wake word exceeded threshold
                    score = prediction.get(self._model_name, 0.0)
                    
                    # Debug: log low confidence detections
                    if score > 0.01:
                        # Only log occasionally to avoid spamming, or log all for now since we are debugging
                        if score > 0.1:
                            logger.debug(f"Wake word score: {score:.3f} (threshold: {self.threshold})")
                    
                    if score >= self.threshold:
                        # Check cooldown using timestamp (non-blocking)
                        current_time = time.time() * 1000
                        if (current_time - self._last_detection_time) > self.cooldown_ms:
                            logger.info(f"✓ Wake word detected: {self._model_name} (score: {score:.3f})")
                            self._last_detection_time = current_time
                            
                            # Trigger callback
                            if self._callback:
                                try:
                                    self._callback()
                                except Exception as e:
                                    logger.error(f"Wake word callback error: {e}")
                        else:
                            # Still in cooldown period
                            logger.debug(f"Wake word detected but in cooldown period (score: {score:.3f})")
                
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.error(f"Detection loop error: {e}")
                        time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Fatal error in detection loop: {e}")
        
        finally:
            logger.info("Wake word detection loop finished")
    
    def is_running(self) -> bool:
        """Check if detector is currently running."""
        return (
            self._detector_thread is not None
            and self._detector_thread.is_alive()
            and not self._stop_event.is_set()
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.stop()
        if self.audio:
            self.audio.terminate()
    
    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            self.stop()
            if self.audio:
                self.audio.terminate()
        except Exception:
            pass


def create_wake_word_detector(
    recorder: Any,
    enable_wake_word: bool = False,
    model: str = "hey_janus",
    threshold: float = 0.5,
    cooldown_ms: int = 1000,
) -> Optional[WakeWordDetector]:
    """
    Factory function to create wake word detector.
    
    Args:
        recorder: WhisperRecorder instance
        enable_wake_word: Whether to enable wake word detection
        model: Model name or path to custom model file
        threshold: Detection threshold
        cooldown_ms: Cooldown period after detection (milliseconds)
    
    Returns:
        WakeWordDetector instance if enabled and available, None otherwise
    """
    if not enable_wake_word:
        return None
        
    if not HAS_OPENWAKEWORD:
        logger.warning(
            "Wake word detection requested but openWakeWord not installed. "
            "Install with: pip install openwakeword"
        )
        return None
        
    try:
        detector = WakeWordDetector(
            recorder=recorder,
            model=model,
            threshold=threshold,
            cooldown_ms=cooldown_ms,
        )
        return detector
    except Exception as e:
        logger.error(f"Failed to create wake word detector: {e}")
        print(f"❌ Failed to create wake word detector: {e}")
        return None
