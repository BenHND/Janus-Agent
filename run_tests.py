#!/usr/bin/env python3
"""
Unified test runner for Janus project.
Runs all tests with proper environment setup and reports results.

Usage:
    python run_tests.py [options]

Options:
    --fast          Run tests in parallel (faster but less detailed output)
    --coverage      Generate coverage report
    --verbose       Verbose output
    --timeout=N     Set timeout per test in seconds (default: 10)
    --pattern=PATTERN   Run only tests matching pattern (e.g., test_parser*)
    --framework=FRAMEWORK  Use 'pytest' or 'unittest' (default: pytest)
    --list          List all test files without running them
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies():
    """Check if required test dependencies are installed."""
    missing = []
    try:
        import pytest
    except ImportError:
        missing.append("pytest")

    try:
        import coverage
    except ImportError:
        missing.append("coverage")

    if missing:
        print(f"❌ Missing test dependencies: {', '.join(missing)}")
        print(f"Install with: pip install -r requirements-test.txt")
        return False
    return True


def list_tests():
    """List all test files."""
    test_dir = PROJECT_ROOT / "tests"
    test_files = sorted(test_dir.glob("test_*.py"))

    print(f"\n📋 Found {len(test_files)} test files:\n")
    for test_file in test_files:
        print(f"  • {test_file.name}")
    print()
    return len(test_files)


def run_with_pytest(args):
    """Run tests using pytest."""
    pytest_args = [
        "pytest",
        "tests/",
        f"--timeout={args.timeout}",
        "--tb=short",  # Shorter traceback format
        "-ra",  # Show summary of all test outcomes
    ]

    if args.verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")  # Quiet mode

    if args.fast:
        # Run tests in parallel
        pytest_args.extend(["-n", "auto"])

    if args.coverage:
        pytest_args.extend(
            [
                "--cov=janus",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
            ]
        )

    if args.pattern:
        pytest_args.extend(["-k", args.pattern])

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    print(f"🧪 Running tests with pytest...")
    print(f"   Command: {' '.join(pytest_args)}\n")

    result = subprocess.run(pytest_args, env=env)
    return result.returncode


def run_with_unittest(args):
    """Run tests using unittest."""
    unittest_args = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        args.pattern if args.pattern else "test_*.py",
    ]

    if args.verbose:
        unittest_args.append("-v")

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    print(f"🧪 Running tests with unittest...")
    print(f"   Command: {' '.join(unittest_args)}\n")

    result = subprocess.run(unittest_args, env=env, timeout=args.timeout * 100)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run Janus test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--fast", action="store_true", help="Run tests in parallel (pytest only)")
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report (pytest only)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--timeout", type=int, default=10, help="Timeout per test in seconds (default: 10)"
    )
    parser.add_argument("--pattern", "-k", help="Run only tests matching pattern")
    parser.add_argument(
        "--framework",
        choices=["pytest", "unittest"],
        default="pytest",
        help="Test framework to use (default: pytest)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List all test files without running them"
    )

    args = parser.parse_args()

    # Change to project root
    os.chdir(PROJECT_ROOT)

    if args.list:
        count = list_tests()
        return 0

    # Check dependencies
    if args.framework == "pytest" and not check_dependencies():
        print("\n💡 Falling back to unittest...")
        args.framework = "unittest"

    print(f"🚀 Janus Test Runner")
    print(f"   Framework: {args.framework}")
    print(f"   Timeout: {args.timeout}s per test")
    if args.pattern:
        print(f"   Pattern: {args.pattern}")
    print()

    # Run tests
    try:
        if args.framework == "pytest":
            return_code = run_with_pytest(args)
        else:
            return_code = run_with_unittest(args)

        # Print summary
        print()
        if return_code == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with return code {return_code}")

        if args.coverage:
            print(f"\n📊 Coverage report saved to: htmlcov/index.html")

        return return_code

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
