"""
Unit tests for ActionCoordinator - Burst OODA Mode

Tests the modern burst OODA loop implementation:
1. Observe phase (system state capture)
2. Decide burst phase (LLM generates 2-6 actions)
3. Execute burst phase (execute actions sequentially)
4. Stop condition evaluation
5. Stagnation detection
"""

import asyncio
import unittest

from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.runtime.core.contracts import SystemState


class TestActionCoordinatorBurstOODA(unittest.TestCase):
    """Test ActionCoordinator burst OODA loop"""
    
    def setUp(self):
        """Set up test environment"""
        self.coordinator = ActionCoordinator(max_iterations=10)
    
    def test_observe_system_state(self):
        """Test OBSERVE phase: system state capture"""
        # This test verifies that _observe_system_state returns a SystemState object
        result = asyncio.run(self.coordinator._observe_system_state())
        
        # Verify it's a SystemState instance
        self.assertIsInstance(result, SystemState)
        self.assertIsInstance(result.active_app, str)
        self.assertIsInstance(result.url, str)
    
    def test_burst_mode_always_enabled(self):
        """Test that burst mode is always enabled (no legacy fallback)"""
        # Burst mode should always be active (no enable_burst_mode parameter)
        coordinator = ActionCoordinator(max_iterations=5)
        
        # Verify burst mode methods exist
        self.assertTrue(hasattr(coordinator, '_decide_burst'))
        self.assertTrue(hasattr(coordinator, '_execute_burst'))
        self.assertTrue(hasattr(coordinator, '_act_single'))
        
        # Verify legacy methods are removed
        self.assertFalse(hasattr(coordinator, '_decide'))
        self.assertFalse(hasattr(coordinator, '_orient'))
        self.assertFalse(hasattr(coordinator, '_act'))
        self.assertFalse(hasattr(coordinator, '_decide_single'))
    
    def test_constructor_no_burst_mode_param(self):
        """Test that constructor no longer accepts enable_burst_mode parameter"""
        # This should work (burst mode is always on)
        coordinator = ActionCoordinator(max_iterations=5)
        self.assertIsNotNone(coordinator)
        
        # Verify no enable_burst_mode attribute exists
        self.assertFalse(hasattr(coordinator, 'enable_burst_mode'))


if __name__ == "__main__":
    unittest.main()
