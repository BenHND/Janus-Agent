"""
Unit tests for ARCH-004: Canonical SystemState

Tests the SystemState dataclass and its integration with ActionCoordinator:
1. SystemState creation and validation
2. SystemState immutability (frozen dataclass)
3. SystemState hashing for stagnation detection
4. SystemState serialization (to_dict/from_dict)
5. Stop condition evaluation with SystemState
6. Stagnation detection using SystemState
7. Domain extraction from URLs
"""

import unittest
from datetime import datetime

from janus.runtime.core.contracts import SystemState, StopCondition, StopConditionType
from janus.runtime.core.action_coordinator import ActionCoordinator


class TestSystemStateCreation(unittest.TestCase):
    """Test SystemState dataclass creation and properties"""
    
    def test_create_system_state(self):
        """Test creating a SystemState instance"""
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="Safari",
            window_title="Example Page - Safari",
            url="https://www.example.com/path",
            domain="example.com",
            clipboard="test content",
            performance_ms=15.5
        )
        
        self.assertEqual(state.active_app, "Safari")
        self.assertEqual(state.window_title, "Example Page - Safari")
        self.assertEqual(state.url, "https://www.example.com/path")
        self.assertEqual(state.domain, "example.com")
        self.assertEqual(state.clipboard, "test content")
        self.assertEqual(state.performance_ms, 15.5)
    
    def test_system_state_immutability(self):
        """Test that SystemState is frozen (immutable)"""
        import dataclasses
        
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="Chrome",
            window_title="Google",
            url="https://google.com",
            domain="google.com",
            clipboard="",
            performance_ms=10.0
        )
        
        # Should raise FrozenInstanceError when trying to modify
        with self.assertRaises(dataclasses.FrozenInstanceError):
            state.active_app = "Firefox"
    
    def test_system_state_to_dict(self):
        """Test SystemState.to_dict() serialization"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="VSCode",
            window_title="main.py - VSCode",
            url="",
            domain=None,
            clipboard="code snippet",
            performance_ms=20.3
        )
        
        state_dict = state.to_dict()
        
        self.assertIsInstance(state_dict, dict)
        self.assertEqual(state_dict["active_app"], "VSCode")
        self.assertEqual(state_dict["window_title"], "main.py - VSCode")
        self.assertEqual(state_dict["url"], "")
        self.assertIsNone(state_dict["domain"])
        self.assertEqual(state_dict["clipboard"], "code snippet")
        self.assertEqual(state_dict["performance_ms"], 20.3)
    
    def test_system_state_from_dict(self):
        """Test SystemState.from_dict() deserialization"""
        data = {
            "timestamp": "2024-01-01T12:00:00",
            "active_app": "Terminal",
            "window_title": "bash",
            "url": "",
            "domain": None,
            "clipboard": "ls -la",
            "performance_ms": 5.0
        }
        
        state = SystemState.from_dict(data)
        
        self.assertEqual(state.active_app, "Terminal")
        self.assertEqual(state.window_title, "bash")
        self.assertEqual(state.url, "")
        self.assertIsNone(state.domain)
        self.assertEqual(state.clipboard, "ls -la")
    
    def test_system_state_from_dict_with_defaults(self):
        """Test SystemState.from_dict() provides defaults for missing keys"""
        data = {
            "active_app": "Safari"
        }
        
        state = SystemState.from_dict(data)
        
        self.assertEqual(state.active_app, "Safari")
        self.assertEqual(state.window_title, "")
        self.assertEqual(state.url, "")
        self.assertIsNone(state.domain)
        self.assertEqual(state.clipboard, "")
        self.assertIsInstance(state.timestamp, str)  # Auto-generated


class TestSystemStateHashing(unittest.TestCase):
    """Test SystemState hashing for stagnation detection"""
    
    def test_identical_states_same_hash(self):
        """Test that identical states produce the same hash"""
        state1 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="test",
            performance_ms=10.0
        )
        
        state2 = SystemState(
            timestamp="2024-01-01T12:00:01",  # Different timestamp
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="test",
            performance_ms=15.0  # Different performance
        )
        
        # Hash should be same because it only considers observable state
        # (active_app, window_title, url, clipboard[:100])
        self.assertEqual(hash(state1), hash(state2))
    
    def test_different_apps_different_hash(self):
        """Test that different apps produce different hashes"""
        state1 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        state2 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Chrome",  # Different app
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        self.assertNotEqual(hash(state1), hash(state2))
    
    def test_different_urls_different_hash(self):
        """Test that different URLs produce different hashes"""
        state1 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        state2 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://google.com",  # Different URL
            domain="google.com",
            clipboard="",
            performance_ms=10.0
        )
        
        self.assertNotEqual(hash(state1), hash(state2))
    
    def test_clipboard_truncated_in_hash(self):
        """Test that clipboard is truncated to 100 chars for hashing"""
        long_text = "a" * 200
        
        state1 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard=long_text,
            performance_ms=10.0
        )
        
        state2 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard=long_text[:100] + "different ending",
            performance_ms=10.0
        )
        
        # Should have same hash because only first 100 chars are considered
        self.assertEqual(hash(state1), hash(state2))


class TestStopConditionEvaluation(unittest.TestCase):
    """Test stop condition evaluation with SystemState"""
    
    def setUp(self):
        """Set up test coordinator"""
        self.coordinator = ActionCoordinator(max_iterations=5)
    
    def test_url_contains_condition(self):
        """Test url_contains stop condition"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="YouTube",
            url="https://www.youtube.com/watch?v=123",
            domain="youtube.com",
            clipboard="",
            performance_ms=10.0
        )
        
        condition = StopCondition(
            type=StopConditionType.URL_CONTAINS,
            value="youtube.com"
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, state)
        self.assertTrue(result)
    
    def test_url_contains_condition_negative(self):
        """Test url_contains stop condition when URL doesn't match"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Google",
            url="https://www.google.com",
            domain="google.com",
            clipboard="",
            performance_ms=10.0
        )
        
        condition = StopCondition(
            type=StopConditionType.URL_CONTAINS,
            value="youtube.com"
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, state)
        self.assertFalse(result)
    
    def test_app_active_condition(self):
        """Test app_active stop condition"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Chrome",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        condition = StopCondition(
            type=StopConditionType.APP_ACTIVE,
            value="Chrome"
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, state)
        self.assertTrue(result)
    
    def test_window_title_contains_condition(self):
        """Test window_title_contains stop condition"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Login - Example.com",
            url="https://example.com/login",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        condition = StopCondition(
            type=StopConditionType.WINDOW_TITLE_CONTAINS,
            value="Login"
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, state)
        self.assertTrue(result)
    
    def test_clipboard_contains_condition(self):
        """Test clipboard_contains stop condition"""
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="VSCode",
            window_title="main.py",
            url="",
            domain=None,
            clipboard="def main():\n    pass",
            performance_ms=10.0
        )
        
        condition = StopCondition(
            type=StopConditionType.CLIPBOARD_CONTAINS,
            value="def main"
        )
        
        result = self.coordinator._evaluate_single_stop_condition(condition, state)
        self.assertTrue(result)


class TestDomainExtraction(unittest.TestCase):
    """Test domain extraction from URLs"""
    
    def setUp(self):
        """Set up test coordinator"""
        self.coordinator = ActionCoordinator(max_iterations=5)
    
    def test_extract_domain_with_https(self):
        """Test domain extraction from https URL"""
        domain = self.coordinator._extract_domain("https://www.example.com/path?query=value")
        self.assertEqual(domain, "example.com")
    
    def test_extract_domain_with_http(self):
        """Test domain extraction from http URL"""
        domain = self.coordinator._extract_domain("http://github.com/user/repo")
        self.assertEqual(domain, "github.com")
    
    def test_extract_domain_with_subdomain(self):
        """Test domain extraction preserves subdomain (except www)"""
        domain = self.coordinator._extract_domain("https://api.example.com/v1/users")
        self.assertEqual(domain, "api.example.com")
    
    def test_extract_domain_with_port(self):
        """Test domain extraction removes port"""
        domain = self.coordinator._extract_domain("https://localhost:8080/app")
        self.assertEqual(domain, "localhost")
    
    def test_extract_domain_empty_url(self):
        """Test domain extraction with empty URL"""
        domain = self.coordinator._extract_domain("")
        self.assertIsNone(domain)
    
    def test_extract_domain_no_protocol(self):
        """Test domain extraction without protocol"""
        domain = self.coordinator._extract_domain("www.example.org/page")
        self.assertEqual(domain, "example.org")


class TestStagnationDetection(unittest.TestCase):
    """Test stagnation detection with SystemState"""
    
    def setUp(self):
        """Set up test coordinator with low threshold"""
        self.coordinator = ActionCoordinator(max_iterations=10, stagnation_threshold=3)
        self.coordinator._state_history = []  # Reset history
    
    def test_stagnation_detection_with_identical_states(self):
        """Test that identical states trigger stagnation"""
        from janus.runtime.core.contracts import BurstMetrics
        
        state = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Example",
            url="https://example.com",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        metrics = BurstMetrics()
        
        # First two observations - no stagnation
        self.assertFalse(self.coordinator._detect_stagnation(state, metrics))
        self.assertFalse(self.coordinator._detect_stagnation(state, metrics))
        
        # Third observation - stagnation detected
        self.assertTrue(self.coordinator._detect_stagnation(state, metrics))
        self.assertEqual(metrics.stagnation_events, 1)
    
    def test_no_stagnation_with_changing_states(self):
        """Test that changing states don't trigger stagnation"""
        from janus.runtime.core.contracts import BurstMetrics
        
        metrics = BurstMetrics()
        
        # Create different states
        state1 = SystemState(
            timestamp="2024-01-01T12:00:00",
            active_app="Safari",
            window_title="Page 1",
            url="https://example.com/page1",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        state2 = SystemState(
            timestamp="2024-01-01T12:00:01",
            active_app="Safari",
            window_title="Page 2",
            url="https://example.com/page2",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        state3 = SystemState(
            timestamp="2024-01-01T12:00:02",
            active_app="Safari",
            window_title="Page 3",
            url="https://example.com/page3",
            domain="example.com",
            clipboard="",
            performance_ms=10.0
        )
        
        # Observe different states - no stagnation
        self.assertFalse(self.coordinator._detect_stagnation(state1, metrics))
        self.assertFalse(self.coordinator._detect_stagnation(state2, metrics))
        self.assertFalse(self.coordinator._detect_stagnation(state3, metrics))
        self.assertEqual(metrics.stagnation_events, 0)


if __name__ == "__main__":
    unittest.main()
