"""
Integration test for TICKET 003 - Reasoner with Strict Validator

This demonstrates the complete flow:
1. ReasonerLLM generates a plan (with schema-aware prompt)
2. StrictActionValidator validates and corrects the plan
3. Plan is ready for execution
"""

import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM
from janus.safety.validation.strict_action_validator import StrictActionValidator


class TestReasonerValidatorIntegration(unittest.TestCase):
    """Test integration of Reasoner with Strict Validator"""
    
    def setUp(self):
        """Set up test components"""
        # Use mock backend for fast, predictable tests
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = StrictActionValidator(
            auto_correct=True,
            allow_fallback=True,
            strict_mode=False
        )
        self.validator.reset_stats()
    
    def test_simple_command_validation(self):
        """Test that a simple command generates valid plan"""
        # Generate plan
        plan = self.reasoner.generate_structured_plan(
            command="ouvre Safari",
            language="fr"
        )
        
        # Validate plan
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"Plan should be valid. Errors: {errors}")
        self.assertIsNotNone(corrected_plan)
        self.assertEqual(len(corrected_plan["steps"]), len(plan["steps"]))
    
    def test_multi_step_command_validation(self):
        """Test multi-step command with validation"""
        # Generate plan for complex command
        plan = self.reasoner.generate_structured_plan(
            command="ouvre Safari, va sur YouTube et cherche Python",
            language="fr"
        )
        
        # Validate plan
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"Plan should be valid. Errors: {errors}")
        self.assertIsNotNone(corrected_plan)
        
        # Check that all steps are valid
        self.assertGreaterEqual(len(corrected_plan["steps"]), 3)
        
        # Verify modules and actions
        from janus.runtime.core.module_action_schema import is_valid_module, is_valid_action
        for step in corrected_plan["steps"]:
            module = step["module"]
            action = step["action"]
            self.assertTrue(is_valid_module(module), f"Invalid module: {module}")
            self.assertTrue(is_valid_action(module, action), f"Invalid action: {module}.{action}")
    
    def test_alias_normalization(self):
        """Test that validator normalizes aliases to canonical names"""
        # Create a plan with action aliases
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",  # Alias for open_app
                    "args": {"app_name": "Chrome"},
                    "context": {}
                },
                {
                    "module": "browser",
                    "action": "navigate",  # Alias for open_url
                    "args": {"url": "https://youtube.com"},
                    "context": {}
                }
            ]
        }
        
        # Validate and normalize
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_plan)
        
        # Check that aliases were normalized
        self.assertEqual(corrected_plan["steps"][0]["action"], "open_app")
        self.assertEqual(corrected_plan["steps"][1]["action"], "open_url")
    
    def test_invalid_action_correction(self):
        """Test that validator corrects or fallsback for invalid actions"""
        # Create a plan with an invalid action
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": {}
                },
                {
                    "module": "browser",
                    "action": "nonexistent_action",  # Invalid
                    "args": {},
                    "context": {}
                }
            ]
        }
        
        # Validate with auto-correct and fallback
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        # With fallback enabled, should still succeed
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_plan)
        
        # First step should be unchanged
        self.assertEqual(corrected_plan["steps"][0]["action"], "open_app")
        
        # Second step should have fallback
        self.assertIn("fallback_reason", corrected_plan["steps"][1])
    
    def test_validation_statistics(self):
        """Test that validator tracks statistics correctly"""
        self.validator.reset_stats()
        
        # Validate several plans
        plans = [
            {"steps": [{"module": "system", "action": "open_app", "args": {"app_name": "Safari"}}]},
            {"steps": [{"module": "SYSTEM", "action": "open_app", "args": {"app_name": "Chrome"}}]},  # Needs correction
            {"steps": [{"module": "browser", "action": "open_url", "args": {"url": "https://google.com"}}]},
        ]
        
        for plan in plans:
            self.validator.validate_plan(plan)
        
        # Check statistics
        stats = self.validator.get_validation_report()
        
        self.assertEqual(stats["total_validations"], 3)
        self.assertGreater(stats["success_rate"], 0)
    
    def test_reasoner_prompt_includes_schema(self):
        """Test that Reasoner prompt includes the complete schema"""
        # Build a prompt
        prompt = self.reasoner._build_structured_plan_prompt(
            command="test command",
            context=None,
            language="fr"
        )
        
        # Check that schema is included
        self.assertIn("MODULES DISPONIBLES", prompt)
        self.assertIn("system", prompt.lower())
        self.assertIn("browser", prompt.lower())
        self.assertIn("llm", prompt.lower())
        self.assertIn("RÈGLES STRICTES", prompt)
    
    def test_end_to_end_workflow(self):
        """Test complete workflow: generate -> validate -> execute"""
        # 1. Generate plan with Reasoner
        command = "ouvre Chrome et va sur YouTube"
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)
        
        # 2. Validate with StrictValidator
        is_valid, validated_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"Validation failed: {errors}")
        self.assertIsNotNone(validated_plan)
        
        # 3. Check that plan is execution-ready
        from janus.runtime.core.module_action_schema import validate_action_plan
        plan_valid, plan_errors = validate_action_plan(validated_plan)
        
        self.assertTrue(plan_valid, f"Plan not execution-ready: {plan_errors}")
        
        # 4. Verify all required fields are present
        for step in validated_plan["steps"]:
            self.assertIn("module", step)
            self.assertIn("action", step)
            self.assertIn("args", step)
            self.assertIn("context", step)
    
    def test_strict_mode_rejects_invalid(self):
        """Test that strict mode rejects invalid plans"""
        # Create validator in strict mode
        strict_validator = StrictActionValidator(
            auto_correct=False,
            allow_fallback=False,
            strict_mode=True
        )
        
        # Create a plan with case issue
        plan = {
            "steps": [
                {
                    "module": "SYSTEM",  # Wrong case
                    "action": "open_app",
                    "args": {"app_name": "Safari"}
                }
            ]
        }
        
        # Validate in strict mode
        is_valid, corrected_plan, errors = strict_validator.validate_plan(plan)
        
        # Should reject
        self.assertFalse(is_valid)
        self.assertIsNone(corrected_plan)
        self.assertGreater(len(errors), 0)
    
    def test_llm_action_validation(self):
        """Test that LLM module actions are validated correctly"""
        # Create plan with LLM actions
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "extract_text",
                    "args": {},
                    "context": {}
                },
                {
                    "module": "llm",
                    "action": "summarize",
                    "args": {"input_from": "last_output"},
                    "context": {}
                }
            ]
        }
        
        # Validate
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid, f"LLM actions should be valid. Errors: {errors}")
        self.assertIsNotNone(corrected_plan)
        
        # Check both steps are valid
        self.assertEqual(len(corrected_plan["steps"]), 2)
        self.assertEqual(corrected_plan["steps"][0]["module"], "browser")
        self.assertEqual(corrected_plan["steps"][1]["module"], "llm")


if __name__ == "__main__":
    unittest.main()
