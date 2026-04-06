"""
Action Validator for contextual validation and confirmation
Implements safety checks before executing critical actions
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from janus.logging import get_logger


class ActionRisk(Enum):
    """Risk level for actions"""

    SAFE = "safe"  # Safe actions that don't require confirmation
    LOW = "low"  # Low risk, optional confirmation
    MEDIUM = "medium"  # Medium risk, recommended confirmation
    HIGH = "high"  # High risk, requires confirmation
    CRITICAL = "critical"  # Critical actions, strict confirmation required


@dataclass
class ValidationResult:
    """Result of action validation"""

    allowed: bool
    risk_level: ActionRisk
    requires_confirmation: bool
    warning_message: Optional[str] = None
    recommendation: Optional[str] = None


class ActionValidator:
    """
    Validates actions before execution
    Provides contextual validation and confirmation for critical actions
    """

    def __init__(
        self, auto_confirm_safe: bool = True, confirmation_callback: Optional[Callable] = None
    ):
        """
        Initialize action validator

        Args:
            auto_confirm_safe: Automatically confirm safe actions
            confirmation_callback: Function to call for user confirmation
        """
        self.logger = get_logger("action_validator")
        self.auto_confirm_safe = auto_confirm_safe
        self.confirmation_callback = confirmation_callback or self._default_confirmation

        # Action risk classifications
        self.risk_map = {
            # Safe actions
            "open_application": ActionRisk.SAFE,
            "open_url": ActionRisk.SAFE,
            "navigate_back": ActionRisk.SAFE,
            "navigate_forward": ActionRisk.SAFE,
            "refresh_page": ActionRisk.SAFE,
            "new_tab": ActionRisk.SAFE,
            "close_tab": ActionRisk.SAFE,
            "open_file": ActionRisk.SAFE,
            "goto_line": ActionRisk.SAFE,
            "save_file": ActionRisk.LOW,
            "close_file": ActionRisk.SAFE,
            "find_text": ActionRisk.SAFE,
            "list_files": ActionRisk.SAFE,
            "get_current_directory": ActionRisk.SAFE,
            # Low risk actions
            "click": ActionRisk.LOW,
            "copy": ActionRisk.SAFE,
            "paste": ActionRisk.LOW,
            "type_text": ActionRisk.LOW,
            "insert_text": ActionRisk.LOW,
            # Medium risk actions
            "execute_command": ActionRisk.MEDIUM,
            "change_directory": ActionRisk.LOW,
            "run_script": ActionRisk.MEDIUM,
            # High risk actions (destructive)
            "delete_file": ActionRisk.HIGH,
            "remove_file": ActionRisk.HIGH,
            "delete": ActionRisk.HIGH,
            "remove": ActionRisk.HIGH,
            "rm": ActionRisk.HIGH,
            # Critical actions (system-level)
            "shutdown": ActionRisk.CRITICAL,
            "reboot": ActionRisk.CRITICAL,
            "format": ActionRisk.CRITICAL,
            "wipe": ActionRisk.CRITICAL,
        }

        # Dangerous command patterns for terminal execution
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Delete root
            r"rm\s+-rf\s+\*",  # Delete all files
            r":\(\)\{\s*:\|:&\s*\};:",  # Fork bomb
            r"mkfs\.",  # Format filesystem
            r"dd\s+if=.*of=/dev/",  # Write to disk device
            r"chmod\s+-R\s+777",  # Dangerous permissions
            r"sudo\s+rm",  # Sudo delete
            r"curl.*\|\s*(?:bash|sh)",  # Pipe to shell
            r"wget.*\|\s*(?:bash|sh)",  # Pipe to shell
        ]

    def validate_action(
        self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate an action before execution

        Args:
            action: Action dictionary
            context: Optional context (session state, etc.)

        Returns:
            ValidationResult with validation decision
        """
        action_type = action.get("action", "unknown")

        # Get base risk level
        risk_level = self.risk_map.get(action_type, ActionRisk.MEDIUM)

        # Check for dangerous patterns in commands
        if action_type == "execute_command":
            command = action.get("command", "")
            risk_level, warning = self._check_command_safety(command)
            if warning:
                return ValidationResult(
                    allowed=False,
                    risk_level=risk_level,
                    requires_confirmation=True,
                    warning_message=warning,
                    recommendation="This command is potentially dangerous. Please review carefully.",
                )

        # Check if confirmation is required
        requires_confirmation = self._requires_confirmation(action, risk_level, context)

        # Auto-approve safe actions if configured
        if self.auto_confirm_safe and risk_level == ActionRisk.SAFE:
            return ValidationResult(
                allowed=True, risk_level=risk_level, requires_confirmation=False
            )

        # For actions requiring confirmation, use callback
        if requires_confirmation:
            allowed = self.confirmation_callback(action, risk_level, context)
            return ValidationResult(
                allowed=allowed,
                risk_level=risk_level,
                requires_confirmation=True,
                recommendation=self._get_recommendation(action, risk_level),
            )

        # Allow by default
        return ValidationResult(allowed=True, risk_level=risk_level, requires_confirmation=False)

    def validate_action_plan(
        self, actions: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """
        Validate multiple actions

        Args:
            actions: List of actions
            context: Optional context

        Returns:
            List of validation results
        """
        results = []
        for action in actions:
            result = self.validate_action(action, context)
            results.append(result)

            # Stop if any action is not allowed
            if not result.allowed:
                break

        return results

    def _check_command_safety(self, command: str) -> tuple:
        """
        Check if a terminal command is safe

        Args:
            command: Command string

        Returns:
            Tuple of (risk_level, warning_message)
        """
        command_lower = command.lower().strip()

        # Check dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command_lower):
                return (
                    ActionRisk.CRITICAL,
                    f"Dangerous command pattern detected: This command could be destructive",
                )

        # Check for destructive keywords
        destructive_keywords = ["delete", "remove", "rm", "format", "wipe", "destroy"]
        if any(keyword in command_lower for keyword in destructive_keywords):
            return (ActionRisk.HIGH, "Command contains destructive keywords")

        # Check for system-level operations
        system_keywords = ["shutdown", "reboot", "halt", "poweroff"]
        if any(keyword in command_lower for keyword in system_keywords):
            return (ActionRisk.CRITICAL, "System-level operation detected")

        # Check for sudo usage
        if command_lower.startswith("sudo "):
            return (ActionRisk.HIGH, "Command uses elevated privileges (sudo)")

        return (ActionRisk.MEDIUM, None)

    def _requires_confirmation(
        self, action: Dict[str, Any], risk_level: ActionRisk, context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Determine if action requires confirmation

        Args:
            action: Action dictionary
            risk_level: Risk level
            context: Optional context

        Returns:
            True if confirmation required
        """
        # Critical and high risk always require confirmation
        if risk_level in [ActionRisk.CRITICAL, ActionRisk.HIGH]:
            return True

        # Medium risk may require confirmation based on context
        if risk_level == ActionRisk.MEDIUM:
            # Check if action affects important files or directories
            action_type = action.get("action")
            if action_type in ["execute_command", "run_script"]:
                return True

        # Low risk and safe don't require confirmation
        return False

    def _get_recommendation(self, action: Dict[str, Any], risk_level: ActionRisk) -> str:
        """
        Get recommendation for action

        Args:
            action: Action dictionary
            risk_level: Risk level

        Returns:
            Recommendation string
        """
        action_type = action.get("action", "unknown")

        if risk_level == ActionRisk.CRITICAL:
            return f"⚠️  CRITICAL: Action '{action_type}' is highly destructive. Confirm you want to proceed."
        elif risk_level == ActionRisk.HIGH:
            return f"⚠️  HIGH RISK: Action '{action_type}' may have significant consequences. Review carefully."
        elif risk_level == ActionRisk.MEDIUM:
            return f"ℹ️  MEDIUM RISK: Action '{action_type}' will make changes. Confirm to proceed."
        else:
            return f"✓ Action '{action_type}' is safe to execute."

    def _default_confirmation(
        self, action: Dict[str, Any], risk_level: ActionRisk, context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Default confirmation callback (auto-deny critical actions)

        Args:
            action: Action dictionary
            risk_level: Risk level
            context: Optional context

        Returns:
            True if action is confirmed
        """
        # In default mode, deny critical and high-risk actions
        if risk_level in [ActionRisk.CRITICAL, ActionRisk.HIGH]:
            self.logger.warning(f"Action requires manual confirmation: {action.get('action')}")
            self.logger.warning(f"Risk level: {risk_level.value}")
            self.logger.info("Use interactive mode for confirmation.")
            return False

        # Allow medium and low risk
        return True

    def set_confirmation_callback(self, callback: Callable):
        """
        Set custom confirmation callback

        Args:
            callback: Function that takes (action, risk_level, context) and returns bool
        """
        self.confirmation_callback = callback

    def classify_action(self, action_type: str) -> ActionRisk:
        """
        Classify action by risk level

        Args:
            action_type: Type of action

        Returns:
            ActionRisk level
        """
        return self.risk_map.get(action_type, ActionRisk.MEDIUM)
