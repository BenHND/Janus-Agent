#!/bin/bash
# Complete cleanup and reinstallation script for Janus
# Use this script after a pull to clean everything and reinstall cleanly

set -e  # Exit on error

echo "🧹 Complete cleanup and reinstallation of Janus"
echo "=================================================="
echo ""

# Check that Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 is not installed or not accessible"
    echo "   Install it with: brew install python@3.11"
    exit 1
fi

echo "✓ Python version: $(python3.11 --version)"

# Navigate to repository root (two levels up from scripts/)
# Expected structure: repo_root/scripts/clean.sh
# This assumes venv is at repo_root/../venv
cd "$(dirname "$0")/../.."

echo "🗑️  Removing existing virtual environment..."
rm -rf venv/

echo "🧽 Cleaning Python cache files..."
cd Janus
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true

echo "🐍 Creating a new virtual environment with Python 3.11..."
cd ..
python3.11 -m venv venv

echo "⚡ Activating the virtual environment..."
# Activation for the current session
# shellcheck disable=SC1091
source venv/bin/activate

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "🔧 Next steps:"
echo "   Automatically launching install.sh with the activated venv"
echo ""

# Launch the complete installation with the correct Python/pip (in Janus/)
cd Janus
./scripts/install/install.sh
