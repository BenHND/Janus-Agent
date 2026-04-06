"""
System Information - Grounding context for agent awareness

This module provides real-time system state information to enable the agent
to understand contextual references like "this tab", "that window", "here", etc.

TICKET-403: System Context (Grounding) injection
TICKET-AUDIT-004: Enhanced with available apps and running processes

Features:
- Active application detection (macOS)
- Active window title extraction
- Browser URL detection (Safari, Chrome, Firefox)
- Available applications listing
- Running processes detection
- Structured context dictionary for LLM consumption

The agent can now "see" what's on screen and respond to implicit references.
"""

import logging
import platform
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def get_active_context(clipboard_manager=None) -> Dict[str, Any]:
    """
    Get the current system context (active app, window title, browser URL, clipboard).
    
    This function provides the "grounding" context that allows the agent to
    understand what the user is referring to when they say "this", "that", "here", etc.
    
    TICKET-FEAT-001: Smart Clipboard integration - captures recent clipboard content
    at wake word time to enable implicit references like "explain this code".
    
    Args:
        clipboard_manager: Optional ClipboardManager for smart clipboard capture
    
    Returns:
        Dictionary with system context:
        {
            "active_app": str,        # Name of frontmost application
            "window_title": str,      # Title of active window
            "browser_url": str,       # Current URL (if browser is active)
            "clipboard": str,         # Recent clipboard content (<10s old)
            "platform": str,          # Operating system
            "error": str,             # Error message if detection failed
        }
    
    Example:
        >>> context = get_active_context()
        >>> print(context)
        {
            "active_app": "Safari",
            "window_title": "Example Page",
            "browser_url": "https://www.example.com/page",
            "clipboard": "def hello(): print('world')",
            "platform": "Darwin"
        }
    """
    context = {
        "active_app": None,
        "window_title": None,
        "browser_url": None,
        "clipboard": None,
        "platform": platform.system(),
    }
    
    system = platform.system()
    
    if system == "Darwin":
        # macOS implementation using AppleScript
        context = _get_active_context_macos()
    else:
        # Unsupported platform
        logger.warning(f"System context detection not implemented for platform: {system}")
        context["error"] = f"Platform {system} not supported"
    
    # TICKET-FEAT-001: Capture recent clipboard content (Smart Clipboard)
    if clipboard_manager:
        try:
            recent_clipboard = clipboard_manager.get_recent_clipboard(max_age_seconds=10.0)
            if recent_clipboard:
                # Truncate long clipboard content to avoid bloating the context
                max_clipboard_length = 2000
                if len(recent_clipboard) > max_clipboard_length:
                    context["clipboard"] = recent_clipboard[:max_clipboard_length] + "..."
                else:
                    context["clipboard"] = recent_clipboard
                logger.debug(f"Smart Clipboard: Added recent clipboard content ({len(recent_clipboard)} chars)")
        except Exception as e:
            logger.warning(f"Failed to capture clipboard content: {e}")
    
    return context


def _get_active_context_macos() -> Dict[str, Any]:
    """
    Get active context on macOS using AppleScript and NSWorkspace.
    
    Uses AppleScript to query:
    1. System Events for active app name and window title
    2. Safari/Chrome for current URL (if they are active)
    
    Returns:
        Dictionary with macOS system context
    """
    context = {
        "active_app": None,
        "window_title": None,
        "browser_url": None,
        "platform": "Darwin",
    }
    
    try:
        # Import AppleScript executor for macOS automation
        from janus.platform.os.macos.applescript_executor import AppleScriptExecutor
        executor = AppleScriptExecutor()
        
        # Step 1: Get active app and window title
        script_app_info = """
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            set frontWindow to ""
            try
                set frontWindow to name of front window of first application process whose frontmost is true
            end try
            return frontApp & "|" & frontWindow
        end tell
        """
        
        result = executor.execute(script_app_info, timeout=2.0, retries=0)
        
        if result["status"] == "success":
            output = result["stdout"].strip()
            parts = output.split("|", 1)
            
            if len(parts) >= 1:
                context["active_app"] = parts[0].strip()
            if len(parts) >= 2:
                context["window_title"] = parts[1].strip()
            
            logger.debug(
                f"System context: app='{context['active_app']}', "
                f"window='{context['window_title']}'"
            )
        else:
            logger.warning(f"Failed to get app info: {result.get('error')}")
            context["error"] = "Failed to detect active app"
            return context
        
        # Step 2: If browser is active, get current URL
        active_app = context.get("active_app", "")
        
        if active_app in ["Safari", "Safari Technology Preview"]:
            url = _get_safari_url(executor)
            if url:
                context["browser_url"] = url
        
        elif active_app in ["Google Chrome", "Chrome"]:
            url = _get_chrome_url(executor)
            if url:
                context["browser_url"] = url
        
        elif "Firefox" in active_app:
            # Firefox URL extraction via window title
            # Firefox doesn't expose URL via AppleScript like Safari/Chrome,
            # but the window title contains the page title which provides useful context
            url = _get_firefox_url(executor)
            if url:
                context["browser_url"] = url
        
        return context
        
    except ImportError:
        logger.warning("AppleScriptExecutor not available - cannot get system context")
        context["error"] = "AppleScript not available"
        return context
    except Exception as e:
        logger.error(f"Error getting system context: {e}", exc_info=True)
        context["error"] = str(e)
        return context


def _get_safari_url(executor) -> Optional[str]:
    """
    Get the current URL from Safari.
    
    Args:
        executor: AppleScriptExecutor instance
        
    Returns:
        Current URL string, or None if failed
    """
    try:
        script = """
        tell application "Safari"
            if (count of windows) > 0 then
                get URL of current tab of front window
            end if
        end tell
        """
        
        result = executor.execute(script, timeout=2.0, retries=0)
        
        if result["status"] == "success":
            url = result["stdout"].strip()
            logger.debug(f"Safari URL: {url}")
            return url
        else:
            logger.debug(f"Could not get Safari URL: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.debug(f"Exception getting Safari URL: {e}")
        return None


def _get_chrome_url(executor) -> Optional[str]:
    """
    Get the current URL from Google Chrome.
    
    Args:
        executor: AppleScriptExecutor instance
        
    Returns:
        Current URL string, or None if failed
    """
    try:
        script = """
        tell application "Google Chrome"
            if (count of windows) > 0 then
                get URL of active tab of front window
            end if
        end tell
        """
        
        result = executor.execute(script, timeout=2.0, retries=0)
        
        if result["status"] == "success":
            url = result["stdout"].strip()
            logger.debug(f"Chrome URL: {url}")
            return url
        else:
            logger.debug(f"Could not get Chrome URL: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.debug(f"Exception getting Chrome URL: {e}")
        return None


def _get_firefox_url(executor) -> Optional[str]:
    """
    Get the current URL/page info from Firefox.
    
    Firefox doesn't expose URL via AppleScript like Safari/Chrome.
    However, we can extract useful page information from the window title.
    
    Note: Firefox window titles typically show "Page Title - Mozilla Firefox"
    or similar format. We extract the page title as a proxy for context.
    
    For full URL extraction, Firefox would require:
    - Browser extension with native messaging
    - Remote debugging protocol (Firefox DevTools Protocol)
    - UI automation to read address bar (fragile)
    
    Args:
        executor: AppleScriptExecutor instance
        
    Returns:
        Page title/context string, or None if failed
    """
    try:
        script = """
        tell application "System Events"
            tell process "Firefox"
                if exists (window 1) then
                    return name of window 1
                end if
            end tell
        end tell
        """
        
        result = executor.execute(script, timeout=2.0, retries=0)
        
        if result["status"] == "success":
            window_title = result["stdout"].strip()
            # Firefox window titles typically end with " - Mozilla Firefox" or " — Mozilla Firefox"
            # Remove the browser name suffix to get page title
            for suffix in [" - Mozilla Firefox", " — Mozilla Firefox", " - Firefox", " — Firefox"]:
                if window_title.endswith(suffix):
                    page_title = window_title[:-len(suffix)]
                    logger.debug(f"Firefox page title: {page_title}")
                    return f"Firefox: {page_title}"
            
            # If no standard suffix found, return as-is with Firefox prefix
            logger.debug(f"Firefox window: {window_title}")
            return f"Firefox: {window_title}"
        else:
            logger.debug(f"Could not get Firefox window title: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.debug(f"Exception getting Firefox window info: {e}")
        return None


def get_available_applications() -> List[str]:
    """
    Get list of available applications that can be launched.
    
    TICKET-AUDIT-004: Added for prompt enrichment with available apps.
    
    Returns:
        List of application names (e.g., ["Safari", "Chrome", "VS Code"])
    
    Note:
        - macOS: Returns apps from /Applications and ~/Applications
        - Other platforms: Returns empty list (not implemented)
    """
    system = platform.system()
    
    if system == "Darwin":
        return _get_available_applications_macos()
    else:
        logger.debug(f"get_available_applications not implemented for platform: {system}")
        return []


def _get_available_applications_macos() -> List[str]:
    """
    Get available applications on macOS.
    
    Scans /Applications and ~/Applications directories for .app bundles.
    
    Returns:
        List of application names without .app extension
    """
    import os
    from pathlib import Path
    
    apps = []
    app_dirs = [
        Path("/Applications"),
        Path.home() / "Applications"
    ]
    
    for app_dir in app_dirs:
        if not app_dir.exists():
            continue
        
        try:
            for item in app_dir.iterdir():
                if item.suffix == ".app" and item.is_dir():
                    # Remove .app extension
                    app_name = item.stem
                    if app_name not in apps:
                        apps.append(app_name)
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not scan {app_dir}: {e}")
            continue
    
    return sorted(apps)


def get_running_processes() -> List[str]:
    """
    Get list of currently running applications.
    
    TICKET-AUDIT-004: Added for prompt enrichment with running processes.
    
    Returns:
        List of running process names
    
    Note:
        - macOS: Uses AppleScript to query System Events
        - Other platforms: Uses psutil if available
    """
    system = platform.system()
    
    if system == "Darwin":
        return _get_running_processes_macos()
    else:
        return _get_running_processes_generic()


def _get_running_processes_macos() -> List[str]:
    """
    Get running processes on macOS using AppleScript.
    
    Returns:
        List of running application names
    """
    try:
        from janus.platform.os.macos.applescript_executor import AppleScriptExecutor
        executor = AppleScriptExecutor()
        
        script = """
        tell application "System Events"
            get name of every application process
        end tell
        """
        
        result = executor.execute(script, timeout=2.0, retries=0)
        
        if result["status"] == "success":
            output = result["stdout"].strip()
            # AppleScript returns comma-separated list
            processes = [p.strip() for p in output.split(",")]
            logger.debug(f"Found {len(processes)} running processes")
            return sorted(processes)
        else:
            logger.warning(f"Failed to get running processes: {result.get('error')}")
            return []
            
    except ImportError:
        logger.debug("AppleScriptExecutor not available - falling back to generic method")
        return _get_running_processes_generic()
    except Exception as e:
        logger.error(f"Error getting running processes: {e}")
        return []


def _get_running_processes_generic() -> List[str]:
    """
    Get running processes using psutil (cross-platform).
    
    Returns:
        List of running process names
    """
    try:
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and name not in processes:
                    processes.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return sorted(processes)
        
    except ImportError:
        logger.debug("psutil not available - cannot get running processes")
        return []
    except Exception as e:
        logger.error(f"Error getting running processes with psutil: {e}")
        return []


# Convenience function for quick testing
if __name__ == "__main__":
    import json
    print("Testing system context detection...")
    context = get_active_context()
    print(json.dumps(context, indent=2, ensure_ascii=False))
    
    print("\nTesting available applications...")
    apps = get_available_applications()
    print(f"Found {len(apps)} available applications")
    print(apps[:10])  # Show first 10
    
    print("\nTesting running processes...")
    processes = get_running_processes()
    print(f"Found {len(processes)} running processes")
    print(processes[:10])  # Show first 10
