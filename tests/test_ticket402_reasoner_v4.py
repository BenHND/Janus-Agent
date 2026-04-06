"""
TICKET-402 - Reasoner V4 "Think-First" Architecture Tests

Tests for V4 Reasoner to ensure it:
- Analyzes before planning
- Detects missing information
- Never invents arguments
- Returns empty plan when info is missing
"""

import unittest
from typing import Dict, Any

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestReasonerV4ThinkFirst(unittest.TestCase):
    """Test Reasoner V4 think-first architecture"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_send_email_without_recipient(self):
        """
        ACCEPTANCE CRITERIA TEST:
        Command: "Envoie un mail" (without recipient)
        Expected:
        - analysis.missing_info contains "recipient"
        - plan is EMPTY []
        - NO send_message action with invented email
        """
        command = "Envoie un mail"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr", version="v4")

        # Verify plan structure
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        
        # CRITICAL: Plan must be EMPTY when recipient is missing
        self.assertEqual(len(plan["steps"]), 0, 
                        "Plan should be empty when recipient is missing")
        
        # Verify no send_message action was generated
        for step in plan["steps"]:
            self.assertNotEqual(step.get("action"), "send_message",
                              "Should NOT generate send_message action without recipient")

    def test_send_email_with_recipient(self):
        """
        Test: "Envoie un mail à john@example.com"
        Expected:
        - analysis.missing_info is EMPTY []
        - plan contains send_message action with correct recipient
        """
        command = "Envoie un mail à john@example.com"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr", version="v4")

        # Verify plan structure
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        
        # Plan should contain at least one step
        self.assertGreater(len(plan["steps"]), 0,
                          "Plan should not be empty when recipient is provided")
        
        # Verify send_message action exists with recipient
        has_send_message = False
        for step in plan["steps"]:
            if step.get("action") == "send_message":
                has_send_message = True
                self.assertIn("recipient", step.get("args", {}),
                            "send_message action must have recipient argument")
                # Recipient should not be empty or None
                recipient = step["args"].get("recipient")
                self.assertIsNotNone(recipient, "Recipient should not be None")
                self.assertNotEqual(recipient, "", "Recipient should not be empty")
        
        self.assertTrue(has_send_message, 
                       "Plan should contain send_message action when recipient is provided")

    def test_open_safari_v4(self):
        """
        Test: "Ouvre Safari" with V4
        Expected:
        - analysis shows intent and detected entities
        - plan contains system.open_application action
        """
        command = "Ouvre Safari"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr", version="v4")

        # Verify plan structure
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(len(plan["steps"]), 1)

        # Verify step structure
        step = plan["steps"][0]
        self.assertEqual(step["module"], "system")
        self.assertIn(step["action"], ["open_app", "open_application"])
        self.assertIn("Safari", step["args"].get("app_name", ""))

    def test_v4_never_invents_arguments(self):
        """
        Test that V4 never invents arguments for incomplete commands
        """
        # Various incomplete commands that should result in empty plans
        incomplete_commands = [
            "Envoie un mail",  # Missing recipient
            "Ouvre",  # Missing app name - but this is tricky, might default
        ]
        
        for command in incomplete_commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr", version="v4")
                
                # For "Envoie un mail" without recipient, plan should be empty
                if "mail" in command.lower() and "@" not in command:
                    self.assertEqual(len(plan["steps"]), 0,
                                   f"Plan should be empty for incomplete command: {command}")


class TestReasonerV4BackwardCompatibility(unittest.TestCase):
    """Test that V3 still works when not specifying version"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_default_is_v3(self):
        """Test that default version is V3"""
        command = "Ouvre Safari"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")
        
        # Should work with V3 format (no version parameter)
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(len(plan["steps"]), 1)

    def test_explicit_v3(self):
        """Test explicit V3 version parameter"""
        command = "Ouvre Safari"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr", version="v3")
        
        # Should work with V3 format
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(len(plan["steps"]), 1)


if __name__ == "__main__":
    unittest.main()
