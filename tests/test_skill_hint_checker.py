"""
Unit tests for SkillHintChecker

Tests skill hint retrieval logic.
"""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from janus.runtime.core.skill_hint_checker import SkillHintChecker
from janus.runtime.core.contracts import SystemState, SkillMetrics


class MockSkillHint:
    """Mock skill hint"""
    def __init__(self, confidence=0.9, success_count=5):
        self.confidence = confidence
        self.success_count = success_count
    
    def to_context_string(self):
        return f"Hint: confidence={self.confidence}"


class TestSkillHintChecker(unittest.TestCase):
    """Test SkillHintChecker"""
    
    def setUp(self):
        """Set up test environment"""
        self.skill_metrics = SkillMetrics()
        self.checker = SkillHintChecker(skill_metrics=self.skill_metrics)
    
    def test_initialization(self):
        """Test SkillHintChecker initialization"""
        self.assertIsNone(self.checker.semantic_router)
        self.assertIsNotNone(self.checker.skill_metrics)
    
    def test_check_skill_hint_no_router(self):
        """Test check_skill_hint when no semantic router"""
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="App",
            url="https://example.com",
            window_title="Test",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        result = self.checker.check_skill_hint("test goal", state)
        self.assertIsNone(result)
    
    def test_check_skill_hint_with_router_found(self):
        """Test check_skill_hint when hint is found"""
        # Mock semantic router
        semantic_router = MagicMock()
        semantic_router.check_skill_cache.return_value = MockSkillHint()
        
        checker = SkillHintChecker(
            semantic_router=semantic_router,
            skill_metrics=self.skill_metrics
        )
        
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="App",
            url="https://example.com",
            window_title="Test",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        result = checker.check_skill_hint("test goal", state)
        
        self.assertIsNotNone(result)
        self.assertIn("Hint", result)
        semantic_router.check_skill_cache.assert_called_once()
    
    def test_check_skill_hint_with_router_not_found(self):
        """Test check_skill_hint when no hint found"""
        # Mock semantic router
        semantic_router = MagicMock()
        semantic_router.check_skill_cache.return_value = None
        
        checker = SkillHintChecker(
            semantic_router=semantic_router,
            skill_metrics=self.skill_metrics
        )
        
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="App",
            url="https://example.com",
            window_title="Test",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        result = checker.check_skill_hint("test goal", state)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
