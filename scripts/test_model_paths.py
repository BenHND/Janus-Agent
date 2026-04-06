#!/usr/bin/env python3
"""
Test script to verify that model paths are correctly configured
Tests the new janus/config/model_paths.py module
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_model_paths_configuration():
    """Test that model paths are correctly configured"""
    print("=" * 60)
    print("Testing Model Paths Configuration")
    print("=" * 60)
    print()

    # Test 1: Import model_paths module
    print("Test 1: Importing model_paths module...")
    try:
        from janus.config import model_paths

        print("  ✓ Successfully imported model_paths")
    except Exception as e:
        print(f"  ✗ Failed to import: {e}")
        return False

    # Test 2: Check that directories are defined
    print("\nTest 2: Checking directory definitions...")
    required_paths = [
        "MODELS_ROOT",
        "WHISPER_MODELS_DIR",
        "VISION_MODELS_DIR",
        "TRANSFORMERS_MODELS_DIR",
        "TORCH_CACHE_DIR",
        "HF_CACHE_DIR",
    ]

    for path_name in required_paths:
        if hasattr(model_paths, path_name):
            path_value = getattr(model_paths, path_name)
            print(f"  ✓ {path_name}: {path_value}")
        else:
            print(f"  ✗ {path_name}: not defined")
            return False

    # Test 3: Test setup_model_paths function
    print("\nTest 3: Testing setup_model_paths()...")
    try:
        result = model_paths.setup_model_paths()
        print("  ✓ setup_model_paths() executed successfully")
    except Exception as e:
        print(f"  ✗ setup_model_paths() failed: {e}")
        return False

    # Test 4: Check environment variables
    print("\nTest 4: Checking environment variables...")
    required_env_vars = [
        "TORCH_HOME",
        "TRANSFORMERS_CACHE",
        "HF_HOME",
        "HF_HUB_CACHE",
        "SPECTRA_MODELS_DIR",
        "SPECTRA_VISION_MODELS_DIR",
    ]

    for env_var in required_env_vars:
        if env_var in os.environ:
            print(f"  ✓ {env_var}: {os.environ[env_var]}")
        else:
            print(f"  ✗ {env_var}: not set")
            return False

    # Test 5: Verify directories exist
    print("\nTest 5: Verifying directories exist...")
    directories = result.get("directories", {})
    for dir_name, dir_path in directories.items():
        if dir_path.exists():
            print(f"  ✓ {dir_name}: {dir_path}")
        else:
            print(f"  ✗ {dir_name}: {dir_path} does not exist")
            return False

    # Test 6: Check .gitkeep files
    print("\nTest 6: Checking .gitkeep files...")
    for dir_name, dir_path in directories.items():
        gitkeep = dir_path / ".gitkeep"
        if gitkeep.exists():
            print(f"  ✓ {dir_name}/.gitkeep exists")
        else:
            print(f"  ✗ {dir_name}/.gitkeep missing")
            return False

    # Test 7: Test that paths are within project
    print("\nTest 7: Verifying paths are within project...")
    for dir_name, dir_path in directories.items():
        if dir_name == "models_root":
            continue
        if str(dir_path).startswith(str(project_root)):
            print(f"  ✓ {dir_name} is within project")
        else:
            print(f"  ✗ {dir_name} is outside project: {dir_path}")
            return False

    # Test 8: Test helper functions
    print("\nTest 8: Testing helper functions...")
    try:
        whisper_dir = model_paths.get_whisper_models_dir()
        vision_dir = model_paths.get_vision_models_dir()
        transformers_dir = model_paths.get_transformers_cache_dir()

        print(f"  ✓ get_whisper_models_dir(): {whisper_dir}")
        print(f"  ✓ get_vision_models_dir(): {vision_dir}")
        print(f"  ✓ get_transformers_cache_dir(): {transformers_dir}")
    except Exception as e:
        print(f"  ✗ Helper functions failed: {e}")
        return False

    # Test 9: Test that import janus sets up paths
    print("\nTest 9: Testing automatic setup on import...")
    # Clear environment variables to test fresh import
    env_vars_to_clear = ["TORCH_HOME", "TRANSFORMERS_CACHE", "HF_HOME"]
    saved_vars = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            saved_vars[var] = os.environ[var]
            del os.environ[var]

    # Remove janus from sys.modules to force reimport
    modules_to_remove = [m for m in sys.modules if m.startswith("janus")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Import janus
    import janus

    # Check that env vars are set
    if "TORCH_HOME" in os.environ and "TRANSFORMERS_CACHE" in os.environ:
        print("  ✓ Environment variables set on janus import")
    else:
        print("  ✗ Environment variables not set on janus import")
        return False

    # Restore saved vars
    for var, value in saved_vars.items():
        os.environ[var] = value

    # Summary
    print("\n" + "=" * 60)
    print("✓ All model paths tests passed!")
    print("=" * 60)
    print()
    print("Environment variables configured:")
    print(f"  TORCH_HOME: {os.environ.get('TORCH_HOME', 'NOT SET')}")
    print(f"  TRANSFORMERS_CACHE: {os.environ.get('TRANSFORMERS_CACHE', 'NOT SET')}")
    print(f"  HF_HOME: {os.environ.get('HF_HOME', 'NOT SET')}")
    print(f"  XDG_CACHE_HOME: {os.environ.get('XDG_CACHE_HOME', 'NOT SET')}")
    print()
    print("All AI models will be downloaded to:")
    print(f"  {model_paths.MODELS_ROOT}/")
    print(f"  ├── whisper/       (Standard Whisper models)")
    print(f"  ├── torch/         (PyTorch cache)")
    print(f"  ├── transformers/  (HuggingFace transformers)")
    print(f"  ├── huggingface/   (HuggingFace Hub)")
    print(f"  ├── vision/        (Vision models)")
    print(f"  └── xdg_cache/     (faster-whisper on Linux/Mac)")
    print()

    return True


if __name__ == "__main__":
    success = test_model_paths_configuration()
    exit(0 if success else 1)
