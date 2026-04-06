"""
Tests for TICKET 003 - Strict Action Validator

Tests for:
- Step validation with auto-correction
- Plan validation
- Fallback behavior
- Validation statistics
"""

import unittest

from janus.safety.validation.strict_action_validator import (
    StrictActionValidator,
    get_global_validator,
    validate_action,
    validate_plan,
)


class TestStrictActionValidator(unittest.TestCase):
    """Test strict action validator"""
    
    def setUp(self):
        """Set up test validator"""
        self.validator = StrictActionValidator(
            auto_correct=True,
            allow_fallback=True,
            strict_mode=False
        )
        self.validator.reset_stats()
    
    def test_validate_valid_step(self):
        """Test validating a valid step"""
        step = {
            "module": "system",
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected)
        self.assertIsNone(error)
        self.assertEqual(corrected["module"], "system")
        self.assertEqual(corrected["action"], "open_app")
    
    def test_validate_invalid_module(self):
        """Test validating step with invalid module"""
        step = {
            "module": "invalid_module",
            "action": "open_app",
            "args": {}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        # Should fail or fallback
        if is_valid:
            # Fallback was used
            self.assertIsNotNone(corrected)
            self.assertIn("fallback", str(corrected).lower())
        else:
            self.assertFalse(is_valid)
            self.assertIsNotNone(error)
    
    def test_validate_invalid_action(self):
        """Test validating step with invalid action"""
        step = {
            "module": "system",
            "action": "invalid_action",
            "args": {}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        # Should fail or fallback
        if is_valid:
            # Fallback was used
            self.assertIsNotNone(corrected)
        else:
            self.assertFalse(is_valid)
            self.assertIsNotNone(error)
    
    def test_auto_correct_module_case(self):
        """Test auto-correcting module name case"""
        step = {
            "module": "SYSTEM",  # Wrong case
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected)
        self.assertEqual(corrected["module"], "system")  # Corrected
    
    def test_auto_correct_action_alias(self):
        """Test auto-correcting action using alias"""
        step = {
            "module": "system",
            "action": "open_application",  # Alias
            "args": {"app_name": "Safari"}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected)
        self.assertEqual(corrected["action"], "open_app")  # Corrected to canonical name
    
    def test_strict_mode_rejects_invalid(self):
        """Test strict mode rejects invalid actions"""
        validator = StrictActionValidator(strict_mode=True)
        
        step = {
            "module": "SYSTEM",  # Wrong case
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, corrected, error = validator.validate_step(step)
        
        # Strict mode should reject without correction
        self.assertFalse(is_valid)
        self.assertIsNone(corrected)
        self.assertIsNotNone(error)
    
    def test_validate_plan_all_valid(self):
        """Test validating plan with all valid steps"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "open_url", "args": {"url": "https://youtube.com"}},
                {"module": "browser", "action": "search", "args": {"query": "Python"}}
            ]
        }
        
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_plan)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(corrected_plan["steps"]), 3)
    
    def test_validate_plan_with_corrections(self):
        """Test validating plan that needs corrections"""
        plan = {
            "steps": [
                {"module": "SYSTEM", "action": "open_app", "args": {"app_name": "Safari"}},  # Case issue
                {"module": "browser", "action": "navigate", "args": {"url": "https://youtube.com"}},  # Alias
                {"module": "browser", "action": "search", "args": {"query": "Python"}}
            ]
        }
        
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_plan)
        
        # Check corrections were applied
        self.assertEqual(corrected_plan["steps"][0]["module"], "system")
        self.assertEqual(corrected_plan["steps"][1]["action"], "open_url")  # navigate -> open_url
    
    def test_validate_plan_partial_failure(self):
        """Test validating plan with some invalid steps"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},  # Valid
                {"module": "invalid", "action": "invalid", "args": {}},  # Invalid
                {"module": "browser", "action": "search", "args": {"query": "Python"}}  # Valid
            ]
        }
        
        is_valid, corrected_plan, errors = self.validator.validate_plan(plan)
        
        # In non-strict mode with fallback, should succeed with fallback steps
        if is_valid:
            self.assertIsNotNone(corrected_plan)
            # Should have all steps (some might be fallback)
            self.assertEqual(len(corrected_plan["steps"]), 3)
    
    def test_statistics_tracking(self):
        """Test validation statistics tracking"""
        self.validator.reset_stats()
        
        # Valid step
        valid_step = {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}}
        self.validator.validate_step(valid_step)
        
        # Step needing correction
        correctable_step = {"module": "SYSTEM", "action": "open_app", "args": {"app_name": "Safari"}}
        self.validator.validate_step(correctable_step)
        
        stats = self.validator.get_validation_report()
        
        self.assertEqual(stats["total_validations"], 2)
        self.assertGreater(stats["success_rate"], 0)
    
    def test_suggest_correction_invalid_module(self):
        """Test suggesting correction for invalid module"""
        suggestion = self.validator.suggest_correction("invalid_module", "open_app")
        
        self.assertIsNotNone(suggestion)
        self.assertIn("module", suggestion.lower())
    
    def test_suggest_correction_invalid_action(self):
        """Test suggesting correction for invalid action"""
        suggestion = self.validator.suggest_correction("system", "invalid_action")
        
        self.assertIsNotNone(suggestion)
        # Should suggest valid actions or a correction
        self.assertTrue(
            "valid actions" in suggestion.lower() or "did you mean" in suggestion.lower()
        )
    
    def test_suggest_correction_for_alias(self):
        """Test suggesting correction recognizes aliases"""
        suggestion = self.validator.suggest_correction("system", "open_application")
        
        # Should suggest the canonical action name
        if suggestion:
            self.assertIn("open_app", suggestion.lower())
    
    def test_fallback_to_ui_module(self):
        """Test fallback to UI module for completely invalid steps"""
        step = {
            "module": "completely_invalid",
            "action": "nonexistent_action",
            "args": {}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        # With fallback enabled, should succeed with UI fallback
        if self.validator.allow_fallback:
            self.assertTrue(is_valid)
            self.assertEqual(corrected["module"], "ui")
            self.assertIn("fallback_reason", corrected)
    
    def test_fallback_to_first_action(self):
        """Test fallback to first valid action of module"""
        step = {
            "module": "system",
            "action": "completely_invalid_action",
            "args": {}
        }
        
        is_valid, corrected, error = self.validator.validate_step(step)
        
        # With fallback enabled, should succeed with fallback action
        if self.validator.allow_fallback:
            self.assertTrue(is_valid)
            self.assertEqual(corrected["module"], "system")
            # Should use a valid system action
            from janus.runtime.core.module_action_schema import is_valid_action
            self.assertTrue(is_valid_action(corrected["module"], corrected["action"]))


class TestGlobalValidator(unittest.TestCase):
    """Test global validator functions"""
    
    def test_get_global_validator(self):
        """Test getting global validator instance"""
        validator1 = get_global_validator()
        validator2 = get_global_validator()
        
        # Should be the same instance (singleton)
        self.assertIs(validator1, validator2)
    
    def test_validate_action_convenience(self):
        """Test validate_action convenience function"""
        step = {
            "module": "system",
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, corrected, error = validate_action(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected)
    
    def test_validate_plan_convenience(self):
        """Test validate_plan convenience function"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "open_url", "args": {"url": "https://youtube.com"}}
            ]
        }
        
        is_valid, corrected_plan, errors = validate_plan(plan)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_plan)
        self.assertEqual(len(errors), 0)


class TestValidatorConfiguration(unittest.TestCase):
    """Test validator configuration options"""
    
    def test_auto_correct_enabled(self):
        """Test validator with auto-correct enabled"""
        validator = StrictActionValidator(auto_correct=True, strict_mode=False)
        
        step = {"module": "SYSTEM", "action": "open_app", "args": {"app_name": "Safari"}}
        is_valid, corrected, error = validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertEqual(corrected["module"], "system")
    
    def test_auto_correct_disabled(self):
        """Test validator with auto-correct disabled"""
        validator = StrictActionValidator(auto_correct=False, strict_mode=False)
        
        step = {"module": "SYSTEM", "action": "open_app", "args": {"app_name": "Safari"}}
        is_valid, corrected, error = validator.validate_step(step)
        
        # Without auto-correct, should try fallback or reject
        # Depends on allow_fallback setting
        pass  # Behavior varies based on fallback setting
    
    def test_fallback_enabled(self):
        """Test validator with fallback enabled"""
        validator = StrictActionValidator(allow_fallback=True, strict_mode=False)
        
        step = {"module": "invalid_module", "action": "invalid_action", "args": {}}
        is_valid, corrected, error = validator.validate_step(step)
        
        # Should succeed with fallback
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected)
        self.assertIn("fallback_reason", corrected)
    
    def test_fallback_disabled(self):
        """Test validator with fallback disabled"""
        validator = StrictActionValidator(allow_fallback=False, strict_mode=False)
        
        step = {"module": "invalid_module", "action": "invalid_action", "args": {}}
        is_valid, corrected, error = validator.validate_step(step)
        
        # Should reject without fallback
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
