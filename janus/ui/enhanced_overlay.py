"""
Enhanced Action Overlay - Visual feedback with element coordinates and highlights
Ticket 10.1: Overlay visuel programme showing actions, coordinates, and highlights
Ticket 10.3: Optimized rendering to reduce CPU/GPU lag
TICKET-FEAT-003: Mini screenshot overlay for visual feedback
"""

import logging
import queue
import threading
import time
import tkinter as tk
from enum import Enum
from tkinter import ttk
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class OverlayStatus(Enum):
    """Status types for overlay display"""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class EnhancedOverlay:
    """
    Enhanced transparent overlay window with:
    - Action status feedback
    - Element coordinate display
    - Visual element highlighting
    - Mini screenshot preview overlay
    - Optimized rendering for reduced CPU/GPU usage
    """

    def __init__(
        self,
        position: str = "top-right",
        duration: int = 3000,
        show_coordinates: bool = True,
        highlight_color: str = "#FF0000",
        highlight_width: int = 3,
        enable_rendering_optimization: bool = True,
        screenshot_max_size: int = 200,
        screenshot_position: str = "bottom-right",
    ):
        """
        Initialize enhanced overlay

        Args:
            position: Position on screen ('top-right', 'top-left', 'bottom-right', 'bottom-left')
            duration: How long to show success/error messages in milliseconds
            show_coordinates: Whether to show element coordinates
            highlight_color: Color for element highlighting (hex)
            highlight_width: Width of highlight border
            enable_rendering_optimization: Enable rendering optimizations
            screenshot_max_size: Maximum size for screenshot preview (pixels)
            screenshot_position: Position for screenshot overlay
        """
        self.position = position
        self.duration = duration
        self.show_coordinates = show_coordinates
        self.highlight_color = highlight_color
        self.highlight_width = highlight_width
        self.enable_rendering_optimization = enable_rendering_optimization
        self.screenshot_max_size = screenshot_max_size
        self.screenshot_position = screenshot_position

        # Windows
        self.info_window: Optional[tk.Tk] = None
        self.highlight_window: Optional[tk.Toplevel] = None
        self.screenshot_window: Optional[tk.Toplevel] = None

        # State
        self.message_queue = queue.Queue()
        self.current_message: Optional[str] = None
        self.current_coordinates: Optional[Dict[str, int]] = None
        self.is_showing = False
        self._thread: Optional[threading.Thread] = None
        self._last_update_time = 0
        self._update_throttle_ms = 50  # Minimum time between updates (optimization)

        # Status colors
        self.colors = {
            OverlayStatus.IN_PROGRESS: "#2196F3",  # Blue
            OverlayStatus.SUCCESS: "#4CAF50",  # Green
            OverlayStatus.ERROR: "#F44336",  # Red
            OverlayStatus.WARNING: "#FF9800",  # Orange
        }

    def _create_info_window(self):
        """Create the info overlay window"""
        self.info_window = tk.Tk()
        self.info_window.withdraw()

        # Configure window
        self.info_window.title("Janus")
        self.info_window.overrideredirect(True)
        self.info_window.attributes("-topmost", True)

        # Set transparency
        try:
            self.info_window.attributes("-alpha", 0.9)
        except tk.TclError:
            pass

        # Create main frame
        self.frame = ttk.Frame(self.info_window, padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Status indicator (colored circle)
        self.status_canvas = tk.Canvas(
            self.frame, width=20, height=20, bg="white", highlightthickness=0
        )
        self.status_canvas.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.status_indicator = self.status_canvas.create_oval(
            2, 2, 18, 18, fill=self.colors[OverlayStatus.IN_PROGRESS], outline=""
        )

        # Message label
        self.label = ttk.Label(self.frame, text="", font=("Arial", 11), wraplength=300)
        self.label.grid(row=0, column=1, sticky="w")

        # Coordinates label (initially hidden)
        self.coords_label = ttk.Label(self.frame, text="", font=("Courier", 9), foreground="gray")
        self.coords_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.coords_label.grid_remove()  # Hide initially

        # Position window
        self._position_info_window()

    def _position_info_window(self):
        """Position the info window based on configured position"""
        if not self.info_window:
            return

        self.info_window.update_idletasks()
        screen_width = self.info_window.winfo_screenwidth()
        screen_height = self.info_window.winfo_screenheight()
        window_width = self.info_window.winfo_width()
        window_height = self.info_window.winfo_height()

        # Calculate position
        if self.position == "top-right":
            x = screen_width - window_width - 20
            y = 20
        elif self.position == "top-left":
            x = 20
            y = 20
        elif self.position == "bottom-right":
            x = screen_width - window_width - 20
            y = screen_height - window_height - 60
        elif self.position == "bottom-left":
            x = 20
            y = screen_height - window_height - 60
        else:
            x = screen_width - window_width - 20
            y = 20

        self.info_window.geometry(f"+{x}+{y}")

    def _should_throttle_update(self) -> bool:
        """Check if update should be throttled (optimization)"""
        if not self.enable_rendering_optimization:
            return False

        current_time = time.time() * 1000  # Convert to ms
        if current_time - self._last_update_time < self._update_throttle_ms:
            return True

        self._last_update_time = current_time
        return False

    def _update_display(
        self, message: str, status: OverlayStatus, coordinates: Optional[Dict[str, int]] = None
    ):
        """Update the overlay display"""
        # Apply throttling if enabled
        if self._should_throttle_update():
            return

        if not self.info_window:
            self._create_info_window()

        # Update status indicator color
        self.status_canvas.itemconfig(self.status_indicator, fill=self.colors[status])

        # Update message
        self.label.config(text=message)

        # Update coordinates if provided and enabled
        if coordinates and self.show_coordinates:
            coord_text = self._format_coordinates(coordinates)
            self.coords_label.config(text=coord_text)
            self.coords_label.grid()
            self.current_coordinates = coordinates
        else:
            self.coords_label.grid_remove()
            self.current_coordinates = None

        # Reposition in case window size changed
        self.info_window.update_idletasks()
        self._position_info_window()

        # Show window
        self.info_window.deiconify()
        self.is_showing = True

    def _format_coordinates(self, coordinates: Dict[str, int]) -> str:
        """Format coordinates for display"""
        parts = []
        if "x" in coordinates and "y" in coordinates:
            parts.append(f"Position: ({coordinates['x']}, {coordinates['y']})")
        if "center_x" in coordinates and "center_y" in coordinates:
            parts.append(f"Center: ({coordinates['center_x']}, {coordinates['center_y']})")
        if "width" in coordinates and "height" in coordinates:
            parts.append(f"Size: {coordinates['width']}x{coordinates['height']}")
        return " | ".join(parts) if parts else ""

    def show_highlight(
        self, x: int, y: int, width: int, height: int, duration: Optional[int] = None
    ):
        """
        Show visual highlight rectangle around an element

        Args:
            x: X coordinate of element
            y: Y coordinate of element
            width: Width of element
            height: Height of element
            duration: How long to show highlight (ms), None for permanent
        """

        def create_highlight():
            if not self.info_window:
                return

            # Create or update highlight window
            if self.highlight_window is None or not self.highlight_window.winfo_exists():
                self.highlight_window = tk.Toplevel(self.info_window)
                self.highlight_window.overrideredirect(True)
                self.highlight_window.attributes("-topmost", True)

                # Make transparent background
                try:
                    self.highlight_window.attributes("-alpha", 0.7)
                    self.highlight_window.attributes("-transparentcolor", "white")
                except tk.TclError:
                    pass

                # Create canvas for drawing
                self.highlight_canvas = tk.Canvas(
                    self.highlight_window, bg="white", highlightthickness=0
                )
                self.highlight_canvas.pack(fill=tk.BOTH, expand=True)

            # Set window size and position
            border_margin = self.highlight_width
            self.highlight_window.geometry(
                f"{width + border_margin * 2}x{height + border_margin * 2}+"
                f"{x - border_margin}+{y - border_margin}"
            )

            # Clear and redraw highlight rectangle
            self.highlight_canvas.delete("all")
            self.highlight_canvas.create_rectangle(
                border_margin,
                border_margin,
                width + border_margin,
                height + border_margin,
                outline=self.highlight_color,
                width=self.highlight_width,
            )

            # Show window
            self.highlight_window.deiconify()

            # Auto-hide after duration
            if duration is not None:
                self.info_window.after(duration, self.hide_highlight)

        if self.info_window:
            self.info_window.after(0, create_highlight)

    def hide_highlight(self):
        """Hide the highlight window"""

        def do_hide():
            if self.highlight_window and self.highlight_window.winfo_exists():
                self.highlight_window.withdraw()

        if self.info_window:
            self.info_window.after(0, do_hide)

    def show_screenshot(self, screenshot, duration: Optional[int] = None):
        """
        Show mini screenshot preview overlay
        
        Args:
            screenshot: PIL Image object to display
            duration: How long to show screenshot (ms), None for permanent
        """
        try:
            # Import PIL for image processing
            from PIL import Image, ImageTk
        except ImportError:
            logger.warning("PIL not available - cannot show screenshot overlay")
            return

        def create_screenshot_overlay():
            if not self.info_window:
                return

            # Create or update screenshot window
            if self.screenshot_window is None or not self.screenshot_window.winfo_exists():
                self.screenshot_window = tk.Toplevel(self.info_window)
                self.screenshot_window.overrideredirect(True)
                self.screenshot_window.attributes("-topmost", True)
                
                # Set transparency
                try:
                    self.screenshot_window.attributes("-alpha", 0.95)
                except tk.TclError:
                    pass
                
                # Create label for image
                self.screenshot_label = tk.Label(
                    self.screenshot_window,
                    bg="#1e1e1e",
                    borderwidth=2,
                    relief="solid"
                )
                self.screenshot_label.pack(padx=2, pady=2)

            # Resize screenshot to fit max size while maintaining aspect ratio
            img = screenshot
            if isinstance(screenshot, str):
                # If screenshot is a path, load it
                img = Image.open(screenshot)
            
            # Calculate resize dimensions
            width, height = img.size
            max_size = self.screenshot_max_size
            
            if width > height:
                if width > max_size:
                    new_width = max_size
                    new_height = int((max_size / width) * height)
                else:
                    new_width, new_height = width, height
            else:
                if height > max_size:
                    new_height = max_size
                    new_width = int((max_size / height) * width)
                else:
                    new_width, new_height = width, height
            
            # Resize image
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img_resized)
            
            # Keep a reference to prevent garbage collection
            self.screenshot_label.image = photo
            self.screenshot_label.configure(image=photo)
            
            # Position the screenshot window
            screen_width = self.info_window.winfo_screenwidth()
            screen_height = self.info_window.winfo_screenheight()
            
            # Calculate position based on screenshot_position
            if self.screenshot_position == "bottom-right":
                x = screen_width - new_width - 20
                y = screen_height - new_height - 80
            elif self.screenshot_position == "bottom-left":
                x = 20
                y = screen_height - new_height - 80
            elif self.screenshot_position == "top-right":
                x = screen_width - new_width - 20
                y = 20
            elif self.screenshot_position == "top-left":
                x = 20
                y = 20
            else:
                # Default to bottom-right
                x = screen_width - new_width - 20
                y = screen_height - new_height - 80
            
            self.screenshot_window.geometry(f"{new_width + 4}x{new_height + 4}+{x}+{y}")
            
            # Show window
            self.screenshot_window.deiconify()
            
            # Auto-hide after duration
            if duration is not None:
                self.info_window.after(duration, self.hide_screenshot)

        if self.info_window:
            self.info_window.after(0, create_screenshot_overlay)

    def hide_screenshot(self):
        """Hide the screenshot overlay window"""

        def do_hide():
            if self.screenshot_window and self.screenshot_window.winfo_exists():
                self.screenshot_window.withdraw()

        if self.info_window:
            self.info_window.after(0, do_hide)

    def _hide_info_window(self):
        """Hide the info overlay window"""
        if self.info_window and self.is_showing:
            self.info_window.withdraw()
            self.is_showing = False

    def show(
        self,
        message: str,
        status: OverlayStatus = OverlayStatus.IN_PROGRESS,
        coordinates: Optional[Dict[str, int]] = None,
    ):
        """
        Show overlay with message and optional coordinates

        Args:
            message: Message to display
            status: Status type for visual indicator
            coordinates: Optional element coordinates to display
        """
        self.current_message = message

        if self.info_window is None:
            # Start UI thread if not already running
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_ui_loop, daemon=True)
                self._thread.start()

        # Queue the update
        self.message_queue.put((message, status, coordinates))

    def show_with_highlight(
        self,
        message: str,
        status: OverlayStatus,
        coordinates: Dict[str, int],
        highlight_duration: Optional[int] = None,
    ):
        """
        Show overlay with message, coordinates, and element highlight

        Args:
            message: Message to display
            status: Status type
            coordinates: Element coordinates (must include x, y, width, height)
            highlight_duration: How long to show highlight (ms), None for until next action
        """
        # Show info overlay with coordinates
        self.show(message, status, coordinates)

        # Show highlight if coordinates include position and size
        if all(k in coordinates for k in ["x", "y", "width", "height"]):
            self.show_highlight(
                coordinates["x"],
                coordinates["y"],
                coordinates["width"],
                coordinates["height"],
                highlight_duration or self.duration,
            )

    def show_with_screenshot(
        self,
        message: str,
        status: OverlayStatus,
        screenshot,
        coordinates: Optional[Dict[str, int]] = None,
        screenshot_duration: Optional[int] = None,
    ):
        """
        Show overlay with message, coordinates, and screenshot preview
        
        Args:
            message: Message to display
            status: Status type
            screenshot: PIL Image object or path to screenshot
            coordinates: Optional element coordinates
            screenshot_duration: How long to show screenshot (ms), None for same as message
        """
        # Show info overlay
        self.show(message, status, coordinates)
        
        # Show screenshot overlay
        if screenshot:
            self.show_screenshot(screenshot, screenshot_duration or self.duration)

    def show_complete_feedback(
        self,
        message: str,
        status: OverlayStatus,
        screenshot=None,
        coordinates: Optional[Dict[str, int]] = None,
        highlight_duration: Optional[int] = None,
        screenshot_duration: Optional[int] = None,
    ):
        """
        Show complete visual feedback with message, coordinates, highlight, and screenshot
        
        Args:
            message: Message to display
            status: Status type
            screenshot: Optional PIL Image object or path
            coordinates: Optional element coordinates
            highlight_duration: How long to show highlight (ms)
            screenshot_duration: How long to show screenshot (ms)
        """
        # Show info overlay with coordinates
        self.show(message, status, coordinates)
        
        # Show highlight if coordinates include position and size
        if coordinates and all(k in coordinates for k in ["x", "y", "width", "height"]):
            self.show_highlight(
                coordinates["x"],
                coordinates["y"],
                coordinates["width"],
                coordinates["height"],
                highlight_duration or self.duration,
            )
        
        # Show screenshot if provided
        if screenshot:
            self.show_screenshot(screenshot, screenshot_duration or self.duration)

    def _run_ui_loop(self):
        """Run the tkinter main loop in a separate thread"""
        self._create_info_window()

        def check_queue():
            """Check for queued messages"""
            try:
                while not self.message_queue.empty():
                    item = self.message_queue.get_nowait()
                    if len(item) == 3:
                        message, status, coordinates = item
                        self._update_display(message, status, coordinates)
                    else:
                        message, status = item
                        self._update_display(message, status, None)

                    # Auto-hide after duration if not in progress
                    if status != OverlayStatus.IN_PROGRESS:
                        self.info_window.after(self.duration, self._hide_info_window)
                        self.info_window.after(self.duration, self.hide_highlight)
                        self.info_window.after(self.duration, self.hide_screenshot)
            except queue.Empty:
                pass

            # Check again in 100ms
            if self.info_window:
                self.info_window.after(100, check_queue)

        # Start checking queue
        check_queue()

        # Run main loop
        try:
            self.info_window.mainloop()
        except tk.TclError as e:
            logger.debug(f"Enhanced overlay main loop ended: {e}")
            pass

    def update(
        self,
        message: str,
        status: OverlayStatus = OverlayStatus.IN_PROGRESS,
        coordinates: Optional[Dict[str, int]] = None,
    ):
        """
        Update overlay message and coordinates

        Args:
            message: New message to display
            status: Status type for visual indicator
            coordinates: Optional element coordinates
        """
        self.show(message, status, coordinates)

    def success(self, message: str, coordinates: Optional[Dict[str, int]] = None):
        """Show success message"""
        self.show(message, OverlayStatus.SUCCESS, coordinates)

    def error(self, message: str, coordinates: Optional[Dict[str, int]] = None):
        """Show error message"""
        self.show(message, OverlayStatus.ERROR, coordinates)

    def warning(self, message: str, coordinates: Optional[Dict[str, int]] = None):
        """Show warning message"""
        self.show(message, OverlayStatus.WARNING, coordinates)

    def hide(self):
        """Hide the overlay"""
        if self.info_window:
            self.message_queue.put(("", OverlayStatus.IN_PROGRESS, None))
            self.info_window.after(0, self._hide_info_window)
            self.hide_highlight()
            self.hide_screenshot()

    def destroy(self):
        """Destroy the overlay windows"""
        if self.screenshot_window:
            try:
                self.screenshot_window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy screenshot window: {e}")
                pass
            self.screenshot_window = None

        if self.highlight_window:
            try:
                self.highlight_window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy highlight window: {e}")
                pass
            self.highlight_window = None

        if self.info_window:
            try:
                self.info_window.quit()
                self.info_window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy info window: {e}")
                pass
            self.info_window = None
