"""
Light Vision Engine - Lightweight post-action verification using Florence-2
TICKET-302: Clean implementation with Florence-2 only (no legacy code)
TICKET-P1-03: Added fast heuristic pre-check for screen change detection

Features:
- Florence-2 ultra-light vision model (< 1s on M4, < 4GB RAM)
- CPU-only mode for systems without GPU
- Fast verification (<1s target)
- Graceful fallback to heuristics when model unavailable
- Logging of all detections with timestamps and confidence
- TICKET-P1-03: Fast heuristic image comparison before heavy AI models
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# TICKET-P1-03: numpy is optional - fall back to pixel-by-pixel comparison if unavailable
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from PIL import Image

from janus.constants import IntentType

logger = logging.getLogger(__name__)

# TICKET-P1-03: Default timeout for vision verification (1.5s max as per spec)
DEFAULT_VISION_TIMEOUT_MS = 1500
# Threshold for significant screen change (percentage of pixels changed)
SCREEN_CHANGE_THRESHOLD = 0.01  # 1% of pixels changed = significant change
# Threshold for pixel intensity change (gray level difference to count as changed)
PIXEL_CHANGE_THRESHOLD = 10
# Maximum dimension for comparison (images are downsampled for speed)
MAX_COMPARISON_DIMENSION = 400


class LightVisionEngine:
    """
    Lightweight vision engine using Florence-2 for post-action verification.
    
    TICKET-302: Uses only Florence-2, no legacy BLIP-2/CLIP code.
    
    Features:
    - Florence-2 ultra-light model (microsoft/Florence-2-base)
    - CPU-only inference mode
    - Fast verification (<1s)
    - Graceful fallback to heuristics
    - Detection logging with timestamps
    """

    def __init__(
        self,
        enable_ai_models: bool = True,
        force_cpu: bool = False,
        log_detections: bool = True,
        log_path: Optional[str] = None,
        lazy_load: bool = False,
    ):
        """
        Initialize light vision engine with Florence-2.

        Args:
            enable_ai_models: Try to load Florence-2 model
            force_cpu: Force CPU inference even if GPU available
            log_detections: Log all detections to file
            log_path: Path to detection log file (default: logs/vision_detections.jsonl)
            lazy_load: If True, models are not loaded immediately
        """
        self.enable_ai_models = enable_ai_models
        self.force_cpu = force_cpu
        self.log_detections = log_detections
        self._lazy_load = lazy_load

        # Setup detection logging
        if log_path:
            self.log_path = Path(log_path)
        else:
            self.log_path = Path("logs") / "vision_detections.jsonl"

        if self.log_detections:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Florence-2 engine (lazy-loaded)
        self._vision_engine = None
        self._models_available = False
        self._device = "cpu" if force_cpu else "auto"
        self._loading = False

        # Performance metrics
        self._total_verifications = 0
        self._total_time = 0.0
        self._avg_time = 0.0
        
        # TICKET-P1-03: Store last screenshot for change detection
        self._last_screenshot: Optional[Image.Image] = None

        # Initialize Florence-2 if enabled and not lazy loading
        if self.enable_ai_models and not lazy_load:
            self._init_models()

    # ==================== TICKET-P1-03: Fast Heuristic Methods ====================
    
    def compare_screenshots(
        self,
        before: Image.Image,
        after: Image.Image,
        threshold: float = SCREEN_CHANGE_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Fast heuristic comparison of two screenshots to detect screen changes.
        
        TICKET-P1-03: This is the core optimization - a fast pixel-based comparison
        that runs before heavy AI models to quickly detect if a click had any effect.
        
        Args:
            before: Screenshot taken before the action
            after: Screenshot taken after the action
            threshold: Percentage of pixels that must change to be considered significant
                      (default: 1% of pixels)
        
        Returns:
            Dict with:
            - changed: bool - True if screen changed significantly
            - change_ratio: float - Percentage of pixels that changed (0.0 to 1.0)
            - duration_ms: int - Time taken for comparison
            - method: str - "heuristic_pixel_comparison"
        """
        start_time = time.time()
        
        try:
            # Resize to same dimensions if needed (fast resize)
            if before.size != after.size:
                # Use the smaller dimensions for comparison (faster)
                target_size = (
                    min(before.width, after.width),
                    min(before.height, after.height)
                )
                before = before.resize(target_size, Image.Resampling.NEAREST)
                after = after.resize(target_size, Image.Resampling.NEAREST)
            
            # Downsample for faster comparison
            if before.width > MAX_COMPARISON_DIMENSION or before.height > MAX_COMPARISON_DIMENSION:
                scale = MAX_COMPARISON_DIMENSION / max(before.width, before.height)
                new_size = (int(before.width * scale), int(before.height * scale))
                before = before.resize(new_size, Image.Resampling.NEAREST)
                after = after.resize(new_size, Image.Resampling.NEAREST)
            
            # Convert to grayscale for faster comparison
            before_gray = before.convert("L")
            after_gray = after.convert("L")
            
            if NUMPY_AVAILABLE:
                # Fast path with numpy
                before_arr = np.array(before_gray, dtype=np.int16)
                after_arr = np.array(after_gray, dtype=np.int16)
                
                # Calculate pixel-wise absolute difference
                diff = np.abs(before_arr - after_arr)
                
                # Count pixels with significant change
                changed_pixels = np.sum(diff > PIXEL_CHANGE_THRESHOLD)
                total_pixels = before_arr.size
            else:
                # Fallback: pixel-by-pixel comparison (slower but works without numpy)
                changed_pixels = 0
                total_pixels = before_gray.width * before_gray.height
                for y in range(before_gray.height):
                    for x in range(before_gray.width):
                        diff = abs(before_gray.getpixel((x, y)) - after_gray.getpixel((x, y)))
                        if diff > PIXEL_CHANGE_THRESHOLD:
                            changed_pixels += 1
            
            change_ratio = changed_pixels / total_pixels
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "changed": change_ratio >= threshold,
                "change_ratio": round(change_ratio, 4),
                "duration_ms": duration_ms,
                "method": "heuristic_pixel_comparison",
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Screenshot comparison failed: {e}")
            return {
                "changed": True,  # Assume changed on error (conservative)
                "change_ratio": 0.0,
                "duration_ms": duration_ms,
                "method": "heuristic_error",
                "error": str(e),
            }
    
    def check_pixel_changed(
        self,
        before: Image.Image,
        after: Image.Image,
        x: int,
        y: int,
        tolerance: int = 20,
    ) -> Dict[str, Any]:
        """
        Check if a specific pixel has changed between two screenshots.
        
        TICKET-P1-03: Ultra-fast single-pixel check for targeted verification.
        Useful for checking if a button click had any effect at click coordinates.
        
        Args:
            before: Screenshot before action
            after: Screenshot after action
            x: X coordinate to check
            y: Y coordinate to check
            tolerance: Color difference threshold (0-255)
        
        Returns:
            Dict with:
            - changed: bool
            - color_diff: int - Maximum color channel difference
            - before_color: tuple - RGB color before
            - after_color: tuple - RGB color after
            - duration_ms: int
        """
        start_time = time.time()
        
        try:
            # Ensure coordinates are valid
            if not (0 <= x < before.width and 0 <= y < before.height):
                return {
                    "changed": True,  # Assume changed if coordinates invalid
                    "color_diff": 0,
                    "error": "Coordinates out of bounds",
                    "duration_ms": int((time.time() - start_time) * 1000),
                }
            
            if not (0 <= x < after.width and 0 <= y < after.height):
                return {
                    "changed": True,  # Assume changed if coordinates invalid
                    "color_diff": 0,
                    "error": "Coordinates out of bounds (after)",
                    "duration_ms": int((time.time() - start_time) * 1000),
                }
            
            # Get pixel colors
            before_color = before.getpixel((x, y))
            after_color = after.getpixel((x, y))
            
            # Handle grayscale images
            if isinstance(before_color, int):
                before_color = (before_color, before_color, before_color)
            if isinstance(after_color, int):
                after_color = (after_color, after_color, after_color)
            
            # Calculate max color difference across channels
            color_diff = max(
                abs(before_color[i] - after_color[i])
                for i in range(min(len(before_color), len(after_color), 3))
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "changed": color_diff > tolerance,
                "color_diff": color_diff,
                "before_color": before_color[:3] if len(before_color) >= 3 else before_color,
                "after_color": after_color[:3] if len(after_color) >= 3 else after_color,
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "changed": True,  # Assume changed on error
                "color_diff": 0,
                "error": str(e),
                "duration_ms": duration_ms,
            }
    
    def detect_action_effect(
        self,
        before: Image.Image,
        after: Image.Image,
        action: Dict[str, Any],
        timeout_ms: int = DEFAULT_VISION_TIMEOUT_MS,
    ) -> Dict[str, Any]:
        """
        Detect if an action had any visible effect on the screen.
        
        TICKET-P1-03: Main method for fast action verification.
        Uses fast heuristic comparison first, then AI verification only if needed.
        
        Args:
            before: Screenshot before the action
            after: Screenshot after the action
            action: Action dict with type and parameters
            timeout_ms: Maximum verification time (default: 1500ms / 1.5s)
        
        Returns:
            Dict with:
            - action_had_effect: bool - True if screen changed
            - verified: bool - True if action likely succeeded
            - confidence: float (0-1)
            - method: str
            - duration_ms: int
            - reason: str
        """
        start_time = time.time()
        action_type = action.get("action", action.get("type", "unknown"))
        
        # Step 1: Fast heuristic comparison
        comparison = self.compare_screenshots(before, after)
        
        if not comparison["changed"]:
            # Screen didn't change - action likely had no effect
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "action_had_effect": False,
                "verified": False,
                "confidence": 0.9,  # High confidence that nothing happened
                "method": "heuristic_no_change",
                "duration_ms": duration_ms,
                "reason": f"Screen unchanged after {action_type} (change_ratio={comparison['change_ratio']})",
                "change_ratio": comparison["change_ratio"],
            }
        
        # Step 2: If screen changed, check time budget
        elapsed_ms = (time.time() - start_time) * 1000
        remaining_ms = timeout_ms - elapsed_ms
        
        if remaining_ms < 100:
            # Not enough time for AI verification - use heuristic result
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "action_had_effect": True,
                "verified": True,
                "confidence": 0.6,
                "method": "heuristic_change_detected",
                "duration_ms": duration_ms,
                "reason": f"Screen changed after {action_type} (change_ratio={comparison['change_ratio']})",
                "change_ratio": comparison["change_ratio"],
            }
        
        # Step 3: If AI models available and we have time, do deeper verification
        if self._models_available and self._vision_engine:
            try:
                ai_result = self._verify_with_florence(
                    after, action, start_time, int(remaining_ms)
                )
                duration_ms = int((time.time() - start_time) * 1000)
                ai_result["action_had_effect"] = True
                ai_result["duration_ms"] = duration_ms
                ai_result["change_ratio"] = comparison["change_ratio"]
                return ai_result
            except Exception as e:
                logger.debug(f"AI verification failed, using heuristic: {e}")
        
        # Fallback: screen changed, assume success
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "action_had_effect": True,
            "verified": True,
            "confidence": 0.7,
            "method": "heuristic_with_change",
            "duration_ms": duration_ms,
            "reason": f"Screen changed after {action_type}",
            "change_ratio": comparison["change_ratio"],
        }
    
    def store_screenshot(self, screenshot: Image.Image) -> None:
        """
        Store a screenshot for later comparison.
        
        TICKET-P1-03: Call this before executing an action to enable
        automatic before/after comparison.
        
        Args:
            screenshot: Screenshot to store
        """
        self._last_screenshot = screenshot.copy()
    
    def get_stored_screenshot(self) -> Optional[Image.Image]:
        """
        Get the stored screenshot.
        
        Returns:
            The stored screenshot or None if none stored
        """
        return self._last_screenshot
    
    # ==================== End TICKET-P1-03 Heuristic Methods ====================

    def _init_models(self):
        """Initialize OmniParser vision engine (replaces Florence-2)."""
        if self._loading or self._models_available:
            return
            
        self._loading = True
        try:
            from janus.vision.omniparser_adapter import OmniParserVisionEngine
            
            logger.info("Initializing OmniParser vision engine...")
            start_time = time.time()
            
            self._vision_engine = OmniParserVisionEngine(
                device=self._device,
                enable_cache=True,
                cache_size=20,
                lazy_load=False,
            )
            
            if self._vision_engine.is_available():
                init_time = time.time() - start_time
                self._models_available = True
                logger.info(f"✓ OmniParser vision engine initialized in {init_time:.2f}s")
            else:
                logger.warning("OmniParser failed to load, using heuristic fallback")
                self._vision_engine = None
                    
        except ImportError as e:
            logger.warning(f"OmniParser not available: {e}, using heuristic fallback")
            self._models_available = False
        except Exception as e:
            logger.warning(f"Failed to initialize OmniParser: {e}, using heuristic fallback")
            self._models_available = False
        finally:
            self._loading = False

    async def preload_models_async(self):
        """
        Asynchronously preload OmniParser model in the background.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        import asyncio
        
        if not self.enable_ai_models:
            logger.debug("AI models disabled, skipping preload")
            return False
            
        if self._models_available:
            logger.debug("OmniParser already loaded")
            return True
            
        if self._loading:
            logger.debug("OmniParser is already being loaded")
            while self._loading:
                await asyncio.sleep(0.1)
            return self._models_available
        
        logger.info("Starting async preload of OmniParser...")
        start_time = time.time()
        
        try:
            from janus.vision.omniparser_adapter import OmniParserVisionEngine
            
            self._vision_engine = OmniParserVisionEngine(
                device=self._device,
                enable_cache=True,
                cache_size=20,
                lazy_load=True,
            )
            
            success = await self._vision_engine.preload_models_async()
            
            if success:
                self._models_available = self._vision_engine.is_available()
                duration = time.time() - start_time
                logger.info(f"✓ Florence-2 preloaded in {duration:.2f}s")
                return True
            else:
                logger.warning("Florence-2 preload failed")
                self._vision_engine = None
                return False
                
        except ImportError as e:
            logger.warning(f"Florence-2 not available: {e}")
            self._models_available = False
            return False
        except Exception as e:
            logger.error(f"Failed to preload Florence-2: {e}")
            self._models_available = False
            return False

    def verify_action_result(
        self, screenshot: Image.Image, action: Dict[str, Any], timeout_ms: int = DEFAULT_VISION_TIMEOUT_MS
    ) -> Dict[str, Any]:
        """
        Verify action result using Florence-2 vision (target: <1.5s).
        
        TICKET-P1-03: Updated default timeout to 1.5s (1500ms) as per spec.

        Args:
            screenshot: PIL Image of screen after action
            action: Action dictionary with type and parameters
            timeout_ms: Maximum time for verification (default: 1500ms / 1.5s)

        Returns:
            Verification result with:
            - verified: bool
            - confidence: float (0-1)
            - method: str (florence2/heuristic/fallback)
            - duration_ms: int
            - reason: str
        """
        start_time = time.time()
        action_type = action.get("action", action.get("type", "unknown"))

        try:
            # Load model if not yet loaded
            if self.enable_ai_models and not self._models_available and not self._loading:
                logger.warning("Florence-2 not preloaded, loading synchronously")
                self._init_models()

            # Use Florence-2 if available, otherwise heuristics
            if self._models_available and self._vision_engine:
                result = self._verify_with_florence(screenshot, action, start_time, timeout_ms)
            else:
                result = self._verify_with_heuristics(screenshot, action)

            # Calculate final duration
            duration_ms = int((time.time() - start_time) * 1000)
            result["duration_ms"] = duration_ms

            # Update performance metrics
            self._update_metrics(duration_ms)

            # Log detection if enabled
            if self.log_detections:
                self._log_detection(action, result)

            # Warn if verification took too long
            if duration_ms > timeout_ms:
                logger.warning(f"Vision verification exceeded target: {duration_ms}ms > {timeout_ms}ms")

            return result

        except TimeoutError as e:
            logger.warning(str(e))
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "verified": True,
                "confidence": 0.3,
                "method": "timeout",
                "duration_ms": duration_ms,
                "reason": str(e),
            }

        except Exception as e:
            logger.error(f"Vision verification error: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "verified": True,
                "confidence": 0.0,
                "method": "error",
                "duration_ms": duration_ms,
                "reason": f"Verification error: {str(e)}",
            }

    def _verify_with_florence(
        self, screenshot: Image.Image, action: Dict[str, Any], start_time: float, timeout_ms: int
    ) -> Dict[str, Any]:
        """Verify using Florence-2 vision model."""
        action_type = action.get("action", action.get("type", "unknown"))

        # Check for visual errors first (fast check)
        error_result = self._vision_engine.detect_errors(screenshot)

        if error_result.get("has_error", False):
            return {
                "verified": False,
                "confidence": error_result.get("confidence", 0.8),
                "method": "florence2_error_detection",
                "reason": f"Error detected: {error_result.get('error_type', 'unknown')}",
                "error_details": error_result,
            }

        # Action-specific verification
        if action_type in ["open_url", "navigate_url"]:
            context = {"url": action.get("url"), "app_name": "Chrome"}
            verification = self._vision_engine.verify_action_result(
                screenshot, action_type, context
            )
            return verification

        elif action_type in ["open_application", IntentType.OPEN_APP.value]:
            app_name = action.get("app_name", action.get("name", ""))
            desc_result = self._vision_engine.describe(screenshot)
            description = desc_result.get("description", "").lower()

            is_visible = app_name.lower() in description

            return {
                "verified": is_visible,
                "confidence": desc_result.get("confidence", 0.5),
                "method": "florence2_description",
                "reason": f"App {'visible' if is_visible else 'not visible'} in screen: {description[:60]}",
            }

        else:
            # Generic verification - just check for errors
            return {
                "verified": True,
                "confidence": 0.6,
                "method": "florence2_generic",
                "reason": "No errors detected, action assumed successful",
            }

    def _verify_with_heuristics(
        self, screenshot: Image.Image, action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback heuristic verification when Florence-2 unavailable."""
        action_type = action.get("action", action.get("type", "unknown"))

        if action_type in [
            "open_url",
            "navigate_url",
            "open_application",
            IntentType.OPEN_APP.value,
        ]:
            return {
                "verified": True,
                "confidence": 0.5,
                "method": "heuristic",
                "reason": "Cannot verify without Florence-2, assuming success",
            }

        else:
            return {
                "verified": True,
                "confidence": 0.4,
                "method": "heuristic",
                "reason": "Basic action verification, Florence-2 not available",
            }

    def _log_detection(self, action: Dict[str, Any], result: Dict[str, Any]):
        """Log detection to file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action.get("action", action.get("type", "unknown")),
                "action_params": {k: v for k, v in action.items() if k not in ["action", "type"]},
                "verified": result.get("verified", False),
                "confidence": result.get("confidence", 0.0),
                "method": result.get("method", "unknown"),
                "duration_ms": result.get("duration_ms", 0),
                "reason": result.get("reason", ""),
            }

            with open(self.log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.debug(f"Failed to log detection: {e}")

    def _update_metrics(self, duration_ms: int):
        """Update performance metrics."""
        self._total_verifications += 1
        self._total_time += duration_ms
        self._avg_time = self._total_time / self._total_verifications

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "models_available": self._models_available,
            "device": self._device,
            "total_verifications": self._total_verifications,
            "avg_time_ms": round(self._avg_time, 2),
            "total_time_ms": round(self._total_time, 2),
            "log_path": str(self.log_path) if self.log_detections else None,
            "engine": "florence2",
        }

    def is_available(self) -> bool:
        """Check if Florence-2 model is available."""
        return self._models_available
