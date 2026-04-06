"""
Element locator for identifying UI elements and their coordinates
Ticket 3.3: Localisation éléments
Ticket 9.3: Error Handling & Fallback
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pyautogui
from PIL import Image

from janus.constants import ActionStatus
from janus.logging import get_logger

from ..utils.retry import FallbackChain, RetryConfig, retry_with_fallback
from .native_ocr_adapter import NativeOCRAdapter as OCREngine
from .native_ocr_adapter import OCRResult
from .screenshot_engine import ScreenshotEngine


class ElementMatch:
    """
    Represents a matched UI element
    """

    def __init__(self, text: str, x: int, y: int, width: int, height: int, confidence: float):
        """
        Initialize element match

        Args:
            text: Matched text
            x: X coordinate (top-left)
            y: Y coordinate (top-left)
            width: Width of element
            height: Height of element
            confidence: Match confidence (0-100)
        """
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
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "confidence": self.confidence,
        }


class ElementLocator:
    """
    Locates UI elements on screen using OCR for clicking or copying
    Ticket 3.3: Identifies coordinates for interaction via pyautogui
    Enhanced with retry and fallback mechanisms (Phase 9.3)
    """

    def __init__(
        self,
        screenshot_engine: Optional[ScreenshotEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        min_confidence: float = 50.0,
        enable_fallback: bool = True,
    ):
        """
        Initialize element locator

        Args:
            screenshot_engine: Screenshot engine instance
            ocr_engine: OCR engine instance
            min_confidence: Minimum confidence threshold for matches
            enable_fallback: Enable OCR backend fallback (Phase 9.3)
        """
        self.logger = get_logger("element_locator")
        self.screenshot_engine = screenshot_engine or ScreenshotEngine()
        self.ocr_engine = ocr_engine or OCREngine(backend="auto")
        self.min_confidence = min_confidence
        self.enable_fallback = enable_fallback

        # Fallback OCR engine (EasyOCR) for Phase 9.3
        self._fallback_ocr = None
        if enable_fallback:
            try:
                self._fallback_ocr = OCREngine(backend="easyocr")
            except Exception as e:
                logging.warning(f"Could not initialize fallback OCR: {e}")
                self._fallback_ocr = None

    def find_element_by_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
    ) -> Optional[ElementMatch]:
        """
        Find a UI element by its text content

        Args:
            text: Text to search for
            region: Optional region to search (x, y, width, height)
            case_sensitive: Whether search should be case sensitive

        Returns:
            ElementMatch if found, None otherwise
        """
        matches = self.find_all_elements_by_text(text, region, case_sensitive)

        if matches:
            # Return the match with highest confidence
            return max(matches, key=lambda m: m.confidence)

        return None

    def find_all_elements_by_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
    ) -> List[ElementMatch]:
        """
        Find all UI elements matching the text with automatic fallback (Phase 9.3)

        Args:
            text: Text to search for
            region: Optional region to search (x, y, width, height)
            case_sensitive: Whether search should be case sensitive

        Returns:
            List of ElementMatch objects
        """

        # Build fallback chain for OCR
        def find_with_primary_ocr():
            return self._find_elements_with_ocr(text, region, case_sensitive, self.ocr_engine)

        def find_with_fallback_ocr():
            if self._fallback_ocr is None:
                raise Exception("Fallback OCR not available")
            return self._find_elements_with_ocr(text, region, case_sensitive, self._fallback_ocr)

        # Try primary OCR first, then fallback if enabled
        if self.enable_fallback and self._fallback_ocr:
            chain = FallbackChain(log_attempts=True)
            chain.add(
                "Primary OCR (Tesseract)",
                find_with_primary_ocr,
                retry_config=RetryConfig(max_attempts=2, initial_delay=0.5),
            )
            chain.add(
                "Fallback OCR (EasyOCR)",
                find_with_fallback_ocr,
                retry_config=RetryConfig(max_attempts=1, initial_delay=0.5),
            )

            try:
                return chain.execute()
            except Exception as e:
                logging.error(f"All OCR methods failed: {e}")
                return []
        else:
            # No fallback, use primary with retry
            retry_config = RetryConfig(max_attempts=2, initial_delay=0.5)
            decorated_func = retry_with_fallback(config=retry_config, log_failures=True)(
                find_with_primary_ocr
            )

            try:
                return decorated_func()
            except Exception as e:
                logging.error(f"OCR failed: {e}")
                return []

    def _find_elements_with_ocr(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]],
        case_sensitive: bool,
        ocr_engine: OCREngine,
    ) -> List[ElementMatch]:
        """
        Internal method to find elements using a specific OCR engine

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Whether search should be case sensitive
            ocr_engine: OCR engine to use

        Returns:
            List of ElementMatch objects
        """
        # Capture screenshot
        if region:
            screenshot = self.screenshot_engine.capture_region(*region)
            offset_x, offset_y = region[0], region[1]
        else:
            screenshot = self.screenshot_engine.capture_screen()
            offset_x, offset_y = 0, 0

        # Find text using OCR
        ocr_results = ocr_engine.find_text(screenshot, text, case_sensitive)

        # Convert OCR results to ElementMatch objects
        matches = []
        for result in ocr_results:
            if result.confidence >= self.min_confidence and result.bbox:
                x, y, w, h = result.bbox
                # Adjust coordinates if we searched in a region
                matches.append(
                    ElementMatch(
                        text=result.text,
                        x=x + offset_x,
                        y=y + offset_y,
                        width=w,
                        height=h,
                        confidence=result.confidence,
                    )
                )

        if not matches:
            raise Exception(f"No elements found matching '{text}'")

        return matches

    def click_element(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
        button: str = "left",
    ) -> Dict[str, Any]:
        """
        Find and click on an element by its text

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Whether search should be case sensitive
            button: Mouse button to click ("left", "right", "middle")

        Returns:
            Result dictionary with status and details
        """
        try:
            element = self.find_element_by_text(text, region, case_sensitive)

            if not element:
                return {
                    "status": ActionStatus.FAILED.value,
                    "action": "click_element",
                    "error": f"Element with text '{text}' not found",
                }

            # Click at the center of the element
            pyautogui.click(element.center_x, element.center_y, button=button)

            return {
                "status": ActionStatus.SUCCESS.value,
                "action": "click_element",
                "element": element.to_dict(),
                "message": f"Clicked on '{element.text}' at ({element.center_x}, {element.center_y})",
            }

        except Exception as e:
            return {"status": ActionStatus.FAILED.value, "action": "click_element", "error": str(e)}

    def hover_element(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """
        Find and hover over an element by its text

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Whether search should be case sensitive

        Returns:
            Result dictionary with status and details
        """
        try:
            element = self.find_element_by_text(text, region, case_sensitive)

            if not element:
                return {
                    "status": ActionStatus.FAILED.value,
                    "action": "hover_element",
                    "error": f"Element with text '{text}' not found",
                }

            # Move mouse to center of element
            pyautogui.moveTo(element.center_x, element.center_y)

            return {
                "status": ActionStatus.SUCCESS.value,
                "action": "hover_element",
                "element": element.to_dict(),
                "message": f"Hovered over '{element.text}' at ({element.center_x}, {element.center_y})",
            }

        except Exception as e:
            return {"status": ActionStatus.FAILED.value, "action": "hover_element", "error": str(e)}

    def get_element_coordinates(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
    ) -> Optional[Dict[str, int]]:
        """
        Get the coordinates of an element without interacting with it

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Whether search should be case sensitive

        Returns:
            Dictionary with coordinates or None if not found
        """
        element = self.find_element_by_text(text, region, case_sensitive)

        if element:
            return {
                "x": element.x,
                "y": element.y,
                "center_x": element.center_x,
                "center_y": element.center_y,
                "width": element.width,
                "height": element.height,
                "confidence": element.confidence,
            }

        return None

    def get_all_elements(
        self, region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[ElementMatch]:
        """
        Get all detected text elements on screen

        Args:
            region: Optional region to search

        Returns:
            List of all detected ElementMatch objects
        """
        try:
            # Capture screenshot
            if region:
                screenshot = self.screenshot_engine.capture_region(*region)
                offset_x, offset_y = region[0], region[1]
            else:
                screenshot = self.screenshot_engine.capture_screen()
                offset_x, offset_y = 0, 0

            # Get all text with OCR
            ocr_results = self.ocr_engine.get_all_text_with_boxes(screenshot)

            # Convert to ElementMatch objects
            matches = []
            for result in ocr_results:
                if result.confidence >= self.min_confidence and result.bbox:
                    x, y, w, h = result.bbox
                    matches.append(
                        ElementMatch(
                            text=result.text,
                            x=x + offset_x,
                            y=y + offset_y,
                            width=w,
                            height=h,
                            confidence=result.confidence,
                        )
                    )

            return matches

        except Exception as e:
            self.logger.error(f"Error getting all elements: {str(e)}", exc_info=True)
            return []

    def copy_element_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """
        Find an element and copy its text to clipboard

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Whether search should be case sensitive

        Returns:
            Result dictionary with status and copied text
        """
        try:
            element = self.find_element_by_text(text, region, case_sensitive)

            if not element:
                return {
                    "status": ActionStatus.FAILED.value,
                    "action": "copy_element_text",
                    "error": f"Element with text '{text}' not found",
                }

            # Copy text to clipboard
            import pyperclip

            pyperclip.copy(element.text)

            return {
                "status": ActionStatus.SUCCESS.value,
                "action": "copy_element_text",
                "element": element.to_dict(),
                "copied_text": element.text,
                "message": f"Copied text: '{element.text}'",
            }

        except Exception as e:
            return {
                "status": ActionStatus.FAILED.value,
                "action": "copy_element_text",
                "error": str(e),
            }
