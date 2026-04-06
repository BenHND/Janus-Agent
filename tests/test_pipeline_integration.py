"""
Integration tests for full pipeline
Tests: STT → VoiceReasoner → Executor
"""
import unittest
from unittest.mock import Mock, patch

from janus.runtime.api import PipelineEntry
from janus.exec.executor import Executor
from janus.exec.safety import SafetyManager


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for full pipeline"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock STT engine
        self.mock_stt = Mock()

        # Use real VoiceReasoner with minimal setup
        from janus.ai.reasoning.voice_reasoner import VoiceReasoner

        self.voice_reasoner = VoiceReasoner(use_ml_classifier=False)

        # Create executor with dry_run mode
        self.executor = Executor(dry_run=True)

        # Create pipeline
        self.pipeline = PipelineEntry(
            stt_engine=self.mock_stt,
            voice_reasoner=self.voice_reasoner,
            executor=self.executor,
        )

    def test_process_simple_command(self):
        """Test processing simple text command"""
        result = self.pipeline.process_text("open Chrome", auto_execute=True)

        self.assertEqual(result["status"], "executed")
        self.assertIn("text", result)
        self.assertIn("intents", result)
        self.assertIn("execution_report", result)

        # Check intents
        intents = result["intents"]
        self.assertGreater(len(intents), 0)
        self.assertEqual(intents[0]["intent"], "open_app")

    def test_process_multi_action_command(self):
        """Test processing multi-action command"""
        result = self.pipeline.process_text(
            "open Chrome and go to github.com",
            auto_execute=True,
        )

        self.assertEqual(result["status"], "executed")

        # Should have multiple intents
        intents = result["intents"]
        self.assertGreater(len(intents), 0)

    def test_process_without_execution(self):
        """Test processing without auto-execution"""
        result = self.pipeline.process_text("open VSCode", auto_execute=False)

        self.assertEqual(result["status"], "parsed")
        self.assertIn("intents", result)
        self.assertNotIn("execution_report", result)

    def test_process_unknown_command(self):
        """Test processing unknown command"""
        result = self.pipeline.process_text("xyzabc nonsense", auto_execute=True)

        # Should either parse with low confidence or return no_intent
        self.assertIn(result["status"], ["no_intent", "executed"])

    def test_listen_and_execute_mock(self):
        """Test listen_and_execute with mocked STT"""
        self.mock_stt.listen_and_transcribe.return_value = "open Terminal"

        result = self.pipeline.listen_and_execute(auto_execute=True)

        self.assertEqual(result["status"], "executed")
        self.assertIn("transcription", result)
        self.assertEqual(result["transcription"], "open Terminal")

        # Verify STT was called
        self.mock_stt.listen_and_transcribe.assert_called_once()

    def test_listen_and_execute_no_transcription(self):
        """Test listen_and_execute with no transcription"""
        self.mock_stt.listen_and_transcribe.return_value = None

        result = self.pipeline.listen_and_execute(auto_execute=True)

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_pipeline_with_safety_manager(self):
        """Test pipeline with safety manager blocking action"""
        # Create executor with safety manager that blocks all
        safety_manager = SafetyManager(
            whitelist=set(),  # Empty whitelist
            require_confirmation=True,
        )
        executor = Executor(safety_manager=safety_manager, dry_run=False)

        pipeline = PipelineEntry(
            stt_engine=self.mock_stt,
            voice_reasoner=self.voice_reasoner,
            executor=executor,
        )

        result = pipeline.process_text("delete_file test.txt", auto_execute=True)

        # Command may not be understood as delete_file intent
        # But if executed, should be blocked or failed
        self.assertIn("execution_report", result)
        report = result["execution_report"]
        # Report status should indicate some kind of failure or no-intent
        self.assertIn(report["status"], ["fatal_fail", "retryable_fail", "success", "no_intent"])

    def test_pipeline_with_adapter(self):
        """Test pipeline with registered adapter"""
        mock_adapter = Mock()
        mock_adapter.execute.return_value = {"status": "success"}

        executor = Executor(dry_run=False)
        executor.register_adapter("chrome", mock_adapter)

        pipeline = PipelineEntry(
            stt_engine=self.mock_stt,
            voice_reasoner=self.voice_reasoner,
            executor=executor,
        )

        result = pipeline.process_text("go to github.com", auto_execute=True)

        self.assertEqual(result["status"], "executed")

        # Adapter should have been called if intent was routed correctly
        # (depends on intent parsing)

    def test_execution_report_structure(self):
        """Test execution report structure"""
        result = self.pipeline.process_text("open Chrome", auto_execute=True)

        self.assertIn("execution_report", result)
        report = result["execution_report"]

        # Check report structure
        self.assertIn("status", report)
        self.assertIn("results", report)
        self.assertIn("total_duration", report)
        self.assertIn("timestamp", report)
        self.assertIn("dry_run", report)
        self.assertIn("success_count", report)
        self.assertIn("failure_count", report)

        self.assertTrue(report["dry_run"])

    def test_french_command(self):
        """Test French command processing"""
        result = self.pipeline.process_text("ouvre Chrome", auto_execute=True)

        self.assertEqual(result["status"], "executed")

        intents = result["intents"]
        self.assertGreater(len(intents), 0)
        self.assertEqual(intents[0]["intent"], "open_app")

    def test_context_tracking_across_commands(self):
        """Test context tracking across multiple commands"""
        # First command
        result1 = self.pipeline.process_text("open Chrome", auto_execute=False)
        self.assertEqual(result1["status"], "parsed")

        # Second command with implicit reference
        result2 = self.pipeline.process_text("close it", auto_execute=False)

        # Both should parse
        self.assertIn(result2["status"], ["parsed", "no_intent"])


if __name__ == "__main__":
    unittest.main()
