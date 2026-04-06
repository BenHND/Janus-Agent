"""
Custom exception hierarchy for Janus.

This module defines a comprehensive exception hierarchy for proper error
handling throughout the application. All Janus-specific exceptions inherit
from JanusError for easy catching of any application-specific error.

Exception messages are automatically filtered to prevent exposure of
sensitive data such as API keys, tokens, and passwords.

Exception Hierarchy:
    JanusError (base)
    ├── CommandError
    │   ├── ParsingError
    │   ├── ExecutionError
    │   └── ValidationError
    ├── ConfigError
    ├── MemoryError (not to be confused with built-in MemoryError)
    ├── IntegrationError
    ├── AudioError
    ├── VisionError
    └── AutomationError
"""

from typing import Any, Dict, Optional


def _filter_sensitive_data(text: str) -> str:
    """
    Filter sensitive data from exception messages

    This is a lightweight version that doesn't import the full secrets_filter
    to avoid circular dependencies. It performs basic pattern matching.

    Args:
        text: Text that may contain sensitive data

    Returns:
        Filtered text with sensitive data redacted
    """
    import re

    # Basic patterns for common secrets - matching the ones in secrets_filter
    patterns = [
        (
            r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{8,})',
            lambda m: m.group(1) + "***REDACTED***" + (m.group(3) if len(m.groups()) >= 3 else ""),
        ),
        (
            r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']{4,})',
            lambda m: m.group(1) + "***REDACTED***" + (m.group(3) if len(m.groups()) >= 3 else ""),
        ),
        (
            r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{10,})',
            lambda m: m.group(1) + "***REDACTED***" + (m.group(3) if len(m.groups()) >= 3 else ""),
        ),
        (r"(bearer\s+)([a-zA-Z0-9_\-\.]{20,})", lambda m: m.group(1) + "***REDACTED***"),
        (r"sk-[a-zA-Z0-9]{10,}", lambda m: "***REDACTED***"),  # OpenAI keys
        (r"sk-ant-[a-zA-Z0-9\-_]{10,}", lambda m: "***REDACTED***"),  # Anthropic keys
    ]

    filtered = text
    for pattern, replacement in patterns:
        if callable(replacement):
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        else:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

    return filtered


class JanusError(Exception):
    """
    Base exception for all Janus-specific errors.

    All custom exceptions in Janus should inherit from this class.
    This allows for catching any Janus-specific error with a single
    except clause while still allowing standard Python exceptions to
    propagate normally.

    Exception messages are automatically filtered to prevent exposure
    of sensitive data such as API keys and tokens.

    Attributes:
        message: Human-readable error message (filtered)
        error_code: Optional error code for programmatic handling
        details: Optional dictionary with additional error context (filtered)
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize JanusError.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional dictionary with additional error context
        """
        # Filter sensitive data from message
        self.message = _filter_sensitive_data(message)
        self.error_code = error_code
        # Filter sensitive data from details
        self.details = self._filter_details(details) if details else {}
        super().__init__(self.message)

    def _filter_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from details dictionary"""
        if not isinstance(details, dict):
            return details

        sensitive_keys = {
            "api_key",
            "apikey",
            "api-key",
            "password",
            "passwd",
            "pwd",
            "secret",
            "secret_key",
            "token",
            "auth_token",
            "bearer",
            "authorization",
            "private_key",
        }

        filtered = {}
        for key, value in details.items():
            key_lower = key.lower().replace("-", "_")
            if any(sk in key_lower for sk in sensitive_keys):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, str):
                filtered[key] = _filter_sensitive_data(value)
            elif isinstance(value, dict):
                filtered[key] = self._filter_details(value)
            else:
                filtered[key] = value

        return filtered

    def __str__(self):
        """Return string representation of error."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class CommandError(JanusError):
    """
    Base exception for command-related errors.

    Raised when there's an error in command processing, including
    parsing, execution, or validation failures.
    """

    pass


class ParsingError(CommandError):
    """
    Exception raised when command parsing fails.

    This occurs when the system cannot understand or parse a user command
    into actionable intents.

    Examples:
        - Unrecognized command syntax
        - Ambiguous command interpretation
        - Missing required parameters
    """

    pass


class ExecutionError(CommandError):
    """
    Exception raised when command execution fails.

    This occurs when a parsed command cannot be executed successfully,
    either due to system constraints, application state, or runtime errors.

    Examples:
        - Application not responding
        - UI element not found
        - System permission denied
        - Timeout during execution
    """

    pass


class ValidationError(CommandError):
    """
    Exception raised when command validation fails.

    This occurs when a command is syntactically correct but fails
    validation checks (e.g., safety checks, risk assessment).

    Examples:
        - Dangerous command blocked
        - Invalid parameter values
        - Precondition not met
    """

    pass


class ConfigError(JanusError):
    """
    Exception raised when configuration is invalid or cannot be loaded.

    This occurs when there are issues with configuration files, settings,
    or initialization parameters.

    Examples:
        - Missing configuration file
        - Invalid configuration value
        - Type mismatch in settings
        - Required setting not provided
    """

    pass


class JanusMemoryError(JanusError):
    """
    Exception raised when memory/persistence operations fail.

    Note: Named JanusMemoryError to avoid confusion with Python's
    built-in MemoryError which is for out-of-memory conditions.

    This occurs when there are issues with session management, database
    operations, or persistent storage.

    Examples:
        - Database connection failure
        - Session data corruption
        - Storage quota exceeded
        - Invalid session ID
    """

    pass


class IntegrationError(JanusError):
    """
    Exception raised when external integrations fail.

    This occurs when there are issues integrating with external services,
    APIs, or system components.

    Examples:
        - API request failure
        - Service unavailable
        - Authentication failure
        - Network timeout
    """

    pass


class AudioError(JanusError):
    """
    Exception raised when audio operations fail.

    This occurs when there are issues with audio recording, playback,
    or processing (STT/TTS).

    Examples:
        - Microphone not available
        - Audio device initialization failure
        - Speech recognition failure
        - TTS engine error
    """

    pass


class VisionError(JanusError):
    """
    Exception raised when vision/OCR operations fail.

    This occurs when there are issues with screen capture, OCR,
    or vision-based automation.

    Examples:
        - Screenshot capture failure
        - OCR engine not available
        - Element not found on screen
        - Vision model loading failure
    """

    pass


class AutomationError(JanusError):
    """
    Exception raised when automation operations fail.

    This occurs when there are issues with UI automation, keyboard/mouse
    control, or application interaction.

    Examples:
        - PyAutoGUI operation failure
        - AppleScript execution error
        - Window focus failure
        - Automation permission denied
    """

    pass


class SecurityException(JanusError):
    """
    Exception raised when a command is blocked for security reasons.

    This occurs when the sandbox security layer detects a forbidden
    or potentially destructive command that should never be executed.

    Examples:
        - rm -rf / (destructive delete)
        - mkfs (format filesystem)
        - dd if=... of=/dev/... (raw disk write)
        - format (Windows format command)
        - Fork bombs
    """

    pass
