"""
Base Agent Interface for V3 Execution - ATOMIC OPERATIONS ONLY

TICKET-AUDIT-002: Simplified architecture - Agents provide ONLY atomic operations.
Complex logic, fallbacks, and intelligence belong in the Reasoner/Orchestrator.

This module defines the abstract base class that all V3 agents must implement,
along with the custom exception for agent execution errors.

ATOMIC OPERATION PRINCIPLES:
1. Each operation < 20 lines of code
2. No business logic or heuristics
3. No retry loops or fallbacks
4. No multi-step workflows
5. Dumb execution only - intelligence in Reasoner

All agents must:
1. Inherit from BaseAgent
2. Implement async execute(action, args, context) method
3. Log before/after execution
4. Raise AgentExecutionError for unsupported actions or failures
5. Never interpret user intent or modify plans
6. Keep all operations atomic and simple
"""

import logging
import platform
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """
    Exception raised when agent execution fails.
    
    This exception is raised when:
    - Action is not supported by the agent
    - Required arguments are missing
    - Application is not available
    - Context preconditions are not met
    - Execution fails for any reason
    
    Attributes:
        module: Module/agent name (e.g., "system", "browser")
        action: Action name that failed
        details: Detailed error description
        recoverable: Whether the error is potentially recoverable
    """
    
    def __init__(
        self,
        module: str,
        action: str,
        details: str,
        recoverable: bool = True
    ):
        """
        Initialize AgentExecutionError.
        
        Args:
            module: Module/agent name
            action: Action that failed
            details: Error details
            recoverable: Whether error is recoverable
        """
        self.module = module
        self.action = action
        self.details = details
        self.recoverable = recoverable
        
        message = f"Agent '{module}' failed to execute '{action}': {details}"
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for ExecutionEngineV3."""
        return {
            "status": "error",
            "module": self.module,
            "action": self.action,
            "error": self.details,
            "error_type": "agent_execution_error",
            "recoverable": self.recoverable,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all V3 execution agents.
    
    TICKET-AUDIT-002: ATOMIC OPERATIONS ONLY
    Each agent provides only mechanical, atomic operations with no intelligence.
    
    ATOMIC OPERATION CONTRACT:
    - Each operation is < 20 lines of actual logic
    - No retry loops (Orchestrator handles retries)
    - No fallback mechanisms (Reasoner decides alternatives)
    - No heuristics or "smart" behavior (Reasoner provides intelligence)
    - No multi-step workflows (Reasoner chains atomic operations)
    - Direct, mechanical execution only
    
    All agents must implement the execute() method which:
    1. Validates action and arguments
    2. Logs before execution
    3. Performs ONE atomic action mechanically
    4. Logs after execution
    5. Returns standardized result dictionary
    
    Agents should NEVER:
    - Interpret natural language
    - Modify or replan action sequences
    - Make decisions about user intent
    - Implement retry logic or fallbacks
    - Contain business rules or heuristics
    - Handle multiple steps in one operation
    
    Agents should ONLY:
    - Execute ONE atomic validated action
    - Update context when necessary
    - Raise errors immediately for invalid actions
    - Return structured results
    
    Example of ATOMIC operations:
    - GOOD: open_url(url) - opens URL, nothing else
    - BAD: smart_navigate(url) - tries multiple strategies, has fallbacks
    
    - GOOD: click(selector) - clicks element, nothing else  
    - BAD: fill_form(data) - fills multiple fields, validates, submits
    
    - GOOD: type_text(text) - types text, nothing else
    - BAD: search_and_click(query) - searches, waits, clicks result
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize base agent.
        
        Args:
            agent_name: Name of the agent (e.g., "system", "browser")
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agents.{agent_name}")
        self.is_v3 = True  # TICKET 201: Mark as V3 agent to prevent overwriting
        # TICKET-AUDIT-002: Shared platform detection to avoid duplication
        self.is_mac = platform.system() == "Darwin"
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.logger.info(f"✓ {agent_name.capitalize()}Agent initialized")
    
    @abstractmethod
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute an action with given arguments and context.
        
        This is the main entry point for agent execution. All agents must
        implement this method.
        
        Args:
            action: Action name (e.g., "open_application", "click")
            args: Action arguments as dictionary
            context: Execution context containing:
                - app: Current application (Safari, Chrome, VSCode, etc.)
                - surface: Current UI surface (browser, editor, chat, etc.)
                - url: Current URL (for browser actions)
                - domain: Current domain (example.com, github.com, etc.)
                - thread: Current thread ID (for messaging)
                - record: Current record ID (for CRM)
            dry_run: If True, preview action without executing (P2 feature)
        
        Returns:
            Result dictionary with structure:
            {
                "status": "success" | "error",
                "data": <result_data>,
                "error": <error_message>,
                "context_updates": {<context_changes>},
                "dry_run": True/False,  # P2: Indicates if this was dry-run
                "reversible": True/False,  # P2: Whether action can be undone
                "compensation_data": {...}  # P2: Data needed for rollback
            }
        
        Raises:
            AgentExecutionError: If action is unsupported or execution fails
        """
        pass
    
    def _log_before(self, action: str, args: Dict[str, Any], context: Dict[str, Any], dry_run: bool = False) -> None:
        """
        Log before action execution.
        
        Args:
            action: Action name
            args: Action arguments
            context: Execution context
            dry_run: Whether this is a dry-run execution
        """
        prefix = "[DRY-RUN] " if dry_run else ""
        self.logger.info(
            f"{prefix}→ Executing {self.agent_name}.{action} | "
            f"args={self._sanitize_args(args)} | "
            f"context={self._sanitize_context(context)}"
        )
    
    def _log_dry_run_preview(self, action: str, args: Dict[str, Any], description: str) -> None:
        """
        Log dry-run preview of what would be executed.
        
        Args:
            action: Action name
            args: Action arguments
            description: Human-readable description of what would happen
        """
        self.logger.info(
            f"[DRY-RUN PREVIEW] {self.agent_name}.{action} would: {description}"
        )
    
    def _log_after(
        self,
        action: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        dry_run: bool = False
    ) -> None:
        """
        Log after action execution.
        
        Args:
            action: Action name
            success: Whether action succeeded
            duration_ms: Execution duration in milliseconds
            error: Optional error message
            dry_run: Whether this was a dry-run execution
        """
        status_symbol = "✓" if success else "✗"
        log_level = logging.INFO if success else logging.ERROR
        prefix = "[DRY-RUN] " if dry_run else ""
        
        message = (
            f"{prefix}{status_symbol} {self.agent_name}.{action} "
            f"({'success' if success else 'failed'}) | "
            f"duration={duration_ms:.0f}ms"
        )
        
        if error:
            message += f" | error={error}"
        
        self.logger.log(log_level, message)
    
    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize arguments for logging (remove sensitive data).
        
        Args:
            args: Arguments dictionary
        
        Returns:
            Sanitized arguments
        """
        # Simple sanitization - can be enhanced
        sensitive_keys = {"password", "token", "api_key", "secret"}
        sanitized = {}
        
        for key, value in args.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context for logging (keep only relevant fields).
        
        Args:
            context: Context dictionary
        
        Returns:
            Sanitized context
        """
        # Only log relevant context fields
        relevant_keys = {"app", "surface", "url", "domain", "thread", "record"}
        return {k: v for k, v in context.items() if k in relevant_keys and v}
    
    def _validate_required_args(
        self,
        action: str,
        args: Dict[str, Any],
        required: list[str]
    ) -> None:
        """
        Validate that required arguments are present.
        
        Args:
            action: Action name
            args: Arguments dictionary
            required: List of required argument names
        
        Raises:
            AgentExecutionError: If required arguments are missing
        """
        missing = [arg for arg in required if arg not in args or args[arg] is None]
        
        if missing:
            raise AgentExecutionError(
                module=self.agent_name,
                action=action,
                details=f"Missing required arguments: {', '.join(missing)}",
                recoverable=False
            )
    
    def _success_result(
        self,
        data: Any = None,
        context_updates: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a success result dictionary.
        
        Args:
            data: Optional result data
            context_updates: Optional context updates
            message: Optional success message
        
        Returns:
            Success result dictionary
        """
        result = {
            "status": "success",
            "data": data,
        }
        
        if message:
            result["message"] = message
        
        if context_updates:
            result["context_updates"] = context_updates
        
        return result
    
    def _error_result(
        self,
        error: str,
        recoverable: bool = True,
        error_type: str = "execution_error"
    ) -> Dict[str, Any]:
        """
        Create an error result dictionary.
        
        Args:
            error: Error message
            recoverable: Whether error is recoverable
            error_type: Type of error
        
        Returns:
            Error result dictionary
        """
        return {
            "status": "error",
            "error": error,
            "error_type": error_type,
            "recoverable": recoverable,
        }
