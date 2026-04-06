"""
Tests for Action Overlay (Ticket 6.1)
TICKET-FEAT-003: Mini screenshot overlay tests
"""
import time
import unittest
from unittest.mock import MagicMock, patch

from janus.ui.overlay import ActionOverlay, OverlayStatus


class TestActionOverlay(unittest.TestCase):
    """Test cases for ActionOverlay"""

    def setUp(self):
        """Set up test fixtures"""
        self.overlay = ActionOverlay(position="top-right", duration=1000)

    def tearDown(self):
        """Clean up"""
        if self.overlay:
            self.overlay.destroy()

    def test_initialization(self):
        """Test overlay initialization"""
        self.assertEqual(self.overlay.position, "top-right")
        self.assertEqual(self.overlay.duration, 1000)
        self.assertIsNone(self.overlay.window)
        self.assertFalse(self.overlay.is_showing)

    def test_show_message(self):
        """Test showing a message"""
        # Show message (don't wait for UI thread)
        self.overlay.show("Test message", OverlayStatus.IN_PROGRESS)

        # Verify message was queued
        self.assertEqual(self.overlay.current_message, "Test message")

    def test_success_message(self):
        """Test showing success message"""
        self.overlay.success("Operation completed")
        self.assertEqual(self.overlay.current_message, "Operation completed")

    def test_error_message(self):
        """Test showing error message"""
        self.overlay.error("Operation failed")
        self.assertEqual(self.overlay.current_message, "Operation failed")

    def test_warning_message(self):
        """Test showing warning message"""
        self.overlay.warning("Warning message")
        self.assertEqual(self.overlay.current_message, "Warning message")

    def test_update_message(self):
        """Test updating message"""
        self.overlay.show("Initial message")
        self.overlay.update("Updated message")
        self.assertEqual(self.overlay.current_message, "Updated message")

    def test_hide(self):
        """Test hiding overlay"""
        self.overlay.show("Test message")
        self.overlay.hide()
        # Just verify hide doesn't crash
        self.assertTrue(True)

    def test_position_variants(self):
        """Test different position settings"""
        positions = ["top-right", "top-left", "bottom-right", "bottom-left"]

        for position in positions:
            overlay = ActionOverlay(position=position)
            self.assertEqual(overlay.position, position)
            overlay.destroy()

    def test_screenshot_configuration(self):
        """Test screenshot configuration options"""
        overlay = ActionOverlay(
            screenshot_max_size=300,
            screenshot_position="top-left"
        )
        self.assertEqual(overlay.screenshot_max_size, 300)
        self.assertEqual(overlay.screenshot_position, "top-left")
        overlay.destroy()

    def test_status_colors(self):
        """Test status color definitions"""
        self.assertIn(OverlayStatus.IN_PROGRESS, self.overlay.colors)
        self.assertIn(OverlayStatus.SUCCESS, self.overlay.colors)
        self.assertIn(OverlayStatus.ERROR, self.overlay.colors)
        self.assertIn(OverlayStatus.WARNING, self.overlay.colors)

    def test_show_vision_feedback_without_screenshot(self):
        """Test vision feedback without screenshot"""
        verification = {
            "verified": True,
            "confidence": 0.85,
            "reason": "Action verified",
            "duration_ms": 150,
            "method": "ocr"
        }
        self.overlay.show_vision_feedback(verification)
        # Just verify it doesn't crash
        self.assertTrue(True)

    def test_show_vision_feedback_with_screenshot(self):
        """Test vision feedback with mock screenshot"""
        verification = {
            "verified": True,
            "confidence": 0.90,
            "reason": "Action verified",
            "duration_ms": 120,
            "method": "vision"
        }
        
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        # This should handle the screenshot gracefully
        self.overlay.show_vision_feedback(verification, screenshot=mock_image)
        # Just verify it doesn't crash
        self.assertTrue(True)

    def test_hide_screenshot_overlay(self):
        """Test hiding screenshot overlay"""
        # Should handle case where screenshot window doesn't exist
        self.overlay._hide_screenshot_overlay()
        # Just verify it doesn't crash
        self.assertTrue(True)

    def test_show_vision_feedback_failed_verification(self):
        """Test vision feedback with failed verification"""
        verification = {
            "verified": False,
            "confidence": 0.30,
            "reason": "Element not found",
            "duration_ms": 200,
            "method": "ocr"
        }
        self.overlay.show_vision_feedback(verification)
        # Just verify it doesn't crash
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

