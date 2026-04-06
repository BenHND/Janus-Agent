"""
Centralized Model Paths Configuration for Janus

This module defines and manages all AI model storage paths, ensuring that:
1. All models are stored in ./models directory instead of ~/.cache
2. Environment variables are set at application startup
3. Models are portable with the project
4. Cache directories are properly initialized

Usage:
    from janus.config.model_paths import setup_model_paths
    setup_model_paths()  # Call at application startup

TICKET: P1 Hybrid LLM Optimization
Defines model constants for bi-cephalic architecture:
- REASONER_MODEL: Complex reasoning (Qwen 2.5 7B Q3_K_M, ~3.8 GB)
- REFLEX_MODEL: Fast tasks (Qwen 2.5 1.5B, ~1.2 GB)
"""

import os
from pathlib import Path
from typing import Optional

# ============================================================================
# TICKET: P1 Hybrid LLM Optimization - Model Configuration
# ============================================================================

# Reasoner Model (Brain) - Qwen 2.5 7B quantized Q3_K_M
# Usage: Planning, Complex Tool Use, Code, Deep Visual Analysis
# RAM: ~3.8 GB (vs 6 GB for Q4 variant)
# Installation: ollama pull qwen2.5:7b-instruct-q3_k_m
REASONER_MODEL = "qwen2.5:7b-instruct-q3_k_m"

# Reflex Model (Fast) - Qwen 2.5 1.5B
# Usage: Simple Summary, Date Extraction, Small talk Chat, Routing
# RAM: ~1.2 GB
# Installation: ollama pull qwen2.5:1.5b
REFLEX_MODEL = "qwen2.5:1.5b"

# Total estimated VRAM with both models loaded: ~5 GB
# Models can be loaded dynamically or kept in memory based on usage patterns

# Get project root directory (where main.py is located)
# This file is at janus/config/model_paths.py, so go up 2 levels
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Root models directory
MODELS_ROOT = PROJECT_ROOT / "models"

# Subdirectories for different model types
WHISPER_MODELS_DIR = MODELS_ROOT / "whisper"
VISION_MODELS_DIR = MODELS_ROOT / "vision"
TRANSFORMERS_MODELS_DIR = MODELS_ROOT / "transformers"

# Additional cache directories
TORCH_CACHE_DIR = MODELS_ROOT / "torch"
HF_CACHE_DIR = MODELS_ROOT / "huggingface"


def setup_model_paths(custom_root: Optional[Path] = None) -> dict:
    """
    Initialize model directories and set environment variables.

    This function should be called at application startup (in main.py or __init__.py)
    to ensure all AI models are downloaded to the local ./models directory instead
    of the global ~/.cache directory.

    Args:
        custom_root: Optional custom root directory for models (overrides MODELS_ROOT)

    Returns:
        Dictionary with all configured paths

    Environment Variables Set:
        - TORCH_HOME: For PyTorch model cache
        - TRANSFORMERS_CACHE: For HuggingFace transformers cache
        - HF_HOME: For HuggingFace Hub cache
        - HF_HUB_CACHE: For HuggingFace Hub cache (alternative)
        - SPECTRA_MODELS_DIR: For Whisper models (legacy compatibility)
        - SPECTRA_VISION_MODELS_DIR: For vision models (legacy compatibility)
    """
    # Use custom root if provided
    models_root = Path(custom_root) if custom_root else MODELS_ROOT

    # Ensure all directories exist
    directories = {
        "models_root": models_root,
        "whisper": models_root / "whisper",
        "vision": models_root / "vision",
        "transformers": models_root / "transformers",
        "torch": models_root / "torch",
        "huggingface": models_root / "huggingface",
    }

    for dir_name, dir_path in directories.items():
        dir_path.mkdir(parents=True, exist_ok=True)
        # Create .gitkeep to preserve directory structure
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # Set environment variables for model caching
    # These must be set BEFORE importing torch, transformers, or whisper

    # PyTorch cache (for whisper and torch models)
    os.environ["TORCH_HOME"] = str(directories["torch"])

    # HuggingFace Transformers cache (for BLIP-2, CLIP, etc.)
    os.environ["TRANSFORMERS_CACHE"] = str(directories["transformers"])
    os.environ["HF_HOME"] = str(directories["huggingface"])
    os.environ["HF_HUB_CACHE"] = str(directories["huggingface"])

    # Janus-specific environment variables (for backward compatibility)
    os.environ["SPECTRA_MODELS_DIR"] = str(directories["whisper"])
    os.environ["SPECTRA_VISION_MODELS_DIR"] = str(directories["vision"])

    # Note: faster-whisper downloads models to a cache directory that respects
    # XDG_CACHE_HOME on Linux or LOCALAPPDATA on Windows. We'll set those too.
    if os.name == "posix":  # Linux/Mac
        os.environ["XDG_CACHE_HOME"] = str(models_root / "xdg_cache")
        xdg_path = Path(os.environ["XDG_CACHE_HOME"])
        xdg_path.mkdir(parents=True, exist_ok=True)
        (xdg_path / ".gitkeep").touch(exist_ok=True)

    return {
        "TORCH_HOME": os.environ["TORCH_HOME"],
        "TRANSFORMERS_CACHE": os.environ["TRANSFORMERS_CACHE"],
        "HF_HOME": os.environ["HF_HOME"],
        "HF_HUB_CACHE": os.environ["HF_HUB_CACHE"],
        "SPECTRA_MODELS_DIR": os.environ["SPECTRA_MODELS_DIR"],
        "SPECTRA_VISION_MODELS_DIR": os.environ["SPECTRA_VISION_MODELS_DIR"],
        "directories": directories,
    }


def get_whisper_models_dir() -> Path:
    """Get the Whisper models directory."""
    return Path(os.environ.get("SPECTRA_MODELS_DIR", WHISPER_MODELS_DIR))


def get_vision_models_dir() -> Path:
    """Get the Vision models directory."""
    return Path(os.environ.get("SPECTRA_VISION_MODELS_DIR", VISION_MODELS_DIR))


def get_transformers_cache_dir() -> Path:
    """Get the Transformers cache directory."""
    return Path(os.environ.get("TRANSFORMERS_CACHE", TRANSFORMERS_MODELS_DIR))


if __name__ == "__main__":
    # For testing: show what directories would be created and what env vars would be set
    print("Model Paths Configuration")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Models Root: {MODELS_ROOT}")
    print()
    print("Directories:")
    print(f"  - Whisper: {WHISPER_MODELS_DIR}")
    print(f"  - Vision: {VISION_MODELS_DIR}")
    print(f"  - Transformers: {TRANSFORMERS_MODELS_DIR}")
    print(f"  - Torch: {TORCH_CACHE_DIR}")
    print(f"  - HuggingFace: {HF_CACHE_DIR}")
    print()
    print("Setting up paths...")
    result = setup_model_paths()
    print()
    print("Environment Variables Set:")
    for key, value in result.items():
        if key != "directories":
            print(f"  {key}: {value}")
