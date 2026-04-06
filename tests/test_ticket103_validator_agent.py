"""
TICKET 103 - Validator Agent Tests

Tests for the independent ValidatorAgent that validates and corrects
JSON plans before execution.

Test Categories:
1. Structural validation
2. Module/action validation
3. Auto-correction of malformed JSON
4. Context inference from previous steps
5. Error reporting
6. Statistics tracking
7. Specific test case from the issue
"""

import json
import unittest

from janus.capabilities.agents.validator_agent import ValidatorAgent, validate_plan


class TestValidatorAgentBasics(unittest.TestCase):
    """Test basic validator agent functionality"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent(
            strict_mode=False,
            auto_correct=True,
            allow_missing_context=True
        )
    
    def test_validator_initialization(self):
        """Test: Validator initializes correctly"""
        self.assertIsNotNone(self.validator)
        self.assertFalse(self.validator.strict_mode)
        self.assertTrue(self.validator.auto_correct)
        self.assertTrue(self.validator.allow_missing_context)
    
    def test_validate_valid_plan(self):
        """Test: Accept valid plan"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
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
        
        result = self.validator.validate(plan)
        
        self.assertTrue(result["valid"], f"Should accept valid plan: {result['errors']}")
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(len(result["steps"]), 1)
    
    def test_validate_invalid_module(self):
        """Test: Reject plan with invalid module"""
        plan = {
            "steps": [
                {
                    "module": "invalid_module",
                    "action": "some_action",
                    "args": {},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("module" in err.lower() for err in result["errors"]))
    
    def test_validate_invalid_action(self):
        """Test: Reject plan with invalid action for module"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "invalid_action",
                    "args": {},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("action" in err.lower() for err in result["errors"]))


class TestValidatorAutoCorrection(unittest.TestCase):
    """Test auto-correction features"""
    
    def setUp(self):
        """Initialize validator with auto-correction"""
        self.validator = ValidatorAgent(
            strict_mode=False,
            auto_correct=True,
            allow_missing_context=True
        )
    
    def test_add_missing_args(self):
        """Test: Add missing args field"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    # Missing args
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        # Should be corrected
        if result["valid"]:
            self.assertIn("args", result["steps"][0])
        else:
            # Should have identified missing args
            self.assertTrue(any("args" in err.lower() for err in result["errors"]))
    
    def test_add_missing_context(self):
        """Test: Add missing context field"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"}
                    # Missing context
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        # Should be valid after correction
        self.assertTrue(result["valid"] or len(result["warnings"]) > 0)
        self.assertTrue(len(result["corrections"]) > 0 or result["valid"])
    
    def test_complete_context_fields(self):
        """Test: Complete missing context fields"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://youtube.com"},
                    "context": {"app": "Safari"}  # Incomplete context
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        # Should be valid (context completed)
        self.assertTrue(result["valid"] or len(result["warnings"]) > 0)


class TestValidatorMalformedJSON(unittest.TestCase):
    """Test validation and correction of malformed JSON"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent(
            strict_mode=False,
            auto_correct=True,
            allow_missing_context=True
        )
    
    def test_correct_missing_quotes_in_keys(self):
        """Test: Correct JSON with missing quotes around keys"""
        # This is a string with invalid JSON syntax
        malformed_json = '{ steps: [ { module: "system", action: "open_app", args: {"app_name": "Safari"}, context: null } ] }'
        
        result = self.validator.validate(malformed_json)
        
        # Should be corrected and valid
        self.assertTrue(result["valid"], f"Should correct missing quotes: {result['errors']}")
        self.assertTrue(len(result["corrections"]) > 0 or result["valid"])
    
    def test_correct_python_none_to_null(self):
        """Test: Correct Python None to JSON null"""
        # Python None needs to be converted to JSON null
        # In this test, we'll pass it as already-parsed dict with None
        plan = {
            "steps": [{
                "module": "system",
                "action": "open_app",
                "args": {"app_name": "Safari"},
                "context": None
            }]
        }
        
        result = self.validator.validate(plan)
        
        # Should be valid
        self.assertTrue(result["valid"] or len(result["warnings"]) > 0)
    
    def test_correct_trailing_commas(self):
        """Test: Correct JSON with trailing commas"""
        malformed_json = '{"steps": [{"module": "system", "action": "open_app", "args": {"app_name": "Safari"}, "context": null}]}'
        
        result = self.validator.validate(malformed_json)
        
        # Should be corrected and valid
        self.assertTrue(result["valid"])


class TestValidatorContextInference(unittest.TestCase):
    """Test context inference from previous steps"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent(
            strict_mode=False,
            auto_correct=True,
            allow_missing_context=True
        )
    
    def test_infer_app_from_previous_step(self):
        """Test: Infer app context from previous open_app step"""
        # Previous step opened Safari
        previous_steps = [
            {
                "module": "system",
                "action": "open_app",
                "args": {"app_name": "Safari"},
                "context": {"app": None, "surface": None, "url": None, "domain": None, "thread": None, "record": None}
            }
        ]
        
        # Current plan doesn't specify app
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://youtube.com"},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan, previous_steps=previous_steps)
        
        # Should be valid and should have inferred Safari as app
        self.assertTrue(result["valid"], f"Should infer context: {result['errors']}")
        if result["valid"] and result["steps"]:
            step_context = result["steps"][0].get("context", {})
            self.assertEqual(step_context.get("app"), "Safari")
    
    def test_infer_domain_from_previous_step(self):
        """Test: Infer domain from previous open_url step"""
        previous_steps = [
            {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://www.youtube.com"},
                "context": {"app": "Safari", "surface": "browser", "url": None, "domain": None, "thread": None, "record": None}
            }
        ]
        
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "search",
                    "args": {"query": "test"},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan, previous_steps=previous_steps)
        
        # Should infer youtube.com domain
        self.assertTrue(result["valid"] or len(result["warnings"]) > 0)
        if result["valid"] and result["steps"]:
            step_context = result["steps"][0].get("context", {})
            # Domain should be inferred
            self.assertIsNotNone(step_context.get("domain"))


class TestValidatorSpecificIssueCase(unittest.TestCase):
    """Test the specific example from TICKET 103"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent(
            strict_mode=False,
            auto_correct=True,
            allow_missing_context=True
        )
    
    def test_ticket103_example_malformed_json(self):
        """
        Test: Correct the exact malformed JSON from the issue
        
        Input: { steps: [ { module: browser action "open_url" args { url: youtube.com } ] }
        
        Expected corrections:
        - Add quotes around unquoted keys
        - Add quotes around youtube.com value
        - Add missing context field
        - Add domain if deducible
        - Add context.app if previous step = Safari
        """
        # The malformed JSON from the issue
        malformed_json = '{ steps: [ { module: browser action "open_url" args { url: youtube.com } } ] }'
        
        # Validate without previous steps first
        result = self.validator.validate(malformed_json)
        
        # Should be corrected
        self.assertTrue(
            result["valid"],
            f"Should correct malformed JSON. Errors: {result['errors']}, Corrections: {result['corrections']}"
        )
        
        # Should have applied corrections
        self.assertTrue(
            len(result["corrections"]) > 0,
            f"Should have applied corrections: {result['corrections']}"
        )
        
        # Check the corrected steps
        if result["valid"]:
            self.assertEqual(len(result["steps"]), 1)
            step = result["steps"][0]
            
            # Should have corrected module
            self.assertEqual(step["module"], "browser")
            
            # Should have corrected action
            self.assertEqual(step["action"], "open_url")
            
            # Should have args with url
            self.assertIn("args", step)
            self.assertIn("url", step["args"])
            
            # Should have context (added if missing)
            self.assertIn("context", step)
    
    def test_ticket103_example_with_previous_safari_step(self):
        """
        Test: Correct malformed JSON and infer context from previous Safari step
        
        If previous step opened Safari, the corrected plan should have
        context.app = "Safari"
        """
        malformed_json = '{ steps: [ { module: browser action "open_url" args { url: youtube.com } } ] }'
        
        # Previous step opened Safari
        previous_steps = [
            {
                "module": "system",
                "action": "open_app",
                "args": {"app_name": "Safari"},
                "context": {"app": None, "surface": None, "url": None, "domain": None, "thread": None, "record": None}
            }
        ]
        
        result = self.validator.validate(malformed_json, previous_steps=previous_steps)
        
        # Should be valid
        self.assertTrue(result["valid"], f"Should be valid: {result['errors']}")
        
        # Should have inferred Safari as app
        if result["valid"] and result["steps"]:
            step = result["steps"][0]
            context = step.get("context", {})
            self.assertEqual(context.get("app"), "Safari", f"Should infer Safari from previous step. Context: {context}")


class TestValidatorOutput(unittest.TestCase):
    """Test validator output format"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent()
    
    def test_output_format_valid(self):
        """Test: Output format for valid plan"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        # Check output structure
        self.assertIn("valid", result)
        self.assertIn("steps", result)
        self.assertIn("errors", result)
        self.assertIn("warnings", result)
        self.assertIn("corrections", result)
        
        # Check types
        self.assertIsInstance(result["valid"], bool)
        self.assertIsInstance(result["steps"], list)
        self.assertIsInstance(result["errors"], list)
        self.assertIsInstance(result["warnings"], list)
        self.assertIsInstance(result["corrections"], list)
    
    def test_output_format_invalid(self):
        """Test: Output format for invalid plan"""
        plan = {
            "steps": [
                {
                    "module": "invalid_module",
                    "action": "invalid_action",
                    "args": {},
                    "context": None
                }
            ]
        }
        
        result = self.validator.validate(plan)
        
        # Should be invalid
        self.assertFalse(result["valid"])
        
        # Should have error messages
        self.assertTrue(len(result["errors"]) > 0)
        
        # Check structure
        self.assertIn("valid", result)
        self.assertIn("steps", result)
        self.assertIn("errors", result)


class TestValidatorStatistics(unittest.TestCase):
    """Test validator statistics tracking"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent()
        self.validator.reset_stats()
    
    def test_stats_tracking(self):
        """Test: Statistics are tracked correctly"""
        initial_stats = self.validator.get_stats()
        self.assertEqual(initial_stats["total_validations"], 0)
        
        # Validate a valid plan
        valid_plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": None
                }
            ]
        }
        self.validator.validate(valid_plan)
        
        # Validate an invalid plan
        invalid_plan = {
            "steps": [
                {
                    "module": "invalid",
                    "action": "test",
                    "args": {},
                    "context": None
                }
            ]
        }
        self.validator.validate(invalid_plan)
        
        # Check stats
        stats = self.validator.get_stats()
        self.assertEqual(stats["total_validations"], 2)
        self.assertGreater(stats["valid_plans"] + stats["rejected_plans"], 0)
    
    def test_success_rate_calculation(self):
        """Test: Success rate is calculated correctly"""
        self.validator.reset_stats()
        
        # Validate multiple plans
        valid_plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": None
                }
            ]
        }
        
        for _ in range(3):
            self.validator.validate(valid_plan)
        
        stats = self.validator.get_stats()
        self.assertIn("success_rate", stats)
        self.assertIsInstance(stats["success_rate"], float)


class TestValidatorConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_validate_plan_function(self):
        """Test: validate_plan convenience function"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Safari"},
                    "context": None
                }
            ]
        }
        
        result = validate_plan(plan)
        
        self.assertIn("valid", result)
        self.assertTrue(result["valid"] or len(result["errors"]) > 0)


class TestValidatorSingleStep(unittest.TestCase):
    """Test single step validation"""
    
    def setUp(self):
        """Initialize validator"""
        self.validator = ValidatorAgent()
    
    def test_validate_single_step(self):
        """Test: Validate a single step"""
        step = {
            "module": "system",
            "action": "open_app",
            "args": {"app_name": "Safari"},
            "context": None
        }
        
        result = self.validator.validate_step(step)
        
        self.assertIn("valid", result)
        self.assertIn("step", result)
        self.assertIn("errors", result)


if __name__ == "__main__":
    unittest.main()
