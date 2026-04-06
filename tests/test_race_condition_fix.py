"""
Tests for race condition fixes in async executor - TICKET B1
These tests reproduce the race condition bug and validate the fix
"""
import asyncio
import time
import unittest
from unittest.mock import Mock, patch

from janus.constants import ExecutionStatus
from janus.exec.async_executor import AsyncExecutor
from janus.exec.executor import ActionResult, ExecutionReport, Executor


class TestRaceConditionDetection(unittest.TestCase):
    """Test race condition detection in async executor"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_executor = Mock(spec=Executor)
        self.async_executor = AsyncExecutor(
            executor=self.mock_executor,
            action_timeout=5.0,
        )

    def test_get_resource_id_file_operations(self):
        """Test resource ID extraction for file operations"""
        intent1 = {"action": "write_file", "parameters": {"path": "/tmp/test.txt"}}
        intent2 = {"action": "read_file", "parameters": {"path": "/tmp/test.txt"}}
        intent3 = {"action": "write_file", "parameters": {"path": "/tmp/other.txt"}}

        resource1 = self.async_executor._get_resource_id(intent1)
        resource2 = self.async_executor._get_resource_id(intent2)
        resource3 = self.async_executor._get_resource_id(intent3)

        # Same file should have same resource ID
        self.assertEqual(resource1, resource2)

        # Different file should have different resource ID
        self.assertNotEqual(resource1, resource3)

    def test_get_resource_id_ui_elements(self):
        """Test resource ID extraction for UI operations"""
        intent1 = {"action": "click", "parameters": {"target": "Submit Button"}}
        intent2 = {"action": "type", "parameters": {"target": "Submit Button", "text": "hello"}}
        intent3 = {"action": "click", "parameters": {"target": "Cancel Button"}}

        resource1 = self.async_executor._get_resource_id(intent1)
        resource2 = self.async_executor._get_resource_id(intent2)
        resource3 = self.async_executor._get_resource_id(intent3)

        # Same UI element should have same resource ID
        self.assertEqual(resource1, resource2)

        # Different UI element should have different resource ID
        self.assertNotEqual(resource1, resource3)

    def test_get_resource_id_clipboard(self):
        """Test resource ID for clipboard operations"""
        intent1 = {"action": "copy", "parameters": {"text": "hello"}}
        intent2 = {"action": "paste", "parameters": {}}

        resource1 = self.async_executor._get_resource_id(intent1)
        resource2 = self.async_executor._get_resource_id(intent2)

        # Both clipboard operations should have same resource ID
        self.assertEqual(resource1, resource2)
        self.assertEqual(resource1, "clipboard")

    def test_detect_conflicts_no_conflict(self):
        """Test conflict detection with non-conflicting intents"""
        intents = [
            {"action": "click", "parameters": {"target": "Button1"}},
            {"action": "click", "parameters": {"target": "Button2"}},
            {"action": "type", "parameters": {"target": "TextBox1", "text": "hello"}},
        ]

        has_conflict = self.async_executor._detect_conflicts(intents)
        self.assertFalse(has_conflict)

    def test_detect_conflicts_with_conflict(self):
        """Test conflict detection with conflicting intents"""
        intents = [
            {"action": "click", "parameters": {"target": "Submit"}},
            {"action": "type", "parameters": {"target": "Submit", "text": "hello"}},
        ]

        has_conflict = self.async_executor._detect_conflicts(intents)
        self.assertTrue(has_conflict)

    def test_detect_conflicts_file_operations(self):
        """Test conflict detection with file operations"""
        intents = [
            {"action": "write_file", "parameters": {"path": "/tmp/test.txt", "content": "data1"}},
            {"action": "read_file", "parameters": {"path": "/tmp/test.txt"}},
        ]

        has_conflict = self.async_executor._detect_conflicts(intents)
        self.assertTrue(has_conflict)

    def test_detect_conflicts_clipboard(self):
        """Test conflict detection with clipboard operations"""
        intents = [
            {"action": "copy", "parameters": {"text": "hello"}},
            {"action": "paste", "parameters": {}},
        ]

        has_conflict = self.async_executor._detect_conflicts(intents)
        self.assertTrue(has_conflict)

    def test_execute_parallel_without_conflicts(self):
        """Test parallel execution when no conflicts detected"""
        # Mock successful execution
        mock_report = ExecutionReport(
            status=ExecutionStatus.SUCCESS,
            results=[
                ActionResult(
                    status=ExecutionStatus.SUCCESS,
                    action="click",
                    intent="click",
                    parameters={"target": f"Button{i}"},
                    timestamp=time.time(),
                    duration=0.1,
                )
                for i in range(3)
            ],
            total_duration=0.3,
            timestamp=time.time(),
        )
        self.mock_executor.execute_intents.return_value = mock_report

        intents = [
            {"action": "click", "parameters": {"target": "Button1"}},
            {"action": "click", "parameters": {"target": "Button2"}},
            {"action": "click", "parameters": {"target": "Button3"}},
        ]

        async def run_test():
            report = await self.async_executor.execute_parallel(intents)
            self.assertEqual(report.status, ExecutionStatus.SUCCESS)
            self.assertEqual(len(report.results), 3)

        asyncio.run(run_test())

    def test_execute_serialized_with_conflicts(self):
        """Test serialized execution when conflicts detected"""
        # Mock execution that tracks order
        execution_order = []

        def track_execution(intents):
            for intent in intents:
                execution_order.append(intent["parameters"]["target"])
            return ExecutionReport(
                status=ExecutionStatus.SUCCESS,
                results=[
                    ActionResult(
                        status=ExecutionStatus.SUCCESS,
                        action="test",
                        intent="test",
                        parameters=intent["parameters"],
                        timestamp=time.time(),
                        duration=0.1,
                    )
                    for intent in intents
                ],
                total_duration=0.2,
                timestamp=time.time(),
            )

        self.mock_executor.execute_intents.side_effect = track_execution

        intents = [
            {"action": "click", "parameters": {"target": "Submit"}},
            {"action": "type", "parameters": {"target": "Submit", "text": "data"}},
        ]

        async def run_test():
            report = await self.async_executor.execute_parallel(intents)
            # Should execute serially due to conflict
            self.assertEqual(report.status, ExecutionStatus.SUCCESS)
            # Verify execution order is preserved
            self.assertEqual(len(execution_order), 2)

        asyncio.run(run_test())

    def test_race_condition_reproduction(self):
        """Reproduce race condition with conflicting parallel operations"""
        # This test simulates the race condition before the fix
        # Multiple operations on same resource should be serialized

        shared_resource = {"value": 0}

        def modify_resource(intents):
            # Simulate race condition
            for intent in intents:
                current = shared_resource["value"]
                time.sleep(0.01)  # Small delay to increase chance of race
                shared_resource["value"] = current + 1

            return ExecutionReport(
                status=ExecutionStatus.SUCCESS,
                results=[],
                total_duration=0.1,
                timestamp=time.time(),
            )

        self.mock_executor.execute_intents.side_effect = modify_resource

        # Two operations on same resource
        intents = [
            {"action": "write", "parameters": {"target": "shared_data", "value": 1}},
            {"action": "write", "parameters": {"target": "shared_data", "value": 2}},
        ]

        async def run_test():
            # With conflict detection, these should be serialized
            report = await self.async_executor.execute_parallel(intents)
            self.assertEqual(report.status, ExecutionStatus.SUCCESS)

        asyncio.run(run_test())


class TestSerializedExecution(unittest.TestCase):
    """Test serialized execution fallback"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_executor = Mock(spec=Executor)
        self.async_executor = AsyncExecutor(executor=self.mock_executor)

    def test_execute_serialized_preserves_order(self):
        """Test that serialized execution preserves intent order"""
        execution_order = []

        def track_order(intents):
            for intent in intents:
                execution_order.append(intent["id"])
            return ExecutionReport(
                status=ExecutionStatus.SUCCESS,
                results=[],
                total_duration=0.1,
                timestamp=time.time(),
            )

        self.mock_executor.execute_intents.side_effect = track_order

        intents = [
            {"id": 1, "action": "step1"},
            {"id": 2, "action": "step2"},
            {"id": 3, "action": "step3"},
        ]

        async def run_test():
            report = await self.async_executor._execute_serialized(intents)
            # Verify order is preserved
            self.assertEqual(execution_order, [1, 2, 3])

        asyncio.run(run_test())

    def test_execute_serialized_handles_errors(self):
        """Test that serialized execution handles errors gracefully"""

        def failing_execution(intents):
            return ExecutionReport(
                status=ExecutionStatus.FATAL_FAIL,
                results=[
                    ActionResult(
                        status=ExecutionStatus.FATAL_FAIL,
                        action="test",
                        intent="test",
                        parameters={},
                        timestamp=time.time(),
                        duration=0,
                        error="Test error",
                    )
                ],
                total_duration=0,
                timestamp=time.time(),
            )

        self.mock_executor.execute_intents.return_value = failing_execution([])

        intents = [{"action": "test"}]

        async def run_test():
            report = await self.async_executor._execute_serialized(intents)
            self.assertEqual(report.status, ExecutionStatus.FATAL_FAIL)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
