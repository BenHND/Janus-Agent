"""
TICKET 009: Test V3 Pipeline Integration

Verifies that the V3 pipeline (Reasoner → Validator → Executor) works end-to-end
and that legacy components are not used in the main command flow.
"""
import asyncio
import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core import MemoryEngine
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import Settings


class TestTicket009V3Pipeline(unittest.TestCase):
    """Test V3 pipeline integration"""

    def setUp(self):
        """Set up test pipeline"""
        self.settings = Settings()
        self.memory = MemoryEngine(self.settings.database)  # Pass settings.database object
        self.pipeline = JanusPipeline(
            self.settings,
            self.memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
        )

    def test_reasoner_v3_available(self):
        """Test that ReasonerLLM V3 is initialized and available"""
        reasoner = self.pipeline.reasoner_llm
        self.assertIsNotNone(reasoner)
        # Should fall back to mock backend if Ollama not available
        self.assertTrue(reasoner.available, "ReasonerLLM should be available (mock fallback)")

    def test_validator_v3_exists(self):
        """Test that JSONPlanValidator V3 exists"""
        validator = self.pipeline.validator_v3
        self.assertIsNotNone(validator)
        self.assertEqual(validator.__class__.__name__, "JSONPlanValidator")

    def test_execution_engine_v3_exists(self):
        """Test that ExecutionEngineV3 exists"""
        executor = self.pipeline.execution_engine_v3
        self.assertIsNotNone(executor)
        self.assertEqual(executor.__class__.__name__, "ExecutionEngineV3")

    def test_agent_registry_exists(self):
        """Test that AgentRegistry exists"""
        registry = self.pipeline.agent_registry
        self.assertIsNotNone(registry)
        self.assertEqual(registry.__class__.__name__, "AgentRegistry")

    def test_simple_command_generates_plan(self):
        """Test that a simple command generates a structured plan"""
        command = "Ouvre Chrome"
        plan = self.pipeline.reasoner_llm.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertGreater(len(plan["steps"]), 0)

        # Verify first step structure
        first_step = plan["steps"][0]
        self.assertIn("module", first_step)
        self.assertIn("action", first_step)
        self.assertIn("args", first_step)
        self.assertIn("context", first_step)

    def test_compound_command_generates_multi_step_plan(self):
        """Test that compound command generates multi-step plan"""
        command = "Ouvre Safari, va sur YouTube et cherche Python tutoriels"
        plan = self.pipeline.reasoner_llm.generate_structured_plan(command, {}, "fr")

        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        # Should have 3 steps: open Safari, go to YouTube, search
        self.assertEqual(len(plan["steps"]), 3)

        # Verify step 1: open Safari
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertEqual(step1["action"], "open_app")
        self.assertIn("Safari", step1["args"].get("app_name", ""))

        # Verify step 2: go to YouTube
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["action"], "open_url")
        self.assertIn("youtube", step2["args"].get("url", "").lower())

        # Verify step 3: search
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3["action"], "search")

    def test_v3_pipeline_end_to_end_mock(self):
        """Test complete V3 pipeline with mock execution"""
        command = "Ouvre Safari, va sur YouTube et cherche Python tutoriels"

        # Run command through pipeline
        result = asyncio.run(self.pipeline.process_command_async(command, mock_execution=True))

        # Verify result
        self.assertIsNotNone(result)
        self.assertTrue(result.success, f"Pipeline failed: {result.message if hasattr(result, 'message') else 'unknown'}")

        # Verify all steps executed
        self.assertGreaterEqual(len(result.action_results), 3)

        # Verify steps succeeded
        for action_result in result.action_results:
            self.assertTrue(action_result.success, f"Step {action_result.action_type} failed")

    def test_conversation_mode_parameter_accepted(self):
        """Test that conversation_mode parameter is accepted (backward compatibility)"""
        command = "Ouvre Chrome"

        # Should not raise TypeError
        try:
            result = asyncio.run(
                self.pipeline.process_command_async(command, mock_execution=True, conversation_mode=False)
            )
            self.assertIsNotNone(result)
        except TypeError as e:
            self.fail(f"conversation_mode parameter not accepted: {e}")

    def test_legacy_components_not_used_in_main_flow(self):
        """Test that legacy components are not called in main V3 flow"""
        command = "Ouvre Chrome"

        # Mock the legacy components
        with patch.object(self.pipeline, '_parse_with_nlu') as mock_nlu, \
             patch.object(self.pipeline, '_create_plan_deterministic') as mock_planner:

            # Run command
            result = asyncio.run(self.pipeline.process_command_async(command, mock_execution=True))

            # Verify legacy components were NOT called
            mock_nlu.assert_not_called()
            mock_planner.assert_not_called()

            # Verify result succeeded
            self.assertIsNotNone(result)

    def test_validator_rejects_invalid_json(self):
        """Test that validator rejects invalid JSON plans"""
        invalid_plan = {
            "steps": [
                {
                    # Missing required 'action' field
                    "module": "system",
                    "args": {"app_name": "Chrome"},
                }
            ]
        }

        validator = self.pipeline.validator_v3
        validation_result = validator.validate_plan(invalid_plan)

        self.assertFalse(validation_result.is_valid)
        self.assertGreater(len(validation_result.errors), 0)

    def test_validator_accepts_valid_json(self):
        """Test that validator accepts valid JSON plans"""
        valid_plan = {
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

        validator = self.pipeline.validator_v3
        validation_result = validator.validate_plan(valid_plan)

        self.assertTrue(validation_result.is_valid)


if __name__ == "__main__":
    unittest.main()
