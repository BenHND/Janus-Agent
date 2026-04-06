#!/bin/bash
# Run Baseline E2E Tests - TICKET-PRE-AUDIT-000
# 
# This script runs the critical baseline tests that validate
# core agent functionality. These tests MUST pass before and
# after any architectural changes.
#
# Usage:
#   ./run_baseline_tests.sh           # Run all baseline tests
#   ./run_baseline_tests.sh -v        # Run with verbose output
#   ./run_baseline_tests.sh -s        # Run with output capture disabled

# Note: We use 'set -e' with explicit error handling
# to properly report test failures
set -e

# Get script directory and repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$REPO_ROOT"

# Set Python path to repository root
export PYTHONPATH="$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "  JANUS BASELINE E2E TESTS (Golden Master)"
echo "  TICKET-PRE-AUDIT-000"
echo "================================================"
echo ""

# Check platform
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${YELLOW}WARNING: These tests are designed for macOS${NC}"
    echo "Tests will be skipped on this platform: $OSTYPE"
    echo ""
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest is not installed${NC}"
    echo "Install with: pip install -r requirements-test.txt"
    exit 1
fi

# Run the tests
echo "Running critical baseline tests..."
echo ""

# Build pytest command
PYTEST_CMD="pytest tests/e2e/test_baseline_capabilities.py -m 'e2e and critical'"

# Add extra arguments
if [[ "$1" == "-v" ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
elif [[ "$1" == "-s" ]]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Execute tests with explicit error handling
# Temporarily disable 'set -e' to capture exit code
set +e
eval $PYTEST_CMD
TEST_EXIT_CODE=$?
set -e

# Handle results based on exit code
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ BASELINE TESTS PASSED${NC}"
    echo ""
    echo "All critical scenarios validated:"
    echo "  ✓ Scenario A: System capability (open app)"
    echo "  ✓ Scenario B: Web capability (browser navigation)"
    echo "  ✓ Scenario C: Text editing capability"
    echo ""
    echo "Safe to proceed with architectural changes."
    exit 0
else
    echo ""
    echo -e "${RED}✗ BASELINE TESTS FAILED${NC}"
    echo ""
    echo "One or more critical scenarios failed."
    echo "DO NOT proceed with architectural changes until these pass."
    echo ""
    echo "Review the test output above and fix any issues."
    exit 1
fi
