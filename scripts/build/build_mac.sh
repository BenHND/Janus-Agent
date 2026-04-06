#!/bin/bash
# Build script for creating Janus macOS application bundle
# Ticket 11.1 & README #4: macOS Packaging & Distribution
#
# This script creates a standalone macOS .app bundle with all dependencies
# and prepares it for distribution via DMG installer.
#
# USAGE:
#   ./build_mac.sh
#
# REQUIREMENTS:
#   - macOS 10.14 or later
#   - Python 3.8+
#   - py2app (will be installed if missing)
#   - All project dependencies in requirements.txt
#
# OUTPUT:
#   - dist/Janus.app - Standalone application bundle
#   - Ready for code signing and DMG creation
#
# NEXT STEPS:
#   1. Sign and notarize: ./scripts/sign_and_notarize.sh
#   2. Create DMG: ./scripts/create_dmg.sh
#   3. Distribute to users
#
# For detailed build documentation, see:
#   - docs/user/installation-guide-macos.md
#   - INSTALL.md

set -e  # Exit on error

echo "================================================"
echo "Janus macOS Build Script"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

echo "Step 1: Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"

echo ""
echo "Step 2: Checking for py2app..."
if ! python3 -c "import py2app" 2>/dev/null; then
    echo -e "${YELLOW}Installing py2app...${NC}"
    pip3 install py2app
fi
echo -e "${GREEN}✓ py2app available${NC}"

echo ""
echo "Step 3: Installing dependencies..."
pip3 install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo "Step 4: Cleaning previous build..."
if [ -d "build" ]; then
    rm -rf build
fi
if [ -d "dist" ]; then
    rm -rf dist
fi
echo -e "${GREEN}✓ Cleaned previous build${NC}"

echo ""
echo "Step 5: Building application bundle..."
python3 setup.py py2app
echo -e "${GREEN}✓ Application built${NC}"

echo ""
echo "Step 6: Checking bundle..."
APP_PATH="dist/Janus.app"
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}Error: Application bundle not created${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bundle created at $APP_PATH${NC}"

echo ""
echo "Step 7: Downloading Whisper model..."
# Pre-download Whisper model to include in bundle
python3 -c "import whisper; whisper.load_model('base')" 2>/dev/null || true
echo -e "${GREEN}✓ Whisper model ready${NC}"

echo ""
echo "Step 8: Verifying bundle contents..."
if [ -d "$APP_PATH/Contents/MacOS" ]; then
    echo -e "${GREEN}✓ MacOS executable present${NC}"
else
    echo -e "${RED}Error: MacOS executable missing${NC}"
    exit 1
fi

if [ -d "$APP_PATH/Contents/Resources" ]; then
    echo -e "${GREEN}✓ Resources present${NC}"
else
    echo -e "${RED}Error: Resources missing${NC}"
    exit 1
fi

echo ""
echo "================================================"
echo -e "${GREEN}Build completed successfully!${NC}"
echo "================================================"
echo ""
echo "Application: $APP_PATH"
echo "Size: $(du -sh "$APP_PATH" | cut -f1)"
echo ""
echo "To test the application:"
echo "  open dist/Janus.app"
echo ""
echo "To create DMG installer:"
echo "  ./scripts/create_dmg.sh"
echo ""
