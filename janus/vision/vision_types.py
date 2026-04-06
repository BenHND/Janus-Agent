"""
Vision Types - Shared data types for vision modules

This module contains shared data classes and enums used across
the vision action mapping system.

Created as part of TICKET-REVIEW-001 refactoring to avoid duplication.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .element_locator import ElementMatch


class ElementType(Enum):
    """Types of UI elements that can be detected"""

    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    TEXT = "text"
    IMAGE = "image"
    ICON = "icon"
    MENU = "menu"
    ANY = "any"


@dataclass
class VisualAttributes:
    """Visual attributes for element matching"""

    element_type: Optional[ElementType] = None
    color: Optional[Tuple[int, int, int]] = None  # RGB color
    size: Optional[Tuple[int, int]] = None  # (width, height) range
    position: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height) region
    confidence_threshold: float = 50.0


@dataclass
class ActionResult:
    """Result of a vision-based action"""

    success: bool
    action: str
    element: Optional[ElementMatch] = None
    message: str = ""
    error: Optional[str] = None
    retry_count: int = 0
    verification: Optional[Dict[str, Any]] = None
