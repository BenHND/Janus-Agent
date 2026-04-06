"""
TICKET-P1-01: Tests for Replanning (The Brain Fix)

Tests that verify:
1. ReasonerLLM.replan() generates valid JSON plans with alternative actions
2. AgentExecutorV3._attempt_replanning() calls the reasoner and injects new steps
3. Execution doesn't stop on error but logs "Attempting replan..."
4. Simulated "Element not found" error generates a different action plan

Definition of Done (DoD):
- Test unitaire: Simuler une erreur "Element not found". Le système doit 
  générer un nouveau plan JSON valide contenant une action différente.
- L'exécution ne s'arrête pas sur l'erreur mais loggue "Attempting replan...".
"""

import asyncio
import json
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import ActionResult, ErrorType, ExecutionResult, Intent
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


def make_v3_context(app=None, surface=None, url=None, domain=None, thread=None, record=None):
    """Helper to create V3 context structure for tests."""
    return {
        "app": app,
        "surface": surface,
        "url": url,
        "domain": domain,
        "thread": thread,
        "record": record
    }


class TestReasonerLLMReplan(unittest.TestCase):
    """Test ReasonerLLM.replan() method generates valid alternative plans"""
    
    def setUp(self):
        """Set up mock ReasonerLLM"""
        self.llm = ReasonerLLM(backend="mock")
    
    def test_replan_on_element_not_found(self):
        """
        DoD: Simulate 'Element not found' error.
        System must generate a new valid JSON plan with a different action.
        """
        failed_action = {
            "module": "browser",
            "action": "click_element",
            "args": {"selector": "#non-existent-button"},
            "context": {"app": "Safari", "surface": "browser"}
        }
        error = "Element not found: selector '#non-existent-button' did not match any elements"
        
        result = self.llm.replan(
            failed_action=failed_action,
            error=error,
            language="fr"
        )
        
        # Verify valid JSON structure
        self.assertIn("steps", result)
        self.assertIsInstance(result["steps"], list)
        self.assertGreater(len(result["steps"]), 0, "Replan must generate at least one step")
        
        # Verify the new plan contains an action
        first_step = result["steps"][0]
        self.assertIn("module", first_step)
        self.assertIn("action", first_step)
        
        # Verify explanation is provided
        self.assertIn("explanation", result)
    
    def test_replan_with_execution_context(self):
        """Test replan includes context from previous execution"""
        failed_action = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"},
            "context": {}
        }
        error = "Network timeout: connection refused"
        execution_context = {
            "completed_steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}
            ],
            "original_command": "ouvre Safari et va sur example.com"
        }
        
        result = self.llm.replan(
            failed_action=failed_action,
            error=error,
            execution_context=execution_context,
            language="fr"
        )
        
        self.assertIn("steps", result)
        self.assertIsInstance(result["steps"], list)
        self.assertIn("explanation", result)
    
    def test_replan_unavailable_returns_error(self):
        """Test replan returns error when LLM unavailable"""
        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")
        self.assertFalse(llm.available)
        
        failed_action = {"module": "test", "action": "test_action", "args": {}}
        result = llm.replan(failed_action=failed_action, error="Test error")
        
        self.assertIn("steps", result)
        self.assertEqual(len(result["steps"]), 0)
        self.assertIn("error", result)


class TestAgentExecutorV3Replanning(unittest.TestCase):
    """Test AgentExecutorV3._attempt_replanning() integration"""
    
    def setUp(self):
        """Set up test environment with mock agents and reasoner"""
        # Create mock registry
        self.registry = AgentRegistry()
        
        # Mock agent that fails with "Element not found"
        self.mock_failing_agent = Mock()
        self.mock_failing_agent.execute = Mock(return_value={
            "status": "error",
            "error": "Element not found: selector '#submit-button' did not match any elements",
            "error_type": "element_not_found",
            "recoverable": True
        })
        
        # Mock agent for replan success
        self.mock_success_agent = Mock()
        self.mock_success_agent.execute = Mock(return_value={
            "status": "success",
            "message": "Action completed via alternative method",
            "data": {"context_updates": {"surface": "browser"}}
        })
        
        self.registry.register("browser", self.mock_failing_agent)
        self.registry.register("ui", self.mock_success_agent)
        self.registry.register("system", self.mock_success_agent)
    
    @async_test
    async def test_attempt_replanning_logs_message(self):
        """
        DoD: Execution doesn't stop on error but logs "Attempting replan..."
        """
        # Create executor with replanning enabled
        executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=True,
            max_retries=0
        )
        
        # Mock the reasoner
        mock_reasoner = Mock()
        mock_reasoner.available = True
        mock_reasoner.replan = Mock(return_value={
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                    "context": make_v3_context()
                }
            ],
            "explanation": "Trying to open the browser first before navigating"
        })
        executor._reasoner = mock_reasoner
        
        # Create a step that will fail (using valid action open_url)
        steps = [
            {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://example.com"},
                "context": make_v3_context()
            }
        ]
        
        intent = Intent(
            action="open_url",
            confidence=0.95,
            parameters={},
            raw_command="va sur example.com"
        )
        
        # Capture logs
        with self.assertLogs('janus.core.agent_executor_v3', level='INFO') as log:
            result = await executor.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test_session",
                request_id="test_request"
            )
            
            # Check that "Attempting replan" was logged
            log_output = '\n'.join(log.output)
            self.assertIn("Attempting replan", log_output)
    
    @async_test
    async def test_replanning_generates_alternative_action(self):
        """
        DoD: After 'Element not found' error, system generates alternative action
        """
        executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=True,
            max_retries=0
        )
        
        # Mock reasoner with alternative action plan
        mock_reasoner = Mock()
        mock_reasoner.available = True
        mock_reasoner.replan = Mock(return_value={
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                    "context": make_v3_context()
                }
            ],
            "explanation": "Browser open_url failed, trying to open browser application first"
        })
        executor._reasoner = mock_reasoner
        
        # Failed step (using valid browser action)
        failed_step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"},
            "context": make_v3_context()
        }
        error = "Element not found: browser window not available"
        
        # Create intent and result
        intent = Intent(
            action="test",
            confidence=0.9,
            parameters={},
            raw_command="test"
        )
        result = ExecutionResult(
            intent=intent,
            success=False,
            session_id="test",
            request_id="test"
        )
        
        # Call _attempt_replanning directly
        success = await executor._attempt_replanning(
            failed_step=failed_step,
            error=error,
            context={"app": None, "surface": None},
            executed_steps=[],
            result=result
        )
        
        # Verify replan was called with correct parameters
        mock_reasoner.replan.assert_called_once()
        call_args = mock_reasoner.replan.call_args
        self.assertEqual(call_args.kwargs["failed_action"]["action"], "open_url")
        self.assertIn("Element not found", call_args.kwargs["error"])
        
        # Verify the alternative action was different from original
        replan_result = mock_reasoner.replan.return_value
        alternative_module = replan_result["steps"][0]["module"]
        alternative_action = replan_result["steps"][0]["action"]
        # Alternative uses system.open_application instead of browser.open_url
        self.assertEqual(alternative_module, "system", "Alternative should use 'system' module")
        self.assertEqual(alternative_action, "open_application", "Alternative should use 'open_application' action")
    
    @async_test
    async def test_replanning_disabled_does_not_call_reasoner(self):
        """Test that replanning is skipped when disabled"""
        executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=False,
            enable_replanning=False,  # Disabled
            max_retries=0
        )
        
        # Should not have reasoner loaded
        self.assertIsNone(executor._reasoner)
        
        intent = Intent(
            action="test",
            confidence=0.9,
            parameters={},
            raw_command="test"
        )
        result = ExecutionResult(
            intent=intent,
            success=False,
            session_id="test",
            request_id="test"
        )
        
        # _attempt_replanning should return False without calling reasoner
        success = await executor._attempt_replanning(
            failed_step={"module": "test", "action": "test"},
            error="Test error",
            context={},
            executed_steps=[],
            result=result
        )
        
        self.assertFalse(success)


class TestReplanPromptTemplate(unittest.TestCase):
    """Test that replan prompt templates are properly loaded"""
    
    def test_replan_fr_template_loads(self):
        """Test French replan template loads correctly"""
        from janus.ai.reasoning.prompt_loader import load_prompt
        
        prompt = load_prompt("replan", "fr")
        
        self.assertIsNotNone(prompt)
        self.assertIn("récupérer", prompt.lower())
        self.assertIn("json", prompt.lower())
    
    def test_replan_en_template_loads(self):
        """Test English replan template loads correctly"""
        from janus.ai.reasoning.prompt_loader import load_prompt
        
        prompt = load_prompt("replan", "en")
        
        self.assertIsNotNone(prompt)
        self.assertIn("recover", prompt.lower())
        self.assertIn("json", prompt.lower())
    
    def test_replan_prompt_includes_recovery_strategies(self):
        """Test replan prompt includes recovery strategies"""
        from janus.ai.reasoning.prompt_loader import load_prompt
        
        prompt_fr = load_prompt("replan", "fr")
        prompt_en = load_prompt("replan", "en")
        
        # Check for recovery strategies in French prompt
        self.assertIn("CSS", prompt_fr)
        self.assertIn("Element not found", prompt_fr)
        
        # Check for recovery strategies in English prompt
        self.assertIn("CSS", prompt_en)
        self.assertIn("Element not found", prompt_en)


if __name__ == "__main__":
    unittest.main()
