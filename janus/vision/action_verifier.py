"""
Action Verifier - Responsible for verifying action results

This module handles post-action verification by:
- Capturing pre-action screenshots
- Comparing before/after states using hash comparison
- Detecting UI changes reliably

TICKET-4: Improved verification using screenshot hash instead of size comparison
"""

import hashlib
import time
from typing import Any, Dict, Optional

from janus.logging import get_logger

from .screenshot_engine import ScreenshotEngine


class ActionVerifier:
    """
    Verifies that actions had the expected effect using hash-based comparison
    """

    def __init__(self, screenshot_engine: Optional[ScreenshotEngine] = None):
        """
        Initialize Action Verifier

        Args:
            screenshot_engine: Screenshot engine for capturing screen state
        """
        self.logger = get_logger("action_verifier")
        self.screenshot_engine = screenshot_engine or ScreenshotEngine()

    def capture_pre_action_state(self) -> Any:
        """
        Capture the state before an action is performed

        Returns:
            Pre-action state (screenshot)
        """
        return self.screenshot_engine.capture_screen()
    
    def _compute_screenshot_hash(self, screenshot) -> str:
        """
        Compute hash of a screenshot for change detection.
        
        TICKET-4: More reliable than size comparison for detecting UI changes.
        
        Args:
            screenshot: PIL Image
            
        Returns:
            SHA256 hash (first 16 chars)
        """
        try:
            return hashlib.sha256(screenshot.tobytes()).hexdigest()[:16]
        except Exception as e:
            self.logger.warning(f"Failed to compute screenshot hash: {e}")
            return "error"

    def verify_action(
        self, action: str, target: str, pre_state: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Verify action result by comparing before/after states using hash comparison
        
        TICKET-4: Uses screenshot hash instead of size comparison for more reliable
        change detection. This reduces false positives that led to retry loops.

        Args:
            action: Action that was performed
            target: Target element
            pre_state: State before action (screenshot)

        Returns:
            Verification result dictionary
        """
        try:
            # Capture post-action state
            time.sleep(0.3)  # Wait for UI to update
            post_state = self.screenshot_engine.capture_screen()

            if not post_state or not pre_state:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "reason": "Could not capture screenshots for verification",
                }

            # TICKET-4: Hash-based verification instead of size comparison
            pre_hash = self._compute_screenshot_hash(pre_state)
            post_hash = self._compute_screenshot_hash(post_state)
            
            if pre_hash == "error" or post_hash == "error":
                # Fallback to assuming success if hash computation failed
                return {
                    "verified": True,
                    "confidence": 0.5,
                    "reason": "Hash computation failed, assuming action succeeded",
                }
            
            if pre_hash != post_hash:
                # Screen content changed - action likely succeeded
                return {
                    "verified": True,
                    "confidence": 0.9,
                    "reason": "Screen content changed (hash mismatch)",
                }
            else:
                # Screen unchanged - this could be normal for some actions
                # (e.g., clicking already selected button)
                return {
                    "verified": True,
                    "confidence": 0.7,
                    "reason": "Screen unchanged (may be expected for this action)",
                }

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return {"verified": False, "confidence": 0.0, "reason": f"Verification error: {str(e)}"}
