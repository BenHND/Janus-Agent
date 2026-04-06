"""
Vision Runner - Visual fallback system using OCR and template matching
Integrates with existing vision modules for element detection and interaction
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VisionRunner:
    """
    Vision-based automation fallback system

    Features:
    - Screenshot capture (window or region)
    - OCR text detection
    - Template matching
    - Visual element interaction (click, type)
    - Window focus enforcement
    """

    def __init__(
        self,
        screenshot_engine=None,
        ocr_engine=None,
        element_locator=None,
    ):
        """
        Initialize Vision Runner

        Args:
            screenshot_engine: ScreenshotEngine instance
            ocr_engine: OCREngine instance
            element_locator: ElementLocator instance
        """
        # Import existing vision modules
        try:
            from janus.vision.element_locator import ElementLocator
            from janus.vision.native_ocr_adapter import NativeOCRAdapter
            from janus.vision.screenshot_engine import ScreenshotEngine

            self.screenshot_engine = screenshot_engine or ScreenshotEngine()
            self.ocr_engine = ocr_engine or NativeOCRAdapter(backend="auto")
            self.element_locator = element_locator or ElementLocator(
                screenshot_engine=self.screenshot_engine,
                ocr_engine=self.ocr_engine,
            )

            self.available = True
            logger.info("VisionRunner initialized with vision modules")

        except ImportError as e:
            logger.warning(f"Vision modules not available: {e}")
            self.screenshot_engine = None
            self.ocr_engine = None
            self.element_locator = None
            self.available = False

    def is_available(self) -> bool:
        """Check if vision system is available"""
        return self.available

    def screenshot(
        self, window: Optional[str] = None, region: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Capture screenshot

        Args:
            window: Optional window name
            region: Optional region tuple (x, y, width, height)

        Returns:
            PIL Image or None
        """
        if not self.available:
            logger.error("Vision system not available")
            return None

        try:
            if region:
                return self.screenshot_engine.capture_region(*region)
            else:
                return self.screenshot_engine.capture_screen()
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None

    def ocr(self, image=None) -> Dict[str, Any]:
        """
        Perform OCR text detection

        Args:
            image: PIL Image (None uses current screen)

        Returns:
            Dictionary with detected text and bounding boxes
        """
        if not self.available:
            logger.error("Vision system not available")
            return {"texts": [], "boxes": []}

        try:
            if image is None:
                image = self.screenshot_engine.capture_screen()

            result = self.ocr_engine.extract_text(image)
            return {
                "texts": result.get("texts", []),
                "boxes": result.get("boxes", []),
                "confidence": result.get("confidence", []),
            }
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return {"texts": [], "boxes": []}

    def find_text(self, text: str, confidence: float = 0.7) -> Optional[Tuple[int, int, int, int]]:
        """
        Find text on screen and return bounding box

        Args:
            text: Text to find
            confidence: Minimum confidence threshold

        Returns:
            Bounding box tuple (x, y, width, height) or None
        """
        if not self.available:
            logger.error("Vision system not available")
            return None

        try:
            logger.info(f"Looking for text: '{text}' (confidence={confidence})")

            result = self.element_locator.find_element_by_text(
                text,
                confidence_threshold=confidence,
            )

            if result["found"]:
                bbox = result.get("bbox")
                logger.info(f"Found text at: {bbox}")
                return bbox
            else:
                logger.warning(f"Text not found: '{text}'")
                return None

        except Exception as e:
            logger.error(f"Error finding text: {e}")
            return None

    def template_match(
        self, template_path: str, threshold: float = 0.8
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find template image on screen

        Args:
            template_path: Path to template image
            threshold: Matching threshold

        Returns:
            Bounding box tuple (x, y, width, height) or None
        """
        if not self.available:
            logger.error("Vision system not available")
            return None

        try:
            logger.info(f"Looking for template: {template_path}")

            # Use element locator for template matching
            result = self.element_locator.find_element_by_image(
                template_path,
                confidence_threshold=threshold,
            )

            if result["found"]:
                bbox = result.get("bbox")
                logger.info(f"Found template at: {bbox}")
                return bbox
            else:
                logger.warning(f"Template not found: {template_path}")
                return None

        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return None

    def click_at_bbox(self, bbox: Tuple[int, int, int, int]) -> bool:
        """
        Click at center of bounding box

        Args:
            bbox: Bounding box tuple (x, y, width, height)

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y, width, height = bbox
            center_x = x + width // 2
            center_y = y + height // 2

            logger.info(f"Clicking at ({center_x}, {center_y})")

            # Use pyautogui for clicking
            try:
                import pyautogui

                pyautogui.click(center_x, center_y)
                return True
            except ImportError:
                logger.error("pyautogui not available")
                return False

        except Exception as e:
            logger.error(f"Error clicking at bbox: {e}")
            return False

    def type_at_bbox(self, bbox: Tuple[int, int, int, int], text: str) -> bool:
        """
        Click at bbox and type text

        Args:
            bbox: Bounding box tuple (x, y, width, height)
            text: Text to type

        Returns:
            True if successful, False otherwise
        """
        try:
            # First click at the location
            if not self.click_at_bbox(bbox):
                return False

            # Then type the text
            import time

            time.sleep(0.2)  # Small delay after click

            try:
                import pyautogui

                pyautogui.write(text, interval=0.05)
                return True
            except ImportError:
                logger.error("pyautogui not available")
                return False

        except Exception as e:
            logger.error(f"Error typing at bbox: {e}")
            return False

    def verify_action_result(self, action_result) -> bool:
        """
        Verify action execution result (stub implementation)
        
        Note: This is a stub implementation that skips actual vision verification
        to avoid performance delays (previously 20+ seconds). A full implementation
        would capture screenshots before/after and verify the action succeeded using
        OCR or AI vision models.
        
        Args:
            action_result: ActionResult to verify
            
        Returns:
            True if verification passed (or skipped), False otherwise
        """
        if not action_result or not hasattr(action_result, 'action_type'):
            logger.warning("Invalid action_result provided to verify_action_result")
            return False
            
        logger.debug(f"Vision verification skipped for action: {action_result.action_type}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get vision runner statistics"""
        return {
            "available": self.available,
            "has_screenshot": self.screenshot_engine is not None,
            "has_ocr": self.ocr_engine is not None,
            "has_locator": self.element_locator is not None,
        }
