"""
Realtime STT Engine with faster-whisper integration (Phase 16.1)

This module provides streaming speech-to-text with:
- faster-whisper (CTranslate2 backend) for low-latency transcription
- Rolling buffer support (2-4 seconds)
- Language profile enforcement (FR/EN)
- Automatic fallback to standard whisper on errors
"""

import tempfile
import time
import warnings
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from janus.logging import get_logger

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel

    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    warnings.warn("faster-whisper not installed - RealtimeSTTEngine will use standard whisper")

# Standard whisper fallback
try:
    import whisper

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False


@dataclass
class TranscriptionResult:
    """Result of a transcription operation"""

    text: str
    language: str
    confidence: float
    duration_ms: float
    model_used: str
    segments: Optional[List[Dict]] = None


class RealtimeSTTEngine:
    """
    High-performance realtime STT engine using faster-whisper

    Features:
    - CTranslate2 backend for 4x faster inference
    - Streaming mode with rolling buffer
    - Language profile enforcement
    - Automatic fallback to standard whisper
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "fr",  # TICKET-1: Default to "fr", never None
        beam_size: int = 5,
        buffer_duration_sec: float = 3.0,
        sample_rate: int = 16000,
        use_faster_whisper: bool = True,
        download_root: Optional[str] = None,
        # VAD parameters (configurable via config.ini)
        enable_vad_filter: bool = False,
        vad_min_silence_duration_ms: int = 500,
        vad_speech_pad_ms: int = 200,
        # TICKET-STT-002: Speaker verification parameters
        enable_speaker_verification: bool = False,
        speaker_embedding_path: Optional[str] = None,
        speaker_similarity_threshold: float = 0.75,
    ):
        """
        Initialize Realtime STT Engine
        TICKET-1: Language is always explicit, never None or "auto"

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to use (cpu, cuda)
            compute_type: Compute type for CTranslate2 (int8, float16, float32)
            language: Explicit language code (fr, en) - TICKET-1: Never None or "auto"
            beam_size: Beam size for decoding
            buffer_duration_sec: Duration of rolling buffer in seconds
            sample_rate: Audio sample rate
            use_faster_whisper: Use faster-whisper if available, fallback to standard
            download_root: Directory for model storage (uses env var if not provided)
            enable_vad_filter: Enable VAD filtering in faster-whisper
            vad_min_silence_duration_ms: Minimum silence duration to split segments
            vad_speech_pad_ms: Padding around speech segments
            enable_speaker_verification: Enable speaker verification (TICKET-STT-002)
            speaker_embedding_path: Path to user voice embedding file
            speaker_similarity_threshold: Minimum similarity threshold for speaker verification
        """
        self.logger = get_logger("realtime_stt_engine")
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        # TICKET-1: Ensure language is always explicit and only fr/en
        lang = (language or "fr").lower().strip()
        if lang == "auto" or lang not in ("fr", "en"):
            lang = "fr"
        self.language = lang
        self.beam_size = beam_size
        self.buffer_duration_sec = buffer_duration_sec
        self.sample_rate = sample_rate
        self.use_faster_whisper = use_faster_whisper
        self.download_root = download_root
        
        # Store VAD parameters from config
        self.enable_vad_filter = enable_vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.vad_speech_pad_ms = vad_speech_pad_ms
        
        # TICKET-STT-002: Speaker verification setup
        self.enable_speaker_verification = enable_speaker_verification
        self.speaker_verifier = None
        if enable_speaker_verification:
            try:
                from janus.io.stt.speaker_verifier import SpeakerVerifier
                self.speaker_verifier = SpeakerVerifier(
                    embedding_path=speaker_embedding_path,
                    similarity_threshold=speaker_similarity_threshold,
                    sample_rate=sample_rate,
                )
                if self.speaker_verifier.is_available():
                    self.logger.info("Speaker verification enabled")
                else:
                    self.logger.warning("Speaker verification requested but not available")
            except Exception as e:
                self.logger.error(f"Failed to initialize speaker verification: {e}")
                self.speaker_verifier = None

        # Initialize model
        self.model = None
        self.model_type = None  # 'faster' or 'standard'
        self._initialize_model()

        # Rolling buffer for streaming
        self.rolling_buffer: List[np.ndarray] = []
        self.buffer_max_samples = int(buffer_duration_sec * sample_rate)

        # Statistics
        self.stats = {
            "total_transcriptions": 0,
            "total_duration_ms": 0.0,
            "avg_latency_ms": 0.0,
            "faster_whisper_count": 0,
            "standard_whisper_count": 0,
            "errors": 0,
            "voice_rejections": 0,  # TICKET-STT-002: Track rejected voices
        }

    def _initialize_model(self):
        """Initialize the appropriate whisper model"""
        # Try faster-whisper first if requested
        if self.use_faster_whisper and HAS_FASTER_WHISPER:
            try:
                self.logger.info(
                    f"Loading faster-whisper model '{self.model_size}' (device: {self.device}, compute: {self.compute_type})..."
                )

                # Try to pass download_root if supported by faster-whisper
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                        download_root=self.download_root,
                    )
                except TypeError:
                    # download_root not supported, use default cache (respects XDG_CACHE_HOME)
                    self.model = WhisperModel(
                        self.model_size, device=self.device, compute_type=self.compute_type
                    )

                self.model_type = "faster"
                self.logger.info(f" faster-whisper model loaded successfully")
                return
            except Exception as e:
                self.logger.error(f"Failed to load faster-whisper: {e}")
                self.logger.info("Falling back to standard whisper...")

        # Fallback to standard whisper
        if HAS_WHISPER:
            try:
                self.logger.info(f"Loading standard whisper model '{self.model_size}'...")
                self.model = whisper.load_model(
                    self.model_size,
                    download_root=self.download_root if self.download_root else None,
                )
                self.model_type = "standard"
                self.logger.info(f" Standard whisper model loaded successfully")
            except Exception as e:
                raise RuntimeError(f"Failed to load whisper model: {e}")
        else:
            raise RuntimeError(
                "No whisper implementation available (install whisper or faster-whisper)"
            )

    def add_to_buffer(self, audio_data: np.ndarray):
        """
        Add audio data to rolling buffer

        Args:
            audio_data: Audio samples as numpy array
        """
        self.rolling_buffer.append(audio_data)

        # Calculate total samples in buffer
        total_samples = sum(len(chunk) for chunk in self.rolling_buffer)

        # Remove old chunks if buffer exceeds max size
        while total_samples > self.buffer_max_samples and len(self.rolling_buffer) > 1:
            removed = self.rolling_buffer.pop(0)
            total_samples -= len(removed)

    def get_buffer_audio(self) -> Optional[np.ndarray]:
        """
        Get concatenated audio from rolling buffer

        Returns:
            Concatenated audio array or None if buffer is empty
        """
        if not self.rolling_buffer:
            return None
        return np.concatenate(self.rolling_buffer)

    def clear_buffer(self):
        """Clear the rolling buffer"""
        self.rolling_buffer.clear()

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: Optional[str] = None,
        use_buffer: bool = True,
        temperature: float = 0.0,
    ) -> TranscriptionResult:
        """
        Transcribe audio data
        TICKET-1: Language is always explicit, never None or "auto"

        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            language: Override language (None uses instance language)
            use_buffer: Include rolling buffer context
            temperature: Sampling temperature (0 = greedy, higher = more random)

        Returns:
            TranscriptionResult with text and metadata
        """
        start_time = time.time()

        # TICKET-1: Determine language to use - always explicit and only fr/en
        lang = (language or self.language).lower().strip()
        if lang == "auto" or lang not in ("fr", "en"):
            lang = self.language
        transcribe_language = lang

        # Add current audio to buffer if enabled
        if use_buffer:
            self.add_to_buffer(audio_data)
            audio_to_transcribe = self.get_buffer_audio()
        else:
            audio_to_transcribe = audio_data

        if audio_to_transcribe is None:
            return TranscriptionResult(
                text="",
                language=transcribe_language,
                confidence=0.0,
                duration_ms=0.0,
                model_used=self.model_type or "none",
            )
        
        # TICKET-STT-002: Speaker verification before transcription
        if self.enable_speaker_verification and self.speaker_verifier:
            is_verified, similarity = self.speaker_verifier.verify_speaker(audio_to_transcribe)
            if not is_verified:
                self.logger.warning(f"Voice mismatch - ignoring audio segment (similarity: {similarity:.3f})")
                self.stats["voice_rejections"] += 1
                return TranscriptionResult(
                    text="",
                    language=transcribe_language,
                    confidence=0.0,
                    duration_ms=(time.time() - start_time) * 1000,
                    model_used=self.model_type or "none",
                )

        try:
            # Transcribe based on model type
            if self.model_type == "faster":
                result = self._transcribe_faster_whisper(
                    audio_to_transcribe, transcribe_language, temperature
                )
            else:
                result = self._transcribe_standard_whisper(
                    audio_to_transcribe, transcribe_language, temperature
                )

            # Update statistics
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            self.stats["total_transcriptions"] += 1
            self.stats["total_duration_ms"] += duration_ms
            self.stats["avg_latency_ms"] = (
                self.stats["total_duration_ms"] / self.stats["total_transcriptions"]
            )

            if self.model_type == "faster":
                self.stats["faster_whisper_count"] += 1
            else:
                self.stats["standard_whisper_count"] += 1

            return result

        except Exception as e:
            self.logger.error(f"Transcription error: {e}", exc_info=True)
            self.stats["errors"] += 1

            # Try fallback if faster-whisper failed
            if self.model_type == "faster" and HAS_WHISPER:
                self.logger.info("Attempting fallback to standard whisper...")
                try:
                    # Reinitialize with standard whisper
                    old_use_faster = self.use_faster_whisper
                    self.use_faster_whisper = False
                    self._initialize_model()

                    result = self._transcribe_standard_whisper(
                        audio_to_transcribe, transcribe_language, temperature
                    )

                    duration_ms = (time.time() - start_time) * 1000
                    result.duration_ms = duration_ms

                    # Restore flag but keep standard model
                    self.use_faster_whisper = old_use_faster

                    return result
                except Exception as e2:
                    self.logger.error(f"Fallback also failed: {e2}", exc_info=True)

            # Return empty result on complete failure
            return TranscriptionResult(
                text="",
                language=transcribe_language or "unknown",
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                model_used=self.model_type or "none",
            )

    def _transcribe_faster_whisper(
        self,
        audio_data: np.ndarray,
        language: str,  # TICKET-1: Always explicit, not Optional
        temperature: float,
    ) -> TranscriptionResult:
        """
        Transcribe using faster-whisper
        TICKET-1: Language is always explicit, never None or "auto"
        """
        # Use VAD parameters from config
        transcribe_kwargs = {
            "language": language,
            "beam_size": self.beam_size,
            "temperature": temperature,
            "vad_filter": self.enable_vad_filter,
        }
        
        # Only add vad_parameters if VAD is enabled
        if self.enable_vad_filter:
            transcribe_kwargs["vad_parameters"] = {
                "min_silence_duration_ms": self.vad_min_silence_duration_ms,
                "speech_pad_ms": self.vad_speech_pad_ms,
            }
        
        segments, info = self.model.transcribe(audio_data, **transcribe_kwargs)

        # Collect segments
        segment_list = []
        full_text = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            segment_list.append(segment_dict)
            full_text.append(segment.text.strip())

            # Average word-level confidence if available
            if hasattr(segment, "words") and segment.words:
                word_confidences = [
                    w.probability for w in segment.words if hasattr(w, "probability")
                ]
                if word_confidences:
                    total_confidence += sum(word_confidences) / len(word_confidences)
                    segment_count += 1
            else:
                # Use no_speech_prob as inverse confidence estimate
                if hasattr(segment, "no_speech_prob"):
                    total_confidence += 1.0 - segment.no_speech_prob
                    segment_count += 1

        # Calculate average confidence
        avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.5

        return TranscriptionResult(
            text=" ".join(full_text),
            language=info.language if hasattr(info, "language") else language,
            confidence=avg_confidence,
            duration_ms=0.0,  # Will be set by caller
            model_used="faster-whisper",
            segments=segment_list if segment_list else None,
        )

    def _transcribe_standard_whisper(
        self,
        audio_data: np.ndarray,
        language: str,  # TICKET-1: Always explicit, not Optional
        temperature: float,
    ) -> TranscriptionResult:
        """
        Transcribe using standard whisper
        TICKET-1: Language is always explicit, never None or "auto"
        """
        # Standard whisper expects float32 in [-1, 1]
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32) / 32768.0

        result = self.model.transcribe(
            audio_data,
            language=language,  # TICKET-1: Always explicit
            temperature=temperature,
            fp16=False,  # Use FP32 on CPU
        )

        # Extract segments if available
        segments = None
        if "segments" in result and result["segments"]:
            segments = [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result["segments"]
            ]

        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", language),
            confidence=0.8,  # Standard whisper doesn't provide confidence
            duration_ms=0.0,  # Will be set by caller
            model_used="standard-whisper",
            segments=segments,
        )

    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from file
        TICKET-1: Language is always explicit, never None or "auto"

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            language: Override language (uses instance language if None)

        Returns:
            TranscriptionResult
        """
        # TICKET-1: Ensure explicit language
        transcribe_lang = language if language and language != "auto" else self.language

        # Load audio file
        if self.model_type == "faster":
            # faster-whisper can handle files directly
            return self._transcribe_file_faster_whisper(audio_path, transcribe_lang)
        else:
            # Standard whisper needs numpy array
            audio_data = whisper.load_audio(audio_path)
            audio_data = whisper.pad_or_trim(audio_data)
            return self.transcribe(audio_data, language=transcribe_lang, use_buffer=False)

    def _transcribe_file_faster_whisper(
        self,
        audio_path: str,
        language: str,  # TICKET-1: Always explicit, not Optional
    ) -> TranscriptionResult:
        """
        Transcribe file using faster-whisper (optimized path)
        TICKET-1: Language is always explicit, never None or "auto"
        """
        start_time = time.time()

        try:
            # Use same VAD parameters as regular transcription
            transcribe_kwargs = {
                "language": language,
                "beam_size": self.beam_size,
                "vad_filter": self.enable_vad_filter,
            }
            
            # Only add vad_parameters if VAD is enabled
            if self.enable_vad_filter:
                transcribe_kwargs["vad_parameters"] = {
                    "min_silence_duration_ms": self.vad_min_silence_duration_ms,
                    "speech_pad_ms": self.vad_speech_pad_ms,
                }
            
            segments, info = self.model.transcribe(audio_path, **transcribe_kwargs)

            # Collect results
            segment_list = []
            full_text = []

            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                segment_list.append(segment_dict)
                full_text.append(segment.text.strip())

            duration_ms = (time.time() - start_time) * 1000

            return TranscriptionResult(
                text=" ".join(full_text),
                language=info.language if hasattr(info, "language") else language,
                confidence=0.9,
                duration_ms=duration_ms,
                model_used="faster-whisper",
                segments=segment_list if segment_list else None,
            )

        except Exception as e:
            self.logger.error(f"File transcription error: {e}", exc_info=True)
            self.stats["errors"] += 1

            return TranscriptionResult(
                text="",
                language=language,
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                model_used="faster-whisper",
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            **self.stats,
            "model_type": self.model_type,
            "model_size": self.model_size,
            "language": self.language,
            "buffer_duration_sec": self.buffer_duration_sec,
            "buffer_size": len(self.rolling_buffer),
        }

    def benchmark(self, audio_data: np.ndarray, iterations: int = 10) -> Dict[str, float]:
        """
        Benchmark transcription performance

        Args:
            audio_data: Test audio samples
            iterations: Number of iterations

        Returns:
            Benchmark results with timing statistics
        """
        self.logger.info(f"Running benchmark ({iterations} iterations)...")

        latencies = []

        for i in range(iterations):
            result = self.transcribe(audio_data, use_buffer=False)
            latencies.append(result.duration_ms)
            self.logger.debug(f"  Iteration {i+1}/{iterations}: {result.duration_ms:.1f}ms")

        # Calculate statistics
        latencies = sorted(latencies)
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        median_latency = latencies[len(latencies) // 2]
        p95_latency = latencies[int(len(latencies) * 0.95)]

        results = {
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "median_latency_ms": median_latency,
            "p95_latency_ms": p95_latency,
            "model_type": self.model_type,
            "model_size": self.model_size,
        }

        self.logger.info("Benchmark Results:")
        self.logger.info(f"  Model: {self.model_type} ({self.model_size})")
        self.logger.info(f"  Average latency: {avg_latency:.1f}ms")
        self.logger.info(f"  Median latency: {median_latency:.1f}ms")
        self.logger.info(f"  95th percentile: {p95_latency:.1f}ms")
        self.logger.info(f"  Min/Max: {min_latency:.1f}ms / {max_latency:.1f}ms")

        return results


def create_realtime_stt_engine(
    model_size: str = "base",
    language: Optional[str] = None,
    use_faster_whisper: bool = True,
    **kwargs,
) -> RealtimeSTTEngine:
    """
    Factory function to create a RealtimeSTTEngine instance

    Args:
        model_size: Whisper model size
        language: Force language (fr, en) or None
        use_faster_whisper: Try faster-whisper first
        **kwargs: Additional arguments for RealtimeSTTEngine

    Returns:
        Configured RealtimeSTTEngine instance
    """
    return RealtimeSTTEngine(
        model_size=model_size, language=language, use_faster_whisper=use_faster_whisper, **kwargs
    )
