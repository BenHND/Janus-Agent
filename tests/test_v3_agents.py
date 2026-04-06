"""
Tests for V3 Agent Architecture

This test suite validates the V3 execution agents including:
- BaseAgent interface
- AgentExecutionError exception
- All 8 specialized agents
- Agent registry integration
- ExecutionEngineV3 integration
"""

import asyncio
import unittest

# Try to import pytest, but fall back to unittest if not available
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Create pytest marker stubs for unittest compatibility
    class pytest:
        @staticmethod
        def mark(*args, **kwargs):
            class Mark:
                @staticmethod
                def asyncio(func):
                    return func
            return Mark()

from janus.capabilities.agents import (
    AgentExecutionError,
    BaseAgent,
    BrowserAgent,
    CodeAgent,
    FilesAgent,
    LLMAgent,
    MessagingAgent,
    SystemAgent,
    UIAgent,
)
from janus.runtime.core.agent_registry import AgentRegistry


def async_test(coro):
    """Decorator to run async tests in unittest."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestBaseAgent(unittest.TestCase):
    """Test BaseAgent interface and helpers."""
    
    def test_agent_execution_error(self):
        """Test AgentExecutionError creation and conversion."""
        error = AgentExecutionError(
            module="test",
            action="test_action",
            details="Test error",
            recoverable=True
        )
        
        self.assertEqual(error.module, "test")
        self.assertEqual(error.action, "test_action")
        self.assertEqual(error.details, "Test error")
        self.assertTrue(error.recoverable)
        
        # Test to_dict conversion
        error_dict = error.to_dict()
        self.assertEqual(error_dict["status"], "error")
        self.assertEqual(error_dict["module"], "test")
        self.assertEqual(error_dict["action"], "test_action")
        self.assertEqual(error_dict["error"], "Test error")
        self.assertTrue(error_dict["recoverable"])
    
    def test_base_agent_abstract(self):
        """Test that BaseAgent is abstract and cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseAgent("test")


class TestSystemAgent(unittest.TestCase):
    """Test SystemAgent operations."""
    
    @async_test
    async def test_system_agent_initialization(self):
        """Test SystemAgent initializes correctly."""
        agent = SystemAgent()
        self.assertEqual(agent.agent_name, "system")
    
    @async_test
    async def test_missing_required_args(self):
        """Test validation of required arguments."""
        agent = SystemAgent()
        
        # Missing app_name should raise error
        with self.assertRaises(AgentExecutionError) as cm:
            await agent.execute(
                action="open_application",
                args={},
                context={}
            )
        
        self.assertIn("Missing required arguments", str(cm.exception))
    
    @async_test
    async def test_unknown_action(self):
        """Test handling of unknown action."""
        agent = SystemAgent()
        
        with self.assertRaises(AgentExecutionError) as cm:
            await agent.execute(
                action="unknown_action",
                args={},
                context={}
            )
        
        self.assertIn("Unknown action", str(cm.exception))


class TestBrowserAgent(unittest.TestCase):
    """Test BrowserAgent operations."""
    
    @async_test
    async def test_browser_agent_initialization(self):
        """Test BrowserAgent initializes correctly."""
        agent = BrowserAgent()
        self.assertEqual(agent.agent_name, "browser")


class TestMessagingAgent(unittest.TestCase):
    """Test MessagingAgent operations."""
    
    @async_test
    async def test_messaging_agent_initialization(self):
        """Test MessagingAgent initializes correctly."""
        agent = MessagingAgent()
        self.assertEqual(agent.agent_name, "messaging")


class TestFilesAgent(unittest.TestCase):
    """Test FilesAgent operations."""
    
    @async_test
    async def test_files_agent_initialization(self):
        """Test FilesAgent initializes correctly."""
        agent = FilesAgent()
        self.assertEqual(agent.agent_name, "files")


class TestCodeAgent(unittest.TestCase):
    """Test CodeAgent operations."""
    
    @async_test
    async def test_code_agent_initialization(self):
        """Test CodeAgent initializes correctly."""
        agent = CodeAgent()
        self.assertEqual(agent.agent_name, "code")


class TestUIAgent(unittest.TestCase):
    """Test UIAgent operations."""
    
    @async_test
    async def test_ui_agent_initialization(self):
        """Test UIAgent initializes correctly."""
        agent = UIAgent()
        self.assertEqual(agent.agent_name, "ui")


class TestLLMAgent(unittest.TestCase):
    """Test LLMAgent operations."""
    
    @async_test
    async def test_llm_agent_initialization(self):
        """Test LLMAgent initializes correctly."""
        agent = LLMAgent()
        self.assertEqual(agent.agent_name, "llm")


class TestAgentRegistry(unittest.TestCase):
    """Test AgentRegistry with V3 agents."""
    
    def test_register_v3_agent(self):
        """Test registering a V3 agent."""
        registry = AgentRegistry()
        agent = SystemAgent()
        
        registry.register("system", agent)
        
        self.assertTrue(registry.has_agent("system"))
        self.assertEqual(registry.get_agent("system"), agent)
    
    def test_unknown_module(self):
        """Test executing action on unknown module."""
        registry = AgentRegistry()
        
        result = registry.execute(
            module="unknown",
            action="test",
            args={}
        )
        
        self.assertEqual(result["status"], "error")
        self.assertIn("not registered", result["error"])


class TestIntegration(unittest.TestCase):
    """Integration tests for V3 agents with ExecutionEngineV3."""
    
    @async_test
    async def test_full_execution_flow(self):
        """Test full execution flow from ExecutionEngineV3 to V3 agents."""
        from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3
        from janus.runtime.core.contracts import Intent, IntentType
        from janus.runtime.core.agent_setup import setup_agent_registry
        
        # Setup registry with V3 agents
        registry = setup_agent_registry(use_v3_agents=True)
        
        # Create execution engine
        engine = ExecutionEngineV3(
            agent_registry=registry,
            max_retries=0,
            enable_replanning=False
        )
        
        # Create simple test steps
        steps = [
            {
                "module": "system",
                "action": "type",
                "args": {"text": "Hello"},
                "context": {}
            }
        ]
        
        # Create intent
        intent = Intent(
            type=IntentType.CUSTOM,
            raw_text="type hello",
            confidence=1.0
        )
        
        # Execute plan
        result = await engine.execute_plan_async(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=True  # Use mock to avoid actual execution
        )
        
        # Check result
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.action_results)
        self.assertEqual(len(result.action_results), 1)
        
        # Check first action result
        action_result = result.action_results[0]
        self.assertTrue(action_result.success)


if __name__ == "__main__":
    # Run with unittest
    unittest.main()

