"""
Unit tests for StopConditionEvaluator

Tests stop condition evaluation logic.
"""

import unittest
from unittest.mock import MagicMock

from janus.runtime.core.stop_conditions import StopConditionEvaluator
from janus.runtime.core.contracts import StopCondition, StopConditionType, SystemState


class TestStopConditionEvaluator(unittest.TestCase):
    """Test StopConditionEvaluator"""
    
    def setUp(self):
        """Set up test environment"""
        from datetime import datetime
        self.evaluator = StopConditionEvaluator()
        self.system_state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="Safari",
            url="https://example.com/page",
            window_title="Example Page - Safari",
            clipboard="test content",
            domain="example.com",
            performance_ms=10.0
        )
    
    def test_url_contains(self):
        """Test url_contains condition"""
        condition = StopCondition(type=StopConditionType.URL_CONTAINS, value="example.com")
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
        
        # Test negative case
        condition = StopCondition(type=StopConditionType.URL_CONTAINS, value="other.com")
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_url_equals(self):
        """Test url_equals condition"""
        condition = StopCondition(type=StopConditionType.URL_EQUALS, value="https://example.com/page")
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
        
        # Test negative case
        condition = StopCondition(type=StopConditionType.URL_EQUALS, value="https://other.com")
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_app_active(self):
        """Test app_active condition"""
        condition = StopCondition(type=StopConditionType.APP_ACTIVE, value="Safari")
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
        
        # Test negative case
        condition = StopCondition(type=StopConditionType.APP_ACTIVE, value="Chrome")
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_window_title_contains(self):
        """Test window_title_contains condition"""
        condition = StopCondition(type=StopConditionType.WINDOW_TITLE_CONTAINS, value="Example Page")
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
        
        # Test negative case
        condition = StopCondition(type=StopConditionType.WINDOW_TITLE_CONTAINS, value="Other Page")
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_clipboard_contains(self):
        """Test clipboard_contains condition"""
        condition = StopCondition(type=StopConditionType.CLIPBOARD_CONTAINS, value="test")
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
        
        # Test negative case
        condition = StopCondition(type=StopConditionType.CLIPBOARD_CONTAINS, value="missing")
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_evaluate_stop_conditions_empty(self):
        """Test evaluate_stop_conditions with empty list"""
        result = self.evaluator.evaluate_stop_conditions([], self.system_state)
        self.assertFalse(result)
    
    def test_evaluate_stop_conditions_multiple(self):
        """Test evaluate_stop_conditions with multiple conditions"""
        conditions = [
            StopCondition(type=StopConditionType.URL_CONTAINS, value="other.com"),
            StopCondition(type=StopConditionType.APP_ACTIVE, value="Safari"),
        ]
        
        # Should return True because second condition matches
        result = self.evaluator.evaluate_stop_conditions(conditions, self.system_state)
        self.assertTrue(result)
    
    def test_dict_condition_format(self):
        """Test evaluation with dict condition format"""
        condition = {"type": "url_contains", "value": "example.com"}
        
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)
    
    def test_ui_element_visible_no_vision(self):
        """Test ui_element_visible when vision engine not available"""
        condition = StopCondition(type=StopConditionType.UI_ELEMENT_VISIBLE, value="button_1")
        
        # No vision engine
        result = self.evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertFalse(result)
    
    def test_ui_element_visible_with_vision(self):
        """Test ui_element_visible with vision engine"""
        # Mock vision engine
        vision_engine = MagicMock()
        vision_engine.is_available.return_value = True
        vision_engine.get_element_by_id.return_value = {"id": "button_1", "text": "Click me"}
        
        evaluator = StopConditionEvaluator(vision_engine=vision_engine)
        condition = StopCondition(type=StopConditionType.UI_ELEMENT_VISIBLE, value="button_1")
        
        result = evaluator.evaluate_single_stop_condition(condition, self.system_state)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
