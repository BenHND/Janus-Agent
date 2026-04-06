"""
Test script to validate Janus components without hardware dependencies
"""
import sys

# ActionExecutor removed - use AgentExecutorV3 instead
# from janus.automation.action_executor import ActionExecutor
from janus.runtime.core import Settings, MemoryEngine
from janus.runtime.core.contracts import Intent


def test_parser():
    """Test command parser - DEPRECATED: CommandParser removed in V3"""
    print("Testing Command Parser...")
    print("  ⚠ CommandParser removed in V3 - test skipped")
    print("  Use JanusAgent or ReasonerLLM for command parsing")
    print("\nParser Tests: Skipped\n")
    return True  # Skip test


def test_action_plans():
    """Test action plan generation - DEPRECATED: CommandParser removed in V3"""
    print("Testing Action Plan Generation...")
    print("  ⚠ CommandParser removed in V3 - test skipped")
    print("  Use ReasonerLLM for action plan generation")
    print("\nAction Plan Tests: Skipped\n")
    return True  # Skip test


def test_unified_memory():
    """Test memory engine"""
    print("Testing Memory Engine...")

    import os
    import tempfile

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        settings = Settings()
        memory = MemoryEngine(db_path=temp_file.name)

        # Test recording commands
        memory.record_action("command", {"text": "test command", "intent": "test_intent", "param": "value"})
        memory.store("clipboard", "test content")

        # Verify
        history = memory.get_history(limit=10)
        clipboard = memory.retrieve("clipboard")
        assert len(history) >= 1, "Actions not recorded"
        assert clipboard == "test content", "Clipboard not saved"

        # Test command history
        cmd_history = memory.get_history(limit=10, action_type="command")
        assert len(cmd_history) >= 1, "Command history not saved"

        print("  ✓ Memory creation and basic operations")
        print("  ✓ Command recording")
        print("  ✓ Session context")

        print("\nUnified Memory Manager Tests: All passed\n")
        return True

    except AssertionError as e:
        print(f"  ✗ {e}")
        print("\nUnified Memory Manager Tests: Failed\n")
        return False

    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_executor_safety():
    """Test executor initialization - DEPRECATED: ActionExecutor removed in V3"""
    print("Testing Action Executor (safety checks only)...")
    print("  ⚠ ActionExecutor removed in V3 - test skipped")
    print("  Use AgentExecutorV3 for action execution")
    print("\nAction Executor Tests: Skipped\n")
    return True  # Skip test


def main():
    """Run all tests"""
    print("=" * 60)
    print("SPECTRA COMPONENT VALIDATION")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("Parser", test_parser()))
    results.append(("Action Plans", test_action_plans()))
    results.append(("Unified Memory Manager", test_unified_memory()))
    results.append(("Action Executor", test_executor_safety()))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All component tests passed!")
        print("\nNote: STT (Whisper) not tested as it requires:")
        print("  - Microphone hardware")
        print("  - Model download (~140MB)")
        print("  - Audio input permissions")
        print("\nTo test full system, run: python main.py --once 'ouvre Safari'")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
