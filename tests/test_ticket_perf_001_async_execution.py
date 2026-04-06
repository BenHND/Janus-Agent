"""
Tests for TICKET-PERF-001: Asynchronous Optimistic Execution

Tests the new blocking flag and parallel execution of non-blocking steps.
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3, StepGroup


class TestStepGrouping(unittest.TestCase):
    """Test step grouping for parallel execution"""

    def setUp(self):
        self.engine = ExecutionEngineV3(
            agent_registry=AgentRegistry(),
            enable_context_validation=False,
        )

    def test_all_blocking_steps(self):
        """Test that all blocking steps are in separate groups"""
        steps = [
            {"module": "system", "action": "open_app1", "blocking": True},
            {"module": "system", "action": "open_app2", "blocking": True},
            {"module": "system", "action": "open_app3", "blocking": True},
        ]
        
        groups = self.engine._group_steps_for_parallel_execution(steps)
        
        # Should have 3 groups, each with 1 step
        self.assertEqual(len(groups), 3)
        for group in groups:
            self.assertEqual(len(group.steps), 1)
            self.assertTrue(group.is_blocking)

    def test_all_non_blocking_steps(self):
        """Test that all non-blocking steps are in one group"""
        steps = [
            {"module": "system", "action": "open_calc", "blocking": False},
            {"module": "system", "action": "open_notepad", "blocking": False},
            {"module": "system", "action": "open_chrome", "blocking": False},
        ]
        
        groups = self.engine._group_steps_for_parallel_execution(steps)
        
        # Should have 1 group with all 3 steps
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].steps), 3)
        self.assertFalse(groups[0].is_blocking)

    def test_mixed_blocking_steps(self):
        """Test mixed blocking and non-blocking steps"""
        steps = [
            {"module": "system", "action": "open_calc", "blocking": False},
            {"module": "system", "action": "open_notepad", "blocking": False},
            {"module": "system", "action": "wait_load", "blocking": True},
            {"module": "system", "action": "open_chrome", "blocking": False},
        ]
        
        groups = self.engine._group_steps_for_parallel_execution(steps)
        
        # Should have 3 groups:
        # 1. Non-blocking: [open_calc, open_notepad]
        # 2. Blocking: [wait_load]
        # 3. Non-blocking: [open_chrome]
        self.assertEqual(len(groups), 3)
        
        # First group: 2 non-blocking steps
        self.assertEqual(len(groups[0].steps), 2)
        self.assertFalse(groups[0].is_blocking)
        self.assertEqual(groups[0].steps[0][1]["action"], "open_calc")
        self.assertEqual(groups[0].steps[1][1]["action"], "open_notepad")
        
        # Second group: 1 blocking step
        self.assertEqual(len(groups[1].steps), 1)
        self.assertTrue(groups[1].is_blocking)
        self.assertEqual(groups[1].steps[0][1]["action"], "wait_load")
        
        # Third group: 1 non-blocking step
        self.assertEqual(len(groups[2].steps), 1)
        self.assertFalse(groups[2].is_blocking)
        self.assertEqual(groups[2].steps[0][1]["action"], "open_chrome")

    def test_default_blocking_behavior(self):
        """Test that steps without blocking flag default to blocking=True"""
        steps = [
            {"module": "system", "action": "open_app"},  # No blocking flag
        ]
        
        groups = self.engine._group_steps_for_parallel_execution(steps)
        
        # Should be treated as blocking by default
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0].is_blocking)

    def test_empty_steps(self):
        """Test grouping with empty steps list"""
        steps = []
        
        groups = self.engine._group_steps_for_parallel_execution(steps)
        
        self.assertEqual(len(groups), 0)


class TestParallelExecution(unittest.TestCase):
    """Test parallel execution of non-blocking steps"""

    def setUp(self):
        # Create mock registry with mock agent
        self.registry = AgentRegistry()
        self.mock_agent = MagicMock()
        self.mock_agent.__class__.__name__ = "MockAgent"
        
        # Track execution order and timing
        self.execution_log = []
        
        def mock_execute(action, args, context=None):
            """Mock execution that logs calls and simulates delay
            
            Note: Using time.sleep() here is intentional. The agent's execute()
            method is synchronous and runs in a thread pool via run_in_executor().
            This simulates real blocking I/O operations that would happen during
            actual execution (e.g., launching apps, file operations).
            """
            self.execution_log.append({
                "action": action,
                "time": time.time(),
            })
            # Simulate slow operation (100ms) - this is blocking I/O
            time.sleep(0.1)
            return {
                "status": "success",
                "message": f"Executed {action}",
            }
        
        self.mock_agent.execute.side_effect = mock_execute
        self.registry.register("system", self.mock_agent)
        
        # Create execution engine
        self.engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
        )
        
        # Create test intent
        self.intent = Intent(
            action="test_action",
            confidence=1.0,
            raw_command="Test command",
        )

    def test_parallel_execution_of_non_blocking_steps(self):
        """Test that non-blocking steps execute in parallel (faster than sequential)"""
        steps = [
            {"module": "system", "action": "open_calc", "args": {}, "blocking": False},
            {"module": "system", "action": "open_notepad", "args": {}, "blocking": False},
            {"module": "system", "action": "open_chrome", "args": {}, "blocking": False},
        ]
        
        start_time = time.time()
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 3)
        
        # All 3 steps should complete
        self.assertTrue(all(ar.success for ar in result.action_results))
        
        # Verify parallel execution: should take ~100ms (one batch), not 300ms (sequential)
        # Allow some overhead for scheduling, but should be significantly faster
        self.assertLess(elapsed_time, 0.25, 
                       f"Parallel execution took {elapsed_time:.3f}s, expected < 0.25s")
        
        # Verify all actions were executed
        self.assertEqual(len(self.execution_log), 3)
        executed_actions = {log["action"] for log in self.execution_log}
        self.assertEqual(executed_actions, {"open_calc", "open_notepad", "open_chrome"})
        
        # Verify approximate simultaneity (all should start within 50ms of each other)
        times = [log["time"] for log in self.execution_log]
        time_spread = max(times) - min(times)
        self.assertLess(time_spread, 0.05, 
                       f"Steps started {time_spread:.3f}s apart, expected < 0.05s")

    def test_blocking_steps_execute_sequentially(self):
        """Test that blocking steps execute one at a time"""
        steps = [
            {"module": "system", "action": "step1", "args": {}, "blocking": True},
            {"module": "system", "action": "step2", "args": {}, "blocking": True},
        ]
        
        start_time = time.time()
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 2)
        
        # Verify sequential execution: should take ~200ms (two batches)
        self.assertGreaterEqual(elapsed_time, 0.2, 
                               f"Sequential execution took {elapsed_time:.3f}s, expected >= 0.2s")

    def test_mixed_execution(self):
        """Test mixed blocking and non-blocking execution"""
        steps = [
            {"module": "system", "action": "open_calc", "args": {}, "blocking": False},
            {"module": "system", "action": "open_notepad", "args": {}, "blocking": False},
            {"module": "system", "action": "wait", "args": {}, "blocking": True},
            {"module": "system", "action": "open_chrome", "args": {}, "blocking": False},
        ]
        
        start_time = time.time()
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 4)
        
        # Expected: ~100ms (parallel: calc+notepad) + ~100ms (blocking: wait) + ~100ms (non-blocking: chrome)
        # Total: ~300ms (3 batches)
        self.assertLess(elapsed_time, 0.4, 
                       f"Mixed execution took {elapsed_time:.3f}s, expected < 0.4s")

    def test_mock_execution_with_parallel_steps(self):
        """Test that mock execution also works with parallel steps"""
        steps = [
            {"module": "system", "action": "open_calc", "args": {}, "blocking": False},
            {"module": "system", "action": "open_notepad", "args": {}, "blocking": False},
        ]
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=True,
        )
        
        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 2)
        self.assertTrue(all(ar.success for ar in result.action_results))
        
        # Mock execution should not call the agent
        self.mock_agent.execute.assert_not_called()


class TestAcceptanceCriteria(unittest.TestCase):
    """Test the specific acceptance criteria from the ticket"""

    def setUp(self):
        # Create mock registry with fast mock agent
        self.registry = AgentRegistry()
        self.mock_agent = MagicMock()
        self.mock_agent.__class__.__name__ = "MockAgent"
        self.mock_agent.execute.return_value = {
            "status": "success",
            "message": "App opened",
        }
        self.registry.register("system", self.mock_agent)
        
        self.engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
        )
        
        self.intent = Intent(
            action="open_apps",
            confidence=1.0,
            raw_command="Ouvre Calc, Notepad et Chrome",
        )

    def test_acceptance_criteria_parallel_app_launch(self):
        """
        Acceptance Criteria: The command "Ouvre Calc, Notepad et Chrome"
        launches the 3 apps quasi-simultaneously, without waiting for the first
        to be fully loaded.
        """
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Calculator"},
                "blocking": False,  # Non-blocking: don't wait for full load
            },
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "TextEdit"},
                "blocking": False,  # Non-blocking: don't wait for full load
            },
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Chrome"},
                "blocking": False,  # Non-blocking: don't wait for full load
            },
        ]
        
        start_time = time.time()
        
        result = self.engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False,
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify success
        self.assertTrue(result.success)
        self.assertEqual(len(result.action_results), 3)
        self.assertTrue(all(ar.success for ar in result.action_results))
        
        # All 3 apps should be launched via agent
        self.assertEqual(self.mock_agent.execute.call_count, 3)
        
        # Verify they were executed as a single parallel group
        groups = self.engine._group_steps_for_parallel_execution(steps)
        self.assertEqual(len(groups), 1, "Should be one parallel group")
        self.assertEqual(len(groups[0].steps), 3, "Group should have all 3 steps")
        self.assertFalse(groups[0].is_blocking, "Group should be non-blocking")


if __name__ == "__main__":
    unittest.main()
