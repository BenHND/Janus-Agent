"""
Janus - Voice-controlled computer automation agent
"""

__version__ = "1.0.0"
__author__ = "BenHND"

# Initialize model paths before any AI model imports
# This ensures all models are downloaded to ./models instead of ~/.cache
try:
    from .config.model_paths import setup_model_paths

    setup_model_paths()
except Exception:
    # If setup fails, continue - models will use default cache locations
    pass

# Import core components
# Note: Some imports may fail if dependencies are not installed or in headless environments
try:
    from .stt.whisper_stt import WhisperSTT
except (ImportError, Exception):
    WhisperSTT = None

try:
    from .core.janus_agent import JanusAgent
except (ImportError, Exception):
    JanusAgent = None

try:
    from .memory.session_manager import SessionManager
except (ImportError, Exception):
    SessionManager = None

__all__ = [
    "WhisperSTT",
    "JanusAgent",
    # SessionManager is internal - not exposed in public API
]
