"""
AppleScript Executor - Centralized utility for stable AppleScript automation
MAC-06: Stabilization of macOS automation (Finder, Chrome, Terminal)

Features:
- Configurable timeouts to prevent hanging
- Intelligent retry logic with exponential backoff
- Proper AppleScript error parsing
- Execution time logging
- Reduced fixed delays for 2x speed improvement
- Internationalized error detection via locale configuration
"""

import logging
import subprocess
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from janus.constants import ActionStatus
from janus.resources.locale_loader import get_locale_loader

logger = logging.getLogger(__name__)


class AppleScriptError(Exception):
    """Custom exception for AppleScript execution errors"""

    pass


class AppleScriptExecutor:
    """
    Centralized AppleScript executor with timeout, retry, and error handling

    Features:
    - Explicit timeouts (default 10s, never hangs)
    - Smart retry logic (1-2 retries with exponential backoff)
    - Error parsing from AppleScript stderr
    - Execution time tracking and logging
    """
    
    # Cache locale loader as class attribute for performance
    _locale_loader = None

    def __init__(
        self,
        default_timeout: float = 10.0,
        max_retries: int = 2,
        retry_delay: float = 0.5,
        enable_logging: bool = True,
    ):
        """
        Initialize AppleScript executor

        Args:
            default_timeout: Default timeout for osascript calls (seconds)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
            enable_logging: Whether to log execution details
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_logging = enable_logging

    def execute(
        self,
        script: str,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        retry_on_error: bool = True,
        error_handler: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Execute AppleScript with timeout, retry, and error handling

        Args:
            script: AppleScript code to execute
            timeout: Timeout in seconds (uses default if None)
            retries: Number of retries (uses default if None)
            retry_on_error: Whether to retry on errors
            error_handler: Optional function to check if error is retryable

        Returns:
            Dict with status, stdout, stderr, execution_time, and retry_count
        """
        timeout = timeout if timeout is not None else self.default_timeout
        max_retries = retries if retries is not None else self.max_retries

        attempt = 0
        last_error = None
        total_start = datetime.now()

        while attempt <= max_retries:
            try:
                if self.enable_logging:
                    logger.debug(f"AppleScript execution attempt {attempt + 1}/{max_retries + 1}")

                start_time = datetime.now()

                # Execute osascript with timeout
                result = subprocess.run(
                    ["osascript", "-e", script], capture_output=True, text=True, timeout=timeout
                )

                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()

                # Check return code
                if result.returncode == 0:
                    if self.enable_logging:
                        logger.info(
                            f"AppleScript success in {execution_time:.3f}s "
                            f"(attempt {attempt + 1})"
                        )

                    return {
                        "status": ActionStatus.SUCCESS.value,
                        "stdout": result.stdout.strip(),
                        "stderr": result.stderr.strip(),
                        "execution_time": execution_time,
                        "total_time": (end_time - total_start).total_seconds(),
                        "retry_count": attempt,
                        "returncode": result.returncode,
                    }
                else:
                    # Parse error from stderr
                    error_msg = self._parse_error(result.stderr)

                    # Check if error is retryable
                    should_retry = retry_on_error and attempt < max_retries

                    if error_handler:
                        should_retry = should_retry and error_handler(error_msg)

                    if should_retry:
                        if self.enable_logging:
                            logger.warning(
                                f"AppleScript error on attempt {attempt + 1}: {error_msg}. "
                                f"Retrying..."
                            )

                        # Exponential backoff
                        delay = self.retry_delay * (2**attempt)
                        time.sleep(delay)
                        attempt += 1
                        last_error = error_msg
                        continue
                    else:
                        if self.enable_logging:
                            logger.error(
                                f"AppleScript failed in {execution_time:.3f}s: {error_msg}"
                            )

                        return {
                            "status": ActionStatus.FAILED.value,
                            "stdout": result.stdout.strip(),
                            "stderr": result.stderr.strip(),
                            "error": error_msg,
                            "execution_time": execution_time,
                            "total_time": (end_time - total_start).total_seconds(),
                            "retry_count": attempt,
                            "returncode": result.returncode,
                        }

            except subprocess.TimeoutExpired:
                if self.enable_logging:
                    logger.error(f"AppleScript timeout after {timeout}s on attempt {attempt + 1}")

                # Timeout is usually not retryable (app is frozen)
                if attempt < max_retries and retry_on_error:
                    delay = self.retry_delay * (2**attempt)
                    time.sleep(delay)
                    attempt += 1
                    last_error = f"Timeout after {timeout}s"
                    continue
                else:
                    total_time = (datetime.now() - total_start).total_seconds()
                    return {
                        "status": ActionStatus.FAILED.value,
                        "error": f"Timeout after {timeout}s",
                        "execution_time": timeout,
                        "total_time": total_time,
                        "retry_count": attempt,
                        "timeout": True,
                    }

            except Exception as e:
                if self.enable_logging:
                    logger.error(f"Unexpected error in AppleScript execution: {e}")

                total_time = (datetime.now() - total_start).total_seconds()
                return {
                    "status": ActionStatus.FAILED.value,
                    "error": str(e),
                    "total_time": total_time,
                    "retry_count": attempt,
                    "exception": True,
                }

        # Max retries exceeded
        total_time = (datetime.now() - total_start).total_seconds()
        return {
            "status": ActionStatus.FAILED.value,
            "error": f"Max retries exceeded. Last error: {last_error}",
            "total_time": total_time,
            "retry_count": attempt,
            "max_retries_exceeded": True,
        }

    def execute_simple(self, script: str, timeout: Optional[float] = None) -> bool:
        """
        Simple execution that returns True on success, False on failure

        Args:
            script: AppleScript code to execute
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        result = self.execute(script, timeout)
        return result.get("status") == "success"

    def execute_with_result(self, script: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Execute and return stdout, or None on failure

        Args:
            script: AppleScript code to execute
            timeout: Timeout in seconds

        Returns:
            stdout string on success, None on failure
        """
        result = self.execute(script, timeout)
        if result.get("status") == "success":
            return result.get("stdout")
        return None

    def _parse_error(self, stderr: str) -> str:
        """
        Parse AppleScript error from stderr

        Args:
            stderr: Standard error output from osascript

        Returns:
            Cleaned error message
        """
        if not stderr:
            return "Unknown error"

        # AppleScript errors often have format: "line:column: error message"
        # Extract the actual error message
        lines = stderr.strip().split("\n")

        # Try to extract meaningful error message
        for line in lines:
            if "error" in line.lower() or "execution error" in line.lower():
                # Remove line/column information
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    return parts[2].strip()
                return line.strip()

        # Return first non-empty line if no specific error found
        for line in lines:
            if line.strip():
                return line.strip()

        return stderr.strip()

    @staticmethod
    def is_application_error(error_msg: str, language: str = "en") -> bool:
        """
        Check if error is related to application not responding
        
        Error patterns are loaded from locale configuration for internationalization.

        Args:
            error_msg: Error message
            language: Language code for error patterns (default: "en")

        Returns:
            True if it's an application error (potentially retryable)
        """
        # Load application error patterns from locale configuration (cached at class level)
        if AppleScriptExecutor._locale_loader is None:
            AppleScriptExecutor._locale_loader = get_locale_loader()
        
        app_error_patterns = AppleScriptExecutor._locale_loader.get_keywords(
            "applescript_app_errors", language=language
        )

        error_lower = error_msg.lower()
        return any(pattern in error_lower for pattern in app_error_patterns)

    @staticmethod
    def is_timeout_error(result: Dict[str, Any]) -> bool:
        """
        Check if result indicates a timeout

        Args:
            result: Result dictionary from execute()

        Returns:
            True if timeout occurred
        """
        return result.get("timeout", False) or "timeout" in result.get("error", "").lower()


# Singleton instance for global use
_default_executor: Optional[AppleScriptExecutor] = None


def get_executor() -> AppleScriptExecutor:
    """
    Get the default AppleScript executor instance

    Returns:
        AppleScriptExecutor instance
    """
    global _default_executor
    if _default_executor is None:
        _default_executor = AppleScriptExecutor()
    return _default_executor


def execute_applescript(
    script: str, timeout: Optional[float] = None, retries: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to execute AppleScript with default executor

    Args:
        script: AppleScript code
        timeout: Timeout in seconds
        retries: Number of retries

    Returns:
        Result dictionary
    """
    return get_executor().execute(script, timeout, retries)
