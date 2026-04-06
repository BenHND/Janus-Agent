"""
Tests for UnifiedActionValidator - SAFETY-001

Tests the unified validation system with single source of truth for risk levels.
"""

import logging
import unittest
from unittest.mock import Mock

from janus.runtime.core.module_action_schema import RiskLevel
from janus.safety.validation.unified_action_validator import (
    UnifiedActionValidator,
    get_global_validator,
    validate_action,
)


class TestUnifiedActionValidator(unittest.TestCase):
    """Test suite for UnifiedActionValidator"""
    
    def test_validator_initialization(self):
        """Test validator initializes with correct defaults"""
        validator = UnifiedActionValidator()
        
        self.assertTrue(validator.auto_correct)
        self.assertTrue(validator.allow_fallback)
        self.assertFalse(validator.strict_mode)
        self.assertIsNotNone(validator.confirmation_callback)
        self.assertGreater(len(validator.dangerous_patterns), 0)
        
    def test_global_validator_singleton(self):
        """Test global validator is a singleton"""
        validator1 = get_global_validator()
        validator2 = get_global_validator()
        
        self.assertIs(validator1, validator2)
        
    def test_valid_low_risk_action(self):
        """Test validation of a valid LOW risk action"""
        validator = UnifiedActionValidator()
        
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_step)
        self.assertIsNone(error)
        self.assertEqual(risk_level, RiskLevel.LOW)
        self.assertTrue(user_confirmed)  # Auto-approved for LOW risk
        
    def test_valid_medium_risk_action(self):
        """Test validation of a valid MEDIUM risk action"""
        validator = UnifiedActionValidator()
        
        step = {
            "module": "ui",
            "action": "click",
            "args": {"target": "Submit button"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_step)
        self.assertIsNone(error)
        self.assertEqual(risk_level, RiskLevel.MEDIUM)
        self.assertTrue(user_confirmed)  # Auto-approved for MEDIUM risk (SAFETY-001)
        
    def test_valid_high_risk_action_requires_confirmation(self):
        """Test HIGH risk action requires confirmation"""
        # Use default callback which denies HIGH risk
        validator = UnifiedActionValidator()
        
        step = {
            "module": "files",
            "action": "delete_file",
            "args": {"path": "/tmp/test.txt"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertFalse(is_valid)  # Denied by default callback
        self.assertIsNone(corrected_step)
        self.assertIn("denied", error.lower())
        self.assertEqual(risk_level, RiskLevel.HIGH)
        self.assertFalse(user_confirmed)
        
    def test_high_risk_action_with_approval(self):
        """Test HIGH risk action with user approval"""
        # Mock confirmation callback that approves
        def mock_approve(step, risk_level, context):
            return True
        
        validator = UnifiedActionValidator(confirmation_callback=mock_approve)
        
        step = {
            "module": "files",
            "action": "delete_file",
            "args": {"path": "/tmp/test.txt"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_step)
        self.assertIsNone(error)
        self.assertEqual(risk_level, RiskLevel.HIGH)
        self.assertTrue(user_confirmed)
        
    def test_critical_action_detected_from_schema(self):
        """Test that we could detect CRITICAL level if defined in schema"""
        # Note: Currently no actions in schema are marked CRITICAL by default
        # This tests the infrastructure is in place
        validator = UnifiedActionValidator()
        
        # Test with HIGH risk (closest to CRITICAL currently in schema)
        step = {
            "module": "messaging",
            "action": "send_message",
            "args": {"message": "Test", "recipient": "user@example.com"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        # Should require confirmation
        self.assertEqual(risk_level, RiskLevel.HIGH)
        self.assertFalse(is_valid)  # Denied by default callback
        
    def test_dangerous_command_detection(self):
        """Test detection of dangerous command patterns"""
        validator = UnifiedActionValidator()
        
        # Test rm -rf pattern
        risk, warning = validator._check_command_safety("rm -rf /")
        self.assertEqual(risk, RiskLevel.CRITICAL)
        self.assertIsNotNone(warning)
        
        # Test sudo rm pattern
        risk, warning = validator._check_command_safety("sudo rm -rf /tmp")
        self.assertEqual(risk, RiskLevel.CRITICAL)
        self.assertIsNotNone(warning)
        
        # Test shutdown command
        risk, warning = validator._check_command_safety("shutdown -h now")
        self.assertEqual(risk, RiskLevel.CRITICAL)
        self.assertIsNotNone(warning)
        
    def test_safe_command_no_elevation(self):
        """Test safe commands are not elevated"""
        validator = UnifiedActionValidator()
        
        risk, warning = validator._check_command_safety("ls -la")
        self.assertIsNone(risk)
        self.assertIsNone(warning)
        
        risk, warning = validator._check_command_safety("echo 'hello'")
        self.assertIsNone(risk)
        self.assertIsNone(warning)
        
    def test_invalid_module_rejected(self):
        """Test invalid module is rejected"""
        validator = UnifiedActionValidator(strict_mode=True)
        
        step = {
            "module": "invalid_module",
            "action": "some_action",
            "args": {}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertFalse(is_valid)
        self.assertIsNone(corrected_step)
        self.assertIsNotNone(error)
        self.assertIn("invalid module", error.lower())
        
    def test_invalid_action_rejected(self):
        """Test invalid action for valid module is rejected"""
        validator = UnifiedActionValidator(strict_mode=True)
        
        step = {
            "module": "browser",
            "action": "invalid_action",
            "args": {}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertFalse(is_valid)
        self.assertIsNone(corrected_step)
        self.assertIsNotNone(error)
        
    def test_auto_correction_of_action_name(self):
        """Test auto-correction of action names using aliases"""
        validator = UnifiedActionValidator(auto_correct=True)
        
        # Use alias instead of canonical name
        step = {
            "module": "browser",
            "action": "navigate",  # Alias for "open_url"
            "args": {"url": "https://example.com"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_step)
        self.assertEqual(corrected_step["action"], "open_url")  # Normalized to canonical
        
    def test_auto_correction_disabled_in_strict_mode(self):
        """Test auto-correction is disabled in strict mode"""
        validator = UnifiedActionValidator(strict_mode=True)
        
        step = {
            "module": "browser",
            "action": "navigate",  # Alias
            "args": {"url": "https://example.com"}
        }
        
        # In strict mode, aliases should still work (they're valid)
        # but invalid names should not be corrected
        is_valid, _, _, _, _ = validator.validate_and_confirm(step)
        self.assertTrue(is_valid)  # Alias is valid
        
    def test_validation_statistics(self):
        """Test validation statistics are tracked"""
        validator = UnifiedActionValidator()
        
        # Valid action
        step1 = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        validator.validate_and_confirm(step1)
        
        # Invalid action
        step2 = {
            "module": "invalid",
            "action": "test",
            "args": {}
        }
        validator.validate_and_confirm(step2)
        
        stats = validator.get_validation_report()
        
        self.assertEqual(stats["total_validations"], 2)
        self.assertGreaterEqual(stats["valid_actions"], 1)
        self.assertGreaterEqual(stats["rejected_actions"], 1)
        
    def test_no_arbitrary_regex_blocking(self):
        """Test that LOW/MEDIUM actions are not blocked by arbitrary patterns"""
        validator = UnifiedActionValidator()
        
        # MEDIUM risk action should not be blocked
        step = {
            "module": "ui",
            "action": "click",
            "args": {"target": "Delete"}  # Contains "delete" keyword but action is MEDIUM
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
        
        # Should be allowed (MEDIUM risk, no confirmation needed per SAFETY-001)
        self.assertTrue(is_valid)
        self.assertTrue(user_confirmed)
        self.assertEqual(risk_level, RiskLevel.MEDIUM)
        
    def test_risk_level_from_ssot_only(self):
        """Test risk level comes from module_action_schema.py only"""
        validator = UnifiedActionValidator()
        
        # Test multiple actions with known risk levels
        test_cases = [
            ("browser", "open_url", RiskLevel.LOW),
            ("ui", "click", RiskLevel.MEDIUM),
            ("files", "delete_file", RiskLevel.HIGH),
            ("messaging", "send_message", RiskLevel.HIGH),
        ]
        
        for module, action, expected_risk in test_cases:
            step = {"module": module, "action": action, "args": {}}
            risk_level = validator._get_risk_level(step)
            self.assertEqual(risk_level, expected_risk, 
                           f"{module}.{action} should be {expected_risk}")
            
    def test_logging_of_validation_decision(self):
        """Test that validation decisions are logged"""
        with self.assertLogs(level=logging.INFO) as log_context:
            validator = UnifiedActionValidator()
            
            step = {
                "module": "browser",
                "action": "open_url",
                "args": {"url": "https://example.com"}
            }
            
            validator.validate_and_confirm(step)
            
            # Check logs contain key information
            log_text = '\n'.join(log_context.output)
            self.assertIn("risk_level", log_text)
            self.assertIn("requires_confirmation", log_text)
        
    def test_confirmation_callback_receives_correct_params(self):
        """Test confirmation callback receives correct parameters"""
        received_params = {}
        
        def mock_callback(step, risk_level, context):
            received_params["step"] = step
            received_params["risk_level"] = risk_level
            received_params["context"] = context
            return True
        
        validator = UnifiedActionValidator(confirmation_callback=mock_callback)
        
        step = {
            "module": "files",
            "action": "delete_file",
            "args": {"path": "/tmp/test.txt"}
        }
        context = {"user": "test_user"}
        
        validator.validate_and_confirm(step, context)
        
        self.assertIsNotNone(received_params["step"])
        self.assertEqual(received_params["risk_level"], RiskLevel.HIGH)
        self.assertEqual(received_params["context"], context)
        
    def test_convenience_function_validate_action(self):
        """Test convenience function works"""
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        
        is_valid, corrected_step, error, risk_level, user_confirmed = validate_action(step)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(corrected_step)
        self.assertEqual(risk_level, RiskLevel.LOW)
        
    def test_reset_statistics(self):
        """Test statistics can be reset"""
        validator = UnifiedActionValidator()
        
        # Do some validations
        step = {"module": "browser", "action": "open_url", "args": {"url": "https://example.com"}}
        validator.validate_and_confirm(step)
        
        self.assertGreater(validator.stats["total_validations"], 0)
        
        # Reset
        validator.reset_stats()
        
        self.assertEqual(validator.stats["total_validations"], 0)
        self.assertEqual(validator.stats["valid_actions"], 0)


class TestRiskLevelEnforcement(unittest.TestCase):
    """Test that risk levels are enforced according to SAFETY-001 requirements"""
    
    def test_high_and_critical_require_confirmation(self):
        """Test HIGH and CRITICAL actions ALWAYS require confirmation"""
        validator = UnifiedActionValidator()
        
        # HIGH risk
        step_high = {
            "module": "files",
            "action": "delete_file",
            "args": {"path": "/tmp/test.txt"}
        }
        
        risk_level = validator._get_risk_level(step_high)
        requires_conf = validator._requires_confirmation(step_high, risk_level, None)
        
        self.assertEqual(risk_level, RiskLevel.HIGH)
        self.assertTrue(requires_conf)
        
    def test_low_and_medium_no_confirmation(self):
        """Test LOW and MEDIUM actions do NOT require confirmation"""
        validator = UnifiedActionValidator()
        
        # LOW risk
        step_low = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        
        risk_level = validator._get_risk_level(step_low)
        requires_conf = validator._requires_confirmation(step_low, risk_level, None)
        
        self.assertEqual(risk_level, RiskLevel.LOW)
        self.assertFalse(requires_conf)
        
        # MEDIUM risk
        step_medium = {
            "module": "ui",
            "action": "click",
            "args": {"target": "button"}
        }
        
        risk_level = validator._get_risk_level(step_medium)
        requires_conf = validator._requires_confirmation(step_medium, risk_level, None)
        
        self.assertEqual(risk_level, RiskLevel.MEDIUM)
        self.assertFalse(requires_conf)
        
    def test_no_arbitrary_blocking_of_low_medium(self):
        """Test LOW/MEDIUM actions are not blocked by arbitrary rules"""
        validator = UnifiedActionValidator()
        
        # Test various LOW/MEDIUM actions that should NOT be blocked
        test_cases = [
            {"module": "browser", "action": "open_url", "args": {"url": "https://example.com"}},
            {"module": "browser", "action": "refresh", "args": {}},
            {"module": "ui", "action": "copy", "args": {}},
            {"module": "ui", "action": "paste", "args": {}},
            {"module": "system", "action": "get_active_app", "args": {}},
        ]
        
        for step in test_cases:
            is_valid, _, error, risk_level, user_confirmed = validator.validate_and_confirm(step)
            
            # All should be valid and auto-approved
            self.assertTrue(is_valid, 
                          f"Action {step['module']}.{step['action']} should be valid")
            self.assertTrue(user_confirmed, 
                          f"Action {step['module']}.{step['action']} should be auto-approved")
            self.assertIn(risk_level, [RiskLevel.LOW, RiskLevel.MEDIUM])


if __name__ == '__main__':
    unittest.main()
