"""
macOS Keyboard Manager - Keyboard input operations.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module handles keyboard-related operations:
- Typing text
- Pressing individual keys
- Key combinations with modifiers
- Special key support

Usage:
    from janus.platform.os.macos.keyboard_manager import MacOSKeyboardManager
    
    manager = MacOSKeyboardManager(applescript_executor)
    result = manager.type_text("Hello, World!")
"""

import logging
from typing import List, Optional

from janus.platform.os.macos.macos_types import SPECIAL_KEY_CODES
from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus

logger = logging.getLogger(__name__)


class MacOSKeyboardManager:
    """
    Handles keyboard input operations for macOS.
    
    Uses System Events via AppleScript to simulate keyboard input.
    """
    
    def __init__(self, applescript_executor, is_available_fn):
        """
        Initialize keyboard manager.
        
        Args:
            applescript_executor: AppleScriptExecutor instance for running scripts
            is_available_fn: Function to check if macOS is available
        """
        self.executor = applescript_executor
        self.is_available = is_available_fn
    
    def type_text(self, text: str) -> SystemBridgeResult:
        """
        Type text using System Events keystroke.
        
        Args:
            text: Text to type
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            # Escape quotes and backslashes for AppleScript
            escaped_text = text.replace('\\', '\\\\').replace('"', '\\"')
            
            script = f'tell application "System Events" to keystroke "{escaped_text}"'
            
            result = self.executor.execute(
                script,
                timeout=10.0,  # Longer timeout for typing
                retries=0,
            )
            
            if self._is_success(result):
                logger.debug(f"Typed text ({len(text)} characters)")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text_length": len(text)}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to type text: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"type_text error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception typing text: {str(e)}"
            )
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Press a key or key combination.
        
        Args:
            key: Key to press (character or special key name)
            modifiers: Optional list of modifiers (command, control, option, shift)
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            # Check if this is a special key that needs key code
            key_lower = key.lower()
            key_code = SPECIAL_KEY_CODES.get(key_lower)
            
            # Build AppleScript for keystrokes
            if key_code is not None:
                # Use key code for special keys
                if modifiers:
                    modifier_str = ", ".join(f"{m} down" for m in modifiers)
                    script = f'tell application "System Events" to key code {key_code} using {{{modifier_str}}}'
                else:
                    script = f'tell application "System Events" to key code {key_code}'
            else:
                # Use keystroke for regular characters
                if modifiers:
                    modifier_str = ", ".join(f"{m} down" for m in modifiers)
                    script = f'tell application "System Events" to keystroke "{key}" using {{{modifier_str}}}'
                else:
                    script = f'tell application "System Events" to keystroke "{key}"'
            
            result = self.executor.execute(
                script,
                timeout=5.0,
                retries=0,
            )
            
            if self._is_success(result):
                logger.debug(f"Pressed key: {key} (modifiers: {modifiers})")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"key": key, "modifiers": modifiers}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to press key: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"press_key error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception pressing key: {str(e)}"
            )
    
    def send_keys(self, keys: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Send keyboard input to the active window.
        
        This is an alias for press_key().
        
        Args:
            keys: Keys to send
            modifiers: Optional list of modifier keys
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.press_key(keys, modifiers)
    
    def _is_success(self, result: dict) -> bool:
        """Check if AppleScript executor result indicates success."""
        from janus.constants import ActionStatus
        return result.get("status") == ActionStatus.SUCCESS.value
