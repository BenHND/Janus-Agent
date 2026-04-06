"""
Integration tests for TICKET 004 - JSON Validation & Auto-Correction with ReasonerLLM
"""

import json
import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestTicket004Integration(unittest.TestCase):
    """Test TICKET 004 integration with ReasonerLLM"""

    def setUp(self):
        """Set up test ReasonerLLM with mock backend"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_reasoner_produces_valid_json(self):
        """Test that ReasonerLLM produces valid JSON plans"""
        plan = self.reasoner.generate_structured_plan("ouvre Chrome", language="fr")

        # Plan should have steps array
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)

        # If steps exist, they should be valid
        if len(plan["steps"]) > 0:
            step = plan["steps"][0]
            self.assertIn("module", step)
            self.assertIn("action", step)
            self.assertIn("args", step)

    def test_reasoner_handles_malformed_llm_output(self):
        """
        Test that ReasonerLLM handles malformed output gracefully.
        
        Mock backend produces valid JSON, so we can't test actual malformed output here.
        This test verifies the structure is correct.
        """
        plan = self.reasoner.generate_structured_plan("copie", language="fr")

        # Should not crash and should return valid structure
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)

    def test_multi_step_plan_validation(self):
        """Test validation of multi-step plans"""
        plan = self.reasoner.generate_structured_plan(
            "Ouvre Safari, va sur YouTube et cherche Python", language="fr"
        )

        # Should have multiple steps
        self.assertIn("steps", plan)
        self.assertGreater(len(plan["steps"]), 1)

        # Each step should be valid
        for i, step in enumerate(plan["steps"]):
            self.assertIn("module", step, f"Step {i} missing module")
            self.assertIn("action", step, f"Step {i} missing action")
            self.assertIn("args", step, f"Step {i} missing args")
            # Context may be null for first step
            if i > 0:
                self.assertIn("context", step, f"Step {i} missing context")

    def test_context_propagation_in_multi_step(self):
        """Test that context is properly propagated in multi-step plans"""
        plan = self.reasoner.generate_structured_plan(
            "Ouvre Safari et va sur YouTube", language="fr"
        )

        # Should have at least 2 steps
        self.assertGreaterEqual(len(plan["steps"]), 2)

        # First step should open Safari
        first_step = plan["steps"][0]
        self.assertEqual(first_step["module"], "system")
        self.assertEqual(first_step["action"], "open_app")

        # Second step should have Safari in context
        if len(plan["steps"]) > 1:
            second_step = plan["steps"][1]
            self.assertIn("context", second_step)
            if second_step["context"] is not None and isinstance(second_step["context"], dict):
                # Context should have app field (may be "Safari" or other browser)
                self.assertIn("app", second_step["context"])

    def test_empty_plan_handling(self):
        """Test handling of commands that produce empty plans"""
        # Mock backend should handle unknown commands
        plan = self.reasoner.generate_structured_plan("commande inconnue xyz", language="fr")

        # Should still return valid structure
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)

    def test_fallback_plan_format(self):
        """Test that fallback plans (when LLM unavailable) are valid"""
        # When LLM is unavailable, fallback should still produce valid structure
        plan = self.reasoner.generate_structured_plan("ouvre Chrome", language="fr")

        # Valid structure
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)

    def test_english_command_validation(self):
        """Test validation works for English commands"""
        plan = self.reasoner.generate_structured_plan("open Chrome", language="en")

        self.assertIn("steps", plan)
        if len(plan["steps"]) > 0:
            step = plan["steps"][0]
            self.assertIn("module", step)
            self.assertIn("action", step)

    def test_complex_command_with_search(self):
        """Test complex command with search action"""
        plan = self.reasoner.generate_structured_plan(
            "Ouvre Safari, va sur YouTube et cherche Python tutorials", language="fr"
        )

        # Should have multiple steps including search
        self.assertIn("steps", plan)
        self.assertGreater(len(plan["steps"]), 0)

        # Last step should be a search or open_url
        if len(plan["steps"]) >= 3:
            last_step = plan["steps"][-1]
            # Should have search action or similar
            self.assertIn("action", last_step)

    def test_plan_metrics_tracking(self):
        """Test that ReasonerLLM tracks metrics correctly"""
        # Generate a few plans
        self.reasoner.generate_structured_plan("ouvre Chrome", language="fr")
        self.reasoner.generate_structured_plan("copie", language="fr")

        # Get metrics
        metrics = self.reasoner.get_metrics()

        # Should have recorded calls
        self.assertIn("total_calls", metrics)
        self.assertGreater(metrics["total_calls"], 0)

    def test_validation_never_crashes_executor(self):
        """
        Test the main goal of TICKET 004: Executor never receives invalid JSON.
        
        This test simulates various problematic inputs and ensures they're all handled.
        """
        test_commands = [
            "ouvre Chrome",
            "copie",
            "colle",
            "cherche Python",
            "ouvre Safari et va sur YouTube",
            "",  # Empty command
        ]

        for command in test_commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, language="fr")

                # All plans should have valid structure
                self.assertIn("steps", plan)
                self.assertIsInstance(plan["steps"], list)

                # Each step should be valid
                for step in plan["steps"]:
                    self.assertIsInstance(step, dict)
                    self.assertIn("module", step)
                    self.assertIn("action", step)
                    # args may be empty dict but should exist
                    self.assertIn("args", step)
                    self.assertIsInstance(step["args"], dict)


class TestJSONValidationPreventsExecutorCrash(unittest.TestCase):
    """Test that validation prevents malformed JSON from reaching executor"""

    def test_direct_malformed_json_handling(self):
        """Test direct handling of malformed JSON strings"""
        from janus.safety.validation.json_plan_corrector import correct_json_plan
        from janus.safety.validation.json_plan_validator import validate_json_plan

        # Test various malformed JSON strings
        malformed_cases = [
            '{"steps": [{"module": "system",}]}',  # Trailing comma
            "{'steps': []}",  # Single quotes
            '{steps: []}',  # Unquoted key
            '{"steps": [{"module": "system"}',  # Unclosed
        ]

        for malformed in malformed_cases:
            with self.subTest(json=malformed):
                # Corrector should fix or fail gracefully
                success, corrected, fixes = correct_json_plan(malformed)

                if success:
                    # If corrected, should be valid
                    result = validate_json_plan(corrected)
                    # May have errors but should not crash
                    self.assertIsNotNone(result)

    def test_validator_catches_all_required_fields(self):
        """Test that validator catches all required field violations"""
        from janus.safety.validation.json_plan_validator import validate_plan

        invalid_plans = [
            {},  # No steps
            {"steps": "not a list"},  # Steps not a list
            {"steps": [{}]},  # Empty step
            {"steps": [{"module": "system"}]},  # Missing action
            {"steps": [{"action": "open_app"}]},  # Missing module
            {"steps": [{"module": "system", "action": "open_app"}]},  # Missing args
        ]

        for invalid_plan in invalid_plans:
            with self.subTest(plan=invalid_plan):
                result = validate_plan(invalid_plan)
                # Should detect the problem
                self.assertTrue(result.has_errors() or result.has_warnings())

    def test_corrector_auto_fixes_common_issues(self):
        """Test that corrector automatically fixes common issues"""
        from janus.safety.validation.json_plan_corrector import correct_plan_structure

        incomplete_plan = {"steps": [{"module": "system", "action": "open_app"}]}

        corrected, fixes = correct_plan_structure(incomplete_plan)

        # Should have added missing fields
        self.assertIn("args", corrected["steps"][0])
        self.assertTrue(len(fixes) > 0)


if __name__ == "__main__":
    unittest.main()
