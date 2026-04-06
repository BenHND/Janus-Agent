"""Speech-to-Text module using Whisper with enhanced features"""

# Import individual components that don't require external dependencies
from .audio_logger import AudioLogger
from .calibration_manager import CalibrationManager, CalibrationProfile
from .context_buffer import ContextBuffer
from .correction_dictionary import CorrectionDictionary
from .text_normalizer import TextNormalizer

# Try to import optional Phase 15 modules
try:
    from .neural_vad import NeuralVAD, create_neural_vad

    HAS_NEURAL_VAD = True
except ImportError:
    HAS_NEURAL_VAD = False

try:
    from .semantic_corrector import SemanticCorrector, SimpleSemanticCorrector

    HAS_SEMANTIC_CORRECTOR = True
except ImportError:
    HAS_SEMANTIC_CORRECTOR = False

# Try to import Phase 16 modules
try:
    from .realtime_stt_engine import (
        RealtimeSTTEngine,
        TranscriptionResult,
        create_realtime_stt_engine,
    )

    HAS_REALTIME_STT = True
except ImportError:
    HAS_REALTIME_STT = False

# TICKET-P2-01: Try to import MLX Whisper engine (Apple Silicon only)
try:
    from .mlx_stt_engine import (
        MLXSTTEngine,
        create_mlx_stt_engine,
        is_mlx_available,
    )

    HAS_MLX_STT = True
except ImportError:
    HAS_MLX_STT = False

    # Provide stub for is_mlx_available when module not importable
    def is_mlx_available() -> bool:
        return False

# TICKET-P2-01: Import STT factory for automatic engine selection
try:
    from .stt_factory import (
        create_stt_engine,
        get_best_stt_engine_type,
        get_stt_engine_info,
    )

    HAS_STT_FACTORY = True
except ImportError:
    HAS_STT_FACTORY = False

try:
    from .natural_reformatter import (
        NaturalReformatter,
        ReformattedResult,
        RuleBasedReformatter,
        create_natural_reformatter,
    )

    HAS_NATURAL_REFORMATTER = True
except ImportError:
    HAS_NATURAL_REFORMATTER = False

try:
    from .voice_adaptation_cache import CacheEntry, VoiceAdaptationCache, create_voice_cache

    HAS_VOICE_CACHE = True
except ImportError:
    HAS_VOICE_CACHE = False

# Try to import WhisperSTT (requires external dependencies)
try:
    from .whisper_stt import WhisperSTT

    __all__ = [
        "WhisperSTT",
        "CorrectionDictionary",
        "TextNormalizer",
        "AudioLogger",
        "CalibrationManager",
        "CalibrationProfile",
        "ContextBuffer",
    ]

    # Add optional Phase 15 exports
    if HAS_NEURAL_VAD:
        __all__.extend(["NeuralVAD", "create_neural_vad"])

    if HAS_SEMANTIC_CORRECTOR:
        __all__.extend(["SemanticCorrector", "SimpleSemanticCorrector"])

    # Add optional Phase 16 exports
    if HAS_REALTIME_STT:
        __all__.extend(["RealtimeSTTEngine", "create_realtime_stt_engine", "TranscriptionResult"])

    if HAS_NATURAL_REFORMATTER:
        __all__.extend(
            [
                "NaturalReformatter",
                "RuleBasedReformatter",
                "create_natural_reformatter",
                "ReformattedResult",
            ]
        )

    if HAS_VOICE_CACHE:
        __all__.extend(["VoiceAdaptationCache", "create_voice_cache", "CacheEntry"])

    # TICKET-P2-01: Add MLX STT exports
    if HAS_MLX_STT:
        __all__.extend(["MLXSTTEngine", "create_mlx_stt_engine", "is_mlx_available"])
    else:
        __all__.append("is_mlx_available")  # Always export availability check

    # TICKET-P2-01: Add STT factory exports
    if HAS_STT_FACTORY:
        __all__.extend(["create_stt_engine", "get_best_stt_engine_type", "get_stt_engine_info"])

except ImportError:
    # If whisper is not installed, only export the standalone components
    __all__ = [
        "CorrectionDictionary",
        "TextNormalizer",
        "AudioLogger",
        "CalibrationManager",
        "CalibrationProfile",
        "ContextBuffer",
    ]

    # Add optional Phase 15 exports
    if HAS_NEURAL_VAD:
        __all__.extend(["NeuralVAD", "create_neural_vad"])

    if HAS_SEMANTIC_CORRECTOR:
        __all__.extend(["SemanticCorrector", "SimpleSemanticCorrector"])

    # Add optional Phase 16 exports
    if HAS_REALTIME_STT:
        __all__.extend(["RealtimeSTTEngine", "create_realtime_stt_engine", "TranscriptionResult"])

    if HAS_NATURAL_REFORMATTER:
        __all__.extend(
            [
                "NaturalReformatter",
                "RuleBasedReformatter",
                "create_natural_reformatter",
                "ReformattedResult",
            ]
        )

    if HAS_VOICE_CACHE:
        __all__.extend(["VoiceAdaptationCache", "create_voice_cache", "CacheEntry"])

    # TICKET-P2-01: Add MLX STT exports (fallback block)
    if HAS_MLX_STT:
        __all__.extend(["MLXSTTEngine", "create_mlx_stt_engine", "is_mlx_available"])
    else:
        __all__.append("is_mlx_available")  # Always export availability check

    # TICKET-P2-01: Add STT factory exports (fallback block)
    if HAS_STT_FACTORY:
        __all__.extend(["create_stt_engine", "get_best_stt_engine_type", "get_stt_engine_info"])
