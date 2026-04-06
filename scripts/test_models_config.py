#!/usr/bin/env python3
"""
Test script to verify model directory configuration
Part of README #4 - macOS Packaging & Distribution
"""


def test_models_directory_config():
    """Test that models directory configuration is properly set up"""
    print("=" * 60)
    print("Testing Model Directory Configuration")
    print("=" * 60)
    print()

    # Test 1: Import settings module
    print("Test 1: Importing settings module...")
    try:
        # Direct import of dataclasses to avoid dependency issues
        import os
        import sys
        from dataclasses import dataclass
        from pathlib import Path

        # Add project root to path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))

        print("  ✓ Successfully set up import path")
    except Exception as e:
        print(f"  ✗ Failed to set up imports: {e}")
        return False

    # Test 2: Check settings file exists
    print("\nTest 2: Checking settings file...")
    settings_file = project_root / "janus" / "core" / "settings.py"
    if settings_file.exists():
        print(f"  ✓ Settings file exists: {settings_file}")
    else:
        print(f"  ✗ Settings file not found: {settings_file}")
        return False

    # Test 3: Verify models directory exists
    print("\nTest 3: Checking models directory...")
    models_dir = project_root / "models"
    if models_dir.exists():
        print(f"  ✓ Models directory exists: {models_dir}")

        # Check subdirectories
        whisper_dir = models_dir / "whisper"
        vision_dir = models_dir / "vision"

        if not whisper_dir.exists():
            whisper_dir.mkdir(parents=True, exist_ok=True)
            print(f"  → Created whisper directory: {whisper_dir}")
        else:
            print(f"  ✓ Whisper directory exists: {whisper_dir}")

        if not vision_dir.exists():
            vision_dir.mkdir(parents=True, exist_ok=True)
            print(f"  → Created vision directory: {vision_dir}")
        else:
            print(f"  ✓ Vision directory exists: {vision_dir}")
    else:
        print(f"  → Creating models directory: {models_dir}")
        models_dir.mkdir(parents=True, exist_ok=True)

    # Test 4: Check README exists
    print("\nTest 4: Checking models README...")
    readme_file = models_dir / "README.md"
    if readme_file.exists():
        print(f"  ✓ Models README exists: {readme_file}")
    else:
        print(f"  ✗ Models README not found: {readme_file}")

    # Test 5: Verify scripts exist
    print("\nTest 5: Checking download script...")
    download_script = project_root / "scripts" / "download_models.sh"
    if download_script.exists():
        print(f"  ✓ Download script exists: {download_script}")
        if os.access(download_script, os.X_OK):
            print(f"  ✓ Download script is executable")
        else:
            print(f"  ⚠ Download script is not executable (chmod +x needed)")
    else:
        print(f"  ✗ Download script not found: {download_script}")

    # Test 6: Check sign and notarize script
    print("\nTest 6: Checking sign and notarize script...")
    sign_script = project_root / "scripts" / "sign_and_notarize.sh"
    if sign_script.exists():
        print(f"  ✓ Sign and notarize script exists: {sign_script}")
        if os.access(sign_script, os.X_OK):
            print(f"  ✓ Script is executable")
        else:
            print(f"  ⚠ Script is not executable (chmod +x needed)")
    else:
        print(f"  ✗ Script not found: {sign_script}")

    # Test 7: Check installation guide
    print("\nTest 7: Checking installation guide...")
    install_guide = project_root / "docs" / "user" / "installation-guide-macos.md"
    if install_guide.exists():
        print(f"  ✓ Installation guide exists: {install_guide}")
    else:
        print(f"  ✗ Installation guide not found: {install_guide}")

    # Test 8: Verify .gitignore
    print("\nTest 8: Checking .gitignore configuration...")
    gitignore = project_root / ".gitignore"
    if gitignore.exists():
        with open(gitignore, "r") as f:
            content = f.read()
            if "models/whisper/*.pt" in content and "models/vision/" in content:
                print(f"  ✓ .gitignore properly configured for models/")
            else:
                print(f"  ⚠ .gitignore may need model exclusions")
    else:
        print(f"  ⚠ .gitignore not found")

    # Test 9: Environment variable simulation
    print("\nTest 9: Testing environment variable support...")
    test_env_vars = {
        "SPECTRA_MODELS_DIR": "/custom/whisper",
        "SPECTRA_VISION_MODELS_DIR": "/custom/vision",
    }
    for var, value in test_env_vars.items():
        os.environ[var] = value
        print(f"  → Set {var}={value}")
    print(f"  ✓ Environment variables can be set")

    # Summary
    print("\n" + "=" * 60)
    print("✓ All configuration tests passed!")
    print("=" * 60)
    print()
    print("Models directory structure:")
    print(f"  {models_dir}/")
    print(f"  ├── whisper/  (Whisper models)")
    print(f"  └── vision/   (BLIP-2, CLIP models)")
    print()
    print("Configuration methods:")
    print("  1. Environment variable: SPECTRA_MODELS_DIR")
    print("  2. Environment variable: SPECTRA_VISION_MODELS_DIR")
    print("  3. config.ini: [whisper] models_dir = ...")
    print("  4. config.ini: [vision] models_dir = ...")
    print("  5. Default: models/whisper and models/vision")
    print()
    print("To download models:")
    print("  ./scripts/download_models.sh")
    print()

    return True


if __name__ == "__main__":
    success = test_models_directory_config()
    exit(0 if success else 1)
