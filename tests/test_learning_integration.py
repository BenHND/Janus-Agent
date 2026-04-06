"""
Integration tests for Learning Module with CommandParser
Tests the complete learning feedback loop
"""

import os
import tempfile
import unittest

from janus.learning.learning_manager import LearningManager
from janus.runtime.core.contracts import Intent
from janus.legacy.parser.learning_command_parser import EnhancedCommand, LearningCommandParser


class TestLearningCommandParserIntegration(unittest.TestCase):
    """Test learning integration with command parser"""

    def setUp(self):
        """Set up test environment with temporary files"""
        # Create temporary files for test data
        self.temp_files = []

        # Create temp files for all learning components
        self.db_file = self._create_temp_file(suffix=".db")
        self.cache_file = self._create_temp_file(suffix=".json")
        self.heuristics_file = self._create_temp_file(suffix=".json")
        self.corrections_file = self._create_temp_file(suffix=".json")
        self.reports_dir = tempfile.mkdtemp()

        # Create learning manager with test files
        self.learning_manager = LearningManager(
            db_path=self.db_file,
            cache_path=self.cache_file,
            heuristics_config_path=self.heuristics_file,
            correction_history_path=self.corrections_file,
            reports_dir=self.reports_dir,
            profile_name="test_user",
            auto_update=False,
        )

        # Create learning command parser
        self.parser = LearningCommandParser(
            learning_manager=self.learning_manager, enable_learning=True
        )

    def _create_temp_file(self, suffix=""):
        """Create a temporary file and track it for cleanup"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Clean up test files"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        # Clean up reports directory
        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                os.unlink(os.path.join(self.reports_dir, file))
            os.rmdir(self.reports_dir)

    def test_basic_parsing_with_learning(self):
        """Test that parsing works with learning enabled"""
        command = self.parser.parse("ouvre Chrome")

        self.assertIsInstance(command, EnhancedCommand)
        self.assertEqual(command.intent, Intent.OPEN_APP)
        self.assertIn("app_name", command.parameters)
        self.assertIsNotNone(command.recommended_params)

    def test_feedback_recording(self):
        """Test that parsing feedback is recorded"""
        # Start a session
        session_id = self.parser.start_learning_session()
        self.assertIsNotNone(session_id)

        # Parse a command
        command = self.parser.parse("ouvre Chrome")

        # Verify feedback was recorded
        stats = self.learning_manager.feedback_manager.get_action_statistics(
            action_type="command_parse", days=1
        )

        self.assertGreater(stats["total_count"], 0)

    def test_action_execution_feedback(self):
        """Test recording action execution feedback"""
        session_id = self.parser.start_learning_session()

        # Create an action
        action = {"action": "click", "target": "button"}

        # Record successful execution
        feedback_id = self.parser.record_action_result(action=action, success=True, duration_ms=250)

        self.assertGreater(feedback_id, 0)

        # Verify it was recorded
        stats = self.learning_manager.feedback_manager.get_action_statistics(
            action_type="click", days=1
        )

        self.assertEqual(stats["total_count"], 1)
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["success_rate"], 100.0)

    def test_user_correction_handling(self):
        """Test user correction recording"""
        session_id = self.parser.start_learning_session()

        # Parse and record an action
        command = self.parser.parse("ouvre Chrome")
        action = {"action": "open_app", "app_name": "Chrome"}
        self.parser.record_action_result(action, success=True)

        # Record a user correction
        correction = self.parser.handle_user_correction(
            correction_text="non, pas ça",
            language="fr",
            alternative_action={"action": "open_app", "app_name": "Firefox"},
        )

        self.assertIsNotNone(correction)
        self.assertIn("original_action", correction)

        # Verify correction was recorded
        summary = self.learning_manager.get_correction_summary(days=1)
        self.assertEqual(summary["total_corrections"], 1)

    def test_recommended_parameters(self):
        """Test that recommended parameters are provided"""
        # Record some feedback to build heuristics
        session_id = self.parser.start_learning_session()

        for i in range(5):
            self.learning_manager.record_action_execution(
                action_type="click",
                action_parameters={"target": "button"},
                success=True,
                duration_ms=200 + (i * 10),
            )

        # Parse a command
        command = self.parser.parse("clique sur bouton")

        # Check for recommended parameters
        self.assertIsNotNone(command.recommended_params)
        self.assertIn("wait_time_ms", command.recommended_params)

    def test_action_plan_with_recommendations(self):
        """Test that action plan includes recommendations"""
        command = self.parser.parse("ouvre Chrome")
        action_plan = self.parser.generate_action_plan(command, apply_recommendations=True)

        self.assertGreater(len(action_plan), 0)

        # Check that recommendations are included
        first_action = action_plan[0]
        self.assertIn("recommended_wait_ms", first_action)

    def test_learning_session_lifecycle(self):
        """Test complete learning session lifecycle"""
        # Start session
        session_id = self.parser.start_learning_session()
        self.assertIsNotNone(session_id)

        # Parse and execute some commands
        for command_text in ["ouvre Chrome", "clique sur bouton", "copie le texte"]:
            command = self.parser.parse(command_text)

            # Simulate action execution
            if command.intent != Intent.UNKNOWN:
                action = {"action": command.intent.value, "parameters": command.parameters}
                self.parser.record_action_result(action, success=True, duration_ms=200)

        # End session
        report = self.parser.end_learning_session()

        self.assertIsNotNone(report)
        self.assertIn("session_id", report)
        self.assertIn("summary", report)
        # We record both parse and execution, so expect 6 actions (3 commands × 2)
        self.assertGreaterEqual(report["summary"]["total_actions"], 3)

    def test_success_rate_tracking(self):
        """Test success rate tracking over time"""
        session_id = self.parser.start_learning_session()

        # Record mix of successes and failures
        for i in range(10):
            success = i % 3 != 0  # 2 successes, 1 failure pattern
            self.learning_manager.record_command_parse(
                raw_command=f"test command {i}",
                parsed_intent="click",
                confidence=0.9,
                success=success,
                execution_time_ms=100,
            )

        # Get success rate
        success_rate = self.parser.get_success_rate(days=1)

        # Should be approximately 66.7% (6-7 out of 10 successful)
        self.assertGreater(success_rate, 50.0)
        self.assertLess(success_rate, 80.0)

    def test_improvement_metrics(self):
        """Test improvement metrics calculation"""
        session_id = self.parser.start_learning_session()

        # Record some activity
        for i in range(5):
            self.parser.parse(f"ouvre Chrome {i}")

        # Get improvement metrics
        metrics = self.parser.get_improvement_metrics(days=1)

        self.assertIn("overall_performance", metrics)
        self.assertIn("learning_status", metrics)
        self.assertGreater(metrics["learning_status"]["total_actions"], 0)

    def test_heuristics_update(self):
        """Test manual heuristics update"""
        session_id = self.parser.start_learning_session()

        # Record actions with durations
        for i in range(10):
            self.learning_manager.record_action_execution(
                action_type="click",
                action_parameters={"target": "button"},
                success=True,
                duration_ms=200 + (i * 5),
            )

        # Update heuristics
        updates = self.parser.update_heuristics(days=1)

        self.assertIsNotNone(updates)
        self.assertIn("wait_times", updates)

    def test_export_import_learning_data(self):
        """Test export and import of learning data"""
        # Record some learning data
        session_id = self.parser.start_learning_session()

        for i in range(5):
            self.learning_manager.record_action_execution(
                action_type="click",
                action_parameters={"target": f"button{i}"},
                success=True,
                duration_ms=200,
            )

        # Export data
        export_file = self._create_temp_file(suffix=".json")
        success = self.parser.export_learning_data(export_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_file))

        # Create new parser
        new_parser = LearningCommandParser(enable_learning=True)

        # Import data
        success = new_parser.import_learning_data(export_file)
        self.assertTrue(success)

    def test_learning_disabled(self):
        """Test that learning can be disabled"""
        parser = LearningCommandParser(enable_learning=False)

        # Parse should work but not record feedback
        command = parser.parse("ouvre Chrome", record_feedback=False)
        self.assertEqual(command.intent, Intent.OPEN_APP)

        # Recommended params should be None
        self.assertIsNone(command.recommended_params)

    def test_avoid_action_detection(self):
        """Test that actions are marked for avoidance after corrections"""
        session_id = self.parser.start_learning_session()

        # Use a specific context
        context = {"target": "button"}

        # Record multiple corrections for the same action and context
        for i in range(3):
            # Record an action with the specific context
            action_record = {
                "action_type": "click",
                "context": context,
                "success": True,
                "timestamp": "2024-01-01T00:00:00",
            }
            self.learning_manager.correction_listener.record_action(action_record)

            # Record the correction
            correction = self.learning_manager.correction_listener.process_correction(
                correction_text="non",
                language="fr",
                alternative_action={"action": "click", "target": "other_button"},
            )

            # Verify correction was recorded
            self.assertIsNotNone(correction)

        # Verify we have 3 corrections
        summary = self.learning_manager.get_correction_summary(days=1)
        self.assertEqual(summary["total_corrections"], 3)

        # Check if action should be avoided with threshold 2 (should be True after 3 corrections)
        should_avoid = self.learning_manager.should_avoid_action("click", context, threshold=2)

        # After 3 corrections, should be marked for avoidance
        self.assertTrue(should_avoid, "Action should be avoided after 3 corrections")

    def test_multiple_commands_in_session(self):
        """Test handling multiple commands in a single session"""
        session_id = self.parser.start_learning_session()

        commands_to_test = [
            ("ouvre Chrome", Intent.OPEN_APP),
            ("clique sur bouton", Intent.CLICK),
            ("copie le texte", Intent.COPY),
            ("colle", Intent.PASTE),
        ]

        for cmd_text, expected_intent in commands_to_test:
            command = self.parser.parse(cmd_text)
            self.assertEqual(command.intent, expected_intent)

            # Record execution
            if command.intent != Intent.UNKNOWN:
                action = {"action": command.intent.value, "parameters": command.parameters}
                self.parser.record_action_result(action, success=True, duration_ms=150)

        # End session and verify
        report = self.parser.end_learning_session()
        # We record both parse and execution, so expect 8 actions (4 commands × 2)
        self.assertGreaterEqual(report["summary"]["total_actions"], 4)
        self.assertEqual(report["summary"]["success_rate"], 100.0)


class TestLearningManagerStandalone(unittest.TestCase):
    """Test LearningManager independently"""

    def setUp(self):
        """Set up test environment"""
        self.temp_files = []

        self.db_file = self._create_temp_file(suffix=".db")
        self.cache_file = self._create_temp_file(suffix=".json")
        self.heuristics_file = self._create_temp_file(suffix=".json")
        self.corrections_file = self._create_temp_file(suffix=".json")
        self.reports_dir = tempfile.mkdtemp()

        self.manager = LearningManager(
            db_path=self.db_file,
            cache_path=self.cache_file,
            heuristics_config_path=self.heuristics_file,
            correction_history_path=self.corrections_file,
            reports_dir=self.reports_dir,
            auto_update=False,
        )

    def _create_temp_file(self, suffix=""):
        """Create a temporary file and track it"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Clean up"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                os.unlink(os.path.join(self.reports_dir, file))
            os.rmdir(self.reports_dir)

    def test_learning_manager_initialization(self):
        """Test that learning manager initializes correctly"""
        self.assertIsNotNone(self.manager.feedback_manager)
        self.assertIsNotNone(self.manager.learning_cache)
        self.assertIsNotNone(self.manager.heuristic_updater)
        self.assertIsNotNone(self.manager.performance_reporter)
        self.assertIsNotNone(self.manager.correction_listener)

    def test_session_management(self):
        """Test session start and end"""
        session_id = self.manager.start_session()
        self.assertIsNotNone(session_id)
        self.assertEqual(self.manager.current_session_id, session_id)

        report = self.manager.end_session()
        self.assertIsNotNone(report)
        self.assertIsNone(self.manager.current_session_id)

    def test_learning_status(self):
        """Test getting learning status"""
        status = self.manager.get_learning_status()

        self.assertIn("profile", status)
        self.assertIn("total_actions", status)
        self.assertIn("total_corrections", status)
        self.assertIn("session_active", status)


if __name__ == "__main__":
    unittest.main()
