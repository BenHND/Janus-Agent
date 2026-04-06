"""
Unit tests for RecoveryManager

Tests the recovery state machine and recovery logic.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

from janus.runtime.core.recovery_manager import RecoveryManager
from janus.runtime.core.contracts import RecoveryState, SystemState, ActionResult


class TestRecoveryManager(unittest.TestCase):
    """Test RecoveryManager recovery state machine"""
    
    def setUp(self):
        """Set up test environment"""
        self.recovery_manager = RecoveryManager(max_recovery_attempts=3)
    
    def test_initialization(self):
        """Test RecoveryManager initialization"""
        self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.IDLE)
        self.assertEqual(self.recovery_manager._recovery_attempts, 0)
        self.assertEqual(self.recovery_manager._max_recovery_attempts, 3)
    
    def test_set_recovery_state(self):
        """Test recovery state transitions"""
        self.recovery_manager.set_recovery_state(RecoveryState.DETECTING, "test reason")
        self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.DETECTING)
        
        self.recovery_manager.set_recovery_state(RecoveryState.RECOVERING)
        self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.RECOVERING)
    
    def test_reset_recovery_state(self):
        """Test recovery state reset"""
        self.recovery_manager.set_recovery_state(RecoveryState.RECOVERING)
        self.recovery_manager._recovery_attempts = 2
        
        self.recovery_manager.reset_recovery_state()
        
        self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.IDLE)
        self.assertEqual(self.recovery_manager._recovery_attempts, 0)
    
    def test_build_recovery_prompt(self):
        """Test recovery prompt generation"""
        from datetime import datetime
        system_state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="TestApp",
            url="https://example.com",
            window_title="Test Window",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        action_history = [
            ActionResult(action_type="click", success=False, message="Element not found")
        ]
        
        prompt = self.recovery_manager.build_recovery_prompt(
            user_goal="Test goal",
            system_state=system_state,
            error_context="Test error",
            action_history=action_history
        )
        
        self.assertIn("Test goal", prompt)
        self.assertIn("TestApp", prompt)
        self.assertIn("Test error", prompt)
        self.assertIn("click", prompt)
    
    def test_try_recovery_success(self):
        """Test successful recovery"""
        from datetime import datetime
        system_state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="TestApp",
            url="https://example.com",
            window_title="Test Window",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        # Mock reasoner
        reasoner = MagicMock()
        reasoner.available = False  # Don't use LLM for this test
        
        async def run_test():
            success = await self.recovery_manager.try_recovery(
                system_state=system_state,
                reasoner=reasoner,
                error_context="stagnation",
                action_history=[],
                user_goal="Test goal"
            )
            
            # Recovery should succeed (force_vision fallback)
            self.assertTrue(success)
            self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.IDLE)
            self.assertEqual(self.recovery_manager._recovery_attempts, 1)
        
        asyncio.run(run_test())
    
    def test_try_recovery_max_attempts(self):
        """Test recovery fails after max attempts"""
        from datetime import datetime
        system_state = SystemState(
            timestamp=datetime.now().isoformat(),
            active_app="TestApp",
            url="https://example.com",
            window_title="Test Window",
            clipboard="",
            domain="example.com",
            performance_ms=10.0
        )
        
        reasoner = MagicMock()
        reasoner.available = False
        
        async def run_test():
            # Exhaust attempts
            for i in range(3):
                await self.recovery_manager.try_recovery(
                    system_state=system_state,
                    reasoner=reasoner,
                    error_context="stagnation",
                    action_history=[],
                    user_goal="Test goal"
                )
            
            # Next attempt should fail
            success = await self.recovery_manager.try_recovery(
                system_state=system_state,
                reasoner=reasoner,
                error_context="stagnation",
                action_history=[],
                user_goal="Test goal"
            )
            
            self.assertFalse(success)
            self.assertEqual(self.recovery_manager.get_recovery_state(), RecoveryState.FAILED)
        
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
