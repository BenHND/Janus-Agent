"""
Configuration module for Janus
Contains centralized configuration for model paths and other settings
"""

from .model_paths import (
    MODELS_ROOT,
    TRANSFORMERS_MODELS_DIR,
    VISION_MODELS_DIR,
    WHISPER_MODELS_DIR,
    setup_model_paths,
)

__all__ = [
    "setup_model_paths",
    "MODELS_ROOT",
    "WHISPER_MODELS_DIR",
    "VISION_MODELS_DIR",
    "TRANSFORMERS_MODELS_DIR",
]
