#!/bin/bash
# CI/CD Activation Verification Script
# This script demonstrates that the CI is properly disabled by default

echo "========================================"
echo "CI/CD Protection Verification"
echo "========================================"
echo ""

# Check if .github/workflows directory exists
if [ ! -d ".github/workflows" ]; then
    echo "❌ ERROR: .github/workflows directory not found"
    exit 1
fi
echo "✅ .github/workflows directory exists"

# Check if test.yml.example exists
if [ ! -f ".github/workflows/test.yml.example" ]; then
    echo "❌ ERROR: test.yml.example not found"
    exit 1
fi
echo "✅ test.yml.example exists (CI template available)"

# Check if test.yml does NOT exist (should be disabled)
if [ -f ".github/workflows/test.yml" ]; then
    echo "⚠️  WARNING: test.yml exists - CI is ACTIVE"
    echo "   To disable: rm .github/workflows/test.yml"
    exit 1
else
    echo "✅ test.yml does NOT exist (CI is disabled)"
fi

# Check if .gitignore exists and works
if [ ! -f ".github/workflows/.gitignore" ]; then
    echo "❌ ERROR: .gitignore not found in workflows directory"
    exit 1
fi
echo "✅ .gitignore exists for workflow protection"

# Test that .gitignore prevents tracking of .yml files
echo ""
echo "Testing .gitignore protection..."
cp .github/workflows/test.yml.example .github/workflows/test.yml 2>/dev/null

# Check git status
if git status --porcelain | grep -q "test.yml"; then
    echo "❌ ERROR: test.yml is being tracked by git!"
    rm .github/workflows/test.yml
    exit 1
else
    echo "✅ .gitignore correctly prevents tracking of test.yml"
fi

# Clean up
rm .github/workflows/test.yml 2>/dev/null

echo ""
echo "========================================"
echo "✅ All CI/CD Protection Checks Passed"
echo "========================================"
echo ""
echo "Summary:"
echo "  - CI workflow is disabled by default"
echo "  - Template file available for activation"
echo "  - .gitignore prevents accidental commits"
echo "  - Zero risk of GitHub Actions costs"
echo ""
echo "To enable CI, run:"
echo "  mv .github/workflows/test.yml.example .github/workflows/test.yml"
echo "  git add .github/workflows/test.yml"
echo "  git commit -m 'Enable CI workflow'"
echo ""
