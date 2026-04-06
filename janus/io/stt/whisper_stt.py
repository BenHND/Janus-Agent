"""
Whisper-based Speech-to-Text implementation with voice activity detection
Enhanced with correction dictionary, text normalization, audio logging, and calibration

This module now acts as a facade to maintain backward compatibility.
The actual implementation is split across multiple modules:
- whisper_recorder.py: Recording logic
- whisper_transcriber.py: Transcription logic
- whisper_post_processor.py: Post-processing (corrections, normalization)

CRITICAL AUDIO QUALITY NOTES:
==============================
Whisper was trained on RAW, unfiltered audio containing:
- Natural background noise, breathing, micro-pauses
- Clicks, echoes, ambient sounds
- Natural speech patterns with all imperfections

DO NOT apply aggressive filtering:
❌ NO VAD for audio filtering (cuts word beginnings/endings)
❌ NO aggressive noise suppression (makes voice robotic)
❌ NO silence removal (Whisper needs natural pauses for alignment)
❌ NO short chunks (< 5 seconds) - Whisper needs context

✅ DO provide:
✅ Raw 16kHz mono PCM 16-bit WAV files
✅ 5-30 second recordings (optimal for context)
✅ Complete, unfiltered audio
✅ Only use energy-based detection for recording stop (not VAD)
"""

import asyncio
import os
import wave
from typing import Any, Callable, Dict, List, Optional, Tuple

# Ajout de PyAudio pour le keep-alive micro
try:
    import pyaudio
except ImportError:  # pragma: no cover - environnement sans audio
    pyaudio = None

from janus.logging import get_logger
from janus.resources.locale_loader import get_locale_loader

from .audio_logger import AudioLogger
from .calibration_manager import CalibrationManager, CalibrationProfile
from .correction_dictionary import CorrectionDictionary
from .whisper_post_processor import WhisperPostProcessor
from .whisper_recorder import WhisperRecorder
from .whisper_transcriber import WhisperTranscriber

logger = get_logger("whisper_stt")


# Optional imports
try:
    from .context_buffer import ContextBuffer

    HAS_CONTEXT_BUFFER = True
except ImportError:
    HAS_CONTEXT_BUFFER = False

try:
    from .realtime_stt_engine import RealtimeSTTEngine

    HAS_REALTIME_STT = True
except ImportError:
    HAS_REALTIME_STT = False

try:
    from .mlx_stt_engine import MLXSTTEngine

    HAS_MLX_STT = True
except ImportError:
    HAS_MLX_STT = False

try:
    from .voice_adaptation_cache import VoiceAdaptationCache

    HAS_VOICE_CACHE = True
except ImportError:
    HAS_VOICE_CACHE = False


def _is_apple_silicon() -> bool:
    """Check if running on Apple Silicon (M1/M2/M3/M4)."""
    import platform
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def get_effective_language(
    default_language: str = "fr", calibration_profile: Optional["CalibrationProfile"] = None
) -> str:
    """
    Get the effective language to use for transcription.
    Never returns "auto" or None - always returns an explicit language code.
    Supports any language code supported by Whisper - falls back to "en" if not specified.

    Args:
        default_language: Default language from settings (e.g., "fr", "en", "es", "de")
        calibration_profile: Optional calibration profile that may override language

    Returns:
        Explicit language code, never "auto" or None. Falls back to "en" if invalid.
    """
    # If calibration profile has an explicit language (not "auto"), use it
    if calibration_profile and hasattr(calibration_profile, "language"):
        profile_lang = calibration_profile.language
        if profile_lang and profile_lang != "auto" and profile_lang.strip():
            # Normalize - accept any language code
            profile_lang = profile_lang.lower().strip()
            return profile_lang

    # Fall back to default language, ensuring it's never "auto" or empty
    if default_language and default_language != "auto" and default_language.strip():
        # Normalize - accept any language code
        default_language = default_language.lower().strip()
        return default_language

    # Ultimate fallback: English (more universal than French)
    return "en"


class WhisperSTT:
    """Speech-to-Text using OpenAI Whisper with voice activity detection (Facade)"""

    def __init__(
        self,
        model_size: str = "base",
        sample_rate: int = 16000,
        chunk_duration_ms: int = 20,
        silence_threshold: int = 30,  # TICKET: Reduced from 60 to 30 (~0.6s) for faster response
        enable_corrections: bool = True,
        enable_normalization: bool = True,
        enable_logging: bool = True,
        correction_dict_path: Optional[str] = None,
        log_dir: str = "audio_logs",
        user_id: str = "default",
        language: str = "fr",
        # Phase 15 parameters
        enable_context_buffer: bool = True,
        enable_semantic_correction: bool = True,
        semantic_correction_model_path: Optional[str] = None,
        context_buffer_duration: float = 2.5,
        context_overlap_duration: float = 1.0,
        # Phase 16 parameters
        use_faster_whisper: bool = True,
        enable_natural_reformatter: bool = False,
        natural_reformatter_model_path: Optional[str] = None,
        enable_voice_cache: bool = False,
        voice_cache_db_path: str = "voice_cache.db",
        voice_cache_encryption: bool = True,
        # Performance optimization parameters
        lazy_load: bool = True,
        use_gpu: bool = True,
        device: Optional[str] = None,
        models_dir: Optional[str] = None,
        # VAD parameters for faster-whisper
        enable_vad_filter: bool = False,
        vad_min_silence_duration_ms: int = 500,
        vad_speech_pad_ms: int = 200,
        # MLX parameters for Apple Silicon
        mlx_batch_size: int = 12,
        # TICKET: Unified LLM Architecture
        llm_service=None,  # Centralized LLM service for semantic correction
        # TICKET-STT-002: Speaker verification parameters
        enable_speaker_verification: bool = False,
        speaker_embedding_path: Optional[str] = None,
        speaker_similarity_threshold: float = 0.75,
        # TICKET: Zero-Latency Audio Pipeline
        tts_service=None,  # TTS service for anti-echo (Neural Gatekeeper)
    ):
        """
        Initialize Whisper STT with enhanced features

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large, large-v2, large-v3)
            sample_rate: Audio sample rate in Hz (16000 optimal for Whisper)
            chunk_duration_ms: Duration of each audio chunk in milliseconds
            silence_threshold: Number of consecutive silent chunks to stop recording (~0.6s at default 30 chunks)
            enable_corrections: Enable correction dictionary
            enable_normalization: Enable text normalization
            enable_logging: Enable audio/transcription logging
            correction_dict_path: Optional path to custom correction dictionary
            log_dir: Directory for audio logs
            user_id: User ID for calibration profile
            language: Default language code (fr, en) - never "auto"
            enable_context_buffer: Enable context buffering
            enable_semantic_correction: Enable LLM-based semantic correction
            semantic_correction_model_path: Path to GGUF model for semantic correction
            context_buffer_duration: Duration of context buffer in seconds
            context_overlap_duration: Duration of overlap between segments
            use_faster_whisper: Use faster-whisper for realtime transcription
            enable_natural_reformatter: Enable natural language reformatting
            natural_reformatter_model_path: Path to LLM model for reformatting
            enable_voice_cache: Enable voice adaptation cache
            voice_cache_db_path: Path to voice cache database
            voice_cache_encryption: Enable AES256 encryption for voice cache
            lazy_load: Lazy load Whisper model on first use
            use_gpu: Use GPU acceleration if available
            device: Specific device to use ("cuda", "mps", "cpu") or None for auto-detect
            models_dir: Directory for Whisper models
            enable_vad_filter: Enable VAD filtering for faster-whisper
            vad_min_silence_duration_ms: Minimum silence duration for VAD in milliseconds
            vad_speech_pad_ms: Speech padding duration for VAD in milliseconds
            mlx_batch_size: Batch size for MLX inference on Apple Silicon (higher = faster but more memory)
            llm_service: Centralized LLM service for semantic correction (from janus.ai.llm.llm_service)
            tts_service: TTS service for anti-echo (Neural Gatekeeper)

        Note: VAD parameters removed - we use energy-based silence detection only
        Note: Semantic correction uses main LLM by default; model paths are optional overrides
        Note: silence_threshold reduced from 60 to 30 chunks for faster response (~0.6s instead of 1.2s)
        """
        # Store parameters
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.silence_threshold = silence_threshold
        self.enable_corrections = enable_corrections
        self.enable_normalization = enable_normalization
        self.enable_logging = enable_logging
        self.user_id = user_id
        self.tts_service = tts_service  # Neural Gatekeeper

        # Store default language (never "auto")
        self.default_language = language if language and language != "auto" else "fr"

        # Initialize calibration manager
        self.calibration_manager = CalibrationManager()
        self.calibration_profile = self.calibration_manager.get_profile(user_id)

        # Determine effective language (never "auto" or None)
        self.effective_language = get_effective_language(
            self.default_language, self.calibration_profile
        )
        
        # Initialize locale loader for i18n
        self.locale_loader = get_locale_loader()
        
        # Use effective language for logs (or fallback to English if not available)
        log_language = self.effective_language if self.effective_language in ("en", "fr") else "en"
        logger.info(self.locale_loader.get("whisper.using_language", language=log_language).format(lang=self.effective_language))

        # Initialize realtime STT engine if requested
        # Priority: MLX (Apple Silicon) > faster-whisper > standard whisper
        self.realtime_engine = None
        self.use_faster_whisper = use_faster_whisper
        self.use_mlx = False  # Track if using MLX engine
        
        # Determine log language (use effective language if available in locale files, else English)
        self.log_language = self.effective_language if self.effective_language in ("en", "fr") else "en"
        
        # Try MLX first on Apple Silicon (TICKET-P2-01: MLX Whisper for instant STT)
        if _is_apple_silicon() and HAS_MLX_STT:
            try:
                logger.info(self.locale_loader.get("whisper.mlx_detected", language=self.log_language))
                self.realtime_engine = MLXSTTEngine(
                    model_size=model_size,
                    language=self.effective_language,
                    batch_size=mlx_batch_size,
                )
                self.use_mlx = True
                self.use_faster_whisper = False  # MLX takes priority
                logger.info(self.locale_loader.get("whisper.mlx_initialized", language=self.log_language).format(
                    model=model_size, lang=self.effective_language
                ))
            except Exception as e:
                logger.warning(self.locale_loader.get("whisper.mlx_failed", language=self.log_language).format(error=str(e)))
                logger.info(self.locale_loader.get("whisper.mlx_fallback", language=self.log_language))
        elif _is_apple_silicon() and not HAS_MLX_STT:
            logger.info(self.locale_loader.get("whisper.mlx_not_installed", language=self.log_language))
        
        # Fall back to faster-whisper if MLX not available/failed
        if self.realtime_engine is None and use_faster_whisper and HAS_REALTIME_STT:
            try:
                from ..utils.gpu_utils import get_optimal_compute_type, get_optimal_device

                optimal_device = device if device else get_optimal_device()
                optimal_compute_type = get_optimal_compute_type(optimal_device)

                # faster-whisper doesn't support mps → force CPU
                if optimal_device == "mps":
                    logger.info(self.locale_loader.get("whisper.faster_whisper_no_mps", language=self.log_language))
                    optimal_device = "cpu"

                logger.info(self.locale_loader.get("whisper.realtime_initializing", language=self.log_language))
                logger.info(self.locale_loader.get("whisper.realtime_device", language=self.log_language).format(
                    device=optimal_device, compute_type=optimal_compute_type
                ))

                self.realtime_engine = RealtimeSTTEngine(
                    model_size=model_size,
                    device=optimal_device,
                    compute_type=optimal_compute_type,
                    language=self.effective_language,
                    use_faster_whisper=True,
                    sample_rate=sample_rate,
                    enable_vad_filter=enable_vad_filter,
                    vad_min_silence_duration_ms=vad_min_silence_duration_ms,
                    vad_speech_pad_ms=vad_speech_pad_ms,
                    enable_speaker_verification=enable_speaker_verification,
                    speaker_embedding_path=speaker_embedding_path,
                    speaker_similarity_threshold=speaker_similarity_threshold,
                )
                logger.info(self.locale_loader.get("whisper.realtime_initialized", language=self.log_language).format(
                    device=optimal_device
                ))
            except Exception as e:
                logger.info(self.locale_loader.get("whisper.realtime_failed", language=self.log_language).format(error=str(e)))
                logger.info(self.locale_loader.get("whisper.realtime_fallback", language=self.log_language))
                self.use_faster_whisper = False
        elif self.realtime_engine is None and use_faster_whisper and not HAS_REALTIME_STT:
            logger.info(self.locale_loader.get("whisper.faster_whisper_unavailable", language=self.log_language))
            self.use_faster_whisper = False

        # Initialize context buffer
        self.context_buffer = None
        if enable_context_buffer and HAS_CONTEXT_BUFFER:
            self.context_buffer = ContextBuffer(
                buffer_duration_sec=context_buffer_duration,
                overlap_duration_sec=context_overlap_duration,
                sample_rate=sample_rate,
            )
            logger.info(self.locale_loader.get("whisper.context_buffer_enabled", language=self.log_language).format(
                duration=context_buffer_duration, overlap=context_overlap_duration
            ))
        elif enable_context_buffer and not HAS_CONTEXT_BUFFER:
            logger.info(self.locale_loader.get("whisper.context_buffer_unavailable", language=self.log_language))

        # Initialize voice cache
        self.voice_cache = None
        if enable_voice_cache and HAS_VOICE_CACHE:
            try:
                self.voice_cache = VoiceAdaptationCache(
                    db_path=voice_cache_db_path,
                    user_id=user_id,
                    enable_encryption=voice_cache_encryption,
                )
                logger.info(self.locale_loader.get("whisper.voice_cache_enabled", language=self.log_language).format(
                    db=voice_cache_db_path, encrypted=voice_cache_encryption
                ))
            except Exception as e:
                logger.info(self.locale_loader.get("whisper.voice_cache_failed", language=self.log_language).format(error=str(e)))
        elif enable_voice_cache and not HAS_VOICE_CACHE:
            logger.info(self.locale_loader.get("whisper.voice_cache_unavailable", language=self.log_language))

        # Initialize audio logger
        if enable_logging:
            self.logger_instance = AudioLogger(log_dir=log_dir)
        else:
            self.logger_instance = None

        # Initialize modules
        self.recorder = WhisperRecorder(
            sample_rate=sample_rate,
            chunk_duration_ms=chunk_duration_ms,
            silence_threshold=silence_threshold,
            calibration_manager=self.calibration_manager,
            context_buffer=self.context_buffer,
            tts_service=tts_service,  # Neural Gatekeeper for anti-echo
        )


        # NOTE: WhisperRecorder already maintains a persistent stream with background reader thread.
        # No need for separate keep-alive stream (was causing "Microphone stream not available" conflicts).

        self.transcriber = WhisperTranscriber(
            model_size=model_size,
            effective_language=self.effective_language,
            use_faster_whisper=use_faster_whisper,
            lazy_load=lazy_load,
            use_gpu=use_gpu,
            device=device,
            models_dir=models_dir,
            realtime_engine=self.realtime_engine,
        )

        self.post_processor = WhisperPostProcessor(
            enable_corrections=enable_corrections,
            enable_normalization=enable_normalization,
            enable_semantic_correction=enable_semantic_correction,
            enable_natural_reformatter=enable_natural_reformatter,
            correction_dict_path=correction_dict_path,
            semantic_correction_model_path=semantic_correction_model_path,
            natural_reformatter_model_path=natural_reformatter_model_path,
            llm_service=llm_service,  # Pass centralized LLM service
            sample_rate=sample_rate,
            voice_cache=self.voice_cache,
            context_buffer=self.context_buffer,
        )

        # Apply calibration profile
        self._apply_calibration_profile()

    def _apply_calibration_profile(self):
        """Apply calibration profile settings to STT instance"""
        # Apply calibration settings
        if self.calibration_profile:
            self.recorder.silence_threshold = self.calibration_profile.silence_threshold

    async def record_audio_async(
        self,
        max_duration: int = 10,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Record audio from microphone asynchronously"""
        return await self.recorder.record_audio_async(max_duration, on_audio_chunk)

    def record_audio(
        self,
        max_duration: int = 10,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Record audio from microphone"""
        return self.recorder.record_audio(max_duration, on_audio_chunk)

    async def transcribe_async(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe audio file to text asynchronously with enhanced processing"""
        # Transcribe
        transcription_result = await self.transcriber.transcribe_async(audio_path, language)

        if not transcription_result.get("success"):
            # Log error if enabled
            if self.enable_logging and self.logger_instance:
                self.logger_instance.log_transcription(
                    audio_path=audio_path,
                    raw_transcription="",
                    language=language,
                    model=self.model_size,
                    duration_seconds=transcription_result.get("duration", 0),
                    error=transcription_result.get("error"),
                )
            return transcription_result

        # Post-process
        raw_text = transcription_result["raw"]
        effective_language = transcription_result["language"]

        processed = self.post_processor.process(raw_text, effective_language, audio_path)

        # Merge results
        result = {**transcription_result, **processed}

        # Log transcription if enabled
        if self.enable_logging and self.logger_instance:
            self.logger_instance.log_transcription(
                audio_path=audio_path,
                raw_transcription=raw_text,
                corrected_transcription=processed["corrected"],
                normalized_transcription=processed["normalized"],
                language=effective_language,
                model=self.model_size,
                duration_seconds=transcription_result["duration"],
            )

        return result

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio file to text using Whisper with enhanced processing"""
        # Transcribe
        transcription_result = self.transcriber.transcribe(audio_path, language)

        if not transcription_result.get("success"):
            # Log error if enabled
            if self.enable_logging and self.logger_instance:
                self.logger_instance.log_transcription(
                    audio_path=audio_path,
                    raw_transcription="",
                    language=language,
                    model=self.model_size,
                    duration_seconds=transcription_result.get("duration", 0),
                    error=transcription_result.get("error"),
                )
            return transcription_result

        # Post-process
        raw_text = transcription_result["raw"]
        effective_language = transcription_result["language"]

        processed = self.post_processor.process(raw_text, effective_language, audio_path)

        # Merge results
        result = {**transcription_result, **processed}

        # Log transcription if enabled
        if self.enable_logging and self.logger_instance:
            self.logger_instance.log_transcription(
                audio_path=audio_path,
                raw_transcription=raw_text,
                corrected_transcription=processed["corrected"],
                normalized_transcription=processed["normalized"],
                language=effective_language,
                model=self.model_size,
                duration_seconds=transcription_result["duration"],
            )

        return result

    async def listen_and_transcribe_async(
        self,
        max_duration: int = 10,
        language: Optional[str] = None,
        cleanup: bool = True,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Optional[str]:
        """Complete pipeline: record audio and transcribe to text asynchronously"""
        audio_path, error = await self.record_audio_async(
            max_duration, on_audio_chunk=on_audio_chunk
        )

        if error or not audio_path:
            logger.info(f"Recording failed: {error}")
            return None

        result = await self.transcribe_async(audio_path, language)

        # Cleanup temporary file
        if cleanup and audio_path:
            try:
                os.remove(audio_path)
            except Exception as e:
                logger.info(f"Warning: Could not delete temporary file: {e}")

        return result.get("final") if result.get("success") else None

    def listen_and_transcribe(
        self,
        max_duration: int = 10,
        language: Optional[str] = None,
        cleanup: bool = True,
        on_audio_chunk: Optional[Callable[[float, bool], None]] = None,
    ) -> Optional[str]:
        """Complete pipeline: record audio and transcribe to text"""
        audio_path, error = self.record_audio(max_duration, on_audio_chunk=on_audio_chunk)

        if error or not audio_path:
            logger.info(f"Recording failed: {error}")
            return None

        result = self.transcribe(audio_path, language)

        # Cleanup temporary file
        if cleanup and audio_path:
            try:
                os.remove(audio_path)
            except Exception as e:
                logger.info(f"Warning: Could not delete temporary file: {e}")

        return result.get("final") if result.get("success") else None

    def run_calibration(self, language: str = "fr") -> CalibrationProfile:
        """Run interactive calibration for the current user"""
        logger.info("=" * 60)
        logger.info(self.locale_loader.get("whisper.calibration_header", language=language))
        logger.info("=" * 60)

        phrases, instructions = self.calibration_manager.start_calibration(self.user_id, language)

        logger.info(instructions)
        input()  # Wait for user to press Enter

        # Record samples for each phrase
        audio_samples = []

        for i, phrase in enumerate(phrases, 1):
            logger.info(self.locale_loader.get("whisper.calibration_phrase", language=language).format(
                current=i, total=len(phrases), phrase=phrase
            ))
            logger.info(self.locale_loader.get("whisper.calibration_speak_now", language=language))

            audio_path, error = self.record_audio(max_duration=10)

            if audio_path and not error:
                try:
                    with wave.open(audio_path, "rb") as wf:
                        audio_data = wf.readframes(wf.getnframes())
                        energy = self.recorder._calculate_energy(audio_data)
                        audio_samples.append((audio_data, energy))
                        logger.info(self.locale_loader.get("whisper.calibration_recorded", language=language).format(
                            energy=energy
                        ))
                except Exception as e:
                    logger.info(self.locale_loader.get("whisper.calibration_read_error", language=language).format(
                        error=str(e)
                    ))

                # Cleanup
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
            else:
                logger.info(self.locale_loader.get("whisper.calibration_record_failed", language=language).format(
                    error=error
                ))

        # Generate calibration profile
        logger.info(self.locale_loader.get("whisper.calibration_analyzing", language=language))
        profile = self.calibration_manager.calibrate_from_samples(
            self.user_id, audio_samples, language
        )

        # Apply new profile
        self.calibration_profile = profile
        self._apply_calibration_profile()

        # Show report
        report = self.calibration_manager.generate_calibration_report(profile)
        logger.info(report)

        return profile

    def add_custom_correction(self, error: str, correction: str):
        """Add a custom correction to the dictionary"""
        self.post_processor.add_custom_correction(error, correction)

    def get_logger_stats(self) -> Optional[Dict[str, Any]]:
        """Get audio logger statistics"""
        if self.logger_instance:
            return self.logger_instance.get_statistics()
        return None

    def get_recent_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent transcription logs"""
        if self.logger_instance:
            return self.logger_instance.get_recent_logs(count)
        return []

    def export_logs(self, output_file: str, format: str = "json"):
        """Export transcription logs"""
        if self.logger_instance:
            self.logger_instance.export_logs(output_file, format)

    def stop_listening(self):
        """Stop the current listening operation"""
        self.recorder.stop_listening()

    def start_listening(self):
        """Reset the stop listening flag for new listening operation"""
        self.recorder.start_listening()

    def disable_listening(self):
        """Disable listening (alias for stop_listening)"""
        self.stop_listening()

    def enable_listening(self):
        """Enable listening (alias for start_listening)"""
        self.start_listening()

    async def enable_listening_async(self):
        """Async version of enable_listening"""
        self.enable_listening()
        logger.debug("Listening enabled asynchronously")

    async def disable_listening_async(self):
        """Async version of disable_listening"""
        self.disable_listening()
        logger.debug("Listening disabled asynchronously")

    def __del__(self):
        """Cleanup resources"""
        # Recorder will handle PyAudio cleanup
        pass
