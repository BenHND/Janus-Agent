#!/usr/bin/env python3
"""
Example usage script for Janus voice agent
Demonstrates how to use Janus programmatically

Note: CommandParser has been removed in V3. Use JanusAgent or JanusPipeline 
for command processing via LLM reasoning.
"""

from janus.runtime.core import Settings, MemoryEngine


def example_session():
    """Example: Using memory engine"""
    print("\n" + "=" * 60)
    print("Example: Memory Engine")
    print("=" * 60)

    # Use memory engine
    settings = Settings()
    memory = MemoryEngine(db_path="example_session.db")

    # Record commands and actions
    print("\nRecording session activity...")
    memory.record_action("command", {"text": "ouvre Safari", "intent": "open_app", "app": "Safari"})
    memory.store("clipboard", "Hello World")
    memory.record_action("command", {"text": "copie", "intent": "copy"})

    # Retrieve state
    print("\nRetrieving session state...")
    history = memory.get_history(limit=5)
    print(f"  Total actions recorded: {len(history)}")
    print(f"  Last clipboard: {memory.retrieve('clipboard', default='(none)')}")

    # Get command history
    print("\nAction history:")
    for action in memory.get_history(limit=10, action_type="command"):
        print(f"  - {action.get('action_data', {}).get('text', 'unknown')} at {action.get('timestamp')}")


def example_workflow():
    """Example: Complete workflow simulation with memory"""
    print("\n" + "=" * 60)
    print("Example: Memory Workflow")
    print("=" * 60)

    settings = Settings()
    memory = MemoryEngine(db_path="example_workflow.db")

    # Simulate a workflow with manual recording
    workflow_steps = [
        ("open_app", {"app_name": "TextEdit"}, "ouvre TextEdit"),
        ("click", {}, "clique"),
        ("copy", {}, "copie le texte"),
        ("open_app", {"app_name": "Safari"}, "ouvre Safari"),
        ("paste", {}, "colle"),
    ]

    print("\nSimulating workflow:")
    for intent, params, cmd in workflow_steps:
        print(f"\n→ Voice command: '{cmd}'")
        print(f"  Intent: {intent}")

        # Record in memory based on intent
        action_data = {
            "text": cmd,
            "intent": intent,
            "parameters": params
        }
        memory.record_action("command", action_data)
        
        if intent == "open_app":
            app = params.get("app_name")
            print(f"  [Memory] Recorded command: open {app}")
        elif intent == "copy":
            memory.store("clipboard", "Sample text from screen")
            print(f"  [Memory] Recorded copy action")
        else:
            print(f"  [Memory] Recorded: {intent}")

    # Show final state
    print("\n" + "-" * 60)
    print("Final workflow state:")
    history = memory.get_history(limit=10)
    print(f"  Total actions: {len(history)}")
    print(f"  Last clipboard: {memory.retrieve('clipboard', default='(none)')}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SPECTRA - Example Usage")
    print("=" * 60)
    print("\nThis script demonstrates how to use Janus components")
    print("programmatically without requiring microphone or audio.")
    print()

    try:
        example_session()
        example_workflow()

        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        print("\nTo use Janus with voice input, run:")
        print("  python main.py")
        print()

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()
