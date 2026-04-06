#!/bin/bash
# macOS compatibility verification script
# Ticket 11.3: Verify automatic functioning on different macOS versions

set -e

echo "================================================"
echo "Janus macOS Compatibility Checker"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Results tracking
PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    ((WARNINGS++))
}

check_info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

echo "System Information"
echo "----------------"

# Check OS
if [[ "$(uname)" != "Darwin" ]]; then
    check_fail "Not running on macOS"
    exit 1
fi
check_pass "Running on macOS"

# Get macOS version
MACOS_VERSION=$(sw_vers -productVersion)
MACOS_BUILD=$(sw_vers -buildVersion)
MACOS_NAME=$(sw_vers -productName)
echo ""
check_info "macOS Version: $MACOS_VERSION ($MACOS_BUILD)"
check_info "Product Name: $MACOS_NAME"

# Parse version
MAJOR=$(echo $MACOS_VERSION | cut -d. -f1)
MINOR=$(echo $MACOS_VERSION | cut -d. -f2)

echo ""
echo "Version Compatibility"
echo "--------------------"

# Check minimum version (10.14 Mojave)
if [ "$MAJOR" -gt 10 ] || ([ "$MAJOR" -eq 10 ] && [ "$MINOR" -ge 14 ]); then
    check_pass "macOS version $MACOS_VERSION is supported (10.14+ required)"
else
    check_fail "macOS version $MACOS_VERSION is too old (10.14+ required)"
fi

# Specific version checks
if [ "$MAJOR" -ge 13 ]; then
    check_info "macOS Ventura (13.0+) or later detected"
    check_pass "Full feature support expected"
elif [ "$MAJOR" -eq 12 ]; then
    check_info "macOS Monterey (12.0) detected"
    check_pass "Full feature support expected"
elif [ "$MAJOR" -eq 11 ]; then
    check_info "macOS Big Sur (11.0) detected"
    check_pass "Full feature support expected"
elif [ "$MAJOR" -eq 10 ] && [ "$MINOR" -eq 15 ]; then
    check_info "macOS Catalina (10.15) detected"
    check_pass "Full feature support expected"
elif [ "$MAJOR" -eq 10 ] && [ "$MINOR" -eq 14 ]; then
    check_info "macOS Mojave (10.14) detected"
    check_warn "Minimum supported version - some features may be limited"
fi

echo ""
echo "Python Environment"
echo "------------------"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    check_pass "Python 3 found: $PYTHON_VERSION"

    # Check version
    PY_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PY_MAJOR" -gt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 8 ]); then
        check_pass "Python version $PYTHON_VERSION meets requirements (3.8+)"
    else
        check_fail "Python version $PYTHON_VERSION is too old (3.8+ required)"
    fi
else
    check_fail "Python 3 not found in PATH"
fi

echo ""
echo "System Requirements"
echo "-------------------"

# Check CPU architecture
ARCH=$(uname -m)
check_info "CPU Architecture: $ARCH"

if [[ "$ARCH" == "arm64" ]]; then
    check_pass "Apple Silicon (M1/M2/M3) detected"
elif [[ "$ARCH" == "x86_64" ]]; then
    check_pass "Intel processor detected"
else
    check_warn "Unknown architecture: $ARCH"
fi

# Check memory
TOTAL_MEM=$(sysctl -n hw.memsize)
TOTAL_MEM_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
check_info "Total Memory: ${TOTAL_MEM_GB}GB"

if [ "$TOTAL_MEM_GB" -ge 8 ]; then
    check_pass "8GB+ RAM available (recommended)"
elif [ "$TOTAL_MEM_GB" -ge 4 ]; then
    check_pass "4GB+ RAM available (minimum)"
else
    check_warn "Less than 4GB RAM may impact performance"
fi

# Check disk space
FREE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
check_info "Free Disk Space: ${FREE_SPACE}GB"

if [ "$FREE_SPACE" -ge 5 ]; then
    check_pass "5GB+ free space available"
elif [ "$FREE_SPACE" -ge 2 ]; then
    check_pass "2GB+ free space available (minimum)"
else
    check_warn "Less than 2GB free space may cause issues"
fi

echo ""
echo "Dependencies"
echo "------------"

# Check Homebrew (optional but recommended)
if command -v brew &> /dev/null; then
    BREW_VERSION=$(brew --version | head -1)
    check_pass "Homebrew installed: $BREW_VERSION"
else
    check_warn "Homebrew not installed (recommended for dependencies)"
fi

# Check PortAudio (for PyAudio)
if brew list portaudio &> /dev/null 2>&1 || [ -d "/usr/local/opt/portaudio" ] || [ -d "/opt/homebrew/opt/portaudio" ]; then
    check_pass "PortAudio found (required for microphone)"
else
    check_warn "PortAudio not found - install with: brew install portaudio"
fi

# TICKET-CLEANUP-VISION: Tesseract no longer required (native OCR is used)
# Check Tesseract (REMOVED - optional, not recommended)
# Platform-native OCR (Apple Vision) is used instead
check_info "OCR: Using platform-native engines (Apple Vision, Windows OCR, RapidOCR)"

echo ""
echo "Permissions"
echo "-----------"

# Note: Can't actually check permissions without running the app
check_info "Required permissions:"
echo "  - Microphone access (for voice input)"
echo "  - Accessibility access (for automation)"
echo "  - AppleScript access (for app control)"
check_warn "Permissions must be granted manually on first run"

echo ""
echo "================================================"
echo "Compatibility Check Summary"
echo "================================================"
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ System is compatible with Janus${NC}"

    if [ "$WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}⚠ Please review warnings above${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ System has compatibility issues${NC}"
    echo "Please address the failed checks above"
    exit 1
fi
