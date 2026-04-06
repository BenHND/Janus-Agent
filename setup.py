"""
Setup script for building Janus macOS application
"""
import os
import sys

from setuptools import find_packages, setup

APP_NAME = "Janus"
VERSION = "1.0.0"
AUTHOR = "BenHND"
DESCRIPTION = "Voice-controlled computer automation for macOS"

# Main script to run
MAIN_SCRIPT = "main.py"

# Check if icon file exists
ICON_PATH = "resources/icon.icns"
HAS_ICON = os.path.exists(ICON_PATH)

# Build py2app options
py2app_options = {
    "argv_emulation": True,
    "packages": [
        "janus",
        "whisper",
        "numpy",
        "pyaudio",
        "pyautogui",
        "pyperclip",
        "PIL",
        "pynput",
        "webrtcvad",
        "psutil",
    ],
    "includes": [
        "janus.stt",
        "janus.parser",
        "janus.automation",
        "janus.memory",
        "janus.orchestrator",
        "janus.modules",
        "janus.clipboard",
        "janus.llm",
        "janus.validation",
        "janus.vision",
        "janus.ui",
        "janus.persistence",
        "janus.logging",
        "janus.utils",
    ],
    "excludes": [
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
    ],
    "resources": [
        "config.ini",
    ],
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleGetInfoString": DESCRIPTION,
        "CFBundleIdentifier": "com.benhnd.janus",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": f"Copyright © 2024 {AUTHOR}",
        "NSMicrophoneUsageDescription": "Janus needs microphone access for voice commands",
        "NSAppleEventsUsageDescription": "Janus needs to control other applications for automation",
    },
    "semi_standalone": False,  # Fully standalone
    "site_packages": True,
}

# Add icon if it exists
if HAS_ICON:
    py2app_options["iconfile"] = ICON_PATH

# Application options for py2app
OPTIONS = {"py2app": py2app_options}

# Setup configuration
setup(
    name=APP_NAME,
    version=VERSION,
    author=AUTHOR,
    description=DESCRIPTION,
    packages=find_packages(),
    app=[MAIN_SCRIPT],
    options=OPTIONS,
    setup_requires=["py2app"],
    install_requires=[
        # Core dependencies (base requirements.txt)
        "openai-whisper==20231117",
        "pyaudio==0.2.14",
        "numpy==1.26.3",
        "pyautogui==0.9.54",
        "pyobjc-framework-Cocoa==10.1",
        "pyobjc-framework-ApplicationServices==10.1",
        "webrtcvad==2.0.10",
        "pynput==1.7.6",
        "pillow==10.2.0",
        "pyperclip==1.8.2",
        "python-dotenv>=1.0.0",
        "psutil>=5.9.0",
        "watchdog>=3.0.0",
    ],
    extras_require={
        # LLM features (requirements-llm.txt)
        "llm": [
            "openai>=1.3.0",
            "anthropic>=0.18.0",
            "mistralai>=0.1.0",
            "llama-cpp-python>=0.2.0",
            "faster-whisper>=0.10.0",
            "cryptography>=41.0.0",
        ],
        # Vision/AI features (requirements-vision.txt)
        "vision": [
            "pytesseract>=0.3.10",
            "easyocr>=1.7.0",
            "opencv-python>=4.8.0",
            "mss>=9.0.0",
            "torch>=2.0.0",
            "transformers>=4.35.0",
            "sentencepiece>=0.1.99",
            "accelerate>=0.24.0",
        ],
        # All features
        "full": [
            "openai>=1.3.0",
            "anthropic>=0.18.0",
            "mistralai>=0.1.0",
            "llama-cpp-python>=0.2.0",
            "faster-whisper>=0.10.0",
            "cryptography>=41.0.0",
            "pytesseract>=0.3.10",
            "easyocr>=1.7.0",
            "opencv-python>=4.8.0",
            "mss>=9.0.0",
            "torch>=2.0.0",
            "transformers>=4.35.0",
            "sentencepiece>=0.1.99",
            "accelerate>=0.24.0",
        ],
    },
    python_requires=">=3.8",
)
