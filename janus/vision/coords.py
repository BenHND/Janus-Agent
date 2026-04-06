"""
Coordinate Conversion Utilities for Vision System

This module provides universal coordinate conversion between different vision engines
and screen coordinate systems. Each vision engine (Apple Vision, Windows OCR, OmniParser)
returns bounding boxes in different formats and coordinate systems.

TICKET-SWITCH-NATIVE: Ensures consistent coordinate handling across platforms.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Union


@dataclass
class Point:
    """Represents a 2D point in screen coordinates"""
    x: int
    y: int


def normalize_coords(
    bbox: Union[Tuple, list],
    source_type: str,
    screen_width: int,
    screen_height: int
) -> Dict[str, Union[Tuple[int, int, int, int], Point]]:
    """
    Convert any bounding box to absolute pixel coordinates (Top-Left Origin).
    
    This function handles the coordinate system differences between:
    - Apple Vision: Normalized (0.0-1.0) with bottom-left origin (Cartesian)
    - Windows OCR: Absolute pixels with top-left origin
    - OmniParser/YOLO: Absolute pixels [x1, y1, x2, y2] format
    
    Args:
        bbox: Bounding box in source format (must have 4 elements)
              - Apple Vision: (x_min, y_min, width, height) normalized 0.0-1.0
              - Windows OCR: (x, y, width, height) in pixels
              - OmniParser: [x1, y1, x2, y2] in pixels (absolute, not normalized)
        source_type: One of 'apple_vision', 'windows_ocr', 'omniparser'
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
    
    Returns:
        Dictionary with:
        - "bbox": (x, y, width, height) in absolute pixels, top-left origin
        - "center": Point object with center coordinates for clicking
    
    Raises:
        ValueError: If bbox doesn't have exactly 4 elements or source_type is invalid
    
    Example:
        >>> # Apple Vision returns normalized coords with bottom-left origin
        >>> result = normalize_coords((0.1, 0.2, 0.3, 0.1), 'apple_vision', 1920, 1080)
        >>> result['center']  # Ready to click!
        Point(x=480, y=756)
    """
    # Validate input
    if len(bbox) != 4:
        raise ValueError(f"bbox must have exactly 4 elements, got {len(bbox)}")
    
    x, y, w, h = 0, 0, 0, 0

    if source_type == 'apple_vision':
        # Apple Vision returns normalized (0.0-1.0) with BOTTOM-LEFT origin (Cartesian)
        # Bbox format: (x_min, y_min, width, height) all normalized
        norm_x, norm_y, norm_w, norm_h = bbox
        
        # Convert to absolute pixels
        x = int(norm_x * screen_width)
        w = int(norm_w * screen_width)
        h = int(norm_h * screen_height)
        
        # Invert Y-axis: Apple uses bottom-left origin, screen uses top-left
        # Mathematical conversion from Cartesian (bottom-left) to screen (top-left):
        # - Apple Y=0 is at bottom, screen Y=0 is at top
        # - Apple bbox bottom edge: norm_y * screen_height
        # - Apple bbox top edge: (norm_y + norm_h) * screen_height
        # - Screen top edge position: screen_height - top_edge
        # Formula: screen_y = screen_height - (norm_y + norm_h) * screen_height
        y = int((1.0 - (norm_y + norm_h)) * screen_height)

    elif source_type == 'omniparser':
        # YOLO/OmniParser returns [x1, y1, x2, y2] in ABSOLUTE pixels (Top-Left)
        # Note: This expects absolute pixel coordinates, not normalized.
        # If your YOLO model outputs normalized coords, multiply by screen dimensions first.
        x1, y1, x2, y2 = bbox
        x = int(x1)
        y = int(y1)
        w = int(x2 - x1)
        h = int(y2 - y1)

    elif source_type == 'windows_ocr':
        # Windows OCR returns absolute pixels (Top-Left origin)
        # Bbox format: (x, y, width, height)
        x, y, w, h = bbox
        x, y, w, h = int(x), int(y), int(w), int(h)
    
    else:
        raise ValueError(
            f"Unknown source_type: {source_type}. "
            f"Must be one of: 'apple_vision', 'windows_ocr', 'omniparser'"
        )

    # Calculate center point for clicking
    center_x = x + (w // 2)
    center_y = y + (h // 2)

    return {
        "bbox": (x, y, w, h),
        "center": Point(center_x, center_y)
    }


def bbox_to_center(bbox: Tuple[int, int, int, int]) -> Point:
    """
    Quick helper to get center point from bbox in (x, y, w, h) format.
    
    Args:
        bbox: Bounding box as (x, y, width, height)
    
    Returns:
        Point with center coordinates
    """
    x, y, w, h = bbox
    return Point(x + (w // 2), y + (h // 2))


def validate_coords(point: Point, screen_width: int, screen_height: int) -> bool:
    """
    Validate that coordinates are within screen bounds.
    
    Args:
        point: Point to validate
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
    
    Returns:
        True if point is within screen bounds, False otherwise
    """
    return (0 <= point.x < screen_width) and (0 <= point.y < screen_height)
