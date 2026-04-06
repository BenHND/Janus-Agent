#!/usr/bin/env python3
"""
Launch the Janus Learning Dashboard UI.

This script provides a graphical interface for:
- Viewing learning system status
- Managing corrections and heuristics
- Monitoring performance metrics
- Exporting/importing learning data
"""

import sys
from pathlib import Path
from typing import NoReturn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.learning.learning_manager import LearningManager
from janus.ui.learning_dashboard import launch_learning_dashboard


def main() -> None:
    """Launch the learning dashboard"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Janus Learning Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Learning Dashboard provides a graphical interface to:
  • View learning system status and statistics
  • Browse user corrections
  • Inspect learned heuristics
  • Monitor performance metrics over time
  • View recurring errors
  • Export/import learning data

The dashboard auto-refreshes every 5 seconds by default.
        """,
    )

    parser.add_argument(
        "--db-path",
        default="janus_learning.db",
        help="Path to learning database (default: janus_learning.db)",
    )
    parser.add_argument(
        "--cache-path",
        default="learning_cache.json",
        help="Path to learning cache (default: learning_cache.json)",
    )
    parser.add_argument(
        "--profile", default="default", help="Learning profile name (default: default)"
    )
    parser.add_argument("--no-auto-refresh", action="store_true", help="Disable auto-refresh")
    parser.add_argument(
        "--refresh-interval",
        type=int,
        default=5000,
        help="Auto-refresh interval in milliseconds (default: 5000)",
    )

    args = parser.parse_args()

    try:
        # Create learning manager
        learning_manager = LearningManager(
            db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
        )

        print("=" * 70)
        print("SPECTRA LEARNING DASHBOARD")
        print("=" * 70)
        print()
        print(f"Profile: {args.profile}")
        print(f"Database: {args.db_path}")
        print(f"Cache: {args.cache_path}")
        print()
        print("Launching dashboard window...")
        print("(Close the window to exit)")
        print()

        # Launch dashboard
        from janus.ui.learning_dashboard import LearningDashboard

        dashboard = LearningDashboard(
            learning_manager=learning_manager,
            auto_refresh=not args.no_auto_refresh,
            refresh_interval_ms=args.refresh_interval,
        )
        dashboard.show()

    except ImportError as e:
        print(f"Error: Could not import required modules")
        print(f"Make sure tkinter is installed: {e}")
        print()
        print("On macOS, tkinter should be included with Python.")
        print("On Ubuntu/Debian: sudo apt-get install python3-tk")
        print("On Fedora: sudo dnf install python3-tkinter")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching dashboard: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
