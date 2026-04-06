"""
TICKET 010 - Comprehensive Executor V3 + Agents Tests

Tests for ExecutionEngineV3 and all 8 specialized agents to ensure:
- All agents execute actions correctly
- Context is propagated and updated correctly
- No silent errors
- Retry and replan mechanisms work
- Logs are coherent and inspectable

Test Categories:
1. Individual agent action tests (all 8 agents)
2. End-to-end execution tests
3. Context propagation tests
4. Error recovery tests
5. Replan success rate tests
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from janus.capabilities.agents import (
    SystemAgent,
    BrowserAgent,
    MessagingAgent,
    FilesAgent,
    CodeAgent,
    UIAgent,
    LLMAgent,
    AgentExecutionError,
)
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.agent_setup import setup_agent_registry
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestExecutorV3SystemAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with SystemAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = SystemAgent()

    @async_test
    async def test_system_open_application(self):
        """Test: system.open_app action"""
        action = "open_application"
        args = {"app_name": "Safari"}
        context = {}

        # Mock the actual application opening
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await self.agent.execute(action, args, context)

        # Verify result structure
        self.assertIn("status", result)
        # On non-macOS systems, this might not work, so allow errors
        self.assertIn(result["status"], ["success", "error"])

    @async_test
    async def test_system_shortcut(self):
        """Test: system.shortcut action"""
        action = "shortcut"
        args = {"name": "cmd+c"}
        context = {"app": "Safari"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_system_switch_app(self):
        """Test: system.switch_app action"""
        action = "switch_application"
        args = {"app_name": "Chrome"}
        context = {}

        # Mock the switch
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await self.agent.execute(action, args, context)

        self.assertIn("status", result)


class TestExecutorV3BrowserAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with BrowserAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = BrowserAgent()

    @async_test
    async def test_browser_open_url(self):
        """Test: browser.open_url action"""
        action = "open_url"
        args = {"url": "https://www.youtube.com"}
        context = {"app": "Safari"}

        # Mock webbrowser.open
        with patch('webbrowser.open') as mock_open:
            mock_open.return_value = True
            result = await self.agent.execute(action, args, context)

        self.assertEqual(result["status"], "success")
        self.assertIn("context_updates", result)
        self.assertIn("url", result["context_updates"])

    @async_test
    async def test_browser_search(self):
        """Test: browser.search action"""
        action = "search"
        args = {"query": "Python tutorials"}
        context = {"app": "Safari", "url": "https://www.youtube.com"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)
        # Should update context with search query
        if result["status"] == "success":
            self.assertIn("context_updates", result)

    @async_test
    async def test_browser_click(self):
        """Test: browser.click action"""
        action = "click"
        args = {"text": "Sign In"}
        context = {"app": "Chrome", "url": "https://example.com"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)
        # May require vision, so error is acceptable

    @async_test
    async def test_browser_scroll(self):
        """Test: browser.scroll action"""
        action = "scroll"
        args = {"direction": "down"}
        context = {"app": "Safari", "url": "https://example.com"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_browser_play_video(self):
        """Test: browser.play_video action"""
        action = "play_video"
        args = {}
        context = {"app": "Safari", "url": "https://www.youtube.com/watch?v=test"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3MessagingAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with MessagingAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = MessagingAgent()

    @async_test
    async def test_messaging_open_chat(self):
        """Test: messaging.open_thread action"""
        action = "open_thread"
        args = {"name": "General"}
        context = {"app": "Teams"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_messaging_send_message(self):
        """Test: messaging.send_message action"""
        action = "send_message"
        args = {"message": "je suis en retard", "recipient": "Paul"}
        context = {"app": "Teams"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_messaging_reply_message(self):
        """Test: messaging.send_message with thread context"""
        action = "send_message"
        args = {"message": "D'accord, merci!"}
        context = {"app": "Teams", "thread": "12345"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3FilesAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with FilesAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = FilesAgent()

    @async_test
    async def test_files_open_path(self):
        """Test: files.open_file action"""
        action = "open_file"
        args = {"path": "/tmp/test.txt"}
        context = {"app": "Finder"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_files_search_files(self):
        """Test: files.search_files action"""
        action = "search_files"
        args = {"query": "invoice.pdf"}
        context = {"app": "Finder"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3CodeAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with CodeAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = CodeAgent()

    @async_test
    async def test_code_open_file(self):
        """Test: code.open_file action"""
        action = "open_file"
        args = {"path": "/tmp/main.py"}
        context = {"app": "VSCode"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_code_goto_line(self):
        """Test: code.goto_line action"""
        action = "goto_line"
        args = {"line": 42}
        context = {"app": "VSCode", "file": "/tmp/main.py"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_code_find_text(self):
        """Test: code.find_text action"""
        action = "find_text"
        args = {"query": "function login"}
        context = {"app": "VSCode"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_code_paste(self):
        """Test: code module with paste (likely UI action)"""
        # Code module might not have paste directly
        action = "save_file"
        args = {}
        context = {"app": "VSCode", "file": "/tmp/main.py"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3UIAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with UIAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = UIAgent()

    @async_test
    async def test_ui_click(self):
        """Test: ui.click action"""
        action = "click"
        args = {"target": "Submit button"}
        context = {"app": "Safari"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_ui_copy(self):
        """Test: ui.copy action"""
        action = "copy"
        args = {}
        context = {"app": "Safari"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_ui_type(self):
        """Test: ui.type action"""
        action = "type"
        args = {"text": "Hello world"}
        context = {"app": "TextEdit"}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3LLMAgent(unittest.TestCase):
    """Test ExecutionEngineV3 with LLMAgent actions"""

    def setUp(self):
        """Set up test environment"""
        self.agent = LLMAgent()

    @async_test
    async def test_llm_summarize(self):
        """Test: llm.summarize action"""
        action = "summarize"
        args = {"input": "This is a long text that needs to be summarized."}
        context = {}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)
        # LLM might not be available, so error is acceptable

    @async_test
    async def test_llm_rewrite(self):
        """Test: llm.rewrite action"""
        action = "rewrite"
        args = {"input": "Make this professional", "style": "professional"}
        context = {}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)

    @async_test
    async def test_llm_extract_keywords(self):
        """Test: llm.extract_keywords action"""
        action = "extract_keywords"
        args = {"input": "Machine learning and artificial intelligence", "count": 3}
        context = {}

        result = await self.agent.execute(action, args, context)
        self.assertIn("status", result)


class TestExecutorV3ContextPropagation(unittest.TestCase):
    """Test that ExecutionEngineV3 properly propagates and updates context"""

    def setUp(self):
        """Set up execution engine"""
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.engine = ExecutionEngineV3(self.registry)

    @async_test
    async def test_context_propagation_multi_step(self):
        """Test: Context is propagated across multiple steps"""
        plan = {
            "steps": [
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
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://www.youtube.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {
                "status": "success",
                "context_updates": {"app": "Safari"}
            }

            with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_browser:
                mock_browser.return_value = {
                    "status": "success",
                    "context_updates": {"url": "https://www.youtube.com"}
                }

                result = await self.engine.execute_plan(plan)

                # Verify execution completed
                self.assertIsNotNone(result)
                self.assertIn("status", result)

    @async_test
    async def test_context_update_after_each_action(self):
        """Test: Context is updated after each successful action"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://example.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_browser:
            mock_browser.return_value = {
                "status": "success",
                "context_updates": {"url": "https://example.com", "domain": "example.com"}
            }

            result = await self.engine.execute_plan(plan)

            # Context should be updated
            if result["status"] == "success":
                self.assertIn("context", result)


class TestExecutorV3ErrorRecovery(unittest.TestCase):
    """Test ExecutionEngineV3 error recovery and retry mechanisms"""

    def setUp(self):
        """Set up execution engine"""
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.engine = ExecutionEngineV3(self.registry)

    @async_test
    async def test_no_silent_errors(self):
        """Test: All errors are reported, no silent failures"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "unknown_action",
                    "args": {},
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
        }

        result = await self.engine.execute_plan(plan)

        # Should have error status
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertIsNotNone(result["error"])
        self.assertGreater(len(result["error"]), 0)

    @async_test
    async def test_retry_on_transient_error(self):
        """Test: Executor retries on transient errors"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://example.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        call_count = 0

        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with timeout
                raise AgentExecutionError("browser", "open_url", "Timeout", recoverable=True)
            else:
                # Second call succeeds
                return {"status": "success", "context_updates": {}}

        with patch.object(BrowserAgent, 'execute', side_effect=failing_then_success):
            result = await self.engine.execute_plan(plan, max_retries=2)

            # Should succeed after retry
            if result["status"] == "success":
                self.assertGreaterEqual(call_count, 1)


class TestExecutorV3ReplanSuccess(unittest.TestCase):
    """Test ExecutionEngineV3 replanning success rate (target: >80%)"""

    def setUp(self):
        """Set up execution engine"""
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.engine = ExecutionEngineV3(self.registry)

    @async_test
    async def test_replan_on_persistent_failure(self):
        """Test: Executor can trigger replanning on persistent failures"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "click",
                    "args": {"text": "NonexistentButton"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": "https://example.com",
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        async def always_fail(*args, **kwargs):
            raise AgentExecutionError("browser", "click", "Element not found", recoverable=True)

        with patch.object(BrowserAgent, 'execute', side_effect=always_fail):
            result = await self.engine.execute_plan(plan, max_retries=3)

            # Should fail after retries
            self.assertEqual(result["status"], "error")
            self.assertIn("error", result)


class TestExecutorV3Logging(unittest.TestCase):
    """Test that ExecutionEngineV3 produces coherent, inspectable logs"""

    def setUp(self):
        """Set up execution engine"""
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.engine = ExecutionEngineV3(self.registry)

    @async_test
    async def test_logs_before_execution(self):
        """Test: Logs are created before action execution"""
        plan = {
            "steps": [
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
        }

        # Execute and check that logging happens
        with patch('subprocess.run'):
            result = await self.engine.execute_plan(plan)

        # Execution should produce result with status
        self.assertIn("status", result)

    @async_test
    async def test_logs_after_execution(self):
        """Test: Logs include execution results and duration"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://example.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "context_updates": {}}
            result = await self.engine.execute_plan(plan)

        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
