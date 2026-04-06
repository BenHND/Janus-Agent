"""
Integration tests for Unified Pipeline (JanusPipeline).

Tests the complete pipeline: NLU → Planner → Executor
Validates unified architecture with no legacy code:
- Deterministic NLU (FR/EN) with validated intents
- Deterministic Planner with testable Intent→Plan mapping
- Clean error handling with ExecutionResult
- Optional integration of STT/TTS/Vision/Learning
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from janus.runtime.core import (
    ActionPlan,
    DeterministicNLU,
    DeterministicPlanner,
    ErrorType,
    ExecutionResult,
    IntentValidationStatus,
    MemoryEngine,
    Settings,
    JanusPipeline,
    ValidatedIntent,
)


class TestDeterministicNLU(unittest.TestCase):
    """Test deterministic NLU component"""

    def setUp(self):
        """Set up test fixtures"""
        self.nlu = DeterministicNLU(enable_llm_disambiguation=False)

    def test_parse_french_open_app(self):
        """Test parsing French open app command"""
        validated = self.nlu.parse_command("ouvre Safari")

        self.assertTrue(validated.is_valid())
        self.assertEqual(validated.validation_status, IntentValidationStatus.VALID)
        self.assertEqual(validated.intent.action, "open_app")
        self.assertEqual(validated.intent.parameters.get("app_name"), "safari")
        self.assertGreater(validated.confidence, 0.5)

    def test_parse_english_open_app(self):
        """Test parsing English open app command"""
        validated = self.nlu.parse_command("open Chrome")

        self.assertTrue(validated.is_valid())
        self.assertEqual(validated.intent.action, "open_app")
        self.assertEqual(validated.intent.parameters.get("app_name"), "chrome")

    def test_parse_french_click(self):
        """Test parsing French click command"""
        validated = self.nlu.parse_command("clique sur le bouton")

        self.assertTrue(validated.is_valid())
        self.assertEqual(validated.intent.action, "click")
        self.assertIn("target", validated.intent.parameters)

    def test_parse_english_click(self):
        """Test parsing English click command"""
        validated = self.nlu.parse_command("click on button")

        self.assertTrue(validated.is_valid())
        self.assertEqual(validated.intent.action, "click")

    def test_parse_copy_paste(self):
        """Test parsing copy and paste commands"""
        # French
        validated_copy = self.nlu.parse_command("copie ceci")
        self.assertTrue(validated_copy.is_valid())
        self.assertEqual(validated_copy.intent.action, "copy")

        validated_paste = self.nlu.parse_command("colle ici")
        self.assertTrue(validated_paste.is_valid())
        self.assertEqual(validated_paste.intent.action, "paste")

        # English
        validated_copy_en = self.nlu.parse_command("copy this")
        self.assertTrue(validated_copy_en.is_valid())
        self.assertEqual(validated_copy_en.intent.action, "copy")

    def test_parse_url_command(self):
        """Test parsing URL command"""
        # Use more explicit URL patterns
        validated = self.nlu.parse_command("va sur github.com")

        self.assertTrue(validated.is_valid())
        self.assertEqual(validated.intent.action, "open_url")
        self.assertIn("url", validated.intent.parameters)

    def test_unknown_command(self):
        """Test handling of unknown commands"""
        validated = self.nlu.parse_command("xyzabc nonsense command")

        # Should parse but may be unknown or invalid
        self.assertIsNotNone(validated)
        self.assertIsNotNone(validated.intent)

    def test_input_normalization(self):
        """Test that input normalization works"""
        # Test with filler words
        validated1 = self.nlu.parse_command("euh ouvre Safari")
        validated2 = self.nlu.parse_command("ouvre Safari")

        # Both should parse to same intent
        self.assertEqual(validated1.intent.action, validated2.intent.action)

        # Test with extra whitespace
        validated3 = self.nlu.parse_command("  ouvre   Safari  ")
        self.assertEqual(validated3.intent.action, "open_app")

    def test_validation_invalid_intent(self):
        """Test validation rejects invalid intents"""
        # Command that matches pattern but has invalid parameters
        # This is harder to test directly, so we test the validation rules
        from janus.runtime.core.contracts import Intent

        # Create an intent with missing required parameter
        intent = Intent(
            action="open_file",
            confidence=0.9,
            parameters={},  # Missing file_path
            raw_command="ouvre le fichier",
        )

        validated = self.nlu._validate_intent(intent)

        self.assertFalse(validated.is_valid())
        self.assertEqual(validated.validation_status, IntentValidationStatus.INVALID)
        self.assertIsNotNone(validated.ambiguity_reason)


class TestDeterministicPlanner(unittest.TestCase):
    """Test deterministic planner component"""

    def setUp(self):
        """Set up test fixtures"""
        self.planner = DeterministicPlanner()

    def _create_intent(self, action: str, **parameters):
        """Helper to create intent"""
        from janus.runtime.core.contracts import Intent

        return Intent(
            action=action, confidence=0.9, parameters=parameters, raw_command=f"test {action}"
        )

    def test_plan_open_app(self):
        """Test planning for open app action"""
        intent = self._create_intent("open_app", app_name="Safari")
        plan = self.planner.create_plan(intent)

        self.assertIsInstance(plan, ActionPlan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0]["type"], "open_app")
        self.assertEqual(plan.actions[0]["app_name"], "Safari")
        self.assertFalse(plan.requires_confirmation)

    def test_plan_click(self):
        """Test planning for click action"""
        intent = self._create_intent("click", target="button")
        plan = self.planner.create_plan(intent)

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0]["type"], "click")

    def test_plan_copy_paste(self):
        """Test planning for copy and paste"""
        intent_copy = self._create_intent("copy", target="text")
        plan_copy = self.planner.create_plan(intent_copy)

        self.assertEqual(len(plan_copy.actions), 1)
        self.assertEqual(plan_copy.actions[0]["type"], "copy")

        intent_paste = self._create_intent("paste")
        plan_paste = self.planner.create_plan(intent_paste)

        self.assertEqual(len(plan_paste.actions), 1)
        self.assertEqual(plan_paste.actions[0]["type"], "paste")

    def test_plan_open_url(self):
        """Test planning for open URL"""
        intent = self._create_intent("open_url", url="https://github.com")
        plan = self.planner.create_plan(intent)

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0]["type"], "open_url")
        self.assertEqual(plan.actions[0]["url"], "https://github.com")
        self.assertEqual(plan.actions[0].get("module"), "chrome")

    def test_plan_terminal_command(self):
        """Test planning for terminal command"""
        intent = self._create_intent("execute_command", command="ls -la")
        plan = self.planner.create_plan(intent)

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0]["type"], "execute_command")
        self.assertEqual(plan.actions[0]["command"], "ls -la")
        self.assertTrue(plan.requires_confirmation)  # Terminal commands need confirmation

    def test_plan_vscode_actions(self):
        """Test planning for VSCode actions"""
        # Open file
        intent_open = self._create_intent("open_file", file_path="test.py")
        plan_open = self.planner.create_plan(intent_open)

        self.assertEqual(len(plan_open.actions), 1)
        self.assertEqual(plan_open.actions[0]["type"], "open_file")
        self.assertEqual(plan_open.actions[0].get("module"), "vscode")

        # Goto line
        intent_goto = self._create_intent("goto_line", line_number=42)
        plan_goto = self.planner.create_plan(intent_goto)

        self.assertEqual(len(plan_goto.actions), 1)
        self.assertEqual(plan_goto.actions[0]["type"], "goto_line")

    def test_plan_has_estimated_duration(self):
        """Test that plans have estimated duration"""
        intent = self._create_intent("open_app", app_name="Safari")
        plan = self.planner.create_plan(intent)

        self.assertIsNotNone(plan.estimated_duration_ms)
        self.assertGreater(plan.estimated_duration_ms, 0)

    def test_plan_validation(self):
        """Test that plans are validated"""
        from janus.runtime.core.deterministic_planner import PlanValidationError

        # Create an empty plan - should fail validation
        intent = self._create_intent("open_app", app_name="Safari")
        plan = ActionPlan(intent=intent)
        # Don't add any actions

        with self.assertRaises(PlanValidationError):
            self.planner._validate_plan(plan)

    def test_deterministic_planning(self):
        """Test that same intent always produces same plan"""
        intent = self._create_intent("open_app", app_name="Chrome")

        plan1 = self.planner.create_plan(intent)
        plan2 = self.planner.create_plan(intent)

        # Plans should be identical
        self.assertEqual(len(plan1.actions), len(plan2.actions))
        self.assertEqual(plan1.actions[0]["type"], plan2.actions[0]["type"])
        self.assertEqual(plan1.actions[0].get("app_name"), plan2.actions[0].get("app_name"))


class TestUnifiedPipeline(unittest.TestCase):
    """Test complete unified pipeline (JanusPipeline)"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[audio]
sample_rate = 16000

[language]
default = fr

[database]
path = janus.db

[logging]
level = INFO
enable_structured = true
log_to_database = true
"""
            )

        # Initialize components
        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(
            self.settings,
            self.memory,
            enable_voice=False,  # No voice for unit tests
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_process_text_command_success(self):
        """Test processing text command through pipeline"""
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.intent.action, "open_app")
        self.assertGreater(len(result.action_results), 0)

    def test_process_english_command(self):
        """Test processing English command"""
        result = self.pipeline.process_command("open Chrome", mock_execution=True)

        self.assertTrue(result.success)
        self.assertEqual(result.intent.action, "open_app")

    def test_process_click_command(self):
        """Test processing click command"""
        result = self.pipeline.process_command("clique sur le bouton", mock_execution=True)

        self.assertTrue(result.success)
        self.assertGreater(len(result.action_results), 0)

    def test_process_unknown_command(self):
        """Test processing unknown command"""
        result = self.pipeline.process_command("xyzabc unknown nonsense", mock_execution=True)

        # Should not raise exception, should return result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ExecutionResult)

    def test_no_uncaught_exceptions(self):
        """Test that pipeline never raises uncaught exceptions"""
        # Try various potentially problematic inputs
        test_cases = [
            "",  # Empty
            "   ",  # Whitespace
            "xyzabc nonsense",  # Unknown
            "ouvre",  # Incomplete
            "normal command",  # Valid
        ]

        for cmd in test_cases:
            try:
                result = self.pipeline.process_command(cmd, mock_execution=True)
                # Should always return a result
                self.assertIsNotNone(result)
                self.assertIsInstance(result, ExecutionResult)
            except Exception as e:
                self.fail(f"Pipeline raised exception for '{cmd}': {e}")

    def test_execution_result_structure(self):
        """Test that execution result has proper structure"""
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        # Check required fields
        self.assertIsNotNone(result.intent)
        self.assertIsNotNone(result.session_id)
        self.assertIsNotNone(result.request_id)
        self.assertIsNotNone(result.timestamp)
        self.assertIsInstance(result.action_results, list)
        self.assertIsInstance(result.success, bool)

    def test_action_result_structure(self):
        """Test that action results have proper structure"""
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        self.assertGreater(len(result.action_results), 0)

        action_result = result.action_results[0]

        # Check required fields
        self.assertIsNotNone(action_result.action_type)
        self.assertIsInstance(action_result.success, bool)
        self.assertIsNotNone(action_result.message)
        self.assertIsNotNone(action_result.timestamp)

    def test_pipeline_logs_to_database(self):
        """Test that pipeline logs to database"""
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        # Get logs for this session
        logs = self.memory.get_structured_logs(session_id=result.session_id, limit=100)

        # Should have logs
        self.assertGreater(len(logs), 0)

    def test_multiple_commands_sequence(self):
        """Test processing multiple commands in sequence"""
        commands = ["ouvre Safari", "clique sur le bouton", "copie ceci", "colle ici"]

        for cmd in commands:
            result = self.pipeline.process_text_command(cmd, mock_execution=True)
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.execution_result)

    def test_error_handling_returns_error_result(self):
        """Test that errors are returned as ActionResult, not exceptions"""
        # Force an error by using invalid intent
        from janus.runtime.core.contracts import Intent
        from janus.runtime.core.deterministic_planner import PlanValidationError

        # Test with empty command
        result = self.pipeline.process_text_command("", mock_execution=True)

        # Should return result with error, not raise
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.execution_result)


class TestIntegrationNLUPlannerExecution(unittest.TestCase):
    """Test integration of NLU → Planner → Execution"""

    def setUp(self):
        """Set up test fixtures"""
        self.nlu = DeterministicNLU()
        self.planner = DeterministicPlanner()

    def test_nlu_to_planner_integration(self):
        """Test that NLU output works with Planner input"""
        # Parse command with NLU
        validated = self.nlu.parse_command("ouvre Chrome")

        self.assertTrue(validated.is_valid())

        # Create plan from validated intent
        plan = self.planner.create_plan(validated.intent)

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0]["type"], "open_app")

    def test_french_english_consistency(self):
        """Test that FR and EN commands produce consistent plans"""
        # French
        validated_fr = self.nlu.parse_command("ouvre Chrome")
        plan_fr = self.planner.create_plan(validated_fr.intent)

        # English
        validated_en = self.nlu.parse_command("open Chrome")
        plan_en = self.planner.create_plan(validated_en.intent)

        # Both should have same structure
        self.assertEqual(len(plan_fr.actions), len(plan_en.actions))
        self.assertEqual(plan_fr.actions[0]["type"], plan_en.actions[0]["type"])

    def test_deterministic_full_pipeline(self):
        """Test that full pipeline is deterministic"""
        command = "ouvre Safari"

        # Process twice
        validated1 = self.nlu.parse_command(command)
        plan1 = self.planner.create_plan(validated1.intent)

        validated2 = self.nlu.parse_command(command)
        plan2 = self.planner.create_plan(validated2.intent)

        # Results should be identical
        self.assertEqual(validated1.intent.action, validated2.intent.action)
        self.assertEqual(len(plan1.actions), len(plan2.actions))
        self.assertEqual(plan1.actions[0]["type"], plan2.actions[0]["type"])


if __name__ == "__main__":
    unittest.main()
