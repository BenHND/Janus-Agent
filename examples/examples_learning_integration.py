"""
Example demonstrating the complete learning module integration
Shows how to use LearningCommandParser and LearningDashboard
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.learning.learning_manager import LearningManager
from janus.runtime.core.contracts import Intent
from janus.legacy.parser.learning_command_parser import LearningCommandParser


def demonstrate_learning_integration():
    """Demonstrate the learning integration features"""

    print("=" * 70)
    print("SPECTRA LEARNING MODULE INTEGRATION DEMO")
    print("=" * 70)
    print()

    # 1. Initialize Learning System
    print("1. Initializing Learning System...")
    learning_manager = LearningManager(
        db_path="demo_learning.db",
        cache_path="demo_cache.json",
        profile_name="demo_user",
        auto_update=True,
    )

    parser = LearningCommandParser(learning_manager=learning_manager, enable_learning=True)
    print("   ✓ Learning system initialized")
    print()

    # 2. Start Learning Session
    print("2. Starting Learning Session...")
    session_id = parser.start_learning_session()
    print(f"   ✓ Session started: {session_id}")
    print()

    # 3. Parse Commands with Learning
    print("3. Parsing Commands with Learning Enhancement...")
    test_commands = [
        "ouvre Chrome",
        "va sur github.com",
        "clique sur le bouton",
        "copie le texte",
        "colle dans le champ",
    ]

    for cmd_text in test_commands:
        print(f"\n   Command: '{cmd_text}'")

        # Parse with learning
        command = parser.parse(cmd_text)

        print(f"   Intent: {command.intent.value}")
        print(f"   Confidence: {command.confidence:.2f}")

        if command.recommended_params:
            print(
                f"   Recommended wait time: {command.recommended_params.get('wait_time_ms', 'N/A')}ms"
            )
            print(f"   Recommended retries: {command.recommended_params.get('retry_count', 'N/A')}")

        # Generate action plan
        if command.intent != Intent.UNKNOWN:
            action_plan = parser.generate_action_plan(command, apply_recommendations=True)

            # Simulate action execution
            for action in action_plan:
                print(f"   Executing: {action.get('action')}")

                # Simulate success with some variation
                import random

                success = random.random() > 0.1  # 90% success rate
                duration_ms = random.randint(100, 500)

                # Record execution result
                parser.record_action_result(action=action, success=success, duration_ms=duration_ms)

                status = "✓ Success" if success else "✗ Failed"
                print(f"   {status} (took {duration_ms}ms)")

    print()

    # 4. Demonstrate User Correction
    print("4. Demonstrating User Correction...")
    print("   User says: 'non, pas ça'")

    correction = parser.handle_user_correction(
        correction_text="non, pas ça",
        language="fr",
        alternative_action={"action": "click", "target": "other_button"},
    )

    if correction:
        print("   ✓ Correction recorded and will improve future parsing")
    print()

    # 5. Show Learning Metrics
    print("5. Learning Metrics...")

    # Get success rate
    success_rate = parser.get_success_rate(days=1)
    print(f"   Overall Success Rate: {success_rate:.1f}%")

    # Get improvement metrics
    metrics = parser.get_improvement_metrics(days=1)
    learning_status = metrics.get("learning_status", {})

    print(f"   Total Actions: {learning_status.get('total_actions', 0)}")
    print(f"   Total Corrections: {learning_status.get('total_corrections', 0)}")
    print(f"   Learning Updates: {learning_status.get('learning_updates', 0)}")
    print()

    # 6. Update Heuristics
    print("6. Updating Heuristics...")
    updates = parser.update_heuristics(days=1)

    if updates.get("wait_times"):
        print("   ✓ Wait times updated:")
        for action_type, update_info in list(updates["wait_times"].items())[:3]:
            print(f"     - {action_type}: {update_info['old']}ms → {update_info['new']}ms")
    else:
        print("   (Not enough data for updates yet)")
    print()

    # 7. Export Learning Data
    print("7. Exporting Learning Data...")
    export_path = "demo_learning_export.json"
    success = parser.export_learning_data(export_path)

    if success:
        print(f"   ✓ Learning data exported to: {export_path}")
    print()

    # 8. End Session
    print("8. Ending Learning Session...")
    report = parser.end_learning_session()

    if report:
        summary = report.get("summary", {})
        print(f"   ✓ Session completed")
        print(f"   Total actions: {summary.get('total_actions', 0)}")
        print(f"   Successful: {summary.get('successful_actions', 0)}")
        print(f"   Failed: {summary.get('failed_actions', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    print()

    # 9. Show Learning Status
    print("9. Final Learning Status...")
    status = learning_manager.get_learning_status()

    print(f"   Profile: {status.get('profile')}")
    print(f"   Total actions recorded: {status.get('total_actions')}")
    print(f"   Active heuristics: {status.get('heuristics_count')}")
    print(f"   Auto-update: {'Enabled' if status.get('auto_update_enabled') else 'Disabled'}")
    print()

    print("=" * 70)
    print("DEMO COMPLETED")
    print("=" * 70)
    print()
    print("To view the learning dashboard, run:")
    print("  python -m janus.ui.learning_dashboard")
    print()


def demonstrate_learning_dashboard():
    """Demonstrate the learning dashboard UI"""

    print("=" * 70)
    print("LAUNCHING LEARNING DASHBOARD")
    print("=" * 70)
    print()
    print("The dashboard provides:")
    print("  • Overview of learning status")
    print("  • Corrections tracking")
    print("  • Heuristics management")
    print("  • Performance metrics")
    print("  • Recurring errors analysis")
    print("  • Export/Import functionality")
    print()

    try:
        from janus.ui.learning_dashboard import launch_learning_dashboard

        # Create learning manager with demo data
        learning_manager = LearningManager(
            db_path="demo_learning.db", cache_path="demo_cache.json", profile_name="demo_user"
        )

        print("Opening dashboard window...")
        print("(Close the window to exit)")
        print()

        launch_learning_dashboard(learning_manager)

    except ImportError as e:
        print(f"Error: Could not import dashboard UI")
        print(f"Make sure tkinter is installed: {e}")
    except Exception as e:
        print(f"Error launching dashboard: {e}")


def quick_test():
    """Quick test to verify everything works"""

    print("Running quick integration test...")

    try:
        # Test imports
        from janus.learning.learning_manager import LearningManager
        from janus.legacy.parser.learning_command_parser import LearningCommandParser

        # Test basic functionality
        parser = LearningCommandParser(enable_learning=True)
        command = parser.parse("ouvre Chrome")

        assert command.intent == Intent.OPEN_APP
        assert "app_name" in command.parameters

        print("✓ All imports successful")
        print("✓ Basic parsing works")
        print("✓ Learning integration functional")
        print()
        print("Integration test PASSED")

        return True

    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            quick_test()
        elif sys.argv[1] == "dashboard":
            # Launch dashboard
            demonstrate_learning_dashboard()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage:")
            print("  python examples_learning_integration.py          # Run demo")
            print("  python examples_learning_integration.py test     # Quick test")
            print("  python examples_learning_integration.py dashboard # Launch UI")
    else:
        # Full demo
        demonstrate_learning_integration()
