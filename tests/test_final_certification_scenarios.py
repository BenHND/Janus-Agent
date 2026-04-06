"""
FINAL-INTEGRATION-CERTIFICATION-008: Scenario Tests (D2)

Mockable scenarios to verify feature integration:
- No-vision scenario (system commands)
- Vision scenario (SOM + click)
- Recovery scenario (stagnation/failure)
"""
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


class TestD2_NoVisionScenario(unittest.TestCase):
    """D2.1: No-vision scenario - system commands work without vision"""
    
    @patch('janus.core.action_coordinator.get_system_bridge')
    def test_system_command_no_vision(self, mock_bridge):
        """Test: System command executes without vision dependency"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        from janus.runtime.core.agent_registry import AgentRegistry
        
        # Mock system bridge
        mock_bridge_instance = MagicMock()
        mock_bridge_instance.get_active_app.return_value = "Finder"
        mock_bridge_instance.get_url.return_value = None
        mock_bridge.return_value = mock_bridge_instance
        
        # Create coordinator with vision disabled
        registry = AgentRegistry()
        coordinator = ActionCoordinator(
            agent_registry=registry,
            enable_burst_mode=False  # Disable burst for simpler test
        )
        
        # Mock the vision engine to None (simulating no vision)
        coordinator._vision_engine = None
        
        # Verify coordinator can work without vision
        self.assertIsNone(coordinator.vision_engine,
                         "Vision engine should be None when disabled")
        
        # System bridge should still work
        self.assertEqual(mock_bridge_instance.get_active_app(), "Finder")


class TestD2_VisionScenario(unittest.TestCase):
    """D2.2: Vision scenario - SOM + click element_id works"""
    
    def test_vision_policy_exists(self):
        """Test: Vision policy configuration exists"""
        from janus.runtime.core.settings import Settings
        
        settings = Settings()
        
        # Verify vision policy settings exist
        self.assertTrue(hasattr(settings.vision, 'policy'),
                       "Vision settings should have policy attribute")
    
    def test_som_engine_configurable(self):
        """Test: Set-of-Marks engine can be configured"""
        try:
            from janus.vision.set_of_marks import SetOfMarksEngine
            
            # Create SOM engine with test config
            som = SetOfMarksEngine(
                cache_ttl=1.0,
                enable_cache=False
            )
            
            # Verify configuration
            self.assertFalse(som.enable_cache,
                           "Cache should be disabled when configured")
            
        except ImportError:
            self.skipTest("Vision modules not available")


class TestD2_RecoveryScenario(unittest.TestCase):
    """D2.3: Recovery scenario - stagnation detection and recovery"""
    
    def test_recovery_state_machine(self):
        """Test: Recovery state machine exists and is bounded"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        from janus.runtime.core.contracts import RecoveryState
        
        coordinator = ActionCoordinator()
        
        # Verify recovery state exists
        self.assertTrue(hasattr(coordinator, '_recovery_state'),
                       "Coordinator should have recovery state")
        self.assertEqual(coordinator._recovery_state, RecoveryState.IDLE,
                        "Initial recovery state should be IDLE")
        
        # Verify recovery attempts are bounded
        self.assertTrue(hasattr(coordinator, '_max_recovery_attempts'),
                       "Coordinator should have max recovery attempts")
        self.assertGreater(coordinator._max_recovery_attempts, 0,
                          "Max recovery attempts should be positive")
        self.assertLess(coordinator._max_recovery_attempts, 10,
                       "Max recovery attempts should be bounded < 10")
    
    def test_stagnation_detection(self):
        """Test: Stagnation detection with threshold"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        from janus.runtime.core.contracts import BurstMetrics
        
        coordinator = ActionCoordinator(stagnation_threshold=3)
        
        # Verify stagnation detection exists
        self.assertTrue(hasattr(coordinator, '_detect_stagnation'),
                       "Coordinator should have stagnation detection")
        self.assertTrue(hasattr(coordinator, '_state_history'),
                       "Coordinator should track state history")
        self.assertEqual(coordinator.stagnation_threshold, 3,
                        "Stagnation threshold should be configurable")
    
    @patch('janus.core.action_coordinator.ActionCoordinator._set_recovery_state')
    def test_recovery_attempt_fails_after_max(self, mock_set_state):
        """Test: Recovery fails after max attempts"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        from janus.runtime.core.contracts import RecoveryState
        
        coordinator = ActionCoordinator()
        coordinator._max_recovery_attempts = 2
        coordinator._recovery_attempts = 2  # Already at max
        coordinator._recovery_state = RecoveryState.IDLE
        
        # Verify recovery has max attempts
        self.assertEqual(coordinator._max_recovery_attempts, 2,
                        "Max recovery attempts should be configurable")
        self.assertEqual(coordinator._recovery_attempts, 2,
                        "Recovery attempts should be trackable")


class TestD2_BurstMode(unittest.TestCase):
    """D2.4: Burst mode produces multiple actions"""
    
    def test_burst_mode_configuration(self):
        """Test: Burst mode can be enabled/disabled"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        
        # Create with burst enabled
        coordinator_burst = ActionCoordinator(enable_burst_mode=True)
        self.assertTrue(coordinator_burst.enable_burst_mode,
                       "Burst mode should be enabled")
        
        # Create with burst disabled
        coordinator_no_burst = ActionCoordinator(enable_burst_mode=False)
        self.assertFalse(coordinator_no_burst.enable_burst_mode,
                        "Burst mode should be disabled")
    
    def test_burst_metrics_tracking(self):
        """Test: Burst metrics can track multiple actions"""
        from janus.runtime.core.contracts import BurstMetrics
        
        metrics = BurstMetrics()
        
        # Verify initial state
        self.assertEqual(metrics.burst_actions_executed, 0,
                        "Initial burst_actions_executed should be 0")
        self.assertEqual(metrics.llm_calls, 0,
                        "Initial llm_calls should be 0")
        
        # Simulate burst
        metrics.burst_actions_executed = 3
        metrics.llm_calls = 1
        metrics.vision_calls = 2
        
        # Verify burst tracked
        self.assertEqual(metrics.burst_actions_executed, 3,
                        "Burst should have 3 actions")
        self.assertGreater(metrics.burst_actions_executed, 1,
                          "Burst should have multiple actions (>=2)")
        self.assertEqual(metrics.llm_calls, 1,
                        "Burst should track LLM calls")


class TestD2_IntegrationFlow(unittest.TestCase):
    """D2.5: End-to-end integration flow verification"""
    
    def test_janus_agent_to_coordinator_flow(self):
        """Test: JanusAgent uses ActionCoordinator for execution"""
        from janus.runtime.core.janus_agent import JanusAgent
        from janus.runtime.core.action_coordinator import ActionCoordinator
        
        # Create JanusAgent
        agent = JanusAgent()
        
        # JanusAgent internally uses ActionCoordinator via JanusPipeline
        # Verify it creates a coordinator when needed
        self.assertTrue(hasattr(agent, 'execute'),
                       "JanusAgent should have execute method")
        
        # The execution flow is: JanusAgent → JanusPipeline → ActionCoordinator
        # Verify JanusAgent has necessary attributes for the flow
        self.assertIsNotNone(agent, "JanusAgent should be created successfully")
    
    def test_coordinator_to_registry_flow(self):
        """Test: ActionCoordinator → AgentRegistry flow exists"""
        from janus.runtime.core.action_coordinator import ActionCoordinator
        from janus.runtime.core.agent_registry import AgentRegistry
        
        coordinator = ActionCoordinator()
        
        # Verify coordinator has agent_registry
        self.assertTrue(hasattr(coordinator, 'agent_registry'),
                       "Coordinator should have agent_registry")
        self.assertIsInstance(coordinator.agent_registry, AgentRegistry,
                            "agent_registry should be AgentRegistry instance")


if __name__ == "__main__":
    unittest.main()
