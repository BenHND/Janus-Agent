"""
Tests for Confirmation Dialog (Ticket 6.2)
"""
import threading
import unittest

from janus.ui.confirmation_dialog import ConfirmationDialog
from janus.safety.validation.action_validator import ActionRisk


class TestConfirmationDialog(unittest.TestCase):
    """Test cases for ConfirmationDialog"""

    def setUp(self):
        """Set up test fixtures"""
        self.dialog = ConfirmationDialog(timeout=1000)

    def test_initialization(self):
        """Test dialog initialization"""
        self.assertEqual(self.dialog.timeout, 1000)
        self.assertIsNotNone(self.dialog.result_queue)

    def test_timeout(self):
        """Test dialog timeout behavior"""
        # Set very short timeout
        dialog = ConfirmationDialog(timeout=100)

        # Start confirmation in thread (won't interact with it)
        result = dialog.confirm("test_action", ActionRisk.HIGH, "This is a test")

        # Should timeout and return False
        self.assertFalse(result)

    def test_risk_levels(self):
        """Test that all risk levels are supported"""
        risk_levels = [
            ActionRisk.SAFE,
            ActionRisk.LOW,
            ActionRisk.MEDIUM,
            ActionRisk.HIGH,
            ActionRisk.CRITICAL,
        ]

        # Just verify the dialog can be created with each risk level
        # (won't show UI in tests)
        for risk in risk_levels:
            dialog = ConfirmationDialog(timeout=100)
            # This will timeout but shouldn't crash
            result = dialog.confirm("test", risk)
            self.assertIsInstance(result, bool)

    def test_with_warning_message(self):
        """Test dialog with warning message"""
        dialog = ConfirmationDialog(timeout=100)
        result = dialog.confirm(
            "test_action", ActionRisk.HIGH, warning_message="This action is dangerous"
        )
        # Should timeout
        self.assertFalse(result)

    def test_with_details(self):
        """Test dialog with additional details"""
        dialog = ConfirmationDialog(timeout=100)
        result = dialog.confirm(
            "test_action", ActionRisk.MEDIUM, details="Additional context about the action"
        )
        # Should timeout
        self.assertFalse(result)

    def test_with_all_parameters(self):
        """Test dialog with all parameters"""
        dialog = ConfirmationDialog(timeout=100)
        result = dialog.confirm(
            "delete_file",
            ActionRisk.CRITICAL,
            warning_message="This will permanently delete the file",
            details="File: important_document.pdf",
        )
        # Should timeout and deny
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
