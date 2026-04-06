"""
Test for CRITICAL: Reasoner Runtime Failures & Execution Shutdown

This test verifies the fixes for the critical reasoner issues:
1. Timeout increased to 8 seconds (was 3 seconds)
2. Split fallback removed from UnifiedCommandParser
3. Validator rejects empty plans
4. Executor never triggers shutdown
5. "Ouvre Safari et vas sur YouTube" works correctly
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.legacy.parser.unified_command_parser import ParserProvider, UnifiedCommandParser
from janus.ai.reasoning.reasoner_llm import LLMBackend, LLMConfig, ReasonerLLM
from janus.safety.validation.json_plan_validator import JSONPlanValidator


class TestCriticalReasonerFixes(unittest.TestCase):
    """Test suite for critical reasoner fixes"""

    def test_reasoner_timeout_increased(self):
        """
        CA1: Verify ReasonerLLM timeout is 8 seconds (not 3 seconds)
        """
        # Test default config
        config = LLMConfig(backend=LLMBackend.MOCK)
        self.assertEqual(
            config.timeout_ms,
            8000,
            "Timeout must be 8000ms (8 seconds), not 3000ms"
        )
        self.assertEqual(
            config.short_timeout_ms,
            4000,
            "Short timeout must be 4000ms (4 seconds), not 1500ms"
        )

    def test_no_split_fallback_in_parser(self):
        """
        CA2: Verify UnifiedCommandParser does not use split fallback
        """
        # Create mock LLM service
        mock_llm = MagicMock()
        mock_llm.available = True
        mock_llm.parse_command = MagicMock(return_value={
            "intents": [],
            "confidence": 0.0,
            "source": "error",
            "error": "LLM failed"
        })

        # Create parser with HYBRID mode
        parser = UnifiedCommandParser(
            provider=ParserProvider.HYBRID,
            llm_service=mock_llm,
            confidence_threshold=0.6
        )

        # Parse a complex command that would trigger split fallback
        result = parser.parse("ouvre Safari et vas sur YouTube")

        # The parser should return error result, not split result
        self.assertEqual(len(result), 1, "Should return single error result, not split")
        self.assertEqual(
            result[0].confidence,
            0.0,
            "Failed parse should have 0 confidence"
        )

    def test_validator_rejects_empty_plans(self):
        """
        CA3: Verify ValidatorAgent rejects plans with 0 steps
        """
        validator = JSONPlanValidator(strict_mode=True)

        # Test empty plan
        empty_plan = {"steps": []}
        result = validator.validate_plan(empty_plan)

        self.assertFalse(result.is_valid, "Empty plan must be INVALID")
        self.assertTrue(
            len(result.errors) > 0,
            "Empty plan must have errors"
        )
        self.assertTrue(
            any("no actionable steps" in err.message.lower() for err in result.errors),
            "Error message must mention 'no actionable steps'"
        )

    def test_executor_never_triggers_shutdown(self):
        """
        CA4: Verify AgentExecutorV3 never triggers application shutdown
        """
        # This test verifies that executor doesn't call sys.exit, os._exit, etc.
        # We'll verify the code doesn't import or use these functions

        import inspect

        executor_source = inspect.getsource(AgentExecutorV3)

        # Check that shutdown-related functions are not called
        forbidden_calls = ['sys.exit', 'os._exit', 'quit()', 'exit()']
        for call in forbidden_calls:
            self.assertNotIn(
                call,
                executor_source,
                f"AgentExecutorV3 must not call {call}"
            )

    def test_safari_youtube_command_produces_correct_plan(self):
        """
        CA5: Verify "Ouvre Safari et vas sur YouTube" produces correct plan
        
        Expected output:
        - Step 1: open_application Safari
        - Step 2: open_url https://youtube.com
        """
        # Use mock backend for testing
        reasoner = ReasonerLLM(backend="mock")
        self.assertTrue(reasoner.available, "Mock reasoner should be available")

        # Test the exact command from the issue
        command = "Ouvre Safari et vas sur YouTube"
        start_time = time.time()
        
        result = reasoner.generate_structured_plan(command, language="fr")
        
        elapsed_time = time.time() - start_time

        # Verify timing
        self.assertLess(
            elapsed_time,
            1.5,
            f"Command should complete in <1.5s, took {elapsed_time:.2f}s"
        )

        # Verify result structure
        self.assertIn("steps", result, "Result must have 'steps' field")
        steps = result["steps"]
        self.assertEqual(len(steps), 2, "Command should produce 2 steps")

        # Verify Step 1: open_application Safari
        step1 = steps[0]
        self.assertEqual(step1["module"], "system", "Step 1 module should be 'system'")
        self.assertEqual(
            step1["action"],
            "open_application",
            "Step 1 action should be 'open_application'"
        )
        self.assertIn("app_name", step1["args"], "Step 1 should have app_name arg")
        self.assertEqual(
            step1["args"]["app_name"],
            "Safari",
            "Step 1 should open Safari"
        )

        # Verify Step 2: open_url https://youtube.com
        step2 = steps[1]
        self.assertEqual(step2["module"], "browser", "Step 2 module should be 'browser'")
        self.assertEqual(
            step2["action"],
            "open_url",
            "Step 2 action should be 'open_url'"
        )
        self.assertIn("url", step2["args"], "Step 2 should have url arg")
        self.assertIn(
            "youtube.com",
            step2["args"]["url"],
            "Step 2 should navigate to YouTube"
        )

        # Verify context propagation
        self.assertIsNotNone(step1.get("context"), "Step 1 should have context")
        self.assertIsNotNone(step2.get("context"), "Step 2 should have context")
        self.assertEqual(
            step2["context"]["app"],
            "Safari",
            "Step 2 context should show app=Safari"
        )
        self.assertEqual(
            step2["context"]["domain"],
            "youtube.com",
            "Step 2 context should show domain=youtube.com"
        )

    def test_various_multi_action_commands(self):
        """
        Additional test: Verify various multi-action commands work correctly
        """
        reasoner = ReasonerLLM(backend="mock")
        
        test_cases = [
            ("ouvre Chrome et vas sur YouTube", 2, "Chrome", "youtube.com"),
            ("lance Safari et ouvre GitHub", 2, "Safari", "github.com"),
        ]
        
        for command, expected_steps, expected_app, expected_domain in test_cases:
            with self.subTest(command=command):
                result = reasoner.generate_structured_plan(command, language="fr")
                
                self.assertIn("steps", result)
                steps = result["steps"]
                self.assertEqual(
                    len(steps),
                    expected_steps,
                    f"'{command}' should produce {expected_steps} steps"
                )
                
                # Verify first step opens the app
                self.assertEqual(steps[0]["module"], "system")
                self.assertEqual(steps[0]["action"], "open_application")
                self.assertEqual(steps[0]["args"]["app_name"], expected_app)
                
                # Verify second step navigates to URL
                self.assertEqual(steps[1]["module"], "browser")
                self.assertEqual(steps[1]["action"], "open_url")
                self.assertIn(expected_domain, steps[1]["args"]["url"])


if __name__ == "__main__":
    unittest.main()
