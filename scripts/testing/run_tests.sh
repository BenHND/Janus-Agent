#!/bin/bash
# Simple test runner for Janus
# Runs all tests with proper environment setup
# This script is in scripts/testing/, navigate to repo root for test execution

set -e  # Exit on error

# Get script directory and repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Janus Test Runner${NC}"
echo -e "Repository root: $REPO_ROOT"
echo ""

# Check if pytest is installed
if python3 -c "import pytest" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Using pytest"

    # Set Python path to repository root
    export PYTHONPATH="$REPO_ROOT"

    # Run pytest with timeout and summary
    python3 -m pytest tests/ \
        --timeout=10 \
        --tb=short \
        -ra \
        "$@"

    EXIT_CODE=$?

else
    echo -e "${YELLOW}⚠${NC}  pytest not found, using unittest"
    echo -e "${YELLOW}   Install pytest for better output: pip install -r requirements-test.txt${NC}"
    echo ""

    # Set Python path and run unittest from repo root
    export PYTHONPATH="$REPO_ROOT"

    python3 -m unittest discover -s tests -p "test_*.py" -v

    EXIT_CODE=$?
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Tests failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
