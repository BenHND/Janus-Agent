# E2E Baseline Tests - Golden Master Testing

## Overview

This directory contains the **critical baseline tests** for the Janus agent. These tests serve as a "golden master" that defines the expected behavior of the agent across refactoring and architectural changes.

**CRITICAL RULE**: These tests MUST pass before AND after any architectural changes. If they fail after refactoring, the changes MUST NOT be merged.

## Purpose (TICKET-PRE-AUDIT-000)

These tests implement "Golden Master Testing" - a black box testing approach where:

- **Input**: Natural language command (e.g., "Ouvre Safari")
- **Output**: Verifiable system state (e.g., Safari process is running)

We test **WHAT** the agent does, not **HOW** it does it.

## Test Scenarios

### 1. Scenario A: System Capability
**Command**: "Ouvre la Calculatrice"  
**Verification**: 
- Calculator process is present in system process list
- Process remains stable

### 2. Scenario B: Web Capability  
**Command**: "Ouvre Safari et va sur example.com"  
**Verification**:
- Safari process is running
- Current URL contains "example.com"

### 3. Scenario C: Text Editing Capability
**Command**: "Ouvre TextEdit et écris 'TEST_VALIDATION_123'"  
**Verification**:
- TextEdit process is running
- Window contains the test string (if accessibility available)

## Running the Tests

### Run all baseline tests:
```bash
pytest tests/e2e/test_baseline_capabilities.py -v
```

### Run only critical E2E tests:
```bash
pytest -m "e2e and critical" -v
```

### Run with detailed logging:
```bash
pytest tests/e2e/test_baseline_capabilities.py -v -s
```

## Requirements

- **Platform**: macOS (tests are automatically skipped on other platforms)
- **Dependencies**: 
  - pytest>=7.4.0
  - pytest-asyncio>=0.21.0
  - Janus core dependencies

- **Permissions**: Some tests may require:
  - Accessibility permissions for window content verification
  - Automation permissions for browser control

## Test Structure

```
tests/e2e/
├── __init__.py
├── README.md                      # This file
├── system_info_helper.py          # System verification utilities
└── test_baseline_capabilities.py  # Main baseline tests
```

## Definition of Done

Before any architectural refactoring:

1. ✅ Run: `pytest tests/e2e/test_baseline_capabilities.py`
2. ✅ All tests PASS (green)
3. ✅ Proceed with refactoring

During refactoring:

1. ⚠️ If tests FAIL (red) → STOP
2. ⚠️ Fix the regression
3. ⚠️ Re-run tests until green

After refactoring:

1. ✅ Run: `pytest tests/e2e/test_baseline_capabilities.py`
2. ✅ All tests PASS (green)
3. ✅ Safe to merge

## Implementation Notes

### SystemInfo Helper
The `system_info_helper.py` module provides utilities for verifying actual system state:

- `is_process_running(name)`: Check if a process is running
- `kill_process(name)`: Terminate a process
- `get_browser_url(browser)`: Get current URL from Safari/Chrome
- `get_active_window_text()`: Get text from active window
- `get_frontmost_app()`: Get name of frontmost application

These utilities use platform-specific APIs (AppleScript on macOS) to provide "ground truth" verification independent of the agent's internal state.

### Test Design Principles

1. **Black Box**: Tests don't care about internal implementation
2. **Ground Truth**: Verify actual system state, not agent messages
3. **Minimal**: Only test core capabilities, not edge cases
4. **Stable**: Tests should be deterministic and reliable
5. **Fast**: Tests should complete in seconds, not minutes

## Troubleshooting

### Tests are skipped
- Check platform: E2E tests require macOS
- Check Python version: Requires Python 3.8+

### Process verification fails
- Ensure app names match platform (e.g., "Calculator" on macOS)
- Check process permissions

### URL verification fails
- Safari/Chrome may require accessibility permissions
- Check System Preferences → Security & Privacy → Accessibility

### Agent fails to execute commands
- Verify Janus is properly configured
- Check LLM backend is available
- Review agent logs for errors

## Future Enhancements

Potential additions (not required for baseline):

- **Scenario D**: File operations (create, move, delete)
- **Scenario E**: Complex multi-step workflows
- **Scenario F**: Error recovery and retry logic
- **Scenario G**: Voice input testing (STT integration)

## References

- **Ticket**: TICKET-PRE-AUDIT-000
- **Testing Strategy**: Golden Master Testing
- **Philosophy**: If it works now, it should work after refactoring
