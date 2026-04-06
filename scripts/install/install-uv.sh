#!/bin/bash
# UV-based Janus Installation Script
# Modern installation using uv package manager
# TICKET-OPS-001: Migration to uv and packaging

set -e  # Exit on error

echo "🎤 Janus - UV Installation"
echo "=================================="
echo ""
echo "This will install Janus using the modern uv package manager."
echo ""
echo "⚠️  Requirements:"
echo "  • Python 3.10 or higher"
echo "  • ~10-15GB of disk space"
echo "  • 10-20 minutes installation time"
echo ""

read -p "Continue with installation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Check Python version
echo "🔍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "   Please install Python 3.10 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python version: $PYTHON_VERSION"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "❌ Error: Python 3.10 or higher is required"
    echo "   Current version: $PYTHON_VERSION"
    exit 1
fi

# Check disk space
echo ""
echo "🔍 Checking disk space..."
REQUIRED_SPACE_MB=15000  # 15GB
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVAILABLE_SPACE_MB=$(df -m . | awk 'NR==2 {print $4}')
else
    AVAILABLE_SPACE_MB=$(df -BM . | awk 'NR==2 {print $4}' | sed 's/M//')
fi

echo "✓ Available space: ${AVAILABLE_SPACE_MB}MB"

if [ "$AVAILABLE_SPACE_MB" -lt "$REQUIRED_SPACE_MB" ]; then
    echo "⚠️  Warning: Low disk space detected"
    echo "   Available: ${AVAILABLE_SPACE_MB}MB"
    echo "   Recommended: ${REQUIRED_SPACE_MB}MB"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install uv if not already installed
echo ""
echo "📦 Checking uv package manager..."
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
    echo "✓ uv installed"
else
    echo "✓ uv is already installed ($(uv --version))"
fi

# Check Homebrew (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "🔍 Checking Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew is not installed!"
        echo ""
        echo "   Homebrew is required for system dependencies."
        echo "   Install it with:"
        echo ""
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        exit 1
    fi
    echo "✓ Homebrew is installed"
    
    # Install system dependencies
    echo ""
    echo "📦 Installing system dependencies via Homebrew..."
    
    # FFmpeg for audio processing
    if ! command -v ffmpeg &> /dev/null; then
        echo "Installing ffmpeg..."
        brew install ffmpeg || echo "⚠️  ffmpeg installation failed"
    else
        echo "✓ ffmpeg already installed"
    fi
    
    # PortAudio for audio I/O
    if ! brew list portaudio &> /dev/null; then
        echo "Installing portaudio..."
        brew install portaudio || echo "⚠️  portaudio installation failed"
    else
        echo "✓ portaudio already installed"
    fi

    # Install tkinter - REQUIRED for GUI features
    echo ""
    echo "📦 Installing tkinter (required for GUI features)..."
    if ! python3 -c "import tkinter" &> /dev/null; then
        echo "⚠️  tkinter not found. Installing python-tk@${PYTHON_VERSION}..."
        if brew install python-tk@${PYTHON_VERSION} 2>/dev/null; then
            echo "✅ Installed python-tk@${PYTHON_VERSION}"
        elif brew install python-tk 2>/dev/null; then
            echo "✅ Installed python-tk"
        else
            echo "❌ Failed to install python-tk via Homebrew."
            echo "   ⚠️  Installation will continue, but GUI features will NOT work."
        fi
    else
        echo "✓ tkinter is already installed"
    fi
fi

# Sync dependencies using uv
echo ""
echo "📦 Installing Python dependencies with uv..."
echo "   This may take 10-20 minutes depending on your connection..."
echo ""

# Install base dependencies only
echo "Installing base dependencies..."
uv sync --no-dev
echo "✓ Base dependencies installed"

# Ask user which optional features to install
echo ""
echo "🎯 Optional Features"
echo "==================="
echo ""
echo "Would you like to install optional features?"
echo ""
echo "Available features:"
echo "  [l] LLM - AI language models (OpenAI, Anthropic, Mistral, local LLMs)"
echo "  [v] Vision - OCR and AI vision (platform-native OCR, opencv, transformers, OmniParser)"
echo "  [s] Semantic - Vector search and RAG (chromadb, sentence-transformers)"
echo "  [t] Test - Testing framework (pytest, coverage)"
echo "  [d] Dev - Development tools (black, isort, mypy)"
echo "  [a] All - Install all features"
echo "  [n] None - Skip optional features"
echo ""
read -p "Enter your choice [l/v/s/t/d/a/n]: " -n 1 -r
echo ""

case "$REPLY" in
    l|L)
        echo "Installing LLM features..."
        uv sync --extra llm --extra audio
        ;;
    v|V)
        echo "Installing Vision features..."
        uv sync --extra vision --extra audio
        ;;
    s|S)
        echo "Installing Semantic features..."
        uv sync --extra semantic --extra audio
        ;;
    t|T)
        echo "Installing Test features..."
        uv sync --extra test --extra audio
        ;;
    d|D)
        echo "Installing Dev features..."
        uv sync --extra dev --extra audio
        ;;
    a|A)
        echo "Installing all features..."
        uv sync --all-extras
        ;;
    n|N)
        echo "Skipping optional features (audio will still be installed)."
        uv sync --extra audio
        ;;
    *)
        echo "Invalid choice. Installing audio only."
        uv sync --extra audio
        ;;
esac

# Create .env file if it doesn't exist
echo ""
if [ ! -f .env ]; then
    echo "📝 Creating .env configuration file..."
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo ""
    echo "   ⚠️  IMPORTANT: Edit .env to add your API keys:"
    echo "   - OPENAI_API_KEY (for GPT models)"
    echo "   - ANTHROPIC_API_KEY (for Claude models)"
    echo "   - MISTRAL_API_KEY (for Mistral models)"
else
    echo "ℹ️  .env file already exists, skipping creation"
fi

# Language configuration
echo ""
echo "🌍 Language Configuration"
echo "========================"
echo ""
echo "Choose your preferred language for voice recognition:"
echo "  fr - Français (French)"
echo "  en - English"
echo ""
read -p "Enter your choice (fr/en) [fr]: " SPECTRA_LANG
echo ""

# Validate and normalize language choice
if [ -z "$SPECTRA_LANG" ]; then
    SPECTRA_LANG="fr"
elif [ "$SPECTRA_LANG" != "en" ] && [ "$SPECTRA_LANG" != "fr" ]; then
    echo "⚠️  Invalid choice '$SPECTRA_LANG', defaulting to French (fr)"
    SPECTRA_LANG="fr"
fi

echo "✅ Language set to: $SPECTRA_LANG"
echo ""

# Write language to config.ini using Python helper script
echo "📝 Updating config.ini with language preference..."
python3 janus/scripts/update_language_config.py "$SPECTRA_LANG" 2>/dev/null || echo "⚠️ Could not update config.ini"

# Create necessary directories
echo ""
echo "📁 Creating model directories..."
mkdir -p models/whisper models/vision models 2>/dev/null || true
echo "✓ Model directories created"

# Download models using Python script
echo ""
echo "📥 Setting up models..."
python3 janus/scripts/install_models.py 2>/dev/null || echo "⚠️  Model installation encountered issues"

# Final verification
echo ""
echo "🔍 Verifying installation..."
echo ""

# Check key dependencies
python3 -c "import whisper" &> /dev/null && echo "   ✅ Whisper (STT)" || echo "   ❌ Whisper - NOT INSTALLED"
python3 -c "import pyautogui" &> /dev/null && echo "   ✅ PyAutoGUI (automation)" || echo "   ❌ PyAutoGUI - NOT INSTALLED"
python3 -c "import torch" &> /dev/null && echo "   ✅ PyTorch (AI)" || echo "   ❌ PyTorch - NOT INSTALLED"
python3 -c "import PySide6" &> /dev/null && echo "   ✅ PySide6 (UI)" || echo "   ❌ PySide6 - NOT INSTALLED"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 What's installed:"
echo "   ✓ Voice recognition (Whisper)"
echo "   ✓ System automation (PyAutoGUI)"
echo "   ✓ GUI support (PySide6)"
echo "   ✓ Memory and persistence (SQLite)"
echo ""
echo "🚀 Next steps:"
echo "   1. Edit .env to add your API keys (if using cloud LLMs)"
echo "   2. Run: python main.py"
echo ""
echo "📖 Documentation: docs/user/02-installation.md"
echo ""
echo "💡 To add more features later, run:"
echo "   uv sync --extra llm     # Add LLM support"
echo "   uv sync --extra vision  # Add vision/OCR support"
echo "   uv sync --all-extras    # Add all features"
echo ""
