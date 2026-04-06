"""
macOS Clipboard Manager - Clipboard operations.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module handles clipboard-related operations:
- Getting clipboard text
- Setting clipboard text

Usage:
    from janus.platform.os.macos.clipboard_manager import MacOSClipboardManager
    
    manager = MacOSClipboardManager()
    result = manager.get_clipboard()
"""

import logging
import subprocess

from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus

logger = logging.getLogger(__name__)


class MacOSClipboardManager:
    """
    Handles clipboard operations for macOS.
    
    Uses macOS command-line tools pbcopy and pbpaste for clipboard access.
    """
    
    def __init__(self, is_available_fn):
        """
        Initialize clipboard manager.
        
        Args:
            is_available_fn: Function to check if macOS is available
        """
        self.is_available = is_available_fn
    
    def get_clipboard(self) -> SystemBridgeResult:
        """
        Get text from clipboard using pbpaste.
        
        Returns:
            SystemBridgeResult with data["text"] containing clipboard text
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            
            if result.returncode == 0:
                text = result.stdout
                logger.debug(f"Got clipboard text ({len(text)} chars)")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": text}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"pbpaste failed: {result.stderr}"
                )
                
        except Exception as e:
            logger.error(f"get_clipboard error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception getting clipboard: {str(e)}"
            )
    
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """
        Set clipboard text using pbcopy.
        
        Args:
            text: Text to write to clipboard
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            result = subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                capture_output=True,
                timeout=2.0,
            )
            
            if result.returncode == 0:
                logger.debug(f"Set clipboard text ({len(text)} chars)")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text_length": len(text)}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"pbcopy failed: {result.stderr}"
                )
                
        except Exception as e:
            logger.error(f"set_clipboard error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception setting clipboard: {str(e)}"
            )
