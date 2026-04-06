#!/usr/bin/env python3
"""
Example demonstrating the unified memory management architecture

This shows how to use the new UnifiedMemoryManager for all memory operations.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core import Settings, UnifiedMemoryManager


def main():
    """Demonstrate unified memory management"""

    print("=" * 60)
    print("Unified Memory Management Demo")
    print("=" * 60)

    # Initialize unified memory manager
    print("\n1. Initializing UnifiedMemoryManager...")
    settings = Settings()
    memory = UnifiedMemoryManager(settings.database, unified_store_path="demo_unified.db")
    print(f"   ✓ Current session: {memory.get_current_session_id()}")

    # Record some commands
    print("\n2. Recording commands...")
    memory.record_command(
        command_text="open Safari",
        intent="open_app",
        parameters={"app_name": "Safari"},
        result={"status": "success", "duration_ms": 1200},
    )
    memory.record_command(
        command_text="navigate to GitHub",
        intent="navigate_url",
        parameters={"url": "https://github.com"},
        result={"status": "success", "duration_ms": 800},
    )
    print("   ✓ Recorded 2 commands")

    # Get command history
    print("\n3. Retrieving command history...")
    history = memory.get_command_history(limit=5)
    for cmd in history:
        print(f"   - {cmd.get('raw_command')} ({cmd.get('intent')})")

    # Track actions in session context
    print("\n4. Tracking session actions...")
    memory.record_click(150, 200, target="address bar")
    memory.record_copy("https://github.com/BenHND/Janus")
    print("   ✓ Recorded click and copy actions")

    # Reference resolution
    print("\n5. Testing reference resolution...")
    url = memory.resolve_reference("it")
    print(f"   'it' resolves to: {url}")

    # Get session summary
    print("\n6. Session summary...")
    summary = memory.get_session_context_summary()
    print(f"   - Total actions: {summary['total_actions']}")
    print(f"   - Session duration: {summary['session_duration_seconds']:.2f}s")
    print(f"   - Last command: {summary['last_command']}")
    print(f"   - Last copied: {summary['last_copied_content']}")

    # Clipboard operations
    print("\n7. Clipboard operations...")
    memory.record_copy("print('Hello, World!')", source="vscode")
    memory.record_copy("SELECT * FROM users", source="sql")

    clipboard_history = memory.get_clipboard_history(limit=5)
    print(f"   ✓ {len(clipboard_history)} entries in clipboard history")
    for i, entry in enumerate(clipboard_history[:3], 1):
        content = entry["content"][:50] + "..." if len(entry["content"]) > 50 else entry["content"]
        print(f"   {i}. {content} (from {entry.get('source', 'unknown')})")

    # Context snapshots
    print("\n8. Saving context snapshot...")
    snapshot = {
        "timestamp": "2025-11-13T22:00:00",
        "active_window": {"app": "Safari", "title": "GitHub"},
        "open_applications": [{"name": "Safari"}, {"name": "VSCode"}, {"name": "Terminal"}],
        "urls": [{"url": "https://github.com"}],
        "visible_text": ["Repository", "Issues", "Pull requests"],
        "performance_ms": 145.3,
    }
    snapshot_id = memory.save_context_snapshot(snapshot, "full")
    print(f"   ✓ Saved snapshot #{snapshot_id}")

    # Retrieve latest snapshot
    latest = memory.get_latest_snapshot()
    if latest:
        print(f"   ✓ Latest snapshot has {len(latest.get('open_applications', []))} applications")

    # File operations
    print("\n9. Recording file operations...")
    memory.record_file_operation("open", "/Users/test/document.txt", "success")
    memory.record_file_operation("save", "/Users/test/document.txt", "success")

    file_ops = memory.get_file_operations(limit=5)
    print(f"   ✓ {len(file_ops)} file operations recorded")

    # Browser tabs
    print("\n10. Recording browser tabs...")
    memory.record_browser_tab("https://github.com", "GitHub", "Safari", is_active=True)
    memory.record_browser_tab("https://stackoverflow.com", "Stack Overflow", "Safari")

    tabs = memory.get_browser_tabs(limit=5)
    print(f"   ✓ {len(tabs)} browser tabs recorded")

    # Multi-session operations
    print("\n11. Multi-session operations...")
    all_sessions = memory.list_all_sessions()
    print(f"   - Total sessions: {len(all_sessions)}")

    session_details = memory.get_session_details()
    if session_details:
        cmd_stats = session_details.get("command_stats", {})
        print(f"   - Commands in current session: {cmd_stats.get('total_commands', 0)}")

    # Storage statistics
    print("\n12. Storage statistics...")
    stats = memory.get_storage_stats()
    print(f"   - Current session: {stats['current_session_id']}")
    print(f"   - Session actions: {stats['session_actions']}")
    print(f"   - Clipboard entries: {stats.get('clipboard_entries', 0)}")
    print(f"   - Context snapshots: {stats.get('context_snapshots', 0)}")
    print(f"   - File operations: {stats.get('file_operations', 0)}")
    print(f"   - Browser tabs: {stats.get('browser_tabs', 0)}")
    print(f"   - Database size: {stats.get('db_size_mb', 0)} MB")

    # Analytics
    print("\n13. Session analytics...")
    analytics = memory.get_session_analytics()
    print(f"   - Total sessions: {analytics.get('total_sessions', 0)}")
    print(f"   - Total commands: {analytics.get('total_commands', 0)}")
    print(f"   - Success rate: {analytics.get('success_rate', 0)}%")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print("\nThe unified memory architecture provides:")
    print("  ✓ Single, clean API for all memory operations")
    print("  ✓ Integrated session context for command chaining")
    print("  ✓ Comprehensive persistence (sessions, commands, clipboard, files)")
    print("  ✓ Multi-session support and analytics")
    print("  ✓ Context snapshots for complex state tracking")
    print("\nSee docs/MEMORY_CONSOLIDATION_GUIDE.md for more information.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
