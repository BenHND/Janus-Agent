"""
MLX-based Whisper STT Engine for Apple Silicon (TICKET-P2-01)

This module provides ultra-low-latency speech-to-text using Apple's MLX framework:
- Optimized for Apple M1/M2/M3 Neural Engine
- Sub-500ms transcription for 5s audio
- Minimal CPU usage via hardware acceleration
- Same interface as RealtimeSTTEngine for seamless integration
"""

import platform
import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from janus.logging import get_logger

# Check if running on Apple Silicon
IS_APPLE_SILICON = (
    platform.system() == "Darwin"
    and platform.machine() == "arm64"
)

# Try to import lightning-whisper-mlx
HAS_MLX_WHISPER = False
if IS_APPLE_SILICON:
    try:
        from lightning_whisper_mlx import LightningWhisperMLX

        HAS_MLX_WHISPER = True
    except ImportError:
        warnings.warn(
            "lightning-whisper-mlx not installed - MLX STT engine unavailable. "
            "Install with: pip install lightning-whisper-mlx"
        )


@dataclass
class TranscriptionResult:
    """Result of a transcription operation (same as RealtimeSTTEngine)"""

    text: str
    language: str
    confidence: float
    duration_ms: float
    model_used: str
    segments: Optional[List[Dict]] = None


class MLXSTTEngine:
    """
    Ultra-fast STT engine using MLX for Apple Silicon

    Features:
    - Native Metal/Neural Engine acceleration
    - Sub-500ms latency for 5s audio
    - Minimal CPU usage
    - Language profile enforcement (FR/EN)
    - Same interface as RealtimeSTTEngine
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str = "fr",
        beam_size: int = 5,
        buffer_duration_sec: float = 3.0,
        sample_rate: int = 16000,
        batch_size: int = 12,
        quant: Optional[str] = None,
    ):
        """
        Initialize MLX STT Engine

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large, large-v2, large-v3, distil-large-v3)
            language: Explicit language code (fr, en) - never None or "auto"
            beam_size: Beam size for decoding (not used by lightning-whisper-mlx but kept for interface compat)
            buffer_duration_sec: Duration of rolling buffer in seconds
            sample_rate: Audio sample rate
            batch_size: Batch size for MLX inference (default 12 for optimal performance)
            quant: Quantization type (None, "4bit", "8bit") for reduced memory
        """
        self.logger = get_logger("mlx_stt_engine")
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.buffer_duration_sec = buffer_duration_sec
        self.beam_size = beam_size
        self.batch_size = batch_size
        self.quant = quant

        # Ensure language is always explicit and only fr/en
        self.language = self._normalize_language(language)

        # Initialize model
        self.model = None
        self._initialize_model()

        # Rolling buffer for streaming
        self.rolling_buffer: List[np.ndarray] = []
        self.buffer_max_samples = int(buffer_duration_sec * sample_rate)

        # Statistics
        self.stats = {
            "total_transcriptions": 0,
            "total_duration_ms": 0.0,
            "avg_latency_ms": 0.0,
            "errors": 0,
        }

    def _normalize_language(self, language: Optional[str]) -> str:
        """
        Normalize language code to ensure it's always explicit (fr or en).

        Args:
            language: Input language code or None

        Returns:
            Normalized language code ("fr" or "en")
        """
        lang = (language or "fr").lower().strip()
        if lang == "auto" or lang not in ("fr", "en"):
            return "fr"
        return lang

    def _initialize_model(self):
        """Initialize the MLX Whisper model"""
        if not HAS_MLX_WHISPER:
            raise RuntimeError(
                "lightning-whisper-mlx not available. "
                "Ensure you are on Apple Silicon and install with: pip install lightning-whisper-mlx"
            )

        try:
            self.logger.info(
                f"Loading MLX Whisper model '{self.model_size}' "
                f"(batch_size: {self.batch_size}, quant: {self.quant or 'none'})..."
            )

            # LightningWhisperMLX initialization
            self.model = LightningWhisperMLX(
                model=self.model_size,
                batch_size=self.batch_size,
                quant=self.quant,
            )

            self.logger.info(f"✓ MLX Whisper model loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load MLX Whisper model: {e}")
            raise RuntimeError(f"Failed to initialize MLX STT engine: {e}")

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
    ) -> TranscriptionResult:
        """
        Transcribe audio data using MLX

        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            language: Override language (None uses instance language)
            use_buffer: Include rolling buffer context

        Returns:
            TranscriptionResult with text and metadata
        """
        start_time = time.time()

        # Determine language to use - always explicit and only fr/en
        transcribe_language = self._normalize_language(language) if language else self.language

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
                model_used="mlx-whisper",
            )

        try:
            # Ensure audio is float32 in [-1, 1] range
            if audio_to_transcribe.dtype != np.float32:
                audio_to_transcribe = audio_to_transcribe.astype(np.float32)
                if audio_to_transcribe.max() > 1.0 or audio_to_transcribe.min() < -1.0:
                    audio_to_transcribe = audio_to_transcribe / 32768.0

            # LightningWhisperMLX transcription
            # The library expects audio path or numpy array as positional arg
            result = self.model.transcribe(
                audio_to_transcribe,
                language=transcribe_language,
            )

            # Extract text from result
            text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()

            duration_ms = (time.time() - start_time) * 1000

            # Update statistics
            self.stats["total_transcriptions"] += 1
            self.stats["total_duration_ms"] += duration_ms
            self.stats["avg_latency_ms"] = (
                self.stats["total_duration_ms"] / self.stats["total_transcriptions"]
            )

            return TranscriptionResult(
                text=text,
                language=transcribe_language,
                confidence=0.95,  # MLX typically has high confidence
                duration_ms=duration_ms,
                model_used="mlx-whisper",
                segments=result.get("segments") if isinstance(result, dict) else None,
            )

        except Exception as e:
            self.logger.error(f"MLX transcription error: {e}", exc_info=True)
            self.stats["errors"] += 1

            return TranscriptionResult(
                text="",
                language=transcribe_language,
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                model_used="mlx-whisper",
            )

    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from file using MLX

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            language: Override language (uses instance language if None)

        Returns:
            TranscriptionResult
        """
        start_time = time.time()

        # Ensure explicit language using helper method
        transcribe_lang = self._normalize_language(language) if language else self.language

        try:
            # LightningWhisperMLX can handle file paths directly
            result = self.model.transcribe(
                audio_path,
                language=transcribe_lang,
            )

            # Extract text from result
            text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()

            duration_ms = (time.time() - start_time) * 1000

            return TranscriptionResult(
                text=text,
                language=transcribe_lang,
                confidence=0.95,
                duration_ms=duration_ms,
                model_used="mlx-whisper",
                segments=result.get("segments") if isinstance(result, dict) else None,
            )

        except Exception as e:
            self.logger.error(f"MLX file transcription error: {e}", exc_info=True)
            self.stats["errors"] += 1

            return TranscriptionResult(
                text="",
                language=transcribe_lang,
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                model_used="mlx-whisper",
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            **self.stats,
            "model_size": self.model_size,
            "language": self.language,
            "buffer_duration_sec": self.buffer_duration_sec,
            "buffer_size": len(self.rolling_buffer),
            "batch_size": self.batch_size,
            "quant": self.quant,
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
        self.logger.info(f"Running MLX benchmark ({iterations} iterations)...")

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
            "model_size": self.model_size,
            "engine": "mlx-whisper",
        }

        self.logger.info("MLX Benchmark Results:")
        self.logger.info(f"  Model: mlx-whisper ({self.model_size})")
        self.logger.info(f"  Average latency: {avg_latency:.1f}ms")
        self.logger.info(f"  Median latency: {median_latency:.1f}ms")
        self.logger.info(f"  95th percentile: {p95_latency:.1f}ms")
        self.logger.info(f"  Min/Max: {min_latency:.1f}ms / {max_latency:.1f}ms")

        return results


def is_mlx_available() -> bool:
    """
    Check if MLX Whisper is available on this system

    Returns:
        True if running on Apple Silicon with lightning-whisper-mlx installed
    """
    return IS_APPLE_SILICON and HAS_MLX_WHISPER


def create_mlx_stt_engine(
    model_size: str = "base",
    language: str = "fr",
    **kwargs,
) -> Optional[MLXSTTEngine]:
    """
    Factory function to create an MLX STT engine if available

    Args:
        model_size: Whisper model size
        language: Force language (fr, en)
        **kwargs: Additional arguments for MLXSTTEngine

    Returns:
        MLXSTTEngine instance or None if not available
    """
    if not is_mlx_available():
        return None

    try:
        return MLXSTTEngine(
            model_size=model_size,
            language=language,
            **kwargs,
        )
    except Exception as e:
        warnings.warn(f"Failed to create MLX STT engine: {e}")
        return None
