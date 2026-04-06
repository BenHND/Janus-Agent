"""
Tests for RELIABILITY-001: Single Owner Recovery/Replanning

Ensures ActionCoordinator is the sole owner of recovery strategy and
prevents multiple parallel recovery attempts.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.runtime.core.contracts import (
    Intent,
    RecoveryState,
    SystemState,
    ExecutionResult,
    ActionResult,
)
from janus.runtime.core.agent_registry import AgentRegistry


class TestSingleOwnerRecovery(unittest.TestCase):
    """Test single owner recovery state machine"""

    def setUp(self):
        """Set up test environment"""
        self.mock_registry = MagicMock(spec=AgentRegistry)
        self.coordinator = ActionCoordinator(
            agent_registry=self.mock_registry,
            max_iterations=5,
            stagnation_threshold=2,
        )

    def test_initial_recovery_state_is_idle(self):
        """Test: Recovery state starts as IDLE"""
        self.assertEqual(self.coordinator._get_recovery_state(), RecoveryState.IDLE)
        self.assertEqual(self.coordinator._recovery_attempts, 0)

    def test_reset_recovery_state(self):
        """Test: Reset recovery state clears attempts and sets IDLE"""
        # Manually set to non-idle state
        self.coordinator._recovery_state = RecoveryState.RECOVERING
        self.coordinator._recovery_attempts = 2

        # Reset
        self.coordinator._reset_recovery_state()

        # Verify reset
        self.assertEqual(self.coordinator._get_recovery_state(), RecoveryState.IDLE)
        self.assertEqual(self.coordinator._recovery_attempts, 0)

    def test_set_recovery_state_transitions(self):
        """Test: State transitions are logged properly"""
        with self.assertLogs(level="INFO") as log_context:
            self.coordinator._set_recovery_state(RecoveryState.DETECTING, "test reason")

        self.assertEqual(self.coordinator._get_recovery_state(), RecoveryState.DETECTING)
        self.assertTrue(
            any("idle → detecting" in msg.lower() for msg in log_context.output)
        )

    def test_recovery_prevents_concurrent_attempts(self):
        """Test: Recovery lock prevents concurrent recovery"""

        async def test_concurrent_recovery():
            # Create sample system state
            system_state = SystemState(
                timestamp="2024-01-01T00:00:00",
                active_app="TestApp",
                window_title="Test",
                url="",
                domain=None,
                clipboard="",
                performance_ms=10.0,
            )

            # Manually set state to DETECTING (simulating ongoing recovery)
            self.coordinator._recovery_state = RecoveryState.DETECTING

            # Try to recover (should fail because already recovering)
            result = await self.coordinator._try_recovery(system_state)

            # Should return False (recovery blocked)
            self.assertFalse(result)

            # State should still be DETECTING
            self.assertEqual(
                self.coordinator._get_recovery_state(), RecoveryState.DETECTING
            )

        asyncio.run(test_concurrent_recovery())

    def test_recovery_max_attempts_limit(self):
        """Test: Recovery stops after max attempts"""

        async def test_max_attempts():
            # Create sample system state
            system_state = SystemState(
                timestamp="2024-01-01T00:00:00",
                active_app="TestApp",
                window_title="Test",
                url="",
                domain=None,
                clipboard="",
                performance_ms=10.0,
            )

            # Set attempts to max
            self.coordinator._recovery_attempts = self.coordinator._max_recovery_attempts

            # Try recovery
            result = await self.coordinator._try_recovery(system_state)

            # Should fail due to max attempts
            self.assertFalse(result)

            # State should be FAILED
            self.assertEqual(
                self.coordinator._get_recovery_state(), RecoveryState.FAILED
            )

        asyncio.run(test_max_attempts())

    def test_recovery_successful_flow(self):
        """Test: Successful recovery flow"""

        async def test_success():
            # Create sample system state
            system_state = SystemState(
                timestamp="2024-01-01T00:00:00",
                active_app="TestApp",
                window_title="Test",
                url="",
                domain=None,
                clipboard="",
                performance_ms=10.0,
            )

            # Ensure IDLE state
            self.coordinator._recovery_state = RecoveryState.IDLE

            # Try recovery
            result = await self.coordinator._try_recovery(system_state, "test error")

            # Should succeed
            self.assertTrue(result)

            # Should be back to IDLE after successful recovery
            self.assertEqual(
                self.coordinator._get_recovery_state(), RecoveryState.IDLE
            )

            # Recovery attempts should be incremented
            self.assertEqual(self.coordinator._recovery_attempts, 1)

        asyncio.run(test_success())

    def test_stagnation_triggers_recovery(self):
        """Test: Stagnation detection triggers recovery"""

        async def test_stagnation():
            # Mock reasoner to return valid decision
            mock_reasoner = MagicMock()
            mock_reasoner.available = True
            mock_reasoner.decide_burst_actions = MagicMock(
                return_value={
                    "actions": [{"module": "system", "action": "done", "args": {}}],
                    "stop_when": [],
                    "needs_vision": False,
                    "reasoning": "test",
                }
            )
            self.coordinator._reasoner = mock_reasoner

            # Mock system bridge
            with patch.object(self.coordinator, "_observe_system_state") as mock_obs:
                # Return identical states to trigger stagnation
                state = SystemState(
                    timestamp="2024-01-01T00:00:00",
                    active_app="TestApp",
                    window_title="Same",
                    url="",
                    domain=None,
                    clipboard="",
                    performance_ms=10.0,
                )
                mock_obs.return_value = state

                # Create intent and execute
                intent = Intent(
                    action="test",
                    confidence=0.9,
                    raw_command="test command"
                )

                # Execute should detect stagnation and attempt recovery
                with self.assertLogs(level="WARNING") as log_context:
                    result = await self.coordinator.execute_goal(
                        user_goal="test goal",
                        intent=intent,
                        session_id="test",
                        request_id="test",
                    )

                # Check that stagnation was detected
                self.assertTrue(any('stagnation' in msg.lower() for msg in log_context.output))

        asyncio.run(test_stagnation())

    def test_recovery_state_reset_on_new_goal(self):
        """Test: Recovery state is reset when starting new goal execution"""

        async def test_reset_on_new_goal():
            # Set recovery state to non-idle
            self.coordinator._recovery_state = RecoveryState.FAILED
            self.coordinator._recovery_attempts = 3

            # Mock reasoner
            mock_reasoner = MagicMock()
            mock_reasoner.available = True
            mock_reasoner.decide_burst_actions = MagicMock(
                return_value={
                    "actions": [{"module": "system", "action": "done", "args": {}}],
                    "stop_when": [],
                    "needs_vision": False,
                    "reasoning": "test",
                }
            )
            self.coordinator._reasoner = mock_reasoner

            # Mock observation
            with patch.object(self.coordinator, "_observe_system_state") as mock_obs:
                mock_obs.return_value = SystemState(
                    timestamp="2024-01-01T00:00:00",
                    active_app="TestApp",
                    window_title="Test",
                    url="",
                    domain=None,
                    clipboard="",
                    performance_ms=10.0,
                )

                # Create intent and execute
                intent = Intent(
                    action="test",
                    confidence=0.9,
                    raw_command="test command"
                )

                result = await self.coordinator.execute_goal(
                    user_goal="new goal",
                    intent=intent,
                    session_id="test",
                    request_id="test",
                )

                # Recovery state should be reset to IDLE
                self.assertEqual(
                    self.coordinator._get_recovery_state(), RecoveryState.IDLE
                )
                self.assertEqual(self.coordinator._recovery_attempts, 0)

        asyncio.run(test_reset_on_new_goal())

    def test_decision_error_triggers_recovery(self):
        """Test: Decision errors trigger recovery attempt"""

        async def test_decision_error():
            # Mock reasoner to return error first, then success
            mock_reasoner = MagicMock()
            mock_reasoner.available = True
            
            call_count = [0]
            
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return {"error": "Test error", "error_type": "test_type"}
                else:
                    return {
                        "actions": [{"module": "system", "action": "done", "args": {}}],
                        "stop_when": [],
                        "needs_vision": False,
                        "reasoning": "recovered",
                    }
            
            mock_reasoner.decide_burst_actions = MagicMock(side_effect=side_effect)
            self.coordinator._reasoner = mock_reasoner

            # Mock observation
            with patch.object(self.coordinator, "_observe_system_state") as mock_obs:
                mock_obs.return_value = SystemState(
                    timestamp="2024-01-01T00:00:00",
                    active_app="TestApp",
                    window_title="Test",
                    url="",
                    domain=None,
                    clipboard="",
                    performance_ms=10.0,
                )

                intent = Intent(
                    action="test",
                    confidence=0.9,
                    raw_command="test command"
                )

                with self.assertLogs(level="WARNING") as log_context:
                    result = await self.coordinator.execute_goal(
                        user_goal="test goal",
                        intent=intent,
                        session_id="test",
                        request_id="test",
                    )

                # Should log decision error
                self.assertTrue(
                    any("decision error" in msg.lower() for msg in log_context.output)
                )

                # Recovery should have been attempted
                self.assertGreaterEqual(self.coordinator._recovery_attempts, 1)

        asyncio.run(test_decision_error())


class TestRecoveryStateEnum(unittest.TestCase):
    """Test RecoveryState enum"""

    def test_recovery_state_values(self):
        """Test: RecoveryState has correct values"""
        self.assertEqual(RecoveryState.IDLE.value, "idle")
        self.assertEqual(RecoveryState.DETECTING.value, "detecting")
        self.assertEqual(RecoveryState.RECOVERING.value, "recovering")
        self.assertEqual(RecoveryState.RECOVERED.value, "recovered")
        self.assertEqual(RecoveryState.FAILED.value, "failed")

    def test_recovery_state_count(self):
        """Test: RecoveryState has exactly 5 states"""
        states = list(RecoveryState)
        self.assertEqual(len(states), 5)


if __name__ == "__main__":
    unittest.main()
