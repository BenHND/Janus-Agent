"""
Tests for Action Validator module
"""
import unittest

from janus.safety.validation.action_validator import ActionRisk, ActionValidator, ValidationResult


class TestActionValidator(unittest.TestCase):
    """Test Action Validator functionality"""

    def setUp(self):
        """Set up test action validator"""
        self.validator = ActionValidator(auto_confirm_safe=True)

    def test_safe_action(self):
        """Test validation of safe action"""
        action = {"action": "open_application", "app_name": "Chrome"}
        result = self.validator.validate_action(action)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.SAFE)
        self.assertFalse(result.requires_confirmation)

    def test_low_risk_action(self):
        """Test validation of low risk action"""
        action = {"action": "click", "target": "button"}
        result = self.validator.validate_action(action)
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.LOW)

    def test_medium_risk_action(self):
        """Test validation of medium risk action"""
        action = {"action": "execute_command", "command": "ls -la"}
        result = self.validator.validate_action(action)
        # Medium risk with default callback should be allowed
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.MEDIUM)

    def test_high_risk_action(self):
        """Test validation of high risk action"""
        action = {"action": "delete_file", "file": "test.txt"}
        result = self.validator.validate_action(action)
        # High risk with default callback should be denied
        self.assertFalse(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.HIGH)
        self.assertTrue(result.requires_confirmation)

    def test_critical_action(self):
        """Test validation of critical action"""
        action = {"action": "shutdown"}
        result = self.validator.validate_action(action)
        self.assertFalse(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.CRITICAL)
        self.assertTrue(result.requires_confirmation)

    def test_dangerous_command_rm_rf(self):
        """Test detection of dangerous rm -rf command"""
        action = {"action": "execute_command", "command": "rm -rf /"}
        result = self.validator.validate_action(action)
        self.assertFalse(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.CRITICAL)
        self.assertIsNotNone(result.warning_message)

    def test_dangerous_command_fork_bomb(self):
        """Test detection of fork bomb"""
        action = {"action": "execute_command", "command": ":(){:|:&};:"}
        result = self.validator.validate_action(action)
        self.assertFalse(result.allowed)
        self.assertEqual(result.risk_level, ActionRisk.CRITICAL)

    def test_dangerous_command_sudo(self):
        """Test detection of sudo command"""
        action = {"action": "execute_command", "command": "sudo rm file.txt"}
        result = self.validator.validate_action(action)
        self.assertFalse(result.allowed)
        # Sudo rm is caught by both sudo pattern AND dangerous pattern, making it CRITICAL
        self.assertEqual(result.risk_level, ActionRisk.CRITICAL)

    def test_safe_command(self):
        """Test safe command validation"""
        action = {"action": "execute_command", "command": "echo hello"}
        result = self.validator.validate_action(action)
        self.assertTrue(result.allowed)

    def test_validate_action_plan(self):
        """Test validation of multiple actions"""
        actions = [
            {"action": "open_application", "app_name": "Chrome"},
            {"action": "click"},
            {"action": "copy"},
        ]
        results = self.validator.validate_action_plan(actions)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.allowed for r in results))

    def test_validate_action_plan_stops_on_deny(self):
        """Test that validation stops when action is denied"""
        actions = [
            {"action": "open_application", "app_name": "Chrome"},
            {"action": "shutdown"},  # This should be denied
            {"action": "click"},  # This should not be validated
        ]
        results = self.validator.validate_action_plan(actions)
        # Should stop at the dangerous action
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].allowed)
        self.assertFalse(results[1].allowed)

    def test_custom_confirmation_callback(self):
        """Test custom confirmation callback"""

        def always_allow(action, risk, context):
            return True

        validator = ActionValidator(confirmation_callback=always_allow)
        action = {"action": "delete_file", "file": "test.txt"}
        result = validator.validate_action(action)
        # With custom callback that always allows, should be allowed
        self.assertTrue(result.allowed)

    def test_classify_action(self):
        """Test action classification"""
        self.assertEqual(self.validator.classify_action("open_url"), ActionRisk.SAFE)
        self.assertEqual(self.validator.classify_action("execute_command"), ActionRisk.MEDIUM)
        self.assertEqual(self.validator.classify_action("delete_file"), ActionRisk.HIGH)
        self.assertEqual(self.validator.classify_action("shutdown"), ActionRisk.CRITICAL)
        self.assertEqual(self.validator.classify_action("unknown_action"), ActionRisk.MEDIUM)

    def test_recommendation_messages(self):
        """Test recommendation message generation"""
        action_safe = {"action": "open_url", "url": "google.com"}
        result_safe = self.validator.validate_action(action_safe)
        self.assertIsNone(result_safe.recommendation)

        action_high = {"action": "delete_file", "file": "test.txt"}
        result_high = self.validator.validate_action(action_high)
        self.assertIsNotNone(result_high.recommendation)
        self.assertIn("HIGH RISK", result_high.recommendation)


if __name__ == "__main__":
    unittest.main()
