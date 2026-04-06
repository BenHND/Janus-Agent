"""
Example usage of new UI components for TICKET-012
Demonstrates logs viewer, statistics panel, and dashboard
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from janus.persistence.action_history import ActionHistory


def example_logs_viewer():
    """Example: Show logs viewer"""
    print("Opening Logs Viewer...")
    print("This displays logs with filtering capabilities.")

    try:
        from janus.ui.logs_viewer import show_logs_viewer

        # Show logs viewer (will open in a window)
        show_logs_viewer()
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure tkinter is installed on your system.")


def example_stats_panel():
    """Example: Show statistics panel"""
    print("Opening Statistics Panel...")
    print("This displays detailed usage statistics and analytics.")

    try:
        from janus.ui.stats_panel import show_stats_panel

        # Create action history with sample data
        action_history = ActionHistory("janus_data.db")

        # Show stats panel
        show_stats_panel(action_history=action_history)
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure tkinter is installed on your system.")


def example_dashboard():
    """Example: Show main dashboard"""
    print("Opening Main Dashboard...")
    print("This displays the unified dashboard with all features.")

    try:
        from janus.ui.dashboard import show_dashboard

        # Create action history with sample data
        action_history = ActionHistory("janus_data.db")

        # Show dashboard
        show_dashboard(action_history=action_history)
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure tkinter is installed on your system.")


def example_config_ui_with_shortcuts():
    """Example: Show configuration UI with shortcuts"""
    print("Opening Configuration UI...")
    print("This displays the configuration interface with shortcuts and theme settings.")

    try:
        from janus.ui.config_ui import ConfigUI

        # Create config UI
        config_ui = ConfigUI(config_path="config.json")

        # Show the UI
        config_ui.show()
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure tkinter is installed on your system.")


def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample action history data...")

    action_history = ActionHistory("janus_data.db")

    # Add sample actions
    actions = [
        ("click", {"x": 100, "y": 200}, "success", 120, "chrome"),
        ("type_text", {"text": "Hello World"}, "success", 150, "vscode"),
        ("open_app", {"app": "Chrome"}, "success", 200, "finder"),
        ("click", {"x": 300, "y": 400}, "failed", 80, "chrome"),
        ("copy", {"text": "sample text"}, "success", 50, "clipboard"),
        ("paste", {}, "success", 60, "clipboard"),
        ("type_text", {"text": "print('hello')"}, "success", 180, "vscode"),
        ("click", {"x": 150, "y": 250}, "success", 110, "chrome"),
    ]

    for action_type, data, status, duration, module in actions:
        error = "Test error" if status == "failed" else None
        action_history.record_action(
            action_type=action_type,
            action_data=data,
            status=status,
            duration_ms=duration,
            module=module,
            error=error,
        )

    print(f"Created {len(actions)} sample actions.")
    return action_history


def main():
    """Main example menu"""
    print("=" * 60)
    print("TICKET-012: Complete User Interface - Examples")
    print("=" * 60)
    print()
    print("Choose an example to run:")
    print("1. Logs Viewer")
    print("2. Statistics Panel")
    print("3. Main Dashboard")
    print("4. Configuration UI (with shortcuts and theme)")
    print("5. Create sample data first (recommended)")
    print("0. Exit")
    print()

    choice = input("Enter your choice (0-5): ").strip()

    if choice == "1":
        example_logs_viewer()
    elif choice == "2":
        example_stats_panel()
    elif choice == "3":
        example_dashboard()
    elif choice == "4":
        example_config_ui_with_shortcuts()
    elif choice == "5":
        action_history = create_sample_data()
        print("\nSample data created! Now you can run examples 2 or 3.")
        print("\nStatistics summary:")
        stats = action_history.get_statistics()
        print(f"  Total actions: {stats.get('total_actions', 0)}")
        print(f"  Success: {stats.get('by_status', {}).get('success', 0)}")
        print(f"  Failed: {stats.get('by_status', {}).get('failed', 0)}")
        print(f"  Avg duration: {stats.get('avg_duration_ms', 0)}ms")
    elif choice == "0":
        print("Exiting...")
        return
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
