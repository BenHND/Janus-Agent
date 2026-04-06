"""
Unit tests for VisualObserver

Tests visual observation and accessibility fallback logic.
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock

from janus.runtime.core.visual_observer import VisualObserver
from janus.platform.accessibility import AccessibilityRole


class MockAccessibilityElement:
    """Mock accessibility element"""
    def __init__(self, name, bounds=None):
        self.name = name
        self.bounds = bounds or [0, 0, 100, 50]


class TestVisualObserver(unittest.TestCase):
    """Test VisualObserver"""
    
    def setUp(self):
        """Set up test environment"""
        self.observer = VisualObserver()
    
    def test_initialization(self):
        """Test VisualObserver initialization"""
        self.assertIsNone(self.observer.vision_engine)
        self.assertIsNone(self.observer.system_bridge)
    
    def test_observe_visual_context_no_vision_no_accessibility(self):
        """Test observe_visual_context when nothing available"""
        async def run_test():
            elements, source = await self.observer.observe_visual_context()
            self.assertEqual(elements, "[]")
            self.assertEqual(source, "none")
        
        asyncio.run(run_test())
    
    def test_observe_visual_context_with_vision(self):
        """Test observe_visual_context with vision engine"""
        # Mock vision engine
        vision_engine = MagicMock()
        vision_engine.is_available.return_value = True
        vision_engine.get_elements_for_reasoner.return_value = '[{"id": "1", "text": "Button"}]'
        
        observer = VisualObserver(vision_engine=vision_engine)
        
        async def run_test():
            elements, source = await observer.observe_visual_context()
            self.assertIn("Button", elements)
            self.assertEqual(source, "vision")
        
        asyncio.run(run_test())
    
    def test_observe_visual_context_with_accessibility(self):
        """Test observe_visual_context with accessibility fallback"""
        # Mock accessibility backend
        accessibility_backend = MagicMock()
        accessibility_backend.is_available.return_value = True
        accessibility_backend.find_elements.return_value = [
            MockAccessibilityElement("Test Button", [10, 20, 100, 50])
        ]
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(system_bridge=system_bridge)
        
        async def run_test():
            elements, source = await observer.observe_visual_context()
            self.assertIn("Test Button", elements)
            self.assertEqual(source, "accessibility")
        
        asyncio.run(run_test())
    
    def test_force_vision_bypasses_accessibility(self):
        """Test that force_vision=True bypasses accessibility (TICKET-ARCHI)"""
        # Mock accessibility backend
        accessibility_backend = MagicMock()
        accessibility_backend.is_available.return_value = True
        accessibility_backend.find_elements.return_value = [
            MockAccessibilityElement("Accessibility Button", [10, 20, 100, 50])
        ]
        
        # Mock vision engine
        vision_engine = MagicMock()
        vision_engine.is_available.return_value = True
        vision_engine.get_elements_for_reasoner.return_value = '[{"id": "1", "text": "Vision Button"}]'
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(vision_engine=vision_engine, system_bridge=system_bridge)
        
        async def run_test():
            # Without force_vision, should use accessibility
            elements, source = await observer.observe_visual_context(force_vision=False)
            self.assertEqual(source, "accessibility")
            self.assertIn("Accessibility Button", elements)
            
            # With force_vision, should use vision
            elements, source = await observer.observe_visual_context(force_vision=True)
            self.assertEqual(source, "vision")
            self.assertIn("Vision Button", elements)
        
        asyncio.run(run_test())
    
    def test_can_use_accessibility_instead_of_vision_no_bridge(self):
        """Test can_use_accessibility_instead_of_vision without system bridge"""
        result = self.observer.can_use_accessibility_instead_of_vision()
        self.assertFalse(result)
    
    def test_can_use_accessibility_instead_of_vision_available(self):
        """Test can_use_accessibility_instead_of_vision when available"""
        # Mock accessibility backend
        accessibility_backend = MagicMock()
        accessibility_backend.is_available.return_value = True
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(system_bridge=system_bridge)
        
        result = observer.can_use_accessibility_instead_of_vision()
        self.assertTrue(result)
    
    def test_map_role_str_to_enum(self):
        """Test map_role_str_to_enum"""
        result = self.observer.map_role_str_to_enum("button")
        self.assertEqual(result, AccessibilityRole.BUTTON)
        
        result = self.observer.map_role_str_to_enum("text_field")
        self.assertEqual(result, AccessibilityRole.TEXT_FIELD)
        
        result = self.observer.map_role_str_to_enum("unknown")
        self.assertIsNone(result)
    
    def test_get_accessibility_elements_json_no_bridge(self):
        """Test get_accessibility_elements_json without system bridge"""
        async def run_test():
            result = await self.observer.get_accessibility_elements_json()
            self.assertEqual(result, "[]")
        
        asyncio.run(run_test())
    
    def test_get_accessibility_elements_json_with_elements(self):
        """Test get_accessibility_elements_json with elements"""
        # Mock accessibility backend
        accessibility_backend = MagicMock()
        accessibility_backend.find_elements.return_value = [
            MockAccessibilityElement("Button 1", [10, 20, 100, 50]),
            MockAccessibilityElement("Button 2", [10, 80, 100, 110])
        ]
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(system_bridge=system_bridge)
        
        async def run_test():
            result = await observer.get_accessibility_elements_json()
            self.assertIn("Button 1", result)
            self.assertIn("Button 2", result)
            self.assertIn('"t": "button"', result)
        
        asyncio.run(run_test())
    
    def test_element_text_truncation(self):
        """Test element text truncation at word boundary"""
        # Create element with very long text
        long_text = "This is a very long button text that should be truncated at word boundary for better readability"
        
        accessibility_backend = MagicMock()
        accessibility_backend.find_elements.return_value = [
            MockAccessibilityElement(long_text, [10, 20, 100, 50])
        ]
        
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(system_bridge=system_bridge)
        
        async def run_test():
            result = await observer.get_accessibility_elements_json()
            # Should be truncated with "..."
            self.assertIn("...", result)
            # Should not contain full long text
            self.assertNotIn(long_text, result)
        
        asyncio.run(run_test())
    
    def test_accessibility_fallback_to_vision_on_empty_elements(self):
        """Test that accessibility falls back to vision when returning 0 elements (TICKET-ARCHI)"""
        # Mock accessibility backend that returns empty list
        accessibility_backend = MagicMock()
        accessibility_backend.is_available.return_value = True
        accessibility_backend.find_elements.return_value = []  # Empty!
        
        # Mock vision engine
        vision_engine = MagicMock()
        vision_engine.is_available.return_value = True
        vision_engine.get_elements_for_reasoner.return_value = '[{"id": "1", "txt": "Vision Button"}]'
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(vision_engine=vision_engine, system_bridge=system_bridge)
        
        async def run_test():
            # Should fallback to vision when accessibility returns 0 elements
            elements, source = await observer.observe_visual_context(force_vision=False)
            self.assertEqual(source, "vision")
            self.assertIn("Vision Button", elements)
        
        asyncio.run(run_test())
    
    def test_accessibility_returns_elements_count_logged(self):
        """Test that we log element count when accessibility succeeds (TICKET-ARCHI)"""
        # Mock accessibility backend with elements
        accessibility_backend = MagicMock()
        accessibility_backend.is_available.return_value = True
        accessibility_backend.find_elements.return_value = [
            MockAccessibilityElement("Button 1", [10, 20, 100, 50]),
            MockAccessibilityElement("Button 2", [10, 80, 100, 110])
        ]
        
        # Mock system bridge
        system_bridge = MagicMock()
        system_bridge.get_accessibility_backend.return_value = accessibility_backend
        
        observer = VisualObserver(system_bridge=system_bridge)
        
        async def run_test():
            # Should use accessibility and return elements
            elements, source = await observer.observe_visual_context()
            self.assertEqual(source, "accessibility")
            # Should have 2 elements
            parsed = json.loads(elements)
            self.assertEqual(len(parsed), 2)
        
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
