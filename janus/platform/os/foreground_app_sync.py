"""
Foreground App Sync Layer - Ensures macOS frontmost app matches agent's context

This module solves the critical problem of app synchronization:
- Agent believes Safari is active, but macOS has Chrome in front
- Actions go to wrong app, vision sees wrong content, reasoning is wrong
- This layer keeps reality and context in sync 100% of the time

Features:
- Read actual frontmost app from macOS via System Events
- Force an app to come to foreground
- Wait for an app to become frontmost with timeout
- Sync ExecutionContext with OS reality
- Detect and log mismatches for debugging

Usage:
    # Simple usage
    current_app = get_active_app()
    ensure_frontmost("Safari")
    wait_until_frontmost("Chrome", timeout=3.0)
    
    # With context sync
    sync = ForegroundAppSync()
    sync.sync_with_context(context)
"""

import logging
import platform
import time
from typing import Optional, Dict, Any, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular import issues during testing
if TYPE_CHECKING:
    from janus.platform.os.macos.applescript_executor import AppleScriptExecutor

from janus.constants import ActionStatus

logger = logging.getLogger(__name__)


class ForegroundAppSync:
    """
    Foreground app synchronization for macOS.
    
    Ensures the OS-level frontmost app matches what the agent believes is active.
    Critical for multi-app workflows, vision consistency, and reliable automation.
    """

    def __init__(
        self,
        default_timeout: float = 3.0,
        poll_interval: float = 0.1,
        enable_auto_sync: bool = True,
    ):
        """
        Initialize foreground app sync.
        
        Args:
            default_timeout: Default timeout for wait operations (seconds)
            poll_interval: Interval between status checks when waiting (seconds)
            enable_auto_sync: Automatically sync context when mismatch detected
        """
        self.default_timeout = default_timeout
        self.poll_interval = poll_interval
        self.enable_auto_sync = enable_auto_sync
        self.is_mac = platform.system() == "Darwin"
        
        if not self.is_mac:
            logger.warning("ForegroundAppSync: Not running on macOS - limited functionality")
        
        # Use AppleScript executor for reliable macOS automation
        # Lazy import to avoid pulling in heavy dependencies during testing
        self._applescript_executor = None
        
        logger.info(
            f"ForegroundAppSync initialized (timeout={default_timeout}s, "
            f"auto_sync={enable_auto_sync})"
        )

    @property
    def applescript_executor(self):
        """Lazy-load AppleScript executor to avoid heavy imports during testing."""
        if self._applescript_executor is None:
            # Import here to avoid circular dependencies and heavy imports
            from janus.platform.os.macos.applescript_executor import AppleScriptExecutor
            self._applescript_executor = AppleScriptExecutor()
        return self._applescript_executor

    def get_active_app(self) -> Optional[str]:
        """
        Get the currently frontmost application on macOS.
        
        Returns:
            Name of frontmost app, or None if detection failed
            
        Example:
            >>> sync = ForegroundAppSync()
            >>> app = sync.get_active_app()
            >>> print(app)
            "Google Chrome"
        """
        if not self.is_mac:
            logger.warning("get_active_app: Not on macOS, returning None")
            return None
            
        try:
            # Use System Events to get frontmost app
            script = """
            tell application "System Events"
                name of first application process whose frontmost is true
            end tell
            """
            
            result = self.applescript_executor.execute(
                script,
                timeout=2.0,  # Short timeout for status check
                retries=0,  # No retries for simple status check
            )
            
            if result["status"] == ActionStatus.SUCCESS.value:
                app_name = result["stdout"].strip()
                logger.debug(f"get_active_app: Detected frontmost app = '{app_name}'")
                return app_name
            else:
                logger.warning(f"get_active_app: AppleScript failed - {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"get_active_app: Exception - {e}", exc_info=True)
            return None

    def ensure_frontmost(self, app_name: str, timeout: Optional[float] = None) -> bool:
        """
        Ensure an application is frontmost by activating it.
        
        Args:
            app_name: Application name (e.g., "Safari", "Google Chrome")
            timeout: Optional timeout override (uses default if None)
            
        Returns:
            True if app is now frontmost, False otherwise
            
        Example:
            >>> sync = ForegroundAppSync()
            >>> success = sync.ensure_frontmost("Safari")
            >>> if not success:
            ...     print("Failed to bring Safari to front")
        """
        if not self.is_mac:
            logger.warning(f"ensure_frontmost: Not on macOS, cannot activate {app_name}")
            return False
            
        if timeout is None:
            timeout = self.default_timeout
            
        try:
            # Map common names to macOS names
            mapped_name = self._map_app_name(app_name)
            
            logger.info(f"ensure_frontmost: Activating '{mapped_name}'")
            
            # Activate the app
            # TICKET-FIX: Force activation with System Events to bypass background restrictions
            script = f'''
            tell application "{mapped_name}" to activate
            tell application "System Events"
                set frontmost of process "{mapped_name}" to true
            end tell
            '''
            result = self.applescript_executor.execute(
                script,
                timeout=timeout,
                retries=1,  # One retry for activation
            )
            
            if result["status"] != ActionStatus.SUCCESS.value:
                logger.error(f"ensure_frontmost: Failed to activate {mapped_name}")
                return False
            
            # Wait for app to become frontmost
            success = self.wait_until_frontmost(mapped_name, timeout=timeout)
            
            if success:
                logger.info(f"ensure_frontmost: '{mapped_name}' is now frontmost")
            else:
                logger.warning(
                    f"ensure_frontmost: '{mapped_name}' activated but did not become "
                    f"frontmost within {timeout}s"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"ensure_frontmost: Exception for {app_name} - {e}", exc_info=True)
            return False

    def wait_until_frontmost(
        self, app_name: str, timeout: Optional[float] = None
    ) -> bool:
        """
        Wait until an application becomes frontmost.
        
        Args:
            app_name: Application name to wait for
            timeout: Maximum time to wait (uses default if None)
            
        Returns:
            True if app became frontmost within timeout, False otherwise
            
        Example:
            >>> sync = ForegroundAppSync()
            >>> # After opening Safari...
            >>> if sync.wait_until_frontmost("Safari", timeout=5.0):
            ...     print("Safari is ready!")
        """
        if not self.is_mac:
            logger.warning(f"wait_until_frontmost: Not on macOS, cannot wait for {app_name}")
            return False
            
        if timeout is None:
            timeout = self.default_timeout
            
        mapped_name = self._map_app_name(app_name)
        start_time = time.time()
        
        logger.debug(f"wait_until_frontmost: Waiting for '{mapped_name}' (timeout={timeout}s)")
        
        while time.time() - start_time < timeout:
            current_app = self.get_active_app()
            
            if current_app == mapped_name:
                elapsed = time.time() - start_time
                logger.debug(
                    f"wait_until_frontmost: '{mapped_name}' became frontmost "
                    f"after {elapsed:.2f}s"
                )
                return True
            
            # Poll at regular interval
            time.sleep(self.poll_interval)
        
        # Timeout reached
        current_app = self.get_active_app()
        logger.warning(
            f"wait_until_frontmost: Timeout waiting for '{mapped_name}'. "
            f"Current frontmost: '{current_app}'"
        )
        return False

    def sync_with_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronize context's active_app with OS reality.
        
        This is the key function that prevents desynchronization issues.
        Call this before actions to ensure agent's belief matches reality.
        
        Args:
            context: Execution context dictionary (will be modified in-place)
            
        Returns:
            Dictionary with sync results:
            - "synced": bool - Whether sync was performed
            - "mismatch_detected": bool - Whether apps differed
            - "old_app": str - App in context before sync
            - "new_app": str - OS frontmost app (now in context)
            - "action_taken": str - What was done ("updated_context" or "forced_foreground")
            
        Example:
            >>> context = {"active_app": "Safari"}
            >>> sync = ForegroundAppSync()
            >>> result = sync.sync_with_context(context)
            >>> if result["mismatch_detected"]:
            ...     print(f"Fixed mismatch: {result['old_app']} -> {result['new_app']}")
        """
        if not self.is_mac:
            logger.warning("sync_with_context: Not on macOS, skipping sync")
            return {
                "synced": False,
                "mismatch_detected": False,
                "old_app": context.get("active_app"),
                "new_app": None,
                "action_taken": "none",
            }
        
        # Get OS reality
        frontmost_app = self.get_active_app()
        
        if frontmost_app is None:
            logger.warning("sync_with_context: Could not detect frontmost app")
            return {
                "synced": False,
                "mismatch_detected": False,
                "old_app": context.get("active_app"),
                "new_app": None,
                "action_taken": "detection_failed",
            }
        
        # Get context's belief
        context_app = context.get("active_app")
        
        # Check for mismatch
        if context_app is None:
            # Context has no app tracked - initialize it
            logger.info(f"sync_with_context: Initializing active_app to '{frontmost_app}'")
            context["active_app"] = frontmost_app
            return {
                "synced": True,
                "mismatch_detected": False,
                "old_app": None,
                "new_app": frontmost_app,
                "action_taken": "initialized",
            }
        
        # Normalize for comparison (case-insensitive)
        if context_app.lower() == frontmost_app.lower():
            # Apps match - all good!
            logger.debug(f"sync_with_context: Apps match ('{context_app}')")
            return {
                "synced": False,
                "mismatch_detected": False,
                "old_app": context_app,
                "new_app": frontmost_app,
                "action_taken": "none",
            }
        
        # MISMATCH DETECTED!
        logger.warning(
            f"⚠️  Foreground mismatch detected → resync triggered\n"
            f"   Context believes: '{context_app}'\n"
            f"   OS frontmost is:  '{frontmost_app}'"
        )
        
        # Decide strategy: force foreground or update context
        if self.enable_auto_sync:
            # Strategy: Try to force context app to foreground
            # (assumes agent intended this app to be active)
            logger.info(f"sync_with_context: Attempting to force '{context_app}' to foreground")
            success = self.ensure_frontmost(context_app, timeout=2.0)
            
            if success:
                logger.info(
                    f"✓ sync_with_context: Forced '{context_app}' to foreground "
                    f"(was '{frontmost_app}')"
                )
                return {
                    "synced": True,
                    "mismatch_detected": True,
                    "old_app": frontmost_app,
                    "new_app": context_app,
                    "action_taken": "forced_foreground",
                }
            else:
                # Couldn't force - update context to match reality
                logger.warning(
                    f"sync_with_context: Could not force '{context_app}' to foreground. "
                    f"Updating context to '{frontmost_app}'"
                )
                context["active_app"] = frontmost_app
                return {
                    "synced": True,
                    "mismatch_detected": True,
                    "old_app": context_app,
                    "new_app": frontmost_app,
                    "action_taken": "updated_context",
                }
        else:
            # Auto-sync disabled - just update context
            logger.info(
                f"sync_with_context: Auto-sync disabled. "
                f"Updating context '{context_app}' -> '{frontmost_app}'"
            )
            context["active_app"] = frontmost_app
            return {
                "synced": True,
                "mismatch_detected": True,
                "old_app": context_app,
                "new_app": frontmost_app,
                "action_taken": "updated_context",
            }

    def _map_app_name(self, app_name: str) -> str:
        """
        Map common app names to official macOS names.
        
        Args:
            app_name: Input app name (may be shorthand)
            
        Returns:
            Official macOS application name
        """
        # Mapping of common names to macOS names
        app_map = {
            "chrome": "Google Chrome",
            "vscode": "Visual Studio Code",
            "vs code": "Visual Studio Code", 
            "code": "Visual Studio Code",
            "terminal": "Terminal",
            "finder": "Finder",
            "safari": "Safari",
            "firefox": "Firefox",
            "slack": "Slack",
        }
        
        # Try lowercase match first
        mapped = app_map.get(app_name.lower())
        if mapped:
            return mapped
        
        # Return as-is if no mapping found
        return app_name


# Convenience module-level functions for simple usage

_default_sync = None


def _get_default_sync() -> ForegroundAppSync:
    """Get or create default ForegroundAppSync instance."""
    global _default_sync
    if _default_sync is None:
        _default_sync = ForegroundAppSync()
    return _default_sync


def get_active_app() -> Optional[str]:
    """
    Get currently frontmost application (convenience function).
    
    Returns:
        Name of frontmost app, or None if detection failed
    """
    return _get_default_sync().get_active_app()


def ensure_frontmost(app_name: str, timeout: Optional[float] = None) -> bool:
    """
    Ensure an application is frontmost (convenience function).
    
    Args:
        app_name: Application name
        timeout: Optional timeout override
        
    Returns:
        True if app is now frontmost, False otherwise
    """
    return _get_default_sync().ensure_frontmost(app_name, timeout)


def wait_until_frontmost(app_name: str, timeout: Optional[float] = None) -> bool:
    """
    Wait until an application becomes frontmost (convenience function).
    
    Args:
        app_name: Application name
        timeout: Maximum time to wait
        
    Returns:
        True if app became frontmost within timeout, False otherwise
    """
    return _get_default_sync().wait_until_frontmost(app_name, timeout)
