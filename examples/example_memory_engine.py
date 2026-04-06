"""
Example: Using the New MemoryEngine (TICKET-AUDIT-005)

This example demonstrates the unified MemoryEngine API that replaces 6 legacy systems.

Run with: python examples/example_memory_engine.py
"""

from janus.runtime.core import MemoryEngine


def example_basic_operations():
    """Example 1: Basic storage and retrieval"""
    print("\n" + "="*60)
    print("Example 1: Basic Storage & Retrieval")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Store simple data
    memory.store("user_name", "Alice")
    memory.store("settings", {"theme": "dark", "language": "en"})
    
    # Retrieve data
    name = memory.retrieve("user_name")
    settings = memory.retrieve("settings")
    
    print(f"✓ Stored and retrieved: {name}")
    print(f"✓ Settings: {settings}")
    
    # Default values
    missing = memory.retrieve("nonexistent", "default_value")
    print(f"✓ Default value: {missing}")


def example_context_tracking():
    """Example 2: Context tracking with temporal decay"""
    print("\n" + "="*60)
    print("Example 2: Context Tracking")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Track user actions
    memory.add_context("user_action", {
        "action": "click",
        "target": "submit_button",
        "x": 100,
        "y": 200
    })
    
    memory.add_context("app_state", {
        "app": "Safari",
        "url": "https://github.com",
        "title": "GitHub"
    })
    
    memory.add_context("intent", {
        "intent": "open_file",
        "confidence": 0.95,
        "file_path": "/path/to/file.txt"
    })
    
    # Retrieve recent context
    recent = memory.get_context(limit=10)
    print(f"✓ Recent context items: {len(recent)}")
    for ctx in recent:
        print(f"  - {ctx['type']}: {ctx['data']}")
    
    # Filter by type
    actions = memory.get_context(limit=5, context_type="user_action")
    print(f"✓ User actions only: {len(actions)}")


def example_action_history():
    """Example 3: Action history tracking"""
    print("\n" + "="*60)
    print("Example 3: Action History")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Record commands
    memory.record_action("command", {
        "command": "open Safari",
        "intent": "open_app",
        "parameters": {"app_name": "Safari"}
    }, result={"status": "success", "duration_ms": 150})
    
    # Record clicks
    memory.record_action("click", {
        "x": 100,
        "y": 200,
        "target": "button"
    })
    
    # Record copies
    memory.record_action("copy", {
        "content": "Hello, World!",
        "source": "Safari"
    })
    
    # Get history
    history = memory.get_history(limit=10)
    print(f"✓ Total actions: {len(history)}")
    
    for action in history:
        print(f"  - {action['type']}: {action['data']}")
        if action['result']:
            print(f"    Result: {action['result']}")
    
    # Filter by type
    commands = memory.get_history(limit=10, action_type="command")
    print(f"✓ Commands only: {len(commands)}")


def example_conversations():
    """Example 4: Multi-turn conversations"""
    print("\n" + "="*60)
    print("Example 4: Conversations")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Start a conversation
    conv_id = memory.start_conversation()
    print(f"✓ Started conversation: {conv_id}")
    
    # Add turns
    memory.add_conversation_turn(conv_id,
        user_input="Hello, open Safari",
        system_response="Opening Safari..."
    )
    
    memory.add_conversation_turn(conv_id,
        user_input="Now go to GitHub",
        system_response="Navigating to https://github.com"
    )
    
    memory.add_conversation_turn(conv_id,
        user_input="Find my repositories",
        system_response="Showing your repositories"
    )
    
    # Get conversation history
    turns = memory.get_conversation_history(conv_id)
    print(f"✓ Conversation has {len(turns)} turns:")
    for turn in turns:
        print(f"  Turn {turn['turn_number']}:")
        print(f"    User: {turn['user_input']}")
        print(f"    System: {turn['system_response']}")
    
    # End conversation
    memory.end_conversation(conv_id, reason="completed")
    print(f"✓ Ended conversation")


def example_reference_resolution():
    """Example 5: Contextual reference resolution"""
    print("\n" + "="*60)
    print("Example 5: Reference Resolution")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Record some actions to create references
    memory.record_action("copy", {"content": "test data from LinkedIn"})
    memory.record_action("click", {"x": 150, "y": 250})
    memory.record_action("open_app", {"app_name": "Salesforce"})
    memory.record_action("open_file", {"file_path": "/Users/alice/document.txt"})
    memory.record_action("open_url", {"url": "https://github.com/BenHND/Janus"})
    
    # Resolve references
    print("✓ Resolving references:")
    print(f"  'it' → {memory.resolve_reference('it')}")
    print(f"  'that' → {memory.resolve_reference('that')}")
    print(f"  'here' → {memory.resolve_reference('here')}")
    print(f"  'that app' → {memory.resolve_reference('that app')}")
    print(f"  'the file' → {memory.resolve_reference('the file')}")
    print(f"  'the url' → {memory.resolve_reference('the url')}")


def example_session_management():
    """Example 6: Session management"""
    print("\n" + "="*60)
    print("Example 6: Session Management")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Original session
    original_session = memory.session_id
    print(f"✓ Original session: {original_session}")
    
    # Store data
    memory.store("original_data", "value1")
    
    # Create new session
    new_session = memory.create_session()
    print(f"✓ Created new session: {new_session}")
    
    # Store different data
    memory.store("new_data", "value2")
    
    # Switch back
    memory.switch_session(original_session)
    print(f"✓ Switched back to original session")
    
    # Verify isolation
    original = memory.retrieve("original_data")
    new = memory.retrieve("new_data")  # Should be None
    
    print(f"✓ Original data: {original}")
    print(f"✓ New data in original session: {new} (isolated)")


def example_cross_window_workflow():
    """Example 7: Cross-window data passing (TICKET-ARCH-005)"""
    print("\n" + "="*60)
    print("Example 7: Cross-Window Workflow")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Simulate: Extract CEO email from LinkedIn
    print("\n1. Extracting from LinkedIn...")
    memory.record_action("extract", {
        "source": "LinkedIn",
        "field": "CEO Email",
        "value": "ceo@company.com"
    })
    memory.store("ceo_email", "ceo@company.com")
    print("  ✓ Extracted: ceo@company.com")
    
    # Simulate: Switch to Salesforce
    print("\n2. Switching to Salesforce...")
    memory.record_action("open_app", {"app_name": "Salesforce"})
    
    # Simulate: Paste email in Salesforce
    print("\n3. Pasting in Salesforce...")
    email = memory.retrieve("ceo_email")
    memory.record_action("fill", {
        "destination": "Salesforce",
        "field": "Contact Email",
        "value": email
    })
    print(f"  ✓ Filled email: {email}")
    
    # Review workflow
    print("\n4. Workflow history:")
    history = memory.get_history(limit=10)
    for action in history:
        print(f"  - {action['type']}: {list(action['data'].keys())}")


def example_statistics():
    """Example 8: Memory statistics"""
    print("\n" + "="*60)
    print("Example 8: Statistics")
    print("="*60)
    
    memory = MemoryEngine()
    
    # Add some data
    memory.store("key1", "value1")
    memory.store("key2", "value2")
    memory.add_context("test", {"data": "value"})
    memory.record_action("test", {"action": "test"})
    conv_id = memory.start_conversation()
    memory.add_conversation_turn(conv_id, "Hello")
    
    # Get statistics
    stats = memory.get_statistics()
    
    print("✓ Memory Statistics:")
    print(f"  Total sessions: {stats.get('total_sessions', 0)}")
    print(f"  Context items: {stats.get('context_items', 0)}")
    print(f"  History items: {stats.get('history_items', 0)}")
    print(f"  Stored items: {stats.get('stored_items', 0)}")
    print(f"  Active conversations: {stats.get('active_conversations', 0)}")
    print(f"  Database size: {stats.get('db_size_mb', 0)} MB")


def example_semantic_memory():
    """Example 9: Semantic memory and search (TICKET-MEM-001)"""
    print("\n" + "="*60)
    print("Example 9: Semantic Memory (Optional)")
    print("="*60)
    
    from janus.runtime.core.memory_engine import SEMANTIC_MEMORY_AVAILABLE
    
    if not SEMANTIC_MEMORY_AVAILABLE:
        print("⚠️  Semantic memory not available")
        print("Install with: pip install chromadb sentence-transformers")
        return
    
    memory = MemoryEngine(enable_semantic_memory=True)
    print("✓ Semantic memory enabled")
    
    # Record various actions
    print("\n1. Recording actions...")
    memory.record_action("open_file", {
        "file_path": "/Users/alice/documents/report.pdf"
    })
    memory.record_action("open_file", {
        "file_path": "/Users/alice/budget_2024.xlsx"
    })
    memory.record_action("open_app", {"app_name": "Safari"})
    memory.record_action("open_url", {"url": "https://github.com"})
    print("  ✓ Actions recorded and vectorized")
    
    # Semantic search
    print("\n2. Semantic search examples:")
    
    # Search for PDF
    results = memory.search_semantic("PDF document", limit=2)
    print(f"  Query: 'PDF document' → {len(results)} results")
    for r in results:
        print(f"    - {r['description']}")
    
    # Search in French
    results = memory.search_semantic("le fichier budget", limit=1)
    print(f"  Query: 'le fichier budget' → {len(results)} results")
    for r in results:
        print(f"    - {r['description']}")
    
    # Reference resolution with semantic fallback
    print("\n3. Semantic reference resolution:")
    
    # Natural language query
    result = memory.resolve_reference("the PDF we saw earlier")
    print(f"  'the PDF we saw earlier' → {result}")
    
    # French query
    result = memory.resolve_reference("le fichier d'hier")
    print(f"  'le fichier d'hier' → {result}")
    
    print("\n✓ Semantic memory examples completed!")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("MemoryEngine Examples (TICKET-AUDIT-005 + TICKET-MEM-001)")
    print("Unified Memory System - 11 Core Methods")
    print("="*60)
    
    try:
        example_basic_operations()
        example_context_tracking()
        example_action_history()
        example_conversations()
        example_reference_resolution()
        example_session_management()
        example_cross_window_workflow()
        example_statistics()
        example_semantic_memory()  # New example
        
        print("\n" + "="*60)
        print("✓ All examples completed successfully!")
        print("="*60)
        print("\nMemoryEngine replaces 6 legacy systems:")
        print("  1. MemoryService (old SQLite memory)")
        print("  2. UnifiedMemory")
        print("  3. ContextMemory")
        print("  4. ConversationManager")
        print("  5. SessionContext")
        print("  6. UnifiedStore")
        print("\nNew features:")
        print("  + Semantic Memory (TICKET-MEM-001) - Vector-based search")
        print("\nSee docs/SEMANTIC_MEMORY.md for semantic memory details")
        print("See docs/architecture/17-memory-engine.md for architecture")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
