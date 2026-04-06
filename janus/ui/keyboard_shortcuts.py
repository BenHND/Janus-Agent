"""
Keyboard Shortcut Handler for Janus

Provides global keyboard shortcuts for undo/redo functionality.
- Cmd+Z (or Ctrl+Z on non-Mac) for undo
- Cmd+Shift+Z (or Ctrl+Shift+Z on non-Mac) for redo
"""

import logging
import platform
from typing import Callable, Optional

from pynput import keyboard

logger = logging.getLogger(__name__)


class KeyboardShortcutHandler:
    """
    Handles global keyboard shortcuts for Janus

    Provides shortcuts for:
    - Undo: Cmd+Z (macOS) or Ctrl+Z (Windows/Linux)
    - Redo: Cmd+Shift+Z (macOS) or Ctrl+Shift+Z (Windows/Linux)
    """

    def __init__(
        self,
        on_undo: Optional[Callable[[], None]] = None,
        on_redo: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize keyboard shortcut handler

        Args:
            on_undo: Callback function for undo action
            on_redo: Callback function for redo action
        """
        self.on_undo = on_undo
        self.on_redo = on_redo
        self.listener = None
        self._is_mac = platform.system() == "Darwin"

        # Track modifier keys
        self.cmd_pressed = False
        self.ctrl_pressed = False
        self.shift_pressed = False

        logger.info(f"KeyboardShortcutHandler initialized (platform: {platform.system()})")

    def start(self):
        """Start listening for keyboard shortcuts"""
        if self.listener is not None:
            logger.warning("Keyboard shortcut listener already running")
            return

        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.listener.start()
        logger.info("Keyboard shortcut listener started")

        # Log shortcuts for user reference
        if self._is_mac:
            logger.info("Shortcuts: Cmd+Z (undo), Cmd+Shift+Z (redo)")
        else:
            logger.info("Shortcuts: Ctrl+Z (undo), Ctrl+Shift+Z (redo)")

    def stop(self):
        """Stop listening for keyboard shortcuts"""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            logger.info("Keyboard shortcut listener stopped")

    def _on_press(self, key):
        """Handle key press events"""
        try:
            # Track modifier keys
            if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
                self.cmd_pressed = True
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = True

            # Check for undo/redo shortcuts
            if hasattr(key, "char") and key.char == "z":
                # Determine if the appropriate modifier is pressed
                modifier_pressed = self.cmd_pressed if self._is_mac else self.ctrl_pressed

                if modifier_pressed:
                    if self.shift_pressed:
                        # Redo shortcut
                        self._trigger_redo()
                    else:
                        # Undo shortcut
                        self._trigger_undo()
        except AttributeError:
            # Special keys don't have char attribute
            pass
        except Exception as e:
            logger.error(f"Error handling key press: {e}", exc_info=True)

    def _on_release(self, key):
        """Handle key release events"""
        try:
            # Track modifier keys
            if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
                self.cmd_pressed = False
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = False
        except Exception as e:
            logger.error(f"Error handling key release: {e}", exc_info=True)

    def _trigger_undo(self):
        """Trigger undo action"""
        if self.on_undo:
            logger.info("Undo shortcut triggered")
            try:
                self.on_undo()
            except Exception as e:
                logger.error(f"Error executing undo callback: {e}", exc_info=True)
        else:
            logger.warning("Undo shortcut triggered but no callback registered")

    def _trigger_redo(self):
        """Trigger redo action"""
        if self.on_redo:
            logger.info("Redo shortcut triggered")
            try:
                self.on_redo()
            except Exception as e:
                logger.error(f"Error executing redo callback: {e}", exc_info=True)
        else:
            logger.warning("Redo shortcut triggered but no callback registered")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
