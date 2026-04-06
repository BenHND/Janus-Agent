"""
TICKET-FIX-CORE-001 - Async Robustness Tests

Tests for the async event loop crash fixes:
1. AgentRegistry.execute() detects running event loop
2. AgentExecutorV3._attempt_context_recovery() uses execute_async()
3. ReasonerLLM._get_system_prompt() loads templates correctly

These tests ensure the agent no longer crashes when correction operations
are performed from within an async context.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
import sys

# Import only what we need to avoid heavy dependencies
from janus.runtime.core.agent_registry import AgentRegistry
from janus.ai.reasoning.reasoner_llm import ReasonerLLM

# Import AgentExecutorV3 only if dependencies are available
try:
    from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
    EXECUTOR_V3_AVAILABLE = True
except ImportError as e:
    EXECUTOR_V3_AVAILABLE = False
    EXECUTOR_V3_IMPORT_ERROR = str(e)


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestAgentRegistryAsyncSafety(unittest.TestCase):
    """Test AgentRegistry async event loop safety"""
    
    def setUp(self):
        """Set up test environment"""
        self.registry = AgentRegistry()
        
        # Create a mock sync agent
        self.sync_agent = Mock()
        self.sync_agent.execute = Mock(return_value={
            "status": "success",
            "data": "sync result"
        })
        
        # Create a mock async agent
        self.async_agent = Mock()
        async def async_execute(action, args, context):
            return {
                "status": "success",
                "data": "async result"
            }
        self.async_agent.execute = async_execute
        
        # Register both agents
        self.registry.register("sync_module", self.sync_agent)
        self.registry.register("async_module", self.async_agent)
    
    def test_sync_execute_with_sync_agent(self):
        """Test: execute() works with sync agents outside async context"""
        result = self.registry.execute("sync_module", "test_action", {})
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "sync result")
        self.sync_agent.execute.assert_called_once()
    
    def test_sync_execute_with_async_agent(self):
        """Test: execute() works with async agents outside async context"""
        result = self.registry.execute("async_module", "test_action", {})
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "async result")
    
    @async_test
    async def test_sync_execute_from_async_context_raises_error(self):
        """Test: execute() raises error when called from async context"""
        # This should raise RuntimeError because we're in an async context
        with self.assertRaises(RuntimeError) as context:
            self.registry.execute("async_module", "test_action", {})
        
        error_msg = str(context.exception)
        self.assertIn("Cannot call sync execute()", error_msg)
        self.assertIn("from within an async loop", error_msg)
        self.assertIn("Use execute_async() instead", error_msg)
    
    @async_test
    async def test_async_execute_from_async_context_works(self):
        """Test: execute_async() works correctly from async context"""
        result = await self.registry.execute_async("async_module", "test_action", {})
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "async result")
    
    @async_test
    async def test_async_execute_with_sync_agent_works(self):
        """Test: execute_async() handles sync agents via executor"""
        result = await self.registry.execute_async("sync_module", "test_action", {})
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "sync result")


class TestAgentExecutorV3ContextRecovery(unittest.TestCase):
    """Test AgentExecutorV3 context recovery uses async correctly"""
    
    def setUp(self):
        """Set up test environment"""
        if not EXECUTOR_V3_AVAILABLE:
            self.skipTest(f"AgentExecutorV3 not available: {EXECUTOR_V3_IMPORT_ERROR}")
        
        self.registry = AgentRegistry()
        
        # Create mock system agent
        self.system_agent = Mock()
        async def mock_execute(action, args, context):
            if action == "open_application":
                return {
                    "status": "success",
                    "data": f"Opened {args.get('app_name')}"
                }
            return {"status": "error", "error": "Unknown action"}
        
        self.system_agent.execute = mock_execute
        self.registry.register("system", self.system_agent)
        
        # Create executor with mock registry
        self.executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,  # Disable to avoid loading vision engine
            enable_replanning=False
        )
    
    @async_test
    async def test_context_recovery_uses_execute_async(self):
        """Test: _attempt_context_recovery() uses execute_async()"""
        expected_context = {"app": "Safari"}
        global_context = {"app": None}
        
        # Should succeed without raising RuntimeError
        result = await self.executor._attempt_context_recovery(
            expected_context, 
            global_context
        )
        
        self.assertTrue(result)
        self.assertEqual(global_context["app"], "Safari")
    
    @async_test
    async def test_context_recovery_handles_failure(self):
        """Test: _attempt_context_recovery() handles failure gracefully"""
        # Mock agent to return error
        async def mock_execute_fail(action, args, context):
            return {"status": "error", "error": "App not found"}
        
        self.system_agent.execute = mock_execute_fail
        
        expected_context = {"app": "NonExistentApp"}
        global_context = {"app": None}
        
        result = await self.executor._attempt_context_recovery(
            expected_context,
            global_context
        )
        
        self.assertFalse(result)
        self.assertIsNone(global_context["app"])
    
    @async_test
    async def test_context_recovery_no_app_returns_false(self):
        """Test: _attempt_context_recovery() returns False when no app specified"""
        expected_context = {"surface": "browser"}  # No app field
        global_context = {"app": None}
        
        result = await self.executor._attempt_context_recovery(
            expected_context,
            global_context
        )
        
        self.assertFalse(result)


class TestReasonerLLMPromptLoading(unittest.TestCase):
    """Test ReasonerLLM prompt loading functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Use mock backend to avoid LLM dependencies
        self.reasoner = ReasonerLLM(backend="mock")
    
    def test_get_system_prompt_react_mode(self):
        """Test: _get_system_prompt() loads ReAct template"""
        prompt = self.reasoner._get_system_prompt(mode="react", language="fr")
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_get_system_prompt_reflex_mode(self):
        """Test: _get_system_prompt() loads Reflex template"""
        prompt = self.reasoner._get_system_prompt(mode="reflex", language="fr")
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_get_system_prompt_planner_mode(self):
        """Test: _get_system_prompt() loads Planner template (legacy)"""
        prompt = self.reasoner._get_system_prompt(mode="planner", language="fr")
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_get_system_prompt_default_mode(self):
        """Test: _get_system_prompt() defaults to ReAct mode"""
        prompt = self.reasoner._get_system_prompt()
        
        # Should default to ReAct mode in French
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_get_system_prompt_english(self):
        """Test: _get_system_prompt() supports English"""
        prompt = self.reasoner._get_system_prompt(mode="react", language="en")
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    def test_get_system_prompt_invalid_mode_fallback(self):
        """Test: _get_system_prompt() falls back to ReAct on invalid mode"""
        prompt = self.reasoner._get_system_prompt(mode="invalid_mode", language="fr")
        
        # Should fall back to ReAct mode
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
    
    @patch('janus.reasoning.reasoner_llm.load_prompt')
    def test_get_system_prompt_failsafe_on_error(self, mock_load_prompt):
        """Test: _get_system_prompt() provides failsafe prompt on error"""
        # Mock load_prompt to raise exception
        mock_load_prompt.side_effect = Exception("Template load error")
        
        # Should not raise exception, should return failsafe prompt
        prompt = self.reasoner._get_system_prompt(mode="react", language="fr")
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
        # Failsafe prompt should contain basic instructions
        self.assertIn("agent", prompt.lower())
        self.assertIn("json", prompt.lower())


class TestIntegrationAsyncCorrections(unittest.TestCase):
    """Integration tests for async corrections workflow"""
    
    @async_test
    async def test_full_correction_flow_no_crash(self):
        """Test: Full correction flow from async context doesn't crash"""
        if not EXECUTOR_V3_AVAILABLE:
            self.skipTest(f"AgentExecutorV3 not available: {EXECUTOR_V3_IMPORT_ERROR}")
        
        # Set up registry with mock agents
        registry = AgentRegistry()
        
        # Mock system agent
        system_agent = Mock()
        async def mock_system_execute(action, args, context):
            return {
                "status": "success",
                "data": f"Executed {action}"
            }
        system_agent.execute = mock_system_execute
        registry.register("system", system_agent)
        
        # Create executor
        executor = AgentExecutorV3(
            agent_registry=registry,
            enable_vision_recovery=False,
            enable_replanning=False
        )
        
        # Simulate context mismatch requiring recovery
        expected_context = {"app": "Safari"}
        global_context = {"app": "Chrome"}  # Wrong app
        
        # This should complete without RuntimeError
        try:
            result = await executor._attempt_context_recovery(
                expected_context,
                global_context
            )
            # If we reach here, no crash occurred
            self.assertTrue(True, "No crash occurred")
        except RuntimeError as e:
            if "asyncio.run()" in str(e):
                self.fail(f"Async event loop crash occurred: {e}")
            raise


if __name__ == '__main__':
    unittest.main()
