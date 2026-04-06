"""
macOS Bridge Types - Shared types and constants for macOS Bridge modules.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module contains shared types, constants, and enumerations used across
the macOS Bridge modules.

Usage:
    from janus.platform.os.macos.macos_types import SPECIAL_KEY_CODES
"""

from typing import Dict

# Map of special key names to AppleScript key codes
# Used for keyboard operations that require key codes instead of characters
SPECIAL_KEY_CODES: Dict[str, int] = {
    "return": 36,
    "enter": 76,  # Numpad enter
    "tab": 48,
    "escape": 53,
    "esc": 53,
    "delete": 51,  # Backspace
    "backspace": 51,
    "forwarddelete": 117,
    "space": 49,
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
    "home": 115,
    "end": 119,
    "pageup": 116,
    "pagedown": 121,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}

# Map of common app names to official macOS names
# Used to normalize application names for AppleScript
APP_NAME_MAP: Dict[str, str] = {
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
