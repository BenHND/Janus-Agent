"""
Overlay UI types and enums

These types can be imported without requiring PySide6/Qt,
making them testable in headless environments.
"""

from enum import Enum


class MicState(str, Enum):
    """Microphone button states"""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    MUTED = "muted"
    LOADING = "loading"
    ERROR = "error"


class StatusState(str, Enum):
    """Status bar states"""

    IDLE = "idle"
    LISTENING = "listening"
    LOOKING = "looking"  # Vision/OCR in progress (TICKET-UX-001)
    THINKING = "thinking"
    ACTING = "acting"
    LOADING = "loading"
    ERROR = "error"


__all__ = ["MicState", "StatusState"]
