"""
Example: Unified Pipeline Usage
TICKET-MAC-02 - Pipeline Unification

This example demonstrates the unified JanusPipeline:
- NLU: Deterministic FR/EN intent recognition with validation
- Planner: Testable Intent→ActionPlan mapping
- Optional STT: Whisper+VAD for voice input
- Optional TTS: Voice feedback
- Optional LLM: Disambiguation support
- Optional Vision: Visual verification
- Optional Learning: Continuous improvement
- Clean architecture with no legacy code
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from janus.runtime.core import (
    DeterministicNLU,
    DeterministicPlanner,
    IntentValidationStatus,
    MemoryEngine,
    Settings,
    JanusPipeline,
)


def example_1_basic_nlu():
    """Example 1: Basic NLU usage"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Deterministic NLU")
    print("=" * 60)

    nlu = DeterministicNLU(enable_llm_disambiguation=False)

    # Test various commands
    commands = [
        "ouvre Safari",
        "open Chrome",
        "clique sur le bouton",
        "click on button",
        "copie ceci",
        "va sur github.com",
    ]

    for cmd in commands:
        validated = nlu.parse_command(cmd)

        print(f"\nCommand: '{cmd}'")
        print(f"  Intent: {validated.intent.action}")
        print(f"  Confidence: {validated.confidence:.2f}")
        print(f"  Status: {validated.validation_status.value}")
        print(f"  Valid: {validated.is_valid()}")
        if validated.intent.parameters:
            print(f"  Parameters: {validated.intent.parameters}")


def example_2_planner():
    """Example 2: Deterministic Planner usage"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Deterministic Planner")
    print("=" * 60)

    nlu = DeterministicNLU()
    planner = DeterministicPlanner()

    # Parse command
    validated = nlu.parse_command("ouvre Chrome")

    if validated.is_valid():
        # Create plan
        plan = planner.create_plan(validated.intent)

        print(f"\nCommand: 'ouvre Chrome'")
        print(f"Intent: {validated.intent.action}")
        print(f"\nPlan Details:")
        print(f"  Actions: {len(plan.actions)}")
        print(f"  Requires confirmation: {plan.requires_confirmation}")
        print(f"  Estimated duration: {plan.estimated_duration_ms}ms")

        print(f"\nActions:")
        for i, action in enumerate(plan.actions, 1):
            print(f"  {i}. Type: {action['type']}")
            print(f"     Module: {action.get('module', 'N/A')}")
            print(
                f"     Parameters: {dict((k, v) for k, v in action.items() if k not in ['type', 'module'])}"
            )


def example_3_complete_pipeline():
    """Example 3: Complete unified pipeline with mock execution"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Complete Unified Pipeline (JanusPipeline)")
    print("=" * 60)

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        # Create minimal config
        config_path = os.path.join(temp_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[audio]
sample_rate = 16000

[language]
default = fr

[database]
path = janus.db

[logging]
level = INFO
enable_structured = true
log_to_database = true
"""
            )

        # Initialize unified pipeline
        settings = Settings(config_path=config_path)
        memory = MemoryEngine(settings.database)

        # Create pipeline with all features disabled except core
        pipeline = JanusPipeline(
            settings,
            memory,
            enable_voice=False,  # No voice input for this example
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )

        # Test commands
        commands = [
            "ouvre Safari",
            "clique sur le bouton",
            "copie le texte",
            "colle ici",
        ]

        for cmd in commands:
            print(f"\n{'─' * 60}")
            print(f"Processing: '{cmd}'")
            print("─" * 60)

            # Process command (mock execution)
            result = pipeline.process_command(cmd, mock_execution=True)

            # Display results
            print(f"\n✓ Pipeline completed:")
            print(f"  Success: {result.success}")
            print(f"  Intent: {result.intent.action}")
            print(f"  Confidence: {result.intent.confidence:.2f}")
            print(f"  Session ID: {result.session_id}")
            print(f"  Request ID: {result.request_id}")
            print(f"  Total duration: {result.total_duration_ms}ms")
            print(f"  Actions executed: {len(result.action_results)}")

            for i, action_result in enumerate(result.action_results, 1):
                print(f"\n    Action {i}:")
                print(f"      Type: {action_result.action_type}")
                print(f"      Success: {action_result.success}")
                print(f"      Message: {action_result.message}")
                print(f"      Duration: {action_result.duration_ms}ms")


def example_4_error_handling():
    """Example 4: Error handling - clean error management"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Error Handling")
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
"""
            )

        # Initialize unified pipeline
        settings = Settings(config_path=config_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(settings, memory)

        # Test edge cases - should never raise exceptions
        test_cases = [
            ("", "Empty command"),
            ("   ", "Whitespace only"),
            ("xyzabc nonsense", "Unknown command"),
            ("ouvre", "Incomplete command"),
        ]

        for cmd, description in test_cases:
            print(f"\n{'─' * 60}")
            print(f"Test: {description}")
            print(f"Command: '{cmd}'")
            print("─" * 60)

            result = pipeline.process_command(cmd, mock_execution=True)

            print(f"✓ Pipeline completed gracefully")
            print(f"  Success: {result.success}")

            if result.error:
                print(f"  Error type: {result.error.error_type.value}")
                print(f"  Message: {result.error.message}")
            else:
                print(f"  Result: Command processed successfully")


def example_5_deterministic_behavior():
    """Example 5: Verify deterministic behavior"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Deterministic Behavior Verification")
    print("=" * 60)

    nlu = DeterministicNLU()
    planner = DeterministicPlanner()

    command = "ouvre Safari"

    print(f"\nCommand: '{command}'")
    print("\nProcessing 5 times to verify determinism:")

    results = []
    for i in range(5):
        # Parse
        validated = nlu.parse_command(command)

        # Plan
        if validated.is_valid():
            plan = planner.create_plan(validated.intent)

            results.append(
                {
                    "intent": validated.intent.action,
                    "confidence": validated.confidence,
                    "action_count": len(plan.actions),
                    "action_type": plan.actions[0]["type"],
                    "estimated_duration": plan.estimated_duration_ms,
                }
            )

    # Verify all results are identical
    first = results[0]
    all_same = all(r == first for r in results)

    print(f"\n  All results identical: {all_same}")
    print(f"\n  Result details:")
    print(f"    Intent: {first['intent']}")
    print(f"    Confidence: {first['confidence']}")
    print(f"    Actions: {first['action_count']}")
    print(f"    Action type: {first['action_type']}")
    print(f"    Estimated duration: {first['estimated_duration']}ms")

    if all_same:
        print("\n✓ Deterministic behavior verified!")
    else:
        print("\n✗ Non-deterministic behavior detected!")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("DETERMINISTIC VOICE PIPELINE EXAMPLES")
    print("Issue #03 - Code Improvement")
    print("=" * 60)

    try:
        example_1_basic_nlu()
        example_2_planner()
        example_3_complete_pipeline()
        example_4_error_handling()
        example_5_deterministic_behavior()

        print("\n" + "=" * 60)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
