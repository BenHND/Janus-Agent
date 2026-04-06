"""
ARCH-003: Tests to ensure legacy JSONPlanCorrector is completely removed

These tests verify that:
1. ValidatorAgent no longer accepts auto_correct parameter
2. ValidatorAgent performs strict JSON validation only
3. Invalid JSON triggers validation errors (not silent correction)
4. No legacy correction code exists in the validator
"""
import unittest

from janus.capabilities.agents.validator_agent import ValidatorAgent, get_global_validator


# Test constants
VALID_PLAN = {
    "steps": [
        {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "test.com"},
            "context": None
        }
    ]
}

MALFORMED_JSON_UNQUOTED_KEYS = '{ "steps": [ { module: "browser", action: "open_url" } ] }'


class TestARCH003LegacyRemoved(unittest.TestCase):
    """Test that legacy JSONPlanCorrector code is completely removed"""
    
    def test_validator_agent_no_auto_correct_param(self):
        """Test: ValidatorAgent no longer has auto_correct parameter"""
        validator = ValidatorAgent()
        
        # Should not have auto_correct attribute
        self.assertFalse(hasattr(validator, 'auto_correct'))
        self.assertFalse(hasattr(validator, 'corrector'))
    
    def test_validator_agent_strict_validation_only(self):
        """Test: ValidatorAgent performs strict validation only"""
        validator = ValidatorAgent()
        
        # Stats should not have legacy tracking
        stats = validator.get_stats()
        self.assertNotIn('legacy_mode_invocations', stats)
        self.assertNotIn('legacy_mode_usage_rate', stats)
        self.assertNotIn('corrected_plans', stats)
    
    def test_global_validator_strict_mode(self):
        """Test: get_global_validator() creates strict validator"""
        # Reset global validator
        import janus.agents.validator_agent as val_module
        val_module._global_validator = None
        
        # Get global validator
        validator = get_global_validator()
        
        # Should NOT have auto_correct or corrector
        self.assertFalse(hasattr(validator, 'auto_correct'))
        self.assertFalse(hasattr(validator, 'corrector'))
    
    def test_invalid_json_rejected_strict(self):
        """Test: Invalid JSON is rejected (not corrected) in strict mode"""
        validator = ValidatorAgent()
        
        # Malformed JSON
        malformed_json = MALFORMED_JSON_UNQUOTED_KEYS
        
        # Should reject without correction
        result = validator.validate(malformed_json)
        
        self.assertFalse(result["valid"])
        self.assertTrue(len(result["errors"]) > 0)
        # Should be JSON parse error
        self.assertTrue(any("JSON parse error" in err for err in result["errors"]))
    
    def test_valid_plan_accepted(self):
        """Test: Valid plan is accepted"""
        validator = ValidatorAgent()
        
        # Valid plan
        result = validator.validate(VALID_PLAN)
        
        # Should be valid
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
    
    def test_stats_no_legacy_fields(self):
        """Test: Stats don't include legacy fields"""
        validator = ValidatorAgent()
        
        # Validate something to generate stats
        validator.validate(VALID_PLAN)
        
        # Get stats
        stats = validator.get_stats()
        
        # Should have basic stats
        self.assertIn("total_validations", stats)
        self.assertIn("valid_plans", stats)
        self.assertIn("rejected_plans", stats)
        self.assertIn("success_rate", stats)
        
        # Should NOT have legacy stats
        self.assertNotIn("legacy_mode_invocations", stats)
        self.assertNotIn("legacy_mode_usage_rate", stats)
        self.assertNotIn("corrected_plans", stats)
        self.assertNotIn("correction_rate", stats)


if __name__ == "__main__":
    unittest.main()
