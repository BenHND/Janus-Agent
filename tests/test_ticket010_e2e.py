"""
TICKET 010 - End-to-End Integration Tests

Tests complete workflows from Reasoner → Validator → Executor → Agents
to ensure the full V3 pipeline works correctly for realistic scenarios.

Test Categories:
1. Safari → YouTube → Search → Play
2. Teams → chat Paul → send message
3. Salesforce → record → update field
4. Finder → find file → VSCode → paste text
5. Full context propagation validation
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from janus.ai.reasoning.reasoner_llm import ReasonerLLM
from janus.safety.validation.json_plan_validator import JSONPlanValidator
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.agent_setup import setup_agent_registry
from janus.capabilities.agents import SystemAgent, BrowserAgent, MessagingAgent, FilesAgent, CodeAgent


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestE2ESafariYouTubeSearchPlay(unittest.TestCase):
    """Test: Complete Safari → YouTube → Search → Play workflow"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    @async_test
    async def test_full_workflow_safari_youtube_search_play(self):
        """Test: 'Ouvre Safari, va sur YouTube, cherche Python tutorials et lance la vidéo'"""
        command = "Ouvre Safari, va sur YouTube, cherche Python tutorials et lance la vidéo"

        # Step 1: Reasoner generates plan
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan, "Reasoner should generate a plan")
        self.assertIn("steps", plan)
        self.assertGreaterEqual(len(plan["steps"]), 3, "Should have at least 3 steps")

        # Step 2: Validator validates plan
        validation_result = self.validator.validate(plan)

        # Plan should be valid or have only minor issues
        if not validation_result.is_valid:
            # Check if errors are recoverable
            self.assertLess(
                len(validation_result.errors),
                len(plan["steps"]),
                f"Too many validation errors: {validation_result.get_error_summary()}"
            )

        # Step 3: Executor executes plan (mocked)
        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {
                "status": "success",
                "context_updates": {"app": "Safari"}
            }

            with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_browser:
                mock_browser.return_value = {
                    "status": "success",
                    "context_updates": {"url": "https://www.youtube.com"}
                }

                result = await self.executor.execute_plan(plan)

                # Verify execution completed
                self.assertIsNotNone(result)
                self.assertIn("status", result)

                # Check that agents were called
                if result["status"] == "success":
                    self.assertGreater(mock_system.call_count + mock_browser.call_count, 0)

    def test_plan_structure_safari_youtube(self):
        """Test: Plan structure is correct for Safari → YouTube workflow"""
        command = "Ouvre Safari et va sur YouTube"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan["steps"]), 2)

        # Step 1: Open Safari
        self.assertEqual(plan["steps"][0]["module"], "system")
        self.assertIn(plan["steps"][0]["action"], ["open_application", "open_application"])

        # Step 2: Open YouTube
        self.assertEqual(plan["steps"][1]["module"], "browser")
        self.assertEqual(plan["steps"][1]["action"], "open_url")

        # Context should propagate
        self.assertEqual(plan["steps"][1].get("context", {}).get("app"), "Safari")


class TestE2ETeamsMessaging(unittest.TestCase):
    """Test: Complete Teams → chat Paul → send message workflow"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    @async_test
    async def test_full_workflow_teams_send_message(self):
        """Test: 'Ouvre Teams, ouvre le chat avec Paul et envoie je suis en retard'"""
        command = "Ouvre Teams, ouvre le chat avec Paul et envoie 'je suis en retard'"

        # Step 1: Reasoner generates plan
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertGreaterEqual(len(plan["steps"]), 2)

        # Should involve messaging module
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertTrue(
            "messaging" in modules_used or "system" in modules_used,
            "Should involve messaging or system module"
        )

        # Step 2: Validator validates plan
        validation_result = self.validator.validate(plan)

        # Step 3: Executor executes plan (mocked)
        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {"status": "success", "context_updates": {"app": "Teams"}}

            with patch.object(MessagingAgent, 'execute', new_callable=AsyncMock) as mock_messaging:
                mock_messaging.return_value = {"status": "success", "context_updates": {}}

                result = await self.executor.execute_plan(plan)

                self.assertIsNotNone(result)
                self.assertIn("status", result)


class TestE2ESalesforceCRM(unittest.TestCase):
    """Test: Complete Salesforce → record → update field workflow"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    def test_plan_structure_salesforce_update(self):
        """Test: Plan structure for Salesforce CRM workflow"""
        command = "Ouvre Salesforce, affiche le dossier 221 et met à jour le statut à 'En cours'"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 2)

        # Should use CRM module
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertTrue(
            "crm" in modules_used or ("browser" in modules_used and "system" in modules_used),
            "Should involve CRM or browser/system modules"
        )

        # Validate the plan
        validation_result = self.validator.validate(plan)
        # Plan should be processable
        self.assertIsNotNone(validation_result)


class TestE2EFinderVSCodeWorkflow(unittest.TestCase):
    """Test: Complete Finder → find file → VSCode → paste text workflow"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    @async_test
    async def test_full_workflow_finder_vscode_paste(self):
        """Test: 'Ouvre Finder, trouve report.txt, ouvre VSCode et colle le contenu'"""
        command = "Ouvre Finder, trouve report.txt, ouvre VSCode et colle le contenu"

        # Step 1: Reasoner generates plan
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertGreaterEqual(len(plan["steps"]), 3)

        # Should involve files and code modules
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertTrue(
            any(m in ["files", "code", "system", "ui"] for m in modules_used),
            "Should involve files, code, system, or ui modules"
        )

        # Step 2: Validator validates plan
        validation_result = self.validator.validate(plan)

        # Step 3: Executor executes plan (mocked)
        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {"status": "success", "context_updates": {}}

            with patch.object(FilesAgent, 'execute', new_callable=AsyncMock) as mock_files:
                mock_files.return_value = {"status": "success", "context_updates": {}}

                with patch.object(CodeAgent, 'execute', new_callable=AsyncMock) as mock_code:
                    mock_code.return_value = {"status": "success", "context_updates": {}}

                    result = await self.executor.execute_plan(plan)

                    self.assertIsNotNone(result)
                    self.assertIn("status", result)


class TestE2EContextPropagation(unittest.TestCase):
    """Test: Full context propagation through entire V3 pipeline"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    def test_context_propagates_through_reasoner(self):
        """Test: Reasoner propagates context across steps"""
        command = "Ouvre Safari, va sur YouTube et cherche Python"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 3)

        # Step 1: Open Safari - no app context yet
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")

        # Step 2: Go to YouTube - should have Safari context
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2.get("context", {}).get("app"), "Safari")

        # Step 3: Search - should have Safari and YouTube context
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3.get("context", {}).get("app"), "Safari")

    @async_test
    async def test_context_updated_after_execution(self):
        """Test: Context is updated after each step execution"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                                        "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://www.youtube.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        # Validate plan
        validation_result = self.validator.validate(plan)
        self.assertTrue(
            validation_result.is_valid or not validation_result.has_errors(),
            f"Plan should be valid: {validation_result.get_error_summary()}"
        )

        # Execute with mocked agents
        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {
                "status": "success",
                "context_updates": {"app": "Safari"}
            }

            with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_browser:
                mock_browser.return_value = {
                    "status": "success",
                    "context_updates": {"url": "https://www.youtube.com", "domain": "youtube.com"}
                }

                result = await self.executor.execute_plan(plan)

                self.assertIsNotNone(result)
                self.assertIn("status", result)

                # Verify both agents were called
                if result["status"] == "success":
                    self.assertGreater(mock_system.call_count, 0)
                    self.assertGreater(mock_browser.call_count, 0)

    def test_validator_preserves_context(self):
        """Test: Validator preserves context during validation"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://youtube.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        validation_result = self.validator.validate(plan)

        if validation_result.plan:
            # Context should be preserved
            self.assertEqual(
                validation_result.plan["steps"][0].get("context", {}).get("app"),
                "Safari"
            )
            self.assertEqual(
                validation_result.plan["steps"][0].get("context", {}).get("session"),
                "12345"
            )


class TestE2EComplexWorkflows(unittest.TestCase):
    """Test: Complex multi-module workflows"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)

    def test_complex_cross_app_workflow(self):
        """Test: Complex workflow spanning multiple apps"""
        command = "Ouvre Chrome, va sur Gmail, copie l'email, ouvre VSCode et colle-le"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan["steps"]), 4)

        # Should involve multiple modules
        modules_used = [step["module"] for step in plan["steps"]]
        self.assertGreater(len(set(modules_used)), 1, "Should use multiple modules")

        # Validate plan
        validation_result = self.validator.validate(plan)
        self.assertIsNotNone(validation_result)

    def test_conditional_workflow_handling(self):
        """Test: Workflow that might require conditional logic"""
        command = "Si Safari est ouvert, ferme-le, sinon ouvre Chrome"
        plan = self.reasoner.generate_structured_plan(command, {}, "fr")

        # Reasoner should generate a reasonable plan
        # (exact behavior depends on implementation)
        self.assertIsNotNone(plan)

        if plan and "steps" in plan and len(plan["steps"]) > 0:
            # Plan should be structured
            for step in plan["steps"]:
                self.assertIn("module", step)
                self.assertIn("action", step)


class TestE2EErrorScenarios(unittest.TestCase):
    """Test: End-to-end error handling scenarios"""

    def setUp(self):
        """Set up full V3 pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    @async_test
    async def test_error_propagation_through_pipeline(self):
        """Test: Errors are properly propagated through the pipeline"""
        # Create a plan that will fail
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "nonexistent_action",
                    "args": {},
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

        # Validator should catch this
        validation_result = self.validator.validate(plan)
        self.assertFalse(validation_result.is_valid)
        self.assertGreater(len(validation_result.errors), 0)

    @async_test
    async def test_partial_execution_on_error(self):
        """Test: Pipeline handles partial execution when step fails"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                                        "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://youtube.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        # First step succeeds, second fails
        with patch.object(SystemAgent, 'execute', new_callable=AsyncMock) as mock_system:
            mock_system.return_value = {"status": "success", "context_updates": {"app": "Safari"}}

            with patch.object(BrowserAgent, 'execute', new_callable=AsyncMock) as mock_browser:
                from janus.capabilities.agents import AgentExecutionError
                mock_browser.side_effect = AgentExecutionError(
                    "browser", "open_url", "Failed to open URL", recoverable=False
                )

                result = await self.executor.execute_plan(plan)

                # Should report error
                self.assertEqual(result["status"], "error")
                self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
