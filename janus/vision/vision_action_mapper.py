"""
Vision-to-Action Mapper - The missing layer between vision and physical actions
Ticket: Vision-to-Action Mapping (VAM)

This module bridges the gap between what the vision system sees (OCR + bounding boxes)
and the physical actions that can be performed (click, select, scroll).

Without this layer, vision ≠ action → the agent is not truly universal.

REFACTORED (TICKET-REVIEW-001): This module now acts as a facade/coordinator,
delegating to specialized components:
- ElementFinder: Finds elements on screen
- ActionExecutor: Executes vision-based actions
- ActionVerifier: Verifies action results

This maintains backward compatibility while improving maintainability.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Try to import optional dependencies
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# Try to import pyautogui, but don't fail if not available
try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

    # Create a mock pyautogui for testing/CI environments
    class MockPyAutoGUI:
        @staticmethod
        def click(*args, **kwargs):
            pass

        @staticmethod
        def scroll(*args, **kwargs):
            pass

    pyautogui = MockPyAutoGUI()

from janus.logging import get_logger

from ..utils.retry import FallbackChain, RetryConfig, retry_with_fallback
from .action_executor import ActionExecutor
from .action_verifier import ActionVerifier
from .element_finder import ElementFinder
from .element_locator import ElementLocator, ElementMatch
from .ocr.factory import get_ocr_engine
from .ocr.interface import OCREngine as OCREngineInterface
from .ocr.interface import OCRResult
from .screenshot_engine import ScreenshotEngine
from .vision_types import ActionResult, ElementType, VisualAttributes


class VisionActionMapper:
    """
    Maps vision data (OCR + bounding boxes) to physical actions

    This is the critical layer that makes Janus universal:
    - Finds elements by text with fuzzy matching
    - Finds elements by visual attributes (color, size, position)
    - Converts bounding boxes to screen coordinates
    - Executes vision-based actions (click, select, extract)
    - Automatically verifies actions with post-action vision
    - Handles scroll and retry for robustness

    REFACTORED (TICKET-REVIEW-001): Now delegates to specialized components:
    - ElementFinder: Element search and scrolling
    - ActionExecutor: Action execution with retry
    - ActionVerifier: Post-action verification
    """

    def __init__(
        self,
        screenshot_engine: Optional[ScreenshotEngine] = None,
        ocr_engine: Optional[OCREngineInterface] = None,
        element_locator: Optional[ElementLocator] = None,
        enable_auto_scroll: bool = True,
        enable_auto_retry: bool = True,
        max_retries: int = 3,
        enable_post_action_verification: bool = True,
        som_engine: Any = None,  # VISION-FOUNDATION-001: Inject SetOfMarksEngine
        enable_accessibility_fastpath: bool = True,  # PERF-M4-002: Enable AX fast-path
    ):
        """
        Initialize Vision-to-Action Mapper

        Args:
            screenshot_engine: Screenshot engine for capturing screen
            ocr_engine: OCR engine for text recognition (uses native factory if None)
            element_locator: Element locator for finding elements
            enable_auto_scroll: Enable automatic scrolling to find elements
            enable_auto_retry: Enable automatic retry on failures
            max_retries: Maximum number of retries
            enable_post_action_verification: Enable automatic post-action verification
            som_engine: Optional SetOfMarksEngine for element_id resolution
            enable_accessibility_fastpath: Enable accessibility fast-path before vision (PERF-M4-002)
        """
        self.logger = get_logger("vision_action_mapper")

        # Initialize base components
        self.screenshot_engine = screenshot_engine or ScreenshotEngine()
        # TICKET-SWITCH-NATIVE: Use native OCR factory for platform-optimized engines
        # This automatically selects the best engine: Vision.framework (macOS), Windows.Media.Ocr (Windows), RapidOCR (Linux)
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self.element_locator = element_locator or ElementLocator(
            screenshot_engine=self.screenshot_engine, ocr_engine=self.ocr_engine
        )

        # Configuration
        self.enable_auto_scroll = enable_auto_scroll
        self.enable_auto_retry = enable_auto_retry
        self.max_retries = max_retries
        self.enable_post_action_verification = enable_post_action_verification
        self.enable_accessibility_fastpath = enable_accessibility_fastpath

        # PERF-M4-002: Initialize accessibility backend for fast-path
        self.accessibility_backend = None
        if enable_accessibility_fastpath:
            try:
                from janus.platform.accessibility.factory import get_accessibility_backend
                backend = get_accessibility_backend()
                if backend.is_available():
                    self.accessibility_backend = backend
                    self.logger.info("✓ Accessibility fast-path enabled")
                else:
                    self.logger.debug("Accessibility backend not available - vision-only mode")
            except Exception as e:
                self.logger.debug(f"Failed to initialize accessibility backend: {e}")

        # Initialize specialized components (TICKET-REVIEW-001 refactoring)
        # VISION-FOUNDATION-001: Pass SOM engine to ElementFinder for element_id resolution
        self.element_finder = ElementFinder(
            screenshot_engine=self.screenshot_engine,
            ocr_engine=self.ocr_engine,
            element_locator=self.element_locator,
            enable_auto_scroll=enable_auto_scroll,
            som_engine=som_engine,  # Pass SOM engine for element_id support
        )

        self.action_verifier = (
            ActionVerifier(screenshot_engine=self.screenshot_engine)
            if enable_post_action_verification
            else None
        )

        self.action_executor = ActionExecutor(
            element_finder=self.element_finder,
            action_verifier=self.action_verifier,
            enable_auto_retry=enable_auto_retry,
            max_retries=max_retries,
            accessibility_backend=self.accessibility_backend,  # PERF-M4-002: Pass AX backend
        )

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
        Find UI element by text content with enhanced matching
        
        PERF-M4-002: Now uses strict detection hierarchy via ElementFinder.

        Args:
            text: Text to search for
            region: Optional region to search (x, y, width, height)
            case_sensitive: Whether search should be case sensitive
            fuzzy_match: Enable fuzzy matching for partial text matches
            scroll_if_not_found: Automatically scroll and retry if not found
            role: Optional role hint for accessibility (e.g., "button", "link")

        Returns:
            ElementMatch if found, None otherwise
        """
        # Delegate to ElementFinder with role hint (PERF-M4-002)
        return self.element_finder.find_element_by_text(
            text, region, case_sensitive, fuzzy_match, scroll_if_not_found, role
        )

    def find_element_by_attributes(
        self, attributes: VisualAttributes, scroll_if_not_found: bool = True
    ) -> Optional[ElementMatch]:
        """
        Find UI element by visual attributes (color, size, position)

        Args:
            attributes: Visual attributes to match
            scroll_if_not_found: Automatically scroll and retry if not found

        Returns:
            ElementMatch if found, None otherwise
        """
        # Delegate to ElementFinder (TICKET-REVIEW-001)
        return self.element_finder.find_element_by_attributes(attributes, scroll_if_not_found)

    def click_viz(
        self, target: str, region: Optional[Tuple[int, int, int, int]] = None, verify: bool = True, element_id: Optional[str] = None
    ) -> ActionResult:
        """
        Vision-based click action - finds and clicks an element

        Args:
            target: Text or description of element to click (can also be an element_id)
            region: Optional region to search
            verify: Enable post-action verification
            element_id: Optional explicit element ID from Set-of-Marks

        Returns:
            ActionResult with details of the action
        """
        # Delegate to ActionExecutor (TICKET-REVIEW-001)
        # VISION-FOUNDATION-001: Pass element_id for SOM support
        return self.action_executor.click_viz(target, region, verify, element_id)

    def select_viz(
        self, target: str, region: Optional[Tuple[int, int, int, int]] = None, verify: bool = True, element_id: Optional[str] = None
    ) -> ActionResult:
        """
        Vision-based select action - finds and selects an element

        Args:
            target: Text or description of element to select (can also be an element_id)
            region: Optional region to search
            verify: Enable post-action verification
            element_id: Optional explicit element ID from Set-of-Marks

        Returns:
            ActionResult with details of the action
        """
        # Delegate to ActionExecutor (TICKET-REVIEW-001)
        # VISION-FOUNDATION-001: Pass element_id for SOM support
        return self.action_executor.select_viz(target, region, verify, element_id)

    def extract_viz(
        self, target: str, region: Optional[Tuple[int, int, int, int]] = None, element_id: Optional[str] = None
    ) -> ActionResult:
        """
        Vision-based extract action - finds and extracts text from an element

        Args:
            target: Text or description of element to extract (can also be an element_id)
            region: Optional region to search
            element_id: Optional explicit element ID from Set-of-Marks

        Returns:
            ActionResult with extracted text
        """
        # Delegate to ActionExecutor (TICKET-REVIEW-001)
        # VISION-FOUNDATION-001: Pass element_id for SOM support
        return self.action_executor.extract_viz(target, region, element_id)

    def scroll_until_viz(
        self, target: str, max_scrolls: int = 10, scroll_amount: int = -3
    ) -> ActionResult:
        """
        Vision-based scroll action - scrolls until target element is found

        Args:
            target: Text or description of element to find
            max_scrolls: Maximum number of scroll attempts
            scroll_amount: Amount to scroll each time (negative = down)

        Returns:
            ActionResult with element info if found
        """
        # Delegate to ActionExecutor (TICKET-REVIEW-001)
        return self.action_executor.scroll_until_viz(target, max_scrolls, scroll_amount)

    def find_on_page(
        self,
        target: str,
        chrome_adapter=None,
        max_scrolls: int = 10,
        fallback_to_vision: bool = True,
    ) -> ActionResult:
        """
        Find element on page using smart scanning (TICKET-OPT-002)
        
        This method leverages ChromeAdapter's autonomous scanning capability
        to find elements without multiple LLM calls. If ChromeAdapter is not
        available or fails, it can fallback to vision-based scrolling.
        
        Args:
            target: Text to search for
            chrome_adapter: Optional ChromeAdapter instance for DOM-based scanning
            max_scrolls: Maximum number of scroll attempts
            fallback_to_vision: If True, use vision-based search as fallback
        
        Returns:
            ActionResult with element info if found
        """
        self.logger.info(f"Finding on page: '{target}' (smart_scan={chrome_adapter is not None})")
        self._stats["total_actions"] += 1
        
        # Try Chrome adapter smart scanning first
        if chrome_adapter:
            try:
                self.logger.debug("Using ChromeAdapter smart scanning")
                scan_result = chrome_adapter.scan_page_for(target, max_scrolls=max_scrolls)
                
                if scan_result["status"] == "success" and scan_result["found"]:
                    # Convert DOM coordinates to ElementMatch for consistency
                    # scan_result["x"] and scan_result["y"] are CENTER coordinates from DOM (rect.left + rect.width/2)
                    # ElementMatch expects TOP-LEFT corner (x, y), so we convert:
                    #   top_left_x = center_x - width/2
                    #   top_left_y = center_y - height/2
                    # ElementMatch then calculates center_x = x + width/2, center_y = y + height/2
                    from .element_locator import ElementMatch
                    
                    element = ElementMatch(
                        text=target,
                        x=scan_result["x"] - scan_result.get("width", 0) // 2,  # center_x - width/2 = top_left_x
                        y=scan_result["y"] - scan_result.get("height", 0) // 2,  # center_y - height/2 = top_left_y
                        width=scan_result.get("width", 0),
                        height=scan_result.get("height", 0),
                        confidence=95.0,  # High confidence for DOM-based search
                    )
                    
                    self._stats["successful_actions"] += 1
                    self._stats["scrolls_performed"] += scan_result["scrolls_done"]
                    
                    return ActionResult(
                        success=True,
                        action="find_on_page",
                        element=element,
                        message=f"Found '{target}' using smart scan after {scan_result['scrolls_done']} scroll(s)",
                        retry_count=scan_result["scrolls_done"],
                    )
                elif scan_result["status"] == "success" and not scan_result["found"]:
                    # Not found via smart scan
                    if not fallback_to_vision:
                        self._stats["failed_actions"] += 1
                        return ActionResult(
                            success=False,
                            action="find_on_page",
                            message=f"Element '{target}' not found via smart scan",
                            error=f"Element not found after {scan_result['scrolls_done']} scrolls",
                            retry_count=scan_result["scrolls_done"],
                        )
                    else:
                        self.logger.debug("Smart scan didn't find element, falling back to vision")
                else:
                    # Smart scan failed
                    self.logger.warning(f"Smart scan failed: {scan_result.get('error')}")
                    if not fallback_to_vision:
                        self._stats["failed_actions"] += 1
                        return ActionResult(
                            success=False,
                            action="find_on_page",
                            message="Smart scan failed",
                            error=scan_result.get("error", "Unknown error"),
                        )
                    else:
                        self.logger.debug("Smart scan failed, falling back to vision")
            
            except Exception as e:
                self.logger.error(f"ChromeAdapter scanning failed: {e}")
                if not fallback_to_vision:
                    self._stats["failed_actions"] += 1
                    return ActionResult(
                        success=False,
                        action="find_on_page",
                        message="Smart scan error",
                        error=str(e),
                    )
        
        # Fallback to vision-based scrolling
        if fallback_to_vision or not chrome_adapter:
            self.logger.debug("Using vision-based scroll_until")
            return self.scroll_until_viz(target, max_scrolls=max_scrolls)
        
        # No adapter and no fallback
        self._stats["failed_actions"] += 1
        return ActionResult(
            success=False,
            action="find_on_page",
            message="No scanning method available",
            error="ChromeAdapter not provided and vision fallback disabled",
        )

    def bbox_to_screen_coords(
        self, bbox: Tuple[int, int, int, int], region_offset: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int, int, int]:
        """
        Convert bounding box to screen coordinates

        Args:
            bbox: Bounding box as (x, y, width, height)
            region_offset: Optional region offset as (x_offset, y_offset)

        Returns:
            Screen coordinates as (x, y, width, height)
        """
        x, y, w, h = bbox

        if region_offset:
            offset_x, offset_y = region_offset
            x += offset_x
            y += offset_y

        return (x, y, w, h)

    def get_element_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Get center coordinates of a bounding box

        Args:
            bbox: Bounding box as (x, y, width, height)

        Returns:
            Center coordinates as (x, y)
        """
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)



    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about vision-action mapping

        Returns:
            Dictionary with statistics
        """
        # Combine stats from ActionExecutor and ElementFinder (TICKET-REVIEW-001)
        executor_stats = self.action_executor.get_stats()
        executor_stats["scrolls_performed"] = self.element_finder.get_scrolls_performed()
        return executor_stats

    def reset_stats(self):
        """Reset statistics"""
        # Reset stats in delegated components (TICKET-REVIEW-001)
        self.action_executor.reset_stats()
        self.element_finder.reset_scrolls()
