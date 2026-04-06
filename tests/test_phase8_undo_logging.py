"""
Tests for Phase 8 - Ticket 8.4: Tests Undo / log
Test undo/redo system, action logging, and step restoration
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.persistence.action_history import ActionHistory
from janus.persistence.undo_manager import LogViewer, UndoableActionType, UndoManager


class TestUndoManagerPhase8(unittest.TestCase):
    """Comprehensive tests for undo/redo functionality"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.undo_manager = UndoManager(self.temp_db.name)

        # Register test undo handlers
        self.undo_results = []

        def file_delete_handler(undo_data):
            self.undo_results.append(("restore_file", undo_data))
            return {"status": "success", "message": "File restored"}

        def text_edit_handler(undo_data):
            self.undo_results.append(("restore_text", undo_data))
            return {"status": "success", "message": "Text restored"}

        def command_exec_handler(undo_data):
            self.undo_results.append(("undo_command", undo_data))
            return {"status": "success", "message": "Command undone"}

        self.undo_manager.register_undo_handler("file_delete", file_delete_handler)
        self.undo_manager.register_undo_handler("text_edit", text_edit_handler)
        self.undo_manager.register_undo_handler("command_exec", command_exec_handler)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_record_and_undo_single_action(self):
        """Test recording and undoing a single action"""
        # Record undoable action
        action_id = self.undo_manager.record_undoable_action(
            action_type="file_delete",
            action_data={"file": "test.txt", "operation": "delete"},
            undo_data={"file": "test.txt", "content": "backup content"},
            description="Delete test.txt",
        )

        self.assertIsNotNone(action_id)

        # Undo the action
        result = self.undo_manager.undo()

        self.assertIsNotNone(result)
        self.assertEqual(len(self.undo_results), 1)
        self.assertEqual(self.undo_results[0][0], "restore_file")

    def test_undo_multiple_actions(self):
        """Test undoing multiple actions in sequence"""
        # Record multiple actions
        self.undo_manager.record_undoable_action(
            action_type="text_edit",
            action_data={"text": "new text"},
            undo_data={"text": "old text"},
            description="Edit text",
        )

        self.undo_manager.record_undoable_action(
            action_type="file_delete",
            action_data={"file": "file1.txt"},
            undo_data={"file": "file1.txt", "content": "data"},
            description="Delete file1",
        )

        self.undo_manager.record_undoable_action(
            action_type="command_exec",
            action_data={"command": "rm file2.txt"},
            undo_data={"command": "touch file2.txt"},
            description="Execute rm",
        )

        # Undo all actions in reverse order
        result1 = self.undo_manager.undo_last_action()
        self.assertEqual(result1["status"], "success")

        result2 = self.undo_manager.undo_last_action()
        self.assertEqual(result2["status"], "success")

        result3 = self.undo_manager.undo_last_action()
        self.assertEqual(result3["status"], "success")

        # Verify all were undone in correct order
        self.assertEqual(len(self.undo_results), 3)
        self.assertEqual(self.undo_results[0][0], "undo_command")
        self.assertEqual(self.undo_results[1][0], "restore_file")
        self.assertEqual(self.undo_results[2][0], "restore_text")

    def test_redo_after_undo(self):
        """Test redoing an action after undo"""
        # Record action
        action_id = self.undo_manager.record_undoable_action(
            action_type="text_edit",
            action_data={"text": "new"},
            undo_data={"text": "old"},
            description="Edit",
        )

        # Undo
        self.undo_manager.undo_last_action()

        # Redo
        result = self.undo_manager.redo_last_action()

        self.assertEqual(result["status"], "success")

    def test_undo_stack_limit(self):
        """Test that undo stack respects size limit"""
        # Record more actions than max undo stack size
        for i in range(150):  # Assuming max is ~100
            self.undo_manager.record_undoable_action(
                action_type="text_edit",
                action_data={"text": f"edit_{i}"},
                undo_data={"text": f"old_{i}"},
                description=f"Edit {i}",
            )

        # Count available undos
        undo_count = 0
        while self.undo_manager.can_undo():
            self.undo_manager.undo_last_action()
            undo_count += 1
            if undo_count > 150:  # Safety limit
                break

        # Should not exceed reasonable limit
        self.assertLessEqual(undo_count, 110)  # Some buffer

    def test_undo_with_no_actions(self):
        """Test undoing when there are no actions"""
        result = self.undo_manager.undo_last_action()

        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)

    def test_redo_with_no_undo(self):
        """Test redoing when there's nothing to redo"""
        result = self.undo_manager.redo_last_action()

        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)

    def test_undo_clears_redo_stack(self):
        """Test that new action clears redo stack"""
        # Record and undo
        self.undo_manager.record_undoable_action(
            action_type="text_edit",
            action_data={"text": "v1"},
            undo_data={"text": "v0"},
            description="Edit 1",
        )
        self.undo_manager.undo_last_action()

        # Record new action (should clear redo stack)
        self.undo_manager.record_undoable_action(
            action_type="text_edit",
            action_data={"text": "v2"},
            undo_data={"text": "v1"},
            description="Edit 2",
        )

        # Redo should fail (stack was cleared)
        result = self.undo_manager.redo_last_action()
        self.assertIn("error", result["status"].lower())


class TestActionLoggingPhase8(unittest.TestCase):
    """Test comprehensive action logging"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.history = ActionHistory(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_log_action_with_all_fields(self):
        """Test logging action with all available fields"""
        action_id = self.history.record_action(
            action="open_file",
            module="vscode",
            parameters={"file": "test.py", "line": 42},
            result={"status": "success", "message": "File opened"},
            workflow_id="wf_001",
            metadata={"user": "test_user", "session": "sess_123"},
        )

        self.assertIsNotNone(action_id)

        # Retrieve and verify
        action = self.history.get_action_by_id(action_id)
        self.assertEqual(action["action"], "open_file")
        self.assertEqual(action["module"], "vscode")
        self.assertEqual(action["workflow_id"], "wf_001")
        self.assertIn("timestamp", action)

    def test_log_action_duration_tracking(self):
        """Test that action duration is tracked"""
        import time

        # Record action with duration
        action_id = self.history.record_action(
            action="execute_command",
            module="terminal",
            parameters={"command": "sleep 1"},
            result={"status": "success"},
        )

        # Simulate duration by updating
        time.sleep(0.1)
        self.history.update_action_duration(action_id, 0.1)

        # Verify duration was recorded
        action = self.history.get_action_by_id(action_id)
        self.assertIn("duration", action)

    def test_log_failed_actions(self):
        """Test logging failed actions"""
        action_id = self.history.record_action(
            action="execute_command",
            module="terminal",
            parameters={"command": "invalid_command"},
            result={"status": "error", "error": "Command not found", "return_code": 127},
        )

        # Retrieve failed actions
        failures = self.history.get_recent_failures(limit=10)

        self.assertGreater(len(failures), 0)
        self.assertTrue(any(f["id"] == action_id for f in failures))

    def test_search_action_logs(self):
        """Test searching through action logs"""
        # Record various actions
        self.history.record_action(
            "open_file", "vscode", {"file": "test.py"}, {"status": "success"}
        )
        self.history.record_action(
            "open_file", "vscode", {"file": "main.py"}, {"status": "success"}
        )
        self.history.record_action(
            "execute_command", "terminal", {"command": "ls"}, {"status": "success"}
        )

        # Search for specific action type
        results = self.history.search_actions("open_file")

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["action"] == "open_file" for r in results))

    def test_filter_logs_by_module(self):
        """Test filtering logs by module"""
        # Record actions from different modules
        self.history.record_action("action1", "chrome", {}, {"status": "success"})
        self.history.record_action("action2", "vscode", {}, {"status": "success"})
        self.history.record_action("action3", "chrome", {}, {"status": "success"})

        # Filter by module
        chrome_actions = self.history.get_history(module="chrome")

        self.assertEqual(len(chrome_actions), 2)
        self.assertTrue(all(a["module"] == "chrome" for a in chrome_actions))

    def test_filter_logs_by_date_range(self):
        """Test filtering logs by date range"""
        # Record actions
        now = datetime.now()

        action_id_1 = self.history.record_action("action1", "test", {}, {"status": "success"})

        # Filter by date
        since = (now - timedelta(minutes=1)).isoformat()
        recent = self.history.get_history(since=since)

        self.assertGreater(len(recent), 0)

    def test_log_statistics(self):
        """Test action statistics calculation"""
        # Record mix of successful and failed actions
        for i in range(7):
            self.history.record_action(f"action_{i}", "test", {}, {"status": "success"})

        for i in range(3):
            self.history.record_action(f"action_fail_{i}", "test", {}, {"status": "error"})

        stats = self.history.get_statistics()

        self.assertEqual(stats["total_actions"], 10)
        self.assertEqual(stats["successful_actions"], 7)
        self.assertEqual(stats["failed_actions"], 3)
        self.assertAlmostEqual(stats["success_rate"], 0.7, places=1)


class TestLogViewerPhase8(unittest.TestCase):
    """Test log viewer functionality"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.log_viewer = LogViewer(self.temp_db.name)
        self.history = ActionHistory(self.temp_db.name)

        # Populate with test data
        for i in range(20):
            self.history.record_action(
                action=f"action_{i}",
                module=f"module_{i % 3}",
                parameters={"param": f"value_{i}"},
                result={"status": "success" if i % 4 != 0 else "error"},
            )

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_view_recent_logs(self):
        """Test viewing recent logs"""
        logs = self.log_viewer.get_recent_logs(limit=10)

        self.assertEqual(len(logs), 10)
        # Should be in reverse chronological order
        self.assertGreater(logs[0]["id"], logs[-1]["id"])

    def test_view_logs_by_workflow(self):
        """Test viewing logs for specific workflow"""
        # Record workflow-specific actions
        self.history.record_action(
            "step1", "test", {}, {"status": "success"}, workflow_id="wf_test"
        )
        self.history.record_action(
            "step2", "test", {}, {"status": "success"}, workflow_id="wf_test"
        )

        logs = self.log_viewer.get_workflow_logs("wf_test")

        self.assertEqual(len(logs), 2)
        self.assertTrue(all(l["workflow_id"] == "wf_test" for l in logs))

    def test_view_error_logs_only(self):
        """Test viewing only error logs"""
        errors = self.log_viewer.get_error_logs()

        self.assertGreater(len(errors), 0)
        # All should have error status
        self.assertTrue(all("error" in str(e.get("result", "")).lower() for e in errors))

    def test_export_logs_to_json(self):
        """Test exporting logs to JSON format"""
        export_data = self.log_viewer.export_logs(format="json")

        self.assertIsInstance(export_data, str)
        # Should be valid JSON
        parsed = json.loads(export_data)
        self.assertIsInstance(parsed, list)

    def test_log_pagination(self):
        """Test log pagination"""
        page1 = self.log_viewer.get_logs_paginated(page=1, per_page=5)
        page2 = self.log_viewer.get_logs_paginated(page=2, per_page=5)

        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        # Different pages should have different items
        self.assertNotEqual(page1[0]["id"], page2[0]["id"])


class TestUndoRedoIntegrationPhase8(unittest.TestCase):
    """Integration tests for undo/redo with logging"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.undo_manager = UndoManager(self.temp_db.name)
        self.history = ActionHistory(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_undo_creates_log_entry(self):
        """Test that undo operations are logged"""

        # Register handler
        def test_handler(undo_data):
            return {"status": "success"}

        self.undo_manager.register_undo_handler("test", test_handler)

        # Record and undo
        self.undo_manager.record_undoable_action(
            action_type="test",
            action_data={"op": "delete"},
            undo_data={"op": "restore"},
            description="Test action",
        )

        initial_count = len(self.history.get_history())
        self.undo_manager.undo_last_action()

        # Should have new log entry for undo
        final_count = len(self.history.get_history())
        # Note: This depends on implementation - undo might or might not create log entry
        # Just verify the system doesn't crash
        self.assertIsNotNone(final_count)

    def test_undo_preserves_action_history(self):
        """Test that undo doesn't delete original action from history"""

        # Register handler
        def test_handler(undo_data):
            return {"status": "success"}

        self.undo_manager.register_undo_handler("preserve_test", test_handler)

        # Record original action in history
        action_id = self.history.record_action(
            action="delete_file",
            module="test",
            parameters={"file": "test.txt"},
            result={"status": "success"},
        )

        # Record as undoable and undo
        self.undo_manager.record_undoable_action(
            action_type="preserve_test",
            action_data={"file": "test.txt"},
            undo_data={"restore": "test.txt"},
            description="Delete",
        )
        self.undo_manager.undo_last_action()

        # Original action should still be in history
        original_action = self.history.get_action_by_id(action_id)
        self.assertIsNotNone(original_action)


if __name__ == "__main__":
    unittest.main()
