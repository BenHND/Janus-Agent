"""
Unit tests for vision-triggered replanning

These tests verify the implementation of:
1. Vision verification after successful actions
2. Automatic replanning when vision verification fails
3. Vision context passed to replanning
4. Integration with execution flow
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from janus.runtime.core import (
    ActionPlan,
    ActionResult,
    ExecutionContext,
    ExecutionResult,
    Intent,
    MemoryEngine,
    Settings,
    JanusPipeline,
)


class TestVisionTriggeredReplanning(unittest.TestCase):
    """Test cases for vision-triggered replanning"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        # Create isolated temp directory for each test
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config.ini for testing
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[audio]
sample_rate = 16000
activation_threshold = 500.0

[language]
default = fr

[automation]
safety_delay = 0.5

[session]
state_file = session_state.json
max_history = 50

[llm]
provider = mock
model = gpt-4

[tts]
enable_tts = false

[database]
path = janus.db
enable_wal = true

[logging]
level = INFO
enable_structured = true
log_to_database = true

[vision]
enable_vision = true
"""
            )

        # Initialize components
        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(self.settings, self.memory)

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_verify_action_with_vision_method_exists(self):
        """Test that vision service has verify_action_with_vision method"""
        self.assertTrue(hasattr(self.pipeline.vision_service, "verify_action_with_vision"))
        self.assertTrue(callable(getattr(self.pipeline.vision_service, "verify_action_with_vision")))

    def test_verify_action_with_vision_returns_data(self):
        """Test that vision verification returns proper data structure"""
        # Mock vision runner
        mock_vision = Mock()
        mock_vision.verify_action_result = Mock(return_value=True)
        self.pipeline.vision_service._vision_runner = mock_vision

        # Create action result
        action_result = ActionResult(
            action_type="test.action", success=True, message="Test action", duration_ms=100
        )

        # Call verification
        vision_data = self.pipeline.vision_service.verify_action_with_vision(action_result, "test_request_001")

        # Verify data structure
        self.assertIsNotNone(vision_data)
        self.assertIn("verification", vision_data)
        self.assertIn("visual_state", vision_data)
        self.assertTrue(vision_data["verification"]["passed"])

    def test_vision_verification_failure_detection(self):
        """Test that vision verification failure is detected"""
        # Mock vision runner that fails verification
        mock_vision = Mock()
        mock_vision.verify_action_result = Mock(return_value=False)
        self.pipeline.vision_service._vision_runner = mock_vision

        # Create action result
        action_result = ActionResult(
            action_type="test.action", success=True, message="Test action", duration_ms=100
        )

        # Call verification
        vision_data = self.pipeline.vision_service.verify_action_with_vision(action_result, "test_request_001")

        # Verify failure detection
        self.assertIsNotNone(vision_data)
        self.assertFalse(vision_data["verification"]["passed"])

    def test_attempt_replanning_accepts_vision_data(self):
        """Test that _attempt_replanning accepts vision_data parameter"""
        intent = Intent(action="test", confidence=0.9, raw_command="test command")
        context = ExecutionContext()

        # Mock NLU and reasoner
        mock_reasoner = Mock()
        mock_reasoner.replan = Mock(return_value={"steps": []})
        mock_nlu = Mock()
        mock_nlu.reasoner = mock_reasoner
        self.pipeline._nlu = mock_nlu

        # Vision data
        vision_data = {
            "verification": {"passed": False, "action_type": "test.action"},
            "visual_state": {"verified": False, "confidence": 0.3},
        }

        # Call replanning with vision data
        result = self.pipeline._attempt_replanning(
            failed_action={"module": "test", "action": "action"},
            error="Vision verification failed",
            completed_steps=[],
            remaining_steps=[],
            original_intent=intent,
            request_id="test_request_001",
            context=context,
            vision_data=vision_data,
        )

        # Verify reasoner was called
        self.assertTrue(mock_reasoner.replan.called)

        # Get the execution_context passed to replan
        call_args = mock_reasoner.replan.call_args
        execution_context = call_args[1]["execution_context"]

        # Verify vision data was included
        self.assertIn("vision_verification", execution_context)
        self.assertIn("visual_state", execution_context)
        self.assertEqual(execution_context["vision_verification"], vision_data["verification"])

    def test_vision_data_without_vision_runner(self):
        """Test that vision verification returns None when no vision runner"""
        # Ensure no vision runner
        self.pipeline.vision_service._vision_runner = None

        # Create action result
        action_result = ActionResult(
            action_type="test.action", success=True, message="Test action", duration_ms=100
        )

        # Call verification
        vision_data = self.pipeline.vision_service.verify_action_with_vision(action_result, "test_request_001")

        # Should return None
        self.assertIsNone(vision_data)

    def test_replanning_without_vision_data(self):
        """Test that replanning works without vision data (backward compatibility)"""
        intent = Intent(action="test", confidence=0.9, raw_command="test command")
        context = ExecutionContext()

        # Mock NLU and reasoner
        mock_reasoner = Mock()
        mock_reasoner.replan = Mock(return_value={"steps": []})
        mock_nlu = Mock()
        mock_nlu.reasoner = mock_reasoner
        self.pipeline._nlu = mock_nlu

        # Call replanning without vision data
        result = self.pipeline._attempt_replanning(
            failed_action={"module": "test", "action": "action"},
            error="Action failed",
            completed_steps=[],
            remaining_steps=[],
            original_intent=intent,
            request_id="test_request_001",
            context=context,
            vision_data=None,
        )

        # Verify reasoner was called
        self.assertTrue(mock_reasoner.replan.called)

        # Get the execution_context passed to replan
        call_args = mock_reasoner.replan.call_args
        execution_context = call_args[1]["execution_context"]

        # Verify vision data keys are not in context
        self.assertNotIn("vision_verification", execution_context)
        self.assertNotIn("visual_state", execution_context)


if __name__ == "__main__":
    unittest.main()
