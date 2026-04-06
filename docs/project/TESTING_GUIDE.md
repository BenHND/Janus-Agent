# Testing Guide for Code Improvement Issue 04

## Overview

This document provides testing instructions for validating the clean architecture implementation on 2 Mac systems.

## What Was Changed

### 1. Clean Adapter Architecture
- **Added**: SlackAdapter with clean implementation (no coords/sleeps/OCR)
- **Verified**: All 5 adapters (Chrome, VSCode, Terminal, Finder, Slack) follow clean principles
- **Updated**: Executor intent mapping to include Slack actions

### 2. Code Cleanup
- **Removed**: 20+ phase example files (examples/examples_phase*.py)
- **Removed**: Legacy run_phase*.py scripts
- **Removed**: State JSON files (clipboard_history.json, context_memory.json, session_memory.json)
- **Cleaned**: workflow_checkpoints/ directory

### 3. Documentation Updates
- **Updated**: README with clean architecture and modern examples
- **Simplified**: Getting Started to just `python main.py`
- **Added**: Comprehensive architecture section with modern patterns

### 4. Test Coverage
- **Created**: tests/test_capabilities_e2e.py with 14 comprehensive tests
- **Validated**: Clean principles (no coords/sleeps/OCR in adapters)
- **Verified**: All 26 tests pass (14 new + 12 existing)

## Key Scenarios to Test on Mac

### Scenario 1: Browser Navigation
```bash
python main.py --unified --once "open github.com"
```
**Expected**: Chrome opens and navigates to GitHub

### Scenario 2: Code Editor
```bash
python main.py --unified --once "open file main.py"
```
**Expected**: VSCode opens main.py

### Scenario 3: Terminal Command
```bash
python main.py --unified --once "run command ls -la"
```
**Expected**: Terminal executes ls -la and shows output

### Scenario 4: Finder Operations
```bash
python main.py --unified --once "open folder Documents"
```
**Expected**: Finder opens Documents folder

### Scenario 5: Slack Messaging (requires Slack app)
```bash
python main.py --unified --once "send message Hello to general"
```
**Expected**: Slack sends message to #general channel

### Scenario 6: Multi-App Workflow
```bash
python main.py --unified --once "open github.com then open main.py then run ls"
```
**Expected**: All three actions execute in sequence

### Scenario 7-10: Combined Tests
Run tests programmatically:
```bash
python -m unittest tests.test_capabilities_e2e -v
```
**Expected**: All 14 tests pass

## Testing Checklist

### Mac 1 Testing
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run basic test: `python main.py --help`
- [ ] Test Scenario 1: Browser Navigation
- [ ] Test Scenario 2: Code Editor
- [ ] Test Scenario 3: Terminal Command
- [ ] Test Scenario 4: Finder Operations
- [ ] Test Scenario 5: Slack (if available)
- [ ] Test Scenario 6: Multi-App Workflow
- [ ] Run E2E tests: `python -m unittest tests.test_capabilities_e2e -v`
- [ ] Verify all tests pass (14/14)

### Mac 2 Testing
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run basic test: `python main.py --help`
- [ ] Test Scenario 1: Browser Navigation
- [ ] Test Scenario 2: Code Editor
- [ ] Test Scenario 3: Terminal Command
- [ ] Test Scenario 4: Finder Operations
- [ ] Test Scenario 5: Slack (if available)
- [ ] Test Scenario 6: Multi-App Workflow
- [ ] Run E2E tests: `python -m unittest tests.test_capabilities_e2e -v`
- [ ] Verify all tests pass (14/14)

## Expected Results

### Test Pass Rate
- **Target**: 10/10 scenarios pass on both Macs
- **Minimum**: All 14 E2E tests pass (100%)

### Clean Principles Validation
The test suite automatically validates:
- ✅ No hardcoded coordinates in adapter code
- ✅ No arbitrary time.sleep() calls (only configurable delays)
- ✅ No OCR dependencies in adapters (handled by executor fallback)

### File Structure Validation
- ✅ No "phase*" folders in root or examples/
- ✅ No run_phase*.py scripts
- ✅ No state JSON files (clipboard_history.json, etc.)
- ✅ workflow_checkpoints/ is empty (except .gitkeep)

## Troubleshooting

### "Application not installed"
- Install the required app (Chrome, VSCode, Slack)
- Or skip that specific test scenario

### "Permission denied"
- Grant Accessibility permissions to Terminal in System Preferences
- System Preferences → Security & Privacy → Accessibility

### Tests fail with "pyautogui not available"
- This is expected in CI/CD
- On Mac, tests should work with actual GUI

### Whisper model download is slow
- First run downloads model (~140MB for base)
- Use `--model tiny` for faster download

## Success Criteria

✅ **All 14 E2E tests pass on both Macs**
✅ **Key scenarios (1-6) work manually on both Macs**
✅ **Clean principles validated by automated tests**
✅ **No phase* files or legacy scripts remain**
✅ **Documentation is coherent (Getting Started = python main.py)**

## Notes

- Tests use `dry_run=True` for CI/CD compatibility
- On actual Mac hardware, adapters will execute real actions
- Slack tests require Slack app to be installed and logged in
- Some tests may need app focus/permissions on first run

## Contact

For issues or questions, please comment on the PR:
https://github.com/BenHND/Janus/pull/[PR_NUMBER]
