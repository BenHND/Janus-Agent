"""
STTService: Speech-to-Text Service

Handles all STT-related operations for the Janus pipeline including:
- Eager initialization of Whisper STT engine (zero-latency)
- Configuration management (semantic correction, context buffer, etc.)
- Integration with LLM for semantic correction
- Transcription of voice input

This service extracts STT functionality from JanusPipeline to improve
modularity and testability.

TICKET: Zero-Latency Audio Pipeline
- STT engine is initialized immediately on startup (no lazy loading)
- Warmup thread preloads model into memory cache for instant first use
"""

import logging
import threading
from typing import Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from janus.runtime.core.settings import Settings

logger = logging.getLogger(__name__)


class STTService:
    """
    Service for Speech-to-Text operations.
    
    Provides eagerly-initialized STT engine for zero-latency performance.
    Handles semantic correction integration with LLM services.
    """
    
    def __init__(
        self,
        settings: "Settings",
        enabled: bool = False,
        unified_llm_client=None,
        tts_service=None,  # Neural Gatekeeper: TTS service for anti-echo
    ):
        """
        Initialize STT Service with eager loading (zero-latency).
        
        Args:
            settings: Unified settings object
            enabled: Whether voice input is enabled
            unified_llm_client: Optional LLM client for semantic correction
            tts_service: Optional TTS service for anti-echo (Neural Gatekeeper)
        """
        self.settings = settings
        self.enabled = enabled
        self.unified_llm_client = unified_llm_client
        self.tts_service = tts_service  # Neural Gatekeeper
        self._stt = None
        
        # Eager initialization for zero-latency (no lazy loading)
        if self.enabled:
            self._initialize_engine()
            # Start warmup thread to preload model into cache
            self._start_warmup_thread()
    
    def _initialize_engine(self):
        """
        Initialize STT engine eagerly (immediately on service creation).
        This eliminates the 3s delay on first use.
        """
        logger.info("Initializing STT engine (eager loading for zero-latency)...")
        try:
            from ..stt.whisper_stt import WhisperSTT
            
            # Get semantic correction settings
            enable_semantic = self.settings.features.enable_semantic_correction
            semantic_model_path = self.settings.whisper.semantic_correction_model_path
            
            # Determine LLM service to use for semantic correction
            # If semantic_correction_model_path is empty, use unified LLM client
            llm_service = None
            if enable_semantic and not semantic_model_path:
                llm_service = self.unified_llm_client
                if llm_service and llm_service.available:
                    logger.info(
                        "Semantic correction will use main LLM: "
                        f"{self.settings.llm.provider}/{self.settings.llm.model}"
                    )
                else:
                    logger.info(
                        "Semantic correction enabled but main LLM not available. "
                        "Will use fallback methods."
                    )
            elif enable_semantic and semantic_model_path:
                logger.info(
                    f"Semantic correction will use dedicated local model: {semantic_model_path}"
                )
            
            self._stt = WhisperSTT(
                enable_context_buffer=self.settings.whisper.enable_context_buffer,
                enable_semantic_correction=enable_semantic,
                semantic_correction_model_path=semantic_model_path,
                enable_corrections=self.settings.whisper.enable_corrections,
                enable_normalization=True,
                llm_service=llm_service,  # Pass unified LLM client for semantic correction
                models_dir=self.settings.whisper.models_dir,
                language=self.settings.language.default,
                tts_service=self.tts_service,  # Neural Gatekeeper for anti-echo
            )
            logger.info("STT engine initialized successfully (ready for instant use)")
        except Exception as e:
            logger.error(f"Failed to initialize STT engine: {e}")
            self._stt = None
    
    def _start_warmup_thread(self):
        """
        Start background thread to warm up STT engine.
        Transcribes silent audio to preload model into memory cache.
        """
        def warmup():
            if self._stt is None:
                return
            
            try:
                logger.debug("Starting STT warmup (preloading model into cache)...")
                # Create 1 second of silent audio at 16kHz
                silent_audio = np.zeros(16000, dtype=np.int16)
                
                # Save to temporary file and transcribe to warm up model
                import tempfile
                import wave
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_path = temp_file.name
                    
                with wave.open(temp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)
                    wf.writeframes(silent_audio.tobytes())
                
                # Transcribe silent audio to warm up the model
                self._stt.transcribe(temp_path)
                
                # Cleanup
                import os
                try:
                    os.remove(temp_path)
                except OSError:
                    pass  # File may already be deleted or not exist
                
                logger.info("STT warmup completed (model preloaded into cache)")
            except Exception as e:
                logger.debug(f"STT warmup failed (non-critical): {e}")
        
        warmup_thread = threading.Thread(target=warmup, daemon=True, name="STT-Warmup")
        warmup_thread.start()
    
    @property
    def stt(self):
        """
        Get STT engine instance.
        
        Returns:
            WhisperSTT instance or None if not enabled/failed to load
        """
        return self._stt
    
    async def listen_and_transcribe_async(self) -> Optional[str]:
        """
        Listen for voice input and transcribe asynchronously.
        
        Returns:
            Transcribed text or None if STT not available or transcription failed
        
        Raises:
            ValueError: If STT is not enabled
        """
        if not self.enabled:
            raise ValueError("Voice input not enabled")
        
        if not self.stt:
            raise ValueError("STT engine not available")
        
        try:
            transcription = await self.stt.listen_and_transcribe_async()
            if transcription:
                logger.info(f"Transcribed: '{transcription}'")
            return transcription
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None
    
    def listen_and_transcribe(self) -> Optional[str]:
        """
        Listen for voice input and transcribe (synchronous version).
        
        Returns:
            Transcribed text or None if STT not available or transcription failed
        
        Raises:
            ValueError: If STT is not enabled
        """
        if not self.enabled:
            raise ValueError("Voice input not enabled")
        
        if not self.stt:
            raise ValueError("STT engine not available")
        
        try:
            transcription = self.stt.listen_and_transcribe()
            if transcription:
                logger.info(f"Transcribed: '{transcription}'")
            return transcription
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None
    
    def is_available(self) -> bool:
        """
        Check if STT engine is available.
        
        Returns:
            True if STT is enabled and engine loaded successfully
        """
        return self.enabled and self.stt is not None
    
    def cleanup(self):
        """Clean up STT resources."""
        if self._stt is not None:
            try:
                # WhisperSTT might have cleanup methods
                if hasattr(self._stt, 'cleanup'):
                    self._stt.cleanup()
                self._stt = None
                logger.debug("STT engine cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up STT: {e}")
