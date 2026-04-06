"""
Unit tests for Execution Reporting
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from janus.exec.reporting import ExecutionReporter


class TestExecutionReporter(unittest.TestCase):
    """Test cases for ExecutionReporter"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.reporter = ExecutionReporter(
            log_dir=os.path.join(self.temp_dir, "logs"),
            screenshot_dir=os.path.join(self.temp_dir, "screenshots"),
            retention_days=7,
            capture_screenshots=False,  # Disable for tests
        )

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test reporter initialization"""
        self.assertTrue(self.reporter.log_dir.exists())
        self.assertEqual(self.reporter.retention_days, 7)
        self.assertFalse(self.reporter.capture_screenshots)

    def test_save_report(self):
        """Test saving execution report"""
        report = {
            "status": "success",
            "results": [
                {"action": "test", "status": "success"},
            ],
        }

        report_path = self.reporter.save_report(report)

        self.assertTrue(os.path.exists(report_path))

        # Load and verify
        with open(report_path, "r") as f:
            loaded_report = json.load(f)

        self.assertEqual(loaded_report["status"], "success")
        self.assertEqual(len(loaded_report["results"]), 1)

    def test_save_report_with_custom_id(self):
        """Test saving report with custom ID"""
        report = {"status": "success"}
        report_id = "test_report_123"

        report_path = self.reporter.save_report(report, report_id=report_id)

        self.assertIn(report_id, report_path)
        self.assertTrue(os.path.exists(report_path))

    def test_load_report(self):
        """Test loading execution report"""
        report = {
            "status": "success",
            "results": [
                {"action": "test", "status": "success"},
            ],
        }

        report_path = self.reporter.save_report(report)
        loaded_report = self.reporter.load_report(report_path)

        self.assertIsNotNone(loaded_report)
        self.assertEqual(loaded_report["status"], "success")

    def test_load_nonexistent_report(self):
        """Test loading nonexistent report"""
        loaded_report = self.reporter.load_report("/nonexistent/report.json")

        self.assertIsNone(loaded_report)

    def test_list_reports(self):
        """Test listing reports"""
        # Save multiple reports
        for i in range(5):
            report = {"status": "success", "index": i}
            self.reporter.save_report(report, report_id=f"report_{i}")

        reports = self.reporter.list_reports(limit=3)

        self.assertEqual(len(reports), 3)

        # Should be sorted by newest first
        for report_path in reports:
            self.assertTrue(os.path.exists(report_path))

    def test_register_undo_hook(self):
        """Test registering undo hook"""

        def test_undo(params):
            return True

        self.reporter.register_undo_hook("test_action", test_undo)

        hook = self.reporter.get_undo_hook("test_action")
        self.assertIsNotNone(hook)
        self.assertEqual(hook, test_undo)

    def test_get_nonexistent_undo_hook(self):
        """Test getting nonexistent undo hook"""
        hook = self.reporter.get_undo_hook("nonexistent_action")

        self.assertIsNone(hook)

    def test_undo_action_success(self):
        """Test successful undo action"""

        def test_undo(params):
            return True

        self.reporter.register_undo_hook("test_action", test_undo)

        result = self.reporter.undo_action("test_action", {"key": "value"})

        self.assertTrue(result)

    def test_undo_action_failure(self):
        """Test failed undo action"""

        def test_undo(params):
            return False

        self.reporter.register_undo_hook("test_action", test_undo)

        result = self.reporter.undo_action("test_action", {})

        self.assertFalse(result)

    def test_undo_action_no_hook(self):
        """Test undo action with no hook registered"""
        result = self.reporter.undo_action("nonexistent_action", {})

        self.assertFalse(result)

    def test_undo_action_exception(self):
        """Test undo action that raises exception"""

        def test_undo(params):
            raise Exception("Test error")

        self.reporter.register_undo_hook("test_action", test_undo)

        result = self.reporter.undo_action("test_action", {})

        self.assertFalse(result)

    def test_get_statistics(self):
        """Test getting statistics"""
        # Save a report
        self.reporter.save_report({"status": "success"})

        stats = self.reporter.get_statistics()

        self.assertIn("log_dir", stats)
        self.assertIn("report_count", stats)
        self.assertIn("retention_days", stats)
        self.assertIn("undo_hooks_count", stats)

        self.assertGreater(stats["report_count"], 0)
        self.assertEqual(stats["retention_days"], 7)


if __name__ == "__main__":
    unittest.main()
