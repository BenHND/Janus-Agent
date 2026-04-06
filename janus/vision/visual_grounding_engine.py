"""
VisualGroundingEngine - Set-of-Marks Implementation
Part of TICKET-ARCH-002: Visual Grounding for LLM

Features:
- Detect interactive UI elements (buttons, links, text fields)
- Assign unique numeric IDs to each element
- Generate structured list with IDs and coordinates
- Enable LLM to click without hallucinating CSS selectors

This implements a simplified "Set-of-Marks" approach where each detected
element gets a temporary ID that the LLM can reference for interactions.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image
else:
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore

from .omniparser_adapter import OmniParserVisionEngine
from .native_ocr_adapter import NativeOCRAdapter as OCREngine

logger = logging.getLogger(__name__)

# Constants for element classification
MAX_LINK_TEXT_LENGTH = 30  # Short text with action indicators
OCR_CONFIDENCE_SCALE = 100  # OCR uses 0-100, we normalize to 0-1


class GroundedElement:
    """
    Represents a UI element with Set-of-Marks ID and coordinates
    """

    def __init__(
        self,
        element_id: int,
        element_type: str,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
    ):
        """
        Initialize grounded element

        Args:
            element_id: Unique numeric ID (1, 2, 3...)
            element_type: Type of element (button, link, textfield, label, etc.)
            text: Text content of the element
            x: X coordinate (top-left)
            y: Y coordinate (top-left)
            width: Width of element
            height: Height of element
            confidence: Detection confidence (0-1)
        """
        self.id = element_id
        self.type = element_type
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.confidence = confidence

        # Calculate center point for clicking
        self.center_x = x + width // 2
        self.center_y = y + height // 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "confidence": self.confidence,
        }

    def to_llm_format(self) -> str:
        """
        Convert to LLM-friendly text format
        Returns: "[ID 1] Button 'Search' (x=100, y=200)"
        """
        return f"[ID {self.id}] {self.type.title()} '{self.text}' (x={self.center_x}, y={self.center_y})"


class VisualGroundingEngine:
    """
    Visual Grounding Engine implementing Set-of-Marks for UI element detection

    TICKET-ARCH-002: Enables LLM to reference screen elements by ID without
    hallucinating CSS selectors.

    Features:
    - Detect interactive elements (buttons, links, fields)
    - Assign temporary numeric IDs
    - Generate structured lists for LLM consumption
    - Support both OCR and object detection methods
    """

    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
        omniparser_engine: Optional[OmniParserVisionEngine] = None,
        use_omniparser: Optional[bool] = None,  # None = auto-detect
        min_confidence: float = 0.5,
    ):
        """
        Initialize Visual Grounding Engine
        
        TICKET-CLEANUP-VISION: Simplified to use OmniParser only

        Args:
            ocr_engine: OCR engine instance for text detection
            omniparser_engine: OmniParser engine for specialized UI detection
            use_omniparser: Whether to use OmniParser (None = auto-detect, True = force, False = disable)
            min_confidence: Minimum confidence threshold for element detection
        """
        self.logger = logger
        self.ocr_engine = ocr_engine or OCREngine(backend="auto")
        self.omniparser_engine = omniparser_engine
        self.min_confidence = min_confidence

        # TICKET-CLEANUP-VISION: Auto-enable OmniParser when available (unless explicitly disabled)
        # If use_omniparser is None (default), try to auto-detect and enable
        # If use_omniparser is True, force enable (warn if not available)
        # If use_omniparser is False, disable
        should_try_omniparser = use_omniparser is not False
        
        if should_try_omniparser and self.omniparser_engine is None:
            try:
                from .omniparser_adapter import OmniParserVisionEngine
                # Use lazy_load=True for auto-detection to avoid long startup times
                self.omniparser_engine = OmniParserVisionEngine(lazy_load=True)
                self.use_omniparser = self.omniparser_engine.is_available()
                if self.use_omniparser:
                    self.logger.info("✓ OmniParser auto-detected and enabled for UI element detection")
                elif use_omniparser is True:
                    # Explicitly requested but not available
                    self.logger.warning("⚠️ OmniParser requested but models not available")
                    self.use_omniparser = False
            except Exception as e:
                self.logger.debug(f"OmniParser not available: {e}")
                self.use_omniparser = False
        elif self.omniparser_engine is not None:
            # Engine was provided externally
            self.use_omniparser = use_omniparser is not False and self.omniparser_engine.is_available()
        else:
            # Explicitly disabled (use_omniparser is False)
            self.use_omniparser = False

    def detect_interactive_elements(
        self, image: Any, region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[GroundedElement]:
        """
        Detect all interactive UI elements and assign IDs

        This is the main Set-of-Marks function that:
        1. Detects interactive elements (buttons, links, fields)
        2. Assigns unique numeric IDs
        3. Returns structured list with coordinates

        Args:
            image: PIL Image to analyze
            region: Optional region to analyze (x, y, width, height)

        Returns:
            List of GroundedElement objects with IDs and coordinates
        """
        start_time = time.time()

        # Priority order: OmniParser > OCR (TICKET-CLEANUP-VISION: Florence removed)
        if self.use_omniparser and self.omniparser_engine:
            elements = self._detect_with_omniparser(image, region)
            method = "omniparser"
        else:
            elements = self._detect_with_ocr(image, region)
            method = "ocr"

        # Assign unique IDs
        for idx, element in enumerate(elements, start=1):
            element.id = idx

        duration = time.time() - start_time
        self.logger.info(
            f"✓ Detected {len(elements)} interactive elements in {duration:.2f}s "
            f"(method: {method})"
        )

        return elements

    def _detect_with_omniparser(
        self, image: Any, region: Optional[Tuple[int, int, int, int]]
    ) -> List[GroundedElement]:
        """
        Detect elements using OmniParser (YOLOv8 + Florence-2)

        Args:
            image: PIL Image to analyze
            region: Optional region to crop to

        Returns:
            List of GroundedElement objects (without IDs assigned yet)
        """
        if not self.omniparser_engine:
            return []

        # Crop to region if specified
        if region:
            x, y, w, h = region
            image = image.crop((x, y, x + w, y + h))
            offset_x, offset_y = x, y
        else:
            offset_x, offset_y = 0, 0

        elements = []

        # Use OmniParser object detection to find UI elements
        detection_result = self.omniparser_engine.detect_objects(image)
        objects = detection_result.get("objects", [])

        # Also get OCR results for text matching
        ocr_result = self.omniparser_engine.extract_text(image, with_regions=True)
        text_regions = ocr_result.get("regions", [])

        # Process detected objects
        for obj in objects:
            label = obj.get("label", "element")
            bbox = obj.get("bbox", (0, 0, 0, 0))  # (x1, y1, x2, y2)
            confidence = obj.get("confidence", 0.0)

            # Convert bbox format
            x1, y1, x2, y2 = bbox
            x = int(x1)
            y = int(y1)
            width = int(x2 - x1)
            height = int(y2 - y1)

            # Try to find matching text in this region
            text = self._find_text_in_region(text_regions, bbox)

            # Classify element type based on label and context
            element_type = self._classify_element_type(label, text)

            # Only include interactive elements
            if self._is_interactive(element_type):
                elements.append(
                    GroundedElement(
                        element_id=0,  # Will be assigned later
                        element_type=element_type,
                        text=text or label,
                        x=x + offset_x,
                        y=y + offset_y,
                        width=width,
                        height=height,
                        confidence=confidence,
                    )
                )

        # If no objects detected, fall back to text regions as potential interactive elements
        if not elements and text_regions:
            for text_region in text_regions:
                text = text_region.get("text", "")
                bbox = text_region.get("bbox", [0, 0, 0, 0])  # [x1, y1, x2, y2]

                x1, y1, x2, y2 = bbox
                x = int(x1)
                y = int(y1)
                width = int(x2 - x1)
                height = int(y2 - y1)

                # Classify based on text content
                element_type = self._classify_from_text(text)

                if self._is_interactive(element_type):
                    elements.append(
                        GroundedElement(
                            element_id=0,
                            element_type=element_type,
                            text=text,
                            x=x + offset_x,
                            y=y + offset_y,
                            width=width,
                            height=height,
                            confidence=0.7,
                        )
                    )

        return elements

    def _detect_with_ocr(
        self, image: Any, region: Optional[Tuple[int, int, int, int]]
    ) -> List[GroundedElement]:
        """
        Detect elements using OCR fallback

        Args:
            image: PIL Image to analyze
            region: Optional region to analyze

        Returns:
            List of GroundedElement objects (without IDs assigned yet)
        """
        # Crop to region if specified
        if region:
            x, y, w, h = region
            image = image.crop((x, y, x + w, y + h))
            offset_x, offset_y = x, y
        else:
            offset_x, offset_y = 0, 0

        elements = []

        # Get all text with bounding boxes
        ocr_results = self.ocr_engine.get_all_text_with_boxes(image)

        for result in ocr_results:
            # OCR uses 0-100 scale, min_confidence is 0-1, so scale for comparison
            if result.confidence < self.min_confidence * OCR_CONFIDENCE_SCALE:
                continue

            text = result.text
            if not result.bbox:
                continue

            x, y, w, h = result.bbox

            # Classify element type based on text content
            element_type = self._classify_from_text(text)

            # Only include interactive elements
            if self._is_interactive(element_type):
                elements.append(
                    GroundedElement(
                        element_id=0,  # Will be assigned later
                        element_type=element_type,
                        text=text,
                        x=x + offset_x,
                        y=y + offset_y,
                        width=w,
                        height=h,
                        confidence=result.confidence / OCR_CONFIDENCE_SCALE,  # Normalize to 0-1
                    )
                )

        return elements

    def _find_text_in_region(
        self, text_regions: List[Dict[str, Any]], bbox: Tuple[int, int, int, int]
    ) -> str:
        """
        Find text that overlaps with the given bounding box

        Args:
            text_regions: List of text regions from OCR
            bbox: Bounding box to search in (x1, y1, x2, y2)

        Returns:
            Matching text or empty string
        """
        x1, y1, x2, y2 = bbox

        for region in text_regions:
            text = region.get("text", "")
            text_bbox = region.get("bbox", [0, 0, 0, 0])
            tx1, ty1, tx2, ty2 = text_bbox

            # Check if text region overlaps with bbox
            if (
                tx1 < x2
                and tx2 > x1
                and ty1 < y2
                and ty2 > y1
            ):
                return text

        return ""

    def _classify_element_type(self, label: str, text: str) -> str:
        """
        Classify element type based on object detection label and text

        Args:
            label: Object detection label
            text: Text content

        Returns:
            Element type (button, link, textfield, etc.)
        """
        label_lower = label.lower()
        text_lower = text.lower() if text else ""

        # Button indicators
        if "button" in label_lower or any(
            word in text_lower for word in ["click", "submit", "send", "ok", "cancel", "search"]
        ):
            return "button"

        # Link indicators
        if "link" in label_lower or "anchor" in label_lower:
            return "link"

        # Input field indicators
        if (
            "input" in label_lower
            or "text" in label_lower
            or "field" in label_lower
            or any(word in text_lower for word in ["email", "password", "username", "search"])
        ):
            return "textfield"

        # Checkbox/radio indicators
        if "checkbox" in label_lower or "radio" in label_lower:
            return "checkbox"

        # Default to label as element type
        return "label"

    def _classify_from_text(self, text: str) -> str:
        """
        Classify element type based only on text content

        Args:
            text: Text content

        Returns:
            Element type
        """
        text_lower = text.lower()

        # TICKET-ARCH-FINAL: Load button action keywords from locale configuration
        from janus.resources.locale_loader import get_locale_loader
        from janus.utils.config_loader import get_config_loader
        
        config_loader = get_config_loader()
        language = config_loader.get("language", "default", "en")  # Default to English
        locale_loader = get_locale_loader()
        
        button_keywords = locale_loader.get_keywords("button_actions", language=language)
        
        # Fallback if locale not available
        if not button_keywords:
            button_keywords = ["click", "submit", "send", "ok", "cancel", "search", "continue", "next"]
        
        if any(keyword in text_lower for keyword in button_keywords):
            return "button"

        # Link indicators (usually short text with action)
        if len(text) < MAX_LINK_TEXT_LENGTH and any(char in text for char in ["→", "»", "›"]):
            return "link"

        # Input field indicators - load from locale
        input_keywords = locale_loader.get_keywords("input_field_indicators", language=language)
        
        # Fallback if locale not available
        if not input_keywords:
            input_keywords = ["email", "password", "username", "name:", "search", "enter"]
        
        if any(keyword in text_lower for keyword in input_keywords):
            return "textfield"

        # Default to label for any other text
        return "label"

    def _is_interactive(self, element_type: str) -> bool:
        """
        Check if element type is interactive

        Args:
            element_type: Element type

        Returns:
            True if interactive, False otherwise
        """
        interactive_types = {"button", "link", "textfield", "checkbox", "radio"}
        return element_type in interactive_types

    def generate_llm_list(self, elements: List[GroundedElement]) -> str:
        """
        Generate text list for LLM consumption

        Format:
        [ID 1] Button "Search" (x=100, y=200)
        [ID 2] Textfield "Email" (x=150, y=250)
        [ID 3] Link "Sign In" (x=200, y=300)

        Args:
            elements: List of grounded elements

        Returns:
            Formatted text list
        """
        if not elements:
            return "No interactive elements detected on screen."

        lines = []
        for element in elements:
            lines.append(element.to_llm_format())

        return "\n".join(lines)

    def get_element_by_id(
        self, elements: List[GroundedElement], element_id: int
    ) -> Optional[GroundedElement]:
        """
        Get element by its Set-of-Marks ID

        Args:
            elements: List of grounded elements
            element_id: Element ID to find

        Returns:
            GroundedElement if found, None otherwise
        """
        for element in elements:
            if element.id == element_id:
                return element
        return None

    def is_available(self) -> bool:
        """Check if visual grounding is available"""
        return self.use_omniparser or self.ocr_engine is not None

    def get_info(self) -> Dict[str, Any]:
        """Get engine information"""
        return {
            "engine": "visual_grounding",
            "method": "omniparser" if self.use_omniparser else "ocr",
            "omniparser_available": self.omniparser_engine is not None,
            "ocr_backend": self.ocr_engine.backend if self.ocr_engine else None,
            "min_confidence": self.min_confidence,
        }
