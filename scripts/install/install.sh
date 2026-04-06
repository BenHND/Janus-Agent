#!/bin/bash
# Unified Janus Installation Script
# Installs all dependencies and configures the system in one go

set -e  # Exit on error

echo "🎤 Janus - Unified Installation"
echo "=================================="
echo ""
echo "This will install:"
echo "  • Base voice control dependencies"
echo "  • LLM integration (OpenAI, Anthropic, Mistral, Ollama)"
echo "  • Vision/AI features (OCR, PyTorch, Transformers)"
echo "  • Semantic correction LLM (integrated)"
echo "  • GUI support (tkinter + PySide6)"
echo "  • All required system dependencies"
echo ""
echo "⚠️  Requirements:"
echo "  • Python 3.10 or higher"
echo "  • ~10-15GB of disk space"
echo "  • 15-30 minutes installation time"
echo ""

read -p "Continue with full installation? (y/N) " -n 1 -r
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
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

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

# Check/Create virtual environment
echo ""
if [ -z "$VIRTUAL_ENV" ]; then
    echo "📦 Setting up virtual environment..."
    if [ ! -d "venv" ]; then
        echo "Creating new virtual environment..."
        python3 -m venv venv
        echo "✓ Virtual environment created"
    else
        echo "✓ Using existing virtual environment"
    fi
    echo ""
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✓ Already in virtual environment: $VIRTUAL_ENV"
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

        # Try to install the specific Python version's tk
        if brew install python-tk@${PYTHON_VERSION} 2>/dev/null; then
            echo "✅ Installed python-tk@${PYTHON_VERSION}"
        elif brew install python-tk 2>/dev/null; then
            echo "✅ Installed python-tk"
        else
            echo "❌ Failed to install python-tk via Homebrew."
            echo ""
            echo "   Please try manually:"
            echo "   brew install python-tk@${PYTHON_VERSION}"
            echo "   OR"
            echo "   brew install python-tk"
            echo ""
            echo "   ⚠️  Installation will continue, but GUI features will NOT work."
        fi
    else
        echo "✓ tkinter is already installed"
    fi

    # --- OLLAMA CONDITIONAL INSTALLATION ---
    # Check config.ini for provider = ollama
    SHOULD_INSTALL_OLLAMA=false
    if [ -f "config.ini" ]; then
        # Extract provider value, handling spaces around =
        PROVIDER=$(grep "^provider" config.ini | head -n 1 | awk -F '=' '{print $2}' | tr -d '[:space:]')
        if [ "$PROVIDER" == "ollama" ]; then
            SHOULD_INSTALL_OLLAMA=true
        fi
    fi

    if [ "$SHOULD_INSTALL_OLLAMA" = true ]; then
        if ! command -v ollama &> /dev/null; then
            echo "⬇️  Installing Ollama (required by config.ini)..."
            brew install ollama
            
            echo "🚀 Starting Ollama service..."
            brew services start ollama 2>/dev/null || (ollama serve > /dev/null 2>&1 &)
            echo "⏳ Waiting for Ollama to initialize..."
            sleep 5
        else
            echo "✓ Ollama installed (required by config.ini)"
            # Ensure service is running
            if ! pgrep -x "ollama" > /dev/null && ! pgrep -f "ollama serve" > /dev/null; then
                echo "🚀 Starting Ollama service..."
                brew services start ollama 2>/dev/null || (ollama serve > /dev/null 2>&1 &)
                sleep 5
            fi
        fi
    else
        echo "ℹ️  Skipping Ollama installation (provider is not 'ollama' in config.ini)"
    fi
fi

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip
echo "✓ pip upgraded"

# Install all Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
echo "   This may take 15-30 minutes depending on your connection..."
echo ""

echo "Installing base dependencies..."
pip install -r requirements.txt
echo "✓ Base dependencies installed"

echo ""
echo "Installing LLM dependencies..."
pip install -r requirements-llm.txt
echo "✓ LLM dependencies installed"

echo ""
echo "Installing Vision/AI dependencies..."
pip install -r requirements-vision.txt
echo "✓ Vision dependencies installed"

# Extra: UI & streaming deps not toujours listées clairement dans les requirements
echo ""
echo "📦 Installing UI / streaming extras (PySide6, numpy, pyaudio, faster-whisper)..."
# PySide6 pour l'overlay Qt
pip install "PySide6>=6.6.0" || echo "⚠️ PySide6 failed to install (overlay Qt may not work)"
# numpy (utilisé partout, STT/streaming)
pip install numpy || echo "⚠️ numpy failed to install"
# pyaudio pour le streaming micro (si build possible sur la machine)
pip install pyaudio || echo "⚠️ pyaudio failed to install (streaming micro peut être désactivé)"
# faster-whisper pour RealtimeSTTEngine
pip install "faster-whisper>=0.10.0" || echo "⚠️ faster-whisper failed to install (realtime STT may be disabled)"
# qasync pour intégrer asyncio avec la boucle Qt (UI overlay propre)
pip install qasync || echo "⚠️ qasync failed to install (Qt/async integration may not work)"

# TICKET-P2-01: Install MLX Whisper for Apple Silicon (M1/M2/M3/M4) - instant STT
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Check if running on Apple Silicon (ARM64)
    if [[ "$(uname -m)" == "arm64" ]]; then
        echo ""
        echo "🍎 Apple Silicon detected - Installing MLX Whisper for instant STT..."
        pip install "lightning-whisper-mlx>=0.0.9" && \
            echo "✓ lightning-whisper-mlx installed (Neural Engine acceleration)" || \
            echo "⚠️ lightning-whisper-mlx failed to install (falling back to faster-whisper)"
    fi
fi

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
    echo "   - OLLAMA_ENDPOINT (default: http://localhost:11434)"
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
python3 ./scripts/install/update_language_config.py "$SPECTRA_LANG"

# Create necessary directories
echo ""
echo "📁 Creating model directories..."
mkdir -p models/whisper models/vision models 2>/dev/null || true
echo "✓ Model directories created"

# Download models using Python script
echo ""
echo "📥 Setting up models..."
python3 ./scripts/install/install_models.py
if [ $? -ne 0 ]; then
    echo "⚠️  Model installation encountered issues (see above)"
    echo "   You can retry later by running: python3 ./scripts/install/install_models.py"
fi

# Final verification
echo ""
echo "🔍 Verifying installation..."
echo ""

# Check key dependencies
python3 -c "import whisper" &> /dev/null && echo "   ✅ Whisper (STT)" || echo "   ❌ Whisper - NOT INSTALLED"
python3 -c "import pyautogui" &> /dev/null && echo "   ✅ PyAutoGUI (automation)" || echo "   ❌ PyAutoGUI - NOT INSTALLED"
python3 -c "import torch" &> /dev/null && echo "   ✅ PyTorch (AI)" || echo "   ❌ PyTorch - NOT INSTALLED"
python3 -c "import transformers" &> /dev/null && echo "   ✅ Transformers (Vision AI)" || echo "   ❌ Transformers - NOT INSTALLED"
python3 -c "import openai" &> /dev/null && echo "   ✅ OpenAI SDK" || echo "   ❌ OpenAI - NOT INSTALLED"
python3 -c "import anthropic" &> /dev/null && echo "   ✅ Anthropic SDK" || echo "   ❌ Anthropic - NOT INSTALLED"
python3 -c "import faster_whisper" &> /dev/null && echo "   ✅ faster-whisper (Realtime STT)" || echo "   ❌ faster-whisper - NOT INSTALLED"
python3 -c "import PySide6" &> /dev/null && echo "   ✅ PySide6 (UI)" || echo "   ❌ PySide6 - NOT INSTALLED"
python3 -c "import qasync" &> /dev/null && echo "   ✅ qasync (UI Async)" || echo "   ❌ qasync - NOT INSTALLED"
python3 -c "import einops" &> /dev/null && echo "   ✅ einops (Florence-2)" || echo "   ❌ einops - NOT INSTALLED"
python3 -c "import timm" &> /dev/null && echo "   ✅ timm (Florence-2)" || echo "   ❌ timm - NOT INSTALLED"
python3 -c "import openwakeword" &> /dev/null && echo "   ✅ openWakeWord (Wake Word Detection)" || echo "   ❌ openWakeWord - NOT INSTALLED"
python3 -c "import resemblyzer" &> /dev/null && echo "   ✅ resemblyzer (Voice Fingerprinting - TICKET-STT-002)" || echo "   ❌ resemblyzer - NOT INSTALLED"

# Check MLX Whisper on Apple Silicon
if [[ "$OSTYPE" == "darwin"* ]] && [[ "$(uname -m)" == "arm64" ]]; then
    python3 -c "import lightning_whisper_mlx" &> /dev/null && echo "   ✅ MLX Whisper (Instant STT - Apple Silicon)" || echo "   ⚠️ MLX Whisper - NOT INSTALLED (optional)"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 What's installed:"
echo "   ✓ Voice recognition (Whisper)"
echo "   ✓ Wake word detection (openWakeWord - TICKET-P3-02)"
echo "   ✓ Voice fingerprinting (resemblyzer - TICKET-STT-002)"
echo "   ✓ Text-to-Speech (Piper Neural TTS)"
echo "   ✓ System automation (PyAutoGUI, AppleScript)"
echo "   ✓ LLM APIs (OpenAI, Anthropic, Mistral)"
echo "   ✓ Local LLM support (Ollama if configured)"
echo "   ✓ Semantic correction (via Main LLM or dedicated model)"
echo "   ✓ OCR (Platform-native: Apple Vision, Windows OCR, RapidOCR)"
echo "   ✓ AI Vision (Florence-2 via OmniParser + YOLOv8)"
echo "   ✓ PyTorch with acceleration support"
echo "   ✓ GUI support (PySide6 + tkinter)"
echo ""
echo "🎯 Features enabled by default (configured in config.ini):"
echo "   • LLM reasoning: ✓ (all providers supported)"
echo "   • Vision features: ✓ (OCR + AI vision)"
echo "   • Semantic correction: ✓ (integrated)"
echo "   • Learning: ✓ (continuous improvement)"
echo "   • Wake word detection: ✗ (disabled, enable in config.ini)"
echo "   • Voice fingerprinting: ✗ (disabled, enable in config.ini for security)"
echo ""
echo "🚀 Next steps:"
echo "   1. Edit .env to add your API keys (if using cloud LLMs)"
echo "   2. Run: python main.py"
echo ""
echo "📖 Documentation: docs/user/01-installation.md"
echo ""