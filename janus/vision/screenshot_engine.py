"""
Screenshot engine for capturing screen or window content
Ticket 3.1: Screenshot engine
Ticket 9.1: Screenshot Latency Optimization
Ticket PRIV-001: PII Visual Filter (Data Leak Prevention)
VISION-FOUNDATION-002: Fast and stable screenshot backend
"""

import io
import logging
import platform
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from janus.vision.screenshot_backend import ScreenshotBackend, get_best_backend

logger = logging.getLogger(__name__)


class ScreenshotEngine:
    """
    Screenshot engine for capturing screen, window, or region
    Supports macOS, Windows, and Linux
    Enhanced with performance optimization (Phase 9.1)
    VISION-FOUNDATION-002: Fast backend with downsampling
    """

    def __init__(
        self,
        optimize_quality: bool = True,
        enable_pii_masking: bool = False,
        backend: Optional[ScreenshotBackend] = None,
        max_width: Optional[int] = 1280,
    ):
        """
        Initialize screenshot engine

        Args:
            optimize_quality: Trade quality for speed by using optimized settings
            enable_pii_masking: Enable PII masking for saved screenshots
            backend: Custom screenshot backend (None for auto-detection)
            max_width: Maximum width for downsampling (None to disable)
        """
        self.is_mac = platform.system() == "Darwin"
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.optimize_quality = optimize_quality
        self.enable_pii_masking = enable_pii_masking
        self.max_width = max_width
        self._performance_metrics = {"total_captures": 0, "total_time": 0.0}
        self._metrics_lock = threading.Lock()

        # Initialize screenshot backend
        self._backend = backend if backend is not None else get_best_backend()
        logger.info(f"Screenshot backend initialized: {self._backend.name}")

        # Lazy initialization of PII masker and OCR engine
        self._pii_masker = None
        self._ocr_engine = None

    def capture_screen(self) -> Image.Image:
        """
        Capture the entire screen with optional downsampling

        Returns:
            PIL Image of the screen
        """
        start_time = time.time()
        try:
            # Capture using backend
            screenshot = self._backend.capture_screen()

            # Apply downsampling if configured
            screenshot = self._apply_downsampling(screenshot)

            # Log metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_capture_metrics(elapsed_ms, screenshot)
            self._update_metrics(elapsed_ms / 1000)

            return screenshot
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_metrics(elapsed_ms / 1000)
            raise RuntimeError(f"Failed to capture screen: {str(e)}")

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """
        Capture a specific region of the screen

        Args:
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner
            width: Width of region
            height: Height of region

        Returns:
            PIL Image of the region
        """
        try:
            screenshot = self._backend.capture_region(x, y, width, height)
            return screenshot
        except Exception as e:
            raise RuntimeError(f"Failed to capture region: {str(e)}")

    def capture_window(
        self, window_name: Optional[str] = None
    ) -> Tuple[Image.Image, Dict[str, int]]:
        """
        Capture a specific window

        Args:
            window_name: Name of the window to capture (None for active window)

        Returns:
            Tuple of (PIL Image, window_bounds dict with x, y, width, height)
        """
        if self.is_mac:
            return self._capture_window_mac(window_name)
        elif self.is_windows:
            return self._capture_window_windows(window_name)
        else:
            # Fallback to full screen for Linux
            return self.capture_screen(), self._get_screen_size()

    def _capture_window_mac(
        self, window_name: Optional[str] = None
    ) -> Tuple[Image.Image, Dict[str, int]]:
        """
        Capture window on macOS using AppleScript

        Args:
            window_name: Application name or window title

        Returns:
            Tuple of (PIL Image, window_bounds)
        """
        try:
            if window_name:
                # Get window bounds using AppleScript
                script = f"""
                tell application "System Events"
                    tell process "{window_name}"
                        get position of window 1
                        get size of window 1
                    end tell
                end tell
                """
                result = subprocess.run(
                    ["osascript", "-e", script], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    # Parse position and size from AppleScript output
                    output = result.stdout.strip()
                    # Output format: "x, y\nwidth, height"
                    lines = output.split("\n")
                    if len(lines) >= 2:
                        pos = lines[0].split(", ")
                        size = lines[1].split(", ")

                        x = int(pos[0])
                        y = int(pos[1])
                        width = int(size[0])
                        height = int(size[1])

                        screenshot = self.capture_region(x, y, width, height)
                        bounds = {"x": x, "y": y, "width": width, "height": height}
                        return screenshot, bounds

            # Fallback: capture full screen
            screenshot = self.capture_screen()
            bounds = self._get_screen_size()
            return screenshot, bounds

        except Exception as e:
            # Fallback to full screen capture
            screenshot = self.capture_screen()
            bounds = self._get_screen_size()
            return screenshot, bounds

    def _capture_window_windows(
        self, window_name: Optional[str] = None
    ) -> Tuple[Image.Image, Dict[str, int]]:
        """
        Capture window on Windows

        Args:
            window_name: Window title

        Returns:
            Tuple of (PIL Image, window_bounds)
        """
        # For Windows, we'll use pyautogui's screenshot for now
        # A more sophisticated implementation could use win32gui
        screenshot = self.capture_screen()
        bounds = self._get_screen_size()
        return screenshot, bounds

    def _get_screen_size(self) -> Dict[str, int]:
        """
        Get the size of the primary screen

        Returns:
            Dict with x, y, width, height
        """
        width, height = self._backend.get_screen_size()
        return {"x": 0, "y": 0, "width": width, "height": height}

    def save_screenshot(
        self,
        image: Image.Image,
        file_path: str,
        mask_pii: Optional[bool] = None,
        ocr_results: Optional[List] = None,
    ) -> None:
        """
        Save a screenshot to disk with optional PII masking

        Args:
            image: PIL Image to save
            file_path: Path to save the image
            mask_pii: Override PII masking setting (None uses instance default)
            ocr_results: Optional pre-computed OCR results for PII detection.
                        If not provided and masking is enabled, OCR will be performed.
        """
        try:
            # Determine if we should mask PII
            should_mask = mask_pii if mask_pii is not None else self.enable_pii_masking

            if should_mask:
                # Apply PII masking before saving
                image = self._apply_pii_masking(image, ocr_results)

            image.save(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to save screenshot: {str(e)}")

    def get_screenshot_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """
        Get screenshot as bytes

        Args:
            image: PIL Image
            format: Image format (PNG, JPEG, etc.)

        Returns:
            Image bytes
        """
        try:
            buffer = io.BytesIO()
            # Optimize for speed if enabled
            if self.optimize_quality and format.upper() == "PNG":
                image.save(buffer, format=format, optimize=False, compress_level=1)
            elif self.optimize_quality and format.upper() in ["JPEG", "JPG"]:
                image.save(buffer, format=format, quality=85, optimize=False)
            else:
                image.save(buffer, format=format)
            return buffer.getvalue()
        except Exception as e:
            raise RuntimeError(f"Failed to convert screenshot to bytes: {str(e)}")

    def _update_metrics(self, elapsed_time: float):
        """
        Update performance metrics (Phase 9.1)

        Args:
            elapsed_time: Time taken for the capture
        """
        with self._metrics_lock:
            self._performance_metrics["total_captures"] += 1
            self._performance_metrics["total_time"] += elapsed_time

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get screenshot performance metrics (Phase 9.1)

        Returns:
            Dictionary with performance statistics
        """
        with self._metrics_lock:
            metrics = self._performance_metrics.copy()
            if metrics["total_captures"] > 0:
                metrics["average_time"] = metrics["total_time"] / metrics["total_captures"]
            else:
                metrics["average_time"] = 0.0
            return metrics

    def reset_metrics(self):
        """Reset performance metrics (Phase 9.1)"""
        with self._metrics_lock:
            self._performance_metrics = {"total_captures": 0, "total_time": 0.0}

    def _get_pii_masker(self):
        """
        Lazy initialization of PII masker (PRIV-001)

        Returns:
            PIIMasker instance
        """
        if self._pii_masker is None:
            from janus.vision.pii_masker import PIIMasker

            self._pii_masker = PIIMasker(blur_radius=15)
        return self._pii_masker

    def _get_ocr_engine(self):
        """
        Lazy initialization of OCR engine (PRIV-001)

        Returns:
            OCREngine instance
        """
        if self._ocr_engine is None:
            from janus.vision.native_ocr_adapter import NativeOCRAdapter

            self._ocr_engine = NativeOCRAdapter(backend="auto")
        return self._ocr_engine

    def _apply_pii_masking(
        self, image: Image.Image, ocr_results: Optional[List] = None
    ) -> Image.Image:
        """
        Apply PII masking to an image (PRIV-001)

        Args:
            image: PIL Image to mask
            ocr_results: Optional pre-computed OCR results

        Returns:
            Masked PIL Image
        """
        masker = self._get_pii_masker()

        # If no OCR results provided, perform OCR
        if ocr_results is None:
            ocr_engine = self._get_ocr_engine()
            ocr_results = ocr_engine.get_all_text_with_boxes(image)

        # Apply masking
        return masker.mask_pii_in_image(image, ocr_results)

    def _apply_downsampling(self, image: Image.Image) -> Image.Image:
        """
        Apply downsampling to reduce image size (VISION-FOUNDATION-002)

        Args:
            image: PIL Image to downsample

        Returns:
            Downsampled PIL Image
        """
        if self.max_width is None:
            return image

        width, height = image.size
        if width <= self.max_width:
            return image

        # Calculate new dimensions maintaining aspect ratio
        ratio = self.max_width / width
        new_width = self.max_width
        new_height = int(height * ratio)

        # Resize using high-quality resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _log_capture_metrics(self, elapsed_ms: float, image: Image.Image):
        """
        Log capture metrics for monitoring (VISION-FOUNDATION-002)

        Args:
            elapsed_ms: Time taken for capture in milliseconds
            image: Captured image
        """
        width, height = image.size
        scale_factor = self._backend.get_scale_factor()

        logger.debug(
            f"Screenshot captured: {elapsed_ms:.1f}ms, "
            f"size={width}x{height}, "
            f"scale_factor={scale_factor:.2f}, "
            f"backend={self._backend.name}"
        )

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the current screenshot backend

        Returns:
            Dictionary with backend details
        """
        return {
            "name": self._backend.name,
            "scale_factor": self._backend.get_scale_factor(),
            "last_capture_time_ms": self._backend.get_last_capture_time() * 1000,
        }
