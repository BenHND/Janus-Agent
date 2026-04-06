"""
Screenshot backend abstraction layer
VISION-FOUNDATION-002: Fast and stable screenshot capture across platforms
"""

import platform
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from PIL import Image


class ScreenshotBackend(ABC):
    """Abstract base class for screenshot backends"""

    def __init__(self):
        """Initialize the backend"""
        self.name = "base"
        self._last_capture_time = 0.0
        self._scale_factor = 1.0

    @abstractmethod
    def capture_screen(self) -> Image.Image:
        """
        Capture the entire screen

        Returns:
            PIL Image of the screen
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get the size of the primary screen

        Returns:
            Tuple of (width, height)
        """
        pass

    def get_scale_factor(self) -> float:
        """
        Get the display scale factor (for high-DPI displays)

        Returns:
            Scale factor (1.0 for standard displays, 2.0 for Retina, etc.)
        """
        return self._scale_factor

    def get_last_capture_time(self) -> float:
        """
        Get the time taken for the last capture in seconds

        Returns:
            Time in seconds
        """
        return self._last_capture_time

    def _measure_capture(self, capture_func):
        """
        Measure the time taken for a capture operation

        Args:
            capture_func: Function that performs the capture

        Returns:
            Result of capture_func
        """
        start_time = time.time()
        result = capture_func()
        self._last_capture_time = time.time() - start_time
        return result


class MacOSQuartzBackend(ScreenshotBackend):
    """
    macOS screenshot backend using Quartz (CoreGraphics)
    Fast and reliable, handles Retina displays correctly
    """

    def __init__(self):
        super().__init__()
        self.name = "macos_quartz"
        self._quartz = None
        self._initialize()

    def _initialize(self):
        """Initialize Quartz framework"""
        try:
            # Import Quartz only on macOS
            import Quartz

            self._quartz = Quartz
            # Detect scale factor
            self._detect_scale_factor()
        except ImportError:
            raise RuntimeError(
                "Quartz framework not available. Install with: pip install pyobjc-framework-Quartz"
            )

    def _detect_scale_factor(self):
        """Detect the display scale factor for Retina displays"""
        try:
            # Get main display
            main_display = self._quartz.CGMainDisplayID()
            # Get mode
            mode = self._quartz.CGDisplayCopyDisplayMode(main_display)
            if mode:
                # Get pixel dimensions
                pixel_width = self._quartz.CGDisplayModeGetPixelWidth(mode)
                # Get logical dimensions
                logical_width = self._quartz.CGDisplayModeGetWidth(mode)
                if logical_width > 0:
                    self._scale_factor = pixel_width / logical_width
        except Exception:
            # Fallback to 1.0 if detection fails
            self._scale_factor = 1.0

    def capture_screen(self) -> Image.Image:
        """Capture the entire screen using Quartz"""

        def _capture():
            # Create screenshot using Quartz
            region = self._quartz.CGRectInfinite
            image_ref = self._quartz.CGWindowListCreateImage(
                region,
                self._quartz.kCGWindowListOptionOnScreenOnly,
                self._quartz.kCGNullWindowID,
                self._quartz.kCGWindowImageDefault,
            )

            if not image_ref:
                raise RuntimeError("Failed to capture screen with Quartz")

            # Convert CGImage to PIL Image
            width = self._quartz.CGImageGetWidth(image_ref)
            height = self._quartz.CGImageGetHeight(image_ref)
            bytes_per_row = self._quartz.CGImageGetBytesPerRow(image_ref)
            data_provider = self._quartz.CGImageGetDataProvider(image_ref)
            data = self._quartz.CGDataProviderCopyData(data_provider)

            # Create PIL Image from raw data
            image = Image.frombytes(
                "RGB", (width, height), data, "raw", "BGRX", bytes_per_row
            )

            return image

        return self._measure_capture(_capture)

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture a specific region using Quartz"""

        def _capture():
            # Adjust coordinates for scale factor
            scaled_x = int(x * self._scale_factor)
            scaled_y = int(y * self._scale_factor)
            scaled_width = int(width * self._scale_factor)
            scaled_height = int(height * self._scale_factor)

            # Create region rectangle
            region = self._quartz.CGRectMake(
                scaled_x, scaled_y, scaled_width, scaled_height
            )

            image_ref = self._quartz.CGWindowListCreateImage(
                region,
                self._quartz.kCGWindowListOptionOnScreenOnly,
                self._quartz.kCGNullWindowID,
                self._quartz.kCGWindowImageDefault,
            )

            if not image_ref:
                raise RuntimeError("Failed to capture region with Quartz")

            # Convert to PIL Image
            img_width = self._quartz.CGImageGetWidth(image_ref)
            img_height = self._quartz.CGImageGetHeight(image_ref)
            bytes_per_row = self._quartz.CGImageGetBytesPerRow(image_ref)
            data_provider = self._quartz.CGImageGetDataProvider(image_ref)
            data = self._quartz.CGDataProviderCopyData(data_provider)

            image = Image.frombytes(
                "RGB", (img_width, img_height), data, "raw", "BGRX", bytes_per_row
            )

            # Resize back to logical size if scale factor is not 1.0
            # The captured image is in physical pixels (img_width x img_height)
            # We resize it to the requested logical size (width x height)
            if self._scale_factor != 1.0:
                image = image.resize((width, height), Image.Resampling.LANCZOS)

            return image

        return self._measure_capture(_capture)

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size using Quartz"""
        main_display = self._quartz.CGMainDisplayID()
        width = self._quartz.CGDisplayPixelsWide(main_display)
        height = self._quartz.CGDisplayPixelsHigh(main_display)

        # Adjust for scale factor to get logical size
        if self._scale_factor != 1.0:
            width = int(width / self._scale_factor)
            height = int(height / self._scale_factor)

        return (width, height)


class MSSBackend(ScreenshotBackend):
    """
    Screenshot backend using mss library
    Fast cross-platform solution for Windows and Linux
    """

    def __init__(self):
        super().__init__()
        self.name = "mss"
        self._sct = None
        self._initialize()

    def _initialize(self):
        """Initialize mss"""
        try:
            import mss

            self._sct = mss.mss()
            # Detect scale factor (Windows DPI scaling)
            self._detect_scale_factor()
        except ImportError:
            raise RuntimeError("mss library not available. Install with: pip install mss")

    def _detect_scale_factor(self):
        """Detect display scale factor"""
        try:
            # Get primary monitor
            monitor = self._sct.monitors[1]  # 0 is all monitors combined
            # mss already handles DPI scaling on Windows
            # For now, assume 1.0 as mss returns logical pixels
            self._scale_factor = 1.0
        except Exception:
            self._scale_factor = 1.0

    def capture_screen(self) -> Image.Image:
        """Capture the entire screen using mss"""

        def _capture():
            # Capture primary monitor (index 1)
            monitor = self._sct.monitors[1]
            sct_img = self._sct.grab(monitor)

            # Convert to PIL Image
            image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return image

        return self._measure_capture(_capture)

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture a specific region using mss"""

        def _capture():
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = self._sct.grab(monitor)

            # Convert to PIL Image
            image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return image

        return self._measure_capture(_capture)

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size using mss"""
        monitor = self._sct.monitors[1]
        return (monitor["width"], monitor["height"])


class PyAutoGUIBackend(ScreenshotBackend):
    """
    Fallback screenshot backend using PyAutoGUI
    Cross-platform but slower and less reliable
    """

    def __init__(self):
        super().__init__()
        self.name = "pyautogui"
        self._initialize()

    def _initialize(self):
        """Initialize PyAutoGUI"""
        try:
            import pyautogui

            self._pyautogui = pyautogui
            # PyAutoGUI doesn't handle scale factors well
            self._scale_factor = 1.0
        except ImportError:
            raise RuntimeError(
                "pyautogui library not available. Install with: pip install pyautogui"
            )

    def capture_screen(self) -> Image.Image:
        """Capture the entire screen using PyAutoGUI"""

        def _capture():
            return self._pyautogui.screenshot()

        return self._measure_capture(_capture)

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture a specific region using PyAutoGUI"""

        def _capture():
            return self._pyautogui.screenshot(region=(x, y, width, height))

        return self._measure_capture(_capture)

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size using PyAutoGUI"""
        size = self._pyautogui.size()
        return (size[0], size[1])


def get_best_backend() -> ScreenshotBackend:
    """
    Get the best available screenshot backend for the current platform

    Returns:
        ScreenshotBackend instance

    Raises:
        RuntimeError: If no backend is available
    """
    system = platform.system()

    # Try platform-specific backends first
    if system == "Darwin":
        # macOS: Try Quartz first
        try:
            return MacOSQuartzBackend()
        except RuntimeError:
            pass

    # Windows and Linux: Try mss
    if system in ("Windows", "Linux"):
        try:
            return MSSBackend()
        except RuntimeError:
            pass

    # Fallback to PyAutoGUI
    try:
        return PyAutoGUIBackend()
    except RuntimeError:
        pass

    raise RuntimeError("No screenshot backend available. Please install mss or pyautogui.")
