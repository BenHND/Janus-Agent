"""
SystemInfo Helper for E2E Tests

This module provides system inspection utilities for verifying agent actions.
It wraps platform-specific operations to check:
- Process status (is app running?)
- Browser state (current URL)
- Window content (text verification)
- Application control (kill, launch)

TICKET-PRE-AUDIT-000: Golden Master Testing support
"""

import asyncio
import logging
import platform
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class SystemInfo:
    """
    System information and control for E2E test verification.
    
    This class provides "ground truth" verification methods to check
    whether the agent successfully performed requested actions.
    """
    
    def __init__(self):
        """Initialize SystemInfo helper"""
        self.platform = platform.system()
        logger.info(f"SystemInfo initialized for platform: {self.platform}")
    
    async def is_process_running(self, process_name: str) -> bool:
        """
        Check if a process is currently running.
        
        Args:
            process_name: Name of the process (e.g., "Calculator", "Safari")
        
        Returns:
            True if process is running, False otherwise
        """
        if self.platform == "Darwin":
            return await self._is_process_running_macos(process_name)
        else:
            logger.warning(f"is_process_running not implemented for {self.platform}")
            return False
    
    async def _is_process_running_macos(self, process_name: str) -> bool:
        """Check if process is running on macOS using pgrep"""
        try:
            # Use pgrep to check if process exists
            result = await asyncio.create_subprocess_exec(
                "pgrep", "-x", process_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            # pgrep returns 0 if process found, 1 if not found
            is_running = result.returncode == 0
            logger.info(f"Process '{process_name}' running: {is_running}")
            return is_running
        except Exception as e:
            logger.error(f"Error checking process '{process_name}': {e}")
            return False
    
    async def kill_process(self, process_name: str) -> bool:
        """
        Terminate a process by name.
        
        Args:
            process_name: Name of the process to kill
        
        Returns:
            True if process was killed, False otherwise
        """
        if self.platform == "Darwin":
            return await self._kill_process_macos(process_name)
        else:
            logger.warning(f"kill_process not implemented for {self.platform}")
            return False
    
    async def _kill_process_macos(self, process_name: str) -> bool:
        """Kill process on macOS using pkill"""
        try:
            # Use pkill to terminate process
            result = await asyncio.create_subprocess_exec(
                "pkill", "-x", process_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            # Wait a moment for process to terminate
            await asyncio.sleep(0.5)
            
            # Verify process is gone
            is_running = await self.is_process_running(process_name)
            success = not is_running
            
            logger.info(f"Kill process '{process_name}': {'success' if success else 'failed'}")
            return success
        except Exception as e:
            logger.error(f"Error killing process '{process_name}': {e}")
            return False
    
    async def get_browser_url(self, browser_name: str = "Safari") -> Optional[str]:
        """
        Get the current URL from a browser.
        
        Args:
            browser_name: Name of the browser ("Safari" or "Chrome")
        
        Returns:
            Current URL string, or None if unable to retrieve
        """
        if self.platform == "Darwin":
            return await self._get_browser_url_macos(browser_name)
        else:
            logger.warning(f"get_browser_url not implemented for {self.platform}")
            return None
    
    async def _get_browser_url_macos(self, browser_name: str) -> Optional[str]:
        """Get browser URL on macOS using AppleScript"""
        try:
            if browser_name.lower() == "safari":
                # Enhanced script with error handling for no tabs
                script = '''
                tell application "Safari"
                    if (count of windows) is 0 then
                        return ""
                    end if
                    if (count of tabs of window 1) is 0 then
                        return ""
                    end if
                    return URL of current tab of front window
                end tell
                '''
            elif browser_name.lower() == "chrome":
                # Enhanced script with error handling for no tabs
                script = '''
                tell application "Google Chrome"
                    if (count of windows) is 0 then
                        return ""
                    end if
                    if (count of tabs of window 1) is 0 then
                        return ""
                    end if
                    return URL of active tab of front window
                end tell
                '''
            else:
                logger.warning(f"Browser '{browser_name}' not supported")
                return None
            
            result = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                url = stdout.decode().strip()
                if url:  # Only log if we got a URL
                    logger.info(f"Browser URL: {url}")
                    return url
                else:
                    logger.info(f"Browser has no open tabs/windows")
                    return None
            else:
                logger.error(f"Failed to get browser URL: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"Error getting browser URL: {e}")
            return None
    
    async def get_active_window_text(self) -> Optional[str]:
        """
        Get text content from the active window.
        
        This is a simplified version that attempts to get window title
        or accessible text content.
        
        Returns:
            Text content from active window, or None if unable to retrieve
        """
        if self.platform == "Darwin":
            return await self._get_active_window_text_macos()
        else:
            logger.warning(f"get_active_window_text not implemented for {self.platform}")
            return None
    
    async def _get_active_window_text_macos(self) -> Optional[str]:
        """Get active window text on macOS using AppleScript"""
        try:
            # Try to get window title and accessible text
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set frontWindow to ""
                try
                    set frontWindow to name of front window of application process frontApp
                end try
                return frontApp & " - " & frontWindow
            end tell
            '''
            
            result = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                text = stdout.decode().strip()
                logger.info(f"Active window text: {text}")
                return text
            else:
                logger.error(f"Failed to get window text: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"Error getting window text: {e}")
            return None
    
    async def get_frontmost_app(self) -> Optional[str]:
        """
        Get the name of the frontmost (active) application.
        
        Returns:
            Name of frontmost app, or None if unable to retrieve
        """
        if self.platform == "Darwin":
            return await self._get_frontmost_app_macos()
        else:
            logger.warning(f"get_frontmost_app not implemented for {self.platform}")
            return None
    
    async def _get_frontmost_app_macos(self) -> Optional[str]:
        """Get frontmost app on macOS using AppleScript"""
        try:
            script = 'tell application "System Events" to return name of first application process whose frontmost is true'
            
            result = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                app_name = stdout.decode().strip()
                logger.info(f"Frontmost app: {app_name}")
                return app_name
            else:
                logger.error(f"Failed to get frontmost app: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"Error getting frontmost app: {e}")
            return None
