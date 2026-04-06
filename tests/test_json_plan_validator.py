"""
Tests for JSON Plan Validator - TICKET 004
"""

import json
import unittest

from janus.safety.validation.json_plan_validator import (
    JSONPlanValidator,
    ValidationError,
    validate_json_plan,
    validate_plan,
)


class TestJSONPlanValidator(unittest.TestCase):
    """Test JSON Plan Validator functionality"""

    def setUp(self):
        """Set up test validator"""
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)

    def test_valid_plan_simple(self):
        """Test validation of a simple valid plan"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Chrome"},
                    "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None,
                    },
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsNotNone(result.plan)

    def test_valid_plan_multi_step(self):
        """Test validation of multi-step plan"""
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
                        "record": None,
                    },
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://www.youtube.com"},
                    "context": {
                        "app": "Safari",
                        "surface": "browser",
                        "url": "https://www.youtube.com",
                        "domain": "youtube.com",
                        "thread": None,
                        "record": None,
                    },
                },
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_missing_steps_field(self):
        """Test validation fails when steps field is missing"""
        plan = {"actions": []}  # Wrong field name

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "structure" for e in result.errors))

    def test_empty_steps_array(self):
        """
        Test empty steps array is INVALID
        
        CRITICAL FIX: Empty plans must be rejected, not just warned.
        This prevents executor from attempting to execute nothing.
        """
        plan = {"steps": []}

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid, "Empty plan must be INVALID")
        self.assertTrue(result.has_errors(), "Empty plan must have errors")
        # Check error message mentions "no actionable steps"
        self.assertTrue(
            any("no actionable steps" in err.message.lower() for err in result.errors),
            "Error should mention 'no actionable steps'"
        )

    def test_missing_module_field(self):
        """Test validation fails when module is missing"""
        plan = {
            "steps": [
                {
                    "action": "open_app",  # Missing module
                    "args": {"app_name": "Chrome"},
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "module" for e in result.errors))

    def test_invalid_module_name(self):
        """Test validation fails for invalid module name"""
        plan = {
            "steps": [
                {
                    "module": "invalid_module",
                    "action": "open_app",
                    "args": {},
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "module" for e in result.errors))
        # Should be recoverable (can be auto-corrected)
        self.assertTrue(any(e.recoverable for e in result.errors if e.error_type == "module"))

    def test_missing_action_field(self):
        """Test validation fails when action is missing"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    # Missing action
                    "args": {},
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "action" for e in result.errors))

    def test_invalid_action_for_module(self):
        """Test validation fails for invalid action-module combination"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "invalid_action",
                    "args": {},
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "action" for e in result.errors))

    def test_missing_args_field(self):
        """Test validation fails when args is missing"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    # Missing args
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "args" for e in result.errors))

    def test_missing_context_field_with_allow(self):
        """Test missing context produces warning when allowed"""
        validator = JSONPlanValidator(allow_missing_context=True)
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},  # Required arg provided
                    # Missing context
                }
            ]
        }

        result = validator.validate_plan(plan)
        self.assertTrue(result.is_valid)  # Valid because allow_missing_context=True
        self.assertTrue(result.has_warnings())

    def test_missing_context_field_strict(self):
        """Test missing context produces error in strict mode"""
        validator = JSONPlanValidator(allow_missing_context=False)
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {},
                    # Missing context
                }
            ]
        }

        result = validator.validate_plan(plan)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "context" for e in result.errors))

    def test_incomplete_context_structure(self):
        """Test validation of incomplete V3 context"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://google.com"},
                    "context": {
                        "app": "Chrome",
                        # Missing other fields
                    },
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        # With allow_missing_context=True, this produces warnings
        self.assertTrue(result.is_valid)
        self.assertTrue(result.has_warnings())

    def test_context_propagation_warning(self):
        """Test logical coherence check for context propagation"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_app",
                    "args": {"app_name": "Chrome"},
                    "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None,
                    },
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://google.com"},
                    "context": {
                        "app": None,  # Should be Chrome after previous step
                        "surface": "browser",
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None,
                    },
                },
            ]
        }

        result = self.validator.validate_plan(plan)
        # Valid but should have warnings about context propagation
        self.assertTrue(result.is_valid)
        self.assertTrue(result.has_warnings())
        self.assertTrue(any(e.error_type == "logic" for e in result.warnings))

    def test_validate_json_string_valid(self):
        """Test validation of valid JSON string"""
        json_str = json.dumps(
            {
                "steps": [
                    {
                        "module": "system",
                        "action": "open_application",
                        "args": {"app_name": "Safari"},  # Required arg provided
                        "context": None,
                    }
                ]
            }
        )

        result = self.validator.validate_json_string(json_str)
        self.assertTrue(result.is_valid)

    def test_validate_json_string_invalid(self):
        """Test validation of invalid JSON string"""
        json_str = '{"steps": [{"module": "system"'  # Incomplete JSON

        result = self.validator.validate_json_string(json_str)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.error_type == "parse" for e in result.errors))

    def test_validation_statistics(self):
        """Test that statistics are tracked correctly"""
        validator = JSONPlanValidator()
        
        # Valid plan - use action with no required args (get_active_app)
        valid_plan = {
            "steps": [
                {"module": "system", "action": "get_active_app", "args": {}, "context": None}
            ]
        }
        validator.validate_plan(valid_plan)
        
        # Invalid plan
        invalid_plan = {"actions": []}  # Wrong field name
        validator.validate_plan(invalid_plan)
        
        stats = validator.get_stats()
        self.assertEqual(stats["total_validations"], 2)
        self.assertEqual(stats["valid_plans"], 1)
        self.assertEqual(stats["invalid_plans"], 1)
        self.assertEqual(stats["structure_errors"], 1)

    def test_error_summary(self):
        """Test error summary generation"""
        plan = {
            "steps": [
                {
                    "module": "invalid",
                    "action": "unknown",
                    "args": {},
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        summary = result.get_error_summary()
        
        self.assertIn("error", summary.lower())
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_convenience_functions(self):
        """
        Test convenience functions work correctly
        
        CRITICAL FIX: Empty plans must be rejected.
        """
        # validate_json_plan - empty plan should be invalid
        json_str = '{"steps": []}'
        result = validate_json_plan(json_str)
        self.assertFalse(result.is_valid, "Empty plan must be INVALID")

        # validate_plan - empty plan should be invalid
        plan = {"steps": []}
        result = validate_plan(plan)
        self.assertFalse(result.is_valid, "Empty plan must be INVALID")

    def test_missing_required_args_rejected(self):
        """
        Test that actions with missing required args are REJECTED.
        
        CRITICAL FIX: This prevents executor from crashing on actions like
        'open_application' with empty 'app_name'.
        """
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {},  # Missing required 'app_name'
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid, "Plan with missing required args must be INVALID")
        self.assertTrue(result.has_errors(), "Plan must have errors for missing args")
        # Check error message mentions missing arg
        self.assertTrue(
            any("app_name" in err.message.lower() or "required" in err.message.lower() 
                for err in result.errors),
            "Error should mention missing required arg"
        )

    def test_missing_required_args_open_url(self):
        """Test that open_url with missing 'url' arg is rejected."""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {},  # Missing required 'url'
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid, "open_url with missing 'url' must be INVALID")

    def test_missing_required_args_search(self):
        """Test that search with missing 'query' arg is rejected."""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "search",
                    "args": {},  # Missing required 'query'
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertFalse(result.is_valid, "search with missing 'query' must be INVALID")

    def test_valid_args_accepted(self):
        """Test that actions with valid required args are accepted."""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},  # Required arg provided
                    "context": None,
                }
            ]
        }

        result = self.validator.validate_plan(plan)
        self.assertTrue(result.is_valid, "Plan with valid required args must be VALID")


if __name__ == "__main__":
    unittest.main()
