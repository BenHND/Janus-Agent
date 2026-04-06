"""
Tests for Accessibility Layer

Tests the unified accessibility abstraction layer and platform implementations.
"""

import platform
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock heavy dependencies before importing
_mock_modules = {
    'pyautogui': MagicMock(),
    'pywinauto': MagicMock(),
    'pywinauto.uia_defines': MagicMock(),
    'pywinauto.findwindows': MagicMock(),
    'ApplicationServices': MagicMock(),
    'Cocoa': MagicMock(),
    'CoreGraphics': MagicMock(),
}
for mod_name, mock in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock

from janus.platform.accessibility import (
    AccessibilityBackend,
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityState,
    AccessibilityResult,
    get_accessibility_backend,
    create_accessibility_backend,
    reset_accessibility_backend,
    is_accessibility_available,
)
from janus.platform.accessibility.mock_accessibility import MockAccessibility


class TestAccessibilityElement(unittest.TestCase):
    """Test AccessibilityElement dataclass."""
    
    def test_element_creation(self):
        """Test element creation with all attributes."""
        element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.BUTTON,
            name="OK",
            value=None,
            description="Confirm action",
            bounds={"x": 100, "y": 200, "width": 80, "height": 30},
            states={AccessibilityState.ENABLED, AccessibilityState.VISIBLE},
        )
        
        self.assertEqual(element.role, AccessibilityRole.BUTTON)
        self.assertEqual(element.name, "OK")
        self.assertEqual(element.description, "Confirm action")
        self.assertIsNotNone(element.bounds)
        self.assertTrue(element.is_enabled())
        self.assertTrue(element.is_visible())
        self.assertFalse(element.is_focused())
    
    def test_element_states(self):
        """Test element state checking methods."""
        element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.TEXT_FIELD,
            states={AccessibilityState.ENABLED, AccessibilityState.FOCUSED},
        )
        
        self.assertTrue(element.is_enabled())
        self.assertTrue(element.is_focused())
        self.assertFalse(element.is_visible())
    
    def test_element_to_dict(self):
        """Test element serialization to dictionary."""
        element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.CHECKBOX,
            name="Accept terms",
            value="1",
            bounds={"x": 50, "y": 100, "width": 20, "height": 20},
            states={AccessibilityState.CHECKED},
        )
        
        data = element.to_dict()
        self.assertEqual(data["role"], "checkbox")
        self.assertEqual(data["name"], "Accept terms")
        self.assertEqual(data["value"], "1")
        self.assertIn("bounds", data)
        self.assertIn("checked", data["states"])


class TestAccessibilityResult(unittest.TestCase):
    """Test AccessibilityResult container."""
    
    def test_success_result(self):
        """Test successful result."""
        result = AccessibilityResult(
            success=True,
            data={"element": "button"}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["element"], "button")
        self.assertIsNone(result.error)
    
    def test_error_result(self):
        """Test error result."""
        result = AccessibilityResult(
            success=False,
            error="Element not found"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Element not found")
    
    def test_result_to_dict(self):
        """Test result serialization."""
        result = AccessibilityResult(
            success=True,
            data={"count": 5}
        )
        
        data = result.to_dict()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["count"], 5)


class TestMockAccessibility(unittest.TestCase):
    """Test MockAccessibility backend."""
    
    def setUp(self):
        """Create mock backend for testing."""
        self.backend = MockAccessibility()
    
    def test_platform_detection(self):
        """Test platform detection."""
        self.assertEqual(self.backend.get_platform_name(), "Mock")
        self.assertFalse(self.backend.is_available())
    
    def test_find_element_returns_none(self):
        """Test that find_element always returns None."""
        element = self.backend.find_element(
            name="OK",
            role=AccessibilityRole.BUTTON
        )
        self.assertIsNone(element)
    
    def test_find_elements_returns_empty(self):
        """Test that find_elements always returns empty list."""
        elements = self.backend.find_elements(
            role=AccessibilityRole.BUTTON
        )
        self.assertEqual(elements, [])
    
    def test_get_focused_element_returns_none(self):
        """Test that get_focused_element returns None."""
        element = self.backend.get_focused_element()
        self.assertIsNone(element)
    
    def test_click_element_fails(self):
        """Test that click_element always fails."""
        mock_element = AccessibilityElement(
            native_element=Mock(),
            role=AccessibilityRole.BUTTON
        )
        
        result = self.backend.click_element(mock_element)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
    
    def test_get_ui_tree_returns_empty(self):
        """Test that get_ui_tree returns empty dict."""
        tree = self.backend.get_ui_tree()
        self.assertEqual(tree, {})
    
    def test_get_active_app_returns_none(self):
        """Test that get_active_app returns None."""
        app = self.backend.get_active_app()
        self.assertIsNone(app)


class TestAccessibilityFactory(unittest.TestCase):
    """Test accessibility factory functions."""
    
    def setUp(self):
        """Reset singleton before each test."""
        reset_accessibility_backend()
    
    def tearDown(self):
        """Reset singleton after each test."""
        reset_accessibility_backend()
    
    def test_get_backend_singleton(self):
        """Test that get_accessibility_backend returns same instance."""
        backend1 = get_accessibility_backend()
        backend2 = get_accessibility_backend()
        
        self.assertIs(backend1, backend2)
    
    def test_reset_backend(self):
        """Test that reset creates new instance."""
        backend1 = get_accessibility_backend()
        reset_accessibility_backend()
        backend2 = get_accessibility_backend()
        
        self.assertIsNot(backend1, backend2)
    
    def test_create_backend_mock(self):
        """Test creating mock backend explicitly."""
        # Create with unknown platform
        backend = create_accessibility_backend("Unknown")
        
        self.assertIsInstance(backend, MockAccessibility)
        self.assertFalse(backend.is_available())
    
    @unittest.skipUnless(platform.system() == "Windows", "Windows only")
    def test_create_windows_backend(self):
        """Test creating Windows backend on Windows."""
        backend = create_accessibility_backend("Windows")
        
        # Should be Windows backend (might not be available without pywinauto)
        self.assertEqual(backend.get_platform_name(), "Windows")
    
    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_create_macos_backend(self):
        """Test creating macOS backend on macOS."""
        backend = create_accessibility_backend("Darwin")
        
        # Should be macOS backend
        self.assertEqual(backend.get_platform_name(), "macOS")
    
    def test_is_accessibility_available(self):
        """Test is_accessibility_available function."""
        # Should return boolean
        available = is_accessibility_available()
        self.assertIsInstance(available, bool)


class TestAccessibilityRoles(unittest.TestCase):
    """Test AccessibilityRole enum."""
    
    def test_common_roles(self):
        """Test common UI element roles."""
        self.assertEqual(AccessibilityRole.BUTTON.value, "button")
        self.assertEqual(AccessibilityRole.TEXT_FIELD.value, "text_field")
        self.assertEqual(AccessibilityRole.CHECKBOX.value, "checkbox")
        self.assertEqual(AccessibilityRole.WINDOW.value, "window")
    
    def test_role_mapping(self):
        """Test that roles can be used for mapping."""
        role_map = {
            AccessibilityRole.BUTTON: "clickable",
            AccessibilityRole.TEXT_FIELD: "editable",
        }
        
        self.assertEqual(role_map[AccessibilityRole.BUTTON], "clickable")


class TestAccessibilityStates(unittest.TestCase):
    """Test AccessibilityState enum."""
    
    def test_common_states(self):
        """Test common element states."""
        self.assertEqual(AccessibilityState.ENABLED.value, "enabled")
        self.assertEqual(AccessibilityState.VISIBLE.value, "visible")
        self.assertEqual(AccessibilityState.FOCUSED.value, "focused")
        self.assertEqual(AccessibilityState.CHECKED.value, "checked")
    
    def test_state_set_operations(self):
        """Test using states in sets."""
        states = {
            AccessibilityState.ENABLED,
            AccessibilityState.VISIBLE,
        }
        
        self.assertIn(AccessibilityState.ENABLED, states)
        self.assertIn(AccessibilityState.VISIBLE, states)
        self.assertNotIn(AccessibilityState.DISABLED, states)


class TestAccessibilityIntegration(unittest.TestCase):
    """Integration tests for accessibility layer."""
    
    def test_backend_interface_compliance(self):
        """Test that all backends implement required interface."""
        backend = get_accessibility_backend()
        
        # Platform detection methods
        self.assertTrue(hasattr(backend, 'is_available'))
        self.assertTrue(hasattr(backend, 'get_platform_name'))
        
        # Element finding methods
        self.assertTrue(hasattr(backend, 'find_element'))
        self.assertTrue(hasattr(backend, 'find_elements'))
        self.assertTrue(hasattr(backend, 'get_focused_element'))
        
        # Element interaction methods
        self.assertTrue(hasattr(backend, 'click_element'))
        self.assertTrue(hasattr(backend, 'focus_element'))
        self.assertTrue(hasattr(backend, 'set_value'))
        
        # State retrieval methods
        self.assertTrue(hasattr(backend, 'get_element_state'))
        self.assertTrue(hasattr(backend, 'get_element_bounds'))
        
        # Tree inspection methods
        self.assertTrue(hasattr(backend, 'get_ui_tree'))
        self.assertTrue(hasattr(backend, 'get_children'))
        self.assertTrue(hasattr(backend, 'get_parent'))
        
        # Application context methods
        self.assertTrue(hasattr(backend, 'get_active_app'))
        self.assertTrue(hasattr(backend, 'get_app_windows'))
    
    def test_graceful_degradation(self):
        """Test that code handles unavailable accessibility gracefully."""
        backend = get_accessibility_backend()
        
        if not backend.is_available():
            # Should not crash, just return None/empty
            element = backend.find_element(name="Test")
            self.assertIsNone(element)
            
            elements = backend.find_elements(role=AccessibilityRole.BUTTON)
            self.assertEqual(elements, [])


if __name__ == "__main__":
    unittest.main()
