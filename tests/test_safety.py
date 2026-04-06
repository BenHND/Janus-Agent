"""
Unit tests for Safety Manager
"""
import unittest

from janus.exec.safety import ActionRiskLevel, ActionWhitelist, DangerousActions, SafetyManager


class TestSafetyManager(unittest.TestCase):
    """Test cases for SafetyManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.safety_manager = SafetyManager(require_confirmation=True)

    def test_initialization(self):
        """Test safety manager initialization"""
        self.assertTrue(self.safety_manager.require_confirmation)
        self.assertGreater(len(self.safety_manager.whitelist), 0)
        self.assertGreater(len(self.safety_manager.dangerous_actions), 0)

    def test_whitelisted_action_allowed(self):
        """Test that whitelisted actions are allowed"""
        is_safe, reason = self.safety_manager.check_action("open_app", {"app_name": "Chrome"})

        self.assertTrue(is_safe)
        self.assertIsNone(reason)

    def test_dangerous_action_blocked_without_confirmation(self):
        """Test that dangerous actions are blocked without confirmation"""
        is_safe, reason = self.safety_manager.check_action("delete_file", {"path": "/test.txt"})

        self.assertFalse(is_safe)
        self.assertIn("confirmation", reason.lower())

    def test_dangerous_action_allowed_with_confirmation_callback(self):
        """Test dangerous action allowed with confirmation callback"""

        def confirm_callback(action, params):
            return True  # User confirms

        safety_manager = SafetyManager(
            require_confirmation=True,
            confirmation_callback=confirm_callback,
        )

        is_safe, reason = safety_manager.check_action("delete_file", {"path": "/test.txt"})

        self.assertTrue(is_safe)
        self.assertIsNone(reason)

    def test_dangerous_action_blocked_with_declined_confirmation(self):
        """Test dangerous action blocked when user declines"""

        def decline_callback(action, params):
            return False  # User declines

        safety_manager = SafetyManager(
            require_confirmation=True,
            confirmation_callback=decline_callback,
        )

        is_safe, reason = safety_manager.check_action("delete_file", {"path": "/test.txt"})

        self.assertFalse(is_safe)
        self.assertIn("declined", reason.lower())

    def test_dangerous_action_allowed_without_require_confirmation(self):
        """Test dangerous action allowed when confirmation not required"""
        safety_manager = SafetyManager(require_confirmation=False)

        is_safe, reason = safety_manager.check_action("delete_file", {"path": "/test.txt"})

        self.assertTrue(is_safe)
        self.assertIsNone(reason)

    def test_unknown_action_allowed_with_warning(self):
        """Test that unknown actions are allowed with moderate risk"""
        is_safe, reason = self.safety_manager.check_action("unknown_action", {})

        self.assertTrue(is_safe)
        self.assertIsNone(reason)

    def test_app_whitelist_restriction(self):
        """Test app whitelist restriction"""
        safety_manager = SafetyManager(allowed_apps={"Chrome", "VSCode"})

        # Allowed app
        is_safe, reason = safety_manager.check_action("open_app", {"app": "Chrome"})
        self.assertTrue(is_safe)

        # Not allowed app
        is_safe, reason = safety_manager.check_action("open_app", {"app": "Firefox"})
        self.assertFalse(is_safe)
        self.assertIn("not in allowed list", reason)

    def test_app_blacklist(self):
        """Test app blacklist"""
        safety_manager = SafetyManager(blocked_apps={"malicious_app"})

        # Not blocked app
        is_safe, reason = safety_manager.check_action("open_app", {"app": "Chrome"})
        self.assertTrue(is_safe)

        # Blocked app
        is_safe, reason = safety_manager.check_action("open_app", {"app": "malicious_app"})
        self.assertFalse(is_safe)
        self.assertIn("blocked", reason)

    def test_assess_risk_level(self):
        """Test risk level assessment"""
        # Safe action
        risk = self.safety_manager.assess_risk_level("open_app")
        self.assertEqual(risk, ActionRiskLevel.SAFE)

        # Dangerous action
        risk = self.safety_manager.assess_risk_level("delete_file")
        self.assertEqual(risk, ActionRiskLevel.DANGEROUS)

        # Unknown action
        risk = self.safety_manager.assess_risk_level("unknown_action")
        self.assertEqual(risk, ActionRiskLevel.MODERATE)

    def test_add_to_whitelist(self):
        """Test adding action to whitelist"""
        self.safety_manager.add_to_whitelist("custom_action")

        self.assertIn("custom_action", self.safety_manager.whitelist)

        # Should be allowed now
        is_safe, reason = self.safety_manager.check_action("custom_action", {})
        self.assertTrue(is_safe)

    def test_remove_from_whitelist(self):
        """Test removing action from whitelist"""
        self.safety_manager.remove_from_whitelist("open_app")

        self.assertNotIn("open_app", self.safety_manager.whitelist)

    def test_add_to_dangerous(self):
        """Test adding action to dangerous list"""
        self.safety_manager.add_to_dangerous("sensitive_action")

        self.assertIn("sensitive_action", self.safety_manager.dangerous_actions)

        # Should require confirmation now
        is_safe, reason = self.safety_manager.check_action("sensitive_action", {})
        self.assertFalse(is_safe)

    def test_remove_from_dangerous(self):
        """Test removing action from dangerous list"""
        self.safety_manager.remove_from_dangerous("delete_file")

        self.assertNotIn("delete_file", self.safety_manager.dangerous_actions)

    def test_block_app(self):
        """Test blocking an app"""
        self.safety_manager.block_app("bad_app")

        self.assertIn("bad_app", self.safety_manager.blocked_apps)

        # Should be blocked
        is_safe, reason = self.safety_manager.check_action("open_app", {"app": "bad_app"})
        self.assertFalse(is_safe)

    def test_unblock_app(self):
        """Test unblocking an app"""
        self.safety_manager.block_app("test_app")
        self.safety_manager.unblock_app("test_app")

        self.assertNotIn("test_app", self.safety_manager.blocked_apps)

    def test_get_statistics(self):
        """Test getting statistics"""
        stats = self.safety_manager.get_statistics()

        self.assertIn("whitelist_count", stats)
        self.assertIn("dangerous_count", stats)
        self.assertIn("blocked_apps_count", stats)
        self.assertIn("require_confirmation", stats)

        self.assertGreater(stats["whitelist_count"], 0)
        self.assertGreater(stats["dangerous_count"], 0)
        self.assertTrue(stats["require_confirmation"])

    def test_custom_whitelist_and_dangerous_sets(self):
        """Test initialization with custom sets"""
        custom_whitelist = {"action1", "action2"}
        custom_dangerous = {"action3", "action4"}

        safety_manager = SafetyManager(
            whitelist=custom_whitelist,
            dangerous_actions=custom_dangerous,
        )

        self.assertEqual(safety_manager.whitelist, custom_whitelist)
        self.assertEqual(safety_manager.dangerous_actions, custom_dangerous)


if __name__ == "__main__":
    unittest.main()
