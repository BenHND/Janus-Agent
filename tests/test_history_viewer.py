"""
Unit tests for History Viewer UI
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.persistence.action_history import ActionHistory


class TestHistoryViewerIntegration(unittest.TestCase):
    """Test cases for History Viewer functionality"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.history = ActionHistory(self.temp_db.name)

        # Add sample data
        self._create_sample_data()

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def _create_sample_data(self):
        """Create sample action history data"""
        # Actions from today
        self.history.record_action(
            action_type="click",
            action_data={"target": "button1", "x": 100, "y": 200},
            result={"status": "success"},
            status="success",
            duration_ms=150,
            module="chrome",
        )

        self.history.record_action(
            action_type="open_app",
            action_data={"app": "vscode"},
            result={"status": "success"},
            status="success",
            duration_ms=500,
            module="system",
        )

        self.history.record_action(
            action_type="copy",
            action_data={"content": "test text"},
            status="failed",
            error="Clipboard access denied",
            duration_ms=50,
            module="clipboard",
        )

        # Workflow actions
        workflow_id = "workflow_test_123"
        self.history.record_action(
            action_type="step1",
            action_data={"step": "initialize"},
            status="success",
            workflow_id=workflow_id,
            step_id="s1",
            module="workflow",
        )

        self.history.record_action(
            action_type="step2",
            action_data={"step": "process"},
            status="success",
            workflow_id=workflow_id,
            step_id="s2",
            module="workflow",
        )

    def test_history_loading(self):
        """Test loading action history"""
        actions = self.history.get_history(limit=100)
        self.assertGreaterEqual(len(actions), 5)

    def test_filter_by_type(self):
        """Test filtering by action type"""
        click_actions = self.history.get_history(action_type="click")
        self.assertEqual(len(click_actions), 1)
        self.assertEqual(click_actions[0]["action_type"], "click")

    def test_filter_by_status(self):
        """Test filtering by status"""
        success_actions = self.history.get_history(status="success")
        failed_actions = self.history.get_history(status="failed")

        self.assertGreater(len(success_actions), 0)
        self.assertGreater(len(failed_actions), 0)

        for action in success_actions:
            self.assertEqual(action["status"], "success")

        for action in failed_actions:
            self.assertEqual(action["status"], "failed")

    def test_filter_by_module(self):
        """Test filtering by module"""
        chrome_actions = self.history.get_history(module="chrome")
        self.assertGreater(len(chrome_actions), 0)

        for action in chrome_actions:
            self.assertEqual(action["module"], "chrome")

    def test_filter_by_workflow(self):
        """Test filtering by workflow ID"""
        workflow_actions = self.history.get_workflow_actions("workflow_test_123")
        self.assertEqual(len(workflow_actions), 2)

        # Actions should be in chronological order
        self.assertEqual(workflow_actions[0]["step_id"], "s1")
        self.assertEqual(workflow_actions[1]["step_id"], "s2")

    def test_search_actions(self):
        """Test searching actions by content"""
        results = self.history.search_actions("button")
        self.assertGreater(len(results), 0)

        # Should find the click action with button1
        found_click = False
        for action in results:
            if action["action_type"] == "click":
                found_click = True
                break
        self.assertTrue(found_click)

    def test_export_json(self):
        """Test exporting history to JSON"""
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()

        try:
            success = self.history.export_history(output_file.name, format="json")
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_file.name))

            # Check file is not empty
            self.assertGreater(os.path.getsize(output_file.name), 0)

            # Verify JSON content
            import json

            with open(output_file.name, "r") as f:
                data = json.load(f)
                self.assertIsInstance(data, list)
                self.assertGreater(len(data), 0)
        finally:
            if os.path.exists(output_file.name):
                os.unlink(output_file.name)

    def test_export_csv(self):
        """Test exporting history to CSV"""
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_file.close()

        try:
            success = self.history.export_history(output_file.name, format="csv")
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_file.name))

            # Check file is not empty
            self.assertGreater(os.path.getsize(output_file.name), 0)

            # Verify CSV content
            import csv

            with open(output_file.name, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertGreater(len(rows), 0)

                # Check that header contains expected columns
                self.assertIn("id", reader.fieldnames)
                self.assertIn("timestamp", reader.fieldnames)
                self.assertIn("action_type", reader.fieldnames)
                self.assertIn("status", reader.fieldnames)
        finally:
            if os.path.exists(output_file.name):
                os.unlink(output_file.name)

    def test_get_statistics(self):
        """Test getting action statistics"""
        stats = self.history.get_statistics()

        self.assertIn("total_actions", stats)
        self.assertIn("by_status", stats)
        self.assertIn("by_type", stats)
        self.assertIn("by_module", stats)
        self.assertIn("avg_duration_ms", stats)

        self.assertGreater(stats["total_actions"], 0)
        self.assertGreater(len(stats["by_status"]), 0)
        self.assertGreater(len(stats["by_type"]), 0)

    def test_date_filtering(self):
        """Test filtering by date range"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Get actions from yesterday to tomorrow (should include all)
        actions = self.history.get_history(
            start_date=yesterday.isoformat(), end_date=tomorrow.isoformat()
        )
        self.assertGreater(len(actions), 0)

        # Get actions from tomorrow onwards (should be empty)
        future_actions = self.history.get_history(start_date=tomorrow.isoformat())
        self.assertEqual(len(future_actions), 0)

    def test_get_action_by_id(self):
        """Test retrieving specific action by ID"""
        # Record a new action and get its ID
        action_id = self.history.record_action(
            action_type="test_action", action_data={"test": "data"}, status="success"
        )

        # Retrieve the action
        action = self.history.get_action_by_id(action_id)
        self.assertIsNotNone(action)
        self.assertEqual(action["id"], action_id)
        self.assertEqual(action["action_type"], "test_action")
        self.assertEqual(action["action_data"]["test"], "data")

    def test_recent_failures(self):
        """Test getting recent failures"""
        failures = self.history.get_recent_failures(limit=10)

        # Should have at least one failure from sample data
        self.assertGreater(len(failures), 0)

        # All should be failed actions
        for action in failures:
            self.assertEqual(action["status"], "failed")


class TestHistoryViewerUI(unittest.TestCase):
    """Test cases for History Viewer UI (without actually creating windows)"""

    def test_import_history_viewer(self):
        """Test that HistoryViewer can be imported"""
        from janus.ui.history_viewer import HistoryViewer

        self.assertIsNotNone(HistoryViewer)

    def test_show_history_viewer_function(self):
        """Test that show_history_viewer function exists"""
        from janus.ui.history_viewer import show_history_viewer

        self.assertIsNotNone(show_history_viewer)

    def test_history_viewer_init(self):
        """Test HistoryViewer initialization"""
        from janus.ui.history_viewer import HistoryViewer

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            viewer = HistoryViewer(db_path=temp_db.name, auto_refresh=False)
            self.assertIsNotNone(viewer)
            self.assertEqual(viewer.db_path, temp_db.name)
            self.assertFalse(viewer.auto_refresh)
            self.assertIsNotNone(viewer.history)
        finally:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)

    def test_theme_colors(self):
        """Test theme color configuration"""
        from janus.ui.history_viewer import HistoryViewer

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            viewer = HistoryViewer(db_path=temp_db.name)

            # Test light theme
            viewer.set_theme("light")
            self.assertEqual(viewer.theme, "light")
            self.assertIn("bg", viewer.colors)
            self.assertIn("fg", viewer.colors)
            self.assertIn("success", viewer.colors)
            self.assertIn("failed", viewer.colors)

            # Test dark theme
            viewer.set_theme("dark")
            self.assertEqual(viewer.theme, "dark")
            self.assertIn("bg", viewer.colors)
            self.assertIn("fg", viewer.colors)
        finally:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)


if __name__ == "__main__":
    unittest.main()
