"""
Tests for TICKET 005 - ExecutionEngineV3 and AgentRegistry

Tests the new JSON V3 execution engine with stable module routing.
"""

import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.agent_registry import AgentRegistry, get_global_agent_registry, reset_global_agent_registry
from janus.runtime.core.contracts import Intent
from janus.runtime.core.execution_engine_v3 import (
    ErrorClassifier,
    ExecutionEngineV3,
    StepValidator,
    StepValidationResult,
)


class TestStepValidator(unittest.TestCase):
    """Test step validation for JSON V3 format"""

    def setUp(self):
        self.validator = StepValidator()

    def test_valid_step(self):
        """Test validation of a valid step"""
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://youtube.com"},
            "context": {"app": "Safari"},
        }
        
        result = self.validator.validate_step(step)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)

    def test_valid_step_minimal(self):
        """Test validation of minimal valid step (module + action only)"""
        step = {
            "module": "system",
            "action": "open_app",
        }
        
        result = self.validator.validate_step(step)
        self.assertTrue(result.is_valid)

    def test_missing_module(self):
        """Test validation fails when module is missing"""
        step = {
            "action": "open_url",
            "args": {"url": "https://youtube.com"},
        }
        
        result = self.validator.validate_step(step)
        self.assertFalse(result.is_valid)
        self.assertIn("module", result.error_message.lower())

    def test_missing_action(self):
        """Test validation fails when action is missing"""
        step = {
            "module": "browser",
            "args": {"url": "https://youtube.com"},
        }
        
        result = self.validator.validate_step(step)
        self.assertFalse(result.is_valid)
        self.assertIn("action", result.error_message.lower())

    def test_invalid_args_type(self):
        """Test validation fails when args is not a dict"""
        step = {
            "module": "browser",
            "action": "open_url",
            "args": "invalid",  # Should be dict
        }
        
        result = self.validator.validate_step(step)
        self.assertFalse(result.is_valid)
        self.assertIn("args", result.error_message.lower())

    def test_invalid_context_type_warning(self):
        """Test validation warns when context is not a dict"""
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {},
            "context": "invalid",  # Should be dict
        }
        
        result = self.validator.validate_step(step)
        # Context is optional, so step is still valid
        self.assertTrue(result.is_valid)
        # But should have a warning
        self.assertIsNotNone(result.warnings)


class TestErrorClassifier(unittest.TestCase):
    """Test error classification for recovery decisions"""

    def setUp(self):
        self.classifier = ErrorClassifier()

    def test_timeout_error(self):
        """Test timeout error classification"""
        result = self.classifier.classify_error("Connection timeout after 30s")
        self.assertTrue(result["recoverable"])
        self.assertTrue(result["retry_recommended"])
        self.assertFalse(result["replan_recommended"])
        self.assertEqual(result["error_category"], "timeout")

    def test_network_error(self):
        """Test network error classification"""
        result = self.classifier.classify_error("Network connection failed")
        self.assertTrue(result["recoverable"])
        self.assertTrue(result["retry_recommended"])
        self.assertEqual(result["error_category"], "network")

    def test_permission_error(self):
        """Test permission error classification"""
        result = self.classifier.classify_error("Access denied: permission required")
        self.assertFalse(result["recoverable"])
        self.assertFalse(result["retry_recommended"])
        self.assertEqual(result["error_category"], "permission")

    def test_element_not_found(self):
        """Test element not found classification"""
        result = self.classifier.classify_error("Element not found with selector #button")
        self.assertTrue(result["recoverable"])
        self.assertTrue(result["retry_recommended"])
        self.assertTrue(result["replan_recommended"])
        self.assertEqual(result["error_category"], "element_not_found")

    def test_module_not_found(self):
        """Test module not found classification"""
        result = self.classifier.classify_error("Module 'unknown_module' not registered")
        self.assertFalse(result["recoverable"])
        self.assertTrue(result["replan_recommended"])
        self.assertEqual(result["error_category"], "module_not_found")

    def test_unknown_error(self):
        """Test unknown error classification (default)"""
        result = self.classifier.classify_error("Some random error message")
        self.assertTrue(result["recoverable"])
        self.assertTrue(result["retry_recommended"])
        self.assertEqual(result["error_category"], "unknown")


class TestAgentRegistry(unittest.TestCase):
    """Test agent registry for module routing"""

    def setUp(self):
        self.registry = AgentRegistry()
        
        # Create mock agents
        self.mock_system_agent = MagicMock()
        self.mock_system_agent.__class__.__name__ = "MockSystemAgent"
        self.mock_system_agent.execute.return_value = {
            "status": "success",
            "message": "Action completed",
        }
        
        self.mock_browser_agent = MagicMock()
        self.mock_browser_agent.__class__.__name__ = "MockBrowserAgent"
        self.mock_browser_agent.execute.return_value = {
            "status": "success",
            "message": "Browser action completed",
        }

    def test_register_agent(self):
        """Test registering an agent"""
        self.registry.register("system", self.mock_system_agent)
        self.assertTrue(self.registry.has_agent("system"))

    def test_get_agent(self):
        """Test retrieving a registered agent"""
        self.registry.register("browser", self.mock_browser_agent)
        agent = self.registry.get_agent("browser")
        self.assertEqual(agent, self.mock_browser_agent)

    def test_get_nonexistent_agent(self):
        """Test retrieving a non-existent agent returns None"""
        agent = self.registry.get_agent("nonexistent")
        self.assertIsNone(agent)

    def test_agent_alias(self):
        """Test that aliases work correctly"""
        self.registry.register("browser", self.mock_browser_agent)
        
        # "chrome" should alias to "browser"
        agent = self.registry.get_agent("chrome")
        self.assertEqual(agent, self.mock_browser_agent)
        
        # "safari" should also alias to "browser"
        agent = self.registry.get_agent("safari")
        self.assertEqual(agent, self.mock_browser_agent)

    def test_execute_action(self):
        """Test executing an action through the registry"""
        self.registry.register("system", self.mock_system_agent)
        
        result = self.registry.execute(
            "system",
            "open_app",
            {"app_name": "Safari"}
        )
        
        self.assertEqual(result["status"], "success")
        self.mock_system_agent.execute.assert_called_once_with(
            "open_app",
            {"app_name": "Safari"}
        )

    def test_execute_unknown_module(self):
        """Test executing action on unknown module returns error"""
        result = self.registry.execute(
            "unknown_module",
            "some_action",
            {}
        )
        
        self.assertEqual(result["status"], "error")
        self.assertIn("unknown_module", result["error"].lower())
        self.assertEqual(result["error_type"], "module_not_found")

    def test_list_modules(self):
        """Test listing registered modules"""
        self.registry.register("system", self.mock_system_agent)
        self.registry.register("browser", self.mock_browser_agent)
        
        modules = self.registry.list_modules()
        self.assertEqual(len(modules), 2)
        self.assertIn("system", modules)
        self.assertIn("browser", modules)

    def test_overwrite_warning(self):
        """Test that overwriting an agent logs a warning"""
        self.registry.register("system", self.mock_system_agent)
        
        new_agent = MagicMock()
        new_agent.__class__.__name__ = "NewAgent"
        
        with self.assertLogs(level='WARNING'):
            self.registry.register("system", new_agent)
        
        # Should have new agent
        agent = self.registry.get_agent("system")
        self.assertEqual(agent, new_agent)


class TestExecutionEngineV3(unittest.TestCase):
    """Test the execution engine V3"""

    def setUp(self):
        # Create mock registry with mock agent
        self.registry = AgentRegistry()
        self.mock_agent = MagicMock()
        self.mock_agent.__class__.__name__ = "MockAgent"
        self.mock_agent.execute.return_value = {
            "status": "success",
            "message": "Action completed",
            "data": {"result": "test"},
        }
        self.registry.register("test_module", self.mock_agent)
        
        # Create execution engine
        self.engine = ExecutionEngineV3(
            agent_registry=self.registry,
            max_retries=1,
            enable_replanning=False,
            enable_context_validation=False,  # Disable for simpler tests
        )
        
        # Create test intent
        self.intent = Intent(
            action="test_action",
            confidence=1.0,
            raw_command="Test command",
        )

    def test_execute_simple_plan(self):
        """Test executing a simple single-step plan"""
        steps = [
            {
                "module": "test_module",
                "action": "test_action",
                "args": {"param": "value"},
            }
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertTrue(result.action_results[0].success)
        self.mock_agent.execute.assert_called_once()

    def test_execute_invalid_step(self):
        """Test that invalid steps are caught"""
        steps = [
            {
                # Missing 'module' field
                "action": "test_action",
                "args": {},
            }
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertFalse(result.action_results[0].success)
        self.assertIn("module", result.action_results[0].error.lower())

    def test_execute_with_retry(self):
        """Test that failed actions are retried"""
        # First call fails, second succeeds
        self.mock_agent.execute.side_effect = [
            {"status": "error", "error": "Temporary timeout"},
            {"status": "success", "message": "Success on retry"},
        ]
        
        steps = [
            {
                "module": "test_module",
                "action": "test_action",
                "args": {},
            }
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        self.assertTrue(result.success)
        self.assertEqual(self.mock_agent.execute.call_count, 2)
        self.assertEqual(result.action_results[0].retry_count, 1)

    def test_execute_multi_step_plan(self):
        """Test executing a multi-step plan"""
        steps = [
            {
                "module": "test_module",
                "action": "action1",
                "args": {},
                "step_id": "step1",
            },
            {
                "module": "test_module",
                "action": "action2",
                "args": {"input_from": "step1"},
                "step_id": "step2",
            },
        ]
        
        # First action returns data
        self.mock_agent.execute.side_effect = [
            {"status": "success", "data": {"value": 42}},
            {"status": "success", "data": {"result": "processed"}},
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 2)
        self.assertTrue(all(ar.success for ar in result.action_results))

    def test_mock_execution(self):
        """Test that mock execution doesn't call real agents"""
        steps = [
            {
                "module": "test_module",
                "action": "test_action",
                "args": {},
            }
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=True,  # Mock mode
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertTrue(result.action_results[0].success)
        # Agent should not be called in mock mode
        self.mock_agent.execute.assert_not_called()


class TestGlobalAgentRegistry(unittest.TestCase):
    """Test global agent registry singleton"""

    def setUp(self):
        # Reset global registry before each test
        reset_global_agent_registry()

    def tearDown(self):
        # Clean up after tests
        reset_global_agent_registry()

    def test_get_global_registry(self):
        """Test getting global registry"""
        registry = get_global_agent_registry()
        self.assertIsInstance(registry, AgentRegistry)

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton"""
        registry1 = get_global_agent_registry()
        registry2 = get_global_agent_registry()
        self.assertIs(registry1, registry2)

    def test_reset_global_registry(self):
        """Test resetting global registry"""
        registry1 = get_global_agent_registry()
        reset_global_agent_registry()
        registry2 = get_global_agent_registry()
        self.assertIsNot(registry1, registry2)


if __name__ == "__main__":
    unittest.main()
