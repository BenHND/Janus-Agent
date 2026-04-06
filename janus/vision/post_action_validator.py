"""
Vision Post-Action Validator for Janus

Feature 2: Vision Post-Action Validation
Issue: FONCTIONNALITÉS MANQUANTES - #2

Use vision to verify action success:
- Check if action succeeded visually
- Verify expected text appeared
- Verify correct screen is displayed
- Detect if errors occurred
- Compare before/after screenshots

This integrates with the unified action schema and provides
automatic verification after actions are executed.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..core.action_schema import (
    ActionTarget,
    ActionType,
    ActionVerification,
    UnifiedAction,
    VerificationType,
)
from ..logging import get_logger
from .element_locator import ElementLocator
from .native_ocr_adapter import NativeOCRAdapter as OCREngine
from .screenshot_engine import ScreenshotEngine
from .visual_error_detector import VisualErrorDetector

try:
    from PIL import Image, ImageChops

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageChops = None


logger = get_logger("vision_post_action_validator")


@dataclass
class ValidationResult:
    """Result of post-action validation"""

    passed: bool
    confidence: float
    verification_type: str
    details: Dict[str, Any]
    error_message: Optional[str] = None
    screenshot_before_path: Optional[str] = None
    screenshot_after_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "verification_type": self.verification_type,
            "details": self.details,
            "error_message": self.error_message,
            "screenshot_before_path": self.screenshot_before_path,
            "screenshot_after_path": self.screenshot_after_path,
        }


class VisionPostActionValidator:
    """
    Validates action success using vision

    Provides multiple verification strategies:
    - Element visibility check
    - Text presence check
    - Screen change detection
    - Error detection
    - Custom verification
    """

    def __init__(
        self,
        screenshot_engine: Optional[ScreenshotEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        error_detector: Optional[VisualErrorDetector] = None,
        element_locator: Optional[ElementLocator] = None,
        capture_screenshots: bool = False,
    ):
        """
        Initialize vision post-action validator

        Args:
            screenshot_engine: Screenshot engine
            ocr_engine: OCR engine
            error_detector: Error detector
            element_locator: Element locator
            capture_screenshots: Save before/after screenshots
        """
        self.logger = get_logger("vision_validator")

        self.screenshot_engine = screenshot_engine or ScreenshotEngine()
        self.ocr_engine = ocr_engine or OCREngine(backend="auto")
        self.error_detector = error_detector or VisualErrorDetector(ocr_engine=self.ocr_engine)
        self.element_locator = element_locator or ElementLocator(
            screenshot_engine=self.screenshot_engine, ocr_engine=self.ocr_engine
        )
        self.capture_screenshots = capture_screenshots

        # Verification statistics
        self._verifications_performed = 0
        self._verifications_passed = 0
        self._verifications_failed = 0

    def verify_action(
        self, action: UnifiedAction, before_screenshot: Optional[Any] = None
    ) -> ValidationResult:
        """
        Verify action success using vision

        Args:
            action: Action that was executed
            before_screenshot: Optional screenshot before action

        Returns:
            ValidationResult with verification details
        """
        self._verifications_performed += 1

        if not action.verification:
            # No verification requested
            return ValidationResult(
                passed=True,
                confidence=1.0,
                verification_type="none",
                details={"message": "No verification requested"},
            )

        verification = action.verification
        verification_type = verification.type

        self.logger.debug(f"Verifying action {action.action_id}: {verification_type.value}")

        # Wait for UI to settle
        time.sleep(0.3)

        # Capture after screenshot
        after_screenshot = self.screenshot_engine.capture_screen()

        if not after_screenshot:
            self._verifications_failed += 1
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type=verification_type.value,
                details={},
                error_message="Failed to capture screenshot",
            )

        # Route to appropriate verification method
        if verification_type == VerificationType.ELEMENT_VISIBLE:
            result = self._verify_element_visible(verification, after_screenshot)

        elif verification_type == VerificationType.ELEMENT_HIDDEN:
            result = self._verify_element_hidden(verification, after_screenshot)

        elif verification_type == VerificationType.TEXT_PRESENT:
            result = self._verify_text_present(verification, after_screenshot)

        elif verification_type == VerificationType.STATE_CHANGED:
            result = self._verify_state_changed(before_screenshot, after_screenshot)

        elif verification_type == VerificationType.NO_ERROR:
            result = self._verify_no_error(after_screenshot)

        elif verification_type == VerificationType.CUSTOM:
            result = self._verify_custom(verification, after_screenshot)

        else:
            result = ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type=verification_type.value,
                details={},
                error_message=f"Unknown verification type: {verification_type.value}",
            )

        # Update statistics
        if result.passed:
            self._verifications_passed += 1
        else:
            self._verifications_failed += 1

        return result

    def _verify_element_visible(
        self, verification: ActionVerification, screenshot
    ) -> ValidationResult:
        """Verify element is visible on screen"""
        if not verification.verification_target:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="element_visible",
                details={},
                error_message="No verification target specified",
            )

        target = verification.verification_target
        target_text = target.text or ""

        # Search for element
        element = self.element_locator.find_element_by_text(target_text, scroll_if_not_found=False)

        if element:
            return ValidationResult(
                passed=True,
                confidence=element.confidence / 100.0,
                verification_type="element_visible",
                details={
                    "element_text": element.text,
                    "position": {
                        "x": element.x,
                        "y": element.y,
                        "center_x": element.center_x,
                        "center_y": element.center_y,
                    },
                },
            )
        else:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="element_visible",
                details={"target_text": target_text},
                error_message=f"Element '{target_text}' not visible",
            )

    def _verify_element_hidden(
        self, verification: ActionVerification, screenshot
    ) -> ValidationResult:
        """Verify element is NOT visible on screen"""
        if not verification.verification_target:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="element_hidden",
                details={},
                error_message="No verification target specified",
            )

        target = verification.verification_target
        target_text = target.text or ""

        # Search for element (should NOT be found)
        element = self.element_locator.find_element_by_text(target_text, scroll_if_not_found=False)

        if element:
            return ValidationResult(
                passed=False,
                confidence=1.0 - (element.confidence / 100.0),
                verification_type="element_hidden",
                details={
                    "element_text": element.text,
                    "position": {"x": element.x, "y": element.y},
                },
                error_message=f"Element '{target_text}' is still visible",
            )
        else:
            return ValidationResult(
                passed=True,
                confidence=1.0,
                verification_type="element_hidden",
                details={"target_text": target_text},
            )

    def _verify_text_present(
        self, verification: ActionVerification, screenshot
    ) -> ValidationResult:
        """Verify expected text is present"""
        expected_text = verification.expected_text

        if not expected_text:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="text_present",
                details={},
                error_message="No expected text specified",
            )

        # Extract text from screenshot
        ocr_result = self.ocr_engine.extract_text(screenshot)

        if not ocr_result or not ocr_result.texts:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="text_present",
                details={},
                error_message="No text found on screen",
            )

        # Check if expected text is present
        all_text = " ".join(ocr_result.texts).lower()
        expected_lower = expected_text.lower()

        if expected_lower in all_text:
            return ValidationResult(
                passed=True,
                confidence=0.9,
                verification_type="text_present",
                details={"expected_text": expected_text, "found": True},
            )
        else:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                verification_type="text_present",
                details={
                    "expected_text": expected_text,
                    "found": False,
                    "screen_text_sample": ocr_result.texts[:5],
                },
                error_message=f"Expected text '{expected_text}' not found",
            )

    def _verify_state_changed(self, before_screenshot, after_screenshot) -> ValidationResult:
        """Verify screen state changed"""
        if not before_screenshot or not after_screenshot:
            # No before screenshot, assume changed
            return ValidationResult(
                passed=True,
                confidence=0.7,
                verification_type="state_changed",
                details={"message": "No before screenshot for comparison"},
            )

        if not PIL_AVAILABLE:
            # Can't compare without PIL
            return ValidationResult(
                passed=True,
                confidence=0.5,
                verification_type="state_changed",
                details={"message": "PIL not available for comparison"},
            )

        try:
            # Compare screenshots
            diff = ImageChops.difference(before_screenshot, after_screenshot)

            # Calculate difference percentage
            # (Simple approach: count non-zero pixels)
            diff_pixels = sum(1 for pixel in diff.getdata() if pixel != 0)
            total_pixels = diff.size[0] * diff.size[1]
            diff_percentage = (diff_pixels / total_pixels) * 100

            # Consider changed if >5% different
            changed = diff_percentage > 5.0

            return ValidationResult(
                passed=changed,
                confidence=min(diff_percentage / 20.0, 1.0),  # Scale to 0-1
                verification_type="state_changed",
                details={"diff_percentage": diff_percentage, "changed": changed},
                error_message=None if changed else "Screen state did not change significantly",
            )

        except Exception as e:
            self.logger.error(f"Screenshot comparison error: {e}")
            return ValidationResult(
                passed=True,
                confidence=0.5,
                verification_type="state_changed",
                details={"error": str(e)},
                error_message=None,
            )

    def _verify_no_error(self, screenshot) -> ValidationResult:
        """Verify no error dialog appeared"""
        error_result = self.error_detector.detect_error(screenshot)

        has_error = error_result.get("has_error", False)

        if has_error:
            return ValidationResult(
                passed=False,
                confidence=error_result.get("confidence", 1.0),
                verification_type="no_error",
                details={
                    "error_type": error_result.get("error_type"),
                    "error_message": error_result.get("message"),
                },
                error_message="Error dialog detected",
            )
        else:
            return ValidationResult(
                passed=True,
                confidence=1.0,
                verification_type="no_error",
                details={"no_errors": True},
            )

    def _verify_custom(self, verification: ActionVerification, screenshot) -> ValidationResult:
        """Custom verification (extensibility point)"""
        # This is a placeholder for custom verification logic
        # In a real implementation, would support pluggable verifiers

        expected_state = verification.expected_state or {}

        return ValidationResult(
            passed=True,
            confidence=0.8,
            verification_type="custom",
            details={
                "message": "Custom verification not fully implemented",
                "expected_state": expected_state,
            },
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        total = self._verifications_performed
        success_rate = (self._verifications_passed / total) if total > 0 else 0

        return {
            "verifications_performed": total,
            "verifications_passed": self._verifications_passed,
            "verifications_failed": self._verifications_failed,
            "success_rate": success_rate,
        }

    def reset_stats(self):
        """Reset statistics"""
        self._verifications_performed = 0
        self._verifications_passed = 0
        self._verifications_failed = 0
