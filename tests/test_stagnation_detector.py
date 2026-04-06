"""
Unit tests for StagnationDetector

Tests stagnation detection logic.
"""

import unittest

from janus.runtime.core.stagnation_detector import StagnationDetector
from janus.runtime.core.contracts import SystemState, BurstMetrics
from datetime import datetime


class TestStagnationDetector(unittest.TestCase):
    """Test StagnationDetector"""
    
    def setUp(self):
        """Set up test environment"""
        self.detector = StagnationDetector(stagnation_threshold=3)
    
    def test_initialization(self):
        """Test StagnationDetector initialization"""
        self.assertEqual(self.detector.stagnation_threshold, 3)
        self.assertEqual(len(self.detector._state_history), 0)
    
    def test_no_stagnation_different_states(self):
        """Test no stagnation when states are different"""
        metrics = BurstMetrics()
        
        # Create different states
        for i in range(5):
            state = SystemState(
                timestamp=datetime.now().isoformat(),
                active_app=f"App{i}",
                url=f"https://example{i}.com",
                window_title="Test",
                clipboard="",
                domain=f"example{i}.com",
                performance_ms=10.0
            )
            is_stagnant = self.detector.detect_stagnation(state, metrics)
            self.assertFalse(is_stagnant)
        
        self.assertEqual(metrics.stagnation_events, 0)
    
    def test_stagnation_same_states(self):
        """Test stagnation when same state repeats"""
        metrics = BurstMetrics()
        
        # Create same state
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="SameApp",
            url="https://same.com",
            window_title="Test",
            clipboard="",
            domain="same.com",
            performance_ms=10.0
        )
        
        # First two calls should not trigger stagnation
        self.assertFalse(self.detector.detect_stagnation(state, metrics))
        self.assertFalse(self.detector.detect_stagnation(state, metrics))
        
        # Third call should trigger stagnation (threshold=3)
        self.assertTrue(self.detector.detect_stagnation(state, metrics))
        self.assertEqual(metrics.stagnation_events, 1)
    
    def test_reset(self):
        """Test reset clears state history"""
        metrics = BurstMetrics()
        
        state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="App",
            url="https://example.com",
            window_title="Test",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        # Add some states
        self.detector.detect_stagnation(state, metrics)
        self.detector.detect_stagnation(state, metrics)
        
        self.assertEqual(len(self.detector._state_history), 2)
        
        # Reset
        self.detector.reset()
        self.assertEqual(len(self.detector._state_history), 0)


if __name__ == "__main__":
    unittest.main()
