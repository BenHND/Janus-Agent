"""
Unit tests for ClipboardManager
"""
import json
import os
import tempfile
import unittest

from janus.platform.clipboard.clipboard_manager import ClipboardEntry, ClipboardManager, ClipboardType


class TestClipboardManager(unittest.TestCase):
    """Test cases for ClipboardManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        self.temp_file.close()
        # Disable system clipboard for testing
        self.clipboard = ClipboardManager(
            history_limit=10, persist_file=self.temp_file.name, use_system_clipboard=False
        )

    def tearDown(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_initialization(self):
        """Test clipboard manager initialization"""
        self.assertIsNotNone(self.clipboard)
        self.assertEqual(self.clipboard.history_limit, 10)
        self.assertEqual(len(self.clipboard.history), 0)

    def test_copy_text(self):
        """Test copying text to clipboard"""
        result = self.clipboard.copy_text("Hello, World!")
        self.assertTrue(result)
        self.assertEqual(len(self.clipboard.history), 1)
        self.assertEqual(self.clipboard.history[0].content, "Hello, World!")
        self.assertEqual(self.clipboard.history[0].content_type, ClipboardType.TEXT)

    def test_copy_with_metadata(self):
        """Test copying with metadata"""
        metadata = {"source": "test", "app": "chrome"}
        result = self.clipboard.copy("test content", ClipboardType.TEXT, metadata)
        self.assertTrue(result)
        self.assertEqual(self.clipboard.history[0].metadata, metadata)

    def test_get_last(self):
        """Test getting last N entries"""
        self.clipboard.copy_text("First")
        self.clipboard.copy_text("Second")
        self.clipboard.copy_text("Third")

        last_two = self.clipboard.get_last(2)
        self.assertEqual(len(last_two), 2)
        self.assertEqual(last_two[0].content, "Third")
        self.assertEqual(last_two[1].content, "Second")

    def test_get_current(self):
        """Test getting current clipboard entry"""
        # Empty clipboard
        self.assertIsNone(self.clipboard.get_current())

        # Add content
        self.clipboard.copy_text("Current content")
        current = self.clipboard.get_current()
        self.assertIsNotNone(current)
        self.assertEqual(current.content, "Current content")

    def test_history_limit(self):
        """Test that history respects limit"""
        for i in range(15):
            self.clipboard.copy_text(f"Entry {i}")

        self.assertEqual(len(self.clipboard.history), 10)
        self.assertEqual(self.clipboard.history[0].content, "Entry 14")
        self.assertEqual(self.clipboard.history[-1].content, "Entry 5")

    def test_get_history_filtered(self):
        """Test getting history filtered by type"""
        self.clipboard.copy_text("Text 1")
        self.clipboard.copy_file_path("/path/to/file")
        self.clipboard.copy_text("Text 2")

        text_entries = self.clipboard.get_history(ClipboardType.TEXT)
        self.assertEqual(len(text_entries), 2)

        file_entries = self.clipboard.get_history(ClipboardType.FILE_PATH)
        self.assertEqual(len(file_entries), 1)

    def test_search(self):
        """Test searching clipboard history"""
        self.clipboard.copy_text("Hello World")
        self.clipboard.copy_text("Python programming")
        self.clipboard.copy_text("Hello Python")

        results = self.clipboard.search("Hello")
        self.assertEqual(len(results), 2)

        results = self.clipboard.search("python", case_sensitive=False)
        self.assertEqual(len(results), 2)

        results = self.clipboard.search("Python", case_sensitive=True)
        self.assertEqual(len(results), 2)

    def test_clear_history(self):
        """Test clearing clipboard history"""
        self.clipboard.copy_text("Test 1")
        self.clipboard.copy_text("Test 2")
        self.assertEqual(len(self.clipboard.history), 2)

        self.clipboard.clear_history()
        self.assertEqual(len(self.clipboard.history), 0)

    def test_copy_file_path(self):
        """Test copying file path"""
        result = self.clipboard.copy_file_path("/home/user/document.txt")
        self.assertTrue(result)
        entry = self.clipboard.get_current()
        self.assertEqual(entry.content_type, ClipboardType.FILE_PATH)
        self.assertEqual(entry.metadata["path"], "/home/user/document.txt")

    def test_copy_json(self):
        """Test copying JSON data"""
        data = {"name": "Test", "value": 42, "nested": {"key": "value"}}
        result = self.clipboard.copy_json(data)
        self.assertTrue(result)

        entry = self.clipboard.get_current()
        self.assertEqual(entry.content_type, ClipboardType.JSON)

        # Verify JSON is valid
        parsed = json.loads(entry.content)
        self.assertEqual(parsed, data)

    def test_persistence(self):
        """Test that clipboard history persists"""
        self.clipboard.copy_text("Persistent entry")

        # Create new clipboard manager with same file
        new_clipboard = ClipboardManager(
            persist_file=self.temp_file.name, use_system_clipboard=False
        )
        self.assertEqual(len(new_clipboard.history), 1)
        self.assertEqual(new_clipboard.history[0].content, "Persistent entry")

    def test_clipboard_entry_serialization(self):
        """Test ClipboardEntry to_dict and from_dict"""
        entry = ClipboardEntry("Test content", ClipboardType.TEXT, {"source": "test"})

        # Convert to dict
        data = entry.to_dict()
        self.assertEqual(data["content"], "Test content")
        self.assertEqual(data["content_type"], "text")

        # Convert back
        restored = ClipboardEntry.from_dict(data)
        self.assertEqual(restored.content, entry.content)
        self.assertEqual(restored.content_type, entry.content_type)
        self.assertEqual(restored.metadata, entry.metadata)

    def test_capture_current_clipboard(self):
        """Test capturing current clipboard content (TICKET-FEAT-001)"""
        # Set internal clipboard content
        self.clipboard._internal_clipboard = "Python code snippet"
        
        # Capture should create a new entry
        entry = self.clipboard.capture_current_clipboard()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content, "Python code snippet")
        self.assertEqual(len(self.clipboard.history), 1)
        
        # Capturing again with same content should not create duplicate
        entry2 = self.clipboard.capture_current_clipboard()
        self.assertEqual(len(self.clipboard.history), 1)
        self.assertEqual(entry.timestamp, entry2.timestamp)

    def test_get_recent_clipboard_new_content(self):
        """Test getting recent clipboard content (TICKET-FEAT-001)"""
        # Set clipboard content
        self.clipboard._internal_clipboard = "def hello(): print('world')"
        
        # Should return content as it's recent
        recent = self.clipboard.get_recent_clipboard(max_age_seconds=10.0)
        self.assertIsNotNone(recent)
        self.assertEqual(recent, "def hello(): print('world')")

    def test_get_recent_clipboard_old_content(self):
        """Test that old clipboard content is not returned (TICKET-FEAT-001)"""
        from datetime import datetime, timedelta, timezone
        
        # Manually create an old clipboard entry
        self.clipboard._internal_clipboard = "old content"
        self.clipboard.copy_text("old content")
        
        # Manipulate the timestamp to be old
        if self.clipboard.history:
            old_time = datetime.now(timezone.utc) - timedelta(seconds=15)
            self.clipboard.history[0].timestamp = old_time.isoformat()
        
        # Should return None as content is old
        recent = self.clipboard.get_recent_clipboard(max_age_seconds=10.0)
        self.assertIsNone(recent)

    def test_get_recent_clipboard_empty(self):
        """Test getting recent clipboard when empty (TICKET-FEAT-001)"""
        # Empty clipboard
        self.clipboard._internal_clipboard = ""
        
        # Should return None
        recent = self.clipboard.get_recent_clipboard(max_age_seconds=10.0)
        self.assertIsNone(recent)

    def test_smart_clipboard_workflow(self):
        """Test the complete Smart Clipboard workflow (TICKET-FEAT-001)"""
        # Simulate user copying code
        self.clipboard._internal_clipboard = "function calculateSum(a, b) { return a + b; }"
        
        # Wake word trigger - capture clipboard
        entry = self.clipboard.capture_current_clipboard()
        self.assertIsNotNone(entry)
        
        # Immediately after, get recent clipboard (simulating voice command processing)
        recent = self.clipboard.get_recent_clipboard(max_age_seconds=10.0)
        self.assertIsNotNone(recent)
        self.assertIn("calculateSum", recent)
        
        # Verify it's in history
        self.assertEqual(len(self.clipboard.history), 1)
        self.assertEqual(self.clipboard.history[0].content, recent)


if __name__ == "__main__":
    unittest.main()
