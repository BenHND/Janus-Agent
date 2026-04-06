"""
Example: Conversation Mode

This example demonstrates multi-turn dialogue with context carryover,
clarification questions, and implicit reference resolution.

Run with:
    python examples/example_conversation_mode.py
"""
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core import MemoryEngine, Settings, JanusPipeline
from janus.runtime.core.settings import DatabaseSettings


def print_result(result, clarification=None):
    """Pretty print execution result"""
    if clarification:
        print(f"\n❓ {clarification}")
        if result.intent and result.intent.parameters.get("options"):
            options = result.intent.parameters["options"]
            for i, option in enumerate(options, 1):
                print(f"   {i}. {option}")
        return

    if result.success:
        print("✓ Command executed successfully")
        for action_result in result.action_results:
            print(f"  - {action_result.action_type}: {action_result.message}")
    else:
        print("✗ Command failed")
        if result.error:
            print(f"  Error: {result.error.message}")


def example_multi_turn_conversation():
    """Example: Multi-turn conversation with context carryover"""
    print("=" * 60)
    print("Example 1: Multi-turn conversation")
    print("=" * 60)

    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "conversation_example.db"

        # Initialize pipeline
        settings = Settings(config_path=None)
        settings.database.path = str(db_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(settings, memory, enable_llm_reasoning=False)

        print(f"Session ID: {pipeline.session_id}\n")

        # Turn 1: Open app
        print("You: 'Open Chrome'")
        result, clarification = pipeline.process_command_with_conversation(
            "Open Chrome", mock_execution=True
        )
        print_result(result, clarification)

        # Turn 2: Navigate (uses context)
        print("\nYou: 'Go to github.com'")
        result, clarification = pipeline.process_command_with_conversation(
            "Go to github.com", mock_execution=True
        )
        print_result(result, clarification)

        # Turn 3: Implicit reference
        print("\nYou: 'Refresh it'")
        result, clarification = pipeline.process_command_with_conversation(
            "Refresh it", mock_execution=True
        )
        print_result(result, clarification)

        print("\n✓ Conversation context maintained across 3 turns")


def example_clarification_question():
    """Example: Clarification question handling"""
    print("\n" + "=" * 60)
    print("Example 2: Clarification questions")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "clarification_example.db"

        settings = Settings(config_path=None)
        settings.database.path = str(db_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(settings, memory)

        # Ambiguous command
        print("\nYou: 'Open chrome'")
        result, clarification = pipeline.process_command_with_conversation(
            "Open chrome", mock_execution=True
        )
        print_result(result, clarification)

        if clarification:
            # Simulate user response
            print("\nYou: '1' (selecting first option)")
            result2, clarification2 = pipeline.process_command_with_conversation(
                "1", mock_execution=True
            )
            print_result(result2, clarification2)


def example_implicit_references():
    """Example: Implicit reference resolution"""
    print("\n" + "=" * 60)
    print("Example 3: Implicit reference resolution")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "references_example.db"

        settings = Settings(config_path=None)
        settings.database.path = str(db_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(settings, memory)

        # Build context
        print("\nYou: 'Open file main.py'")
        result, _ = pipeline.process_command_with_conversation(
            "Open file main.py", mock_execution=True
        )
        print_result(result)

        # Use implicit reference
        print("\nYou: 'Save it' (referring to main.py)")
        result, _ = pipeline.process_command_with_conversation("Save it", mock_execution=True)
        print_result(result)

        print("\nYou: 'Close that' (referring to main.py)")
        result, _ = pipeline.process_command_with_conversation("Close that", mock_execution=True)
        print_result(result)


def example_conversation_context():
    """Example: Conversation context summary"""
    print("\n" + "=" * 60)
    print("Example 4: Conversation context tracking")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "context_example.db"

        settings = Settings(config_path=None)
        settings.database.path = str(db_path)
        memory = MemoryEngine(settings.database)
        pipeline = JanusPipeline(settings, memory)

        # Execute several commands
        commands = [
            "Open Chrome",
            "Go to github.com",
            "Open VSCode",
            "Open file test.py",
        ]

        print("\nExecuting commands to build context:")
        for cmd in commands:
            print(f"  - {cmd}")
            pipeline.process_command_with_conversation(cmd, mock_execution=True)

        # Get conversation context
        conversation = pipeline.conversation_manager.get_active_conversation(pipeline.session_id)
        if conversation:
            context = conversation.get_context_summary()

            print("\nConversation Context:")
            print(f"  Turn count: {context['turn_count']}")
            print(f"  State: {context['state']}")
            print(f"  Last commands: {context['last_commands']}")
            print(f"  Recent entities: {context['recent_entities']}")


def main():
    """Run all examples"""
    print("\nConversation Mode Examples")
    print("=" * 60)

    try:
        example_multi_turn_conversation()
        example_clarification_question()
        example_implicit_references()
        example_conversation_context()

        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
