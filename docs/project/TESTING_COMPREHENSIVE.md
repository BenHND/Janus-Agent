# Janus Testing Guide

## Overview

Janus includes a comprehensive test suite with **1962 tests** across 132 test files. This guide explains how to install dependencies, run tests, and interpret results.

## Quick Start

### 1. Install Test Dependencies

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

This installs:
- pytest (test framework)
- pytest-timeout (handle hanging tests)
- pytest-xdist (parallel execution)
- coverage (code coverage)
- Core dependencies (psutil, pillow, etc.)

### 2. Run All Tests

**Simple way:**
```bash
./run_tests.sh
```

**With Python script (more options):**
```bash
python run_tests.py
```

## Test Runner Options

The `run_tests.py` script provides several options:

### List Tests
```bash
python run_tests.py --list
```

### Run Specific Tests
```bash
# By pattern
python run_tests.py --pattern test_nlu_parser

# Multiple patterns
python run_tests.py --pattern "test_nlu_parser or test_config"
```

### Fast Parallel Execution
```bash
python run_tests.py --fast
```

### Generate Coverage Report
```bash
python run_tests.py --coverage
```
Opens `htmlcov/index.html` for detailed coverage report.

### Verbose Output
```bash
python run_tests.py --verbose
```

### Custom Timeout
```bash
python run_tests.py --timeout 30
```

### Using Unittest Instead of Pytest
```bash
python run_tests.py --framework unittest
```

## Test Results

### Current Status
- **Total Tests**: 1962
- **Passing**: 1406 (71.7%) ✅
- **Failing**: 135 (6.9%) ❌
- **Skipped**: 421 (21.4%) ⏭️

### Test Categories

#### Unit Tests
Core functionality tests (pass consistently):
- NLU Parser tests (`test_nlu_parser.py`) - V3 pipeline command parsing
- Configuration tests (`test_config_manager.py`)
- Memory tests (`test_memory*.py`)
- Persistence tests (`test_action_history.py`)

**Note:** Legacy `test_parser.py` and `test_unified_command_parser.py` removed - CommandParser deprecated in V3

#### Integration Tests
Multi-component tests:
- Workflow tests (`test_workflow*.py`)
- Orchestrator tests (`test_orchestrator*.py`)
- Pipeline tests (`test_pipeline*.py`)

#### Platform-Specific Tests (Skipped on Linux)
Tests requiring macOS:
- `test_applescript_executor.py` - AppleScript automation
- `test_tts_adapter.py` - macOS TTS
- `test_tts_mac03_enhancements.py` - TTS enhancements
- Various `test_mac*.py` files

#### UI Tests (Skipped without Display)
Tests requiring GUI:
- `test_config_ui.py` - Configuration UI
- `test_overlay.py` - Overlay UI
- `test_confirmation_dialog.py` - Dialog boxes

## Running Tests Manually

### Using Pytest Directly

```bash
# Run all tests
pytest tests/

# Run specific file
pytest tests/test_nlu_parser.py

# Run with verbose output
pytest tests/ -v

# Run with short traceback
pytest tests/ --tb=short

# Stop on first failure
pytest tests/ -x

# Run last failed tests only
pytest tests/ --lf
```

### Using Unittest Directly

```bash
# Run all tests
python -m unittest discover tests -p "test_*.py"

# Run specific test file
python -m unittest tests.test_nlu_parser

# Run specific test class
python -m unittest tests.test_nlu_parser.TestNLUParser

# Run specific test method
python -m unittest tests.test_nlu_parser.TestNLUParser.test_basic_open_app

# Verbose output
python -m unittest discover tests -v
```

## Understanding Test Results

### Passing Tests ✅
Tests that execute successfully and meet all assertions.

### Failing Tests ❌
Tests that fail assertions or raise unexpected errors. Common reasons:
- **Environment mismatch**: Test expects macOS but runs on Linux
- **Missing dependencies**: Optional features not installed (LLM, Vision)
- **Mock issues**: Mocks not properly configured
- **API changes**: Code evolved but tests not updated

### Skipped Tests ⏭️
Tests intentionally skipped due to:
- Platform requirements (macOS-only features)
- Missing dependencies (tkinter, Qt, pyautogui)
- Optional features (LLM, Vision when not installed)

## Continuous Integration

### GitHub Actions
Tests run automatically on:
- Pull requests
- Commits to main branch

### Local Pre-commit
Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Troubleshooting

### "pytest not installed"
```bash
pip install pytest
# Or install all test dependencies:
pip install -r requirements-test.txt
```

### "No module named 'janus'"
Run tests from project root:
```bash
cd /path/to/Janus
./run_tests.sh
```

### Tests hang or timeout
Increase timeout:
```bash
python run_tests.py --timeout 30
```

### Too many test failures
Check you're on the correct platform and have dependencies:
```bash
# Install base dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt
```

### "pyautogui not available"
This is expected on Linux/CI. UI automation tests will be skipped or fail. These tests require:
- macOS (for AppleScript integration)
- Display server (for pyautogui)

## Writing Tests

### Test File Structure
```python
"""
Description of what this test file covers
"""
import unittest
from janus.module import ClassToTest


class TestClassName(unittest.TestCase):
    """Test cases for ClassName"""

    def setUp(self):
        """Set up test fixtures"""
        self.instance = ClassToTest()

    def tearDown(self):
        """Clean up after tests"""
        pass

    def test_feature_description(self):
        """Test that feature works correctly"""
        result = self.instance.method()
        self.assertEqual(result, expected_value)


if __name__ == '__main__':
    unittest.main()
```

### Test Best Practices
1. **One assertion per test** (when possible)
2. **Descriptive test names** (`test_parse_open_app_french`)
3. **Use setUp/tearDown** for fixtures
4. **Mock external dependencies** (filesystem, network)
5. **Test edge cases** (empty input, None, invalid data)

### Using Mocks
```python
from unittest.mock import Mock, patch, MagicMock

# Mock a function
@patch('janus.module.function_name')
def test_with_mock(self, mock_func):
    mock_func.return_value = "mocked"
    result = my_function()
    self.assertEqual(result, "mocked")
    mock_func.assert_called_once()

# Mock a class
mock_obj = Mock()
mock_obj.method.return_value = 42
```

## Platform-Specific Considerations

### Linux/CI
- ✅ Can run unit tests
- ✅ Can run logic tests
- ❌ Cannot run UI tests
- ❌ Cannot run macOS-specific tests (AppleScript, TTS)

### macOS (Target Platform)
- ✅ Can run all tests
- ✅ UI tests work with display
- ✅ Platform-specific features available
- May need permissions (Accessibility, Screen Recording)

## Performance

### Full Test Suite
- **Time**: ~78 seconds
- **Can be reduced**: Use `--fast` for parallel execution

### Individual Test Files
- **Parser tests**: ~0.23 seconds
- **Config tests**: ~0.1 seconds
- **Most unit tests**: < 1 second

## Test Coverage

Generate coverage report:
```bash
python run_tests.py --coverage
```

View HTML report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Additional Resources

- **TEST_ANALYSIS.md** - Detailed test suite analysis
- **conftest.py** - Pytest configuration and fixtures
- **pytest.ini** - Pytest settings and markers

## Contact

For questions or issues with tests:
1. Check TEST_ANALYSIS.md for known issues
2. Open an issue on GitHub
3. Check CI logs for failures

## Summary

✅ **1406 tests passing** - Core functionality works
⚠️ **135 tests failing** - Mostly environment-specific
⏭️ **421 tests skipped** - Platform/dependency specific

The test suite provides excellent coverage of core features and ensures code quality. Most failures are expected on non-macOS platforms or when optional dependencies are missing.
