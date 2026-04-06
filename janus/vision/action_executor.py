"""
Action Executor - Responsible for executing vision-based actions

This module handles the execution of vision-guided UI actions:
- click_viz: Click on elements found by vision
- select_viz: Select text or elements
- extract_viz: Extract text from elements
- scroll_until_viz: Scroll until target element is found

Extracted from VisionActionMapper as part of TICKET-REVIEW-001
"""

import time
from typing import Any, Dict, Optional, Tuple

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

    class MockPyAutoGUI:
        @staticmethod
        def click(*args, **kwargs):
            pass

        @staticmethod
        def scroll(*args, **kwargs):
            pass

    pyautogui = MockPyAutoGUI()

from janus.logging import get_logger

from .element_locator import ElementMatch
from .vision_types import ActionResult

# PERF-M4-002: Import accessibility types for fast-path
try:
    from janus.platform.accessibility.base_accessibility import AccessibilityRole
except ImportError:
    AccessibilityRole = None

# PERF-M4-002: Constants for accessibility fast-path
AX_FIND_TIMEOUT_SECONDS = 0.5  # Fast timeout for accessibility element search


class ActionExecutor:
    """
    Executes vision-based UI actions
    """

    def __init__(
        self,
        element_finder,
        action_verifier=None,
        enable_auto_retry: bool = True,
        max_retries: int = 3,
        accessibility_backend=None,  # PERF-M4-002: AX backend for fast-path
    ):
        """
        Initialize Action Executor

        Args:
            element_finder: ElementFinder instance for finding elements
            action_verifier: Optional ActionVerifier for post-action verification
            enable_auto_retry: Enable automatic retry on failures
            max_retries: Maximum number of retries
            accessibility_backend: Optional accessibility backend for fast-path (PERF-M4-002)
        """
        self.logger = get_logger("action_executor")
        self.element_finder = element_finder
        self.action_verifier = action_verifier
        self.enable_auto_retry = enable_auto_retry
        self.max_retries = max_retries
        self.accessibility_backend = accessibility_backend  # PERF-M4-002

        # Statistics
        self._stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "retries_used": 0,
            "ax_fastpath_hits": 0,  # PERF-M4-002: Track AX usage
            "vision_fallbacks": 0,   # PERF-M4-002: Track vision fallbacks
        }

    def click_viz(
        self, target: str, region: Optional[Tuple[int, int, int, int]] = None, verify: bool = True, element_id: Optional[str] = None
    ) -> ActionResult:
        """
        Vision-based click action - finds and clicks an element
        
        PERF-M4-002: Now tries accessibility (AX) fast-path FIRST before vision fallback.

        Args:
            target: Text or description of element to click (can also be an element_id)
            region: Optional region to search
            verify: Enable post-action verification
            element_id: Optional explicit element ID from Set-of-Marks

        Returns:
            ActionResult with details of the action
        """
        self.logger.info(f"Vision click: {target}")
        self._stats["total_actions"] += 1

        # PERF-M4-002: Try accessibility fast-path FIRST
        if self.accessibility_backend and not element_id:  # Don't use AX for element_id (vision-only)
            try:
                
                self.logger.debug(f"🚀 Trying accessibility fast-path for: {target}")
                
                # Try to find element by name (button, link, etc.)
                # First try as button (most common for clicks)
                ax_element = self.accessibility_backend.find_element(
                    name=target,
                    role=AccessibilityRole.BUTTON,
                    timeout=AX_FIND_TIMEOUT_SECONDS  # Fast timeout for AX
                )
                
                # If not found as button, try without role filter
                if not ax_element:
                    ax_element = self.accessibility_backend.find_element(
                        name=target,
                        timeout=AX_FIND_TIMEOUT_SECONDS
                    )
                
                if ax_element and ax_element.is_enabled():
                    self.logger.info(f"✅ AX FAST-PATH HIT: Found '{target}' via accessibility")
                    self._stats["ax_fastpath_hits"] += 1
                    
                    # Click via accessibility API
                    click_result = self.accessibility_backend.click_element(ax_element)
                    
                    if click_result.success:
                        self.logger.info(f"✅ AX click succeeded for '{target}' - NO VISION NEEDED")
                        self._stats["successful_actions"] += 1
                        
                        return ActionResult(
                            success=True,
                            action="click_viz",
                            element=None,  # AX element, not vision element
                            message=f"Clicked '{target}' via accessibility (fast-path)",
                            metadata={"method": "accessibility", "ax_role": ax_element.role.value}
                        )
                    else:
                        self.logger.debug(f"AX click failed: {click_result.error}, falling back to vision")
                else:
                    self.logger.debug(f"Element '{target}' not found via AX, falling back to vision")
                    
            except Exception as e:
                self.logger.debug(f"Accessibility fast-path failed: {e}, falling back to vision")
        
        # Vision fallback: original vision-based implementation
        self.logger.debug(f"🔍 VISION FALLBACK: Using vision for '{target}'")
        self._stats["vision_fallbacks"] += 1

        retry_count = 0
        last_error = None

        # Retry loop
        max_attempts = self.max_retries if self.enable_auto_retry else 1

        for attempt in range(max_attempts):
            try:
                # Find element
                # VISION-FOUNDATION-001: Support element_id from Set-of-Marks
                # Priority: explicit element_id > ID pattern in target > text search
                
                element = None
                
                # 1. If explicit element_id is provided, use it
                if element_id:
                    self.logger.debug(f"Using explicit element_id: {element_id}")
                    element = self.element_finder.find_element_by_id(element_id, region)
                
                # 2. If target looks like an element ID (pattern: word_number), try ID lookup first
                elif "_" in target and any(c.isdigit() for c in target.split("_")[-1]):
                    self.logger.debug(f"Target '{target}' matches element_id pattern, trying ID lookup first")
                    element = self.element_finder.find_element_by_id(target, region)
                    
                    # If ID lookup fails, fall back to text search
                    if not element:
                        self.logger.debug(f"Element ID '{target}' not found, falling back to text search")
                        element = self.element_finder.find_element_by_text(
                            target, region, scroll_if_not_found=True
                        )
                else:
                    # 3. Default: find by text
                    element = self.element_finder.find_element_by_text(
                        target, region, scroll_if_not_found=True
                    )

                if not element:
                    last_error = f"Element '{target}' not found"
                    retry_count += 1
                    if attempt < max_attempts - 1:
                        self.logger.debug(f"Retry {attempt + 1}/{max_attempts}")
                        time.sleep(0.5)
                        continue
                    else:
                        break

                # Capture pre-action state for verification
                pre_state = None
                if verify and self.action_verifier:
                    pre_state = self.action_verifier.capture_pre_action_state()

                # Click at center of element
                pyautogui.click(element.center_x, element.center_y)
                time.sleep(0.3)  # Wait for UI to respond

                # Post-action verification
                verification = None
                if verify and self.action_verifier:
                    verification = self.action_verifier.verify_action("click", target, pre_state)

                self._stats["successful_actions"] += 1
                self._stats["retries_used"] += retry_count

                return ActionResult(
                    success=True,
                    action="click_viz",
                    element=element,
                    message=f"Clicked on '{element.text}' at ({element.center_x}, {element.center_y})",
                    retry_count=retry_count,
                    verification=verification,
                )

            except Exception as e:
                last_error = str(e)
                retry_count += 1
                self.logger.error(f"Click attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(0.5)

        # All retries failed
        self._stats["failed_actions"] += 1
        self._stats["retries_used"] += retry_count

        return ActionResult(
            success=False,
            action="click_viz",
            message="Failed to click element",
            error=last_error,
            retry_count=retry_count,
        )

    def select_viz(
        self, target: str, region: Optional[Tuple[int, int, int, int]] = None, verify: bool = True, element_id: Optional[str] = None
    ) -> ActionResult:
        """
        Vision-based select action - finds and selects an element
        
        PERF-M4-002: Now tries accessibility (AX) fast-path FIRST before vision fallback.

        Args:
            target: Text or description of element to select (can also be an element_id)
            region: Optional region to search
            verify: Enable post-action verification
            element_id: Optional explicit element ID from Set-of-Marks

        Returns:
            ActionResult with details of the action
        """
        self.logger.info(f"Vision select: {target}")
        self._stats["total_actions"] += 1

        # PERF-M4-002: Try accessibility fast-path FIRST
        if self.accessibility_backend and not element_id:
            try:
                
                self.logger.debug(f"🚀 Trying accessibility fast-path for select: {target}")
                
                # Try to find element (text field, combo box, etc.)
                ax_element = self.accessibility_backend.find_element(
                    name=target,
                    role=AccessibilityRole.TEXT_FIELD,
                    timeout=AX_FIND_TIMEOUT_SECONDS
                )
                
                # If not found as text field, try combo box or generic
                if not ax_element:
                    ax_element = self.accessibility_backend.find_element(
                        name=target,
                        role=AccessibilityRole.COMBO_BOX,
                        timeout=AX_FIND_TIMEOUT_SECONDS
                    )
                
                if not ax_element:
                    ax_element = self.accessibility_backend.find_element(
                        name=target,
                        timeout=AX_FIND_TIMEOUT_SECONDS
                    )
                
                if ax_element and ax_element.is_enabled():
                    self.logger.info(f"✅ AX FAST-PATH HIT: Found '{target}' via accessibility")
                    self._stats["ax_fastpath_hits"] += 1
                    
                    # Focus element via accessibility API (selects text)
                    focus_result = self.accessibility_backend.focus_element(ax_element)
                    
                    if focus_result.success:
                        self.logger.info(f"✅ AX select succeeded for '{target}' - NO VISION NEEDED")
                        self._stats["successful_actions"] += 1
                        
                        return ActionResult(
                            success=True,
                            action="select_viz",
                            element=None,
                            message=f"Selected '{target}' via accessibility (fast-path)",
                            metadata={"method": "accessibility", "ax_role": ax_element.role.value}
                        )
                    else:
                        self.logger.debug(f"AX select failed: {focus_result.error}, falling back to vision")
                else:
                    self.logger.debug(f"Element '{target}' not found via AX, falling back to vision")
                    
            except Exception as e:
                self.logger.debug(f"Accessibility fast-path failed: {e}, falling back to vision")
        
        # Vision fallback
        self.logger.debug(f"🔍 VISION FALLBACK: Using vision for select '{target}'")
        self._stats["vision_fallbacks"] += 1

        try:
            # Find element - support element_id like click_viz
            element = None
            
            if element_id:
                element = self.element_finder.find_element_by_id(element_id, region)
            elif "_" in target and any(c.isdigit() for c in target.split("_")[-1]):
                element = self.element_finder.find_element_by_id(target, region)
                if not element:
                    element = self.element_finder.find_element_by_text(
                        target, region, scroll_if_not_found=True
                    )
            else:
                element = self.element_finder.find_element_by_text(
                    target, region, scroll_if_not_found=True
                )

            if not element:
                self._stats["failed_actions"] += 1
                return ActionResult(
                    success=False,
                    action="select_viz",
                    message="Element not found",
                    error=f"Element '{target}' not found",
                )

            # Capture pre-action state
            pre_state = None
            if verify and self.action_verifier:
                pre_state = self.action_verifier.capture_pre_action_state()

            # Triple-click to select (common pattern for text selection)
            pyautogui.click(element.center_x, element.center_y, clicks=3)
            time.sleep(0.2)

            # Post-action verification
            verification = None
            if verify and self.action_verifier:
                verification = self.action_verifier.verify_action("select", target, pre_state)

            self._stats["successful_actions"] += 1

            return ActionResult(
                success=True,
                action="select_viz",
                element=element,
                message=f"Selected '{element.text}' at ({element.center_x}, {element.center_y})",
                verification=verification,
            )

        except Exception as e:
            self._stats["failed_actions"] += 1
            return ActionResult(
                success=False, action="select_viz", message="Failed to select element", error=str(e)
            )

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
        self.logger.info(f"Vision extract: {target}")
        self._stats["total_actions"] += 1

        try:
            # Find element - support element_id like click_viz
            element = None
            
            if element_id:
                element = self.element_finder.find_element_by_id(element_id, region)
            elif "_" in target and any(c.isdigit() for c in target.split("_")[-1]):
                element = self.element_finder.find_element_by_id(target, region)
                if not element:
                    element = self.element_finder.find_element_by_text(
                        target, region, scroll_if_not_found=True
                    )
            else:
                element = self.element_finder.find_element_by_text(
                    target, region, scroll_if_not_found=True
                )

            if not element:
                self._stats["failed_actions"] += 1
                return ActionResult(
                    success=False,
                    action="extract_viz",
                    message="Element not found",
                    error=f"Element '{target}' not found",
                )

            self._stats["successful_actions"] += 1

            return ActionResult(
                success=True,
                action="extract_viz",
                element=element,
                message=f"Extracted text: '{element.text}'",
            )

        except Exception as e:
            self._stats["failed_actions"] += 1
            return ActionResult(
                success=False, action="extract_viz", message="Failed to extract text", error=str(e)
            )

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
        self.logger.info(f"Vision scroll_until: {target}, max_scrolls={max_scrolls}")
        self._stats["total_actions"] += 1

        try:
            # Try finding element first without scrolling
            element = self.element_finder.find_element_by_text(target, scroll_if_not_found=False)

            if element:
                self.logger.debug("Element found without scrolling")
                self._stats["successful_actions"] += 1
                return ActionResult(
                    success=True,
                    action="scroll_until_viz",
                    element=element,
                    message=f"Found '{element.text}' without scrolling",
                )

            # Scroll and search
            for scroll_count in range(1, max_scrolls + 1):
                self.logger.debug(f"Scroll attempt {scroll_count}/{max_scrolls}")

                # Perform scroll
                pyautogui.scroll(scroll_amount)
                time.sleep(0.5)  # Wait for content to load

                # Search for element
                element = self.element_finder.find_element_by_text(target, scroll_if_not_found=False)

                if element:
                    self.logger.info(f"Element found after {scroll_count} scroll(s)")
                    self._stats["successful_actions"] += 1
                    return ActionResult(
                        success=True,
                        action="scroll_until_viz",
                        element=element,
                        message=f"Found '{element.text}' after {scroll_count} scroll(s)",
                        retry_count=scroll_count,
                    )

            # Element not found after max scrolls
            self.logger.warning(f"Element '{target}' not found after {max_scrolls} scrolls")
            self._stats["failed_actions"] += 1
            return ActionResult(
                success=False,
                action="scroll_until_viz",
                message=f"Element not found after {max_scrolls} scrolls",
                error=f"Element '{target}' not found",
                retry_count=max_scrolls,
            )

        except Exception as e:
            self._stats["failed_actions"] += 1
            return ActionResult(
                success=False,
                action="scroll_until_viz",
                message="Failed to scroll until element",
                error=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        stats = self._stats.copy()
        if stats["total_actions"] > 0:
            stats["success_rate"] = stats["successful_actions"] / stats["total_actions"]
            stats["avg_retries"] = stats["retries_used"] / stats["total_actions"]
        else:
            stats["success_rate"] = 0.0
            stats["avg_retries"] = 0.0
        return stats

    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "retries_used": 0,
        }
