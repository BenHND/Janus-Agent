"""
macOS Window Manager - Window management operations.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module handles window-related operations:
- Getting active window information
- Listing all windows
- Focusing/activating windows

Usage:
    from janus.platform.os.macos.window_manager import MacOSWindowManager
    
    manager = MacOSWindowManager(applescript_executor)
    result = manager.get_active_window()
"""

import logging
from typing import Optional

from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus, WindowInfo

logger = logging.getLogger(__name__)


class MacOSWindowManager:
    """
    Handles window management operations for macOS.
    
    Uses AppleScript and System Events to query and manipulate windows.
    """
    
    def __init__(self, applescript_executor, is_available_fn):
        """
        Initialize window manager.
        
        Args:
            applescript_executor: AppleScriptExecutor instance for running scripts
            is_available_fn: Function to check if macOS is available
        """
        self.executor = applescript_executor
        self.is_available = is_available_fn
    
    def get_active_window(self) -> SystemBridgeResult:
        """
        Get information about the currently active window.
        
        Returns:
            SystemBridgeResult with data["window"] containing WindowInfo
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            script = """
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set frontWindow to ""
                try
                    set frontWindow to name of front window of first application process whose frontmost is true
                end try
                return frontApp & "|" & frontWindow
            end tell
            """
            
            result = self.executor.execute(
                script,
                timeout=2.0,
                retries=0,
            )
            
            if self._is_success(result):
                output = result["stdout"].strip()
                parts = output.split("|", 1)
                
                app_name = parts[0].strip() if len(parts) >= 1 else ""
                window_title = parts[1].strip() if len(parts) >= 2 else ""
                
                window = WindowInfo(
                    title=window_title,
                    app_name=app_name,
                    is_active=True,
                )
                
                logger.debug(f"Active window: {app_name} - {window_title}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"window": window}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to get active window: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"get_active_window error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception getting active window: {str(e)}"
            )
    
    def list_windows(self) -> SystemBridgeResult:
        """
        Get list of all windows.
        
        Returns:
            SystemBridgeResult with data["windows"] containing list of WindowInfo
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            # Get all application processes and their windows
            script = """
            tell application "System Events"
                set windowList to {}
                set appList to every application process whose visible is true
                repeat with theApp in appList
                    set appName to name of theApp
                    try
                        set appWindows to name of every window of theApp
                        repeat with winName in appWindows
                            set end of windowList to appName & "|" & winName
                        end repeat
                    end try
                end repeat
                return windowList
            end tell
            """
            
            result = self.executor.execute(
                script,
                timeout=5.0,
                retries=0,
            )
            
            if self._is_success(result):
                output = result["stdout"].strip()
                windows = []
                
                if output:
                    # AppleScript returns comma-separated list
                    items = [item.strip() for item in output.split(",")]
                    for item in items:
                        if "|" in item:
                            parts = item.split("|", 1)
                            app_name = parts[0].strip()
                            window_title = parts[1].strip()
                            windows.append(WindowInfo(
                                title=window_title,
                                app_name=app_name,
                                is_active=False,
                            ))
                
                logger.debug(f"Found {len(windows)} windows")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"windows": windows}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to list windows: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"list_windows error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception listing windows: {str(e)}"
            )
    
    def _is_success(self, result: dict) -> bool:
        """Check if AppleScript executor result indicates success."""
        from janus.constants import ActionStatus
        return result.get("status") == ActionStatus.SUCCESS.value
