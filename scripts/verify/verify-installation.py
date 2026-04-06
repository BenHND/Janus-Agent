#!/usr/bin/env python3
"""
Verify Janus installation and dependency structure.
Tests that base installation works without optional dependencies.
"""

import importlib
import sys
from typing import List, Tuple


def test_import(module_name: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error: {e}"


def main():
    print("🔍 Verifying Janus Installation\n")

    # Base dependencies (required)
    base_deps = [
        "whisper",
        "pyaudio",
        "numpy",
        "pyautogui",
        "PIL",  # pillow
        "pyperclip",
        "pynput",
        "webrtcvad",
        "psutil",
        "watchdog",
        "dotenv",  # python-dotenv
        "piper",  # piper-tts (TTS engine)
        "soundfile",  # required by piper-tts
    ]

    # Optional dependencies (LLM)
    llm_deps = [
        "openai",
        "anthropic",
        "mistralai",
        "faster_whisper",
        "cryptography",
    ]

    # Optional dependencies (Vision/AI)
    vision_deps = [
        "torch",
        "transformers",
        "cv2",  # opencv-python
        "pytesseract",
        "easyocr",
        "mss",
        "accelerate",
    ]

    # Test base dependencies
    print("📦 Base Dependencies (Required)")
    print("-" * 50)
    base_success = 0
    base_total = len(base_deps)

    for dep in base_deps:
        success, msg = test_import(dep)
        status = "✅" if success else "❌"
        print(f"{status} {dep:20s} - {msg if not success else 'OK'}")
        if success:
            base_success += 1

    print()

    # Test optional LLM dependencies
    print("🤖 LLM Dependencies (Optional)")
    print("-" * 50)
    llm_success = 0
    for dep in llm_deps:
        success, msg = test_import(dep)
        status = "✅" if success else "⚠️ "
        result = "OK" if success else "Not installed (optional)"
        print(f"{status} {dep:20s} - {result}")
        if success:
            llm_success += 1

    print()

    # Test optional vision dependencies
    print("👁️  Vision/AI Dependencies (Optional)")
    print("-" * 50)
    vision_success = 0
    for dep in vision_deps:
        success, msg = test_import(dep)
        status = "✅" if success else "⚠️ "
        result = "OK" if success else "Not installed (optional)"
        print(f"{status} {dep:20s} - {result}")
        if success:
            vision_success += 1

    print()
    print("=" * 50)
    print("Summary:")
    print(f"  Base:    {base_success}/{base_total} installed")
    print(f"  LLM:     {llm_success}/{len(llm_deps)} installed (optional)")
    print(f"  Vision:  {vision_success}/{len(vision_deps)} installed (optional)")
    print()

    # Check if base installation is complete
    if base_success == base_total:
        print("✅ Base installation is complete!")
        print("   You can run: python main.py")
        print()
        if llm_success == 0:
            print("💡 To add LLM features: ./install-llm.sh")
        if vision_success == 0:
            print("💡 To add Vision/AI features: ./install-vision.sh")
        if llm_success == 0 and vision_success == 0:
            print("💡 To install everything: ./install-full.sh")
        return 0
    else:
        print("❌ Base installation incomplete!")
        print(f"   Missing {base_total - base_success} required dependencies")
        print("   Run: ./install-base.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
