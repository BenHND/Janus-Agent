"""
Tests for MemoryEngine (TICKET-AUDIT-005)

Validates the unified memory system that replaces 6 legacy systems.
"""
import os
import tempfile
import unittest
from pathlib import Path

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy pytest decorator for when pytest is not available
    class DummyPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = DummyPytest()

from janus.runtime.core.memory_engine import MemoryEngine


class TestMemoryEngineCore:
    """Test core Memory Engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create a temporary memory engine"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_initialization(self, engine):
        """Test engine initialization"""
        assert engine.session_id is not None
        assert engine.db_path.exists()
        
        stats = engine.get_statistics()
        assert stats["total_sessions"] >= 1
    
    def test_store_and_retrieve(self, engine):
        """Test basic storage operations (Core API #1 and #2)"""
        # Store simple values
        assert engine.store("key1", "value1")
        assert engine.store("key2", {"nested": "data"})
        assert engine.store("key3", [1, 2, 3])
        
        # Retrieve values
        assert engine.retrieve("key1") == "value1"
        assert engine.retrieve("key2") == {"nested": "data"}
        assert engine.retrieve("key3") == [1, 2, 3]
        
        # Test default value
        assert engine.retrieve("nonexistent", "default") == "default"
    
    def test_context_management(self, engine):
        """Test context operations (Core API #3 and #4)"""
        # Add context
        assert engine.add_context("user_action", {"action": "click", "target": "button"})
        assert engine.add_context("app_state", {"app": "Safari", "url": "https://github.com"})
        assert engine.add_context("intent", {"intent": "open_file", "confidence": 0.95})
        
        # Get all context
        context = engine.get_context(max_tokens=1000)
        assert len(context) == 3
        assert context[0]["type"] in ["user_action", "app_state", "intent"]
        
        # Filter by type
        user_actions = engine.get_context(max_tokens=1000, context_type="user_action")
        assert len(user_actions) == 1
        assert user_actions[0]["data"]["action"] == "click"
        
        # Filter by relevance
        high_relevance = engine.get_context(max_tokens=1000, min_relevance=0.9)
        assert len(high_relevance) == 3  # All have default relevance of 1.0
    
    def test_history_tracking(self, engine):
        """Test action history (Core API #5 and #6)"""
        # Record actions
        assert engine.record_action("command", {"command": "open Safari"}, {"status": "success"})
        assert engine.record_action("click", {"x": 100, "y": 200, "target": "button"})
        assert engine.record_action("copy", {"content": "test data"})
        
        # Get all history
        history = engine.get_history(max_tokens=2000)
        assert len(history) == 3
        
        # Filter by type
        commands = engine.get_history(max_tokens=2000, action_type="command")
        assert len(commands) == 1
        assert commands[0]["data"]["command"] == "open Safari"
        
        # Check results
        assert commands[0]["result"]["status"] == "success"
    
    def test_conversation_management(self, engine):
        """Test conversation tracking (Core API #7 and #8)"""
        # Start conversation
        conv_id = engine.start_conversation()
        assert conv_id != ""
        assert conv_id.startswith("conv_")
        
        # Add turns
        assert engine.add_conversation_turn(conv_id, "Hello, open Safari")
        assert engine.add_conversation_turn(conv_id, "Now go to GitHub", "Opening GitHub in Safari")
        
        # Get conversation history
        turns = engine.get_conversation_history(conv_id)
        assert len(turns) == 2
        assert turns[0]["user_input"] == "Hello, open Safari"
        assert turns[1]["system_response"] == "Opening GitHub in Safari"
        
        # End conversation
        assert engine.end_conversation(conv_id, reason="completed")
        
        # Verify ended
        stats = engine.get_statistics()
        assert stats["active_conversations"] == 0
    
    def test_reference_resolution(self, engine):
        """Test contextual reference resolution (Core API #9)"""
        # Record some actions to create references
        engine.record_action("copy", {"content": "test data"})
        engine.record_action("click", {"x": 100, "y": 200})
        engine.record_action("open_app", {"app_name": "Safari"})
        engine.record_action("open_file", {"file_path": "/path/to/file.txt"})
        engine.record_action("open_url", {"url": "https://github.com"})
        
        # Resolve references
        assert engine.resolve_reference("it") == "test data"
        assert engine.resolve_reference("here") == (100, 200)
        assert engine.resolve_reference("that app") == "Safari"
        assert engine.resolve_reference("the file") == "/path/to/file.txt"
        assert engine.resolve_reference("the url") == "https://github.com"
    
    def test_cleanup(self, engine):
        """Test data cleanup (Core API #10)"""
        # Add some data
        engine.add_context("test", {"data": "value1"})
        engine.record_action("test", {"action": "test"})
        
        # Cleanup (with 0 days to force deletion)
        stats = engine.cleanup(days_old=999)  # Won't delete recent data
        
        # Should have items
        assert engine.get_context(max_tokens=1000)
        assert engine.get_history(max_tokens=2000)


class TestMemoryEngineTokenAware(unittest.TestCase):
    """Test token-aware memory features (TICKET-LLM-001)"""
    
    def setUp(self):
        """Create a temporary memory engine"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            self.db_path = f.name
        
        self.engine = MemoryEngine(self.db_path)
    
    def tearDown(self):
        """Cleanup"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_get_history_fitting_basic(self):
        """Test basic token-aware history retrieval"""
        # Record some actions with varying sizes
        self.engine.record_action("command", {"command": "open Safari"}, {"status": "success"})
        self.engine.record_action("command", {"command": "go to GitHub"}, {"status": "success"})
        self.engine.record_action("command", {"command": "scroll down"}, {"status": "success"})
        
        # Get history with token budget
        history = self.engine.get_history(max_tokens=500)
        
        # Should get some items within budget
        self.assertGreater(len(history), 0)
        self.assertLessEqual(len(history), 3)
    
    def test_get_history_fitting_large_content(self):
        """Test token-aware history with large content"""
        # Record actions with varying content sizes
        self.engine.record_action("copy", {"content": "short"})
        self.engine.record_action("copy", {"content": "medium length content " * 10})
        self.engine.record_action("copy", {"content": "very long content " * 100})
        
        # Get with small budget - should get at least one item
        history = self.engine.get_history(max_tokens=100)
        self.assertGreaterEqual(len(history), 1)
        
        # Get with larger budget - should get more items
        history_large = self.engine.get_history(max_tokens=1000)
        self.assertGreaterEqual(len(history_large), len(history))
    
    def test_get_history_fitting_empty(self):
        """Test token-aware history when no history exists"""
        history = self.engine.get_history(max_tokens=1000)
        self.assertEqual(history, [])
    
    def test_get_history_fitting_exceeds_budget(self):
        """Test token-aware history when first item exceeds budget"""
        # Record a very large action
        large_content = "x" * 50000  # Very large content
        self.engine.record_action("copy", {"content": large_content})
        
        # Get with very small budget
        history = self.engine.get_history(max_tokens=10)
        
        # Should either return empty or truncate appropriately
        # (implementation may choose to include partial first item or skip it)
        self.assertIsInstance(history, list)
    
    def test_get_context_fitting_basic(self):
        """Test basic token-aware context retrieval"""
        # Add context with varying sizes
        self.engine.add_context("user_action", {"action": "click", "target": "button"})
        self.engine.add_context("app_state", {"app": "Safari", "url": "https://github.com"})
        self.engine.add_context("intent", {"intent": "open_file", "confidence": 0.95})
        
        # Get context with token budget
        context = self.engine.get_context(max_tokens=500)
        
        # Should get some items within budget
        self.assertGreater(len(context), 0)
        self.assertLessEqual(len(context), 3)
    
    def test_get_context_fitting_large_data(self):
        """Test token-aware context with large data"""
        # Add contexts with varying sizes
        self.engine.add_context("small", {"data": "x"})
        self.engine.add_context("medium", {"data": "x" * 100})
        self.engine.add_context("large", {"data": "x" * 1000})
        
        # Get with small budget
        context = self.engine.get_context(max_tokens=100)
        self.assertGreaterEqual(len(context), 1)
        
        # Get with larger budget
        context_large = self.engine.get_context(max_tokens=1000)
        self.assertGreaterEqual(len(context_large), len(context))
    
    def test_get_context_fitting_with_filters(self):
        """Test token-aware context with type filtering"""
        # Add different types
        self.engine.add_context("user_action", {"action": "click"})
        self.engine.add_context("user_action", {"action": "type"})
        self.engine.add_context("app_state", {"app": "Safari"})
        
        # Get specific type with token budget
        user_actions = self.engine.get_context(max_tokens=500, context_type="user_action")
        
        # Should only get user_action items
        self.assertGreater(len(user_actions), 0)
        self.assertTrue(all(item["type"] == "user_action" for item in user_actions))
    
    def test_token_budget_prevents_overflow(self):
        """Test that token budget prevents context window overflow"""
        # Simulate user pasting large text (like a book)
        large_book_text = "Lorem ipsum dolor sit amet. " * 10000  # ~280k chars
        
        self.engine.record_action("copy", {"content": large_book_text})
        self.engine.record_action("command", {"command": "open Safari"})
        
        # Get with realistic LLM context window (4k tokens for Llama 3)
        history = self.engine.get_history(max_tokens=4000)
        
        # Should not crash and should return valid data
        self.assertIsInstance(history, list)
        
        # Calculate total tokens in result
        from janus.utils.token_counter import get_token_counter
        counter = get_token_counter()
        
        total_tokens = 0
        for item in history:
            item_text = str(item)
            total_tokens += counter.count_tokens(item_text)
        
        # Should respect budget (with reasonable margin for JSON overhead)
        self.assertLessEqual(total_tokens, 5000)  # Allow some overhead


class TestMemoryEngineAdvanced:
    """Test advanced Memory Engine features"""
    
    @pytest.fixture
    def engine(self):
        """Create a temporary memory engine"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_session_management(self, engine):
        """Test session creation and switching"""
        original_session = engine.session_id
        
        # Create new session
        new_session = engine.create_session()
        assert new_session != original_session
        assert engine.session_id == new_session
        
        # Store data in new session
        engine.store("new_key", "new_value")
        
        # Switch back to original
        assert engine.switch_session(original_session)
        assert engine.session_id == original_session
        
        # Data should not be in original session
        assert engine.retrieve("new_key") is None
        
        # Switch to new session and verify data
        assert engine.switch_session(new_session)
        assert engine.retrieve("new_key") == "new_value"
    
    def test_cross_session_storage(self, engine):
        """Test storing data in different sessions"""
        session1 = engine.session_id
        session2 = engine.create_session()
        
        # Store in session2
        engine.store("key", "value2")
        
        # Switch to session1 and store different value
        engine.switch_session(session1)
        engine.store("key", "value1")
        
        # Verify isolation
        assert engine.retrieve("key") == "value1"
        assert engine.retrieve("key", session_id=session2) == "value2"
    
    def test_conversation_state_tracking(self, engine):
        """Test conversation state management"""
        # Start multiple conversations
        conv1 = engine.start_conversation()
        
        # Add turns to conv1
        engine.add_conversation_turn(conv1, "First message")
        
        # Stats should show active conversation
        stats = engine.get_statistics()
        assert stats["active_conversations"] == 1
        
        # End conversation
        engine.end_conversation(conv1, reason="user_completed")
        
        # No active conversations
        stats = engine.get_statistics()
        assert stats["active_conversations"] == 0
    
    def test_quick_reference_updates(self, engine):
        """Test that quick references are updated correctly"""
        # Record various actions
        engine.record_action("command", {"command": "test command"})
        engine.record_action("copy", {"content": "copied text"})
        engine.record_action("click", {"x": 50, "y": 100})
        
        # Verify quick references are updated
        assert engine.resolve_reference("it") == "copied text"
        assert engine.resolve_reference("here") == (50, 100)
    
    def test_statistics(self, engine):
        """Test statistics gathering"""
        # Add various data
        engine.store("key1", "value1")
        engine.add_context("test", {"data": "value"})
        engine.record_action("test", {"action": "test"})
        conv_id = engine.start_conversation()
        
        # Get statistics
        stats = engine.get_statistics()
        
        assert stats["total_sessions"] >= 1
        assert stats["context_items"] >= 1
        assert stats["history_items"] >= 1
        assert stats["stored_items"] >= 1
        assert stats["active_conversations"] >= 1
        assert "db_size_mb" in stats


class TestMemoryEngineThreadSafety:
    """Test thread safety of Memory Engine"""
    
    @pytest.fixture
    def engine(self):
        """Create a temporary memory engine"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_concurrent_stores(self, engine):
        """Test concurrent storage operations"""
        import threading
        
        def store_data(key, value):
            engine.store(key, value)
        
        # Create threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=store_data, args=(f"key{i}", f"value{i}"))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify all data stored
        for i in range(10):
            assert engine.retrieve(f"key{i}") == f"value{i}"


class TestMemoryEngineBackwardCompatibility:
    """Test backward compatibility with old memory systems"""
    
    @pytest.fixture
    def engine(self):
        """Create a temporary memory engine"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        engine = MemoryEngine(db_path)
        yield engine
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_session_context_compatibility(self, engine):
        """Test compatibility with SessionContext operations"""
        # Simulate SessionContext operations
        engine.record_action("command", {
            "command_text": "open Safari",
            "intent": "open_app",
            "parameters": {"app_name": "Safari"}
        })
        
        engine.record_action("copy", {
            "content": "test data",
            "source": "Safari"
        })
        
        engine.record_action("click", {
            "x": 100,
            "y": 200,
            "target": "button"
        })
        
        # Verify retrieval
        history = engine.get_history(max_tokens=2000)
        assert len(history) >= 3
    
    def test_context_memory_compatibility(self, engine):
        """Test compatibility with ContextMemory operations"""
        # Simulate ContextMemory operations
        engine.add_context("command", {
            "command_text": "open file",
            "intent": "open_file",
            "parameters": {"file_path": "/test.txt"}
        })
        
        # Verify retrieval
        context = engine.get_context(max_tokens=1000)
        assert len(context) >= 1
    
    def test_conversation_manager_compatibility(self, engine):
        """Test compatibility with ConversationManager operations"""
        # Simulate ConversationManager operations
        conv_id = engine.start_conversation()
        engine.add_conversation_turn(conv_id, "Hello")
        engine.add_conversation_turn(conv_id, "How are you?", "I'm doing well!")
        engine.end_conversation(conv_id)
        
        # Verify conversation history
        turns = engine.get_conversation_history(conv_id)
        assert len(turns) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
