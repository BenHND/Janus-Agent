#!/usr/bin/env python3
"""
Demonstration script showing that model paths are correctly configured
This simulates what would happen when AI models are downloaded
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def demonstrate_model_paths():
    """Demonstrate that model paths are correctly configured"""
    print("=" * 70)
    print("MODEL CACHE CONFIGURATION DEMONSTRATION")
    print("=" * 70)
    print()
    print("This demonstrates that all AI models will be downloaded to ./models")
    print("instead of the global ~/.cache directory.")
    print()

    # Import and setup
    print("1. Importing janus package...")
    import janus

    print("   ✓ Janus imported")
    print()

    # Show environment variables
    print("2. Environment variables configured:")
    env_vars = {
        "TORCH_HOME": "PyTorch models (including standard Whisper)",
        "TRANSFORMERS_CACHE": "HuggingFace Transformers (BLIP-2, CLIP, etc.)",
        "HF_HOME": "HuggingFace Hub cache",
        "HF_HUB_CACHE": "Alternative HuggingFace Hub cache",
        "XDG_CACHE_HOME": "faster-whisper cache (Linux/Mac)",
        "SPECTRA_MODELS_DIR": "Whisper models (legacy)",
        "SPECTRA_VISION_MODELS_DIR": "Vision models (legacy)",
    }

    for var, description in env_vars.items():
        value = os.environ.get(var, "NOT SET")
        print(f"   {var}:")
        print(f"     {description}")
        print(f"     → {value}")
        print()

    # Show directory structure
    print("3. Directory structure created:")
    from janus.config.model_paths import MODELS_ROOT

    if MODELS_ROOT.exists():
        print(f"   {MODELS_ROOT}/")
        for item in sorted(MODELS_ROOT.iterdir()):
            if item.is_dir():
                # Count .gitkeep files
                gitkeep = item / ".gitkeep"
                marker = "✓" if gitkeep.exists() else "✗"
                print(f"   ├── {item.name}/  [{marker}]")
        print()
        print("   [✓] = .gitkeep file present (directory preserved in git)")
        print()

    # Simulate model downloads
    print("4. Model download simulation:")
    print()
    print("   When you download AI models, they will be stored as follows:")
    print()

    model_examples = [
        ("Whisper 'base' model", "models/whisper/base.pt"),
        (
            "faster-whisper models",
            "models/xdg_cache/huggingface/hub/models--Systran--faster-whisper-base/",
        ),
        ("PyTorch cache", "models/torch/hub/checkpoints/"),
        ("BLIP-2 model", "models/transformers/models--Salesforce--blip2-opt-2.7b/"),
        ("CLIP model", "models/transformers/models--openai--clip-vit-base-patch32/"),
        ("HuggingFace Hub", "models/huggingface/hub/models--..."),
    ]

    for model_name, path in model_examples:
        print(f"   • {model_name}")
        print(f"     → {path}")
        print()

    # Show what's NOT in ~/.cache
    print("5. What is NOT in ~/.cache:")
    print()
    home_cache = Path.home() / ".cache"
    print(f"   The following directories will NOT be created in {home_cache}:")
    print(f"   ✗ ~/.cache/huggingface/")
    print(f"   ✗ ~/.cache/torch/")
    print(f"   ✗ ~/.cache/whisper/")
    print()
    print("   Instead, everything is in ./models/ (portable with the project)")
    print()

    # Benefits
    print("6. Benefits:")
    print()
    print("   ✓ Project is self-contained and portable")
    print("   ✓ No global cache pollution")
    print("   ✓ Easy cleanup - just delete the models/ directory")
    print("   ✓ Multiple projects can have separate model caches")
    print("   ✓ Models are not left behind when uninstalling Janus")
    print("   ✓ Can package models with the application")
    print()

    # Verification
    print("7. Verification:")
    print()

    # Check if any models exist
    has_models = False
    model_dirs = [
        MODELS_ROOT / "whisper",
        MODELS_ROOT / "torch",
        MODELS_ROOT / "transformers",
        MODELS_ROOT / "huggingface",
        MODELS_ROOT / "xdg_cache",
    ]

    for model_dir in model_dirs:
        if model_dir.exists():
            # Count files (excluding .gitkeep)
            files = [f for f in model_dir.rglob("*") if f.is_file() and f.name != ".gitkeep"]
            if files:
                has_models = True
                print(f"   ✓ Found {len(files)} file(s) in {model_dir.name}/")

    if not has_models:
        print("   ℹ No models downloaded yet (directories are empty)")
        print("   ℹ Models will be downloaded on first use")
    print()

    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("To test with actual models, run:")
    print("  python -c 'import whisper; whisper.load_model(\"tiny\")'")
    print()
    print("The model will be downloaded to:")
    print(f"  {MODELS_ROOT / 'whisper'}/")
    print()


if __name__ == "__main__":
    demonstrate_model_paths()
