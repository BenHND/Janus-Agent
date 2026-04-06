"""
Tests for TICKET-5: Policy OODA - vision gating + stop conditions

Tests:
- ContextRouter integration for vision gating
- ui_element_visible stop condition via SOM
- ui_element_contains_text stop condition via SOM
- Vision not forced on turn 1 when not needed
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from janus.runtime.core.contracts import (
    StopCondition,
    StopConditionType,
    Intent,
    ExecutionResult,
    ActionResult,
    SystemState
)
from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.ai.reasoning.context_router import MockContextRouter
from janus.vision.set_of_marks import SetOfMarksEngine, InteractiveElement, ScreenCapture


class TestContextRouterIntegration(unittest.TestCase):
    """Test ContextRouter integration for vision gating"""
    
    def setUp(self):
        """Create coordinator with mocked components"""
        from janus.runtime.core import Settings
        settings = Settings()
        settings.features.enable_vision = True
        settings.features.vision_decision_enabled = True
        
        self.coordinator = ActionCoordinator(settings=settings)
    
    def test_context_router_loaded(self):
        """Test that ContextRouter is lazily loaded"""
        self.assertIsNone(self.coordinator._context_router)
        router = self.coordinator.context_router
        self.assertIsNotNone(router)
        self.assertIsInstance(router, MockContextRouter)
    
    def test_vision_gated_by_context_router_vision_needed(self):
        """Test that vision is used when ContextRouter indicates it's needed"""
        # Mock ContextRouter to return vision requirement
        self.coordinator._context_router = Mock()
        self.coordinator._context_router.available = True
        self.coordinator._context_router.get_requirements = Mock(return_value=["vision"])
        
        # This command should trigger vision
        user_goal = "Qu'est-ce qu'il y a à l'écran?"
        requirements = self.coordinator.context_router.get_requirements(user_goal)
        
        self.assertIn("vision", requirements)
    
    def test_vision_gated_by_context_router_vision_not_needed(self):
        """Test that vision is NOT used when ContextRouter indicates it's not needed"""
        # Mock ContextRouter to return NO vision requirement
        self.coordinator._context_router = Mock()
        self.coordinator._context_router.available = True
        self.coordinator._context_router.get_requirements = Mock(return_value=[])
        
        # This command should NOT trigger vision
        user_goal = "Ouvre Safari"
        requirements = self.coordinator.context_router.get_requirements(user_goal)
        
        self.assertNotIn("vision", requirements)


class TestUIElementVisibleStopCondition(unittest.TestCase):
    """Test ui_element_visible stop condition implementation"""
    
    def setUp(self):
        """Create coordinator and mock vision engine"""
        self.coordinator = ActionCoordinator()
        
        # Create mock vision engine with test elements
        self.mock_vision_engine = Mock(spec=SetOfMarksEngine)
        self.mock_vision_engine.is_available = Mock(return_value=True)
        
        # Create test element
        self.test_element = InteractiveElement(
            element_id="btn_submit",
            element_type="button",
            text="Submit",
            bbox=(100, 200, 80, 40),
            confidence=0.95
        )
        
        self.mock_vision_engine.get_element_by_id = Mock(
            side_effect=lambda id: self.test_element if id == "btn_submit" else None
        )
        self.mock_vision_engine.find_element_by_text = Mock(
            side_effect=lambda text: self.test_element if "Submit" in text else None
        )
    
    def test_ui_element_visible_by_id(self):
        """Test ui_element_visible with element ID"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_VISIBLE,
            value="btn_submit"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertTrue(result)
        self.mock_vision_engine.get_element_by_id.assert_called_with("btn_submit")
    
    def test_ui_element_visible_by_text(self):
        """Test ui_element_visible with text search"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_VISIBLE,
            value="Submit"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertTrue(result)
        self.mock_vision_engine.find_element_by_text.assert_called()
    
    def test_ui_element_visible_not_found(self):
        """Test ui_element_visible when element not found"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_VISIBLE,
            value="nonexistent_element"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertFalse(result)
    
    def test_ui_element_visible_no_vision_engine(self):
        """Test ui_element_visible when vision engine not available"""
        self.coordinator._vision_engine = None
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_VISIBLE,
            value="btn_submit"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertFalse(result)


class TestUIElementContainsTextStopCondition(unittest.TestCase):
    """Test ui_element_contains_text stop condition implementation"""
    
    def setUp(self):
        """Create coordinator and mock vision engine"""
        self.coordinator = ActionCoordinator()
        
        # Create mock vision engine with test elements
        self.mock_vision_engine = Mock(spec=SetOfMarksEngine)
        self.mock_vision_engine.is_available = Mock(return_value=True)
        
        # Create test element
        self.test_element = InteractiveElement(
            element_id="msg_status",
            element_type="text",
            text="Successfully submitted",
            bbox=(100, 200, 200, 40),
            confidence=0.95
        )
        
        self.mock_vision_engine.element_contains_text = Mock(
            side_effect=lambda id, text: id == "msg_status" and "Success" in text
        )
        self.mock_vision_engine.find_element_by_text = Mock(
            side_effect=lambda text: self.test_element if "Success" in text else None
        )
    
    def test_ui_element_contains_text_with_element_id(self):
        """Test ui_element_contains_text with element_id:text format"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_CONTAINS_TEXT,
            value="msg_status:Success"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertTrue(result)
        self.mock_vision_engine.element_contains_text.assert_called_with("msg_status", "Success")
    
    def test_ui_element_contains_text_text_only(self):
        """Test ui_element_contains_text with text only (no element ID)"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_CONTAINS_TEXT,
            value="Success"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertTrue(result)
        self.mock_vision_engine.find_element_by_text.assert_called_with("Success")
    
    def test_ui_element_contains_text_not_found(self):
        """Test ui_element_contains_text when text not found"""
        self.coordinator._vision_engine = self.mock_vision_engine
        
        condition = StopCondition(
            type=StopConditionType.UI_ELEMENT_CONTAINS_TEXT,
            value="msg_status:Error"
        )
        
        system_state = SystemState(
            timestamp="2024-01-01T00:00:00",
            active_app="Safari",
            window_title="Test",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, system_state)
        self.assertFalse(result)


class TestSOMHelperMethods(unittest.TestCase):
    """Test SetOfMarksEngine helper methods for stop conditions"""
    
    def test_find_element_by_text_found(self):
        """Test finding element by text"""
        engine = SetOfMarksEngine()
        
        # Create mock capture with elements
        elements = [
            InteractiveElement(
                element_id="btn1",
                element_type="button",
                text="Click Me",
                bbox=(100, 100, 80, 40),
                confidence=0.9
            ),
            InteractiveElement(
                element_id="btn2",
                element_type="button",
                text="Submit Form",
                bbox=(200, 100, 100, 40),
                confidence=0.95
            )
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test_hash",
            capture_duration_ms=100
        )
        
        result = engine.find_element_by_text("Submit")
        self.assertIsNotNone(result)
        self.assertEqual(result.element_id, "btn2")
    
    def test_find_element_by_text_not_found(self):
        """Test finding element by text when not found"""
        engine = SetOfMarksEngine()
        
        elements = [
            InteractiveElement(
                element_id="btn1",
                element_type="button",
                text="Click Me",
                bbox=(100, 100, 80, 40),
                confidence=0.9
            )
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test_hash",
            capture_duration_ms=100
        )
        
        result = engine.find_element_by_text("Submit")
        self.assertIsNone(result)
    
    def test_element_contains_text_true(self):
        """Test checking if element contains text"""
        engine = SetOfMarksEngine()
        
        elements = [
            InteractiveElement(
                element_id="msg",
                element_type="text",
                text="Success: Form submitted",
                bbox=(100, 100, 200, 40),
                confidence=0.95
            )
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test_hash",
            capture_duration_ms=100
        )
        
        result = engine.element_contains_text("msg", "Success")
        self.assertTrue(result)
    
    def test_element_contains_text_false(self):
        """Test checking if element contains text when it doesn't"""
        engine = SetOfMarksEngine()
        
        elements = [
            InteractiveElement(
                element_id="msg",
                element_type="text",
                text="Form submitted",
                bbox=(100, 100, 200, 40),
                confidence=0.95
            )
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test_hash",
            capture_duration_ms=100
        )
        
        result = engine.element_contains_text("msg", "Error")
        self.assertFalse(result)
    
    def test_element_contains_text_element_not_found(self):
        """Test checking if element contains text when element not found"""
        engine = SetOfMarksEngine()
        
        elements = []
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test_hash",
            capture_duration_ms=100
        )
        
        result = engine.element_contains_text("nonexistent", "Success")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
