"""
macOS Bridge Modules - Decomposed macOS system bridge components.

TICKET-REVIEW-002: Review and decompose macos_bridge.py

This package contains the decomposed macOS Bridge functionality,
organized into thematic modules:
- macos_types: Shared types and constants
- app_manager: Application management operations
- window_manager: Window management operations
- keyboard_manager: Keyboard input operations
- clipboard_manager: Clipboard operations

The main MacOSBridge class in janus.os.macos_bridge coordinates these modules
to provide a unified API.
"""

from janus.platform.os.macos.macos_types import SPECIAL_KEY_CODES, APP_NAME_MAP

__all__ = [
    "SPECIAL_KEY_CODES",
    "APP_NAME_MAP",
]
