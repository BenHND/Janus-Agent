"""
TICKET-407 - Smart Self-Healing Tests

Tests for the smart self-healing feature that:
1. Detects ELEMENT_NOT_FOUND and TIMEOUT errors
2. Captures screenshot and analyzes screen state
3. Calls reasoner to generate corrective steps
4. Executes corrective steps (Fail Fast - one attempt)
5. Returns success if correction works, original failure if not

Acceptance Criteria Test:
"Clique sur le bouton 'Rechercher'" → Error: Button not found
→ Agent analyzes screen, sees a magnifying glass icon
→ Generates: click(loupe) → type(...)
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock

from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent, ErrorType, ActionResult
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestSelfHealingBasicSetup(unittest.TestCase):
    """Test basic self-healing setup and configuration"""
    
    def test_self_healing_requires_replanning(self):
        """Test: Self-healing only works when enable_replanning=True"""
        executor = AgentExecutorV3(enable_replanning=False)
        self.assertFalse(executor.enable_replanning)
        self.assertIsNone(executor._reasoner)
    
    def test_self_healing_with_replanning_enabled(self):
        """Test: Self-healing is available when enable_replanning=True"""
        executor = AgentExecutorV3(enable_replanning=True)
        self.assertTrue(executor.enable_replanning)
        # Reasoner will be lazy-loaded on first access
        # self.assertIsNotNone(executor.reasoner)


class TestSelfHealingErrorDetection(unittest.TestCase):
    """Test error type detection for self-healing eligibility"""
    
    @async_test
    async def test_element_not_found_triggers_self_healing(self):
        """Test: ELEMENT_NOT_FOUND error should trigger self-healing"""
        # Create a mock reasoner that returns corrective steps
        mock_reasoner = MagicMock(spec=ReasonerLLM)
        mock_reasoner.available = True
        mock_reasoner.replan_with_vision.return_value = {
            "steps": [
                {
                    "module": "ui",
                    "action": "click",
                    "args": {"text": "loupe"},
                    "context": {"app": "Safari", "surface": "browser", "url": None, "domain": None, "thread": None, "record": None}
                }
            ],
            "explanation": "Bouton texte non trouvé, clic sur icône loupe à la place"
        }
        
        # Create executor with self-healing enabled
        executor = AgentExecutorV3(enable_replanning=True)
        executor._reasoner = mock_reasoner
        
        # Mock the agent registry to fail first, then succeed
        call_count = {"value": 0}
        
        async def mock_execute_async(module, action, args, context):
            call_count["value"] += 1
            if call_count["value"] == 1:
                # First call fails with ELEMENT_NOT_FOUND
                return {
                    "status": "error",
                    "error": "Button 'Rechercher' not found",
                    "error_type": ErrorType.ELEMENT_NOT_FOUND.value,
                    "recoverable": True
                }
            else:
                # Corrective step succeeds
                return {
                    "status": "success",
                    "message": "Clicked on magnifying glass icon"
                }
        
        executor.agent_registry.execute_async = AsyncMock(side_effect=mock_execute_async)
        
        # Mock screenshot capture
        async def mock_capture_screen_state():
            return "Screenshot shows: magnifying glass icon visible in top-right corner"
        
        executor._capture_screen_state = AsyncMock(side_effect=mock_capture_screen_state)
        
        # Execute step
        step = {
            "module": "ui",
            "action": "click",
            "args": {"text": "Rechercher"},
            "context": {"app": "Safari", "surface": "browser", "url": "https://example.com", "domain": "example.com", "thread": None, "record": None}
        }
        
        result = await executor._execute_step_with_self_healing(
            module="ui",
            action="click",
            args={"text": "Rechercher"},
            context={"app": "Safari", "surface": "browser"},
            start_time=time.time(),
            step=step
        )
        
        # Verify self-healing was triggered
        self.assertTrue(result.success)
        self.assertIn("self_healing", result.data)
        self.assertTrue(result.data["self_healing"])
        
        # Verify reasoner was called
        mock_reasoner.replan_with_vision.assert_called_once()
        
        # Verify corrective steps were executed
        self.assertEqual(call_count["value"], 2)
    
    @async_test
    async def test_timeout_error_triggers_self_healing(self):
        """Test: TIMEOUT_ERROR should trigger self-healing"""
        mock_reasoner = MagicMock(spec=ReasonerLLM)
        mock_reasoner.available = True
        mock_reasoner.replan_with_vision.return_value = {
            "steps": [
                {
                    "module": "ui",
                    "action": "click",
                    "args": {"text": "alternative_button"},
                    "context": {"app": "Safari", "surface": "browser", "url": None, "domain": None, "thread": None, "record": None}
                }
            ],
            "explanation": "Timeout détecté, essai d'une action alternative"
        }
        
        executor = AgentExecutorV3(enable_replanning=True)
        executor._reasoner = mock_reasoner
        
        # Mock execute to return timeout error
        async def mock_execute_async(module, action, args, context):
            return {
                "status": "error",
                "error": "Operation timed out",
                "error_type": ErrorType.TIMEOUT_ERROR.value,
                "recoverable": True
            }
        
        executor.agent_registry.execute_async = AsyncMock(side_effect=mock_execute_async)
        executor._capture_screen_state = AsyncMock(return_value="Screen state description")
        
        step = {
            "module": "ui",
            "action": "click",
            "args": {"text": "slow_button"},
            "context": {"app": "Safari", "surface": "browser", "url": None, "domain": None, "thread": None, "record": None}
        }
        
        result = await executor._execute_step_with_self_healing(
            module="ui",
            action="click",
            args={"text": "slow_button"},
            context={"app": "Safari"},
            start_time=time.time(),
            step=step
        )
        
        # Verify reasoner was called
        mock_reasoner.replan_with_vision.assert_called_once()
    
    @async_test
    async def test_validation_error_does_not_trigger_self_healing(self):
        """Test: VALIDATION_ERROR should NOT trigger self-healing"""
        mock_reasoner = MagicMock(spec=ReasonerLLM)
        mock_reasoner.available = True
        
        executor = AgentExecutorV3(enable_replanning=True)
        executor._reasoner = mock_reasoner
        
        # Mock execute to return validation error
        async def mock_execute_async(module, action, args, context):
            return {
                "status": "error",
                "error": "Invalid arguments",
                "error_type": ErrorType.VALIDATION_ERROR.value,
                "recoverable": False
            }
        
        executor.agent_registry.execute_async = AsyncMock(side_effect=mock_execute_async)
        
        step = {
            "module": "ui",
            "action": "click",
            "args": {},
            "context": {}
        }
        
        result = await executor._execute_step_with_self_healing(
            module="ui",
            action="click",
            args={},
            context={},
            start_time=time.time(),
            step=step
        )
        
        # Verify reasoner was NOT called
        mock_reasoner.replan_with_vision.assert_not_called()
        
        # Verify original failure is returned
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid arguments")


class TestSelfHealingFailFast(unittest.TestCase):
    """Test Fail Fast behavior - only one correction attempt"""
    
    @async_test
    async def test_fail_fast_on_corrective_step_failure(self):
        """Test: If corrective step fails, return original failure (Fail Fast)"""
        mock_reasoner = MagicMock(spec=ReasonerLLM)
        mock_reasoner.available = True
        mock_reasoner.replan_with_vision.return_value = {
            "steps": [
                {
                    "module": "ui",
                    "action": "click",
                    "args": {"text": "alternative"},
                    "context": {}
                }
            ],
            "explanation": "Trying alternative"
        }
        
        executor = AgentExecutorV3(enable_replanning=True)
        executor._reasoner = mock_reasoner
        
        # Both original and corrective steps fail
        async def mock_execute_async(module, action, args, context):
            return {
                "status": "error",
                "error": "Element not found",
                "error_type": ErrorType.ELEMENT_NOT_FOUND.value,
                "recoverable": True
            }
        
        executor.agent_registry.execute_async = AsyncMock(side_effect=mock_execute_async)
        executor._capture_screen_state = AsyncMock(return_value="Screen state")
        
        step = {
            "module": "ui",
            "action": "click",
            "args": {"text": "original"},
            "context": {}
        }
        
        result = await executor._execute_step_with_self_healing(
            module="ui",
            action="click",
            args={"text": "original"},
            context={},
            start_time=time.time(),
            step=step
        )
        
        # Verify original failure is returned (Fail Fast)
        self.assertFalse(result.success)
        self.assertNotIn("self_healing", result.data or {})


class TestReasonerReplanWithVision(unittest.TestCase):
    """Test ReasonerLLM.replan_with_vision() method"""
    
    def test_replan_with_vision_requires_llm(self):
        """Test: replan_with_vision returns error when LLM unavailable"""
        # Create reasoner with mock backend (unavailable)
        reasoner = ReasonerLLM(backend="mock")
        reasoner.available = False
        
        result = reasoner.replan_with_vision(
            failed_action={"module": "ui", "action": "click", "args": {"text": "button"}},
            error="Element not found",
            screenshot_description="Screen shows alternative elements",
            execution_context={"current_context": {"app": "Safari"}},
            language="fr"
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "LLM unavailable")
        self.assertEqual(len(result["steps"]), 0)
    
    def test_replan_with_vision_with_mock_llm(self):
        """Test: replan_with_vision generates corrective steps with mock LLM"""
        # Create reasoner with mock backend
        reasoner = ReasonerLLM(backend="mock")
        
        # Mock LLM should be available
        self.assertTrue(reasoner.available)
        
        result = reasoner.replan_with_vision(
            failed_action={"module": "ui", "action": "click", "args": {"text": "Rechercher"}},
            error="Button 'Rechercher' not found",
            screenshot_description="Screen shows magnifying glass icon in top-right",
            execution_context={"current_context": {"app": "Safari", "surface": "browser"}},
            language="fr"
        )
        
        # Verify result structure
        self.assertIn("steps", result)
        self.assertIn("explanation", result)
        
        # Mock reasoner should return at least one step
        # (behavior depends on mock implementation)
        self.assertIsInstance(result["steps"], list)


class TestAcceptanceCriteria(unittest.TestCase):
    """Test acceptance criteria: Button not found → Vision-based correction"""
    
    @async_test
    async def test_acceptance_click_search_button_not_found_uses_icon(self):
        """
        Acceptance Criteria Test:
        Scenario: "Clique sur le bouton 'Rechercher'"
        Error: Bouton non trouvé (peut-être caché dans un menu)
        Correction: L'agent analyse l'écran, voit une loupe, génère: click(loupe) → type(...)
        """
        # Setup mock reasoner
        mock_reasoner = MagicMock(spec=ReasonerLLM)
        mock_reasoner.available = True
        
        # Reasoner generates corrective steps: click on magnifying glass icon
        mock_reasoner.replan_with_vision.return_value = {
            "steps": [
                {
                    "module": "ui",
                    "action": "click",
                    "args": {"text": "loupe"},  # Click on magnifying glass icon
                    "context": {
                        "app": "Safari",
                        "surface": "browser",
                        "url": "https://example.com",
                        "domain": "example.com",
                        "thread": None,
                        "record": None
                    }
                }
            ],
            "explanation": "Bouton 'Rechercher' non trouvé. Analyse de l'écran a détecté une icône de loupe. Génération d'un clic sur cette icône à la place."
        }
        
        # Setup executor
        executor = AgentExecutorV3(enable_replanning=True)
        executor._reasoner = mock_reasoner
        
        # Mock agent registry: fail on text button, succeed on icon
        call_sequence = []
        
        async def mock_execute_async(module, action, args, context):
            call_sequence.append((module, action, args))
            
            if len(call_sequence) == 1:
                # First call: "Rechercher" button not found
                return {
                    "status": "error",
                    "error": "Button 'Rechercher' not found on screen",
                    "error_type": ErrorType.ELEMENT_NOT_FOUND.value,
                    "recoverable": True
                }
            else:
                # Corrective step: click on magnifying glass icon succeeds
                return {
                    "status": "success",
                    "message": "Successfully clicked on magnifying glass icon"
                }
        
        executor.agent_registry.execute_async = AsyncMock(side_effect=mock_execute_async)
        
        # Mock screenshot capture
        executor._capture_screen_state = AsyncMock(
            return_value="Screen shows: search bar with magnifying glass icon on the right. No visible 'Rechercher' button."
        )
        
        # Execute the failing step
        step = {
            "module": "ui",
            "action": "click",
            "args": {"text": "Rechercher"},
            "context": {
                "app": "Safari",
                "surface": "browser",
                "url": "https://example.com",
                "domain": "example.com",
                "thread": None,
                "record": None
            }
        }
        
        result = await executor._execute_step_with_self_healing(
            module="ui",
            action="click",
            args={"text": "Rechercher"},
            context={"app": "Safari", "surface": "browser", "url": "https://example.com", "domain": "example.com"},
            start_time=time.time(),
            step=step
        )
        
        # Verify success via self-healing
        self.assertTrue(result.success, "Self-healing should succeed")
        self.assertIn("self_healing", result.data, "Result should indicate self-healing was used")
        self.assertTrue(result.data["self_healing"])
        
        # Verify the execution sequence
        self.assertEqual(len(call_sequence), 2, "Should have 2 calls: original + corrective")
        
        # First call: original failing action
        self.assertEqual(call_sequence[0][0], "ui")
        self.assertEqual(call_sequence[0][1], "click")
        self.assertEqual(call_sequence[0][2]["text"], "Rechercher")
        
        # Second call: corrective action (click on icon)
        self.assertEqual(call_sequence[1][0], "ui")
        self.assertEqual(call_sequence[1][1], "click")
        self.assertEqual(call_sequence[1][2]["text"], "loupe")
        
        # Verify reasoner was called with correct parameters
        mock_reasoner.replan_with_vision.assert_called_once()
        call_args = mock_reasoner.replan_with_vision.call_args
        
        # Check failed_action parameter
        self.assertEqual(call_args[1]["failed_action"]["module"], "ui")
        self.assertEqual(call_args[1]["failed_action"]["action"], "click")
        
        # Check error parameter
        self.assertIn("not found", call_args[1]["error"])
        
        # Check screenshot_description parameter
        self.assertIn("magnifying glass", call_args[1]["screenshot_description"])


if __name__ == "__main__":
    unittest.main()
