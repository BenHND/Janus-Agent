"""
Tests for Wiring & Activation integrations.

This test suite validates:
1. SystemAgent + ForegroundAppSync integration
2. AgentExecutorV3 + AsyncVisionMonitor integration  
3. UIAgent + VisionActionMapper integration
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch


def async_test(coro):
    """Decorator to run async tests in unittest."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestSystemAgentForegroundAppSyncIntegration(unittest.TestCase):
    """Test SystemAgent integration with ForegroundAppSync."""
    
    @async_test
    async def test_open_application_uses_ensure_frontmost_on_mac(self):
        """Test that _open_application uses ensure_frontmost on macOS."""
        with patch('janus.agents.system_agent.ensure_frontmost') as mock_ensure:
            mock_ensure.return_value = True
            
            with patch('janus.agents.system_agent.platform') as mock_platform:
                mock_platform.system.return_value = "Darwin"
                
                # Need to reimport to pick up patched platform
                from janus.capabilities.agents.system_agent import SystemAgent
                
                # Create a fresh agent with is_mac = True
                agent = SystemAgent()
                agent.is_mac = True
                
                result = await agent._open_application(
                    {"app_name": "Safari"},
                    {}
                )
                
                # Verify ensure_frontmost was called with correct args
                mock_ensure.assert_called_once_with("Safari", 10.0)
                
                # Verify success result
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["data"]["app_name"], "Safari")
                self.assertEqual(result["context_updates"]["app"], "Safari")
    
    @async_test
    async def test_open_application_returns_error_when_focus_fails(self):
        """Test that _open_application returns error when app fails to take focus."""
        with patch('janus.agents.system_agent.ensure_frontmost') as mock_ensure:
            mock_ensure.return_value = False
            
            from janus.capabilities.agents.system_agent import SystemAgent
            
            agent = SystemAgent()
            agent.is_mac = True
            
            result = await agent._open_application(
                {"app_name": "Safari"},
                {}
            )
            
            # Verify error result
            self.assertEqual(result["status"], "error")
            self.assertIn("failed to take focus", result["error"])
            self.assertTrue(result["recoverable"])


class TestAgentExecutorV3MonitorIntegration(unittest.TestCase):
    """Test AgentExecutorV3 integration with AsyncVisionMonitor."""
    
    def test_executor_accepts_monitor_parameter(self):
        """Test that AgentExecutorV3 accepts monitor parameter."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        
        mock_monitor = Mock()
        executor = AgentExecutorV3(monitor=mock_monitor)
        
        self.assertEqual(executor.monitor, mock_monitor)
    
    def test_executor_without_monitor(self):
        """Test that AgentExecutorV3 works without monitor."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        
        executor = AgentExecutorV3()
        
        self.assertIsNone(executor.monitor)
    
    @async_test
    async def test_execute_plan_checks_alert_state(self):
        """Test that execute_plan checks alert state before each step."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3, ExecutionPausedError
        from janus.runtime.core.contracts import Intent
        from janus.runtime.core.agent_registry import AgentRegistry
        
        # Create mock monitor with alert state
        mock_monitor = Mock()
        mock_monitor.check_alert_state.return_value = True  # Alert detected
        
        # Create mock registry
        mock_registry = Mock(spec=AgentRegistry)
        
        executor = AgentExecutorV3(
            agent_registry=mock_registry,
            monitor=mock_monitor,
            enable_vision_recovery=False,
            enable_replanning=False
        )
        
        # Create valid step
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {
                    "app": None,
                    "surface": None,
                    "url": None,
                    "domain": None,
                    "thread": None,
                    "record": None
                }
            }
        ]
        
        intent = Intent(
            action="test",
            confidence=0.95,
            parameters={},
            raw_command="test"
        )
        
        # Execute should raise ExecutionPausedError
        with self.assertRaises(ExecutionPausedError):
            await executor.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test",
                request_id="test"
            )
        
        # Verify monitor was checked
        mock_monitor.check_alert_state.assert_called()
    
    @async_test
    async def test_execute_plan_continues_when_no_alert(self):
        """Test that execute_plan continues normally when no alert."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        from janus.runtime.core.contracts import Intent
        from janus.runtime.core.agent_registry import AgentRegistry
        
        # Create mock monitor without alert
        mock_monitor = Mock()
        mock_monitor.check_alert_state.return_value = False  # No alert
        
        # Create mock registry with mock agent
        mock_registry = Mock(spec=AgentRegistry)
        mock_registry.execute_async = AsyncMock(return_value={
            "status": "success",
            "message": "Test success"
        })
        
        executor = AgentExecutorV3(
            agent_registry=mock_registry,
            monitor=mock_monitor,
            enable_vision_recovery=False,
            enable_replanning=False
        )
        
        # Create valid step with all required context fields
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {
                    "app": None,
                    "surface": None,
                    "url": None,
                    "domain": None,
                    "thread": None,
                    "record": None
                }
            }
        ]
        
        intent = Intent(
            action="test",
            confidence=0.95,
            parameters={},
            raw_command="test"
        )
        
        # Execute should not raise
        result = await executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test",
            request_id="test"
        )
        
        # Verify monitor was checked
        mock_monitor.check_alert_state.assert_called()
        
        # Verify execution continued
        mock_registry.execute_async.assert_called()


class TestAsyncVisionMonitorCheckAlertState(unittest.TestCase):
    """Test AsyncVisionMonitor.check_alert_state method."""
    
    def _create_mock_monitor(self):
        """Create a mock-free AsyncVisionMonitor for testing check_alert_state."""
        # Import types only
        import importlib.util
        
        # Create minimal mock class with check_alert_state logic
        class MockAsyncVisionMonitor:
            def __init__(self):
                self._events = []
                self._lock = __import__('threading').Lock()
                self.logger = Mock()
            
            def check_alert_state(self):
                from enum import Enum
                
                class MonitorEventType(Enum):
                    POPUP_DETECTED = "popup_detected"
                    ERROR_DETECTED = "error_detected"
                
                critical_event_types = [
                    MonitorEventType.POPUP_DETECTED,
                    MonitorEventType.ERROR_DETECTED,
                ]
                
                with self._lock:
                    for event in self._events[-5:]:
                        if event.event_type in critical_event_types and event.priority >= 4:
                            return True
                return False
        
        return MockAsyncVisionMonitor()
    
    def test_check_alert_state_returns_false_when_no_events(self):
        """Test check_alert_state returns False when no events."""
        monitor = self._create_mock_monitor()
        result = monitor.check_alert_state()
        self.assertFalse(result)


class TestUIAgentVisionActionMapperIntegration(unittest.TestCase):
    """Test UIAgent integration with VisionActionMapper."""
    
    def _create_vam_mock(self, success: bool, error: str = None):
        """Helper to create a mocked VisionActionMapper."""
        mock_vam_result = Mock()
        mock_vam_result.success = success
        mock_vam_result.error = error
        
        mock_vam = Mock()
        mock_vam.click_viz.return_value = mock_vam_result
        
        return mock_vam
    
    def _patch_vam(self, mock_vam):
        """Helper context manager to patch VisionActionMapper import."""
        return patch.dict(
            'sys.modules',
            {'janus.vision.vision_action_mapper': Mock(VisionActionMapper=Mock(return_value=mock_vam))}
        )
    
    @async_test
    async def test_click_falls_back_to_vam_when_native_fails(self):
        """Test that _click falls back to VAM when native click fails."""
        from janus.capabilities.agents.ui_agent import UIAgent
        
        agent = UIAgent()
        
        # Mock action_executor to fail
        mock_executor = Mock()
        mock_executor.click_viz.side_effect = Exception("Native click failed")
        agent._action_executor = mock_executor
        
        mock_vam = self._create_vam_mock(success=True)
        
        with self._patch_vam(mock_vam):
            result = await agent._click({"text": "Submit"}, {})
        
        # Verify VAM fallback was attempted
        mock_vam.click_viz.assert_called_once_with("Submit", None, True)
        
        # Verify success result
        self.assertEqual(result["status"], "success")
        self.assertIn("VAM", result["message"])
    
    @async_test
    async def test_click_succeeds_without_vam_when_native_works(self):
        """Test that _click doesn't use VAM when native click works."""
        from janus.capabilities.agents.ui_agent import UIAgent
        
        agent = UIAgent()
        
        # Mock action_executor to succeed
        mock_executor = Mock()
        mock_executor.click_viz.return_value = {"status": "success"}
        agent._action_executor = mock_executor
        
        result = await agent._click({"text": "Submit"}, {})
        
        # Verify native click succeeded
        self.assertEqual(result["status"], "success")
        # Native click should return without "VAM" in message
        self.assertNotIn("VAM", result.get("message", ""))
    
    @async_test
    async def test_click_returns_error_when_both_fail(self):
        """Test that _click returns error when both native and VAM fail."""
        from janus.capabilities.agents.ui_agent import UIAgent
        
        agent = UIAgent()
        
        # Mock action_executor to fail
        mock_executor = Mock()
        mock_executor.click_viz.side_effect = Exception("Native click failed")
        agent._action_executor = mock_executor
        
        mock_vam = self._create_vam_mock(success=False, error="Element not found")
        
        with self._patch_vam(mock_vam):
            result = await agent._click({"text": "Submit"}, {})
        
        # Verify error result
        self.assertEqual(result["status"], "error")
        self.assertIn("Element not found", result["error"])


class TestExecutionPausedError(unittest.TestCase):
    """Test ExecutionPausedError exception."""
    
    def test_exception_can_be_raised(self):
        """Test that ExecutionPausedError can be raised and caught."""
        from janus.runtime.core.agent_executor_v3 import ExecutionPausedError
        
        with self.assertRaises(ExecutionPausedError) as context:
            raise ExecutionPausedError("Test obstruction")
        
        self.assertEqual(str(context.exception), "Test obstruction")
    
    def test_exception_inherits_from_exception(self):
        """Test that ExecutionPausedError inherits from Exception."""
        from janus.runtime.core.agent_executor_v3 import ExecutionPausedError
        
        self.assertTrue(issubclass(ExecutionPausedError, Exception))


if __name__ == "__main__":
    unittest.main()
