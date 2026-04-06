"""
Example: Multi-Module Action Plans with Context Propagation (TICKET 2)

This example demonstrates the new multi-module action plan feature that allows:
1. Executing multiple actions across multiple applications in a single command
2. Automatic output propagation between steps
3. Cross-module workflows (Chrome → LLM → VSCode)

Example scenario:
"Go to Chrome → open Wikipedia → extract text → summarize with LLM → open VSCode → paste result"
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from janus.runtime.core import (
    DeterministicPlanner,
    ExecutionContext,
    MemoryEngine,
    Settings,
    JanusPipeline,
)


def example_1_execution_context():
    """Example 1: Using ExecutionContext for output tracking"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: ExecutionContext - Output Tracking")
    print("=" * 60)

    context = ExecutionContext()

    # Simulate step outputs
    print("\nSimulating step execution:")

    print("  Step 1: Chrome opens URL and extracts page text")
    context.store_output("Wikipedia page content about AI...", "page_text")
    print(f"    → Stored as 'page_text'")

    print("\n  Step 2: LLM summarizes the text")
    context.store_output("AI is a field of computer science...", "summary")
    print(f"    → Stored as 'summary'")
    print(f"    → Also stored as 'last_output'")

    print("\n  Step 3: VSCode pastes the summary")
    print(f"    → Using last_output: '{context.last_output[:40]}...'")

    print("\n✓ Context propagation demonstrated!")
    print(f"  Total outputs stored: {len(context.outputs)}")
    print(f"  Available references: {list(context.outputs.keys())}")


def example_2_resolve_input_from():
    """Example 2: Resolving input_from references"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Resolving input_from References")
    print("=" * 60)

    context = ExecutionContext()

    # Store some outputs
    context.store_output("page content", "page_text")
    context.store_output("summary content", "summary")

    print("\nStored outputs:")
    print("  page_text: 'page content'")
    print("  summary: 'summary content'")

    # Test resolving input_from
    print("\nResolving arguments with input_from:")

    args1 = {"input_from": "page_text", "max_length": 100}
    resolved1 = context.resolve_args(args1)
    print(f"\n  Original:  {args1}")
    print(f"  Resolved:  {resolved1}")

    args2 = {"input_from": "last_output", "format": "markdown"}
    resolved2 = context.resolve_args(args2)
    print(f"\n  Original:  {args2}")
    print(f"  Resolved:  {resolved2}")

    print("\n✓ Input resolution demonstrated!")


def example_3_create_multi_module_plan():
    """Example 3: Creating a multi-module action plan"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Creating Multi-Module Action Plan")
    print("=" * 60)

    planner = DeterministicPlanner()

    # Define the workflow steps
    steps = [
        {
            "module": "chrome",
            "action": "open_url",
            "args": {"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"},
        },
        {"module": "chrome", "action": "extract_page_text", "step_id": "wiki_text"},
        {
            "module": "llm",
            "action": "summarize",
            "args": {"input_from": "wiki_text", "max_length": 200},
            "step_id": "summary",
        },
        {"module": "vscode", "action": "open_file", "args": {"path": "ai_summary.txt"}},
        {"module": "vscode", "action": "paste", "args": {"input_from": "summary"}},
    ]

    # Create the plan
    plan = planner.create_multi_module_plan("Summarize Wikipedia AI article into VSCode", steps)

    print("\nPlan created successfully!")
    print(f"  Intent: {plan.intent.action}")
    print(f"  Description: {plan.intent.parameters['description']}")
    print(f"  Is multi-module: {plan.is_multi_module()}")
    print(f"  Number of steps: {len(plan.steps)}")

    print("\nStep breakdown:")
    for i, step in enumerate(plan.steps, 1):
        print(f"\n  Step {i}: {step['module']}.{step['action']}")
        if step.get("step_id"):
            print(f"    Step ID: {step['step_id']}")
        if step["args"]:
            print(f"    Args: {step['args']}")

    print("\n✓ Multi-module plan created!")


def example_4_execute_multi_module_plan():
    """Example 4: Executing a multi-module plan (mock)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Executing Multi-Module Plan (Mock)")
    print("=" * 60)

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        # Create minimal config
        config_path = os.path.join(temp_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[database]
path = janus.db

[logging]
level = INFO
enable_structured = true
log_to_database = true
"""
            )

        # Initialize pipeline
        settings = Settings(config_path=config_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(
            settings,
            memory,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )

        # Create a multi-module plan
        planner = DeterministicPlanner()
        steps = [
            {"module": "chrome", "action": "open_url", "args": {"url": "https://example.com"}},
            {"module": "chrome", "action": "extract_page_text", "step_id": "page_text"},
            {"module": "llm", "action": "summarize", "args": {"input_from": "page_text"}},
        ]

        plan = planner.create_multi_module_plan("Extract and summarize webpage", steps)

        print("\nExecuting plan (mock mode)...")

        # Execute with mock
        result = pipeline._execute_plan(plan, "example-request-id", mock_execution=True)

        print("\n✓ Execution completed:")
        print(f"  Success: {result.success}")
        print(f"  Steps executed: {len(result.action_results)}")
        print(f"  Session ID: {result.session_id}")
        print(f"  Request ID: {result.request_id}")

        print("\nStep results:")
        for i, action_result in enumerate(result.action_results, 1):
            print(f"\n  Step {i}: {action_result.action_type}")
            print(f"    Success: {action_result.success}")
            print(f"    Message: {action_result.message}")
            print(f"    Duration: {action_result.duration_ms}ms")
            if action_result.output:
                print(f"    Output: {action_result.output}")


def example_5_complex_workflow():
    """Example 5: Complex multi-module workflow"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Complex Multi-Module Workflow")
    print("=" * 60)

    planner = DeterministicPlanner()

    # More complex scenario:
    # 1. Open multiple URLs in Chrome
    # 2. Extract text from each
    # 3. Combine and summarize with LLM
    # 4. Save to file in VSCode
    steps = [
        # Open first page
        {"module": "chrome", "action": "open_url", "args": {"url": "https://example.com/page1"}},
        {"module": "chrome", "action": "extract_page_text", "step_id": "page1_text"},
        # Open second page
        {"module": "chrome", "action": "open_url", "args": {"url": "https://example.com/page2"}},
        {"module": "chrome", "action": "extract_page_text", "step_id": "page2_text"},
        # Combine and summarize (LLM would handle multiple inputs)
        {
            "module": "llm",
            "action": "combine_and_summarize",
            "args": {"inputs": ["page1_text", "page2_text"], "style": "technical"},
            "step_id": "combined_summary",
        },
        # Save to VSCode
        {"module": "vscode", "action": "create_file", "args": {"path": "combined_summary.txt"}},
        {"module": "vscode", "action": "paste", "args": {"input_from": "combined_summary"}},
    ]

    plan = planner.create_multi_module_plan(
        "Extract and combine content from multiple pages", steps
    )

    print("\nComplex workflow plan created!")
    print(f"  Total steps: {len(plan.steps)}")
    print(f"  Modules involved: chrome, llm, vscode")

    print("\nWorkflow overview:")
    print("  1. Chrome: Open and extract page1")
    print("  2. Chrome: Open and extract page2")
    print("  3. LLM: Combine and summarize both texts")
    print("  4. VSCode: Create new file")
    print("  5. VSCode: Paste summary")

    print("\n✓ Complex workflow demonstrated!")


def example_6_backward_compatibility():
    """Example 6: Backward compatibility with legacy plans"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Backward Compatibility")
    print("=" * 60)

    planner = DeterministicPlanner()

    # Create a legacy plan (single-module)
    from janus.runtime.core import Intent

    intent = Intent(
        action="open_app",
        confidence=1.0,
        raw_command="open Chrome",
        parameters={"app_name": "Chrome"},
    )

    legacy_plan = planner.create_plan(intent)

    print("\nLegacy single-module plan:")
    print(f"  Is multi-module: {legacy_plan.is_multi_module()}")
    print(f"  Actions: {len(legacy_plan.actions)}")
    print(f"  Action type: {legacy_plan.actions[0]['type']}")

    # Create a multi-module plan
    steps = [{"module": "chrome", "action": "open_url", "args": {"url": "test"}}]
    multi_plan = planner.create_multi_module_plan("Test", steps)

    print("\nNew multi-module plan:")
    print(f"  Is multi-module: {multi_plan.is_multi_module()}")
    print(f"  Steps: {len(multi_plan.steps)}")

    print("\n✓ Both plan types are supported!")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("MULTI-MODULE ACTION PLAN EXAMPLES")
    print("TICKET 2 - Multi-Module & Context Propagation")
    print("=" * 60)

    try:
        example_1_execution_context()
        example_2_resolve_input_from()
        example_3_create_multi_module_plan()
        example_4_execute_multi_module_plan()
        example_5_complex_workflow()
        example_6_backward_compatibility()

        print("\n" + "=" * 60)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("  ✓ ExecutionContext for output tracking")
        print("  ✓ input_from reference resolution")
        print("  ✓ Multi-module plan creation")
        print("  ✓ Cross-module execution (Chrome → LLM → VSCode)")
        print("  ✓ Complex multi-step workflows")
        print("  ✓ Backward compatibility with legacy plans")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
