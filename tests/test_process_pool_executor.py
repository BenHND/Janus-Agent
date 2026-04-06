"""
Tests for ProcessPoolExecutor support in ExecutionEngineV3

This test validates that the ExecutionEngineV3 can use ProcessPoolExecutor
for CPU-intensive operations to avoid Python's GIL limitations.
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3


class TestProcessPoolExecutor(unittest.TestCase):
    """Test ProcessPoolExecutor support in ExecutionEngineV3"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_registry = MagicMock(spec=AgentRegistry)

    def tearDown(self):
        """Clean up any executors"""
        # Note: Tests use engine.shutdown() explicitly, 
        # so no global cleanup needed here
        pass

    def test_default_executor_is_threadpool(self):
        """Test that default executor is None (ThreadPoolExecutor)"""
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry
        )
        
        # Default should be None (ThreadPoolExecutor)
        self.assertIsNone(engine._executor)
        self.assertFalse(engine.use_process_pool)
        
        engine.shutdown()

    def test_enable_process_pool_executor(self):
        """Test that ProcessPoolExecutor is created when enabled"""
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        )
        
        # Should have a ProcessPoolExecutor
        self.assertIsNotNone(engine._executor)
        self.assertTrue(engine.use_process_pool)
        
        # Clean up
        engine.shutdown()
        self.assertIsNone(engine._executor)

    def test_process_pool_with_max_workers(self):
        """Test ProcessPoolExecutor with custom max_workers"""
        max_workers = 2
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True,
            max_workers=max_workers
        )
        
        self.assertIsNotNone(engine._executor)
        self.assertTrue(engine.use_process_pool)
        
        # Clean up
        engine.shutdown()

    def test_shutdown_multiple_times(self):
        """Test that shutdown can be called multiple times safely"""
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        )
        
        # First shutdown
        engine.shutdown()
        self.assertIsNone(engine._executor)
        
        # Second shutdown should not raise error
        engine.shutdown()
        self.assertIsNone(engine._executor)

    def test_execution_with_threadpool(self):
        """Test execution with default ThreadPoolExecutor"""
        # Mock the registry to return success
        self.mock_registry.execute.return_value = {
            "status": "success",
            "message": "Action completed"
        }
        
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=False  # Explicit ThreadPool
        )
        
        steps = [
            {
                "module": "system",
                "action": "open_application",
                "args": {"app_name": "Calculator"}
            }
        ]
        
        intent = Intent(
            action="open_app",
            confidence=1.0,
            raw_command="Open calculator"
        )
        
        # Execute synchronously
        result = engine.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Verify execution
        self.assertTrue(result.success)
        self.assertEqual(len(result.results), 1)
        
        # Verify default executor was used (None)
        self.assertIsNone(engine._executor)
        
        engine.shutdown()

    def test_execution_with_processpool(self):
        """Test execution with ProcessPoolExecutor"""
        # Mock the registry to return success
        self.mock_registry.execute.return_value = {
            "status": "success",
            "message": "CPU-intensive action completed"
        }
        
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True,  # Use ProcessPool
            max_workers=2
        )
        
        steps = [
            {
                "module": "data",
                "action": "process_heavy_computation",
                "args": {"data": "large_dataset"}
            }
        ]
        
        intent = Intent(
            action="process_data",
            confidence=1.0,
            raw_command="Process heavy data"
        )
        
        # Execute synchronously
        result = engine.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Verify execution
        self.assertTrue(result.success)
        self.assertEqual(len(result.results), 1)
        
        # Verify ProcessPoolExecutor was used
        self.assertIsNotNone(engine._executor)
        
        engine.shutdown()

    def test_executor_cleanup_on_deletion(self):
        """Test that executor is cleaned up when engine is deleted"""
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        )
        
        # Verify executor exists
        self.assertIsNotNone(engine._executor)
        
        # Delete the engine
        del engine
        
        # Executor should be cleaned up (no way to verify directly,
        # but this tests that __del__ doesn't raise errors)

    def test_concurrent_executions_threadpool(self):
        """Test multiple concurrent executions with ThreadPoolExecutor"""
        call_count = 0
        
        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate work
            return {"status": "success", "message": f"Call {call_count}"}
        
        self.mock_registry.execute.side_effect = mock_execute
        
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=False
        )
        
        steps = [
            {
                "module": "system",
                "action": "task1",
                "args": {},
                "blocking": False
            },
            {
                "module": "system",
                "action": "task2",
                "args": {},
                "blocking": False
            }
        ]
        
        intent = Intent(
            action="parallel_tasks",
            confidence=1.0,
            raw_command="Run parallel tasks"
        )
        
        start_time = time.time()
        result = engine.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        elapsed = time.time() - start_time
        
        # Both tasks should execute
        self.assertTrue(result.success)
        self.assertEqual(len(result.results), 2)
        self.assertEqual(call_count, 2)
        
        # With parallel execution, should be faster than sequential
        # (though with such small work, overhead might dominate)
        
        engine.shutdown()


class TestProcessPoolExecutorAsync(unittest.IsolatedAsyncioTestCase):
    """Async tests for ProcessPoolExecutor support"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_registry = MagicMock(spec=AgentRegistry)

    async def test_async_execution_with_processpool(self):
        """Test async execution with ProcessPoolExecutor"""
        self.mock_registry.execute.return_value = {
            "status": "success",
            "message": "Async CPU-intensive action completed"
        }
        
        engine = ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        )
        
        steps = [
            {
                "module": "data",
                "action": "process_async",
                "args": {"data": "async_data"}
            }
        ]
        
        intent = Intent(
            action="async_process",
            confidence=1.0,
            raw_command="Process data async"
        )
        
        # Execute asynchronously
        result = await engine.execute_plan_async(
            steps=steps,
            intent=intent,
            session_id="test_session",
            request_id="test_request"
        )
        
        # Verify execution
        self.assertTrue(result.success)
        self.assertEqual(len(result.results), 1)
        
        engine.shutdown()


class TestContextManager(unittest.TestCase):
    """Test context manager support for ExecutionEngineV3"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_registry = MagicMock(spec=AgentRegistry)
        self.mock_registry.execute.return_value = {
            "status": "success",
            "message": "Action completed"
        }

    def test_context_manager_basic(self):
        """Test basic context manager usage"""
        with ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        ) as engine:
            # Executor should exist inside context
            self.assertIsNotNone(engine._executor)
        
        # Executor should be cleaned up after exiting context
        self.assertIsNone(engine._executor)

    def test_context_manager_with_execution(self):
        """Test context manager with actual execution"""
        steps = [
            {
                "module": "system",
                "action": "test_action",
                "args": {}
            }
        ]
        
        intent = Intent(
            action="test",
            confidence=1.0,
            raw_command="Test command"
        )
        
        with ExecutionEngineV3(
            agent_registry=self.mock_registry,
            use_process_pool=True
        ) as engine:
            result = engine.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test_session",
                request_id="test_request"
            )
            
            # Verify execution succeeded
            self.assertTrue(result.success)
            self.assertIsNotNone(engine._executor)
        
        # Verify cleanup
        self.assertIsNone(engine._executor)

    def test_context_manager_with_exception(self):
        """Test that context manager cleans up even when exception occurs"""
        engine = None
        try:
            with ExecutionEngineV3(
                agent_registry=self.mock_registry,
                use_process_pool=True
            ) as eng:
                engine = eng
                self.assertIsNotNone(engine._executor)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Even though exception occurred, executor should be cleaned up
        self.assertIsNone(engine._executor)


if __name__ == "__main__":
    unittest.main()
