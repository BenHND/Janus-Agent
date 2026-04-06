"""
Tests for Accessibility Fast-Path in VisionActionMapper (PERF-M4-002)

Tests the accessibility-first approach before falling back to vision.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch

from janus.vision.vision_action_mapper import VisionActionMapper
from janus.vision.vision_types import ActionResult
from janus.platform.accessibility.base_accessibility import (
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityResult,
    AccessibilityState,
)


class TestAccessibilityFastPath(unittest.TestCase):
    """Test accessibility fast-path in VisionActionMapper"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mapper with accessibility enabled
        self.mapper = VisionActionMapper(
            enable_accessibility_fastpath=True,
        )
        
        # Mock the accessibility backend
        self.mock_backend = Mock()
        self.mapper.accessibility_backend = self.mock_backend

    def test_accessibility_backend_initialized_when_enabled(self):
        """Test that accessibility backend is initialized when enabled"""
        # Create new mapper with accessibility enabled
        with patch('janus.vision.vision_action_mapper.get_accessibility_backend') as mock_get:
            mock_backend = Mock()
            mock_backend.is_available.return_value = True
            mock_get.return_value = mock_backend
            
            mapper = VisionActionMapper(enable_accessibility_fastpath=True)
            
            # Should have initialized backend
            self.assertIsNotNone(mapper.accessibility_backend)
            mock_get.assert_called_once()

    def test_accessibility_backend_not_initialized_when_disabled(self):
        """Test that accessibility backend is not initialized when disabled"""
        mapper = VisionActionMapper(enable_accessibility_fastpath=False)
        
        # Should not have backend
        self.assertIsNone(mapper.accessibility_backend)

    def test_click_via_accessibility_fast_path(self):
        """Test that click uses accessibility first before vision"""
        # Create mock accessibility element
        mock_element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.BUTTON,
            name="OK",
            bounds={"x": 100, "y": 100, "width": 50, "height": 30}
        )
        mock_element.states = {AccessibilityState.ENABLED, AccessibilityState.VISIBLE}
        
        # Mock find_element to return the element
        self.mock_backend.find_element.return_value = mock_element
        
        # Mock click to succeed
        self.mock_backend.click_element.return_value = AccessibilityResult(
            success=True,
            data={"clicked": True}
        )
        
        # Execute click
        result = self.mapper.click_viz("OK")
        
        # Should have succeeded via accessibility
        self.assertTrue(result.success)
        self.assertIn("accessibility", result.message.lower())
        self.assertEqual(result.metadata.get("method"), "accessibility")
        
        # Should have tried accessibility first
        self.mock_backend.find_element.assert_called()
        self.mock_backend.click_element.assert_called_once_with(mock_element)
        
        # Should have tracked AX hit
        stats = self.mapper.get_stats()
        self.assertEqual(stats["ax_fastpath_hits"], 1)
        self.assertEqual(stats["vision_fallbacks"], 0)

    def test_click_fallback_to_vision_when_ax_not_found(self):
        """Test that click falls back to vision when element not found via AX"""
        # Mock find_element to return None (not found)
        self.mock_backend.find_element.return_value = None
        
        # Mock vision-based search
        with patch.object(self.mapper.element_finder, 'find_element_by_text') as mock_find:
            from janus.vision.element_locator import ElementMatch
            mock_element = ElementMatch(
                text="OK",
                x=100,
                y=100,
                width=50,
                height=30,
                confidence=95.0
            )
            mock_find.return_value = mock_element
            
            # Execute click
            with patch('janus.vision.action_executor.pyautogui') as mock_pyautogui:
                result = self.mapper.click_viz("OK")
            
            # Should have fallen back to vision
            self.assertTrue(result.success)
            mock_find.assert_called_once()
            
            # Should have tracked vision fallback
            stats = self.mapper.get_stats()
            self.assertEqual(stats["ax_fastpath_hits"], 0)
            self.assertEqual(stats["vision_fallbacks"], 1)

    def test_click_fallback_to_vision_when_ax_click_fails(self):
        """Test that click falls back to vision when AX click fails"""
        # Create mock element
        mock_element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.BUTTON,
            name="OK",
        )
        mock_element.states = {AccessibilityState.ENABLED}
        
        self.mock_backend.find_element.return_value = mock_element
        
        # Mock click to fail
        self.mock_backend.click_element.return_value = AccessibilityResult(
            success=False,
            error="Click failed"
        )
        
        # Mock vision-based search
        with patch.object(self.mapper.element_finder, 'find_element_by_text') as mock_find:
            from janus.vision.element_locator import ElementMatch
            mock_element = ElementMatch(text="OK", x=100, y=100, width=50, height=30)
            mock_find.return_value = mock_element
            
            # Execute click
            with patch('janus.vision.action_executor.pyautogui'):
                result = self.mapper.click_viz("OK")
            
            # Should have fallen back to vision
            self.assertTrue(result.success)
            mock_find.assert_called_once()

    def test_select_via_accessibility_fast_path(self):
        """Test that select uses accessibility first before vision"""
        # Create mock text field element
        mock_element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.TEXT_FIELD,
            name="Username",
        )
        mock_element.states = {AccessibilityState.ENABLED, AccessibilityState.VISIBLE}
        
        self.mock_backend.find_element.return_value = mock_element
        self.mock_backend.focus_element.return_value = AccessibilityResult(success=True)
        
        # Execute select
        result = self.mapper.select_viz("Username")
        
        # Should have succeeded via accessibility
        self.assertTrue(result.success)
        self.assertIn("accessibility", result.message.lower())
        
        # Should have tried accessibility first
        self.mock_backend.find_element.assert_called()
        self.mock_backend.focus_element.assert_called_once()
        
        # Should have tracked AX hit
        stats = self.mapper.get_stats()
        self.assertEqual(stats["ax_fastpath_hits"], 1)

    def test_accessibility_not_used_for_element_id(self):
        """Test that accessibility is not used when element_id is provided (vision-only)"""
        # Mock backend
        self.mock_backend.find_element.return_value = None
        
        # Mock vision search
        with patch.object(self.mapper.element_finder, 'find_element_by_id') as mock_find_id:
            from janus.vision.element_locator import ElementMatch
            mock_element = ElementMatch(text="button_123", x=100, y=100, width=50, height=30)
            mock_find_id.return_value = mock_element
            
            # Execute click with element_id
            with patch('janus.vision.action_executor.pyautogui'):
                result = self.mapper.click_viz("button", element_id="button_123")
            
            # Should NOT have tried accessibility (element_id is vision-only)
            self.mock_backend.find_element.assert_not_called()
            mock_find_id.assert_called_once()

    def test_accessibility_statistics_tracking(self):
        """Test that statistics track AX hits vs vision fallbacks correctly"""
        # First click: AX success
        mock_element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.BUTTON,
            name="OK",
        )
        mock_element.states = {AccessibilityState.ENABLED}
        
        self.mock_backend.find_element.return_value = mock_element
        self.mock_backend.click_element.return_value = AccessibilityResult(success=True)
        
        self.mapper.click_viz("OK")
        
        # Second click: AX not found, vision fallback
        self.mock_backend.find_element.return_value = None
        
        with patch.object(self.mapper.element_finder, 'find_element_by_text') as mock_find:
            from janus.vision.element_locator import ElementMatch
            mock_find.return_value = ElementMatch(text="Cancel", x=100, y=100, width=50, height=30)
            
            with patch('janus.vision.action_executor.pyautogui'):
                self.mapper.click_viz("Cancel")
        
        # Check stats
        stats = self.mapper.get_stats()
        self.assertEqual(stats["total_actions"], 2)
        self.assertEqual(stats["ax_fastpath_hits"], 1)
        self.assertEqual(stats["vision_fallbacks"], 1)
        self.assertEqual(stats["successful_actions"], 2)


if __name__ == '__main__':
    unittest.main()
