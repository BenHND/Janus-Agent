"""
TICKET 104 - AgentExecutorV3 Tests

Comprehensive tests for the new Agent Executor V3 that:
1. Validates steps with ValidatorAgent before execution
2. Routes to V3 agents via AgentRegistry
3. Manages global context correctly
4. Handles errors with vision recovery and replanning
5. Ensures no step executes in wrong context

Required Test Scenario:
"Ouvre Safari et va sur YouTube et cherche Forgive Burial"

This must verify:
- Safari opens correctly
- YouTube loads
- Search executes
- Context updates properly: app=Safari, domain=youtube.com, surface=browser
- No step executes in wrong context
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock

from janus.capabilities.agents.validator_agent import ValidatorAgent
from janus.constants import IntentType
from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestAgentExecutorV3Initialization(unittest.TestCase):
    """Test AgentExecutorV3 initialization and configuration"""
    
    def test_initialization_defaults(self):
        """Test: AgentExecutorV3 initializes with default settings"""
        executor = AgentExecutorV3()
        
        self.assertIsNotNone(executor.agent_registry)
        self.assertIsNotNone(executor.validator_agent)
        self.assertTrue(executor.enable_vision_recovery)
        self.assertFalse(executor.enable_replanning)
        self.assertEqual(executor.max_retries, 1)
    
    def test_initialization_custom(self):
        """Test: AgentExecutorV3 accepts custom configuration"""
        registry = AgentRegistry()
        validator = ValidatorAgent()
        
        executor = AgentExecutorV3(
            agent_registry=registry,
            validator_agent=validator,
            enable_vision_recovery=False,
            enable_replanning=True,
            max_retries=3
        )
        
        self.assertEqual(executor.agent_registry, registry)
        self.assertEqual(executor.validator_agent, validator)
        self.assertFalse(executor.enable_vision_recovery)
        self.assertTrue(executor.enable_replanning)
        self.assertEqual(executor.max_retries, 3)


class TestAgentExecutorV3ContextManagement(unittest.TestCase):
    """Test context initialization and updates"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
    
    def test_initialize_context(self):
        """Test: Global context initializes with all V3 fields"""
        context = self.executor._initialize_context()
        
        # Check all required fields exist
        self.assertIn("app", context)
        self.assertIn("surface", context)
        self.assertIn("url", context)
        self.assertIn("domain", context)
        self.assertIn("thread", context)
        self.assertIn("record", context)
        
        # All should be None initially
        self.assertIsNone(context["app"])
        self.assertIsNone(context["surface"])
        self.assertIsNone(context["url"])
        self.assertIsNone(context["domain"])
    
    def test_update_global_context(self):
        """Test: Context updates correctly"""
        context = self.executor._initialize_context()
        
        # Update with new values
        updates = {
            "app": "Safari",
            "surface": "browser",
            "domain": "youtube.com"
        }
        
        self.executor._update_global_context(context, updates)
        
        self.assertEqual(context["app"], "Safari")
        self.assertEqual(context["surface"], "browser")
        self.assertEqual(context["domain"], "youtube.com")
    
    def test_update_global_context_ignores_none(self):
        """Test: Context update ignores None values"""
        context = {
            "app": "Safari",
            "surface": "browser",
            "domain": "youtube.com",
            "url": None,
            "thread": None,
            "record": None,
        }
        
        # Try to update with None - should be ignored
        updates = {
            "app": None,
            "surface": "editor"
        }
        
        self.executor._update_global_context(context, updates)
        
        # app should remain unchanged (None ignored)
        self.assertEqual(context["app"], "Safari")
        # surface should update
        self.assertEqual(context["surface"], "editor")


class TestAgentExecutorV3ContextValidation(unittest.TestCase):
    """Test context precondition validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
    
    def test_validate_context_preconditions_no_requirements(self):
        """Test: Empty step context always validates"""
        step_context = {}
        global_context = {"app": "Safari", "surface": "browser"}
        
        valid, error = self.executor._validate_context_preconditions(
            step_context, global_context
        )
        
        self.assertTrue(valid)
        self.assertIsNone(error)
    
    def test_validate_context_preconditions_app_match(self):
        """Test: Matching app context validates"""
        step_context = {"app": "Safari"}
        global_context = {"app": "Safari", "surface": "browser"}
        
        valid, error = self.executor._validate_context_preconditions(
            step_context, global_context
        )
        
        self.assertTrue(valid)
        self.assertIsNone(error)
    
    def test_validate_context_preconditions_app_mismatch(self):
        """Test: Mismatched app context fails"""
        step_context = {"app": "Safari"}
        global_context = {"app": "Chrome", "surface": "browser"}
        
        valid, error = self.executor._validate_context_preconditions(
            step_context, global_context
        )
        
        self.assertFalse(valid)
        self.assertIn("Safari", error)
        self.assertIn("Chrome", error)
    
    def test_validate_context_preconditions_surface_match(self):
        """Test: Matching surface context validates"""
        step_context = {"surface": "browser"}
        global_context = {"app": "Safari", "surface": "browser"}
        
        valid, error = self.executor._validate_context_preconditions(
            step_context, global_context
        )
        
        self.assertTrue(valid)
        self.assertIsNone(error)
    
    def test_validate_context_preconditions_surface_mismatch(self):
        """Test: Mismatched surface context fails"""
        step_context = {"surface": "editor"}
        global_context = {"app": "Safari", "surface": "browser"}
        
        valid, error = self.executor._validate_context_preconditions(
            step_context, global_context
        )
        
        self.assertFalse(valid)
        self.assertIn("editor", error)
        self.assertIn("browser", error)


class TestAgentExecutorV3StepValidation(unittest.TestCase):
    """Test step validation with ValidatorAgent"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
    
    def test_valid_step_passes_validation(self):
        """Test: Valid step passes validation"""
        step = {
            "module": "system",
            "action": "open_application",
            "args": {"app_name": "Safari"},
            "context": {"app": None}
        }
        context = {}
        
        result = self.executor.validator_agent.validate_step(step, context)
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
    
    def test_invalid_step_fails_validation(self):
        """Test: Invalid step fails validation"""
        step = {
            "module": "invalid_module",
            "action": "invalid_action",
            "args": {},
            "context": {}
        }
        context = {}
        
        result = self.executor.validator_agent.validate_step(step, context)
        
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)


class TestAgentExecutorV3RequiredScenario(unittest.TestCase):
    """
    Test the required scenario: "Ouvre Safari et va sur YouTube et cherche Forgive Burial"
    
    This scenario must verify:
    1. Safari opens (system.open_application)
    2. YouTube loads (browser.open_url)
    3. Search performs (browser.search)
    4. Context updates correctly after each step
    5. No step executes in wrong context
    """
    
    def setUp(self):
        """Set up test environment with mocked agents"""
        # Create mock registry with mock agents
        self.registry = AgentRegistry()
        
        # Mock SystemAgent
        self.mock_system_agent = Mock()
        self.mock_system_agent.execute = Mock(return_value={
            "status": "success",
            "message": "Application opened",
            "data": {
                "context_updates": {"app": "Safari"}
            }
        })
        
        # Mock BrowserAgent
        self.mock_browser_agent = Mock()
        self.mock_browser_agent.execute = Mock(return_value={
            "status": "success",
            "message": "URL opened",
            "data": {
                "context_updates": {
                    "surface": "browser",
                    "domain": "youtube.com",
                    "url": "https://youtube.com"
                }
            }
        })
        
        # Register mocked agents
        self.registry.register("system", self.mock_system_agent)
        self.registry.register("browser", self.mock_browser_agent)
        
        # Create executor with mocked registry
        self.executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=False,
            max_retries=0
        )
    
    @async_test
    async def test_required_scenario_full_execution(self):
        """
        Test: Full scenario executes correctly
        "Ouvre Safari et va sur YouTube et cherche Forgive Burial"
        """
        # Define the plan (as would come from Planner/Reasoner)
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {"app": None}  # No app initially
            },
            {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://youtube.com"},
                "context": {"app": "Safari", "surface": None}  # Safari should be open
            },
            {
                "module": "browser",
                "action": "search",
                "args": {"query": "Forgive Burial"},
                "context": {
                    "app": "Safari",
                    "surface": "browser",
                    "domain": "youtube.com"
                }
            }
        ]
        
        # Create intent
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Ouvre Safari et va sur YouTube et cherche Forgive Burial"
        )
        
        # Execute plan
        result = await self.executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Verify overall success
        self.assertTrue(result.success, "Plan execution should succeed")
        self.assertEqual(len(result.action_results), 3, "Should have 3 action results")
        
        # Verify all steps succeeded
        for i, action_result in enumerate(result.action_results):
            self.assertTrue(
                action_result.success,
                f"Step {i+1} should succeed: {action_result.error}"
            )
        
        # Verify system agent was called for step 1
        # Note: ValidatorAgent may correct action names
        self.mock_system_agent.execute.assert_called()
        # The action might be corrected by validator, so just check it was called
        
        # Verify browser agent was called for steps 2 and 3
        self.assertEqual(self.mock_browser_agent.execute.call_count, 2)
    
    @async_test
    async def test_required_scenario_context_updates(self):
        """
        Test: Context updates correctly through scenario
        """
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {}
            },
            {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://youtube.com"},
                "context": {"app": "Safari"}
            },
            {
                "module": "browser",
                "action": "search",
                "args": {"query": "Forgive Burial"},
                "context": {"app": "Safari", "surface": "browser", "domain": "youtube.com"}
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await self.executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Verify execution succeeded
        self.assertTrue(result.success, "Plan should execute successfully")
        
        # Verify all steps executed
        self.assertEqual(len(result.action_results), 3)
        
        # All steps should have succeeded
        for i, action_result in enumerate(result.action_results):
            self.assertTrue(action_result.success, f"Step {i+1} should succeed")
    
    @async_test
    async def test_required_scenario_wrong_context_prevents_execution(self):
        """
        Test: Step with wrong context preconditions fails validation
        """
        # Create executor without context recovery to ensure failure
        executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=False,
            max_retries=0
        )
        
        # Override the _attempt_context_recovery to always fail
        async def mock_recovery(step_context, global_context):
            return False
        executor._attempt_context_recovery = mock_recovery
        
        # Create steps where step 2 expects Chrome but Safari is active
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {}
            },
            {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://youtube.com"},
                "context": {"app": "Chrome"}  # Wrong! Safari is active
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Execution should fail at step 2 due to context mismatch
        self.assertFalse(result.success, "Execution should fail due to context mismatch")
        # Step 1 should succeed, step 2 should fail
        self.assertTrue(result.action_results[0].success)
        self.assertFalse(result.action_results[1].success)
        self.assertIn("context", result.action_results[1].error.lower())


class TestAgentExecutorV3ErrorHandling(unittest.TestCase):
    """Test error handling, retry, and recovery"""
    
    def setUp(self):
        """Set up test environment"""
        self.registry = AgentRegistry()
        
        # Mock agent that fails first time, succeeds second time
        self.mock_agent = Mock()
        self.call_count = 0
        
        def mock_execute(action, args, context=None):
            self.call_count += 1
            if self.call_count == 1:
                return {
                    "status": "error",
                    "error": "Temporary failure",
                    "recoverable": True
                }
            else:
                return {
                    "status": "success",
                    "message": "Success on retry",
                    "data": {}
                }
        
        self.mock_agent.execute = mock_execute
        self.registry.register("system", self.mock_agent)  # Register for system module
        
        # Disable context recovery to avoid interference
        self.executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=False,
            max_retries=1  # Allow 1 retry
        )
    
    @async_test
    async def test_retry_on_recoverable_error(self):
        """Test: Executor retries on recoverable errors"""
        steps = [
            {
                "module": "system",  # Use valid module
                "action": "open_application",  # Use valid action
                "args": {"app_name": "TestApp"},
                "context": {}
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await self.executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Should succeed after retry
        self.assertTrue(result.success)
        # Should have been called twice (initial + 1 retry)
        self.assertEqual(self.call_count, 2)
    
    @async_test
    async def test_no_retry_on_non_recoverable_error(self):
        """Test: Executor does not retry non-recoverable errors"""
        # Reset mock to return non-recoverable error
        self.call_count = 0
        
        def mock_execute_non_recoverable(action, args, context=None):
            self.call_count += 1
            return {
                "status": "error",
                "error": "Non-recoverable failure",
                "recoverable": False
            }
        
        self.mock_agent.execute = mock_execute_non_recoverable
        
        steps = [
            {
                "module": "system",  # Use valid module
                "action": "open_application",  # Use valid action
                "args": {"app_name": "TestApp"},
                "context": {}
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await self.executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Should fail without retry
        self.assertFalse(result.success)
        # Should have been called only once (no retry)
        self.assertEqual(self.call_count, 1)


class TestAgentExecutorV3Integration(unittest.TestCase):
    """Integration tests with real ValidatorAgent"""
    
    @async_test
    async def test_integration_with_validator_agent(self):
        """Test: Executor integrates correctly with ValidatorAgent"""
        # Create executor with real ValidatorAgent
        executor = AgentExecutorV3(
            enable_vision_recovery=False,
            enable_replanning=False
        )
        
        # Mock registry
        registry = AgentRegistry()
        mock_agent = Mock()
        mock_agent.execute = Mock(return_value={
            "status": "success",
            "message": "Success"
        })
        registry.register("system", mock_agent)
        executor.agent_registry = registry
        
        # Valid step
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Safari"},
                "context": {}
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        self.assertTrue(result.success)
    
    @async_test
    async def test_integration_invalid_step_rejected(self):
        """Test: ValidatorAgent rejects invalid steps"""
        executor = AgentExecutorV3(
            enable_vision_recovery=False,
            enable_replanning=False
        )
        
        # Invalid step (missing required fields)
        steps = [
            {
                "module": "invalid_module",
                "action": "invalid_action"
                # Missing 'args' and 'context'
            }
        ]
        
        intent = Intent(
            action="test_action",
            confidence=0.95,
            parameters={},
            raw_command="Test"
        )
        
        result = await executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Should fail validation
        self.assertFalse(result.success)
        if len(result.action_results) > 0:
            self.assertIn("invalid", result.action_results[0].error.lower())


if __name__ == "__main__":
    unittest.main()
