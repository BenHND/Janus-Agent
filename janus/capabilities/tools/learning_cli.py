"""
Command-line tool for managing Janus's learning system.

Provides utilities to:
- View learned corrections and heuristics
- Export/import learning data
- View performance metrics
- Manage learning profiles
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from janus.learning.learning_cache import LearningCache
from janus.learning.learning_manager import LearningManager


def format_dict(data: dict, indent: int = 0) -> str:
    """Format dictionary for pretty printing"""
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(format_dict(value, indent + 1))
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def cmd_status(args):
    """Show learning system status"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    status = manager.get_learning_status()

    print("=" * 70)
    print("SPECTRA LEARNING SYSTEM STATUS")
    print("=" * 70)
    print()
    print(f"Profile: {status.get('profile')}")
    print(f"Session Active: {status.get('session_active')}")
    print(f"Current Session: {status.get('current_session_id', 'None')}")
    print()
    print("Statistics:")
    print(f"  Total Actions: {status.get('total_actions', 0):,}")
    print(f"  Total Corrections: {status.get('total_corrections', 0):,}")
    print(f"  Learning Updates: {status.get('learning_updates', 0):,}")
    print(f"  Active Heuristics: {status.get('heuristics_count', 0)}")
    print()
    print("Configuration:")
    print(f"  Auto-Update: {'Enabled' if status.get('auto_update_enabled') else 'Disabled'}")
    print(f"  Last Update: {status.get('last_heuristic_update', 'Never')}")
    print(f"  Hours Since Update: {status.get('hours_since_last_update', 0):.1f}")
    print()


def cmd_corrections(args):
    """Show user corrections"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    summary = manager.get_correction_summary(days=args.days)

    print("=" * 70)
    print(f"USER CORRECTIONS (Last {args.days} days)")
    print("=" * 70)
    print()
    print(f"Total Corrections: {summary.get('total_corrections', 0)}")
    print(f"Patterns Tracked: {summary.get('patterns_tracked', 0)}")
    print(f"Preferences Tracked: {summary.get('preferences_tracked', 0)}")
    print()

    if summary.get("corrections_by_type"):
        print("Corrections by Type:")
        for action_type, count in summary.get("corrections_by_type", {}).items():
            print(f"  {action_type}: {count}")
        print()


def cmd_heuristics(args):
    """Show learned heuristics"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    heuristics = manager.heuristic_updater.get_heuristics_summary()

    print("=" * 70)
    print("LEARNED HEURISTICS")
    print("=" * 70)
    print()

    # Wait times
    wait_times = heuristics.get("wait_times", {})
    if wait_times:
        print("Wait Times (ms):")
        for action_type, wait_ms in sorted(wait_times.items()):
            print(f"  {action_type}: {wait_ms}")
        print()

    # Retry counts
    retry_counts = heuristics.get("retry_counts", {})
    if retry_counts:
        print("Retry Counts:")
        for action_type, retries in sorted(retry_counts.items()):
            print(f"  {action_type}: {retries}")
        print()

    # Success probabilities
    success_probs = heuristics.get("success_probabilities", {})
    if success_probs:
        print("Success Probabilities:")
        for action_type, prob in sorted(success_probs.items()):
            print(f"  {action_type}: {prob:.1%}")
        print()

    print(f"Last Updated: {heuristics.get('last_updated', 'Never')}")
    print()


def cmd_performance(args):
    """Show performance metrics"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    performance = manager.get_performance_summary(days=args.days)

    print("=" * 70)
    print(f"PERFORMANCE METRICS (Last {args.days} days)")
    print("=" * 70)
    print()

    overall = performance.get("overall_performance", {})
    if overall:
        print("Overall Performance:")
        print(f"  Success Rate: {overall.get('overall_success_rate', 0):.1f}%")
        print(f"  Total Actions: {overall.get('total_actions', 0):,}")
        print(f"  Successful: {overall.get('successful_actions', 0):,}")
        print(f"  Failed: {overall.get('failed_actions', 0):,}")
        print()

    improvements = performance.get("improvements", {})
    if improvements:
        print("Improvements:")
        for metric, value in improvements.items():
            print(f"  {metric}: {value}")
        print()


def cmd_export(args):
    """Export learning data to JSON"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    output_path = args.output or f"learning_export_{args.profile}.json"

    success = manager.export_heuristics(output_path)

    if success:
        print(f"✓ Learning data exported successfully to: {output_path}")
    else:
        print(f"✗ Failed to export learning data")
        sys.exit(1)


def cmd_import(args):
    """Import learning data from JSON"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    if not Path(args.input).exists():
        print(f"✗ File not found: {args.input}")
        sys.exit(1)

    success = manager.import_heuristics(args.input)

    if success:
        print(f"✓ Learning data imported successfully from: {args.input}")
    else:
        print(f"✗ Failed to import learning data")
        sys.exit(1)


def cmd_update(args):
    """Manually trigger heuristics update"""
    manager = LearningManager(
        db_path=args.db_path, cache_path=args.cache_path, profile_name=args.profile
    )

    print(f"Updating heuristics using {args.days} days of data...")

    updates = manager.update_all_heuristics(days=args.days)

    print()
    print("=" * 70)
    print("HEURISTICS UPDATE RESULTS")
    print("=" * 70)
    print()

    if updates.get("wait_times"):
        print("Wait Times Updated:")
        for action_type, update_info in updates["wait_times"].items():
            old = update_info.get("old", "N/A")
            new = update_info.get("new", "N/A")
            print(f"  {action_type}: {old}ms → {new}ms")
        print()

    if updates.get("retry_counts"):
        print("Retry Counts Updated:")
        for action_type, update_info in updates["retry_counts"].items():
            old = update_info.get("old", "N/A")
            new = update_info.get("new", "N/A")
            print(f"  {action_type}: {old} → {new}")
        print()

    if not updates:
        print("No updates performed (insufficient data)")
    else:
        print(f"✓ Heuristics updated successfully ({len(updates)} categories)")
    print()


def cmd_profiles(args):
    """List available learning profiles"""
    cache = LearningCache(cache_path=args.cache_path)

    profiles = cache.list_profiles()

    print("=" * 70)
    print("AVAILABLE LEARNING PROFILES")
    print("=" * 70)
    print()

    if not profiles:
        print("No profiles found.")
    else:
        for profile_name in profiles:
            cache.switch_profile(profile_name)
            summary = cache.get_cache_summary()

            print(f"Profile: {profile_name}")
            print(f"  Created: {summary.get('created_at', 'Unknown')}")
            print(f"  Last Updated: {summary.get('last_updated', 'Unknown')}")
            print(f"  Heuristics: {summary.get('heuristics_count', 0)}")
            print(f"  Preferences: {summary.get('preferences_count', 0)}")
            stats = summary.get("statistics", {})
            print(f"  Actions: {stats.get('total_actions', 0):,}")
            print(f"  Corrections: {stats.get('total_corrections', 0):,}")
            print()


def main():
    """Main entry point for learning CLI"""
    parser = argparse.ArgumentParser(
        description="Janus Learning System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View learning system status
  python learning_cli.py status

  # View corrections from last 7 days
  python learning_cli.py corrections --days 7

  # View learned heuristics
  python learning_cli.py heuristics

  # Export learning data
  python learning_cli.py export -o my_learning_data.json

  # Import learning data
  python learning_cli.py import -i my_learning_data.json

  # Update heuristics manually
  python learning_cli.py update --days 14

  # List all profiles
  python learning_cli.py profiles
        """,
    )

    # Global arguments
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

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show learning system status")

    # Corrections command
    corrections_parser = subparsers.add_parser("corrections", help="Show user corrections")
    corrections_parser.add_argument(
        "--days", type=int, default=30, help="Days to analyze (default: 30)"
    )

    # Heuristics command
    subparsers.add_parser("heuristics", help="Show learned heuristics")

    # Performance command
    performance_parser = subparsers.add_parser("performance", help="Show performance metrics")
    performance_parser.add_argument(
        "--days", type=int, default=30, help="Days to analyze (default: 30)"
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export learning data")
    export_parser.add_argument("-o", "--output", help="Output file path")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import learning data")
    import_parser.add_argument("-i", "--input", required=True, help="Input file path")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update heuristics")
    update_parser.add_argument(
        "--days", type=int, default=7, help="Days of data to analyze (default: 7)"
    )

    # Profiles command
    subparsers.add_parser("profiles", help="List available profiles")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handler
    handlers = {
        "status": cmd_status,
        "corrections": cmd_corrections,
        "heuristics": cmd_heuristics,
        "performance": cmd_performance,
        "export": cmd_export,
        "import": cmd_import,
        "update": cmd_update,
        "profiles": cmd_profiles,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
