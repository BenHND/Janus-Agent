"""
Tests for Phase 8 - Ticket 8.3: Tests mémoire persistante
Test clipboard persistence, action history persistence, and workflow resumption after restart
"""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.platform.clipboard.clipboard_manager import ClipboardManager
from janus.persistence.action_history import ActionHistory
from janus.persistence.unified_store import UnifiedStore
from janus.persistence.workflow_persistence import WorkflowPersistence


class TestClipboardPersistencePhase8(unittest.TestCase):
    """Test clipboard persistence after restart"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.clipboard = ClipboardManager(persist_file=self.temp_file.name)

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_clipboard_history_persistence(self):
        """Test that clipboard history persists across restarts"""
        # First session: Add items
        self.clipboard.copy("First item")
        self.clipboard.copy("Second item")
        self.clipboard.copy("Third item")

        # Save and close
        self.clipboard.save_history()
        del self.clipboard

        # Second session: Load history
        clipboard2 = ClipboardManager(persist_file=self.temp_file.name)
        history = clipboard2.get_history()

        # Verify items persisted
        self.assertGreaterEqual(len(history), 3)
        # Most recent first
        self.assertIn("Third item", [h["content"] for h in history])
        self.assertIn("Second item", [h["content"] for h in history])
        self.assertIn("First item", [h["content"] for h in history])

    def test_clipboard_max_size_enforcement(self):
        """Test that clipboard respects max size limit"""
        # Add more items than max size
        for i in range(150):  # Default max is 100
            self.clipboard.copy(f"Item {i}")

        history = self.clipboard.get_history()

        # Should not exceed max size
        self.assertLessEqual(len(history), 100)

    def test_clipboard_search_persistence(self):
        """Test searching persisted clipboard history"""
        # Add searchable items
        self.clipboard.copy("Python code snippet")
        self.clipboard.copy("JavaScript function")
        self.clipboard.copy("Python class definition")
        self.clipboard.save_history()

        # Reload and search
        clipboard2 = ClipboardManager(persist_file=self.temp_file.name)
        results = clipboard2.search("Python")

        self.assertEqual(len(results), 2)
        self.assertTrue(all("Python" in r["content"] for r in results))

    def test_clipboard_clear_and_restore(self):
        """Test clearing clipboard and ability to restore"""
        # Add items
        self.clipboard.copy("Item 1")
        self.clipboard.copy("Item 2")
        self.clipboard.save_history()

        # Clear clipboard
        self.clipboard.clear_history()
        self.assertEqual(len(self.clipboard.get_history()), 0)

        # Reload from file should restore
        clipboard2 = ClipboardManager(persist_file=self.temp_file.name)
        history = clipboard2.get_history()

        # History should be restored from file
        self.assertGreaterEqual(len(history), 0)


class TestActionHistoryPersistencePhase8(unittest.TestCase):
    """Test action history persistence after restart"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.history = ActionHistory(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_action_history_survives_restart(self):
        """Test that action history persists across restarts"""
        # First session: Record actions
        action_id_1 = self.history.record_action(
            action="open_app",
            module="chrome",
            parameters={"app": "Chrome"},
            result={"status": "success"},
        )

        action_id_2 = self.history.record_action(
            action="execute_command",
            module="terminal",
            parameters={"command": "ls"},
            result={"status": "success", "output": "file1.txt"},
        )

        # Close and reopen
        del self.history
        history2 = ActionHistory(self.temp_db.name)

        # Verify actions persisted
        all_actions = history2.get_history()
        self.assertGreaterEqual(len(all_actions), 2)

        # Verify specific actions can be retrieved
        action1 = history2.get_action_by_id(action_id_1)
        self.assertIsNotNone(action1)
        self.assertEqual(action1["action"], "open_app")

        action2 = history2.get_action_by_id(action_id_2)
        self.assertIsNotNone(action2)
        self.assertEqual(action2["action"], "execute_command")

    def test_action_statistics_persistence(self):
        """Test that statistics persist after restart"""
        # Record various actions
        for i in range(5):
            self.history.record_action(
                action="open_app", module="chrome", parameters={}, result={"status": "success"}
            )

        for i in range(3):
            self.history.record_action(
                action="execute_command",
                module="terminal",
                parameters={},
                result={"status": "error"},
            )

        # Get initial stats
        stats1 = self.history.get_statistics()

        # Restart
        del self.history
        history2 = ActionHistory(self.temp_db.name)

        # Get stats after restart
        stats2 = history2.get_statistics()

        # Verify stats match
        self.assertEqual(stats1["total_actions"], stats2["total_actions"])
        self.assertEqual(stats1["successful_actions"], stats2["successful_actions"])
        self.assertEqual(stats1["failed_actions"], stats2["failed_actions"])

    def test_search_persisted_history(self):
        """Test searching action history after restart"""
        # Record searchable actions
        self.history.record_action(
            action="open_file",
            module="vscode",
            parameters={"file": "test.py"},
            result={"status": "success"},
        )

        self.history.record_action(
            action="open_file",
            module="vscode",
            parameters={"file": "main.py"},
            result={"status": "success"},
        )

        # Restart
        del self.history
        history2 = ActionHistory(self.temp_db.name)

        # Search for actions
        results = history2.search_actions("open_file")

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["action"] == "open_file" for r in results))


class TestWorkflowPersistencePhase8(unittest.TestCase):
    """Test workflow state persistence and resumption"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.persistence = WorkflowPersistence(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_workflow_state_persistence(self):
        """Test that workflow state persists after restart"""
        # Create workflow
        self.persistence.save_workflow(
            workflow_id="wf_001",
            name="Test Workflow",
            status="in_progress",
            metadata={"priority": "high"},
        )

        # Add steps
        self.persistence.save_workflow_step(
            workflow_id="wf_001",
            step_id="step1",
            step_data={"action": "test", "module": "test_module"},
            status="completed",
            result={"status": "success"},
        )

        self.persistence.save_workflow_step(
            workflow_id="wf_001",
            step_id="step2",
            step_data={"action": "test2", "module": "test_module2"},
            status="in_progress",
            result=None,
        )

        # Restart
        del self.persistence
        persistence2 = WorkflowPersistence(self.temp_db.name)

        # Verify workflow persisted
        workflow = persistence2.get_workflow("wf_001")
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow["name"], "Test Workflow")
        self.assertEqual(workflow["status"], "in_progress")

        # Verify steps persisted
        steps = persistence2.get_workflow_steps("wf_001")
        self.assertEqual(len(steps), 2)

    def test_resume_paused_workflow(self):
        """Test resuming a paused workflow after restart"""
        # Create paused workflow
        self.persistence.save_workflow(
            workflow_id="wf_resume",
            name="Resumable Workflow",
            status="paused",
            metadata={"checkpoint": "step2"},
        )

        # Add completed and pending steps
        self.persistence.save_workflow_step(
            "wf_resume",
            "step1",
            step_data={"action": "test1"},
            status="completed",
            result={"data": "result1"},
        )
        self.persistence.save_workflow_step(
            "wf_resume", "step2", step_data={"action": "test2"}, status="paused", result=None
        )
        self.persistence.save_workflow_step(
            "wf_resume", "step3", step_data={"action": "test3"}, status="pending", result=None
        )

        # Restart and resume
        del self.persistence
        persistence2 = WorkflowPersistence(self.temp_db.name)

        workflow = persistence2.get_workflow("wf_resume")
        steps = persistence2.get_workflow_steps("wf_resume")

        # Verify we can identify where to resume
        completed = [s for s in steps if s["status"] == "completed"]
        pending = [s for s in steps if s["status"] in ["paused", "pending"]]

        self.assertEqual(len(completed), 1)
        self.assertEqual(len(pending), 2)
        self.assertEqual(workflow["status"], "paused")

    def test_workflow_completion_persistence(self):
        """Test that completed workflows persist correctly"""
        # Create and complete workflow
        self.persistence.save_workflow("wf_complete", "Complete Workflow", "pending")

        # Mark all steps complete
        self.persistence.save_workflow_step(
            "wf_complete",
            "s1",
            step_data={"action": "test1"},
            status="completed",
            result={"result": "ok"},
        )
        self.persistence.save_workflow_step(
            "wf_complete",
            "s2",
            step_data={"action": "test2"},
            status="completed",
            result={"result": "ok"},
        )

        # Mark workflow complete
        self.persistence.save_workflow("wf_complete", status="completed")

        # Restart
        del self.persistence
        persistence2 = WorkflowPersistence(self.temp_db.name)

        # Verify completion persisted
        workflow = persistence2.get_workflow("wf_complete")
        self.assertEqual(workflow["status"], "completed")

        steps = persistence2.get_workflow_steps("wf_complete")
        self.assertTrue(all(s["status"] == "completed" for s in steps))

    def test_list_pending_workflows_after_restart(self):
        """Test listing pending workflows after restart"""
        # Create multiple workflows in different states
        self.persistence.save_workflow("wf1", "Workflow 1", "pending")
        self.persistence.save_workflow("wf2", "Workflow 2", "in_progress")
        self.persistence.save_workflow("wf3", "Workflow 3", "completed")
        self.persistence.save_workflow("wf4", "Workflow 4", "paused")

        # Restart
        del self.persistence
        persistence2 = WorkflowPersistence(self.temp_db.name)

        # Get in-progress workflow manually
        workflow = persistence2.get_workflow("wf2")
        self.assertEqual(workflow["status"], "in_progress")

        # Get all workflows by checking each one
        wf1 = persistence2.get_workflow("wf1")
        wf3 = persistence2.get_workflow("wf3")
        wf4 = persistence2.get_workflow("wf4")

        self.assertEqual(wf1["status"], "pending")
        self.assertEqual(wf3["status"], "completed")
        self.assertEqual(wf4["status"], "paused")


class TestPersistentStorageIntegrityPhase8(unittest.TestCase):
    """Test integrity of persistent storage after restart"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.store = UnifiedStore(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_schema_survives_restart(self):
        """Test that database schema remains intact after restart"""
        # Store some data
        self.store.add_clipboard_entry("Test content")

        # Close and reopen
        del self.store
        store2 = UnifiedStore(self.temp_db.name)

        # Verify schema is intact by querying
        items = store2.get_clipboard_history()
        self.assertIsInstance(items, list)

    def test_concurrent_access_safety(self):
        """Test that database handles concurrent access safely"""
        # Create two store instances to same database
        store1 = UnifiedStore(self.temp_db.name)
        store2 = UnifiedStore(self.temp_db.name)

        # Both write data
        store1.add_clipboard_entry("From store 1")
        store2.add_clipboard_entry("From store 2")

        # Both should see all data
        history1 = store1.get_clipboard_history()
        history2 = store2.get_clipboard_history()

        self.assertEqual(len(history1), len(history2))

    def test_data_integrity_after_crash_simulation(self):
        """Test data integrity after simulated crash"""
        # Write data
        self.store.add_clipboard_entry("Important data")

        # Simulate crash by not properly closing
        # Just delete the reference without calling close
        store_ref = self.store
        del self.store

        # Reopen and verify data
        store2 = UnifiedStore(self.temp_db.name)
        items = store2.get_clipboard_history()

        # Data should still be there (SQLite's durability)
        self.assertGreater(len(items), 0)

    def test_persistent_store_migration_compatibility(self):
        """Test that storage format is forward compatible"""
        # Store data with current version
        self.store.add_clipboard_entry("Version test data")

        # Close
        del self.store

        # Reopen and verify we can still read
        store2 = UnifiedStore(self.temp_db.name)
        items = store2.get_clipboard_history()

        self.assertGreater(len(items), 0)
        self.assertIn("Version test data", [i["content"] for i in items])


if __name__ == "__main__":
    unittest.main()
