"""
Integration tests for unified memory architecture

Tests the consolidated memory management system:
- UnifiedMemoryManager
- UnifiedStore
- EnhancedMultiSessionMemory
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from janus.runtime.core import Settings, UnifiedMemoryManager
from janus.memory import EnhancedMultiSessionMemory
from janus.persistence import UnifiedStore


class TestUnifiedStore:
    """Test UnifiedStore functionality"""

    @pytest.fixture
    def store(self):
        """Create a temporary unified store"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        store = UnifiedStore(db_path, auto_cleanup_days=30)
        yield store

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_context_snapshot_storage(self, store):
        """Test storing and retrieving context snapshots"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "active_window": {"app": "Safari", "title": "GitHub"},
            "open_applications": [{"name": "Safari"}, {"name": "Terminal"}],
            "urls": [{"url": "https://github.com"}],
            "visible_text": ["test text 1", "test text 2"],
            "performance_ms": 125.5,
        }

        # Save snapshot
        snapshot_id = store.save_context_snapshot(snapshot, "full", "test")
        assert snapshot_id > 0

        # Retrieve latest
        latest = store.get_latest_snapshot()
        assert latest is not None
        assert latest["active_window"]["app"] == "Safari"
        assert len(latest["open_applications"]) == 2

        # Query elements
        apps = store.query_context_elements("application", limit=10)
        assert len(apps) == 2
        assert apps[0]["name"] in ["Safari", "Terminal"]

    def test_clipboard_operations(self, store):
        """Test clipboard history"""
        # Add entries
        id1 = store.add_clipboard_entry("Hello World", "text", source="test")
        id2 = store.add_clipboard_entry("print('test')", "code", source="vscode")

        assert id1 > 0
        assert id2 > 0

        # Get history
        history = store.get_clipboard_history(limit=10)
        assert len(history) == 2
        assert history[0]["content"] in ["Hello World", "print('test')"]

        # Search
        results = store.search_clipboard("Hello")
        assert len(results) == 1
        assert results[0]["content"] == "Hello World"

        # Filter by type
        code_entries = store.get_clipboard_history(limit=10, content_type="code")
        assert len(code_entries) == 1
        assert code_entries[0]["content"] == "print('test')"

    def test_file_operations(self, store):
        """Test file operation tracking"""
        # Record operations
        store.add_file_operation("open", "/path/to/file.txt", "success")
        store.add_file_operation("save", "/path/to/file.txt", "success")
        store.add_file_operation("delete", "/path/to/old.txt", "success")

        # Get history
        history = store.get_file_operations(limit=10)
        assert len(history) == 3

        # Filter by operation type
        opens = store.get_file_operations(limit=10, operation_type="open")
        assert len(opens) == 1
        assert opens[0]["file_path"] == "/path/to/file.txt"

        # Filter by file path
        file_ops = store.get_file_operations(limit=10, file_path="file.txt")
        assert len(file_ops) == 2

    def test_browser_tabs(self, store):
        """Test browser tab tracking"""
        # Add tabs
        store.add_browser_tab("https://github.com", "GitHub", "Chrome", is_active=True)
        store.add_browser_tab("https://google.com", "Google", "Chrome")
        store.add_browser_tab("https://stackoverflow.com", "Stack Overflow", "Firefox")

        # Get all tabs
        tabs = store.get_browser_tabs(limit=10)
        assert len(tabs) == 3

        # Filter by browser
        chrome_tabs = store.get_browser_tabs(limit=10, browser="Chrome")
        assert len(chrome_tabs) == 2

        # Filter active only
        active_tabs = store.get_browser_tabs(limit=10, active_only=True)
        assert len(active_tabs) == 1
        assert active_tabs[0]["url"] == "https://github.com"

    def test_statistics(self, store):
        """Test statistics aggregation"""
        # Add some data
        store.add_clipboard_entry("test", "text")
        store.add_file_operation("open", "/file.txt", "success")
        store.add_browser_tab("https://test.com", "Test", "Chrome")

        snapshot = {"timestamp": datetime.now().isoformat(), "active_window": {"app": "Test"}}
        store.save_context_snapshot(snapshot, "full", "test")

        # Get stats
        stats = store.get_stats()
        assert stats["clipboard_entries"] == 1
        assert stats["file_operations"] == 1
        assert stats["browser_tabs"] == 1
        assert stats["context_snapshots"] == 1


class TestEnhancedMultiSessionMemory:
    """Test EnhancedMultiSessionMemory with MemoryEngine integration"""

    @pytest.fixture
    def multi_session(self):
        """Create enhanced multi-session memory (can optionally use MemoryEngine)"""
        return EnhancedMultiSessionMemory(memory_service=None)

    def test_session_creation(self, multi_session):
        """Test creating and retrieving sessions"""
        session = multi_session.create_session("test-session-1")
        assert session.session_id == "test-session-1"

        # Retrieve session
        retrieved = multi_session.get_session("test-session-1")
        assert retrieved is not None
        assert retrieved.session_id == "test-session-1"

    def test_session_data(self, multi_session):
        """Test storing data in sessions"""
        session = multi_session.create_session("data-session")

        # Set data
        session.set("key1", "value1")
        session.set("key2", {"nested": "data"})

        # Get data
        assert session.get("key1") == "value1"
        assert session.get("key2") == {"nested": "data"}
        assert session.get("nonexistent", "default") == "default"

    def test_window_data(self, multi_session):
        """Test window-specific data"""
        session = multi_session.create_session("window-session")

        # Set window-specific data
        session.set("cursor", {"x": 100, "y": 200}, window_id="window1")
        session.set("cursor", {"x": 300, "y": 400}, window_id="window2")

        # Get window-specific data
        assert session.get("cursor", window_id="window1") == {"x": 100, "y": 200}
        assert session.get("cursor", window_id="window2") == {"x": 300, "y": 400}

        # List windows
        windows = session.get_all_windows()
        assert len(windows) == 2
        assert "window1" in windows
        assert "window2" in windows

    def test_shared_data(self, multi_session):
        """Test cross-session shared data"""
        # Set shared data
        multi_session.set_shared("global_config", {"theme": "dark"})
        multi_session.set_shared("user_prefs", {"lang": "en"})

        # Get shared data
        assert multi_session.get_shared("global_config") == {"theme": "dark"}
        assert multi_session.get_shared("user_prefs") == {"lang": "en"}
        assert multi_session.get_shared("nonexistent") is None

    def test_global_clipboard(self, multi_session):
        """Test global clipboard functionality"""
        clipboard = multi_session.global_clipboard

        # Copy items
        id1 = clipboard.copy("Hello", "text", module="test")
        id2 = clipboard.copy("World", "text", module="test")

        # Paste current
        assert clipboard.paste() == "World"

        # Get history
        history = clipboard.get_history(limit=10)
        assert len(history) == 2

        # Search
        results = clipboard.search("Hell")
        assert len(results) == 1
        assert results[0]["content"] == "Hello"

    def test_session_deletion(self, multi_session):
        """Test deleting sessions"""
        session = multi_session.create_session("delete-me")
        assert multi_session.get_session("delete-me") is not None

        # Delete
        result = multi_session.delete_session("delete-me")
        assert result is True

        # Verify deleted
        assert multi_session.get_session("delete-me") is None

    def test_statistics(self, multi_session):
        """Test statistics gathering"""
        # Create multiple sessions
        multi_session.create_session("session1")
        multi_session.create_session("session2")

        # Add clipboard entries
        multi_session.global_clipboard.copy("test1", "text")
        multi_session.global_clipboard.copy("test2", "text")

        # Get stats
        stats = multi_session.get_statistics()
        assert stats["total_sessions"] == 2
        assert stats["clipboard_entries"] == 2
        assert "session1" in stats["sessions"]
        assert "session2" in stats["sessions"]


class TestUnifiedMemoryManager:
    """Test UnifiedMemoryManager integration"""

    @pytest.fixture
    def memory_manager(self):
        """Create a UnifiedMemoryManager with temporary databases"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            main_db = f.name
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            unified_db = f.name

        settings = Settings()
        settings.database.path = main_db

        manager = UnifiedMemoryManager(settings.database, unified_store_path=unified_db)

        yield manager

        # Cleanup
        for db in [main_db, unified_db]:
            if os.path.exists(db):
                os.unlink(db)

    def test_session_management(self, memory_manager):
        """Test session creation and switching"""
        session_id = memory_manager.get_current_session_id()
        assert session_id is not None

        # Create new session
        new_session = memory_manager.create_new_session()
        assert new_session != session_id
        assert memory_manager.get_current_session_id() == new_session

    def test_command_recording(self, memory_manager):
        """Test recording commands"""
        memory_manager.record_command(
            "open Safari", "open_app", {"app_name": "Safari"}, result={"status": "success"}
        )

        # Get history
        history = memory_manager.get_command_history(limit=10)
        assert len(history) >= 1

        # Get last command
        last_cmd = memory_manager.get_last_command()
        assert last_cmd == "open Safari"

    def test_context_operations(self, memory_manager):
        """Test context storage and retrieval"""
        memory_manager.store_context("user_action", {"action": "click", "target": "button"})

        context = memory_manager.get_context(limit=10)
        assert len(context) >= 1

    def test_clipboard_integration(self, memory_manager):
        """Test clipboard operations"""
        memory_manager.record_copy("test content", source="test")

        history = memory_manager.get_clipboard_history(limit=10)
        assert len(history) >= 1
        assert history[0]["content"] == "test content"

    def test_reference_resolution(self, memory_manager):
        """Test contextual reference resolution"""
        # Record a copy
        memory_manager.record_copy("test data")

        # Resolve "it"
        resolved = memory_manager.resolve_reference("it")
        assert resolved == "test data"

    def test_multi_session_operations(self, memory_manager):
        """Test multi-session capabilities"""
        # List sessions
        sessions = memory_manager.list_all_sessions()
        assert len(sessions) >= 1

        # Get details
        details = memory_manager.get_session_details()
        assert details is not None
        assert "session_id" in details

    def test_analytics(self, memory_manager):
        """Test analytics functions"""
        # Record some activity
        memory_manager.record_command("test", "test_intent", {})
        memory_manager.record_copy("test")

        # Get stats
        stats = memory_manager.get_storage_stats()
        assert "current_session_id" in stats
        assert "session_actions" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
