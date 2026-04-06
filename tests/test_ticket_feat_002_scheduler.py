"""
Unit tests for TICKET-FEAT-002: Scheduler & Actions Différées (Cron)

Tests the core TaskScheduler functionality including:
- Task scheduling (one-time and recurring)
- Task persistence
- Task execution
- Task cancellation
"""

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

from janus.runtime.core.scheduler import TaskScheduler, TaskStatus, TaskType, ScheduledTask


class TestTaskScheduler(unittest.TestCase):
    """Test TaskScheduler functionality"""
    
    def setUp(self):
        """Set up test scheduler"""
        # Use in-memory scheduler (no database)
        self.scheduler = TaskScheduler(db_connection=None)
    
    def tearDown(self):
        """Clean up scheduler"""
        if self.scheduler and self.scheduler._running:
            self.scheduler.stop()
    
    def test_scheduler_initialization(self):
        """Test that scheduler initializes correctly"""
        self.assertIsNotNone(self.scheduler)
        self.assertFalse(self.scheduler._running)
        self.assertEqual(len(self.scheduler._tasks), 0)
    
    def test_scheduler_start_stop(self):
        """Test starting and stopping the scheduler"""
        # Start scheduler
        self.scheduler.start()
        self.assertTrue(self.scheduler._running)
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Stop scheduler
        self.scheduler.stop()
        self.assertFalse(self.scheduler._running)
    
    def test_schedule_one_time_task(self):
        """Test scheduling a one-time task"""
        task_id = "test_task_1"
        delay_seconds = 5
        message = "Test reminder"
        
        task = self.scheduler.schedule_task(
            task_id=task_id,
            command="Remind me to test",
            action={"type": "tts_notification", "message": message},
            delay_seconds=delay_seconds
        )
        
        # Verify task was created
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, task_id)
        self.assertEqual(task.task_type, TaskType.ONE_TIME)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.action["message"], message)
        
        # Verify task is in scheduler
        self.assertIn(task_id, self.scheduler._tasks)
        
        # Verify next run time is approximately correct
        expected_time = datetime.now() + timedelta(seconds=delay_seconds)
        time_diff = abs((task.next_run - expected_time).total_seconds())
        self.assertLess(time_diff, 2, "Next run time should be within 2 seconds of expected")
    
    def test_schedule_recurring_task(self):
        """Test scheduling a recurring task"""
        task_id = "test_recurring_1"
        schedule_expression = "every 1 hour"
        message = "Hourly reminder"
        
        task = self.scheduler.schedule_task(
            task_id=task_id,
            command="Remind me every hour",
            action={"type": "tts_notification", "message": message},
            schedule_expression=schedule_expression
        )
        
        # Verify task was created
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, task_id)
        self.assertEqual(task.task_type, TaskType.RECURRING)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.schedule_expression, schedule_expression)
    
    def test_cancel_task(self):
        """Test cancelling a scheduled task"""
        task_id = "test_cancel_1"
        
        # Schedule a task
        task = self.scheduler.schedule_task(
            task_id=task_id,
            command="Test command",
            action={"type": "tts_notification", "message": "Test"},
            delay_seconds=300  # 5 minutes
        )
        
        # Verify task exists
        self.assertIn(task_id, self.scheduler._tasks)
        
        # Cancel task
        success = self.scheduler.cancel_task(task_id)
        
        # Verify cancellation
        self.assertTrue(success)
        cancelled_task = self.scheduler.get_task(task_id)
        self.assertEqual(cancelled_task.status, TaskStatus.CANCELLED)
    
    def test_get_pending_tasks(self):
        """Test retrieving pending tasks"""
        # Schedule multiple tasks
        self.scheduler.schedule_task(
            task_id="task1",
            command="Task 1",
            action={"type": "tts_notification", "message": "Task 1"},
            delay_seconds=10
        )
        
        self.scheduler.schedule_task(
            task_id="task2",
            command="Task 2",
            action={"type": "tts_notification", "message": "Task 2"},
            delay_seconds=20
        )
        
        # Get pending tasks
        pending = self.scheduler.get_pending_tasks()
        
        # Verify
        self.assertEqual(len(pending), 2)
        self.assertTrue(all(t.status == TaskStatus.PENDING for t in pending))
    
    def test_task_serialization(self):
        """Test task serialization to dictionary"""
        task = ScheduledTask(
            task_id="test_serialize",
            task_type=TaskType.ONE_TIME,
            command="Test command",
            action={"type": "tts_notification", "message": "Test"},
            schedule_time=datetime.now() + timedelta(seconds=60),
            status=TaskStatus.PENDING
        )
        
        # Serialize to dict
        task_dict = task.to_dict()
        
        # Verify serialization
        self.assertIsInstance(task_dict, dict)
        self.assertEqual(task_dict["task_id"], "test_serialize")
        self.assertEqual(task_dict["task_type"], "one_time")
        self.assertEqual(task_dict["status"], "pending")
        self.assertEqual(task_dict["command"], "Test command")
    
    def test_invalid_schedule_parameters(self):
        """Test that invalid parameters raise appropriate errors"""
        with self.assertRaises(ValueError):
            # Missing both delay_seconds and schedule_expression
            self.scheduler.schedule_task(
                task_id="invalid_task",
                command="Test",
                action={"type": "tts_notification", "message": "Test"}
            )
    
    def test_schedule_expression_parsing(self):
        """Test schedule expression parsing"""
        # Test "every N minutes"
        job = self.scheduler._parse_schedule_expression("5 minutes")
        self.assertIsNotNone(job)
        
        # Test "every hour"
        job = self.scheduler._parse_schedule_expression("1 hour")
        self.assertIsNotNone(job)
        
        # Test "every day at HH:MM"
        job = self.scheduler._parse_schedule_expression("day at 10:30")
        self.assertIsNotNone(job)
        
        # Test "WEEKDAY at HH:MM"
        job = self.scheduler._parse_schedule_expression("friday at 17:00")
        self.assertIsNotNone(job)


class TestSchedulerAgent(unittest.TestCase):
    """Test SchedulerAgent functionality"""
    
    def setUp(self):
        """Set up test agent"""
        from janus.capabilities.agents.scheduler_agent import SchedulerAgent
        from janus.services.lifecycle_service import LifecycleService
        from janus.runtime.core.settings import Settings
        from janus.runtime.core.memory_engine import MemoryEngine
        
        # Create mock dependencies
        self.settings = Settings()
        self.memory = MemoryEngine(db_path=":memory:")
        self.lifecycle_service = LifecycleService(
            settings=self.settings,
            memory=self.memory,
            session_id="test_session"
        )
        
        # Initialize scheduler
        self.lifecycle_service.start_task_scheduler()
        
        # Create agent
        self.agent = SchedulerAgent(lifecycle_service=self.lifecycle_service)
    
    def tearDown(self):
        """Clean up"""
        if self.lifecycle_service:
            self.lifecycle_service.stop_task_scheduler()
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.module_name, "scheduler")
    
    def test_schedule_task_action(self):
        """Test schedule_task action execution"""
        import asyncio
        
        # Prepare arguments
        args = {
            "delay_seconds": 10,
            "message": "Test reminder"
        }
        
        context = {
            "user_goal": "Remind me in 10 seconds"
        }
        
        # Execute action
        result = asyncio.run(self.agent.execute("schedule_task", args, context))
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIn("task_id", result)
        self.assertIn("message", result)
    
    def test_cancel_task_action(self):
        """Test cancel_task action execution"""
        import asyncio
        
        # First, schedule a task
        schedule_args = {
            "delay_seconds": 300,
            "message": "Test"
        }
        
        schedule_result = asyncio.run(
            self.agent.execute("schedule_task", schedule_args, {"user_goal": "Test"})
        )
        
        task_id = schedule_result["task_id"]
        
        # Now cancel it
        cancel_args = {
            "task_id": task_id
        }
        
        cancel_result = asyncio.run(
            self.agent.execute("cancel_task", cancel_args, {})
        )
        
        # Verify cancellation
        self.assertTrue(cancel_result["success"])
    
    def test_list_tasks_action(self):
        """Test list_tasks action execution"""
        import asyncio
        
        # Schedule a few tasks
        for i in range(3):
            args = {
                "delay_seconds": 60 + i * 10,
                "message": f"Test {i}"
            }
            asyncio.run(
                self.agent.execute("schedule_task", args, {"user_goal": f"Test {i}"})
            )
        
        # List tasks
        result = asyncio.run(self.agent.execute("list_tasks", {}, {}))
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIn("tasks", result)
        self.assertEqual(result["count"], 3)


if __name__ == "__main__":
    unittest.main()
