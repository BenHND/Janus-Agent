"""
Whisper STT - Transcription Module
Handles audio transcription using Whisper models
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("whisper_transcriber")


class WhisperTranscriber:
    """Audio transcription using Whisper"""

    def __init__(
        self,
        model_size: str = "base",
        effective_language: str = "fr",
        use_faster_whisper: bool = True,
        lazy_load: bool = True,
        use_gpu: bool = True,
        device: Optional[str] = None,
        models_dir: Optional[str] = None,
        realtime_engine=None,
    ):
        """
        Initialize transcriber

        Args:
            model_size: Whisper model size
            effective_language: Language for transcription
            use_faster_whisper: Use faster-whisper for realtime transcription
            lazy_load: Lazy load Whisper model on first use
            use_gpu: Use GPU acceleration if available
            device: Specific device to use or None for auto-detect
            models_dir: Directory for Whisper models
            realtime_engine: Optional RealtimeSTTEngine instance
        """
        self.model_size = model_size
        self.effective_language = effective_language
        self.use_faster_whisper = use_faster_whisper
        self.lazy_load = lazy_load
        self.use_gpu = use_gpu
        self.device = device
        self.models_dir = models_dir or os.environ.get("SPECTRA_MODELS_DIR", "models/whisper")
        self.realtime_engine = realtime_engine

        self.model = None
        self._model_loaded = False

        # Load model if not lazy loading and no realtime engine
        if not self.realtime_engine and not lazy_load:
            self._load_whisper_model(model_size)
        elif self.realtime_engine:
            self._model_loaded = True
        else:
            logger.info(f"Whisper model '{model_size}' will be lazy loaded on first use")

    def _load_whisper_model(self, model_size: str):
        """
        Load Whisper model with GPU support

        Args:
            model_size: Model size to load
        """
        if self._model_loaded:
            return

        import whisper

        # Set models directory if needed
        if self.models_dir and "TORCH_HOME" not in os.environ:
            os.environ["TORCH_HOME"] = str(Path(self.models_dir).parent)
            logger.info(f"Using models directory: {self.models_dir}")

        # Determine device
        effective_device = self.device
        if effective_device is None and self.use_gpu:
            try:
                from ..utils.gpu_utils import get_whisper_device

                effective_device = get_whisper_device()
            except ImportError:
                effective_device = "cpu"
        elif effective_device is None:
            effective_device = "cpu"

        logger.info(f"Loading Whisper model '{model_size}' on device '{effective_device}'...")

        try:
            # Load model with custom download root
            self.model = whisper.load_model(
                model_size,
                device=effective_device,
                download_root=self.models_dir if self.models_dir else None,
            )
            self._model_loaded = True
            logger.info(f"✓ Whisper model loaded on {effective_device}")
        except Exception as e:
            # Fallback to CPU if GPU fails
            if effective_device != "cpu":
                logger.info(f"Failed to load on {effective_device}: {e}")
                logger.info("Falling back to CPU...")
                self.model = whisper.load_model(
                    model_size,
                    device="cpu",
                    download_root=self.models_dir if self.models_dir else None,
                )
                self._model_loaded = True
                self.device = "cpu"
            else:
                raise

    def _ensure_model_loaded(self):
        """Ensure Whisper model is loaded (for lazy loading)"""
        if not self._model_loaded and self.model is None and not self.realtime_engine:
            self._load_whisper_model(self.model_size)

    async def transcribe_async(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text asynchronously

        Args:
            audio_path: Path to audio file
            language: Language code or None to use effective_language

        Returns:
            Dictionary with transcription results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcribe, audio_path, language)

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file to text using Whisper

        Args:
            audio_path: Path to audio file
            language: Language code or None to use effective_language

        Returns:
            Dictionary with raw transcription and metadata
        """
        # Ensure model is loaded
        self._ensure_model_loaded()

        start_time = time.time()

        try:
            logger.info(f"Transcribing audio...")

            # Determine fp16 support
            use_fp16 = False
            if self.use_gpu and not self.realtime_engine:
                try:
                    from ..utils.gpu_utils import supports_fp16

                    use_fp16 = supports_fp16()
                except ImportError:
                    pass

            # Use effective language
            effective_language = (
                language if language and language != "auto" else self.effective_language
            )
            logger.info(f"Transcribing with explicit language: {effective_language}")

            # Transcribe with realtime engine if available
            if self.realtime_engine:
                transcription_result = self.realtime_engine.transcribe_file(
                    audio_path,
                    language=effective_language,
                )
                raw_text = transcription_result.text
                logger.info(
                    f"Raw transcription (faster-whisper): '{raw_text}' (language: {effective_language})"
                )
            else:
                # Use standard whisper
                result = self.model.transcribe(
                    audio_path, language=effective_language, fp16=use_fp16
                )
                raw_text = result["text"].strip()
                logger.info(f"Raw transcription: '{raw_text}' (language: {effective_language})")

            duration = time.time() - start_time

            return {
                "raw": raw_text,
                "language": effective_language,
                "duration": duration,
                "success": True,
            }

        except Exception as e:
            error = str(e)
            logger.info(f"Transcription error: {error}")
            duration = time.time() - start_time

            return {
                "raw": "",
                "language": language,
                "duration": duration,
                "success": False,
                "error": error,
            }
    
    def cleanup(self):
        """
        Cleanup model resources to free memory.
        
        IMPORTANT: This method should be called explicitly before the object is destroyed.
        While __del__ provides automatic cleanup, relying on it is not recommended as
        Python's garbage collection timing is non-deterministic.
        
        For deterministic cleanup, consider using this class as a context manager
        or call cleanup() explicitly when done.
        
        NOTE: The architecture ensures only ONE model is loaded at a time:
        - If realtime_engine is provided, self.model is never loaded
        - If realtime_engine fails, transcription returns error (no fallback to self.model)
        - This prevents double model loading (500MB-2GB memory issue)
        """
        if self.model is not None:
            logger.info("Cleaning up Whisper model")
            try:
                # Clear model from memory
                del self.model
                self.model = None
                self._model_loaded = False
                
                # Force garbage collection
                import gc
                gc.collect()
                
                # On CUDA, clear cache
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
                    
                logger.info("Whisper model cleanup complete")
            except Exception as e:
                logger.warning(f"Error during model cleanup: {e}")
        
        if self.realtime_engine is not None:
            logger.info("Cleaning up realtime engine")
            try:
                # Realtime engines should have their own cleanup
                if hasattr(self.realtime_engine, 'cleanup'):
                    self.realtime_engine.cleanup()
                del self.realtime_engine
                self.realtime_engine = None
                logger.info("Realtime engine cleanup complete")
            except Exception as e:
                logger.warning(f"Error during realtime engine cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry - allows use of 'with' statement for deterministic cleanup."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup is called."""
        self.cleanup()
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """
        Destructor - cleanup resources.
        
        WARNING: This is a fallback only. For deterministic cleanup, use the context manager
        protocol (with statement) or call cleanup() explicitly.
        """
        try:
            self.cleanup()
        except Exception as e:
            # Log cleanup errors but don't raise from destructor
            logger.warning(f"Error during WhisperTranscriber cleanup in destructor: {e}")
