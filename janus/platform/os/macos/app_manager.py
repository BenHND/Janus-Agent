"""
macOS Application Manager - Application management operations.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module handles application-related operations:
- Opening/launching applications
- Closing/quitting applications  
- Getting list of running applications
- Application name mapping

Usage:
    from janus.platform.os.macos.app_manager import MacOSAppManager
    
    manager = MacOSAppManager(applescript_executor)
    result = manager.open_app("Safari")
"""

import logging
from typing import Optional

from janus.platform.os.macos.macos_types import APP_NAME_MAP
from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus

logger = logging.getLogger(__name__)


class MacOSAppManager:
    """
    Handles application management operations for macOS.
    
    Uses AppleScript via AppleScriptExecutor to launch, quit, and query
    applications on macOS.
    """
    
    def __init__(self, applescript_executor, is_available_fn):
        """
        Initialize application manager.
        
        Args:
            applescript_executor: AppleScriptExecutor instance for running scripts
            is_available_fn: Function to check if macOS is available
        """
        self.executor = applescript_executor
        self.is_available = is_available_fn
    
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Open/launch an application using AppleScript.
        
        Args:
            app_name: Name of the application to open
            timeout: Optional timeout override
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        timeout = timeout or 10.0
        mapped_name = self.map_app_name(app_name)
        
        try:
            script = f'tell application "{mapped_name}" to activate'
            result = self.executor.execute(
                script,
                timeout=timeout,
                retries=1,
            )
            
            if self._is_success(result):
                logger.info(f"Opened app: {mapped_name}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"app_name": mapped_name}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to open {mapped_name}: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"open_app error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception opening {app_name}: {str(e)}"
            )
    
    def close_app(self, app_name: str) -> SystemBridgeResult:
        """
        Close/quit an application using AppleScript.
        
        Args:
            app_name: Name of the application to close
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        mapped_name = self.map_app_name(app_name)
        
        try:
            script = f'tell application "{mapped_name}" to quit'
            result = self.executor.execute(
                script,
                timeout=5.0,
                retries=0,
            )
            
            if self._is_success(result):
                logger.info(f"Closed app: {mapped_name}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"app_name": mapped_name}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to close {mapped_name}: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"close_app error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception closing {app_name}: {str(e)}"
            )
    
    def get_running_apps(self) -> SystemBridgeResult:
        """
        Get list of currently running applications.
        
        Returns:
            SystemBridgeResult with data["apps"] containing list of app names
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            script = """
            tell application "System Events"
                get name of every application process
            end tell
            """
            
            result = self.executor.execute(
                script,
                timeout=2.0,
                retries=0,
            )
            
            if self._is_success(result):
                output = result["stdout"].strip()
                # AppleScript returns comma-separated list
                apps = [app.strip() for app in output.split(",")]
                logger.debug(f"Found {len(apps)} running apps")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"apps": sorted(apps)}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to get running apps: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"get_running_apps error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception getting running apps: {str(e)}"
            )
    
    def map_app_name(self, app_name: str) -> str:
        """
        Map common app names to official macOS names.
        
        Public method for normalizing application names.
        
        Args:
            app_name: Input app name (may be shorthand)
            
        Returns:
            Official macOS application name
        """
        mapped = APP_NAME_MAP.get(app_name.lower())
        if mapped:
            return mapped
        return app_name
    
    # Backward compatibility alias
    def _map_app_name(self, app_name: str) -> str:
        """
        Map common app names to official macOS names.
        
        Deprecated: Use map_app_name() instead.
        This method is kept for backward compatibility.
        
        Args:
            app_name: Input app name (may be shorthand)
            
        Returns:
            Official macOS application name
        """
        return self.map_app_name(app_name)
    
    def _is_success(self, result: dict) -> bool:
        """Check if AppleScript executor result indicates success."""
        from janus.constants import ActionStatus
        return result.get("status") == ActionStatus.SUCCESS.value
