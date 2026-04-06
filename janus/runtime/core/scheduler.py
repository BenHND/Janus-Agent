"""
Task Scheduler for Janus - TICKET-FEAT-002

This module provides a lightweight task scheduler for delayed and recurring actions.
Supports:
- One-time delayed tasks (e.g., "remind me in 5 minutes")
- Recurring tasks (e.g., "send report every Friday")
- Task persistence in database (survives restarts)
- Task cancellation and management

Uses the 'schedule' library for timing and SQLite for persistence.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import schedule
except ImportError:
    raise ImportError(
        "The 'schedule' library is required for task scheduling. "
        "Install it with: pip install schedule"
    )

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a scheduled task"""
    PENDING = "pending"      # Task is waiting to run
    RUNNING = "running"      # Task is currently executing
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"        # Task failed to execute
    CANCELLED = "cancelled"  # Task was cancelled


class TaskType(Enum):
    """Type of scheduled task"""
    ONE_TIME = "one_time"    # Execute once at a specific time
    RECURRING = "recurring"   # Execute repeatedly on a schedule


class ScheduledTask:
    """
    Represents a scheduled task
    
    Attributes:
        task_id: Unique identifier for the task
        task_type: ONE_TIME or RECURRING
        command: Original command that triggered this task
        action: Action to execute (e.g., TTS message, command)
        schedule_time: When to execute (for one-time tasks)
        schedule_expression: Cron-like expression (for recurring tasks)
        status: Current status of the task
        created_at: When the task was created
        last_run: When the task last executed
        next_run: When the task will next execute
        run_count: Number of times the task has executed
        metadata: Additional task metadata
    """
    
    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        command: str,
        action: Dict[str, Any],
        schedule_time: Optional[datetime] = None,
        schedule_expression: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        created_at: Optional[datetime] = None,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None,
        run_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.command = command
        self.action = action
        self.schedule_time = schedule_time
        self.schedule_expression = schedule_expression
        self.status = status
        self.created_at = created_at or datetime.now()
        self.last_run = last_run
        self.next_run = next_run or schedule_time
        self.run_count = run_count
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "command": self.command,
            "action": self.action,
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "schedule_expression": self.schedule_expression,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "metadata": self.metadata,
        }


class TaskScheduler:
    """
    Lightweight task scheduler for Janus
    
    Manages scheduled and recurring tasks with persistence support.
    Runs in a background thread and executes tasks at specified times.
    """
    
    def __init__(self, db_connection=None, tts_service=None, pipeline=None):
        """
        Initialize task scheduler
        
        Args:
            db_connection: Database connection for task persistence
            tts_service: TTS service for voice notifications
            pipeline: JanusPipeline for executing commands
        """
        self.db = db_connection
        self.tts_service = tts_service
        self.pipeline = pipeline
        
        # Task storage
        self._tasks: Dict[str, ScheduledTask] = {}
        self._schedule_jobs: Dict[str, schedule.Job] = {}
        
        # Thread management
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Load tasks from database if available
        if self.db:
            self._load_tasks_from_db()
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting task scheduler...")
        self._running = True
        self._stop_event.clear()
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            name="TaskScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler and wait for thread to finish"""
        if not self._running:
            return
        
        logger.info("Stopping task scheduler...")
        self._running = False
        self._stop_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)
        
        # Clear all schedule jobs
        schedule.clear()
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """
        Main scheduler loop (runs in background thread)
        
        Continuously checks for pending tasks and executes them at the right time.
        """
        logger.info("Scheduler thread started")
        
        while not self._stop_event.is_set():
            try:
                # Run pending scheduled jobs
                schedule.run_pending()
                
                # Sleep for a short interval (check every second)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(1)  # Continue despite errors
        
        logger.info("Scheduler thread stopped")
    
    def schedule_task(
        self,
        task_id: str,
        command: str,
        action: Dict[str, Any],
        delay_seconds: Optional[int] = None,
        schedule_expression: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Schedule a new task
        
        Args:
            task_id: Unique identifier for the task
            command: Original command that triggered this task
            action: Action to execute when task runs
            delay_seconds: Delay in seconds before execution (for one-time tasks)
            schedule_expression: Cron-like expression (for recurring tasks)
            metadata: Additional task metadata
        
        Returns:
            ScheduledTask object
        """
        # Determine task type
        if delay_seconds is not None:
            task_type = TaskType.ONE_TIME
            schedule_time = datetime.now() + timedelta(seconds=delay_seconds)
            next_run = schedule_time
        elif schedule_expression:
            task_type = TaskType.RECURRING
            schedule_time = None
            next_run = self._calculate_next_run(schedule_expression)
        else:
            raise ValueError("Must specify either delay_seconds or schedule_expression")
        
        # Create task
        task = ScheduledTask(
            task_id=task_id,
            task_type=task_type,
            command=command,
            action=action,
            schedule_time=schedule_time,
            schedule_expression=schedule_expression,
            next_run=next_run,
            metadata=metadata,
        )
        
        # Store task
        self._tasks[task_id] = task
        
        # Save to database
        if self.db:
            self._save_task_to_db(task)
        
        # Register with schedule library
        self._register_schedule_job(task)
        
        logger.info(
            f"Scheduled task {task_id} ({task_type.value}): "
            f"next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return task
    
    def _register_schedule_job(self, task: ScheduledTask):
        """Register a task with the schedule library"""
        try:
            if task.task_type == TaskType.ONE_TIME:
                # Schedule one-time task
                delay_seconds = (task.schedule_time - datetime.now()).total_seconds()
                if delay_seconds > 0:
                    job = schedule.every(int(delay_seconds)).seconds.do(
                        self._execute_task, task.task_id
                    )
                    self._schedule_jobs[task.task_id] = job
                else:
                    logger.warning(f"Task {task.task_id} scheduled in the past, executing immediately")
                    self._execute_task(task.task_id)
            
            elif task.task_type == TaskType.RECURRING:
                # Parse schedule expression and register recurring task
                job = self._parse_schedule_expression(task.schedule_expression)
                if job:
                    job.do(self._execute_task, task.task_id)
                    self._schedule_jobs[task.task_id] = job
        
        except Exception as e:
            logger.error(f"Error registering schedule job for task {task.task_id}: {e}")
    
    def _parse_schedule_expression(self, expression: str) -> Optional[schedule.Job]:
        """
        Parse schedule expression and return schedule.Job
        
        Supports expressions like:
        - "every 5 minutes"
        - "every hour"
        - "every day at 10:30"
        - "every monday at 09:00"
        - "every friday at 17:00"
        """
        try:
            expression = expression.lower().strip()
            
            # Remove "every" prefix if present
            if expression.startswith("every "):
                expression = expression[6:]
            
            parts = expression.split()
            
            # Handle "N minutes/hours/days"
            if len(parts) >= 2 and parts[1] in ["minute", "minutes", "hour", "hours", "day", "days"]:
                interval = int(parts[0])
                unit = parts[1].rstrip('s')  # Remove plural 's'
                
                if unit == "minute":
                    return schedule.every(interval).minutes
                elif unit == "hour":
                    return schedule.every(interval).hours
                elif unit == "day":
                    return schedule.every(interval).days
            
            # Handle "day at HH:MM"
            elif "day" in parts and "at" in parts:
                time_str = parts[parts.index("at") + 1]
                return schedule.every().day.at(time_str)
            
            # Handle "WEEKDAY at HH:MM"
            elif "at" in parts:
                weekday = parts[0]
                time_str = parts[parts.index("at") + 1]
                
                weekday_map = {
                    "monday": schedule.every().monday,
                    "tuesday": schedule.every().tuesday,
                    "wednesday": schedule.every().wednesday,
                    "thursday": schedule.every().thursday,
                    "friday": schedule.every().friday,
                    "saturday": schedule.every().saturday,
                    "sunday": schedule.every().sunday,
                }
                
                if weekday in weekday_map:
                    return weekday_map[weekday].at(time_str)
            
            logger.error(f"Unsupported schedule expression: {expression}")
            return None
        
        except Exception as e:
            logger.error(f"Error parsing schedule expression '{expression}': {e}")
            return None
    
    def _calculate_next_run(self, schedule_expression: str) -> datetime:
        """
        Calculate next run time for a recurring task.
        
        This is a simplified implementation that estimates the next run time.
        The actual execution timing is handled by the schedule library.
        
        Args:
            schedule_expression: Schedule expression (e.g., "every 1 hour")
        
        Returns:
            Estimated next run time
        """
        try:
            expression = schedule_expression.lower().strip()
            
            # Remove "every" prefix if present
            if expression.startswith("every "):
                expression = expression[6:]
            
            parts = expression.split()
            
            # Handle "N minutes/hours/days"
            if len(parts) >= 2 and parts[1] in ["minute", "minutes"]:
                minutes = int(parts[0])
                return datetime.now() + timedelta(minutes=minutes)
            elif len(parts) >= 2 and parts[1] in ["hour", "hours"]:
                hours = int(parts[0])
                return datetime.now() + timedelta(hours=hours)
            elif len(parts) >= 2 and parts[1] in ["day", "days"]:
                days = int(parts[0])
                return datetime.now() + timedelta(days=days)
            
            # Handle "day at HH:MM" or "WEEKDAY at HH:MM"
            if "at" in parts:
                # Default to next occurrence (today or tomorrow)
                return datetime.now() + timedelta(days=1)
            
            # Default fallback
            logger.warning(f"Unable to calculate next run for expression: {schedule_expression}")
            return datetime.now() + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return datetime.now() + timedelta(hours=1)
    
    def _execute_task(self, task_id: str):
        """
        Execute a scheduled task
        
        Args:
            task_id: ID of the task to execute
        """
        try:
            task = self._tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            logger.info(f"Executing task {task_id}: {task.command}")
            
            # Update task status
            task.status = TaskStatus.RUNNING
            task.last_run = datetime.now()
            task.run_count += 1
            
            # Execute the action
            action = task.action
            
            if action.get("type") == "tts_notification":
                # Use TTS to deliver a notification
                message = action.get("message", "Reminder")
                if self.tts_service:
                    self.tts_service.speak(message)
                else:
                    logger.warning(f"TTS service not available, cannot speak: {message}")
            
            elif action.get("type") == "execute_command":
                # Execute a command through the pipeline
                # NOTE: Command execution is not yet implemented. This requires:
                # 1. Async/await integration with pipeline.execute()
                # 2. Proper context handling for scheduled execution
                # 3. Error handling for command failures
                # For now, this action type logs the command but doesn't execute it.
                command = action.get("command")
                if self.pipeline:
                    logger.warning(
                        f"Command execution not yet implemented for scheduled tasks. "
                        f"Command would be: {command}"
                    )
                else:
                    logger.warning(f"Pipeline not available, cannot execute: {command}")
            
            else:
                logger.warning(f"Unknown action type: {action.get('type')}")
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            
            # For one-time tasks, remove from schedule
            if task.task_type == TaskType.ONE_TIME:
                self.cancel_task(task_id)
            else:
                # Update next run time for recurring tasks
                task.status = TaskStatus.PENDING
                task.next_run = self._calculate_next_run(task.schedule_expression)
            
            # Update database
            if self.db:
                self._update_task_in_db(task)
            
            logger.info(f"Task {task_id} executed successfully")
        
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.FAILED
                if self.db:
                    self._update_task_in_db(self._tasks[task_id])
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task
        
        Args:
            task_id: ID of the task to cancel
        
        Returns:
            True if task was cancelled, False if not found
        """
        try:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Update task status
            task.status = TaskStatus.CANCELLED
            
            # Remove from schedule library
            if task_id in self._schedule_jobs:
                schedule.cancel_job(self._schedule_jobs[task_id])
                del self._schedule_jobs[task_id]
            
            # Update database
            if self.db:
                self._update_task_in_db(task)
            
            logger.info(f"Task {task_id} cancelled")
            return True
        
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all tasks"""
        return list(self._tasks.values())
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all pending tasks"""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.PENDING
        ]
    
    def _save_task_to_db(self, task: ScheduledTask):
        """Save task to database"""
        try:
            if not self.db:
                return
            
            import json
            
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT INTO scheduled_tasks (
                    task_id, task_type, command, action, schedule_time,
                    schedule_expression, status, created_at, last_run,
                    next_run, run_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.task_type.value,
                    task.command,
                    json.dumps(task.action),
                    task.schedule_time.isoformat() if task.schedule_time else None,
                    task.schedule_expression,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.last_run.isoformat() if task.last_run else None,
                    task.next_run.isoformat() if task.next_run else None,
                    task.run_count,
                    json.dumps(task.metadata),
                ),
            )
            self.db.commit()
        
        except Exception as e:
            logger.error(f"Error saving task to database: {e}")
    
    def _update_task_in_db(self, task: ScheduledTask):
        """Update task in database"""
        try:
            if not self.db:
                return
            
            import json
            
            cursor = self.db.cursor()
            cursor.execute(
                """
                UPDATE scheduled_tasks SET
                    status = ?, last_run = ?, next_run = ?, run_count = ?
                WHERE task_id = ?
                """,
                (
                    task.status.value,
                    task.last_run.isoformat() if task.last_run else None,
                    task.next_run.isoformat() if task.next_run else None,
                    task.run_count,
                    task.task_id,
                ),
            )
            self.db.commit()
        
        except Exception as e:
            logger.error(f"Error updating task in database: {e}")
    
    def _load_tasks_from_db(self):
        """Load tasks from database on startup"""
        try:
            if not self.db:
                return
            
            import json
            
            cursor = self.db.cursor()
            cursor.execute(
                """
                SELECT task_id, task_type, command, action, schedule_time,
                       schedule_expression, status, created_at, last_run,
                       next_run, run_count, metadata
                FROM scheduled_tasks
                WHERE status IN ('pending', 'running')
                """
            )
            
            rows = cursor.fetchall()
            logger.info(f"Loading {len(rows)} tasks from database")
            
            for row in rows:
                task = ScheduledTask(
                    task_id=row[0],
                    task_type=TaskType(row[1]),
                    command=row[2],
                    action=json.loads(row[3]),
                    schedule_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    schedule_expression=row[5],
                    status=TaskStatus(row[6]),
                    created_at=datetime.fromisoformat(row[7]),
                    last_run=datetime.fromisoformat(row[8]) if row[8] else None,
                    next_run=datetime.fromisoformat(row[9]) if row[9] else None,
                    run_count=row[10],
                    metadata=json.loads(row[11]) if row[11] else {},
                )
                
                self._tasks[task.task_id] = task
                
                # Re-register with schedule library
                self._register_schedule_job(task)
            
            logger.info(f"Loaded {len(self._tasks)} tasks from database")
        
        except Exception as e:
            logger.error(f"Error loading tasks from database: {e}")
