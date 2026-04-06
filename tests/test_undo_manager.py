"""
Unit tests for UndoManager and LogViewer
"""
import os
import tempfile
import unittest

from janus.persistence.action_history import ActionHistory
from janus.persistence.undo_manager import LogViewer, UndoableActionType, UndoManager


class TestUndoManager(unittest.TestCase):
    """Test cases for UndoManager"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.undo_manager = UndoManager(self.temp_db.name)

        # Register a simple undo handler
        self.undo_handler_called = False
        self.undo_handler_data = None

        def test_undo_handler(undo_data):
            self.undo_handler_called = True
            self.undo_handler_data = undo_data
            return {"status": "success"}

        self.undo_manager.register_undo_handler("test_action", test_undo_handler)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_record_undoable_action(self):
        """Test recording an undoable action"""
        action_id = self.undo_manager.record_undoable_action(
            action_type="test_action",
            action_data={"operation": "delete", "target": "file.txt"},
            undo_data={"operation": "restore", "target": "file.txt"},
            description="Delete file",
        )
        self.assertIsInstance(action_id, int)
        self.assertGreater(action_id, 0)

    def test_undo_action(self):
        """Test undoing an action"""
        # Record an action
        self.undo_manager.record_undoable_action(
            action_type="test_action",
            action_data={"operation": "delete"},
            undo_data={"operation": "restore"},
        )

        # Undo the action
        result = self.undo_manager.undo()

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        self.assertTrue(self.undo_handler_called)
        self.assertEqual(self.undo_handler_data["operation"], "restore")

    def test_undo_with_no_handler(self):
        """Test undoing action with no registered handler"""
        # Record action with no handler
        self.undo_manager.record_undoable_action(
            action_type="unknown_action", action_data={}, undo_data={}
        )

        result = self.undo_manager.undo()

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "error")
        self.assertIn("No undo handler", result["error"])

    def test_undo_with_empty_stack(self):
        """Test undo with empty stack"""
        result = self.undo_manager.undo()
        self.assertIsNone(result)

    def test_redo_action(self):
        """Test redoing an action"""
        # Record and undo an action
        self.undo_manager.record_undoable_action(
            action_type="test_action",
            action_data={"operation": "delete"},
            undo_data={"operation": "restore"},
        )
        self.undo_manager.undo()

        # Redo the action
        result = self.undo_manager.redo()

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    def test_get_undo_stack(self):
        """Test getting undo stack"""
        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={"op": "1"}, undo_data={}
        )
        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={"op": "2"}, undo_data={}
        )

        stack = self.undo_manager.get_undo_stack()
        self.assertEqual(len(stack), 2)
        # Most recent should be first
        self.assertEqual(stack[0]["action_data"]["op"], "2")

    def test_get_redo_stack(self):
        """Test getting redo stack"""
        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={"op": "1"}, undo_data={}
        )
        self.undo_manager.undo()

        stack = self.undo_manager.get_redo_stack()
        self.assertEqual(len(stack), 1)

    def test_can_undo(self):
        """Test checking if undo is possible"""
        self.assertFalse(self.undo_manager.can_undo())

        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={}, undo_data={}
        )

        self.assertTrue(self.undo_manager.can_undo())

    def test_can_redo(self):
        """Test checking if redo is possible"""
        self.assertFalse(self.undo_manager.can_redo())

        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={}, undo_data={}
        )
        self.undo_manager.undo()

        self.assertTrue(self.undo_manager.can_redo())

    def test_clear_undo_stack(self):
        """Test clearing undo stack"""
        self.undo_manager.record_undoable_action(
            action_type="test_action", action_data={}, undo_data={}
        )

        self.undo_manager.clear_undo_stack()

        self.assertFalse(self.undo_manager.can_undo())

    def test_max_undo_stack_limit(self):
        """Test that undo stack respects max limit"""
        # Create manager with small limit
        manager = UndoManager(self.temp_db.name, max_undo_stack=5)

        # Add more actions than limit
        for i in range(10):
            manager.record_undoable_action(
                action_type="test_action", action_data={"index": i}, undo_data={}
            )

        stack = manager.get_undo_stack(limit=20)
        self.assertLessEqual(len(stack), 5)


class TestLogViewer(unittest.TestCase):
    """Test cases for LogViewer"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Create action history for testing logs
        self.history = ActionHistory(self.temp_db.name)
        self.log_viewer = LogViewer(self.temp_db.name)

        # Add some test actions
        self.history.record_action("click", {"target": "button"}, status="success")
        self.history.record_action("copy", {"content": "text"}, status="success")
        self.history.record_action("paste", {}, status="failed", error="No content")

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_get_logs(self):
        """Test getting logs"""
        logs = self.log_viewer.get_logs(limit=10)
        self.assertEqual(len(logs), 3)

    def test_get_logs_filtered(self):
        """Test getting logs with filters"""
        # Filter by action type
        logs = self.log_viewer.get_logs(action_type="click")
        self.assertEqual(len(logs), 1)

        # Filter by status
        logs = self.log_viewer.get_logs(status="success")
        self.assertEqual(len(logs), 2)

    def test_search_logs(self):
        """Test searching logs"""
        logs = self.log_viewer.search_logs("button")
        self.assertEqual(len(logs), 1)

        logs = self.log_viewer.search_logs("content")
        self.assertGreater(len(logs), 0)

    def test_export_logs(self):
        """Test exporting logs"""
        temp_export = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_export.close()

        try:
            success = self.log_viewer.export_logs(temp_export.name)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(temp_export.name))
            self.assertGreater(os.path.getsize(temp_export.name), 0)
        finally:
            if os.path.exists(temp_export.name):
                os.unlink(temp_export.name)


if __name__ == "__main__":
    unittest.main()
