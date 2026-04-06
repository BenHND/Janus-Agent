"""
Tests for correction dialog UI
"""

import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Mock tkinter if not available
if "tkinter" not in sys.modules:
    sys.modules["tkinter"] = Mock()
    sys.modules["tkinter.ttk"] = Mock()

from janus.runtime.core.contracts import Intent
from janus.ui.correction_dialog import CorrectionResult


class TestCorrectionDialog(unittest.TestCase):
    """Test correction dialog functionality"""

    def test_correction_result_creation(self):
        """Test CorrectionResult dataclass"""
        result = CorrectionResult(
            corrected=True,
            correct_interpretation="ouvre Firefox",
            notes="Je voulais Firefox pas Chrome",
        )

        self.assertTrue(result.corrected)
        self.assertEqual(result.correct_interpretation, "ouvre Firefox")
        self.assertEqual(result.notes, "Je voulais Firefox pas Chrome")

    def test_correction_result_cancelled(self):
        """Test cancelled correction result"""
        result = CorrectionResult(corrected=False)

        self.assertFalse(result.corrected)
        self.assertIsNone(result.correct_interpretation)
        self.assertIsNone(result.notes)

    def test_correction_result_with_intent(self):
        """Test correction result with correct intent"""
        result = CorrectionResult(
            corrected=True,
            correct_interpretation="ouvre Firefox",
            correct_intent="open_app",
            notes="Wrong browser",
        )

        self.assertTrue(result.corrected)
        self.assertEqual(result.correct_intent, "open_app")

    def test_intent_parameter_extraction(self):
        """Test extracting parameters from Intent for display"""
        test_intent = Intent(
            action="open_app",
            parameters={"app_name": "Chrome", "target": "window"},
            confidence=0.9,
            raw_command="ouvre Chrome",
        )

        # Verify intent has expected attributes
        self.assertEqual(test_intent.action, "open_app")
        self.assertIn("app_name", test_intent.parameters)
        self.assertEqual(test_intent.parameters["app_name"], "Chrome")
        self.assertEqual(test_intent.confidence, 0.9)


class TestCorrectionIntegration(unittest.TestCase):
    """Test correction dialog integration with learning"""

    def test_correction_callback(self):
        """Test callback is called with result"""
        callback_called = False
        callback_result = None

        def test_callback(result: CorrectionResult):
            nonlocal callback_called, callback_result
            callback_called = True
            callback_result = result

        # Create a result manually to test callback
        result = CorrectionResult(corrected=True, correct_interpretation="test correction")

        # Call callback
        test_callback(result)

        self.assertTrue(callback_called)
        self.assertIsNotNone(callback_result)
        self.assertTrue(callback_result.corrected)
        self.assertEqual(callback_result.correct_interpretation, "test correction")

    def test_correction_with_learning_manager(self):
        """Test correction can be used with learning manager"""
        import os
        import tempfile

        from janus.learning.learning_manager import LearningManager

        # Create temp files
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_file.close()

        try:
            # Create learning manager
            manager = LearningManager(db_path=db_file.name, auto_update=False)

            # First record an action
            action_record = {
                "action_type": "open_app",
                "parameters": {"app_name": "Chrome"},
                "success": True,
                "timestamp": datetime.now().isoformat(),
            }
            manager.correction_listener.record_action(action_record)

            # Simulate correction
            correction_result = CorrectionResult(
                corrected=True,
                correct_interpretation="ouvre Firefox",
                notes="Wrong browser detected",
            )

            # If corrected, record it with correction phrase
            if correction_result.corrected:
                correction = manager.record_user_correction(
                    correction_text="non",  # Use actual correction phrase
                    language="fr",
                    alternative_action={"action": "open_app", "app_name": "Firefox"},
                )

                # Verify correction was recorded
                self.assertIsNotNone(correction)
                self.assertIn("original_action", correction)

                # Verify correction was saved
                summary = manager.get_correction_summary(days=1)
                self.assertGreaterEqual(summary["total_corrections"], 1)

        finally:
            # Clean up
            if os.path.exists(db_file.name):
                os.unlink(db_file.name)


if __name__ == "__main__":
    unittest.main()
