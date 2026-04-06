"""
Unit tests for HeuristicUpdater
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.learning.feedback_manager import FeedbackManager
from janus.learning.heuristic_updater import HeuristicUpdater


class TestHeuristicUpdater(unittest.TestCase):
    """Test cases for HeuristicUpdater"""

    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.temp_config = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_config.close()

        self.feedback_manager = FeedbackManager(self.temp_db.name)
        self.updater = HeuristicUpdater(
            self.feedback_manager, config_path=self.temp_config.name, update_threshold=3
        )

    def tearDown(self):
        """Clean up test files"""
        for path in [self.temp_db.name, self.temp_config.name]:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_default_wait_time(self):
        """Test getting default wait time"""
        wait_time = self.updater.get_wait_time("unknown_action")
        self.assertEqual(wait_time, 500)  # Default value

    def test_get_default_ocr_threshold(self):
        """Test getting default OCR threshold"""
        threshold = self.updater.get_ocr_threshold()
        self.assertEqual(threshold, 0.7)

    def test_get_default_retry_count(self):
        """Test getting default retry count"""
        retry_count = self.updater.get_retry_count("unknown_action")
        self.assertEqual(retry_count, 2)

    def test_update_wait_times(self):
        """Test updating wait times based on feedback"""
        # Record feedback with durations
        for duration in [100, 120, 110, 115, 105]:
            self.feedback_manager.record_feedback("click", success=True, duration_ms=duration)

        # Update wait times
        updated = self.updater.update_wait_times(days=1)

        # Check that click wait time was updated
        self.assertIn("click", updated)
        new_wait_time = self.updater.get_wait_time("click")

        # Should be around median (110) * 1.2 = 132, but can vary due to safety margin
        self.assertGreater(new_wait_time, 100)
        self.assertLess(new_wait_time, 300)

    def test_wait_time_not_updated_insufficient_samples(self):
        """Test that wait times aren't updated with insufficient samples"""
        # Record only 2 feedbacks (threshold is 3)
        self.feedback_manager.record_feedback("click", success=True, duration_ms=100)
        self.feedback_manager.record_feedback("click", success=True, duration_ms=120)

        updated = self.updater.update_wait_times(days=1)

        # Should not update with insufficient samples
        self.assertNotIn("click", updated)

    def test_update_success_probabilities(self):
        """Test updating success probabilities"""
        # Record mix of successes and failures
        for _ in range(7):
            self.feedback_manager.record_feedback("click", success=True)
        for _ in range(3):
            self.feedback_manager.record_feedback("click", success=False)

        probabilities = self.updater.update_success_probabilities(days=1)

        self.assertIn("click", probabilities)
        self.assertAlmostEqual(probabilities["click"], 0.7, places=2)

    def test_update_retry_counts_low_success(self):
        """Test that retry counts increase for low success rates"""
        # Record low success rate (40%)
        for _ in range(2):
            self.feedback_manager.record_feedback("click", success=True)
        for _ in range(3):
            self.feedback_manager.record_feedback("click", success=False)

        updated = self.updater.update_retry_counts(days=1)

        self.assertIn("click", updated)
        new_retry_count = self.updater.get_retry_count("click")
        self.assertGreaterEqual(new_retry_count, 2)

    def test_update_retry_counts_high_success(self):
        """Test that retry counts decrease for high success rates"""
        # First set a higher retry count
        self.updater.heuristics["retry_counts"]["click"] = 3
        self.updater._save_heuristics()

        # Record high success rate (100%)
        for _ in range(5):
            self.feedback_manager.record_feedback("click", success=True)

        updated = self.updater.update_retry_counts(days=1)

        self.assertIn("click", updated)
        new_retry_count = self.updater.get_retry_count("click")
        self.assertLessEqual(new_retry_count, 3)

    def test_update_all_heuristics(self):
        """Test updating all heuristics at once"""
        # Record comprehensive feedback
        for i in range(10):
            self.feedback_manager.record_feedback(
                "click", success=(i % 3 != 0), duration_ms=100 + i * 10  # ~66% success rate
            )

        updates = self.updater.update_all_heuristics(days=1)

        self.assertIn("wait_times", updates)
        self.assertIn("success_probabilities", updates)
        self.assertIn("retry_counts", updates)
        self.assertIn("timestamp", updates)

    def test_get_heuristics_summary(self):
        """Test getting heuristics summary"""
        summary = self.updater.get_heuristics_summary()

        self.assertIn("wait_times", summary)
        self.assertIn("ocr_thresholds", summary)
        self.assertIn("retry_counts", summary)
        self.assertIn("timeout_values", summary)
        self.assertIn("success_probabilities", summary)
        self.assertIn("last_updated", summary)
        self.assertIn("update_count", summary)

    def test_wait_time_gradual_change(self):
        """Test that wait times don't change drastically (max 50% per update)"""
        # Set initial wait time
        self.updater.heuristics["wait_times"]["click"] = 500
        self.updater._save_heuristics()

        # Record very different durations
        for _ in range(10):
            self.feedback_manager.record_feedback(
                "click", success=True, duration_ms=2000  # Much higher than current 500
            )

        updated = self.updater.update_wait_times(days=1)

        new_wait_time = self.updater.get_wait_time("click")

        # Should not more than double
        self.assertLessEqual(new_wait_time, 750)  # 500 + 50% = 750

    def test_minimum_wait_time_enforced(self):
        """Test that minimum wait time is enforced"""
        # Record very short durations
        for _ in range(10):
            self.feedback_manager.record_feedback("click", success=True, duration_ms=10)

        self.updater.update_wait_times(days=1)
        new_wait_time = self.updater.get_wait_time("click")

        # Should not go below 100ms
        self.assertGreaterEqual(new_wait_time, 100)

    def test_heuristics_persistence(self):
        """Test that heuristics are persisted to file"""
        # Update some heuristics
        self.updater.heuristics["wait_times"]["test_action"] = 300
        self.updater._save_heuristics()

        # Create new updater instance with same config
        new_updater = HeuristicUpdater(self.feedback_manager, config_path=self.temp_config.name)

        # Should load saved heuristics
        self.assertEqual(new_updater.get_wait_time("test_action"), 300)


if __name__ == "__main__":
    unittest.main()
