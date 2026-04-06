"""
Unit tests for PerformanceReporter
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.learning.feedback_manager import FeedbackManager
from janus.learning.learning_cache import LearningCache
from janus.learning.performance_reporter import PerformanceReporter


class TestPerformanceReporter(unittest.TestCase):
    """Test cases for PerformanceReporter"""

    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.temp_cache = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_cache.close()
        self.temp_reports_dir = tempfile.mkdtemp()

        self.feedback_manager = FeedbackManager(self.temp_db.name)
        self.learning_cache = LearningCache(self.temp_cache.name)
        self.reporter = PerformanceReporter(
            self.feedback_manager, self.learning_cache, reports_dir=self.temp_reports_dir
        )

    def tearDown(self):
        """Clean up test files"""
        for path in [self.temp_db.name, self.temp_cache.name]:
            if os.path.exists(path):
                os.unlink(path)
        if os.path.exists(self.temp_reports_dir):
            shutil.rmtree(self.temp_reports_dir)

    def test_generate_session_report_no_data(self):
        """Test generating report for session with no data"""
        report = self.reporter.generate_session_report("nonexistent_session", save_to_file=False)

        self.assertEqual(report["status"], "no_data")
        self.assertIn("message", report)

    def test_generate_session_report_with_data(self):
        """Test generating report for session with feedback data"""
        session_id = "test_session_123"

        # Record feedback for session
        self.feedback_manager.record_feedback(
            "click", success=True, duration_ms=100, session_id=session_id
        )
        self.feedback_manager.record_feedback(
            "copy", success=True, duration_ms=50, session_id=session_id
        )
        self.feedback_manager.record_feedback(
            "paste", success=False, error_type="timeout", session_id=session_id
        )

        report = self.reporter.generate_session_report(session_id, save_to_file=False)

        self.assertEqual(report["session_id"], session_id)
        self.assertEqual(report["summary"]["total_actions"], 3)
        self.assertEqual(report["summary"]["successful_actions"], 2)
        self.assertEqual(report["summary"]["failed_actions"], 1)
        self.assertAlmostEqual(report["summary"]["success_rate"], 66.67, places=1)
        self.assertIn("actions_by_type", report)
        self.assertIn("errors", report)

    def test_session_report_actions_by_type(self):
        """Test that session report groups actions by type"""
        session_id = "test_session"

        # Record multiple clicks and copies
        for _ in range(3):
            self.feedback_manager.record_feedback("click", success=True, session_id=session_id)
        for _ in range(2):
            self.feedback_manager.record_feedback("copy", success=False, session_id=session_id)

        report = self.reporter.generate_session_report(session_id, save_to_file=False)

        actions_by_type = report["actions_by_type"]
        self.assertIn("click", actions_by_type)
        self.assertIn("copy", actions_by_type)
        self.assertEqual(actions_by_type["click"]["total"], 3)
        self.assertEqual(actions_by_type["copy"]["total"], 2)

    def test_session_report_save_to_file(self):
        """Test saving session report to file"""
        session_id = "test_session"
        self.feedback_manager.record_feedback("click", success=True, session_id=session_id)

        report = self.reporter.generate_session_report(session_id, save_to_file=True)

        # Check that file was created
        reports = self.reporter.list_reports()
        self.assertGreater(len(reports), 0)

    def test_generate_improvement_report(self):
        """Test generating improvement report"""
        # Record feedback for current period
        for _ in range(8):
            self.feedback_manager.record_feedback("click", success=True)
        for _ in range(2):
            self.feedback_manager.record_feedback("click", success=False)

        # Record feedback for previous period
        old_timestamp = (datetime.now() - timedelta(days=40)).isoformat()
        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            for _ in range(5):
                cursor.execute(
                    """
                    INSERT INTO action_feedback (
                        action_type, success, timestamp, action_context
                    ) VALUES (?, ?, ?, ?)
                """,
                    ("click", 1, old_timestamp, None),
                )
            for _ in range(5):
                cursor.execute(
                    """
                    INSERT INTO action_feedback (
                        action_type, success, timestamp, action_context
                    ) VALUES (?, ?, ?, ?)
                """,
                    ("click", 0, old_timestamp, None),
                )

        report = self.reporter.generate_improvement_report(days=30, comparison_days=30)

        self.assertIn("improvements", report)
        self.assertIn("success_rate_change", report["improvements"])
        self.assertIn("current_period", report)
        self.assertIn("previous_period", report)

    def test_generate_accuracy_report(self):
        """Test generating accuracy report"""
        # Record feedback with durations
        for duration in [100, 110, 120, 105, 115]:
            self.feedback_manager.record_feedback("click", success=True, duration_ms=duration)

        # Store cached wait time in learning cache
        self.learning_cache.store_heuristic("wait_time_click", 110)

        report = self.reporter.generate_accuracy_report(action_type="click", days=1)

        self.assertEqual(report["action_type"], "click")
        self.assertIn("overall_statistics", report)
        self.assertIn("wait_time_accuracy", report)

    def test_generate_comprehensive_report(self):
        """Test generating comprehensive report"""
        # Record various feedback
        for _ in range(5):
            self.feedback_manager.record_feedback("click", success=True, duration_ms=100)
        for _ in range(2):
            self.feedback_manager.record_feedback("click", success=False, error_type="timeout")

        # Update learning cache
        self.learning_cache.increment_action_count(10)
        self.learning_cache.increment_correction_count(2)
        self.learning_cache.store_heuristic("test_heuristic", 123)

        report = self.reporter.generate_comprehensive_report(days=1, save_to_file=False)

        self.assertEqual(report["report_type"], "comprehensive")
        self.assertIn("overall_performance", report)
        self.assertIn("improvements", report)
        self.assertIn("accuracy", report)
        self.assertIn("learning_status", report)
        self.assertIn("issues", report)

    def test_comprehensive_report_learning_status(self):
        """Test that comprehensive report includes learning status"""
        self.learning_cache.store_heuristic("h1", 1)
        self.learning_cache.store_preference("p1", "v1")
        self.learning_cache.increment_action_count(100)

        self.feedback_manager.record_feedback("click", success=True)

        report = self.reporter.generate_comprehensive_report(days=1, save_to_file=False)

        learning_status = report["learning_status"]
        self.assertEqual(learning_status["heuristics_learned"], 1)
        self.assertEqual(learning_status["preferences_stored"], 1)
        self.assertEqual(learning_status["total_actions"], 100)

    def test_list_reports(self):
        """Test listing generated reports"""
        session_id = "test_session"
        self.feedback_manager.record_feedback("click", success=True, session_id=session_id)

        # Generate multiple reports
        self.reporter.generate_session_report(session_id, save_to_file=True)

        # Add small delay to ensure different timestamps
        import time

        time.sleep(0.01)

        self.reporter.generate_session_report(session_id, save_to_file=True)

        reports = self.reporter.list_reports()
        self.assertGreaterEqual(len(reports), 1)

    def test_load_report(self):
        """Test loading a previously generated report"""
        session_id = "test_session"
        self.feedback_manager.record_feedback("click", success=True, session_id=session_id)

        # Generate and save report
        original_report = self.reporter.generate_session_report(session_id, save_to_file=True)

        # Get report path
        reports = self.reporter.list_reports()
        report_path = reports[0]

        # Load report
        loaded_report = self.reporter.load_report(report_path)

        self.assertIsNotNone(loaded_report)
        self.assertEqual(loaded_report["session_id"], session_id)

    def test_report_includes_error_details(self):
        """Test that report includes detailed error information"""
        session_id = "test_session"

        self.feedback_manager.record_feedback(
            "click",
            success=False,
            error_type="element_not_found",
            error_message="Button not visible",
            session_id=session_id,
        )

        report = self.reporter.generate_session_report(session_id, save_to_file=False)

        errors = report["errors"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "element_not_found")
        self.assertEqual(errors[0]["error_message"], "Button not visible")

    def test_improvement_report_recurring_errors(self):
        """Test that improvement report tracks recurring errors"""
        # Record recurring error
        for _ in range(5):
            self.feedback_manager.record_feedback(
                "click", success=False, error_type="timeout", error_message="Element timeout"
            )

        report = self.reporter.generate_improvement_report(days=1, comparison_days=1)

        self.assertIn("recurring_errors", report)
        self.assertIn("count_current", report["recurring_errors"])

    def test_accuracy_report_wait_time_accuracy(self):
        """Test wait time accuracy calculation in accuracy report"""
        # Record feedback with consistent durations
        for _ in range(10):
            self.feedback_manager.record_feedback("click", success=True, duration_ms=100)

        # Store cached wait time close to actual
        self.learning_cache.store_heuristic("wait_time_click", 105)

        report = self.reporter.generate_accuracy_report(action_type="click", days=1)

        wait_time_accuracy = report.get("wait_time_accuracy", {})
        if "click" in wait_time_accuracy:
            accuracy_pct = wait_time_accuracy["click"]["accuracy_pct"]
            # Should be very accurate (close to 100%)
            self.assertGreater(accuracy_pct, 90)

    def test_comprehensive_report_save_to_file(self):
        """Test saving comprehensive report to file"""
        self.feedback_manager.record_feedback("click", success=True)

        report = self.reporter.generate_comprehensive_report(days=1, save_to_file=True)

        # Verify file was created
        reports = self.reporter.list_reports()
        self.assertGreater(len(reports), 0)

        # Verify it's a comprehensive report
        comprehensive_reports = [r for r in reports if "comprehensive" in r]
        self.assertGreater(len(comprehensive_reports), 0)


if __name__ == "__main__":
    unittest.main()
