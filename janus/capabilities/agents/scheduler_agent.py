"""
SchedulerAgent - Task Scheduling and Delayed Actions

TICKET-FEAT-002: Scheduler & Actions Différées (Cron)
TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

This agent handles scheduling-related operations including:
- Scheduling delayed tasks (e.g., "remind me in 5 minutes")
- Creating recurring tasks (e.g., "send report every Friday")
- Cancelling scheduled tasks
- Listing pending tasks
"""

import uuid
from typing import Any, Dict, Optional

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.logging import get_logger

logger = get_logger("scheduler_agent")


class SchedulerAgent(BaseAgent):
    """
    Agent for task scheduling operations.
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Supported actions:
    - schedule_task(delay_seconds: int, message: str) - Schedule a one-time reminder
    - schedule_task(schedule_expression: str, message: str) - Schedule a recurring reminder
    - schedule_task(schedule_expression: str, command: str) - Schedule a recurring command
    - cancel_task(task_id: str) - Cancel a scheduled task
    - list_tasks() - List all scheduled tasks
    """
    
    def __init__(self, lifecycle_service=None, provider: str = "local"):
        """
        Initialize SchedulerAgent.
        
        Args:
            lifecycle_service: LifecycleService instance to access task scheduler
            provider: Calendar/scheduling provider ("local", "outlook", "google", "apple", "notion")
        """
        super().__init__("scheduler")
        self._lifecycle_service = lifecycle_service
        self.provider = provider
    
    def set_lifecycle_service(self, lifecycle_service):
        """Set the lifecycle service (for late binding)"""
        self._lifecycle_service = lifecycle_service
    
    @property
    def scheduler(self):
        """Get the task scheduler from lifecycle service"""
        if self._lifecycle_service is None:
            raise AgentExecutionError(
                "SchedulerAgent not properly initialized: lifecycle_service is None"
            )
        
        scheduler = self._lifecycle_service.get_task_scheduler()
        if scheduler is None:
            raise AgentExecutionError(
                "Task scheduler not available. Please start the scheduler first."
            )
        
        return scheduler
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a scheduling action by routing to decorated methods."""
        # P2: Dry-run mode - preview without scheduling
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would schedule task via '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": True,  # Scheduled tasks can be cancelled
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        # Route to decorated method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        else:
            raise AgentExecutionError(
                f"Unknown action for SchedulerAgent: {action}",
                recoverable=False
            )
    
    @agent_action(
        description="Schedule a task for delayed or recurring execution",
        required_args=[],
        optional_args={
            "delay_seconds": None,
            "schedule_expression": None, 
            "message": None,
            "command": None
        },
        providers=["local", "outlook", "google", "apple", "notion"],
        examples=[
            "scheduler.schedule_task(delay_seconds=300, message='Reminder: Meeting in 5 minutes')",
            "scheduler.schedule_task(schedule_expression='0 9 * * 1', message='Weekly report reminder')"
        ]
    )
    async def _schedule_task(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a task."""
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Extract parameters
        delay_seconds = args.get("delay_seconds")
        schedule_expression = args.get("schedule_expression")
        message = args.get("message")
        command = args.get("command")
        
        # Validate parameters
        if delay_seconds is None and schedule_expression is None:
            raise AgentExecutionError(
                "Must specify either 'delay_seconds' or 'schedule_expression'",
                recoverable=False
            )
        
        if message is None and command is None:
            raise AgentExecutionError(
                "Must specify either 'message' or 'command'",
                recoverable=False
            )
        
        # Build action for the task
        if message:
            action = {
                "type": "tts_notification",
                "message": message
            }
        else:
            action = {
                "type": "execute_command",
                "command": command
            }
        
        # Get original command from context
        original_command = context.get("user_goal", "Unknown command")
        
        # Schedule the task
        task = self.scheduler.schedule_task(
            task_id=task_id,
            command=original_command,
            action=action,
            delay_seconds=delay_seconds,
            schedule_expression=schedule_expression,
            metadata={
                "context": context
            }
        )
        
        # Build confirmation message
        if delay_seconds:
            minutes = delay_seconds // 60
            seconds = delay_seconds % 60
            if minutes > 0:
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"
                if seconds > 0:
                    time_str += f" et {seconds} seconde{'s' if seconds > 1 else ''}"
            else:
                time_str = f"{seconds} seconde{'s' if seconds > 1 else ''}"
            
            confirmation = f"Tâche planifiée dans {time_str}"
        else:
            confirmation = f"Tâche récurrente planifiée: {schedule_expression}"
        
        logger.info(f"Scheduled task {task_id}: {confirmation}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": confirmation,
            "task_type": task.task_type.value,
            "next_run": task.next_run.isoformat() if task.next_run else None
        }
    
    @agent_action(
        description="Cancel a scheduled task",
        required_args=["task_id"],
        providers=["local", "outlook", "google", "apple", "notion"],
        examples=["scheduler.cancel_task(task_id='12345-abcd-6789')"]
    )
    async def _cancel_task(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a scheduled task."""
        task_id = args["task_id"]
        
        # Cancel the task
        success = self.scheduler.cancel_task(task_id)
        
        if success:
            logger.info(f"Cancelled task {task_id}")
            return {
                "success": True,
                "message": f"Tâche {task_id} annulée"
            }
        else:
            return {
                "success": False,
                "message": f"Tâche {task_id} non trouvée"
            }
    
    @agent_action(
        description="List all pending scheduled tasks",
        required_args=[],
        optional_args={"status": "pending"},
        providers=["local", "outlook", "google", "apple", "notion"],
        examples=["scheduler.list_tasks()"]
    )
    async def _list_tasks(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """List all scheduled tasks."""
        # Get all pending tasks
        tasks = self.scheduler.get_pending_tasks()
        
        # Convert to serializable format
        task_list = [task.to_dict() for task in tasks]
        
        logger.info(f"Listed {len(task_list)} pending tasks")
        
        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list)
        }
