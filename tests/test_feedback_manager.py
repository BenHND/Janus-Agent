"""
Unit tests for FeedbackManager
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.learning.feedback_manager import FeedbackManager


class TestFeedbackManager(unittest.TestCase):
    """Test cases for FeedbackManager"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.manager = FeedbackManager(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_record_feedback_success(self):
        """Test recording successful action feedback"""
        feedback_id = self.manager.record_feedback(
            action_type="click",
            success=True,
            action_context={"target": "button", "x": 100, "y": 200},
            duration_ms=150,
            session_id="test_session",
        )
        self.assertIsInstance(feedback_id, int)
        self.assertGreater(feedback_id, 0)

    def test_record_feedback_failure(self):
        """Test recording failed action feedback"""
        feedback_id = self.manager.record_feedback(
            action_type="click",
            success=False,
            error_type="timeout",
            error_message="Element not found",
            duration_ms=5000,
            session_id="test_session",
        )
        self.assertIsInstance(feedback_id, int)
        self.assertGreater(feedback_id, 0)

    def test_get_success_rate_all_actions(self):
        """Test getting overall success rate"""
        # Record mix of successes and failures
        self.manager.record_feedback("click", success=True)
        self.manager.record_feedback("copy", success=True)
        self.manager.record_feedback("paste", success=False)
        self.manager.record_feedback("click", success=True)

        success_rate = self.manager.get_success_rate()
        self.assertEqual(success_rate, 75.0)  # 3 out of 4 successful

    def test_get_success_rate_by_action_type(self):
        """Test getting success rate for specific action type"""
        # Record multiple actions
        self.manager.record_feedback("click", success=True)
        self.manager.record_feedback("click", success=True)
        self.manager.record_feedback("click", success=False)
        self.manager.record_feedback("copy", success=False)

        click_rate = self.manager.get_success_rate(action_type="click")
        self.assertAlmostEqual(click_rate, 66.67, places=1)

    def test_get_action_statistics(self):
        """Test getting detailed action statistics"""
        # Record various actions
        self.manager.record_feedback("click", success=True, duration_ms=100)
        self.manager.record_feedback("click", success=True, duration_ms=200)
        self.manager.record_feedback("click", success=False, error_type="timeout")
        self.manager.record_feedback("copy", success=True, duration_ms=50)

        # Get stats for all actions
        stats = self.manager.get_action_statistics()
        self.assertEqual(stats["total_count"], 4)
        self.assertEqual(stats["success_count"], 3)
        self.assertEqual(stats["failure_count"], 1)
        self.assertEqual(stats["success_rate"], 75.0)

        # Get stats for specific action
        click_stats = self.manager.get_action_statistics(action_type="click")
        self.assertEqual(click_stats["total_count"], 3)
        self.assertEqual(click_stats["success_count"], 2)

    def test_get_recurring_errors(self):
        """Test identifying recurring errors"""
        # Record same error multiple times
        for _ in range(5):
            self.manager.record_feedback(
                "click",
                success=False,
                error_type="element_not_found",
                error_message="Button not visible",
            )

        # Record different error once
        self.manager.record_feedback("copy", success=False, error_type="timeout")

        recurring = self.manager.get_recurring_errors(min_occurrences=3)
        self.assertEqual(len(recurring), 1)
        self.assertEqual(recurring[0]["action_type"], "click")
        self.assertEqual(recurring[0]["error_type"], "element_not_found")
        self.assertEqual(recurring[0]["occurrence_count"], 5)

    def test_get_performance_trend(self):
        """Test getting performance trend over time"""
        # Record actions over multiple days
        now = datetime.now()

        for day_offset in range(5):
            timestamp = (now - timedelta(days=day_offset)).isoformat()
            # Manually insert with specific timestamp
            with self.manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO action_feedback (
                        action_type, success, timestamp, action_context
                    ) VALUES (?, ?, ?, ?)
                """,
                    ("click", 1, timestamp, None),
                )

        trend = self.manager.get_performance_trend("click", days=7)
        self.assertGreater(len(trend), 0)
        self.assertIn("success_rate", trend[0])

    def test_get_feedback_by_session(self):
        """Test retrieving feedback for specific session"""
        session_id = "test_session_123"

        # Record multiple actions in session
        self.manager.record_feedback("click", success=True, session_id=session_id)
        self.manager.record_feedback("copy", success=True, session_id=session_id)
        self.manager.record_feedback("paste", success=False, session_id=session_id)

        # Record action in different session
        self.manager.record_feedback("click", success=True, session_id="other_session")

        session_feedback = self.manager.get_feedback_by_session(session_id)
        self.assertEqual(len(session_feedback), 3)
        self.assertTrue(all(f["session_id"] == session_id for f in session_feedback))

    def test_clear_old_feedback(self):
        """Test clearing old feedback data"""
        # Record old feedback
        old_timestamp = (datetime.now() - timedelta(days=100)).isoformat()
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action_feedback (
                    action_type, success, timestamp, action_context
                ) VALUES (?, ?, ?, ?)
            """,
                ("click", 1, old_timestamp, None),
            )

        # Record recent feedback
        self.manager.record_feedback("click", success=True)

        # Clear old data (keep last 90 days)
        self.manager.clear_old_feedback(days=90)

        # Verify recent data still exists
        stats = self.manager.get_action_statistics(days=1)
        self.assertGreater(stats["total_count"], 0)

    def test_common_errors_in_statistics(self):
        """Test that common errors are reported in statistics"""
        # Record various errors
        self.manager.record_feedback("click", success=False, error_type="timeout")
        self.manager.record_feedback("click", success=False, error_type="timeout")
        self.manager.record_feedback("click", success=False, error_type="element_not_found")

        stats = self.manager.get_action_statistics()
        common_errors = stats["common_errors"]

        self.assertGreater(len(common_errors), 0)
        self.assertEqual(common_errors[0]["error_type"], "timeout")
        self.assertEqual(common_errors[0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
