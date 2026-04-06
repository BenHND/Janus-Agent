"""
Core data contracts for Janus unified pipeline.
TICKET B4: Updated to use constants instead of magic strings
ARCH-004: Canonical SystemState for stable grounding

This module defines typed data structures using dataclasses for:
- SystemState: Canonical system state representation (ARCH-004)
- Intent: Parsed command intent
- ActionPlan: Planned actions to execute
- ActionResult: Result of individual action execution
- ExecutionResult: Overall execution results
- CommandError: Structured error information
- ErrorType: Error type enumeration
- Result[T]: Generic result wrapper for success/failure patterns
- ParserResult: Result type for command parsers
- AdapterResult: Result type for application adapters
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from janus.constants import ActionStatus

# Generic type variable for Result[T]
T = TypeVar("T")


# ============================================================================
# ARCH-004: Canonical SystemState - Single Source of Truth
# ============================================================================


@dataclass(frozen=True)
class SystemState:
    """
    Canonical system state representation - Single Source of Truth (ARCH-004).
    
    This dataclass defines the stable, uniform structure for system state
    used across the entire application. It ensures consistency between:
    - Action execution (ActionCoordinator)
    - Decision making (ReasonerLLM)
    - Stop condition evaluation
    - Stagnation detection
    
    All state observation should produce instances of this class, ensuring
    uniform keys and preventing state inconsistencies that lead to unstable
    stop conditions.
    
    Immutable (frozen=True) to prevent accidental modifications and ensure
    state snapshots remain consistent.
    
    Attributes:
        timestamp: ISO 8601 timestamp of state capture
        active_app: Name of the active/frontmost application (e.g., "Safari", "Chrome")
        window_title: Title of the active window
        url: Current URL (for browser contexts), empty string if not applicable
        domain: Domain extracted from URL (e.g., "example.com"), None if not applicable
        clipboard: Current clipboard content (first 1000 chars for safety)
        performance_ms: Time taken to capture this state in milliseconds
    """
    
    timestamp: str
    active_app: str
    window_title: str
    url: str
    domain: Optional[str]
    clipboard: str
    performance_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization and backward compatibility.
        
        Returns:
            Dictionary representation of the system state
        """
        return {
            "timestamp": self.timestamp,
            "active_app": self.active_app,
            "window_title": self.window_title,
            "url": self.url,
            "domain": self.domain,
            "clipboard": self.clipboard,
            "performance_ms": self.performance_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemState":
        """
        Create SystemState from dictionary.
        
        Provides defaults for missing keys to handle legacy data.
        
        Args:
            data: Dictionary with system state data
            
        Returns:
            SystemState instance
        """
        return cls(
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            active_app=data.get("active_app", "Unknown"),
            window_title=data.get("window_title", ""),
            url=data.get("url", ""),
            domain=data.get("domain"),
            clipboard=data.get("clipboard", ""),
            performance_ms=data.get("performance_ms", 0.0),
        )
    
    def __hash__(self) -> int:
        """
        Compute hash for stagnation detection.
        
        Hash is based on observable state that indicates progress:
        - active_app: Different app = progress
        - window_title: Different window = progress
        - url: Different URL = progress
        - clipboard (first 100 chars): Different content = progress
        
        Returns:
            Hash value for state comparison
        """
        return hash((
            self.active_app,
            self.window_title,
            self.url,
            self.clipboard[:100] if self.clipboard else "",
        ))


# ============================================================================
# Confirmation Events for High-Risk Actions (TICKET-SEC-001)
# ============================================================================


@dataclass
class RequestConfirmation:
    """
    Event raised when a high-risk action requires user confirmation.
    
    This event pauses execution and waits for user input before proceeding.
    Used for actions like delete, send, execute that could have significant impact.
    """
    action_type: str  # e.g., "files.delete_file"
    action_details: Dict[str, Any]  # Full step information
    risk_level: str  # "HIGH"
    confirmation_prompt: str  # Human-readable prompt
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_type": "request_confirmation",
            "action_type": self.action_type,
            "action_details": self.action_details,
            "risk_level": self.risk_level,
            "confirmation_prompt": self.confirmation_prompt,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_id": self.request_id
        }


@dataclass
class ConfirmationResponse:
    """
    User response to a confirmation request.
    """
    request_id: str
    confirmed: bool  # True = proceed, False = cancel
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ErrorType(Enum):
    """Error types for command processing"""

    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_COMMAND = "unknown_command"
    # TICKET 5: Additional error types for recovery
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND_ERROR = "not_found_error"
    APP_NOT_RESPONDING = "app_not_responding"
    ELEMENT_NOT_FOUND = "element_not_found"


class RecoveryState(Enum):
    """
    Recovery state machine for ActionCoordinator.
    
    RELIABILITY-001: Single owner recovery/replanning.
    ActionCoordinator is the sole owner of recovery strategy.
    
    States:
    - IDLE: No recovery in progress, normal execution
    - DETECTING: Detecting potential issues (stagnation, errors)
    - RECOVERING: Actively recovering (vision re-observation, replanning)
    - RECOVERED: Recovery succeeded, resuming normal execution
    - FAILED: Recovery failed, cannot proceed
    """
    
    IDLE = "idle"
    DETECTING = "detecting"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"


@dataclass
class Intent:
    """Parsed command intent with confidence and parameters"""

    action: str
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_command: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ActionPlan:
    """
    Plan of actions to execute based on intent.

    Supports both single-module (legacy) and multi-module plans:
    - Legacy: actions = [{"type": "open_app", "app_name": "Chrome"}]
    - Multi-module: steps = [{"module": "chrome", "action": "open_url", "args": {...}}]
    - TICKET 5: Conditional steps with condition, if_true, if_false
    """

    intent: Intent
    actions: List[Dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    estimated_duration_ms: Optional[int] = None

    # Multi-module support (TICKET 2)
    steps: Optional[List[Dict[str, Any]]] = None

    def add_step(
        self,
        module: str,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        step_id: Optional[str] = None,
        context: Optional[str] = None,
    ):
        """
        Add a step to multi-module plan (TICKET 2).

        Args:
            module: Module name (e.g., "chrome", "vscode", "llm")
            action: Action name (e.g., "open_url", "extract_page_text", "summarize")
            args: Action arguments (can include "input_from" for context references)
            step_id: Optional step ID for output tracking
            context: Optional execution context (e.g., "example.com", "Safari", null)
                     Indicates the environment where the action must execute
        """
        if self.steps is None:
            self.steps = []

        step = {"module": module, "action": action, "args": args or {}}

        # Always include context field for consistency (TICKET-001)
        step["context"] = context

        if step_id:
            step["step_id"] = step_id

        self.steps.append(step)

    def add_conditional_step(
        self,
        condition: str,
        if_true: List[Dict[str, Any]],
        if_false: Optional[List[Dict[str, Any]]] = None,
        step_id: Optional[str] = None,
    ):
        """
        Add a conditional step to multi-module plan (TICKET 5).

        Args:
            condition: Condition expression (e.g., "app_not_open('Chrome')")
            if_true: Steps to execute if condition is true
            if_false: Steps to execute if condition is false
            step_id: Optional step ID for tracking

        Example:
            plan.add_conditional_step(
                condition="app_not_open('Chrome')",
                if_true=[{"module": "chrome", "action": "open_app"}],
                if_false=[{"module": "chrome", "action": "switch_tab"}]
            )
        """
        if self.steps is None:
            self.steps = []

        conditional_step = {
            "type": "conditional",
            "condition": condition,
            "if_true": if_true,
            "if_false": if_false or [],
        }

        if step_id:
            conditional_step["step_id"] = step_id

        self.steps.append(conditional_step)

    def add_loop(self, repeat: int, steps: List[Dict[str, Any]], step_id: Optional[str] = None):
        """
        Add a loop construct to repeat steps multiple times.

        Args:
            repeat: Number of times to repeat the steps
            steps: Steps to execute in each iteration
            step_id: Optional step ID for tracking

        Example:
            plan.add_loop(
                repeat=3,
                steps=[{"module": "terminal", "action": "execute", "args": {"cmd": "echo {{index}}"}}]
            )
        """
        if self.steps is None:
            self.steps = []

        loop_step = {"type": "loop", "repeat": repeat, "steps": steps}

        if step_id:
            loop_step["step_id"] = step_id

        self.steps.append(loop_step)

    def add_for_each(
        self, items: List[Any], steps: List[Dict[str, Any]], step_id: Optional[str] = None
    ):
        """
        Add a for-each loop to iterate over a collection.

        Args:
            items: Collection of items to iterate over
            steps: Steps to execute for each item (use {{item}} placeholder)
            step_id: Optional step ID for tracking

        Example:
            plan.add_for_each(
                items=["file1.txt", "file2.txt", "file3.txt"],
                steps=[{"module": "vscode", "action": "open_file", "args": {"path": "{{item}}"}}]
            )
        """
        if self.steps is None:
            self.steps = []

        for_each_step = {"type": "for_each", "items": items, "steps": steps}

        if step_id:
            for_each_step["step_id"] = step_id

        self.steps.append(for_each_step)

    def is_multi_module(self) -> bool:
        """Check if this is a multi-module plan"""
        return self.steps is not None and len(self.steps) > 0


@dataclass
class ExecutionContext:
    """
    Execution context for tracking outputs across multi-module steps (TICKET 2).
    
    TICKET-002: Enhanced with V3 context structure for stable propagation.
    TICKET-P2: Added dry_run mode support for preview without side effects.
    
    Context V3 Structure:
    - app: Active application (Safari, Chrome, VSCode, etc.)
    - surface: Interaction surface (browser, editor, chat, timeline, file_browser)
    - url: Current URL (for browser contexts)
    - domain: Domain name extracted from URL (example.com, github.com)
    - thread: Thread/conversation ID (for messaging contexts)
    - record: CRM record ID (for CRM contexts)

    Allows steps to reference outputs from previous steps using:
    - "input_from": "last_output" - Gets the most recent output
    - "input_from": "step.0" - Gets output from step 0
    - "input_from": "step_id" - Gets output from named step
    
    Also tracks the active/frontmost application for sync with OS reality.
    """

    outputs: Dict[str, Any] = field(default_factory=dict)
    last_output: Optional[Any] = None
    step_count: int = 0
    active_app: Optional[str] = None  # Track frontmost app for sync
    
    # V3 Context fields (TICKET-002)
    surface: Optional[str] = None  # browser, editor, chat, timeline, file_browser
    url: Optional[str] = None  # Current URL
    domain: Optional[str] = None  # Domain extracted from URL
    thread: Optional[str] = None  # Thread/conversation ID
    record: Optional[str] = None  # CRM record ID
    
    # P2 Features
    dry_run: bool = False  # Preview mode - no side effects when True

    def store_output(self, output: Any, step_id: Optional[str] = None):
        """
        Store output from a step.

        Args:
            output: The output value to store
            step_id: Optional step ID or index (auto-generated if not provided)
        """
        # Always update last_output
        self.last_output = output

        # Store with step ID or index
        if step_id is None:
            step_id = f"step.{self.step_count}"

        self.outputs[step_id] = output
        self.step_count += 1

    def resolve_input(self, input_ref: str) -> Optional[Any]:
        """
        Resolve an input reference to actual value.

        Args:
            input_ref: Reference like "last_output" or "step.0" or "step_id"

        Returns:
            The resolved value or None if not found
        """
        if input_ref == "last_output":
            return self.last_output

        return self.outputs.get(input_ref)

    def resolve_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all input_from references in arguments.

        Args:
            args: Arguments dictionary that may contain "input_from" keys

        Returns:
            New dictionary with resolved values
        """
        resolved = {}

        for key, value in args.items():
            if key == "input_from":
                # Resolve the input reference
                resolved_value = self.resolve_input(value)
                if resolved_value is not None:
                    # If input_from resolves, add it as the actual input
                    resolved["input"] = resolved_value
            else:
                resolved[key] = value

        return resolved
    
    def update_from_step_context(self, step_context: Dict[str, Any]) -> None:
        """
        Update execution context from a step's context field (TICKET-002).
        
        Propagates context from executed step to maintain continuity.
        
        Args:
            step_context: Context dict from step with V3 structure
                         {app, surface, url, domain, thread, record}
        """
        if not step_context:
            return
        
        # Update each field if provided (non-null values)
        if step_context.get("app") is not None:
            self.active_app = step_context["app"]
        
        if step_context.get("surface") is not None:
            self.surface = step_context["surface"]
        
        if step_context.get("url") is not None:
            self.url = step_context["url"]
            # Auto-extract domain if not explicitly provided
            if step_context.get("domain") is None and self.url:
                self.domain = self._extract_domain(self.url)
        
        if step_context.get("domain") is not None:
            self.domain = step_context["domain"]
        
        if step_context.get("thread") is not None:
            self.thread = step_context["thread"]
        
        if step_context.get("record") is not None:
            self.record = step_context["record"]
    
    def get_current_context(self) -> Dict[str, Any]:
        """
        Get current V3 context as dict (TICKET-002).
        
        Returns:
            Dict with V3 context structure
        """
        return {
            "app": self.active_app,
            "surface": self.surface,
            "url": self.url,
            "domain": self.domain,
            "thread": self.thread,
            "record": self.record
        }
    
    def inject_context_if_missing(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject current context into step if step's context is incomplete (TICKET-002).
        
        Automatic propagation: if step doesn't specify context fields,
        inherit from current execution context.
        
        Args:
            step: Step dict with optional context field
        
        Returns:
            Step dict with complete context
        """
        # Get or create step context
        if "context" not in step or step["context"] is None:
            step["context"] = {}
        
        step_context = step["context"]
        
        # Inherit missing fields from execution context
        if step_context.get("app") is None and self.active_app is not None:
            step_context["app"] = self.active_app
        
        if step_context.get("surface") is None and self.surface is not None:
            step_context["surface"] = self.surface
        
        if step_context.get("url") is None and self.url is not None:
            step_context["url"] = self.url
        
        if step_context.get("domain") is None and self.domain is not None:
            step_context["domain"] = self.domain
        
        if step_context.get("thread") is None and self.thread is not None:
            step_context["thread"] = self.thread
        
        if step_context.get("record") is None and self.record is not None:
            step_context["record"] = self.record
        
        step["context"] = step_context
        return step
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL (TICKET-002).
        
        Args:
            url: Full URL string
        
        Returns:
            Domain string (e.g., "example.com") or None
        
        Examples:
            >>> context._extract_domain("https://www.example.com/watch?v=123")
            "example.com"
            >>> context._extract_domain("http://github.com/user/repo")
            "github.com"
            >>> context._extract_domain("https://subdomain.example.com:8080/path")
            "subdomain.example.com"
            >>> context._extract_domain("www.example.org")
            "example.org"
        """
        if not url:
            return None
        
        # Remove protocol
        if "://" in url:
            url = url.split("://", 1)[1]
        
        # Remove path and query
        if "/" in url:
            url = url.split("/", 1)[0]
        
        # Remove port
        if ":" in url:
            url = url.split(":", 1)[0]
        
        # Remove www. prefix
        if url.startswith("www."):
            url = url[4:]
        
        return url if url else None


@dataclass
class ActionResult:
    """Result of executing a single action"""

    action_type: str
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: Optional[datetime] = None
    output: Optional[Any] = None  # TICKET 2: Add output field for context propagation
    # TICKET 5: Error recovery fields
    error_type: Optional[ErrorType] = None
    recoverable: bool = True  # Whether this error can be retried
    retry_count: int = 0  # Number of retries attempted
    # P2 Features
    dry_run: bool = False  # True if this was a dry-run execution
    reversible: bool = False  # True if action can be undone
    compensation_data: Optional[Dict[str, Any]] = None  # Data needed for rollback/undo

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (TICKET 5)"""
        result = {
            "action_type": self.action_type,
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if self.data:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error
            result["recoverable"] = self.recoverable
            if self.error_type:
                result["error_type"] = self.error_type.value

        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms

        if self.retry_count > 0:
            result["retry_count"] = self.retry_count

        if self.output is not None:
            result["output"] = str(self.output)

        return result


@dataclass
class ExecutionResult:
    """Overall execution result for a command or action execution

    Enhanced for TICKET B3 to support standardized error handling across adapters.
    Enhanced for CORE-FOUNDATION-002 to include burst metrics.
    
    Can be used both for:
    - High-level command execution (with intent and action_results)
    - Individual adapter action execution (with message and error_type)
    """

    success: bool
    message: str = ""
    intent: Optional[Intent] = None
    action_results: List[ActionResult] = field(default_factory=list)
    error_type: Optional[str] = None  # "network", "permission", "user_input", "internal"
    total_duration_ms: float = 0.0
    error: Optional["CommandError"] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    burst_metrics: Optional["BurstMetrics"] = None  # CORE-FOUNDATION-002

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.burst_metrics is None:
            self.burst_metrics = BurstMetrics()

    def add_result(self, result: ActionResult):
        """Add an action result"""
        self.action_results.append(result)
        # Update overall success based on all results
        self.success = all(r.success for r in self.action_results)

    @classmethod
    def error(cls, message: str, error_type: str) -> "ExecutionResult":
        """
        Factory method to create an error ExecutionResult

        Args:
            message: Error message
            error_type: Type of error ("network", "permission", "user_input", "internal")

        Returns:
            ExecutionResult with success=False
        """
        return cls(success=False, message=message, error_type=error_type)


@dataclass
class CommandError:
    """Structured error information (TICKET 5 enhanced)"""

    error_type: ErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    # TICKET 5: Recovery fields
    recoverable: bool = True  # Whether this error allows retry/recovery

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Auto-determine recoverability based on error type (TICKET 5)
        if self.error_type in [
            ErrorType.PARSE_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.UNKNOWN_COMMAND,
            ErrorType.PERMISSION_ERROR,
        ]:
            self.recoverable = False
        elif self.error_type in [
            ErrorType.TIMEOUT_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.APP_NOT_RESPONDING,
            ErrorType.ELEMENT_NOT_FOUND,
        ]:
            self.recoverable = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "status": ActionStatus.FAILED.value,
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ============================================================================
# Generic Result Types for Standardized Return Values (TICKET-CODE-02)
# ============================================================================


@dataclass
class Result(Generic[T]):
    """
    Generic result wrapper for success/failure patterns.

    Standardizes return values to replace mixed patterns (dict, tuple, None, exceptions).
    Use factory methods ok() and err() to create instances.

    Examples:
        # Success case
        result = Result.ok(parsed_command, message="Command parsed")
        if result.is_ok():
            value = result.value

        # Failure case
        result = Result.err("Invalid format", error_type=ErrorType.PARSE_ERROR)
        if result.is_err():
            error = result.error
    """

    is_success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def is_ok(self) -> bool:
        """Check if result is successful"""
        return self.is_success

    def is_err(self) -> bool:
        """Check if result is a failure"""
        return not self.is_success

    def unwrap(self) -> T:
        """Unwrap value if successful, raise ValueError if failure"""
        if not self.is_success:
            raise ValueError(f"Cannot unwrap failed result: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return value if successful, otherwise return default"""
        return self.value if self.is_success else default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result_dict = {
            "success": self.is_success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if self.is_success:
            result_dict["value"] = self.value
        else:
            result_dict["error"] = self.error
            if self.error_type:
                result_dict["error_type"] = self.error_type.value

        if self.metadata:
            result_dict["metadata"] = self.metadata

        return result_dict

    @classmethod
    def ok(
        cls, value: T, message: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> "Result[T]":
        """Create a successful result"""
        return cls(is_success=True, value=value, message=message, metadata=metadata or {})

    @classmethod
    def err(
        cls,
        error: str,
        error_type: Optional[ErrorType] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Result[T]":
        """Create a failed result"""
        return cls(
            is_success=False,
            error=error,
            error_type=error_type,
            message=message,
            metadata=metadata or {},
        )


@dataclass
class ParserResult:
    """
    Result type for command parsers (TICKET-CODE-02).

    Standardizes parser return values across different implementations.
    Replaces patterns of returning tuples, Command objects, or None.

    Usage:
        result = ParserResult.from_intent(intent, confidence=0.95)
        result = ParserResult.from_error("Unknown command")
    """

    is_success: bool
    intents: List[Intent] = field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    raw_command: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def ok(self) -> bool:
        """Check if parsing was successful and unambiguous"""
        return self.is_success and not self.is_ambiguous

    def get_intent(self) -> Optional[Intent]:
        """Get the primary intent (first one if multiple)"""
        return self.intents[0] if self.intents else None

    def get_intents(self) -> List[Intent]:
        """Get all parsed intents"""
        return self.intents

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "success": self.is_success,
            "ambiguous": self.is_ambiguous,
            "raw_command": self.raw_command,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if self.intents:
            result["intents"] = [
                {
                    "action": intent.action,
                    "confidence": intent.confidence,
                    "parameters": intent.parameters,
                    "raw_command": intent.raw_command,
                }
                for intent in self.intents
            ]

        if self.error:
            result["error"] = self.error
            if self.error_type:
                result["error_type"] = self.error_type.value

        if self.is_ambiguous and self.ambiguity_reason:
            result["ambiguity_reason"] = self.ambiguity_reason

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_intent(
        cls,
        intent: Intent,
        confidence: Optional[float] = None,
        raw_command: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ParserResult":
        """Create successful result with single intent"""
        if confidence is not None and hasattr(intent, "confidence"):
            intent.confidence = confidence

        return cls(
            is_success=True,
            intents=[intent],
            raw_command=raw_command or intent.raw_command,
            metadata=metadata or {},
        )

    @classmethod
    def from_intents(
        cls, intents: List[Intent], raw_command: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> "ParserResult":
        """Create successful result with multiple intents"""
        return cls(
            is_success=True, intents=intents, raw_command=raw_command, metadata=metadata or {}
        )

    @classmethod
    def from_error(
        cls,
        error: str,
        error_type: Optional[ErrorType] = None,
        raw_command: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ParserResult":
        """Create failed parser result"""
        return cls(
            is_success=False,
            error=error,
            error_type=error_type or ErrorType.PARSE_ERROR,
            raw_command=raw_command,
            metadata=metadata or {},
        )

    @classmethod
    def from_ambiguous(
        cls,
        intents: List[Intent],
        reason: str,
        raw_command: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ParserResult":
        """Create ambiguous result (multiple interpretations)"""
        return cls(
            is_success=True,
            intents=intents,
            is_ambiguous=True,
            ambiguity_reason=reason,
            raw_command=raw_command,
            metadata=metadata or {},
        )


@dataclass
class AdapterResult:
    """
    Result type for application adapters (TICKET-CODE-02).

    Standardizes adapter return values across different adapters.
    Replaces patterns of returning dictionaries with varied keys.

    Usage:
        result = AdapterResult.from_success("open_url", data={"url": "..."})
        result = AdapterResult.from_failure("click", "Element not found")
    """

    is_success: bool
    action: str
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    is_retryable: bool = False
    duration_ms: Optional[int] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def ok(self) -> bool:
        """Check if action was successful"""
        return self.is_success

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        result = {
            "status": ActionStatus.SUCCESS.value if self.is_success else ActionStatus.FAILED.value,
            "action": self.action,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if self.data:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error
            if self.error_type:
                result["error_type"] = self.error_type.value
            result["retryable"] = self.is_retryable

        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
            result["execution_time"] = self.duration_ms / 1000.0

        if self.retry_count > 0:
            result["retry_count"] = self.retry_count

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def from_success(
        cls,
        action: str,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AdapterResult":
        """Create successful adapter result"""
        return cls(
            is_success=True,
            action=action,
            message=message or f"{action} completed successfully",
            data=data,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

    @classmethod
    def from_failure(
        cls,
        action: str,
        error: str,
        error_type: Optional[ErrorType] = None,
        retryable: bool = False,
        duration_ms: Optional[int] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AdapterResult":
        """Create failed adapter result"""
        return cls(
            is_success=False,
            action=action,
            error=error,
            error_type=error_type or ErrorType.EXECUTION_ERROR,
            is_retryable=retryable,
            duration_ms=duration_ms,
            retry_count=retry_count,
            metadata=metadata or {},
        )

    @classmethod
    def from_dict(cls, result_dict: Dict[str, Any]) -> "AdapterResult":
        """Create from legacy dictionary format (backward compatibility)"""
        status = result_dict.get("status", ActionStatus.FAILED.value)
        is_success = status == ActionStatus.SUCCESS.value

        return cls(
            is_success=is_success,
            action=result_dict.get("action", "unknown"),
            message=result_dict.get("message", ""),
            data=result_dict.get("data"),
            error=result_dict.get("error"),
            error_type=(
                ErrorType(result_dict["error_type"]) if "error_type" in result_dict else None
            ),
            is_retryable=result_dict.get("retryable", False),
            duration_ms=result_dict.get("duration_ms")
            or int(result_dict.get("execution_time", 0) * 1000),
            retry_count=result_dict.get("retry_count", 0),
            metadata=result_dict.get("metadata", {}),
        )


# ============================================================================
# Burst OODA Mode - CORE-FOUNDATION-002
# ============================================================================


class StopConditionType(Enum):
    """Types of stop conditions for burst execution"""
    URL_CONTAINS = "url_contains"
    URL_EQUALS = "url_equals"
    UI_ELEMENT_VISIBLE = "ui_element_visible"
    UI_ELEMENT_CONTAINS_TEXT = "ui_element_contains_text"
    APP_ACTIVE = "app_active"
    WINDOW_TITLE_CONTAINS = "window_title_contains"
    CLIPBOARD_CONTAINS = "clipboard_contains"


@dataclass
class StopCondition:
    """
    Stop condition for burst execution.
    
    Defines when to stop executing a burst and re-observe.
    These are generic, observable conditions that don't require app-specific knowledge.
    """
    type: StopConditionType
    value: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value if isinstance(self.type, StopConditionType) else self.type,
            "value": self.value,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopCondition":
        """Create from dictionary"""
        return cls(
            type=StopConditionType(data["type"]) if isinstance(data["type"], str) else data["type"],
            value=data["value"],
            description=data.get("description")
        )


@dataclass
class BurstDecision:
    """
    Decision containing a burst of 2-6 actions to execute together.
    
    This replaces the single-action decision in standard OODA loop
    to reduce LLM calls while maintaining adaptability.
    """
    actions: List[Dict[str, Any]]  # List of {module, action, args, reasoning}
    stop_when: List[StopCondition] = field(default_factory=list)
    needs_vision: bool = False
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "actions": self.actions,
            "stop_when": [sc.to_dict() for sc in self.stop_when],
            "needs_vision": self.needs_vision,
            "reasoning": self.reasoning
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BurstDecision":
        """Create from dictionary"""
        return cls(
            actions=data.get("actions", []),
            stop_when=[StopCondition.from_dict(sc) for sc in data.get("stop_when", [])],
            needs_vision=data.get("needs_vision", False),
            reasoning=data.get("reasoning", "")
        )


@dataclass
class BurstMetrics:
    """
    Metrics for burst OODA execution tracking.
    
    CORE-FOUNDATION-002: Instrumentation obligatoire
    PERF: Added accessibility_fallback_count to track vision optimization
    CRITICAL-P0: Added retry metrics for action retry tracking
    """
    llm_calls: int = 0
    burst_actions_executed: int = 0
    vision_calls: int = 0
    stagnation_events: int = 0
    accessibility_fallback_count: int = 0  # PERF: Count of times we used accessibility instead of vision
    
    t_llm_ms: float = 0.0
    t_observe_ms: float = 0.0
    t_act_ms: float = 0.0
    t_vision_ms: float = 0.0
    
    total_bursts: int = 0
    avg_actions_per_burst: float = 0.0
    
    # CRITICAL-P0: Retry/recovery metrics
    total_retries: int = 0  # Total number of retry attempts
    successful_retries: int = 0  # Retries that eventually succeeded
    failed_retries: int = 0  # Retries that exhausted all attempts
    recovery_attempts: int = 0  # Number of recovery attempts (replanning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "llm_calls": self.llm_calls,
            "burst_actions_executed": self.burst_actions_executed,
            "vision_calls": self.vision_calls,
            "stagnation_events": self.stagnation_events,
            "accessibility_fallback_count": self.accessibility_fallback_count,
            "t_llm_ms": self.t_llm_ms,
            "t_observe_ms": self.t_observe_ms,
            "t_act_ms": self.t_act_ms,
            "t_vision_ms": self.t_vision_ms,
            "total_bursts": self.total_bursts,
            "avg_actions_per_burst": self.avg_actions_per_burst,
            "total_retries": self.total_retries,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "recovery_attempts": self.recovery_attempts
        }
    
    def record_burst(self, action_count: int) -> None:
        """Record a burst execution"""
        self.total_bursts += 1
        self.burst_actions_executed += action_count
        if self.total_bursts > 0:
            self.avg_actions_per_burst = self.burst_actions_executed / self.total_bursts


# ============================================================================
# LEARNING-001: Skill Hints - Learned Action Sequences as Suggestions
# ============================================================================


@dataclass
class SkillHint:
    """
    Learned action sequence provided as a HINT to the LLM Reasoner.
    
    LEARNING-001: Skills are NEVER executed automatically. They are suggestions
    that provide context to the Reasoner, which then makes decisions through OODA.
    
    This ensures:
    1. All actions pass through the central decision loop (OODA)
    2. Observable preconditions are always checked before execution
    3. Skills improve LLM efficiency without bypassing reasoning
    4. Visual grounding is maintained for all actions
    
    The Reasoner receives the skill as part of its context and can:
    - Follow the suggested sequence if conditions match
    - Adapt the sequence if the situation has changed
    - Reject the skill if it's no longer applicable
    - Learn from discrepancies to improve future skills
    """
    
    skill_id: int
    intent_text: str
    suggested_actions: List[Dict[str, Any]]
    context_hash: str
    success_count: int
    last_used: str
    confidence: float = 0.0  # Similarity score from vector matching
    
    def to_context_string(self) -> str:
        """
        Convert skill to a concise context string for LLM prompt.
        
        Returns a formatted string that describes the learned sequence
        without implying automatic execution.
        
        Returns:
            Formatted hint string for LLM context
        """
        actions_desc = []
        for i, action in enumerate(self.suggested_actions, 1):
            action_type = action.get("action_type", "unknown")
            params = action.get("parameters", {})
            
            # Create concise description
            if params:
                # Show first 2 key params only, truncate values to prevent token bloat
                param_keys = list(params.keys())[:2]
                param_str = ", ".join(
                    f"{k}={str(params[k])[:50]}" for k in param_keys
                )
                actions_desc.append(f"{i}. {action_type}({param_str})")
            else:
                actions_desc.append(f"{i}. {action_type}()")
        
        actions_text = "\n  ".join(actions_desc)
        
        return f"""💡 LEARNED SEQUENCE (Hint only - verify preconditions):
Intent: "{self.intent_text}"
Success rate: {self.success_count} times
Suggested actions:
  {actions_text}

⚠️ IMPORTANT: This is a suggestion based on past success. You MUST:
1. Verify current system state matches expected preconditions
2. Decide each action independently through OODA
3. Adapt if the situation has changed
4. Do NOT blindly follow - think and observe!"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "skill_id": self.skill_id,
            "intent_text": self.intent_text,
            "suggested_actions": self.suggested_actions,
            "context_hash": self.context_hash,
            "success_count": self.success_count,
            "last_used": self.last_used,
            "confidence": self.confidence,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SkillHint":
        """Create SkillHint from dictionary"""
        return SkillHint(
            skill_id=data["skill_id"],
            intent_text=data["intent_text"],
            suggested_actions=data["suggested_actions"],
            context_hash=data["context_hash"],
            success_count=data["success_count"],
            last_used=data["last_used"],
            confidence=data.get("confidence", 0.0),
        )


@dataclass
class SkillMetrics:
    """
    Metrics for skill hint usage and effectiveness.
    
    LEARNING-001: Track how skills are used as hints to improve LLM decisions.
    """
    
    # Retrieval metrics
    hints_retrieved: int = 0  # How many times skills were found and suggested
    hints_used: int = 0  # How many times the LLM followed the hint
    hints_adapted: int = 0  # How many times the LLM adapted the hint
    hints_rejected: int = 0  # How many times the LLM ignored the hint
    
    # Performance metrics
    avg_retrieval_time_ms: float = 0.0  # Average time to retrieve hints
    total_retrieval_time_ms: float = 0.0
    
    # Effectiveness metrics
    hint_follow_rate: float = 0.0  # Percentage of hints followed (hints_used / hints_retrieved)
    hint_adaptation_rate: float = 0.0  # Percentage of hints adapted (hints_adapted / hints_retrieved)
    
    # Cost savings
    llm_tokens_saved: int = 0  # Estimated tokens saved by providing hints
    
    def record_hint_retrieved(self, retrieval_time_ms: float) -> None:
        """Record that a skill hint was retrieved"""
        self.hints_retrieved += 1
        self.total_retrieval_time_ms += retrieval_time_ms
        self.avg_retrieval_time_ms = self.total_retrieval_time_ms / self.hints_retrieved
    
    def record_hint_used(self, tokens_saved: int = 0) -> None:
        """Record that the LLM followed the hint"""
        self.hints_used += 1
        self.llm_tokens_saved += tokens_saved
        self._update_rates()
    
    def record_hint_adapted(self, tokens_saved: int = 0) -> None:
        """Record that the LLM adapted the hint"""
        self.hints_adapted += 1
        self.llm_tokens_saved += tokens_saved
        self._update_rates()
    
    def record_hint_rejected(self) -> None:
        """Record that the LLM ignored the hint"""
        self.hints_rejected += 1
        self._update_rates()
    
    def _update_rates(self) -> None:
        """Update computed rates"""
        if self.hints_retrieved > 0:
            self.hint_follow_rate = self.hints_used / self.hints_retrieved
            self.hint_adaptation_rate = self.hints_adapted / self.hints_retrieved
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hints_retrieved": self.hints_retrieved,
            "hints_used": self.hints_used,
            "hints_adapted": self.hints_adapted,
            "hints_rejected": self.hints_rejected,
            "avg_retrieval_time_ms": self.avg_retrieval_time_ms,
            "total_retrieval_time_ms": self.total_retrieval_time_ms,
            "hint_follow_rate": self.hint_follow_rate,
            "hint_adaptation_rate": self.hint_adaptation_rate,
            "llm_tokens_saved": self.llm_tokens_saved,
        }
