#!/bin/bash
# Download AI models for Janus on first launch
# Models are stored in the local models/ directory instead of ~/.cache

set -e

echo "================================================"
echo "Janus Model Downloader"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models"

# Default model sizes
WHISPER_MODEL="${WHISPER_MODEL:-base}"
VISION_MODELS="${VISION_MODELS:-false}"
PIPER_MODEL="${PIPER_MODEL:-true}"  # Download Piper TTS by default

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --whisper)
            WHISPER_MODEL="$2"
            shift 2
            ;;
        --with-vision)
            VISION_MODELS=true
            shift
            ;;
        --no-piper)
            PIPER_MODEL=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --whisper MODEL    Whisper model size (tiny, base, small, medium, large)"
            echo "                     Default: base (~140MB)"
            echo "  --with-vision      Also download vision AI models (BLIP-2, CLIP)"
            echo "                     Requires ~5-10GB of disk space"
            echo "  --no-piper         Skip Piper TTS model download"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Download Whisper + Piper TTS"
            echo "  $0 --whisper small           # Download small Whisper + Piper"
            echo "  $0 --with-vision             # Download Whisper + Piper + vision models"
            echo "  $0 --no-piper                # Download Whisper only (no TTS)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Create models directory
echo "Step 1: Setting up models directory..."
mkdir -p "$MODELS_DIR"
mkdir -p "$MODELS_DIR/whisper"
mkdir -p "$MODELS_DIR/piper"
mkdir -p "$MODELS_DIR/vision"
echo -e "${GREEN}✓ Models directory created: $MODELS_DIR${NC}"

# Check disk space
echo ""
echo "Step 2: Checking disk space..."
REQUIRED_SPACE=600  # MB for Whisper base + Piper TTS
if [ "$VISION_MODELS" = true ]; then
    REQUIRED_SPACE=10240  # 10GB for Whisper + Piper + vision models
fi

AVAILABLE_SPACE=$(df -m "$MODELS_DIR" | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo -e "${RED}Error: Insufficient disk space${NC}"
    echo "Required: ${REQUIRED_SPACE}MB, Available: ${AVAILABLE_SPACE}MB"
    exit 1
fi
echo -e "${GREEN}✓ Sufficient disk space available${NC}"

# Check Python and dependencies
echo ""
echo "Step 3: Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "Python version: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not running in a virtual environment${NC}"
    echo "It's recommended to use a virtual environment"
fi

echo -e "${GREEN}✓ Python environment ready${NC}"

# Download Piper TTS model
if [ "$PIPER_MODEL" = true ]; then
    echo ""
    echo "================================================"
    echo "Downloading Piper TTS Model"
    echo "================================================"
    echo ""

    PIPER_MODEL_FILE="$MODELS_DIR/piper/fr_FR-siwis-medium.onnx"
    PIPER_CONFIG_FILE="$MODELS_DIR/piper/fr_FR-siwis-medium.onnx.json"

    if [ -f "$PIPER_MODEL_FILE" ] && [ -f "$PIPER_CONFIG_FILE" ]; then
        echo -e "${GREEN}✓ Piper TTS model already exists${NC}"
        echo "  Location: $PIPER_MODEL_FILE"
        echo "  Size: $(du -h "$PIPER_MODEL_FILE" | cut -f1)"
    else
        echo "Model: fr_FR-siwis-medium (French, high-quality)"
        echo "Size: ~60MB"
        echo ""
        echo "Downloading from Hugging Face..."

        # Download Piper model using wget or curl
        if command -v wget &> /dev/null; then
            wget -q --show-progress \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx" \
                -O "$PIPER_MODEL_FILE" && \
            wget -q --show-progress \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json" \
                -O "$PIPER_CONFIG_FILE"
        elif command -v curl &> /dev/null; then
            curl -L --progress-bar \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx" \
                -o "$PIPER_MODEL_FILE" && \
            curl -L --progress-bar \
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json" \
                -o "$PIPER_CONFIG_FILE"
        else
            echo -e "${RED}Error: wget or curl not found${NC}"
            echo "Please install wget or curl to download models"
            exit 1
        fi

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Piper TTS model downloaded successfully${NC}"
            echo "  Location: $PIPER_MODEL_FILE"
            echo "  Size: $(du -h "$PIPER_MODEL_FILE" | cut -f1)"
        else
            echo -e "${RED}✗ Failed to download Piper TTS model${NC}"
            echo "You can continue without TTS or download manually from:"
            echo "https://huggingface.co/rhasspy/piper-voices"
        fi
    fi
fi

# Download Whisper model
echo ""
echo "================================================"
echo "Downloading Whisper Model"
echo "================================================"
echo ""
echo "Model: $WHISPER_MODEL"
echo "Size estimates:"
echo "  - tiny:   ~40MB"
echo "  - base:   ~140MB"
echo "  - small:  ~460MB"
echo "  - medium: ~1.4GB"
echo "  - large:  ~2.9GB"
echo ""

MODEL_SIZES=("tiny:40" "base:140" "small:460" "medium:1400" "large:2900")
for size_pair in "${MODEL_SIZES[@]}"; do
    IFS=':' read -r model size <<< "$size_pair"
    if [ "$model" = "$WHISPER_MODEL" ]; then
        echo "Estimated download size: ~${size}MB"
        break
    fi
done

echo ""
echo "This may take a few minutes depending on your connection..."
echo ""

# Set environment variable to use local models directory
export XDG_CACHE_HOME="$MODELS_DIR"

# Download Whisper model
python3 << EOF
import os
import sys
import whisper

print("Downloading Whisper model: $WHISPER_MODEL")
try:
    # Set cache directory
    os.environ['TORCH_HOME'] = '$MODELS_DIR/whisper'

    # Download model
    model = whisper.load_model('$WHISPER_MODEL', download_root='$MODELS_DIR/whisper')
    print("✓ Whisper model downloaded successfully")
    print(f"  Model size: $WHISPER_MODEL")
    print(f"  Location: $MODELS_DIR/whisper")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error downloading Whisper model: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Whisper model ready${NC}"
else
    echo -e "${RED}✗ Failed to download Whisper model${NC}"
    exit 1
fi

# Download vision models if requested
if [ "$VISION_MODELS" = true ]; then
    echo ""
    echo "================================================"
    echo "Downloading Vision AI Models"
    echo "================================================"
    echo ""
    echo "Models: BLIP-2, CLIP"
    echo "Total size: ~5-10GB"
    echo ""
    echo "This will take several minutes..."
    echo ""

    # Check if vision dependencies are installed
    python3 -c "import transformers, torch" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Vision dependencies not installed${NC}"
        echo "Please install vision dependencies first:"
        echo "  ./install-vision.sh"
        exit 1
    fi

    # Download vision models
    python3 << EOF
import os
import sys
from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel

print("Downloading BLIP-2 model...")
try:
    # Set cache directory
    os.environ['TRANSFORMERS_CACHE'] = '$MODELS_DIR/vision'
    os.environ['HF_HOME'] = '$MODELS_DIR/vision'

    # Download BLIP-2
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        cache_dir='$MODELS_DIR/vision'
    )
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        cache_dir='$MODELS_DIR/vision'
    )
    print("✓ BLIP-2 model downloaded")

    print("\nDownloading CLIP model...")
    clip_processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32",
        cache_dir='$MODELS_DIR/vision'
    )
    clip_model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32",
        cache_dir='$MODELS_DIR/vision'
    )
    print("✓ CLIP model downloaded")

    print("\n✓ All vision models downloaded successfully")
    print(f"  Location: $MODELS_DIR/vision")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error downloading vision models: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Vision models ready${NC}"
    else
        echo -e "${RED}✗ Failed to download vision models${NC}"
        echo "You can continue using Janus without vision features"
    fi
fi

# Create a marker file to indicate models are downloaded
echo ""
echo "Creating download marker..."
cat > "$MODELS_DIR/.models_downloaded" << EOF
# Janus Models Download Information
# This file indicates which models have been downloaded

DOWNLOAD_DATE=$(date +"%Y-%m-%d %H:%M:%S")
WHISPER_MODEL=$WHISPER_MODEL
PIPER_MODEL=$PIPER_MODEL
VISION_MODELS=$VISION_MODELS

# To re-download models, delete this file and run download_models.sh again
EOF

echo -e "${GREEN}✓ Download marker created${NC}"

# Summary
echo ""
echo "================================================"
echo -e "${GREEN}Model download complete!${NC}"
echo "================================================"
echo ""
echo "Downloaded models:"
echo "  ✓ Whisper ($WHISPER_MODEL)"
if [ "$PIPER_MODEL" = true ]; then
    echo "  ✓ Piper TTS (fr_FR-siwis-medium)"
fi
if [ "$VISION_MODELS" = true ]; then
    echo "  ✓ BLIP-2 (image captioning)"
    echo "  ✓ CLIP (image-text matching)"
fi
echo ""
echo "Models location: $MODELS_DIR"
echo "Total size: $(du -sh "$MODELS_DIR" | cut -f1)"
echo ""
echo "To use these models, set environment variable:"
echo "  export SPECTRA_MODELS_DIR=\"$MODELS_DIR\""
echo ""
echo "Or add to your .env file:"
echo "  SPECTRA_MODELS_DIR=$MODELS_DIR"
echo ""
echo "Janus is now ready to use!"
echo ""
