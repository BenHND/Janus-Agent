"""
Standalone tests for V3 Agent Architecture

These tests can run independently without requiring the full Janus stack.
"""

import asyncio
import sys
import unittest
from pathlib import Path

# Add janus to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.capabilities.agents.base_agent import AgentExecutionError, BaseAgent
from janus.capabilities.agents.system_agent import SystemAgent
from janus.capabilities.agents.browser_agent import BrowserAgent
from janus.capabilities.agents.messaging_agent import MessagingAgent
from janus.capabilities.agents.files_agent import FilesAgent
from janus.capabilities.agents.code_agent import CodeAgent
from janus.capabilities.agents.ui_agent import UIAgent
from janus.capabilities.agents.llm_agent import LLMAgent


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


class TestAllAgentsExist(unittest.TestCase):
    """Test that all 7 agents can be instantiated."""
    
    def test_all_agents_instantiate(self):
        """Test all agents can be created."""
        agents = [
            SystemAgent(),
            BrowserAgent(),
            MessagingAgent(),
            FilesAgent(),
            CodeAgent(),
            UIAgent(),
            LLMAgent(),
        ]
        
        self.assertEqual(len(agents), 7)
        
        # Check all have correct agent names
        expected_names = ["system", "browser", "messaging", "files", "code", "ui", "llm"]
        actual_names = [agent.agent_name for agent in agents]
        
        self.assertEqual(actual_names, expected_names)


if __name__ == "__main__":
    # Run with unittest
    unittest.main(verbosity=2)
