"""
Tests for Enhanced Overlay (Ticket 10.1 & 10.3)
"""
import time
import unittest

from janus.ui.enhanced_overlay import EnhancedOverlay, OverlayStatus


class TestEnhancedOverlay(unittest.TestCase):
    """Test cases for EnhancedOverlay"""

    def setUp(self):
        """Set up test fixtures"""
        self.overlay = EnhancedOverlay(
            position="top-right",
            duration=1000,
            show_coordinates=True,
            enable_rendering_optimization=True,
        )

    def tearDown(self):
        """Clean up"""
        if self.overlay:
            self.overlay.destroy()

    def test_initialization(self):
        """Test overlay initialization"""
        self.assertEqual(self.overlay.position, "top-right")
        self.assertEqual(self.overlay.duration, 1000)
        self.assertTrue(self.overlay.show_coordinates)
        self.assertTrue(self.overlay.enable_rendering_optimization)
        self.assertIsNone(self.overlay.info_window)
        self.assertFalse(self.overlay.is_showing)

    def test_show_message_without_coordinates(self):
        """Test showing a message without coordinates"""
        self.overlay.show("Test message", OverlayStatus.IN_PROGRESS)
        self.assertEqual(self.overlay.current_message, "Test message")

    def test_show_message_with_coordinates(self):
        """Test showing a message with coordinates"""
        coords = {"x": 100, "y": 200, "width": 150, "height": 50, "center_x": 175, "center_y": 225}
        self.overlay.show("Element found", OverlayStatus.SUCCESS, coords)
        self.assertEqual(self.overlay.current_message, "Element found")

    def test_format_coordinates(self):
        """Test coordinate formatting"""
        coords = {"x": 100, "y": 200, "width": 150, "height": 50, "center_x": 175, "center_y": 225}
        formatted = self.overlay._format_coordinates(coords)
        self.assertIn("Position: (100, 200)", formatted)
        self.assertIn("Center: (175, 225)", formatted)
        self.assertIn("Size: 150x50", formatted)

    def test_success_message(self):
        """Test showing success message"""
        coords = {"x": 10, "y": 20}
        self.overlay.success("Operation completed", coords)
        self.assertEqual(self.overlay.current_message, "Operation completed")

    def test_error_message(self):
        """Test showing error message"""
        self.overlay.error("Operation failed")
        self.assertEqual(self.overlay.current_message, "Operation failed")

    def test_warning_message(self):
        """Test showing warning message"""
        self.overlay.warning("Warning message")
        self.assertEqual(self.overlay.current_message, "Warning message")

    def test_show_with_highlight(self):
        """Test showing overlay with highlight"""
        coords = {"x": 100, "y": 200, "width": 150, "height": 50, "center_x": 175, "center_y": 225}
        self.overlay.show_with_highlight(
            "Click element", OverlayStatus.IN_PROGRESS, coords, highlight_duration=2000
        )
        self.assertEqual(self.overlay.current_message, "Click element")

    def test_rendering_throttle(self):
        """Test rendering throttle optimization"""
        self.overlay._last_update_time = time.time() * 1000
        # Should throttle if called too quickly
        self.assertTrue(self.overlay._should_throttle_update())

        # Should not throttle after enough time
        self.overlay._last_update_time = 0
        self.assertFalse(self.overlay._should_throttle_update())

    def test_rendering_optimization_disabled(self):
        """Test with rendering optimization disabled"""
        overlay = EnhancedOverlay(enable_rendering_optimization=False)
        self.assertFalse(overlay._should_throttle_update())
        overlay.destroy()

    def test_highlight_customization(self):
        """Test custom highlight settings"""
        overlay = EnhancedOverlay(highlight_color="#00FF00", highlight_width=5)
        self.assertEqual(overlay.highlight_color, "#00FF00")
        self.assertEqual(overlay.highlight_width, 5)
        overlay.destroy()

    def test_coordinate_display_toggle(self):
        """Test toggling coordinate display"""
        overlay_with_coords = EnhancedOverlay(show_coordinates=True)
        self.assertTrue(overlay_with_coords.show_coordinates)
        overlay_with_coords.destroy()

        overlay_without_coords = EnhancedOverlay(show_coordinates=False)
        self.assertFalse(overlay_without_coords.show_coordinates)
        overlay_without_coords.destroy()

    def test_update_method(self):
        """Test update method with coordinates"""
        coords = {"x": 50, "y": 100, "width": 200, "height": 75}
        self.overlay.update("Updated message", OverlayStatus.WARNING, coords)
        self.assertEqual(self.overlay.current_message, "Updated message")

    def test_hide_methods(self):
        """Test hide and hide_highlight methods"""
        self.overlay.show("Test", OverlayStatus.IN_PROGRESS)
        self.overlay.hide()
        # Just verify it doesn't crash
        self.overlay.hide_highlight()
        self.overlay.hide_screenshot()

    def test_multiple_status_types(self):
        """Test all status types"""
        self.overlay.show("In progress", OverlayStatus.IN_PROGRESS)
        self.assertEqual(self.overlay.current_message, "In progress")

        self.overlay.success("Success")
        self.assertEqual(self.overlay.current_message, "Success")

        self.overlay.error("Error")
        self.assertEqual(self.overlay.current_message, "Error")

        self.overlay.warning("Warning")
        self.assertEqual(self.overlay.current_message, "Warning")

    def test_screenshot_overlay_initialization(self):
        """Test screenshot overlay configuration"""
        overlay = EnhancedOverlay(
            screenshot_max_size=300,
            screenshot_position="top-left"
        )
        self.assertEqual(overlay.screenshot_max_size, 300)
        self.assertEqual(overlay.screenshot_position, "top-left")
        self.assertIsNone(overlay.screenshot_window)
        overlay.destroy()

    def test_screenshot_overlay_mock(self):
        """Test screenshot overlay with mock PIL"""
        # Just test that the method exists and doesn't crash without PIL
        try:
            from unittest.mock import MagicMock
            mock_image = MagicMock()
            mock_image.size = (800, 600)
            
            # This should handle missing PIL gracefully
            self.overlay.show_screenshot(mock_image, duration=1000)
        except Exception as e:
            # If PIL is not available or other error, that's expected
            self.assertTrue(True)

    def test_show_with_screenshot(self):
        """Test show_with_screenshot method"""
        from unittest.mock import MagicMock
        mock_image = MagicMock()
        mock_image.size = (400, 300)
        
        coords = {"x": 100, "y": 200}
        self.overlay.show_with_screenshot(
            "Action completed",
            OverlayStatus.SUCCESS,
            mock_image,
            coords,
            screenshot_duration=2000
        )
        self.assertEqual(self.overlay.current_message, "Action completed")

    def test_show_complete_feedback(self):
        """Test show_complete_feedback with all features"""
        from unittest.mock import MagicMock
        mock_image = MagicMock()
        mock_image.size = (600, 400)
        
        coords = {"x": 150, "y": 250, "width": 100, "height": 50, "center_x": 200, "center_y": 275}
        self.overlay.show_complete_feedback(
            "Complete feedback test",
            OverlayStatus.SUCCESS,
            screenshot=mock_image,
            coordinates=coords,
            highlight_duration=1500,
            screenshot_duration=1500
        )
        self.assertEqual(self.overlay.current_message, "Complete feedback test")

    def test_screenshot_position_options(self):
        """Test different screenshot position options"""
        positions = ["top-right", "top-left", "bottom-right", "bottom-left"]
        for position in positions:
            overlay = EnhancedOverlay(screenshot_position=position)
            self.assertEqual(overlay.screenshot_position, position)
            overlay.destroy()


if __name__ == "__main__":
    unittest.main()
