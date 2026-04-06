"""
Unit tests for UserCorrectionListener
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.learning.user_correction_listener import UserCorrectionListener


class TestUserCorrectionListener(unittest.TestCase):
    """Test cases for UserCorrectionListener"""

    def setUp(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.listener = UserCorrectionListener(
            correction_history_path=self.temp_file.name,
            recent_actions_size=5,
            correction_window_seconds=10,
        )

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_record_action(self):
        """Test recording an action"""
        action = {
            "action_type": "click",
            "context": {"target": "button"},
            "timestamp": datetime.now().isoformat(),
        }

        self.listener.record_action(action)
        self.assertEqual(len(self.listener.recent_actions), 1)
        self.assertEqual(self.listener.recent_actions[0]["action_type"], "click")

    def test_is_correction_phrase_french(self):
        """Test French correction phrase detection"""
        self.assertTrue(self.listener.is_correction_phrase("non", "fr"))
        self.assertTrue(self.listener.is_correction_phrase("pas ça", "fr"))
        self.assertTrue(self.listener.is_correction_phrase("erreur", "fr"))
        self.assertFalse(self.listener.is_correction_phrase("oui", "fr"))
        self.assertFalse(self.listener.is_correction_phrase("continue", "fr"))

    def test_is_correction_phrase_english(self):
        """Test English correction phrase detection"""
        self.assertTrue(self.listener.is_correction_phrase("no", "en"))
        self.assertTrue(self.listener.is_correction_phrase("not that", "en"))
        self.assertTrue(self.listener.is_correction_phrase("wrong", "en"))
        self.assertFalse(self.listener.is_correction_phrase("yes", "en"))
        self.assertFalse(self.listener.is_correction_phrase("correct", "en"))

    def test_process_correction_with_recent_action(self):
        """Test processing correction with recent action"""
        # Record an action
        action = {
            "action_type": "click",
            "context": {"target": "wrong_button"},
            "timestamp": datetime.now().isoformat(),
        }
        self.listener.record_action(action)

        # Process correction
        correction = self.listener.process_correction("non", language="fr")

        self.assertIsNotNone(correction)
        self.assertEqual(correction["original_action"]["action_type"], "click")
        self.assertEqual(correction["correction_text"], "non")

    def test_process_correction_no_recent_action(self):
        """Test processing correction without recent actions"""
        correction = self.listener.process_correction("non", language="fr")

        # Should return None if no recent actions
        self.assertIsNone(correction)

    def test_process_correction_with_alternative(self):
        """Test processing correction with alternative action"""
        # Record action
        action = {
            "action_type": "click",
            "context": {"target": "button1"},
            "timestamp": datetime.now().isoformat(),
        }
        self.listener.record_action(action)

        # Process correction with alternative
        alternative = {"action_type": "click", "context": {"target": "button2"}}
        correction = self.listener.process_correction(
            "non pas ça", language="fr", alternative_action=alternative
        )

        self.assertIsNotNone(correction)
        self.assertEqual(correction["alternative_action"]["context"]["target"], "button2")

    def test_get_correction_count(self):
        """Test getting correction count"""
        # Record multiple corrections
        for i in range(3):
            action = {"action_type": "click", "timestamp": datetime.now().isoformat()}
            self.listener.record_action(action)
            self.listener.process_correction("non", language="fr")

        count = self.listener.get_correction_count()
        self.assertEqual(count, 3)

    def test_get_correction_count_by_action_type(self):
        """Test getting correction count filtered by action type"""
        # Record corrections for different action types
        for action_type in ["click", "copy", "click"]:
            action = {"action_type": action_type, "timestamp": datetime.now().isoformat()}
            self.listener.record_action(action)
            self.listener.process_correction("non", language="fr")

        click_count = self.listener.get_correction_count(action_type="click")
        self.assertEqual(click_count, 2)

        copy_count = self.listener.get_correction_count(action_type="copy")
        self.assertEqual(copy_count, 1)

    def test_get_correction_patterns(self):
        """Test getting correction patterns"""
        # Record multiple corrections for same action type
        for _ in range(3):
            action = {
                "action_type": "click",
                "context": {"target": "button"},
                "timestamp": datetime.now().isoformat(),
            }
            self.listener.record_action(action)
            self.listener.process_correction("non", language="fr")

        patterns = self.listener.get_correction_patterns("click")

        self.assertEqual(patterns["correction_count"], 3)
        self.assertIn("common_contexts", patterns)
        self.assertIn("alternatives", patterns)

    def test_should_avoid_action(self):
        """Test checking if action should be avoided"""
        context = {"target": "problematic_button"}

        # Record corrections for same context multiple times
        for _ in range(3):
            action = {
                "action_type": "click",
                "context": context,
                "timestamp": datetime.now().isoformat(),
            }
            self.listener.record_action(action)
            self.listener.process_correction("non", language="fr")

        # Should avoid action with this context
        should_avoid = self.listener.should_avoid_action("click", context, threshold=2)
        self.assertTrue(should_avoid)

    def test_should_not_avoid_action_below_threshold(self):
        """Test that action is not avoided below threshold"""
        context = {"target": "button"}

        # Record only 1 correction
        action = {
            "action_type": "click",
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        self.listener.record_action(action)
        self.listener.process_correction("non", language="fr")

        # Should not avoid with threshold of 2
        should_avoid = self.listener.should_avoid_action("click", context, threshold=2)
        self.assertFalse(should_avoid)

    def test_get_preferred_alternative(self):
        """Test getting preferred alternative action"""
        # Record correction with alternative
        action = {
            "action_type": "click",
            "context": {"target": "button1"},
            "timestamp": datetime.now().isoformat(),
        }
        self.listener.record_action(action)

        alternative = {"action_type": "click", "context": {"target": "button2"}}
        self.listener.process_correction("non", language="fr", alternative_action=alternative)

        # Get preferred alternative
        preferred = self.listener.get_preferred_alternative("click", {"target": "button1"})
        self.assertIsNotNone(preferred)
        self.assertEqual(preferred["context"]["target"], "button2")

    def test_get_corrections_summary(self):
        """Test getting corrections summary"""
        # Record various corrections
        for action_type in ["click", "copy", "click"]:
            action = {"action_type": action_type, "timestamp": datetime.now().isoformat()}
            self.listener.record_action(action)
            self.listener.process_correction("non", language="fr")

        summary = self.listener.get_corrections_summary(days=1)

        self.assertEqual(summary["total_corrections"], 3)
        self.assertIn("click", summary["corrections_by_type"])
        self.assertEqual(summary["corrections_by_type"]["click"], 2)

    def test_recent_actions_max_size(self):
        """Test that recent actions respects max size"""
        # Record more actions than max size
        for i in range(10):
            action = {"action_type": f"action_{i}", "timestamp": datetime.now().isoformat()}
            self.listener.record_action(action)

        # Should only keep last 5 (max size from setUp)
        self.assertEqual(len(self.listener.recent_actions), 5)
        self.assertEqual(self.listener.recent_actions[-1]["action_type"], "action_9")

    def test_correction_window(self):
        """Test that corrections only apply within time window"""
        # Record old action (outside window)
        old_action = {
            "action_type": "click",
            "timestamp": (datetime.now() - timedelta(seconds=20)).isoformat(),
        }
        self.listener.record_action(old_action)

        # Record recent action (within window)
        recent_action = {"action_type": "copy", "timestamp": datetime.now().isoformat()}
        self.listener.record_action(recent_action)

        # Process correction
        correction = self.listener.process_correction("non", language="fr")

        # Should correct the recent action, not the old one
        self.assertEqual(correction["original_action"]["action_type"], "copy")

    def test_persistence(self):
        """Test that corrections are persisted"""
        # Record correction
        action = {"action_type": "click", "timestamp": datetime.now().isoformat()}
        self.listener.record_action(action)
        self.listener.process_correction("non", language="fr")

        # Create new listener with same file
        new_listener = UserCorrectionListener(correction_history_path=self.temp_file.name)

        # Should load saved corrections
        count = new_listener.get_correction_count()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
