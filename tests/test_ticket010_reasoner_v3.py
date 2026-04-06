"""
TICKET 010 - Comprehensive Reasoner V3 Tests

Tests for Reasoner V3 to ensure it always generates valid JSON V3 with:
- Correct module and action mappings
- Proper context propagation
- No invented actions
- Strict adherence to module_action_schema.py

Test Categories:
1. Simple intents (single action)
2. Multi-step commands (compound actions)
3. Cross-app workflows
4. Domain-specific tests (CRM, Messaging, Code, Files)
5. Error handling (empty, impossible, ambiguous)
6. JSON format validation
"""

import unittest
from typing import Dict, Any

from janus.runtime.core.module_action_schema import (
    get_all_module_names,
    get_all_actions_for_module,
    is_valid_module,
    is_valid_action,
    validate_action_step,
)
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestReasonerV3SimpleIntents(unittest.TestCase):
    """Test Reasoner V3 with simple single-action commands"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_open_safari(self):
        """Test: 'ouvre Safari'"""
        command = "ouvre Safari"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Verify plan structure
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(len(plan["steps"]), 1)

        # Verify step structure
        step = plan["steps"][0]
        self.assertIn("module", step)
        self.assertIn("action", step)
        self.assertIn("args", step)
        self.assertIn("context", step)

        # Verify correct module and action
        self.assertEqual(step["module"], "system")
        self.assertIn(step["action"], ["open_app", "open_application"])
        self.assertIn("Safari", step["args"].get("app_name", ""))

        # Verify JSON is valid according to schema
        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid, f"Invalid step: {error}")

    def test_open_chrome(self):
        """Test: 'ouvre Chrome'"""
        command = "ouvre Chrome"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan["steps"]), 1)

        step = plan["steps"][0]
        self.assertEqual(step["module"], "system")
        self.assertIn("Chrome", step["args"].get("app_name", ""))

        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid, f"Invalid step: {error}")

    def test_go_to_youtube(self):
        """Test: 'va sur YouTube'"""
        command = "va sur YouTube"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan["steps"]), 1)

        step = plan["steps"][0]
        self.assertEqual(step["module"], "browser")
        self.assertEqual(step["action"], "open_url")
        self.assertIn("youtube", step["args"].get("url", "").lower())

        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid, f"Invalid step: {error}")

    def test_search_python_tutorials(self):
        """Test: 'cherche Python tutoriels'"""
        command = "cherche Python tutoriels"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan["steps"]), 1)

        step = plan["steps"][0]
        self.assertEqual(step["module"], "browser")
        self.assertEqual(step["action"], "search")
        self.assertIn("Python", step["args"].get("query", ""))

        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid, f"Invalid step: {error}")


class TestReasonerV3MultiStep(unittest.TestCase):
    """Test Reasoner V3 with multi-step compound commands"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_safari_youtube_search(self):
        """Test: 'Ouvre Safari, va sur YouTube et cherche Burial Forgive'"""
        command = "Ouvre Safari, va sur YouTube et cherche Burial Forgive"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Should have 3 steps
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(len(plan["steps"]), 3)

        # Step 1: Open Safari
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertIn(step1["action"], ["open_app", "open_application"])
        self.assertIn("Safari", step1["args"].get("app_name", ""))
        is_valid, _ = validate_action_step(step1)
        self.assertTrue(is_valid)

        # Step 2: Go to YouTube
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["action"], "open_url")
        self.assertIn("youtube", step2["args"].get("url", "").lower())
        is_valid, _ = validate_action_step(step2)
        self.assertTrue(is_valid)

        # Step 3: Search
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3["action"], "search")
        self.assertIn("Burial", step3["args"].get("query", ""))
        is_valid, _ = validate_action_step(step3)
        self.assertTrue(is_valid)

        # Verify context propagation
        # Step 2 should have app: Safari in context
        self.assertEqual(step2.get("context", {}).get("app"), "Safari")
        # Step 3 should have app: Safari and url/domain in context
        self.assertEqual(step3.get("context", {}).get("app"), "Safari")

    def test_chrome_google_search_restaurants(self):
        """Test: 'Ouvre Chrome, va sur Google, cherche restaurants japonais et ouvre le premier résultat'"""
        command = "Ouvre Chrome, va sur Google, cherche restaurants japonais et ouvre le premier résultat"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Should have 4 steps
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 3)  # At least 3 steps

        # Step 1: Open Chrome
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertIn("Chrome", step1["args"].get("app_name", ""))

        # Step 2: Go to Google or search
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertIn(step2["action"], ["open_url", "search"])

        # Step 3: Search (if not already done)
        if step2["action"] == "open_url":
            step3 = plan["steps"][2]
            self.assertEqual(step3["module"], "browser")
            self.assertEqual(step3["action"], "search")
            self.assertIn("japonais", step3["args"].get("query", "").lower())

        # All steps should be valid
        for i, step in enumerate(plan["steps"]):
            is_valid, error = validate_action_step(step)
            self.assertTrue(is_valid, f"Step {i} invalid: {error}")


class TestReasonerV3CrossApp(unittest.TestCase):
    """Test Reasoner V3 with cross-application workflows"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_salesforce_crm_workflow(self):
        """Test: 'Ouvre Salesforce et affiche le dossier 44219 puis met à jour le champ statut à En cours'"""
        command = "Ouvre Salesforce et affiche le dossier 44219 puis met à jour le champ statut à 'En cours'"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 2)

        # Should involve CRM module
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertIn("crm", modules_used)

        # Check for open_record and update_field actions
        actions_used = [step["action"] for step in plan["steps"]]
        self.assertTrue(
            any(action in ["open_record", "view_record"] for action in actions_used),
            "Should have open_record action"
        )
        self.assertTrue(
            any(action in ["update_field", "set_field"] for action in actions_used),
            "Should have update_field action"
        )

        # All steps should be valid
        for step in plan["steps"]:
            is_valid, error = validate_action_step(step)
            self.assertTrue(is_valid, f"Invalid step: {error}")


class TestReasonerV3DomainSpecific(unittest.TestCase):
    """Test Reasoner V3 with domain-specific commands (CRM, Messaging, Code, Files)"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_messaging_teams(self):
        """Test: 'Envoie je suis en retard à Paul sur Teams'"""
        command = "Envoie 'je suis en retard' à Paul sur Teams"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        modules_used = [step["module"] for step in plan["steps"]]

        # Should use messaging module
        self.assertIn("messaging", modules_used)

        # Should have send_message action
        messaging_steps = [s for s in plan["steps"] if s["module"] == "messaging"]
        self.assertTrue(len(messaging_steps) > 0)

        send_step = next(
            (s for s in messaging_steps if s["action"] in ["send_message", "send"]),
            None
        )
        self.assertIsNotNone(send_step, "Should have send_message action")

        # Should have message content
        self.assertIn("message", send_step["args"])
        self.assertIn("retard", send_step["args"]["message"].lower())

    def test_code_vscode_search_function(self):
        """Test: 'Ouvre VSCode et cherche la fonction login'"""
        command = "Ouvre VSCode et cherche la fonction login"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 1)

        # Should involve code module
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertTrue("code" in modules_used or "system" in modules_used)

        # If code module used, should have find_text or search action
        code_steps = [s for s in plan["steps"] if s["module"] == "code"]
        if code_steps:
            actions = [s["action"] for s in code_steps]
            self.assertTrue(
                any(action in ["find_text", "search", "find"] for action in actions)
            )

    def test_files_finder_search(self):
        """Test: 'Ouvre Finder et trouve le fichier invoice.pdf'"""
        command = "Ouvre Finder et trouve le fichier invoice.pdf"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        modules_used = [step["module"] for step in plan["steps"]]

        # Should involve files or system module
        self.assertTrue("files" in modules_used or "system" in modules_used)

        # Should have search_files action if files module used
        files_steps = [s for s in plan["steps"] if s["module"] == "files"]
        if files_steps:
            actions = [s["action"] for s in files_steps]
            self.assertTrue(
                any(action in ["search_files", "find_files", "search"] for action in actions)
            )


class TestReasonerV3ErrorHandling(unittest.TestCase):
    """Test Reasoner V3 error handling and edge cases"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_empty_request(self):
        """Test: Empty command should return error or empty plan"""
        command = ""
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Should either return None, empty steps, or error
        if plan:
            self.assertIn("steps", plan)
            # If there are steps, they should still be valid
            for step in plan.get("steps", []):
                is_valid, _ = validate_action_step(step)
                self.assertTrue(is_valid)

    def test_impossible_action(self):
        """Test: Impossible action without context (search without browser open)"""
        command = "cherche Python"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Reasoner should either:
        # 1. Add browser open step first
        # 2. Generate only search with appropriate context requirements
        self.assertIsNotNone(plan)

        if plan and "steps" in plan and len(plan["steps"]) > 0:
            # First step should be opening browser or the search should specify browser context
            first_step = plan["steps"][0]
            if first_step["module"] == "browser" and first_step["action"] == "search":
                # Context should indicate browser needed
                self.assertIsNotNone(first_step.get("context"))
            else:
                # Should open browser first
                self.assertEqual(first_step["module"], "system")

    def test_ambiguous_action(self):
        """Test: Ambiguous action should be clarified"""
        command = "ouvre le fichier"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Should generate a valid plan even if ambiguous
        # Reasoner should make a reasonable choice
        self.assertIsNotNone(plan)
        if plan and "steps" in plan and len(plan["steps"]) > 0:
            # Should pick files or code module
            modules_used = [step["module"] for step in plan["steps"]]
            self.assertTrue(any(m in ["files", "code"] for m in modules_used))


class TestReasonerV3JSONValidation(unittest.TestCase):
    """Test that Reasoner V3 always generates valid JSON V3 format"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for testing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_all_required_fields_present(self):
        """Test: All steps have required fields (module, action, args, context)"""
        commands = [
            "ouvre Safari",
            "va sur YouTube",
            "cherche Python",
            "Ouvre Safari et va sur YouTube",
        ]

        for command in commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr")
                self.assertIsNotNone(plan)
                self.assertIn("steps", plan)

                for i, step in enumerate(plan["steps"]):
                    self.assertIn("module", step, f"Step {i} missing 'module'")
                    self.assertIn("action", step, f"Step {i} missing 'action'")
                    self.assertIn("args", step, f"Step {i} missing 'args'")
                    self.assertIn("context", step, f"Step {i} missing 'context'")

    def test_modules_are_valid(self):
        """Test: All modules are from the valid module list"""
        commands = [
            "ouvre Safari",
            "va sur YouTube",
            "envoie un message",
            "ouvre VSCode",
        ]

        valid_modules = get_all_module_names()

        for command in commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr")
                if plan and "steps" in plan:
                    for step in plan["steps"]:
                        self.assertIn(
                            step["module"],
                            valid_modules,
                            f"Invalid module: {step['module']}"
                        )

    def test_actions_are_valid_for_module(self):
        """Test: All actions are valid for their respective modules"""
        commands = [
            "ouvre Safari",
            "va sur YouTube",
            "cherche Python",
        ]

        for command in commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr")
                if plan and "steps" in plan:
                    for i, step in enumerate(plan["steps"]):
                        module = step["module"]
                        action = step["action"]
                        valid_actions = get_all_actions_for_module(module)

                        # Check if action is valid (including aliases)
                        self.assertTrue(
                            is_valid_action(module, action),
                            f"Step {i}: Invalid action '{action}' for module '{module}'. "
                            f"Valid actions: {valid_actions}"
                        )

    def test_no_invented_actions(self):
        """Test: Reasoner never invents actions outside the schema"""
        commands = [
            "ouvre Safari",
            "ferme la fenêtre",
            "copie le texte",
            "va sur Google",
        ]

        for command in commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr")
                if plan and "steps" in plan:
                    for step in plan["steps"]:
                        is_valid, error = validate_action_step(step)
                        self.assertTrue(
                            is_valid,
                            f"Invalid step for '{command}': {error}. Step: {step}"
                        )

    def test_context_is_dict(self):
        """Test: Context is always a dictionary"""
        commands = [
            "ouvre Safari",
            "Ouvre Safari et va sur YouTube",
        ]

        for command in commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, {}, "fr")
                if plan and "steps" in plan:
                    for step in plan["steps"]:
                        context = step.get("context")
                        self.assertIsInstance(
                            context,
                            dict,
                            f"Context should be dict, got {type(context)}"
                        )


if __name__ == "__main__":
    unittest.main()
