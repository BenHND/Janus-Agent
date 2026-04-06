"""
Vision module for screen capture and OCR-based automation fallback
Includes Phase 22: Vision Cognitive & Perception IA

New features:
- Async Vision Monitor: Real-time popup/error detection
- Post-Action Validator: Vision-based action verification
- TICKET-CLEANUP-VISION: OmniParser unified vision engine (YOLOv8 + Florence-2)

Note: Imports are lazy to avoid requiring all dependencies upfront
"""


# Lazy imports to avoid loading dependencies unnecessarily
def _import_screenshot_engine():
    from .screenshot_engine import ScreenshotEngine

    return ScreenshotEngine


def _import_ocr_engine():
    from .native_ocr_adapter import NativeOCRAdapter as OCREngine

    return OCREngine


def _import_element_locator():
    from .element_locator import ElementLocator

    return ElementLocator


def _import_vision_cognitive_engine():
    from .vision_cognitive_engine import VisionCognitiveEngine

    return VisionCognitiveEngine


def _import_visual_error_detector():
    from .visual_error_detector import VisualErrorDetector

    return VisualErrorDetector


def _import_vision_config_wizard():
    from .vision_config_wizard import VisionConfig, VisionConfigWizard

    return VisionConfigWizard, VisionConfig


def _import_vision_action_mapper():
    from .vision_action_mapper import (
        ActionResult,
        ElementType,
        VisionActionMapper,
        VisualAttributes,
    )

    return VisionActionMapper, VisualAttributes, ActionResult, ElementType


def _import_async_vision_monitor():
    from .async_vision_monitor import AsyncVisionMonitor, MonitorEvent, MonitorEventType

    return AsyncVisionMonitor, MonitorEvent, MonitorEventType


def _import_post_action_validator():
    from .post_action_validator import ValidationResult, VisionPostActionValidator

    return VisionPostActionValidator, ValidationResult


def _import_visual_grounding_engine():
    from .visual_grounding_engine import GroundedElement, VisualGroundingEngine

    return VisualGroundingEngine, GroundedElement


def _import_omniparser():
    from .omniparser_adapter import OmniParser, OmniParserVisionEngine

    return OmniParser, OmniParserVisionEngine


def _import_coords():
    from .coords import Point, normalize_coords

    return normalize_coords, Point


# Make classes available via lazy loading
__all__ = [
    "ScreenshotEngine",
    "OCREngine",
    "ElementLocator",
    "VisionCognitiveEngine",
    "OmniParserVisionEngine",  # TICKET-CLEANUP-VISION: Unified vision engine (YOLOv8 + Florence-2)
    "VisualErrorDetector",
    "VisionConfigWizard",
    "VisionConfig",
    "VisionActionMapper",
    "VisualAttributes",
    "ActionResult",
    "ElementType",
    "AsyncVisionMonitor",
    "MonitorEvent",
    "MonitorEventType",
    "VisionPostActionValidator",
    "ValidationResult",
    "VisualGroundingEngine",  # TICKET-ARCH-002: Set-of-Marks visual grounding
    "GroundedElement",
    "OmniParser",  # TICKET-SWITCH-NATIVE: OmniParser for UI detection
    "normalize_coords",  # TICKET-SWITCH-NATIVE: Coordinate conversion
    "Point",  # TICKET-SWITCH-NATIVE: Point dataclass
]


def __getattr__(name):
    """Lazy import for vision modules"""
    if name == "ScreenshotEngine":
        return _import_screenshot_engine()
    elif name == "OCREngine":
        return _import_ocr_engine()
    elif name == "ElementLocator":
        return _import_element_locator()
    elif name == "VisionCognitiveEngine":
        return _import_vision_cognitive_engine()
    elif name == "VisualErrorDetector":
        return _import_visual_error_detector()
    elif name == "VisionConfigWizard":
        classes = _import_vision_config_wizard()
        return classes[0]
    elif name == "VisionConfig":
        classes = _import_vision_config_wizard()
        return classes[1]
    elif name == "VisionActionMapper":
        classes = _import_vision_action_mapper()
        return classes[0]
    elif name == "VisualAttributes":
        classes = _import_vision_action_mapper()
        return classes[1]
    elif name == "ActionResult":
        classes = _import_vision_action_mapper()
        return classes[2]
    elif name == "ElementType":
        classes = _import_vision_action_mapper()
        return classes[3]
    elif name == "AsyncVisionMonitor":
        classes = _import_async_vision_monitor()
        return classes[0]
    elif name == "MonitorEvent":
        classes = _import_async_vision_monitor()
        return classes[1]
    elif name == "MonitorEventType":
        classes = _import_async_vision_monitor()
        return classes[2]
    elif name == "VisionPostActionValidator":
        classes = _import_post_action_validator()
        return classes[0]
    elif name == "ValidationResult":
        classes = _import_post_action_validator()
        return classes[1]
    elif name == "VisualGroundingEngine":
        classes = _import_visual_grounding_engine()
        return classes[0]
    elif name == "GroundedElement":
        classes = _import_visual_grounding_engine()
        return classes[1]
    elif name == "OmniParser":
        classes = _import_omniparser()
        return classes[0]
    elif name == "OmniParserVisionEngine":
        classes = _import_omniparser()
        return classes[1]
    elif name == "normalize_coords":
        classes = _import_coords()
        return classes[0]
    elif name == "Point":
        classes = _import_coords()
        return classes[1]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
