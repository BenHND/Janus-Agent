"""
STT Engine Factory - Automatic selection based on hardware (TICKET-P2-01)

This module provides automatic selection of the best STT engine:
- MLX Whisper on Apple Silicon (M1/M2/M3/M4) - instant STT < 500ms
- faster-whisper on CUDA/CPU - 4x faster than standard whisper
- Standard whisper as fallback
"""

import platform
from typing import Any, Dict, Optional, Union

from janus.logging import get_logger

logger = get_logger("stt_factory")


def get_best_stt_engine_type() -> str:
    """
    Detect the best available STT engine based on hardware.

    Returns:
        Engine type: "mlx", "faster-whisper", or "whisper"
    """
    # Check for Apple Silicon + MLX
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            from lightning_whisper_mlx import LightningWhisperMLX

            logger.info("✓ Apple Silicon detected with MLX support - using MLX Whisper")
            return "mlx"
        except ImportError:
            logger.debug("MLX not available on Apple Silicon - checking faster-whisper")

    # Check for faster-whisper
    try:
        from faster_whisper import WhisperModel

        logger.info("✓ Using faster-whisper engine")
        return "faster-whisper"
    except ImportError:
        pass

    # Fallback to standard whisper
    logger.info("Using standard whisper engine (fallback)")
    return "whisper"


def create_stt_engine(
    model_size: str = "base",
    language: str = "fr",
    use_mlx: Optional[bool] = None,
    use_faster_whisper: bool = True,
    **kwargs,
) -> Any:
    """
    Factory function to create the best available STT engine.

    Automatically selects:
    - MLXSTTEngine on Apple Silicon (if use_mlx is True or None on Apple Silicon)
    - RealtimeSTTEngine with faster-whisper on CUDA/CPU
    - Falls back to standard whisper if nothing else available

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large, etc.)
        language: Language code ("fr", "en")
        use_mlx: Force MLX usage (True), disable (False), or auto-detect (None)
        use_faster_whisper: Use faster-whisper if MLX not available
        **kwargs: Additional arguments passed to the engine

    Returns:
        STT engine instance (MLXSTTEngine, RealtimeSTTEngine, or None)

    Raises:
        RuntimeError: If no STT engine is available
    """
    engine_type = get_best_stt_engine_type()

    # Handle MLX
    if engine_type == "mlx" and use_mlx is not False:
        try:
            from .mlx_stt_engine import MLXSTTEngine

            # Extract MLX-specific kwargs
            batch_size = kwargs.pop("batch_size", kwargs.pop("mlx_batch_size", 12))
            quant = kwargs.pop("quant", kwargs.pop("mlx_quant", None))

            engine = MLXSTTEngine(
                model_size=model_size,
                language=language,
                batch_size=batch_size,
                quant=quant if quant else None,
                **kwargs,
            )
            logger.info(f"✓ Created MLXSTTEngine (model: {model_size}, lang: {language})")
            return engine
        except Exception as e:
            logger.warning(f"Failed to create MLX engine: {e}")
            # Fall through to faster-whisper

    # Handle faster-whisper
    if (engine_type == "faster-whisper" or use_mlx is False) and use_faster_whisper:
        try:
            from .realtime_stt_engine import RealtimeSTTEngine
            from janus.utils.gpu_utils import get_optimal_compute_type, get_optimal_device

            device = kwargs.pop("device", get_optimal_device())
            compute_type = kwargs.pop("compute_type", get_optimal_compute_type(device))

            # faster-whisper doesn't support MPS, force CPU
            if device == "mps":
                logger.info("faster-whisper doesn't support MPS, using CPU")
                device = "cpu"
                compute_type = "float32"

            engine = RealtimeSTTEngine(
                model_size=model_size,
                device=device,
                compute_type=compute_type,
                language=language,
                use_faster_whisper=True,
                **kwargs,
            )
            logger.info(
                f"✓ Created RealtimeSTTEngine with faster-whisper "
                f"(model: {model_size}, device: {device}, lang: {language})"
            )
            return engine
        except Exception as e:
            logger.warning(f"Failed to create faster-whisper engine: {e}")
            # Fall through to standard whisper

    # Standard whisper fallback
    try:
        from .realtime_stt_engine import RealtimeSTTEngine

        engine = RealtimeSTTEngine(
            model_size=model_size,
            language=language,
            use_faster_whisper=False,
            **kwargs,
        )
        logger.info(
            f"✓ Created RealtimeSTTEngine with standard whisper "
            f"(model: {model_size}, lang: {language})"
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create any STT engine: {e}")
        raise RuntimeError(
            "No STT engine available. Install whisper, faster-whisper, "
            "or lightning-whisper-mlx (on Apple Silicon)"
        )


def get_stt_engine_info() -> Dict[str, Any]:
    """
    Get information about available STT engines.

    Returns:
        Dictionary with engine availability and recommendations
    """
    info = {
        "platform": platform.system(),
        "machine": platform.machine(),
        "is_apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
        "engines": {
            "mlx": False,
            "faster_whisper": False,
            "whisper": False,
        },
        "recommended_engine": None,
    }

    # Check MLX
    if info["is_apple_silicon"]:
        try:
            from lightning_whisper_mlx import LightningWhisperMLX

            info["engines"]["mlx"] = True
        except ImportError:
            pass

    # Check faster-whisper
    try:
        from faster_whisper import WhisperModel

        info["engines"]["faster_whisper"] = True
    except ImportError:
        pass

    # Check whisper
    try:
        import whisper

        info["engines"]["whisper"] = True
    except ImportError:
        pass

    # Determine recommendation
    if info["engines"]["mlx"]:
        info["recommended_engine"] = "mlx"
        info["recommendation_reason"] = "Apple Silicon with MLX - instant STT (< 500ms for 5s audio)"
    elif info["engines"]["faster_whisper"]:
        info["recommended_engine"] = "faster-whisper"
        info["recommendation_reason"] = "faster-whisper with CTranslate2 - 4x faster than standard"
    elif info["engines"]["whisper"]:
        info["recommended_engine"] = "whisper"
        info["recommendation_reason"] = "Standard OpenAI Whisper - baseline implementation"
    else:
        info["recommended_engine"] = None
        info["recommendation_reason"] = "No STT engine available - install whisper or faster-whisper"

    return info
