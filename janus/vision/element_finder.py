"""
Element Finder - Responsible for locating UI elements on screen

This module handles all element finding logic including:
- Text-based element search
- Fuzzy matching
- Attribute-based search
- Automatic scrolling to find elements

Extracted from VisionActionMapper as part of TICKET-REVIEW-001
"""

import time
from typing import Optional, Tuple

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

    class MockPyAutoGUI:
        @staticmethod
        def scroll(*args, **kwargs):
            pass

    pyautogui = MockPyAutoGUI()

from typing import Any, List

from janus.logging import get_logger

from .element_locator import ElementLocator, ElementMatch
from .native_ocr_adapter import NativeOCRAdapter as OCREngine
from .screenshot_engine import ScreenshotEngine
from .vision_types import VisualAttributes


class ElementFinder:
    """
    Finds UI elements using various strategies (text, attributes, fuzzy matching)
    """

    def __init__(
        self,
        screenshot_engine: Optional[ScreenshotEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        element_locator: Optional[ElementLocator] = None,
        enable_auto_scroll: bool = True,
        som_engine: Any = None,  # TICKET-FIX: Inject SetOfMarksEngine
    ):
        """
        Initialize Element Finder

        Args:
            screenshot_engine: Screenshot engine for capturing screen
            ocr_engine: OCR engine for text recognition
            element_locator: Element locator for finding elements
            enable_auto_scroll: Enable automatic scrolling to find elements
            som_engine: Optional SetOfMarksEngine for ID resolution
        """
        self.logger = get_logger("element_finder")
        self.screenshot_engine = screenshot_engine or ScreenshotEngine()
        self.ocr_engine = ocr_engine or OCREngine(backend="auto")
        self.element_locator = element_locator or ElementLocator(
            screenshot_engine=self.screenshot_engine, ocr_engine=self.ocr_engine
        )
        self.enable_auto_scroll = enable_auto_scroll
        self.som_engine = som_engine  # Store SOM engine
        self._scrolls_performed = 0

    def find_element_by_id(
        self,
        element_id: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        scroll_if_not_found: bool = False,
    ) -> Optional[ElementMatch]:
        """
        Find UI element by Set-of-Marks ID

        Args:
            element_id: Element ID from Set-of-Marks (e.g., "text_22", "button_5")
            region: Optional region to search (not used for ID lookup, kept for API consistency)
            scroll_if_not_found: If True, attempt scrolling to refresh SOM cache (not currently implemented)

        Returns:
            ElementMatch if found, None otherwise
        """
        self.logger.debug(f"Finding element by ID: '{element_id}'")

        if not self.som_engine or not self.som_engine.is_available():
            self.logger.warning(f"SOM engine not available, cannot find element by ID: {element_id}")
            return None

        try:
            som_element = self.som_engine.get_element_by_id(element_id)
            if som_element:
                self.logger.info(f"Found element by ID in SOM cache: {element_id}")
                # Convert InteractiveElement to ElementMatch
                # InteractiveElement has bbox as (x, y, width, height)
                x, y, width, height = som_element.bbox
                return ElementMatch(
                    text=som_element.text or element_id,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    confidence=som_element.confidence,
                )
            else:
                self.logger.warning(f"Element ID not found in SOM cache: {element_id}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to lookup element ID in SOM: {e}")
            return None

    def find_element_by_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        case_sensitive: bool = False,
        fuzzy_match: bool = True,
        scroll_if_not_found: bool = True,
        role: Optional[str] = None,
    ) -> Optional[ElementMatch]:
        """
        Find UI element by text content with STRICT DETECTION HIERARCHY.
        
        PERF-M4-002: Implements detection hierarchy to avoid expensive VLM calls:
        1. Accessibility OS (0-5ms) - ALWAYS FIRST
        2. OCR Cache (0ms if hit)
        3. Native OCR - Apple Vision on macOS (50-100ms)
        4. VLM (OmniParser/Florence) - LAST RESORT ONLY (500-1000ms)

        Args:
            text: Text to search for
            region: Optional region to search (x, y, width, height)
            case_sensitive: Whether search should be case sensitive
            fuzzy_match: Enable fuzzy matching for partial text matches
            scroll_if_not_found: Automatically scroll and retry if not found
            role: Optional role hint for accessibility search (e.g., "button", "link")

        Returns:
            ElementMatch if found, None otherwise
        """
        self.logger.debug(f"Finding element by text with hierarchy: '{text}'")

        # 1. ACCESSIBILITY OS (0-5ms) - ALWAYS TRY FIRST
        element = self._find_via_accessibility(text, role)
        if element:
            self.logger.info(f"✓ Found via accessibility in <5ms: {text}")
            return element

        # 2. OCR CACHE (0ms if hit)
        if hasattr(self.ocr_engine, 'cache') and self.ocr_engine.cache:
            self.logger.debug("Checking OCR cache...")
            # OCR cache checking is implicit in element_locator
            # The element_locator will use cached results if available
        
        # 3. NATIVE OCR - Apple Vision on macOS (50-100ms)
        import platform
        if platform.system() == "Darwin":
            element = self._find_via_apple_vision(text, region)
            if element:
                self.logger.info(f"✓ Found via Apple Vision OCR in ~80ms: {text}")
                return element

        # 4. VLM (OmniParser/Florence) - LAST RESORT (500-1000ms)
        # This is handled by element_locator which may use VLM internally
        # Only call if we haven't found anything yet
        self.logger.info(f"Falling back to VLM/OCR for: {text}")
        
        # Try direct match via element_locator (may use Tesseract OCR or VLM)
        element = self.element_locator.find_element_by_text(text, region, case_sensitive)

        if element:
            self.logger.debug(f"Found element via OCR/VLM: {element.text}")
            return element

        # Try fuzzy matching if enabled
        if fuzzy_match and not element:
            self.logger.debug("Direct match failed, trying fuzzy match")
            element = self._fuzzy_find_element(text, region, case_sensitive)

            if element:
                self.logger.debug(f"Found element with fuzzy match: {element.text}")
                return element

        # Try scrolling and retrying if enabled
        if scroll_if_not_found and self.enable_auto_scroll and not element:
            self.logger.debug("Element not found, trying with scroll")
            element = self._find_with_scroll(text, region, case_sensitive)

            if element:
                self.logger.debug(f"Found element after scroll: {element.text}")
                return element

        self.logger.warning(f"Element not found after full hierarchy: '{text}'")
        return None

    def find_element_by_attributes(
        self, attributes: "VisualAttributes", scroll_if_not_found: bool = True
    ) -> Optional[ElementMatch]:
        """
        Find UI element by visual attributes (color, size, position)

        Args:
            attributes: Visual attributes to match
            scroll_if_not_found: Automatically scroll and retry if not found

        Returns:
            ElementMatch if found, None otherwise
        """
        self.logger.debug(f"Finding element by attributes: {attributes}")

        # Capture screenshot
        region = attributes.position
        if region:
            screenshot = self.screenshot_engine.capture_region(*region)
        else:
            screenshot = self.screenshot_engine.capture_screen()

        if not screenshot:
            self.logger.error("Failed to capture screenshot")
            return None

        # Get all elements in the region
        all_elements = self.element_locator.get_all_elements(region)

        # Filter by attributes
        matching_elements = self._filter_by_attributes(all_elements, attributes, screenshot)

        if matching_elements:
            # Return element with highest confidence
            best_match = max(matching_elements, key=lambda e: e.confidence)
            self.logger.debug(f"Found element by attributes: {best_match.text}")
            return best_match

        # Try scrolling if enabled
        if scroll_if_not_found and self.enable_auto_scroll:
            self.logger.debug("Element not found by attributes, trying with scroll")
            return self._find_by_attributes_with_scroll(attributes)

        self.logger.warning("Element not found by attributes")
        return None

    def _fuzzy_find_element(
        self, text: str, region: Optional[Tuple[int, int, int, int]], case_sensitive: bool
    ) -> Optional[ElementMatch]:
        """
        Find element using fuzzy text matching

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Case sensitivity

        Returns:
            ElementMatch if found, None otherwise
        """
        # Get all elements
        all_elements = self.element_locator.get_all_elements(region)

        if not all_elements:
            return None

        # Prepare search text
        search_text = text if case_sensitive else text.lower()

        # Find partial matches
        matches = []
        for element in all_elements:
            element_text = element.text if case_sensitive else element.text.lower()

            # Check if search text is contained in element text
            if search_text in element_text or element_text in search_text:
                matches.append(element)

        if matches:
            # Return match with highest confidence
            return max(matches, key=lambda e: e.confidence)

        return None

    def _find_with_scroll(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]],
        case_sensitive: bool,
        max_scrolls: int = 3,
    ) -> Optional[ElementMatch]:
        """
        Find element with automatic scrolling

        Args:
            text: Text to search for
            region: Optional region to search
            case_sensitive: Case sensitivity
            max_scrolls: Maximum number of scroll attempts

        Returns:
            ElementMatch if found, None otherwise
        """
        for scroll_attempt in range(max_scrolls):
            # Scroll down
            pyautogui.scroll(-3)  # Negative for down
            time.sleep(0.5)  # Wait for content to load
            self._scrolls_performed += 1

            # Try finding element again
            element = self.element_locator.find_element_by_text(text, region, case_sensitive)

            if element:
                self.logger.debug(f"Found element after {scroll_attempt + 1} scroll(s)")
                return element

        return None

    def _find_by_attributes_with_scroll(
        self, attributes: "VisualAttributes", max_scrolls: int = 3
    ) -> Optional[ElementMatch]:
        """
        Find element by attributes with automatic scrolling

        Args:
            attributes: Visual attributes to match
            max_scrolls: Maximum number of scroll attempts

        Returns:
            ElementMatch if found, None otherwise
        """
        for scroll_attempt in range(max_scrolls):
            # Scroll down
            pyautogui.scroll(-3)
            time.sleep(0.5)
            self._scrolls_performed += 1

            # Try finding element again
            element = self.find_element_by_attributes(attributes, scroll_if_not_found=False)

            if element:
                self.logger.debug(
                    f"Found element by attributes after {scroll_attempt + 1} scroll(s)"
                )
                return element

        return None

    def _filter_by_attributes(
        self, elements: List[ElementMatch], attributes: VisualAttributes, screenshot: Any
    ) -> List[ElementMatch]:
        """
        Filter elements by visual attributes

        Args:
            elements: List of elements to filter
            attributes: Attributes to match
            screenshot: Screenshot for visual analysis

        Returns:
            Filtered list of elements
        """
        filtered = []

        for element in elements:
            # Check confidence threshold
            if element.confidence < attributes.confidence_threshold:
                continue

            # Check size if specified
            if attributes.size:
                target_w, target_h = attributes.size
                # Allow 20% tolerance
                if not (
                    0.8 * target_w <= element.width <= 1.2 * target_w
                    and 0.8 * target_h <= element.height <= 1.2 * target_h
                ):
                    continue

            # Check color if specified (simplified - checks dominant color in bbox)
            if attributes.color:
                if not self._check_color_match(element, attributes.color, screenshot):
                    continue

            filtered.append(element)

        return filtered

    def _check_color_match(
        self, element: ElementMatch, target_color: Tuple[int, int, int], screenshot, tolerance: int = 30
    ) -> bool:
        """
        Check if element matches target color

        Args:
            element: Element to check
            target_color: Target RGB color
            screenshot: Screenshot containing the element
            tolerance: Color matching tolerance (0-255)

        Returns:
            True if color matches within tolerance
        """
        try:
            # Crop element region from screenshot
            region = screenshot.crop(
                (element.x, element.y, element.x + element.width, element.y + element.height)
            )

            # Get dominant color (simplified - use center pixel)
            center_x = element.width // 2
            center_y = element.height // 2
            pixel_color = region.getpixel((center_x, center_y))

            # Compare colors
            if isinstance(pixel_color, int):  # Grayscale
                pixel_color = (pixel_color, pixel_color, pixel_color)

            r_diff = abs(pixel_color[0] - target_color[0])
            g_diff = abs(pixel_color[1] - target_color[1])
            b_diff = abs(pixel_color[2] - target_color[2])

            return r_diff <= tolerance and g_diff <= tolerance and b_diff <= tolerance

        except Exception as e:
            self.logger.debug(f"Color check failed: {e}")
            return False

    def get_scrolls_performed(self) -> int:
        """Get number of scrolls performed"""
        return self._scrolls_performed

    def reset_scrolls(self):
        """Reset scroll counter"""
        self._scrolls_performed = 0
    
    # =========================================================================
    # PERF-M4-002: Detection Hierarchy Implementation
    # =========================================================================
    
    def _find_via_accessibility(
        self, 
        target: str, 
        role: Optional[str] = None
    ) -> Optional[ElementMatch]:
        """
        Find element via OS Accessibility API (0-5ms).
        
        PERF-M4-002: Priority #1 - Accessibility is INSTANTANEOUS when it works.
        This should ALWAYS be tried first before any vision-based approach.
        
        Args:
            target: Text to search for (element name/title)
            role: Optional role hint (e.g., "button", "link")
        
        Returns:
            ElementMatch if found, None otherwise
        """
        try:
            # Get system bridge for accessibility
            from janus.platform.os import get_system_bridge
            bridge = get_system_bridge()
            
            # Get accessibility backend
            if hasattr(bridge, 'get_accessibility_backend'):
                accessibility = bridge.get_accessibility_backend()
                if accessibility and accessibility.is_available():
                    # Convert role string to AccessibilityRole enum if provided
                    ax_role = None
                    if role:
                        from janus.platform.accessibility.base_accessibility import AccessibilityRole
                        role_map = {
                            'button': AccessibilityRole.BUTTON,
                            'link': AccessibilityRole.LINK,
                            'text': AccessibilityRole.TEXT_FIELD,
                            'checkbox': AccessibilityRole.CHECKBOX,
                            'menu': AccessibilityRole.MENU_ITEM,
                        }
                        ax_role = role_map.get(role.lower())
                    
                    # Search for element
                    ax_element = accessibility.find_element(
                        name=target,
                        role=ax_role,
                        timeout=0.1  # Quick search only
                    )
                    
                    if ax_element and ax_element.bounds:
                        # Convert to ElementMatch
                        bounds = ax_element.bounds
                        return ElementMatch(
                            text=ax_element.name or target,
                            x=bounds['x'],
                            y=bounds['y'],
                            width=bounds['width'],
                            height=bounds['height'],
                            confidence=95.0,  # High confidence for accessibility
                        )
        except Exception as e:
            self.logger.debug(f"Accessibility search failed: {e}")
        
        return None
    
    def _find_via_apple_vision(
        self, 
        target: str, 
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[ElementMatch]:
        """
        Find element via Apple Vision.framework native OCR (50-100ms).
        
        PERF-M4-002: Priority #3 - Native macOS OCR is much faster than VLM
        but slower than accessibility. Should be used before falling back to
        expensive VLM calls.
        
        Args:
            target: Text to search for
            region: Optional region to search
        
        Returns:
            ElementMatch if found, None otherwise
        """
        try:
            # Try to use Apple Vision OCR if available
            import platform
            if platform.system() != "Darwin":
                return None
            
            # Check if apple_vision_ocr module exists
            try:
                from janus.vision.apple_vision_ocr import AppleVisionOCR
                
                # Initialize Apple Vision OCR
                apple_ocr = AppleVisionOCR()
                
                # Capture screenshot for region
                if region:
                    screenshot = self.screenshot_engine.capture_region(*region)
                else:
                    screenshot = self.screenshot_engine.capture_screen()
                
                if not screenshot:
                    return None
                
                # Run OCR with Apple Vision
                ocr_result = apple_ocr.recognize_text(screenshot)
                
                # Search for target text in results
                if ocr_result and ocr_result.texts:
                    target_lower = target.lower() if not target.isupper() else target
                    
                    for text_item in ocr_result.texts:
                        text_lower = text_item['text'].lower()
                        
                        # Check for match (exact or contains)
                        if target_lower == text_lower or target_lower in text_lower:
                            # Found match
                            bbox = text_item['bbox']
                            return ElementMatch(
                                text=text_item['text'],
                                x=bbox['x'],
                                y=bbox['y'],
                                width=bbox['width'],
                                height=bbox['height'],
                                confidence=text_item.get('confidence', 90.0),
                            )
                
            except ImportError:
                # Apple Vision OCR not available - will be created later
                self.logger.debug("Apple Vision OCR module not yet available")
                pass
            
        except Exception as e:
            self.logger.debug(f"Apple Vision OCR search failed: {e}")
        
        return None
