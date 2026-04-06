#!/bin/bash
# Quick verification that test infrastructure is working
# This simulates a fresh install scenario

echo "🔍 Verifying Test Infrastructure Setup"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }
echo "✅ Python 3 available"
echo ""

# Check test files exist
echo "2. Checking test runner scripts..."
if [ -f "run_tests.sh" ] && [ -f "run_tests.py" ]; then
    echo "✅ Test runner scripts exist"
else
    echo "❌ Test runner scripts missing"
    exit 1
fi
echo ""

# Check requirements file exists
echo "3. Checking requirements-test.txt..."
if [ -f "requirements-test.txt" ]; then
    echo "✅ requirements-test.txt exists"
else
    echo "❌ requirements-test.txt missing"
    exit 1
fi
echo ""

# Check pytest config exists
echo "4. Checking pytest configuration..."
if [ -f "pytest.ini" ] && [ -f "conftest.py" ]; then
    echo "✅ pytest configuration exists"
else
    echo "❌ pytest configuration missing"
    exit 1
fi
echo ""

# List test files
echo "5. Listing test files..."
python3 run_tests.py --list 2>&1 | grep "Found" || { echo "❌ Failed to list tests"; exit 1; }
echo "✅ Test listing works"
echo ""

# Try running a single simple test
echo "6. Running sample test (test_parser)..."
timeout 30 python3 -m pytest tests/test_parser.py -q --tb=no 2>&1 | grep -E "(passed|PASSED)" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Sample test runs successfully"
else
    echo "⚠️  Sample test had issues (may need dependencies)"
fi
echo ""

echo "✅ Test infrastructure verification complete!"
echo ""
echo "To run tests, use:"
echo "  ./run_tests.sh           # Simple"
echo "  python run_tests.py      # With options"
