"""
TICKET 5 Demo: Error Recovery and Replanning

This example demonstrates the resilient error recovery system that makes
the agent intelligent and capable of recovering from failures.

Features demonstrated:
1. Automatic retry on temporary errors (timeout, network)
2. Dynamic replanning when actions fail
3. Conditional execution based on system state
4. Comprehensive error logging and tracking
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import Mock

from janus.runtime.core.contracts import (
    ActionPlan,
    ActionResult,
    CommandError,
    ErrorType,
    ExecutionContext,
    Intent,
)
from janus.runtime.core import MemoryEngine
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import Settings


def demo_error_classification():
    """
    Demo 1: Error Classification and Recoverability

    Shows how errors are automatically classified and marked as recoverable or not.
    """
    print("=" * 70)
    print("Demo 1: Error Classification and Recoverability")
    print("=" * 70)

    # Example 1: Recoverable timeout error
    timeout_error = CommandError(
        error_type=ErrorType.TIMEOUT_ERROR, message="Request timeout after 30 seconds"
    )

    print("\n✅ Timeout Error:")
    print(f"   Type: {timeout_error.error_type.value}")
    print(f"   Recoverable: {timeout_error.recoverable}")
    print(f"   Message: {timeout_error.message}")
    print(f"   Response: {timeout_error.to_dict()}")

    # Example 2: Non-recoverable permission error
    permission_error = CommandError(
        error_type=ErrorType.PERMISSION_ERROR, message="Access denied to system resource"
    )

    print("\n❌ Permission Error:")
    print(f"   Type: {permission_error.error_type.value}")
    print(f"   Recoverable: {permission_error.recoverable}")
    print(f"   Message: {permission_error.message}")

    # Example 3: Recoverable network error
    network_error = CommandError(
        error_type=ErrorType.NETWORK_ERROR, message="Connection failed to remote server"
    )

    print("\n✅ Network Error:")
    print(f"   Type: {network_error.error_type.value}")
    print(f"   Recoverable: {network_error.recoverable}")
    print(f"   Message: {network_error.message}")

    print("\n💡 Recovery Strategy:")
    print("   - Timeout errors → Retry once")
    print("   - Network errors → Retry once")
    print("   - Permission errors → Stop immediately (cannot recover)")
    print()


def demo_action_result_with_retry():
    """
    Demo 2: ActionResult with Retry Information

    Shows how action results track retry attempts and error details.
    """
    print("=" * 70)
    print("Demo 2: ActionResult with Retry Information")
    print("=" * 70)

    # Simulate an action that succeeded after retry
    result = ActionResult(
        action_type="chrome.open_url",
        success=True,
        message="Successfully opened URL after retry",
        duration_ms=2500,
        retry_count=1,  # Succeeded on second attempt
    )

    print("\n✅ Successful Action (after retry):")
    print(f"   Action: {result.action_type}")
    print(f"   Success: {result.success}")
    print(f"   Retries: {result.retry_count}")
    print(f"   Duration: {result.duration_ms}ms")

    # Simulate a failed action with error details
    failed_result = ActionResult(
        action_type="vscode.open_file",
        success=False,
        message="File not found",
        error="File 'missing.py' does not exist",
        error_type=ErrorType.NOT_FOUND_ERROR,
        recoverable=True,
        duration_ms=150,
        retry_count=1,
    )

    print("\n❌ Failed Action (recoverable):")
    print(f"   Action: {failed_result.action_type}")
    print(f"   Error Type: {failed_result.error_type.value}")
    print(f"   Error: {failed_result.error}")
    print(f"   Recoverable: {failed_result.recoverable}")
    print(f"   Retries: {failed_result.retry_count}")

    result_dict = failed_result.to_dict()
    print(f"\n   Full Response: {result_dict}")
    print()


def demo_conditional_action_plan():
    """
    Demo 3: Conditional Action Plans

    Shows how to create plans with conditional execution based on system state.
    """
    print("=" * 70)
    print("Demo 3: Conditional Action Plans")
    print("=" * 70)

    # Create a plan with conditional step
    intent = Intent(
        action="open_browser", confidence=0.95, raw_command="Open Chrome and go to GitHub"
    )

    plan = ActionPlan(intent=intent)

    # Add conditional: Check if Chrome is open
    plan.add_conditional_step(
        condition="app_not_open('Chrome')",
        if_true=[
            {"module": "default", "action": "open_application", "args": {"app_name": "Chrome"}}
        ],
        if_false=[{"module": "chrome", "action": "switch_to_chrome"}],
        step_id="chrome_check",
    )

    # Add navigation step
    plan.add_step(module="chrome", action="open_url", args={"url": "https://github.com"})

    print("\n📋 Action Plan with Conditional:")
    print(f"   Intent: {plan.intent.action}")
    print(f"   Steps: {len(plan.steps)}")

    print("\n   Step 1 (Conditional):")
    print(f"      Condition: {plan.steps[0]['condition']}")
    print(f"      If True: Open Chrome")
    print(f"      If False: Switch to existing Chrome window")

    print("\n   Step 2 (Direct):")
    print(f"      Module: chrome")
    print(f"      Action: open_url")
    print(f"      Args: https://github.com")

    print("\n💡 Intelligent Behavior:")
    print("   - Checks if Chrome is already running")
    print("   - Opens app if not running")
    print("   - Switches to it if already running")
    print("   - Then navigates to URL")
    print()


def demo_retry_logic():
    """
    Demo 4: Retry Logic in Action

    Simulates retry logic for temporary failures.
    """
    print("=" * 70)
    print("Demo 4: Retry Logic in Action")
    print("=" * 70)

    print("\n📝 Scenario: Network request with temporary failure")
    print("   Attempt 1: Timeout (recoverable)")
    print("   Attempt 2: Success")

    # First attempt - timeout
    attempt_1 = ActionResult(
        action_type="api.fetch_data",
        success=False,
        error="Request timeout after 30s",
        error_type=ErrorType.TIMEOUT_ERROR,
        recoverable=True,
        duration_ms=30000,
        retry_count=0,
    )

    print(f"\n❌ Attempt 1:")
    print(f"   Success: {attempt_1.success}")
    print(f"   Error: {attempt_1.error}")
    print(f"   Recoverable: {attempt_1.recoverable}")
    print(f"   → Decision: Retry")

    # Second attempt - success
    attempt_2 = ActionResult(
        action_type="api.fetch_data",
        success=True,
        message="Data fetched successfully",
        duration_ms=1500,
        retry_count=1,
        data={"records": 150, "status": "complete"},
    )

    print(f"\n✅ Attempt 2 (Retry):")
    print(f"   Success: {attempt_2.success}")
    print(f"   Message: {attempt_2.message}")
    print(f"   Duration: {attempt_2.duration_ms}ms")
    print(f"   Total Retries: {attempt_2.retry_count}")

    print("\n💡 Retry Rules:")
    print("   - Maximum 1 retry for temporary errors")
    print("   - No infinite loops")
    print("   - Only retry on recoverable errors (timeout, network, etc.)")
    print("   - Never retry permission or parse errors")
    print()


def demo_replanning_flow():
    """
    Demo 5: Dynamic Replanning

    Shows how the system generates alternative plans when actions fail.
    """
    print("=" * 70)
    print("Demo 5: Dynamic Replanning")
    print("=" * 70)

    print("\n📝 Scenario: File operation failure with replanning")

    # Original plan
    print("\n🎯 Original Plan:")
    print("   Step 1: vscode.open_file('config.json')")
    print("   Step 2: vscode.edit_content()")
    print("   Step 3: vscode.save_file()")

    # Step 1 fails
    print("\n❌ Step 1 Failed:")
    print("   Error: File 'config.json' not found")
    print("   Error Type: NOT_FOUND_ERROR")
    print("   Recoverable: True")

    # Replanning triggered
    print("\n🔄 Replanning Triggered:")
    print("   Analyzing failure...")
    print("   Generating alternative approach...")

    # Alternative plan
    print("\n✨ Alternative Plan Generated:")
    print("   Step 1: finder.search_files('config.json')")
    print("   Step 2: finder.get_file_location()")
    print("   Step 3: vscode.open_file(<found_path>)")
    print("   Step 4: vscode.edit_content()")
    print("   Step 5: vscode.save_file()")

    print("\n   Explanation: File not in expected location, searching system")

    print("\n💡 Replanning Features:")
    print("   - Automatic when action fails after retries")
    print("   - Uses LLM reasoner for intelligent alternatives")
    print("   - Receives full execution context")
    print("   - Logs explanation for debugging")
    print()


def demo_execution_context():
    """
    Demo 6: Execution Context and Output Propagation

    Shows how outputs flow between steps and inform replanning.
    """
    print("=" * 70)
    print("Demo 6: Execution Context and Output Propagation")
    print("=" * 70)

    context = ExecutionContext()

    print("\n📝 Multi-step execution with context:")

    # Step 1: Extract data
    print("\n   Step 1: chrome.extract_page_text()")
    context.store_output("Homepage content about API v2.0", "step_1")
    print(f"      Output: '{context.last_output}'")
    print(f"      Stored as: step_1")

    # Step 2: Summarize (uses previous output)
    print("\n   Step 2: llm.summarize(input_from='last_output')")
    summary = "API version 2.0 documentation"
    context.store_output(summary, "step_2")
    print(f"      Input: {context.resolve_input('last_output')[:50]}...")
    print(f"      Output: '{summary}'")

    # Step 3: Conditional based on output
    print("\n   Step 3: Conditional check")
    condition = "output_contains('2.0')"
    print(f"      Condition: {condition}")
    print(f"      Last output: '{context.last_output}'")
    print(f"      Result: True (contains '2.0')")

    print("\n💡 Context Features:")
    print("   - Tracks all step outputs")
    print("   - Enables input_from references")
    print("   - Used for conditional evaluation")
    print("   - Passed to replanner on failure")
    print()


def demo_comprehensive_error_response():
    """
    Demo 7: Complete Error Response Format

    Shows the standardized error response format.
    """
    print("=" * 70)
    print("Demo 7: Complete Error Response Format")
    print("=" * 70)

    error = CommandError(
        error_type=ErrorType.ELEMENT_NOT_FOUND,
        message="Button 'Submit' not found on page",
        details={
            "selector": "#submit-button",
            "page_url": "https://example.com/form",
            "retry_attempted": True,
        },
    )

    response = error.to_dict()

    print("\n📋 Standardized Error Response:")
    print(
        f"""
    {{
        "status": "{response['status']}",
        "error_type": "{response['error_type']}",
        "message": "{response['message']}",
        "recoverable": {response['recoverable']},
        "details": {{
            "selector": "{response['details']['selector']}",
            "page_url": "{response['details']['page_url']}",
            "retry_attempted": {response['details']['retry_attempted']}
        }},
        "timestamp": "{response['timestamp']}"
    }}
    """
    )

    print("\n💡 Response Format Benefits:")
    print("   - Consistent structure across all errors")
    print("   - Clear recoverability indication")
    print("   - Detailed context in 'details' field")
    print("   - Enables automated error handling")
    print()


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 70)
    print("TICKET 5: ERROR RECOVERY & REPLANNING DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo showcases the resilient error recovery system that makes")
    print("the agent intelligent and capable of self-correction.\n")

    demos = [
        ("Error Classification", demo_error_classification),
        ("ActionResult with Retry", demo_action_result_with_retry),
        ("Conditional Plans", demo_conditional_action_plan),
        ("Retry Logic", demo_retry_logic),
        ("Dynamic Replanning", demo_replanning_flow),
        ("Execution Context", demo_execution_context),
        ("Error Response Format", demo_comprehensive_error_response),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        if i > 1:
            input("\nPress Enter to continue to next demo...")
        demo_func()

    print("=" * 70)
    print("✅ All Demonstrations Complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. ✅ Automatic error classification and recoverability detection")
    print("  2. ✅ Smart retry for temporary failures (1 retry)")
    print("  3. ✅ Dynamic replanning with LLM-powered alternatives")
    print("  4. ✅ Conditional execution based on system state")
    print("  5. ✅ Comprehensive logging and error tracking")
    print("  6. ✅ Context propagation between steps")
    print("  7. ✅ Standardized error response format")
    print("\nThe agent is now RESILIENT and INTELLIGENT! 🎉")
    print()


if __name__ == "__main__":
    main()
