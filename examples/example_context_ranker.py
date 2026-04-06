#!/usr/bin/env python3
"""
Example demonstrating Context Ranker functionality (TICKET A4).

This example shows how to use the new smart context loading system
with relevance scoring and temporal decay.
"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core import ContextRanker, Intent, Settings, UnifiedMemoryManager


def example_basic_ranking():
    """Example 1: Basic context ranking"""
    print("=" * 70)
    print("Example 1: Basic Context Ranking")
    print("=" * 70)

    # Create a ranker
    ranker = ContextRanker(decay_halflife_hours=24.0)

    # Create sample context items
    now = datetime.now()
    context_items = [
        {
            "type": "app",
            "data": {"app_name": "Chrome"},
            "timestamp": (now - timedelta(hours=2)).isoformat(),  # 2 hours old
        },
        {
            "type": "app",
            "data": {"app_name": "Chrome"},
            "timestamp": (now - timedelta(minutes=5)).isoformat(),  # 5 minutes old
        },
        {
            "type": "file",
            "data": {"file_path": "/home/user/document.txt"},
            "timestamp": (now - timedelta(minutes=10)).isoformat(),  # 10 minutes old
        },
        {
            "type": "clipboard",
            "data": {"content": "test text"},
            "timestamp": (now - timedelta(hours=1)).isoformat(),  # 1 hour old
        },
    ]

    # Current intent: open Chrome
    intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Chrome"})

    # Rank context items
    ranked_items = ranker.rank_context_items(context_items, intent, max_items=10)

    print(f"\nIntent: {intent.action} - {intent.parameters}")
    print(f"\nRanked context items (total: {len(ranked_items)}):")
    for i, (item, score) in enumerate(ranked_items, 1):
        print(f"\n{i}. Score: {score:.3f}")
        print(f"   Type: {item['type']}")
        print(f"   Data: {item['data']}")
        timestamp = item["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        age_minutes = (now - timestamp.replace(tzinfo=None)).total_seconds() / 60
        print(f"   Age: {age_minutes:.1f} minutes")


def example_temporal_decay():
    """Example 2: Temporal decay visualization"""
    print("\n" + "=" * 70)
    print("Example 2: Temporal Decay Visualization")
    print("=" * 70)

    ranker = ContextRanker(decay_halflife_hours=24.0)

    # Show decay at different time points
    time_points = [
        (0.5, "30 minutes"),
        (1.0, "1 hour"),
        (6.0, "6 hours"),
        (12.0, "12 hours"),
        (24.0, "24 hours (half-life)"),
        (48.0, "48 hours"),
        (72.0, "72 hours"),
        (168.0, "1 week"),
    ]

    print("\nTemporal decay multipliers:")
    print(f"{'Age':<25} {'Decay Multiplier':<20} {'Effective Weight':<20}")
    print("-" * 70)

    for hours, label in time_points:
        decay = ranker.apply_decay(hours)
        bar_length = int(decay * 40)
        bar = "█" * bar_length
        print(f"{label:<25} {decay:.4f} ({decay*100:.1f}%)      {bar}")


def example_memory_service_integration():
    """Example 3: Integration with MemoryEngine"""
    print("\n" + "=" * 70)
    print("Example 3: Memory Service Integration")
    print("=" * 70)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    try:
        # Initialize settings
        settings = Settings()
        settings.database.path = temp_db

        # Create memory manager
        memory_manager = UnifiedMemoryManager(settings.database)

        print(f"\nCreated session: {memory_manager.get_current_session_id()}")

        # Store some context
        print("\nStoring context items...")
        memory_manager.store_context("app", {"app_name": "Chrome", "action": "opened"})
        memory_manager.store_context(
            "file", {"file_path": "/home/user/project/main.py", "action": "edited"}
        )
        memory_manager.store_context("clipboard", {"content": "important code snippet"})
        memory_manager.store_context("browser", {"url": "https://github.com", "title": "GitHub"})

        print("✓ Stored 4 context items")

        # Load context with ranking
        intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Chrome"})

        print(f"\nLoading ranked context for intent: {intent.action}")
        ranked_context = memory_manager.load_recent_context_ranked(intent, max_items=10)

        print(f"\nRetrieved {len(ranked_context)} ranked context items:")
        for i, (item, score) in enumerate(ranked_context, 1):
            print(f"\n{i}. Score: {score:.3f}")
            print(f"   Type: {item['type']}")
            print(f"   Data: {item['data']}")

        # Demonstrate cleanup
        print("\n" + "-" * 70)
        print("Cleanup demonstration:")

        # Get current context count
        all_context = memory_manager.get_context(limit=100)
        print(f"Context items before cleanup: {len(all_context)}")

        # Cleanup with 30 days threshold (should not delete anything)
        deleted = memory_manager.cleanup_old_context(days_threshold=30)
        print(f"Deleted with 30-day threshold: {deleted} items")

        # Cleanup with 0 days threshold (should delete old items)
        deleted = memory_manager.cleanup_old_context(days_threshold=0)
        print(f"Deleted with 0-day threshold: {deleted} items")

        # Check remaining context
        remaining_context = memory_manager.get_context(limit=100)
        print(f"Context items after cleanup: {len(remaining_context)}")

    finally:
        # Cleanup
        import os

        if os.path.exists(temp_db):
            os.unlink(temp_db)


def example_type_matching():
    """Example 4: Type matching scores"""
    print("\n" + "=" * 70)
    print("Example 4: Type Matching Scores")
    print("=" * 70)

    ranker = ContextRanker()

    # Test different context types with different intents
    test_cases = [
        # (context_type, context_data, intent_action, intent_params, expected_match)
        ("app", {"app_name": "Chrome"}, "open_app", {"app_name": "Chrome"}, "Exact match"),
        ("app", {"app_name": "Safari"}, "open_app", {"app_name": "Chrome"}, "Type match"),
        (
            "file",
            {"file_path": "/test/file.py"},
            "open_file",
            {"path": "/test/file.py"},
            "Exact match",
        ),
        (
            "file",
            {"file_path": "/test/file1.py"},
            "open_file",
            {"path": "/test/file2.py"},
            "Same dir",
        ),
        ("clipboard", {"content": "text"}, "paste_text", {}, "High relevance"),
        (
            "browser",
            {"url": "https://github.com"},
            "open_browser",
            {"url": "https://github.com"},
            "URL match",
        ),
        ("app", {"app_name": "Chrome"}, "open_file", {"path": "/test.txt"}, "Type mismatch"),
    ]

    print("\nType matching scores:")
    print(f"{'Context Type':<15} {'Intent Action':<20} {'Match Type':<15} {'Score':<10}")
    print("-" * 70)

    for ctx_type, ctx_data, intent_action, intent_params, match_type in test_cases:
        context_item = {"type": ctx_type, "data": ctx_data, "timestamp": datetime.now().isoformat()}

        intent = Intent(action=intent_action, confidence=0.9, parameters=intent_params)

        score = ranker.score_relevance(context_item, intent)

        # Create visual representation
        bar_length = int(score * 30)
        bar = "█" * bar_length

        print(f"{ctx_type:<15} {intent_action:<20} {match_type:<15} {score:.3f} {bar}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("TICKET A4 - Context Engine Smart with Relevance Scoring")
    print("Examples and Demonstrations")
    print("=" * 70)

    try:
        example_basic_ranking()
        example_temporal_decay()
        example_type_matching()
        example_memory_service_integration()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
