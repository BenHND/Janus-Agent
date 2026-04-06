#!/usr/bin/env python3
"""
Example demonstrating multi-session memory features

This example shows:
1. Creating multiple sessions with commands
2. Automatic context loading from recent sessions
3. Finding related sessions
4. Using session analytics
5. Exporting and importing sessions

Run this to see multi-session memory in action!
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core.contracts import Intent
from janus.runtime.core import MemoryEngine
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import DatabaseSettings, Settings


def demo_multi_session_memory():
    """Demonstrate multi-session memory features"""

    print("\n" + "=" * 70)
    print("MULTI-SESSION MEMORY DEMO")
    print("=" * 70 + "\n")

    # Setup
    print("1. Setting up memory service...")
    settings = Settings()
    settings.database = DatabaseSettings(path="demo_memory.db", enable_wal=True)
    memory = MemoryEngine(settings.database)

    # Create first session - Chrome browsing
    print("\n2. Creating Session 1: Chrome Browsing")
    session1 = memory.create_session()

    chrome_commands = [
        ("open chrome", "navigate_url", {"url": "https://github.com"}),
        ("go to example site", "navigate_url", {"url": "https://example.com"}),
        ("open new tab", "browser_action", {"action": "new_tab"}),
        ("close tab", "browser_action", {"action": "close_tab"}),
    ]

    for i, (cmd, intent_action, params) in enumerate(chrome_commands):
        memory.store_command(
            session_id=session1,
            request_id=f"s1_req_{i}",
            raw_command=cmd,
            intent=Intent(
                action=intent_action, confidence=0.95, parameters=params, raw_command=cmd
            ),
        )
        memory.log_execution(
            session_id=session1,
            request_id=f"s1_req_{i}",
            action=intent_action,
            status="success",
            duration_ms=100 + i * 10,
        )

    print(f"   Session ID: {session1[:12]}...")
    print(f"   Added {len(chrome_commands)} commands")

    # Create second session - App management
    print("\n3. Creating Session 2: App Management")
    session2 = memory.create_session()

    app_commands = [
        ("open vscode", "open_app", {"app_name": "VSCode"}),
        ("open terminal", "open_app", {"app_name": "Terminal"}),
        ("close vscode", "close_app", {"app_name": "VSCode"}),
    ]

    for i, (cmd, intent_action, params) in enumerate(app_commands):
        memory.store_command(
            session_id=session2,
            request_id=f"s2_req_{i}",
            raw_command=cmd,
            intent=Intent(
                action=intent_action, confidence=0.92, parameters=params, raw_command=cmd
            ),
        )
        memory.log_execution(
            session_id=session2,
            request_id=f"s2_req_{i}",
            action=intent_action,
            status="success",
            duration_ms=120,
        )

    print(f"   Session ID: {session2[:12]}...")
    print(f"   Added {len(app_commands)} commands")

    # Create third session - Mixed (similar to session 1)
    print("\n4. Creating Session 3: Mixed Browsing & Apps")
    session3 = memory.create_session()

    mixed_commands = [
        ("open chrome", "navigate_url", {"url": "https://example.com"}),
        ("open vscode", "open_app", {"app_name": "VSCode"}),
        ("send message", "send_message", {"recipient": "John"}),
    ]

    for i, (cmd, intent_action, params) in enumerate(mixed_commands):
        memory.store_command(
            session_id=session3,
            request_id=f"s3_req_{i}",
            raw_command=cmd,
            intent=Intent(
                action=intent_action, confidence=0.90, parameters=params, raw_command=cmd
            ),
        )
        memory.log_execution(
            session_id=session3,
            request_id=f"s3_req_{i}",
            action=intent_action,
            status="success",
            duration_ms=110,
        )

    print(f"   Session ID: {session3[:12]}...")
    print(f"   Added {len(mixed_commands)} commands")

    # List all sessions
    print("\n5. Listing All Sessions:")
    print("-" * 70)
    sessions = memory.list_all_sessions()

    for session in sessions[-3:]:  # Show last 3
        print(
            f"   {session['session_id'][:12]}... - "
            f"Commands: {session['command_count']}, "
            f"Executions: {session['execution_count']}"
        )

    # Get session details
    print("\n6. Session 1 Details:")
    print("-" * 70)
    details = memory.get_session_details(session1)
    print(f"   Total Commands: {details['command_stats']['total_commands']}")
    print(f"   Unique Intents: {details['command_stats']['unique_intents']}")
    print(
        f"   Success Rate: {details['execution_stats']['successful']}/{details['execution_stats']['total_executions']}"
    )
    print(f"   Top Intents:")
    for intent in details["top_intents"][:3]:
        print(f"     - {intent['intent']}: {intent['count']} times")

    # Search sessions
    print("\n7. Searching Sessions for 'chrome':")
    print("-" * 70)
    results = memory.search_sessions("chrome")
    print(f"   Found {len(results)} session(s)")
    for result in results[:3]:
        print(
            f"   {result['session_id'][:12]}... - {result['matching_commands']} matching command(s)"
        )

    # Get analytics
    print("\n8. Overall Analytics:")
    print("-" * 70)
    analytics = memory.get_session_analytics()
    print(f"   Total Sessions: {analytics['total_sessions']}")
    print(f"   Total Commands: {analytics['total_commands']}")
    print(f"   Success Rate: {analytics['success_rate']}%")
    print(f"   Top Intents:")
    for intent in analytics["top_intents"][:5]:
        print(f"     - {intent['intent']}: {intent['count']} times")

    # Create new pipeline with context loading
    print("\n9. Creating New Pipeline with Context Loading:")
    print("-" * 70)
    pipeline = JanusPipeline(
        settings=settings,
        memory=memory,
        load_context_from_recent=True,  # Load context from recent sessions
    )

    print(f"   New Session ID: {pipeline.session_id[:12]}...")

    # Check loaded context
    context = memory.get_context(pipeline.session_id, limit=10)
    loaded_context = next((c for c in context if c["type"] == "loaded_recent_context"), None)

    if loaded_context:
        print(
            f"   Context loaded from {len(loaded_context['data']['source_sessions'])} recent session(s)"
        )
        print(f"   Loaded {loaded_context['data']['loaded_commands']} commands")
        print(f"   Recent intents: {', '.join(loaded_context['data']['recent_intents'][:5])}")

    # Find related sessions
    print("\n10. Finding Related Sessions:")
    print("-" * 70)
    related = pipeline.get_related_sessions(min_similarity=0.2)

    print(f"   Found {len(related)} related session(s)")
    for rel in related[:3]:
        print(f"   {rel['session_id'][:12]}... - {rel['similarity']*100:.1f}% similar")
        print(f"      Common intents: {', '.join(rel['common_intents'][:3])}")

    # Export session
    print("\n11. Exporting Session 1:")
    print("-" * 70)
    export_file = "demo_session_export.json"
    export_data = memory.export_session(session1)

    import json

    with open(export_file, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"   Exported to: {export_file}")
    print(f"   Commands: {len(export_data['commands'])}")
    print(f"   Execution Logs: {len(export_data['execution_logs'])}")
    print(f"   File size: {Path(export_file).stat().st_size} bytes")

    # Session summary
    print("\n12. Current Session Summary:")
    print("-" * 70)
    summary = pipeline.get_session_summary()
    print(f"   Session ID: {summary['session_id'][:12]}...")
    print(f"   Created: {summary['created_at']}")
    print(f"   Commands: {summary['command_stats']['total_commands']}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE!")
    print("=" * 70)
    print("\nTo explore more, use the Session Manager CLI:")
    print("  python -m janus.tools.session_manager_cli list")
    print("  python -m janus.tools.session_manager_cli analytics")
    print(f"  python -m janus.tools.session_manager_cli details {session1[:12]}")
    print("\nClean up with:")
    print("  rm demo_memory.db demo_session_export.json")
    print()


if __name__ == "__main__":
    try:
        demo_multi_session_memory()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
