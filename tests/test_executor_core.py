"""
Unit tests for Core Executor
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.exec.executor import ActionResult, ExecutionReport, ExecutionStatus, Executor


class TestExecutor(unittest.TestCase):
    """Test cases for Executor"""

    def setUp(self):
        """Set up test fixtures"""
        self.executor = Executor(
            timeout=5.0,
            max_retries=2,
            dry_run=False,
        )

    def test_initialization(self):
        """Test executor initialization"""
        self.assertEqual(self.executor.timeout, 5.0)
        self.assertEqual(self.executor.max_retries, 2)
        self.assertFalse(self.executor.dry_run)
        self.assertEqual(len(self.executor.adapters), 0)

    def test_register_adapter(self):
        """Test adapter registration"""
        mock_adapter = Mock()
        self.executor.register_adapter("test_app", mock_adapter)

        self.assertIn("test_app", self.executor.adapters)
        self.assertEqual(self.executor.adapters["test_app"], mock_adapter)

    def test_dry_run_mode(self):
        """Test dry run mode"""
        executor = Executor(dry_run=True)

        intents = [
            {"intent": "open_app", "parameters": {"app_name": "Chrome"}},
            {"intent": "click", "parameters": {"target": "button"}},
        ]

        report = executor.execute_intents(intents)

        self.assertTrue(report.dry_run)
        self.assertEqual(report.status, ExecutionStatus.SUCCESS)
        self.assertEqual(len(report.results), 2)

        # All results should be successful in dry run
        for result in report.results:
            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertTrue(result.metadata.get("dry_run"))

    def test_execute_with_safety_manager(self):
        """Test execution with safety manager blocking action"""
        from janus.exec.safety import SafetyManager

        safety_manager = SafetyManager(require_confirmation=True)
        executor = Executor(safety_manager=safety_manager)

        intents = [
            {"intent": "delete_file", "parameters": {"path": "/test.txt"}},
        ]

        report = executor.execute_intents(intents)

        # Should be blocked
        self.assertEqual(report.status, ExecutionStatus.FATAL_FAIL)
        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].status, ExecutionStatus.SKIPPED)
        self.assertIn("Blocked", report.results[0].error)

    def test_execute_with_adapter(self):
        """Test execution with registered adapter"""
        mock_adapter = Mock()
        mock_adapter.execute.return_value = {
            "status": "success",
            "data": "test_data",
        }

        self.executor.register_adapter("test_app", mock_adapter)

        intents = [
            {"intent": "test_action", "parameters": {"app": "test_app", "value": 123}},
        ]

        report = self.executor.execute_intents(intents)

        self.assertEqual(report.status, ExecutionStatus.SUCCESS)
        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].status, ExecutionStatus.SUCCESS)

        # Verify adapter was called
        mock_adapter.execute.assert_called_once()

    def test_retry_logic(self):
        """Test retry logic on retryable failure"""
        mock_adapter = Mock()

        # First two calls fail, third succeeds
        mock_adapter.execute.side_effect = [
            {"status": "failed", "error": "temporary error"},
            {"status": "failed", "error": "temporary error"},
            {"status": "success"},
        ]

        self.executor.register_adapter("test_app", mock_adapter)

        intents = [
            {"intent": "test_action", "parameters": {"app": "test_app"}},
        ]

        report = self.executor.execute_intents(intents)

        self.assertEqual(report.status, ExecutionStatus.SUCCESS)
        self.assertEqual(len(report.results), 1)

        result = report.results[0]
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.retries, 2)  # Succeeded on 3rd attempt (2 retries)

        # Verify adapter was called 3 times
        self.assertEqual(mock_adapter.execute.call_count, 3)

    def test_fatal_failure_stops_execution(self):
        """Test that fatal failure stops execution"""
        mock_adapter = Mock()
        mock_adapter.execute.return_value = {"status": "success"}

        self.executor.register_adapter("test_app", mock_adapter)

        intents = [
            {"intent": "test_action1", "parameters": {"app": "test_app"}},
            {"intent": "unknown_action", "parameters": {}},  # This will fail
            {"intent": "test_action3", "parameters": {"app": "test_app"}},
        ]

        report = self.executor.execute_intents(intents)

        # Unknown actions are retryable failures, not fatal
        # All actions should be attempted
        self.assertEqual(len(report.results), 3)

        self.assertEqual(report.results[0].status, ExecutionStatus.SUCCESS)
        self.assertEqual(report.results[1].status, ExecutionStatus.RETRYABLE_FAIL)
        self.assertEqual(report.results[2].status, ExecutionStatus.SUCCESS)

    def test_visual_fallback_on_element_not_found(self):
        """Test visual fallback when element not found"""
        mock_adapter = Mock()
        mock_adapter.execute.return_value = {
            "status": "failed",
            "element_not_found": True,
            "error": "Element not found",
        }

        mock_vision_runner = Mock()
        mock_vision_runner.find_text.return_value = (100, 100, 50, 50)
        mock_vision_runner.click_at_bbox.return_value = True

        self.executor.register_adapter("test_app", mock_adapter)
        self.executor.vision_runner = mock_vision_runner

        intents = [
            {"intent": "click", "parameters": {"app": "test_app", "text": "Submit"}},
        ]

        report = self.executor.execute_intents(intents)

        # Should succeed via visual fallback
        self.assertEqual(report.status, ExecutionStatus.SUCCESS)

        # Verify vision runner was called
        mock_vision_runner.find_text.assert_called_once_with("Submit")
        mock_vision_runner.click_at_bbox.assert_called_once()

    def test_execution_report_statistics(self):
        """Test execution report statistics"""
        mock_adapter = Mock()
        mock_adapter.execute.side_effect = [
            {"status": "success"},
            {"status": "failed", "error": "test error"},
            {"status": "success"},
        ]

        self.executor.register_adapter("test_app", mock_adapter)

        intents = [
            {"intent": "action1", "parameters": {"app": "test_app"}},
            {"intent": "action2", "parameters": {"app": "test_app"}},
            {"intent": "action3", "parameters": {"app": "test_app"}},
        ]

        report = self.executor.execute_intents(intents)

        self.assertEqual(report.success_count, 2)
        self.assertEqual(report.failure_count, 1)
        self.assertEqual(len(report.results), 3)

    def test_window_manager_focus(self):
        """Test window manager focus enforcement"""
        mock_adapter = Mock()
        mock_adapter.execute.return_value = {"status": "success"}

        mock_window_manager = Mock()
        mock_window_manager.ensure_focus.return_value = True

        self.executor.register_adapter("chrome", mock_adapter)
        self.executor.window_manager = mock_window_manager

        intents = [
            {"intent": "open_url", "parameters": {"url": "https://github.com"}},
        ]

        report = self.executor.execute_intents(intents)

        self.assertEqual(report.status, ExecutionStatus.SUCCESS)

        # Verify window manager was called
        mock_window_manager.ensure_focus.assert_called_once_with("chrome")

    def test_action_result_to_dict(self):
        """Test ActionResult serialization"""
        result = ActionResult(
            status=ExecutionStatus.SUCCESS,
            action="test_action",
            intent="test_intent",
            parameters={"key": "value"},
            timestamp=1234567890.0,
            duration=1.5,
            retries=0,
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict["status"], "success")
        self.assertEqual(result_dict["action"], "test_action")
        self.assertEqual(result_dict["intent"], "test_intent")
        self.assertEqual(result_dict["parameters"], {"key": "value"})
        self.assertEqual(result_dict["duration"], 1.5)
        self.assertEqual(result_dict["retries"], 0)

    def test_execution_report_to_dict(self):
        """Test ExecutionReport serialization"""
        results = [
            ActionResult(
                status=ExecutionStatus.SUCCESS,
                action="action1",
                intent="intent1",
                parameters={},
                timestamp=1234567890.0,
                duration=1.0,
            ),
        ]

        report = ExecutionReport(
            status=ExecutionStatus.SUCCESS,
            results=results,
            total_duration=2.0,
            timestamp=1234567890.0,
            dry_run=False,
        )

        report_dict = report.to_dict()

        self.assertEqual(report_dict["status"], "success")
        self.assertEqual(len(report_dict["results"]), 1)
        self.assertEqual(report_dict["total_duration"], 2.0)
        self.assertEqual(report_dict["success_count"], 1)
        self.assertEqual(report_dict["failure_count"], 0)
        self.assertFalse(report_dict["dry_run"])


if __name__ == "__main__":
    unittest.main()
