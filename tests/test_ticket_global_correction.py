"""
Tests for TICKET: Global Pipeline Correction (Reasoner → Validator → Executor)

This test suite validates that:
1. Fallback returns SINGLE simple steps (no multi-action regex)
2. Validator is STRICT (no auto-correction)
3. Reasoner handles all multi-action planning
4. No manual parsing or "et/puis/ensuite" heuristics
"""

import unittest
from janus.ai.reasoning.reasoner_llm import ReasonerLLM
from janus.capabilities.agents.validator_agent import ValidatorAgent


class TestGlobalPipelineCorrection(unittest.TestCase):
    """Test suite for global pipeline correction"""

    def setUp(self):
        """Set up test fixtures"""
        # Use mock backend for testing
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = ValidatorAgent(
            strict_mode=True,
            auto_correct=False,
            allow_missing_context=False
        )

    def test_fallback_returns_single_step_only(self):
        """
        SECTION 1: Fallback should return SINGLE simple step, not multi-action plan.
        
        Test that _fallback_structured_plan returns only ONE step for commands
        like "ouvre Safari et va sur YouTube" (not 2 steps).
        """
        # Test with multi-action command (French)
        command_fr = "ouvre Safari et va sur YouTube"
        result_fr = self.reasoner._fallback_structured_plan(command_fr, None, "fr")
        
        # Fallback should either return 1 step (open Safari) OR empty plan
        # It should NOT return 2 steps (Safari + YouTube)
        steps = result_fr.get("steps", [])
        self.assertLessEqual(
            len(steps), 1,
            f"Fallback returned {len(steps)} steps for '{command_fr}'. "
            "Expected 0 or 1 step. Multi-action plans must come from LLM Reasoner only."
        )
        
        # If it returned a step, verify it's a simple open_application
        if steps:
            step = steps[0]
            self.assertEqual(step.get("module"), "system")
            self.assertEqual(step.get("action"), "open_application")
            self.assertIn(step.get("args", {}).get("app_name"), ["Safari", "Chrome", None])

    def test_fallback_no_multi_action_for_complex_commands(self):
        """
        SECTION 1: Fallback should return empty plan for complex multi-action commands.
        
        Commands like "cherche python" that previously created multi-step plans
        should now return either a single simple step OR empty plan.
        """
        # Test search command
        command_search = "cherche Python tutoriels"
        result_search = self.reasoner._fallback_structured_plan(command_search, None, "fr")
        steps_search = result_search.get("steps", [])
        
        # Should return 0 or 1 step (not 2+ steps)
        self.assertLessEqual(
            len(steps_search), 1,
            f"Fallback returned {len(steps_search)} steps for search command. "
            "Expected 0 or 1. Complex commands require LLM Reasoner."
        )

    def test_validator_strict_mode_default(self):
        """
        SECTION 2: Validator should default to STRICT mode (no auto-correction).
        """
        # Create default validator
        default_validator = ValidatorAgent()
        
        # Verify strict mode enabled by default
        self.assertTrue(
            default_validator.strict_mode,
            "ValidatorAgent should default to strict_mode=True"
        )
        
        # Verify auto-correction disabled by default
        self.assertFalse(
            default_validator.auto_correct,
            "ValidatorAgent should default to auto_correct=False"
        )
        
        # Verify missing context not allowed by default
        self.assertFalse(
            default_validator.allow_missing_context,
            "ValidatorAgent should default to allow_missing_context=False"
        )

    def test_validator_rejects_invalid_plan(self):
        """
        SECTION 2: Validator should REJECT invalid plans (not auto-correct them).
        """
        # Create an invalid plan (missing context)
        invalid_plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"}
                    # Missing "context" field - should be rejected
                }
            ]
        }
        
        # Validate with strict validator
        result = self.validator.validate(invalid_plan)
        
        # Should be rejected
        self.assertFalse(
            result["valid"],
            "Strict validator should reject plan with missing context field"
        )
        
        # Should have errors
        self.assertGreater(
            len(result["errors"]), 0,
            "Validator should provide error messages for invalid plan"
        )

    def test_reasoner_generates_multi_step_for_compound_command(self):
        """
        SECTION 3: LLM Reasoner (mock) should generate multi-step plan for "ouvre X et va sur Y".
        
        This tests that the mock backend correctly handles compound commands.
        """
        # Test with compound command (note: "va" is correct imperative form)
        command = "Ouvre Safari et va sur YouTube"
        result = self.reasoner.generate_structured_plan(command, language="fr")
        
        steps = result.get("steps", [])
        
        # Mock reasoner should generate 2 steps for this command
        self.assertGreaterEqual(
            len(steps), 2,
            f"Reasoner generated {len(steps)} steps for '{command}'. "
            "Expected 2+ steps (open Safari + navigate YouTube)"
        )
        
        # Verify first step is open_application
        if len(steps) >= 1:
            self.assertEqual(steps[0].get("module"), "system")
            self.assertEqual(steps[0].get("action"), "open_application")
        
        # Verify second step is browser action
        if len(steps) >= 2:
            self.assertEqual(steps[1].get("module"), "browser")
            self.assertIn(steps[1].get("action"), ["open_url", "search"])

    def test_no_regex_patterns_in_fallback(self):
        """
        SECTION 1: Verify that fallback code doesn't use multi-action regex patterns.
        
        This is a code inspection test to ensure the refactoring removed the regex.
        """
        import inspect
        
        # Get source code of _fallback_structured_plan
        source = inspect.getsource(self.reasoner._fallback_structured_plan)
        
        # Patterns that should NOT be in the code
        forbidden_patterns = [
            r"(et|and)\s+",  # "et" / "and" conjunction
            r"(puis|then)",  # "puis" / "then" sequence
            r"(ensuite)",    # "ensuite" continuation
            "multi_step_patterns",  # Old pattern list variable
        ]
        
        for pattern in forbidden_patterns:
            self.assertNotIn(
                pattern.replace("\\s", " ").replace("\\", ""),
                source.lower(),
                f"Fallback code should not contain pattern: {pattern}"
            )

    def test_reasoner_timeout_with_retry(self):
        """
        SECTION 6: Verify that reasoner has timeout and retry mechanism.
        """
        # Check config has timeout
        self.assertEqual(
            self.reasoner.config.timeout_ms, 5000,
            "Reasoner timeout should be 5000ms (5 seconds)"
        )
        
        # Verify generate_structured_plan has max_retries parameter
        import inspect
        sig = inspect.signature(self.reasoner.generate_structured_plan)
        self.assertIn(
            "max_retries",
            sig.parameters,
            "generate_structured_plan should have max_retries parameter"
        )


if __name__ == "__main__":
    unittest.main()
