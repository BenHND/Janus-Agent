"""
Unit tests for ActionHistory
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.persistence.action_history import ActionHistory


class TestActionHistory(unittest.TestCase):
    """Test cases for ActionHistory"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.history = ActionHistory(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_record_action(self):
        """Test recording an action"""
        action_id = self.history.record_action(
            action_type="click",
            action_data={"target": "button", "x": 100, "y": 200},
            result={"status": "success"},
            status="success",
            duration_ms=150,
        )
        self.assertIsInstance(action_id, int)
        self.assertGreater(action_id, 0)

    def test_get_history(self):
        """Test getting action history"""
        # Record multiple actions
        self.history.record_action("click", {"target": "button1"}, status="success")
        self.history.record_action("copy", {"content": "text"}, status="success")
        self.history.record_action("paste", {}, status="failed", error="No content")

        # Get all actions
        actions = self.history.get_history(limit=10)
        self.assertEqual(len(actions), 3)

        # Most recent should be first
        self.assertEqual(actions[0]["action_type"], "paste")

    def test_get_history_filtered(self):
        """Test getting history with filters"""
        self.history.record_action("click", {}, status="success", module="chrome")
        self.history.record_action("copy", {}, status="success", module="vscode")
        self.history.record_action("click", {}, status="failed", module="chrome")

        # Filter by action type
        clicks = self.history.get_history(action_type="click")
        self.assertEqual(len(clicks), 2)

        # Filter by status
        successes = self.history.get_history(status="success")
        self.assertEqual(len(successes), 2)

        # Filter by module
        chrome_actions = self.history.get_history(module="chrome")
        self.assertEqual(len(chrome_actions), 2)

    def test_get_action_by_id(self):
        """Test getting specific action by ID"""
        action_id = self.history.record_action(
            action_type="click", action_data={"target": "button"}, status="success"
        )

        action = self.history.get_action_by_id(action_id)
        self.assertIsNotNone(action)
        self.assertEqual(action["action_type"], "click")
        self.assertEqual(action["action_data"]["target"], "button")

    def test_get_workflow_actions(self):
        """Test getting actions for a specific workflow"""
        workflow_id = "workflow_123"

        self.history.record_action("step1", {}, workflow_id=workflow_id, step_id="s1")
        self.history.record_action("step2", {}, workflow_id=workflow_id, step_id="s2")
        self.history.record_action("step3", {}, workflow_id="other_workflow")

        workflow_actions = self.history.get_workflow_actions(workflow_id)
        self.assertEqual(len(workflow_actions), 2)

        # Actions should be in chronological order
        self.assertEqual(workflow_actions[0]["step_id"], "s1")
        self.assertEqual(workflow_actions[1]["step_id"], "s2")

    def test_search_actions(self):
        """Test searching actions"""
        self.history.record_action("click", {"target": "submit_button"}, result={"clicked": True})
        self.history.record_action("copy", {"content": "hello world"}, result={"copied": True})
        self.history.record_action("paste", {}, result={"pasted": "hello world"})

        # Search in action data
        results = self.history.search_actions("hello")
        self.assertEqual(len(results), 2)

        # Search in action type
        results = self.history.search_actions("button")
        self.assertEqual(len(results), 1)

    def test_get_statistics(self):
        """Test getting action statistics"""
        self.history.record_action("click", {}, status="success", duration_ms=100, module="chrome")
        self.history.record_action("copy", {}, status="success", duration_ms=50, module="vscode")
        self.history.record_action("click", {}, status="failed", duration_ms=200, module="chrome")

        stats = self.history.get_statistics()

        self.assertEqual(stats["total_actions"], 3)
        self.assertEqual(stats["by_status"]["success"], 2)
        self.assertEqual(stats["by_status"]["failed"], 1)
        self.assertEqual(stats["by_type"]["click"], 2)
        self.assertEqual(stats["by_module"]["chrome"], 2)
        self.assertGreater(stats["avg_duration_ms"], 0)

    def test_get_statistics_with_date_filter(self):
        """Test statistics with date filtering"""
        now = datetime.now()
        yesterday = (now - timedelta(days=1)).isoformat()
        tomorrow = (now + timedelta(days=1)).isoformat()

        self.history.record_action("click", {}, status="success")

        # Filter with date range
        stats = self.history.get_statistics(start_date=yesterday, end_date=tomorrow)
        self.assertEqual(stats["total_actions"], 1)

    def test_get_recent_failures(self):
        """Test getting recent failures"""
        self.history.record_action("click", {}, status="success")
        self.history.record_action("copy", {}, status="failed", error="Error 1")
        self.history.record_action("paste", {}, status="failed", error="Error 2")

        failures = self.history.get_recent_failures(limit=10)
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]["status"], "failed")

    def test_clear_history(self):
        """Test clearing action history"""
        self.history.record_action("click", {})
        self.history.record_action("copy", {})

        self.history.clear_history()

        actions = self.history.get_history()
        self.assertEqual(len(actions), 0)

    def test_clear_history_by_workflow(self):
        """Test clearing history for specific workflow"""
        self.history.record_action("step1", {}, workflow_id="wf1")
        self.history.record_action("step2", {}, workflow_id="wf2")

        self.history.clear_history(workflow_id="wf1")

        actions = self.history.get_history()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["workflow_id"], "wf2")

    def test_clear_history_before_date(self):
        """Test clearing history before a specific date"""
        # This is a basic test - in real usage, would need to manipulate timestamps
        self.history.record_action("action1", {})

        future_date = (datetime.now() + timedelta(days=1)).isoformat()
        self.history.clear_history(before_date=future_date)

        actions = self.history.get_history()
        self.assertEqual(len(actions), 0)

    def test_export_history(self):
        """Test exporting action history to JSON"""
        self.history.record_action("click", {"target": "button"}, status="success")
        self.history.record_action("copy", {"content": "text"}, status="success")

        # Export to temporary file
        temp_export = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_export.close()

        try:
            success = self.history.export_history(temp_export.name)
            self.assertTrue(success)

            # Verify file exists and has content
            self.assertTrue(os.path.exists(temp_export.name))
            self.assertGreater(os.path.getsize(temp_export.name), 0)
        finally:
            if os.path.exists(temp_export.name):
                os.unlink(temp_export.name)

    def test_action_with_metadata(self):
        """Test recording action with metadata"""
        metadata = {"user": "test_user", "context": "testing"}

        action_id = self.history.record_action("click", {"target": "button"}, metadata=metadata)

        action = self.history.get_action_by_id(action_id)
        self.assertEqual(action["metadata"], metadata)

    def test_duration_tracking(self):
        """Test duration tracking for actions"""
        self.history.record_action("fast_action", {}, duration_ms=50)
        self.history.record_action("slow_action", {}, duration_ms=500)

        stats = self.history.get_statistics()
        self.assertEqual(stats["avg_duration_ms"], 275)


if __name__ == "__main__":
    unittest.main()
