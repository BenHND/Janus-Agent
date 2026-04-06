# How to Use the Baseline E2E Tests During Refactoring

## Overview

The baseline E2E tests (TICKET-PRE-AUDIT-000) are your safety net during architectural refactoring. This guide explains how to use them effectively to ensure no functionality is lost during code changes.

## The Golden Master Testing Workflow

### Phase 1: Before You Start Refactoring

**Step 1: Verify Current State**
```bash
# Run the baseline tests
./run_baseline_tests.sh
```

**Expected Result**: ✅ All tests should PASS (or SKIP on non-macOS)

If tests fail at this point:
- ❌ Do NOT proceed with refactoring
- Fix the existing issues first
- Ensure the agent works correctly before changing code
- Re-run tests until they pass

**Step 2: Document Baseline**
```bash
# Save test output for reference
./run_baseline_tests.sh > baseline_test_results_BEFORE.txt
```

This creates a record of the working state before changes.

---

### Phase 2: During Refactoring

**After Each Significant Change:**

1. **Run tests frequently**
   ```bash
   ./run_baseline_tests.sh
   ```

2. **If tests PASS**: ✅ Continue refactoring
   - Your changes haven't broken core functionality
   - Safe to make more changes

3. **If tests FAIL**: ⚠️ STOP IMMEDIATELY
   - Your changes broke something
   - Review the test output to see what failed
   - Options:
     - **Fix the regression** (recommended)
     - **Revert the breaking change**
     - **Update tests if behavior intentionally changed** (rare)

**Example Workflow:**
```bash
# 1. Make a code change
vim janus/core/some_module.py

# 2. Run baseline tests
./run_baseline_tests.sh

# 3a. If PASS: commit and continue
git commit -m "Refactor module X - baseline tests pass"

# 3b. If FAIL: fix or revert
git diff  # Review what you changed
# Fix the issue or:
git restore janus/core/some_module.py  # Revert if needed
```

---

### Phase 3: After Refactoring

**Step 1: Final Verification**
```bash
# Run the baseline tests one more time
./run_baseline_tests.sh
```

**Expected Result**: ✅ All tests should PASS (same as before)

**Step 2: Compare with Baseline**
```bash
# Save final test results
./run_baseline_tests.sh > baseline_test_results_AFTER.txt

# Compare (optional)
diff baseline_test_results_BEFORE.txt baseline_test_results_AFTER.txt
```

The results should be identical (or only differ in timestamps).

**Step 3: Final Checks**

Before merging:
- ✅ All baseline tests pass
- ✅ No new test failures introduced
- ✅ Behavior matches pre-refactoring state
- ✅ Code is cleaner/better organized

If all checks pass: **Safe to merge! 🎉**

---

## Understanding Test Output

### Success Output
```
✓ BASELINE TESTS PASSED

All critical scenarios validated:
  ✓ Scenario A: System capability (open app)
  ✓ Scenario B: Web capability (browser navigation)
  ✓ Scenario C: Text editing capability

Safe to proceed with architectural changes.
```

**Meaning**: All core functionality works correctly. Refactoring is safe.

---

### Failure Output
```
✗ BASELINE TESTS FAILED

One or more critical scenarios failed.
DO NOT proceed with architectural changes until these pass.
```

**Meaning**: Something broke. Review test output for details.

**Common Failure Patterns:**

1. **Process Not Running**
   ```
   FAILURE: Calculator should be running after command execution.
   ```
   → Agent failed to launch the application

2. **Browser URL Incorrect**
   ```
   FAILURE: Browser URL should contain 'example.com', but got: 'about:blank'
   ```
   → Agent opened browser but didn't navigate

3. **Timeout/Hang**
   → Agent is stuck or commands aren't executing

---

## Debugging Failed Tests

### Step 1: Read the Test Output
The test output shows:
- Which scenario failed
- What was expected
- What actually happened

### Step 2: Run Tests with Debug Output
```bash
# Show all output (including logs)
./run_baseline_tests.sh -s

# Or use pytest directly with verbose logging
pytest tests/e2e/test_baseline_capabilities.py -m "e2e and critical" -v -s
```

### Step 3: Run Individual Scenarios
```bash
# Test only Scenario A
pytest tests/e2e/test_baseline_capabilities.py::TestBaselineCapabilities::test_scenario_a_open_system_app -v -s

# Test only Scenario B
pytest tests/e2e/test_baseline_capabilities.py::TestBaselineCapabilities::test_scenario_b_web_navigation -v -s

# Test only Scenario C
pytest tests/e2e/test_baseline_capabilities.py::TestBaselineCapabilities::test_scenario_c_text_editing -v -s
```

### Step 4: Manual Testing
If automated tests fail, try the command manually:
```bash
# Start Janus
python main.py

# Say or type the failing command
# Example: "Ouvre la Calculatrice"

# Observe what happens
```

### Step 5: Check Agent Logs
```bash
# View recent logs
tail -f logs/janus.log

# Or check specific log entries
grep "ERROR\|FAIL" logs/janus.log
```

---

## When to Update Tests

**RARELY!** These tests define expected behavior. Only update them if:

1. **Intentional Behavior Change**
   - You deliberately changed how a feature works
   - Document the change clearly
   - Get approval before updating tests

2. **Test Bug**
   - The test itself has a bug (not the agent)
   - Fix the test, not the behavior

**DO NOT update tests just to make them pass!**

---

## Advanced Usage

### Run Tests in CI/CD
```yaml
# Example GitHub Actions workflow
- name: Run Baseline E2E Tests
  run: ./run_baseline_tests.sh
  if: runner.os == 'macOS'
```

### Run Tests on Schedule
```bash
# Add to crontab for nightly testing
0 2 * * * cd /path/to/Janus && ./run_baseline_tests.sh >> baseline_test_log.txt 2>&1
```

### Integration with Git Hooks
```bash
# .git/hooks/pre-push
#!/bin/bash
echo "Running baseline tests before push..."
./run_baseline_tests.sh
if [ $? -ne 0 ]; then
    echo "Baseline tests failed! Push aborted."
    exit 1
fi
```

---

## Troubleshooting

### Tests are Skipped (Linux/Windows)
**Cause**: E2E tests require macOS  
**Solution**: Tests will skip automatically. This is expected behavior.

### Tests Hang or Timeout
**Cause**: Agent is waiting for user input or stuck  
**Solution**: 
- Check if any apps are showing dialogs
- Increase timeout in test code
- Check system resources

### Process Detection Fails
**Cause**: Process name doesn't match or app didn't launch  
**Solution**:
- Verify app name is correct (case-sensitive)
- Check if app is installed
- Try launching app manually

### Browser URL Verification Fails
**Cause**: Accessibility permissions or no tabs open  
**Solution**:
- Grant accessibility permissions to Terminal/IDE
- Check System Preferences → Security & Privacy → Accessibility
- Partial success still counts (browser launched)

---

## Summary Checklist

### Before Refactoring:
- [ ] Run baseline tests
- [ ] All tests pass
- [ ] Document baseline state

### During Refactoring:
- [ ] Run tests after each significant change
- [ ] Stop if tests fail
- [ ] Fix regressions immediately

### After Refactoring:
- [ ] Run final baseline tests
- [ ] All tests pass (same as before)
- [ ] Behavior is preserved
- [ ] Safe to merge

---

## Key Principles

1. **Trust the Tests**: If they pass, you haven't broken anything critical
2. **Stop on Failure**: Don't ignore failing tests
3. **Fix, Don't Skip**: Resolve issues rather than disabling tests
4. **Document Changes**: If you must change tests, explain why
5. **Run Often**: Catch regressions early

---

**Remember**: These tests are your safety net. They protect against regressions and give you confidence that refactoring didn't break core functionality. Use them wisely! 🛡️
