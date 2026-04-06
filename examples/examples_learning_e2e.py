"""
End-to-End Learning Integration Demo
Demonstrates complete learning system with visual feedback
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.learning.learning_manager import LearningManager
from janus.runtime.core.contracts import Intent
from janus.legacy.parser.learning_command_parser import LearningCommandParser


def simulate_action_execution(action, duration_base=200):
    """
    Simulate action execution with random variation

    Args:
        action: Action to execute
        duration_base: Base duration in ms

    Returns:
        Tuple of (success, duration_ms)
    """
    import random

    # Simulate execution time with variation
    duration = duration_base + random.randint(-50, 100)

    # 90% success rate
    success = random.random() > 0.1

    # Simulate delay
    time.sleep(duration / 1000.0)

    return success, duration


def end_to_end_demo_console():
    """
    Console-based end-to-end demo
    Shows complete learning flow without UI
    """

    print("=" * 70)
    print("SPECTRA LEARNING - END-TO-END DEMO (Console Mode)")
    print("=" * 70)
    print()

    # Initialize learning system
    print("Initializing learning system...")
    learning_manager = LearningManager(
        db_path="e2e_demo_learning.db",
        cache_path="e2e_demo_cache.json",
        profile_name="e2e_demo",
        auto_update=True,
    )

    parser = LearningCommandParser(learning_manager=learning_manager, enable_learning=True)
    print("✓ Learning system ready\n")

    # Session 1: Initial Learning
    print("-" * 70)
    print("SESSION 1: Initial Learning Phase")
    print("-" * 70)

    session_id = parser.start_learning_session()
    print(f"Started session: {session_id}\n")

    commands_phase1 = [
        "ouvre Chrome",
        "clique sur le bouton",
        "copie le texte",
        "colle",
        "ouvre Firefox",
    ]

    for i, cmd_text in enumerate(commands_phase1, 1):
        print(f"[{i}/{len(commands_phase1)}] Parsing: '{cmd_text}'")

        # Parse command
        command = parser.parse(cmd_text)
        print(f"  Intent: {command.intent.value}")

        if command.intent != Intent.UNKNOWN:
            # Generate action plan
            actions = parser.generate_action_plan(command, apply_recommendations=True)

            for action in actions:
                action_type = action.get("action")
                print(f"  Executing: {action_type}")

                # Check for recommendations
                if action.get("recommended_wait_ms"):
                    print(f"    → Using learned wait time: {action['recommended_wait_ms']}ms")

                # Simulate execution
                success, duration = simulate_action_execution(action)

                # Record result
                parser.record_action_result(action=action, success=success, duration_ms=duration)

                status = "✓" if success else "✗"
                print(f"    {status} Result: {'Success' if success else 'Failed'} ({duration}ms)")

        print()

    # End session 1
    report1 = parser.end_learning_session()
    print("Session 1 Summary:")
    print(f"  Total actions: {report1['summary']['total_actions']}")
    print(f"  Success rate: {report1['summary']['success_rate']:.1f}%")
    print()

    # Session 2: With User Corrections
    print("-" * 70)
    print("SESSION 2: Learning from Corrections")
    print("-" * 70)

    session_id = parser.start_learning_session()
    print(f"Started session: {session_id}\n")

    # Parse a command
    print("Parsing: 'clique sur le bouton'")
    command = parser.parse("clique sur le bouton")

    # Simulate execution
    action = {"action": "click", "target": "button"}
    success, duration = simulate_action_execution(action)
    parser.record_action_result(action, success, duration)
    print(f"  Executed: click → {'Success' if success else 'Failed'}\n")

    # User says correction
    print("User correction: 'non, pas ça'")
    correction = parser.handle_user_correction(
        correction_text="non, pas ça",
        language="fr",
        alternative_action={"action": "click", "target": "other_button"},
    )

    if correction:
        print("  ✓ Correction recorded and learned")
        print(f"  Original action: {correction['original_action']['action_type']}")
    print()

    # Continue with more commands
    commands_phase2 = ["copie le texte", "va sur github.com", "clique sur login"]

    for cmd_text in commands_phase2:
        print(f"Parsing: '{cmd_text}'")
        command = parser.parse(cmd_text)

        if command.intent != Intent.UNKNOWN:
            actions = parser.generate_action_plan(command)

            for action in actions:
                success, duration = simulate_action_execution(action)
                parser.record_action_result(action, success, duration)
                print(f"  {action.get('action')} → {'✓' if success else '✗'}")

        print()

    # End session 2
    report2 = parser.end_learning_session()
    print("Session 2 Summary:")
    print(f"  Total actions: {report2['summary']['total_actions']}")
    print(f"  Success rate: {report2['summary']['success_rate']:.1f}%")
    print()

    # Session 3: Update Heuristics
    print("-" * 70)
    print("SESSION 3: Heuristic Updates")
    print("-" * 70)

    print("Updating heuristics based on feedback...")
    updates = parser.update_heuristics(days=1)

    if updates.get("wait_times"):
        print("\nWait time improvements:")
        for action_type, update_info in list(updates["wait_times"].items())[:5]:
            change = update_info["change_pct"]
            symbol = "↓" if change < 0 else "↑"
            print(
                f"  {action_type}: {update_info['old']}ms → {update_info['new']}ms ({symbol}{abs(change):.1f}%)"
            )
    else:
        print("  (Need more data for updates)")
    print()

    # Show overall metrics
    print("-" * 70)
    print("OVERALL LEARNING METRICS")
    print("-" * 70)

    metrics = parser.get_improvement_metrics(days=1)
    learning_status = metrics.get("learning_status", {})

    print(f"Total Actions: {learning_status.get('total_actions', 0)}")
    print(f"Total Corrections: {learning_status.get('total_corrections', 0)}")
    print(f"Learning Updates: {learning_status.get('learning_updates', 0)}")
    print(f"Active Heuristics: {learning_status.get('heuristics_count', 0)}")
    print()

    # Show success rates by action
    print("Success Rates by Intent:")
    for intent in [Intent.OPEN_APP, Intent.CLICK, Intent.COPY, Intent.PASTE]:
        rate = parser.get_success_rate(intent, days=1)
        if rate > 0:
            print(f"  {intent.value}: {rate:.1f}%")
    print()

    # Export learning data
    print("-" * 70)
    print("EXPORT LEARNING DATA")
    print("-" * 70)

    export_path = "e2e_demo_export.json"
    success = parser.export_learning_data(export_path)

    if success:
        print(f"✓ Learning data exported to: {export_path}")
        print("  This data can be shared or imported on another system")
    print()

    print("=" * 70)
    print("DEMO COMPLETED")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  1. Learning system automatically tracks all actions")
    print("  2. User corrections are recorded and applied")
    print("  3. Heuristics improve over time based on real data")
    print("  4. Performance metrics show learning effectiveness")
    print("  5. Data can be exported and shared")
    print()
    print("Next Steps:")
    print("  • Run with UI: python examples_learning_integration.py dashboard")
    print("  • View data: Check generated .db and .json files")
    print("  • Test import: Use exported data in new session")
    print()


def end_to_end_demo_with_overlay():
    """
    Demo with visual overlay feedback
    Requires tkinter
    """

    print("=" * 70)
    print("SPECTRA LEARNING - END-TO-END DEMO (With Visual Feedback)")
    print("=" * 70)
    print()

    try:
        from janus.ui.learning_overlay import LearningFeedbackIntegration, LearningOverlay

        # Initialize learning system
        learning_manager = LearningManager(
            db_path="e2e_demo_visual.db",
            cache_path="e2e_demo_visual_cache.json",
            profile_name="visual_demo",
        )

        parser = LearningCommandParser(learning_manager=learning_manager)

        # Create overlay integration
        overlay_integration = LearningFeedbackIntegration(learning_manager)

        print("Visual overlay will show learning feedback...")
        print("Watch for notifications in the corner of your screen!")
        print()

        # Start session
        session_id = parser.start_learning_session()
        overlay_integration.on_session_start()
        time.sleep(2)

        # Parse and execute commands with visual feedback
        commands = ["ouvre Chrome", "clique sur bouton", "copie le texte"]

        for cmd_text in commands:
            print(f"Executing: {cmd_text}")

            # Parse
            command = parser.parse(cmd_text)
            overlay_integration.on_command_parsed(command)
            time.sleep(2)

            # Execute
            if command.intent != Intent.UNKNOWN:
                actions = parser.generate_action_plan(command)

                for action in actions:
                    success, duration = simulate_action_execution(action)
                    action_type = action.get("action", "unknown")

                    parser.record_action_result(action, success, duration)
                    overlay_integration.on_action_executed(action_type, success, duration)

                    time.sleep(1)

        # Simulate correction
        print("\nSimulating user correction...")
        parser.handle_user_correction("non", "fr")
        overlay_integration.on_user_correction("click")
        time.sleep(3)

        # Update heuristics
        print("Updating heuristics...")
        updates = parser.update_heuristics(days=1)
        overlay_integration.on_heuristics_updated(updates)
        time.sleep(3)

        # End session
        parser.end_learning_session()

        print("\nDemo completed!")
        print("Visual feedback demonstrated successfully.")

    except ImportError as e:
        print(f"Error: Could not import UI components")
        print(f"Make sure tkinter is installed: {e}")
        print("\nFalling back to console mode...")
        print()
        end_to_end_demo_console()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "visual":
        # Visual mode with overlay
        end_to_end_demo_with_overlay()
    else:
        # Console mode
        end_to_end_demo_console()
