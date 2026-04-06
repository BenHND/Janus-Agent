"""
Unified Action Schema for Janus

⚠️ DEPRECATED: This module is kept for backward compatibility only.

The Single Source of Truth (SSOT) for actions is now:
  {module, action, args} format from module_action_schema.py

Do NOT use UnifiedAction in new code. Instead:
- Use module_action_schema.py for action definitions
- Use ActionCoordinator with {module, action, args} format
- Use AgentRegistry.execute(module, action, args) for execution

This module provides a unified schema for actions across:
- LLM reasoning and planning
- Pipeline execution
- Vision-based actions
- Adapter execution

Feature 3: Unified Action Schema
Issue: FONCTIONNALITÉS MANQUANTES - #3

The schema standardizes how actions are represented throughout the system:
{
    "type": "click",
    "target": "Envoyer",
    "method": "vision|adapter|position",
    "parameters": {...}
}
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ActionMethod(Enum):
    """Method for executing an action"""

    VISION = "vision"  # Use vision/OCR to find and interact with element
    ADAPTER = "adapter"  # Use application-specific adapter
    POSITION = "position"  # Use direct screen position (x, y coordinates)
    KEYBOARD = "keyboard"  # Use keyboard shortcuts
    API = "api"  # Use application API (AppleScript, JavaScript, etc.)
    AUTO = "auto"  # Automatically choose best method


class ActionType(Enum):
    """Standard action types"""

    # Basic interactions
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    DRAG = "drag"

    # Text operations
    TYPE = "type"
    COPY = "copy"
    PASTE = "paste"
    SELECT = "select"

    # Navigation
    SCROLL = "scroll"
    SCROLL_UNTIL = "scroll_until"
    SWIPE = "swipe"

    # Application control
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SWITCH_APP = "switch_app"
    OPEN_TAB = "open_tab"
    CLOSE_TAB = "close_tab"
    SWITCH_TAB = "switch_tab"

    # Advanced operations
    WAIT_FOR = "wait_for"
    VERIFY_STATE = "verify_state"
    EXTRACT = "extract"
    FIND_ELEMENT = "find_element"

    # Workflow control
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    RETRY = "retry"
    
    # Task scheduling (TICKET-FEAT-002)
    SCHEDULE_TASK = "schedule_task"
    CANCEL_TASK = "cancel_task"


class VerificationType(Enum):
    """Types of verification for actions"""

    NONE = "none"  # No verification
    ELEMENT_VISIBLE = "element_visible"  # Verify element is visible
    ELEMENT_HIDDEN = "element_hidden"  # Verify element is hidden
    TEXT_PRESENT = "text_present"  # Verify text is present
    STATE_CHANGED = "state_changed"  # Verify screen/state changed
    NO_ERROR = "no_error"  # Verify no error dialog appeared
    CUSTOM = "custom"  # Custom verification function


@dataclass
class ActionTarget:
    """
    Unified target specification for actions

    Supports multiple ways to specify a target:
    - text: Text content or description
    - selector: CSS selector or XPath
    - position: Exact coordinates (x, y)
    - region: Bounding box (x, y, width, height)
    - reference: Reference to element from previous action
    """

    text: Optional[str] = None
    selector: Optional[str] = None
    position: Optional[tuple[int, int]] = None
    region: Optional[tuple[int, int, int, int]] = None
    reference: Optional[str] = None
    fuzzy_match: bool = True
    case_sensitive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActionVerification:
    """
    Verification specification for post-action validation

    Feature 2: Vision Post-Action Validation
    """

    type: VerificationType = VerificationType.NONE
    timeout_ms: int = 5000
    retry_on_failure: bool = False
    expected_text: Optional[str] = None
    expected_state: Optional[Dict[str, Any]] = None
    verification_target: Optional[ActionTarget] = None
    custom_verifier: Optional[str] = None  # Name of custom verification function

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "type": self.type.value,
            "timeout_ms": self.timeout_ms,
            "retry_on_failure": self.retry_on_failure,
        }
        if self.expected_text:
            result["expected_text"] = self.expected_text
        if self.expected_state:
            result["expected_state"] = self.expected_state
        if self.verification_target:
            result["verification_target"] = self.verification_target.to_dict()
        if self.custom_verifier:
            result["custom_verifier"] = self.custom_verifier
        return result


@dataclass
class ActionRetryPolicy:
    """
    Retry policy for robust action execution

    Feature 5: Robust Chaining
    """

    max_retries: int = 3
    retry_delay_ms: int = 500
    exponential_backoff: bool = True
    retry_on_errors: List[str] = field(
        default_factory=lambda: ["element_not_found", "timeout", "verification_failed"]
    )
    fallback_method: Optional[ActionMethod] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class UnifiedAction:
    """
    Unified action schema for all Janus actions

    This is the standard format for actions throughout the system:
    - LLM generates UnifiedActions
    - Pipeline processes UnifiedActions
    - Executors receive UnifiedActions
    - Vision validates UnifiedActions

    Example:
        action = UnifiedAction(
            type=ActionType.CLICK,
            target=ActionTarget(text="Envoyer"),
            method=ActionMethod.VISION,
            verification=ActionVerification(type=VerificationType.STATE_CHANGED)
        )
    """

    # Core action specification
    type: ActionType
    target: Optional[ActionTarget] = None
    method: ActionMethod = ActionMethod.AUTO

    # Action parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Verification and reliability
    verification: Optional[ActionVerification] = None
    retry_policy: Optional[ActionRetryPolicy] = None

    # Metadata
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    module: Optional[str] = None  # Target module (chrome, vscode, etc.)
    timestamp: datetime = field(default_factory=datetime.now)

    # Context for chaining
    depends_on: List[str] = field(default_factory=list)  # IDs of dependent actions
    output_key: Optional[str] = None  # Key to store output in context

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = {
            "action_id": self.action_id,
            "type": self.type.value,
            "method": self.method.value,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.target:
            result["target"] = self.target.to_dict()
        if self.verification:
            result["verification"] = self.verification.to_dict()
        if self.retry_policy:
            result["retry_policy"] = self.retry_policy.to_dict()
        if self.description:
            result["description"] = self.description
        if self.module:
            result["module"] = self.module
        if self.depends_on:
            result["depends_on"] = self.depends_on
        if self.output_key:
            result["output_key"] = self.output_key

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedAction":
        """Create UnifiedAction from dictionary"""
        # Convert enum strings to enums
        action_type = ActionType(data["type"]) if isinstance(data["type"], str) else data["type"]
        method = (
            ActionMethod(data.get("method", "auto"))
            if isinstance(data.get("method"), str)
            else data.get("method", ActionMethod.AUTO)
        )

        # Extract target if present
        target = None
        if "target" in data and data["target"]:
            target_data = data["target"]
            target = ActionTarget(**target_data) if isinstance(target_data, dict) else target_data

        # Extract verification if present
        verification = None
        if "verification" in data and data["verification"]:
            ver_data = data["verification"]
            if isinstance(ver_data, dict):
                ver_type = VerificationType(ver_data["type"])
                verification = ActionVerification(
                    type=ver_type,
                    timeout_ms=ver_data.get("timeout_ms", 5000),
                    retry_on_failure=ver_data.get("retry_on_failure", False),
                    expected_text=ver_data.get("expected_text"),
                    expected_state=ver_data.get("expected_state"),
                    custom_verifier=ver_data.get("custom_verifier"),
                )

        # Extract retry policy if present
        retry_policy = None
        if "retry_policy" in data and data["retry_policy"]:
            retry_data = data["retry_policy"]
            if isinstance(retry_data, dict):
                retry_policy = ActionRetryPolicy(**retry_data)

        # Create action
        return cls(
            type=action_type,
            target=target,
            method=method,
            parameters=data.get("parameters", {}),
            verification=verification,
            retry_policy=retry_policy,
            action_id=data.get("action_id", str(uuid.uuid4())),
            description=data.get("description"),
            module=data.get("module"),
            depends_on=data.get("depends_on", []),
            output_key=data.get("output_key"),
        )


@dataclass
class ActionChain:
    """
    Chain of actions for workflow execution

    Supports:
    - Sequential execution
    - Parallel execution
    - Conditional branching
    - Retry and fallback
    - Context passing between actions

    Feature 5: Robust Chaining
    """

    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: List[UnifiedAction] = field(default_factory=list)
    execution_mode: str = "sequential"  # sequential, parallel, conditional
    stop_on_failure: bool = True
    context: Dict[str, Any] = field(default_factory=dict)  # Shared context

    def add_action(self, action: UnifiedAction):
        """Add action to chain"""
        self.actions.append(action)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chain_id": self.chain_id,
            "actions": [action.to_dict() for action in self.actions],
            "execution_mode": self.execution_mode,
            "stop_on_failure": self.stop_on_failure,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionChain":
        """Create ActionChain from dictionary"""
        actions = [UnifiedAction.from_dict(a) for a in data.get("actions", [])]
        return cls(
            chain_id=data.get("chain_id", str(uuid.uuid4())),
            actions=actions,
            execution_mode=data.get("execution_mode", "sequential"),
            stop_on_failure=data.get("stop_on_failure", True),
            context=data.get("context", {}),
        )


# Convenience functions for creating common actions


def click_action(
    target: Union[str, ActionTarget], method: ActionMethod = ActionMethod.AUTO, verify: bool = True
) -> UnifiedAction:
    """Create a click action"""
    if isinstance(target, str):
        target = ActionTarget(text=target)

    verification = ActionVerification(type=VerificationType.STATE_CHANGED) if verify else None

    return UnifiedAction(
        type=ActionType.CLICK, target=target, method=method, verification=verification
    )


def type_action(text: str, target: Optional[Union[str, ActionTarget]] = None) -> UnifiedAction:
    """Create a type action"""
    target_obj = None
    if target:
        target_obj = ActionTarget(text=target) if isinstance(target, str) else target

    return UnifiedAction(type=ActionType.TYPE, target=target_obj, parameters={"text": text})


def wait_for_action(target: Union[str, ActionTarget], timeout_ms: int = 10000) -> UnifiedAction:
    """Create a wait_for action"""
    if isinstance(target, str):
        target = ActionTarget(text=target)

    return UnifiedAction(
        type=ActionType.WAIT_FOR,
        target=target,
        parameters={"timeout_ms": timeout_ms},
        verification=ActionVerification(
            type=VerificationType.ELEMENT_VISIBLE, timeout_ms=timeout_ms
        ),
    )


def verify_state_action(expected_state: Dict[str, Any]) -> UnifiedAction:
    """Create a verify_state action"""
    return UnifiedAction(
        type=ActionType.VERIFY_STATE,
        verification=ActionVerification(
            type=VerificationType.CUSTOM, expected_state=expected_state
        ),
    )


def scroll_until_action(target: Union[str, ActionTarget], max_scrolls: int = 10) -> UnifiedAction:
    """Create a scroll_until action"""
    if isinstance(target, str):
        target = ActionTarget(text=target)

    return UnifiedAction(
        type=ActionType.SCROLL_UNTIL,
        target=target,
        parameters={"max_scrolls": max_scrolls},
        retry_policy=ActionRetryPolicy(max_retries=max_scrolls, retry_delay_ms=300),
    )


def open_tab_action(url: Optional[str] = None) -> UnifiedAction:
    """Create an open_tab action"""
    return UnifiedAction(
        type=ActionType.OPEN_TAB,
        module="chrome",
        parameters={"url": url} if url else {},
        verification=ActionVerification(type=VerificationType.STATE_CHANGED),
    )
