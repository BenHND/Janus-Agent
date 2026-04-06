#!/bin/bash
# Nuitka Build Script for Janus
# Creates standalone binary with embedded Python interpreter
# TICKET-OPS-001: Migration to uv and packaging

set -e  # Exit on error

echo "================================================"
echo "Janus Nuitka Build Script"
echo "================================================"
echo ""
echo "This script builds a standalone binary of Janus"
echo "that includes the Python interpreter and all dependencies."
echo ""
echo "Users will NOT need Python installed to run it."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS and architecture
OS_TYPE="unknown"
ARCH=$(uname -m)
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    OUTPUT_NAME="janus-macos-${ARCH}"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    OUTPUT_NAME="janus-linux-${ARCH}"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS_TYPE="windows"
    OUTPUT_NAME="janus-windows-${ARCH}.exe"
else
    echo -e "${RED}Error: Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo "Building for: $OS_TYPE ($ARCH)"
echo ""

# Check Python version
echo "Step 1: Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"

# Check if Nuitka is installed
echo ""
echo "Step 2: Checking Nuitka..."
if ! python3 -c "import nuitka" 2>/dev/null; then
    echo -e "${YELLOW}Installing Nuitka...${NC}"
    pip install nuitka
fi
echo -e "${GREEN}✓ Nuitka available${NC}"

# Check if ordered-set is installed (required by Nuitka)
echo ""
echo "Step 3: Checking Nuitka dependencies..."
if ! python3 -c "import ordered_set" 2>/dev/null; then
    echo -e "${YELLOW}Installing ordered-set...${NC}"
    pip install ordered-set
fi
echo -e "${GREEN}✓ Nuitka dependencies available${NC}"

# Install dependencies if not already installed
echo ""
echo "Step 4: Installing project dependencies..."
if command -v uv &> /dev/null; then
    echo "Using uv to install dependencies..."
    uv sync --all-extras
else
    echo "Using pip to install dependencies..."
    pip install -e .
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Clean previous build
echo ""
echo "Step 5: Cleaning previous build..."
if [ -d "build" ]; then
    rm -rf build
fi
if [ -d "dist" ]; then
    rm -rf dist
fi
if [ -f "${OUTPUT_NAME}" ]; then
    rm -f "${OUTPUT_NAME}"
fi
echo -e "${GREEN}✓ Cleaned previous build${NC}"

# Create build output directory
mkdir -p dist

# Build with Nuitka
echo ""
echo "Step 6: Building standalone binary with Nuitka..."
echo "This may take 10-30 minutes..."
echo ""

# Common Nuitka options
# Note: --onefile creates a single executable (includes --standalone functionality)
NUITKA_OPTS=(
    --onefile
    --assume-yes-for-downloads
    --output-dir=dist
    --python-flag=no_site
    --enable-plugin=anti-bloat
    --noinclude-pytest-mode=nofollow
    --noinclude-setuptools-mode=nofollow
)

# Platform-specific options
if [[ "$OS_TYPE" == "macos" ]]; then
    NUITKA_OPTS+=(
        --macos-create-app-bundle
        --macos-app-icon=resources/icon.icns
        --macos-app-name=Janus
        --macos-app-version=1.0.0
    )
elif [[ "$OS_TYPE" == "windows" ]]; then
    NUITKA_OPTS+=(
        --windows-console-mode=disable
        --windows-icon-from-ico=resources/icon.ico
    )
fi

# Include data files
NUITKA_OPTS+=(
    --include-data-dir=models=models
    --include-data-file=config.ini=config.ini
    --include-data-file=.env.example=.env.example
)

# Execute Nuitka build
python3 -m nuitka "${NUITKA_OPTS[@]}" --output-filename="${OUTPUT_NAME}" main.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build completed successfully!${NC}"
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

# Find the output binary
echo ""
echo "Step 7: Locating output binary..."
if [[ "$OS_TYPE" == "macos" ]]; then
    BINARY_PATH="dist/Janus.app"
else
    BINARY_PATH="dist/${OUTPUT_NAME}"
fi

if [ -e "$BINARY_PATH" ]; then
    echo -e "${GREEN}✓ Binary created at: $BINARY_PATH${NC}"
    
    # Get size
    if [[ "$OS_TYPE" == "macos" ]]; then
        SIZE=$(du -sh "$BINARY_PATH" | cut -f1)
    else
        SIZE=$(du -h "$BINARY_PATH" | cut -f1)
    fi
    echo "Size: $SIZE"
else
    echo -e "${RED}✗ Binary not found at expected location${NC}"
    echo "Expected: $BINARY_PATH"
    echo "Contents of dist/:"
    ls -la dist/
    exit 1
fi

# Test the binary (basic smoke test)
echo ""
echo "Step 8: Testing binary..."
if [[ "$OS_TYPE" == "macos" ]]; then
    # For macOS app bundle, test the executable inside
    EXECUTABLE="$BINARY_PATH/Contents/MacOS/main"
    if [ -x "$EXECUTABLE" ]; then
        echo -e "${GREEN}✓ Executable found and is runnable${NC}"
    else
        echo -e "${RED}✗ Executable not found or not runnable${NC}"
        exit 1
    fi
else
    # For Linux/Windows, test the binary directly
    if [ -x "$BINARY_PATH" ]; then
        echo -e "${GREEN}✓ Binary is executable${NC}"
    else
        echo -e "${RED}✗ Binary is not executable${NC}"
        exit 1
    fi
fi

echo ""
echo "================================================"
echo -e "${GREEN}Build completed successfully!${NC}"
echo "================================================"
echo ""
echo "Binary: $BINARY_PATH"
echo "Size: $SIZE"
echo ""
echo "To test the binary:"
if [[ "$OS_TYPE" == "macos" ]]; then
    echo "  open $BINARY_PATH"
elif [[ "$OS_TYPE" == "windows" ]]; then
    echo "  .\\$BINARY_PATH"
else
    echo "  ./$BINARY_PATH"
fi
echo ""
echo "To distribute:"
if [[ "$OS_TYPE" == "macos" ]]; then
    echo "  1. Sign the app: codesign -s 'Developer ID' $BINARY_PATH"
    echo "  2. Create DMG: hdiutil create -volname Janus -srcfolder dist/Janus.app -ov -format UDZO dist/Janus-installer.dmg"
elif [[ "$OS_TYPE" == "windows" ]]; then
    echo "  1. Create installer using NSIS or InnoSetup"
    echo "  2. Sign the executable with signtool"
else
    echo "  1. Create .deb or .rpm package"
    echo "  2. Or distribute as AppImage or tarball"
fi
echo ""

# Create a simple README for distribution
cat > dist/README.txt << EOF
Janus Standalone Binary
=======================

This is a standalone version of Janus that includes the Python interpreter
and all dependencies. You do NOT need Python installed to run this.

System Requirements:
- macOS 10.14+ / Windows 10+ / Linux (recent distribution)
- 8GB RAM (16GB recommended)
- Microphone for voice input

Quick Start:
1. Extract/Copy the binary to your desired location
2. Create a .env file with your API keys (optional for cloud features)
3. Run the binary

For detailed documentation, visit:
https://github.com/BenHND/Janus

License: MIT
EOF

echo "Created distribution README at dist/README.txt"
echo ""
