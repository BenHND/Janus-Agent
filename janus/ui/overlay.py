"""
Action Overlay - Visual feedback for ongoing actions
Displays a transparent overlay showing current action status
Now with vision detection feedback and mini screenshot overlay (TICKET-FEAT-003)
"""

import logging
import queue
import threading
import tkinter as tk
from enum import Enum
from tkinter import ttk
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OverlayStatus(Enum):
    """Status types for overlay display"""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ActionOverlay:
    """
    Transparent overlay window showing action feedback
    Displays at top-right of screen with status indicators
    """

    def __init__(
        self, 
        position: str = "top-right", 
        duration: int = 3000,
        screenshot_max_size: int = 200,
        screenshot_position: str = "bottom-right"
    ):
        """
        Initialize action overlay

        Args:
            position: Position on screen ('top-right', 'top-left', 'bottom-right', 'bottom-left')
            duration: How long to show success/error messages in milliseconds
            screenshot_max_size: Maximum size for screenshot preview (pixels)
            screenshot_position: Position for screenshot overlay
        """
        self.position = position
        self.duration = duration
        self.screenshot_max_size = screenshot_max_size
        self.screenshot_position = screenshot_position
        self.window: Optional[tk.Tk] = None
        self.screenshot_window: Optional[tk.Toplevel] = None
        self.message_queue = queue.Queue()
        self.current_message: Optional[str] = None
        self.is_showing = False
        self._thread: Optional[threading.Thread] = None

        # Status colors
        self.colors = {
            OverlayStatus.IN_PROGRESS: "#2196F3",  # Blue
            OverlayStatus.SUCCESS: "#4CAF50",  # Green
            OverlayStatus.ERROR: "#F44336",  # Red
            OverlayStatus.WARNING: "#FF9800",  # Orange
        }

    def _create_window(self):
        """Create the overlay window"""
        self.window = tk.Tk()
        self.window.withdraw()  # Hide initially

        # Configure window
        self.window.title("Janus")
        self.window.overrideredirect(True)  # Remove window decorations
        self.window.attributes("-topmost", True)  # Always on top

        # Try to make window transparent (may not work on all platforms)
        try:
            self.window.attributes("-alpha", 0.9)
        except tk.TclError:
            pass  # Alpha transparency not supported

        # Create frame
        self.frame = ttk.Frame(self.window, padding=10)
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

        # Position window
        self._position_window()

    def _position_window(self):
        """Position the window based on configured position"""
        if not self.window:
            return

        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()

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

        self.window.geometry(f"+{x}+{y}")

    def _update_display(self, message: str, status: OverlayStatus):
        """Update the overlay display"""
        if not self.window:
            self._create_window()

        # Update status indicator color
        self.status_canvas.itemconfig(self.status_indicator, fill=self.colors[status])

        # Update message
        self.label.config(text=message)

        # Reposition in case window size changed
        self.window.update_idletasks()
        self._position_window()

        # Show window
        self.window.deiconify()
        self.is_showing = True

    def _hide_window(self):
        """Hide the overlay window"""
        if self.window and self.is_showing:
            self.window.withdraw()
            self.is_showing = False

    def show(self, message: str, status: OverlayStatus = OverlayStatus.IN_PROGRESS):
        """
        Show overlay with message

        Args:
            message: Message to display
            status: Status type for visual indicator
        """
        self.current_message = message

        if self.window is None:
            # Start UI thread if not already running
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_ui_loop, daemon=True)
                self._thread.start()

        # Queue the update
        self.message_queue.put((message, status))

    def _run_ui_loop(self):
        """Run the tkinter main loop in a separate thread"""
        self._create_window()

        def check_queue():
            """Check for queued messages"""
            try:
                while not self.message_queue.empty():
                    message, status = self.message_queue.get_nowait()
                    self._update_display(message, status)

                    # Auto-hide after duration if not in progress
                    if status != OverlayStatus.IN_PROGRESS:
                        self.window.after(self.duration, self._hide_window)
            except queue.Empty:
                pass

            # Check again in 100ms
            if self.window:
                self.window.after(100, check_queue)

        # Start checking queue
        check_queue()

        # Run main loop
        try:
            self.window.mainloop()
        except tk.TclError as e:
            logger.debug(f"Overlay main loop ended: {e}")
            pass

    def update(self, message: str, status: OverlayStatus = OverlayStatus.IN_PROGRESS):
        """
        Update overlay message

        Args:
            message: New message to display
            status: Status type for visual indicator
        """
        self.show(message, status)

    def success(self, message: str):
        """Show success message"""
        self.show(message, OverlayStatus.SUCCESS)

    def error(self, message: str):
        """Show error message"""
        self.show(message, OverlayStatus.ERROR)

    def warning(self, message: str):
        """Show warning message"""
        self.show(message, OverlayStatus.WARNING)

    def show_vision_feedback(self, verification: Dict[str, Any], screenshot: Optional[Any] = None):
        """
        Show vision verification feedback with optional mini capture overlay
        TICKET-MAC-05: Enhanced visual feedback
        TICKET-FEAT-003: Mini screenshot overlay implementation

        Args:
            verification: Verification result from vision cognitive engine
            screenshot: Optional PIL Image to show as mini preview
        """
        verified = verification.get("verified", True)
        confidence = verification.get("confidence", 0.0)
        reason = verification.get("reason", "")
        duration_ms = verification.get("duration_ms", 0)
        method = verification.get("method", "unknown")

        if verified:
            # Show success with confidence and timing
            icon = "✅" if confidence > 0.7 else "✓"
            message = f"{icon} Verified ({confidence:.0%})"
            if duration_ms > 0:
                message += f" • {duration_ms}ms"
            if method and method != "none":
                message += f" • {method}"
            if reason and reason != "Cannot verify specific action without specialized check":
                message += f"\n{reason[:60]}"
            self.success(message)
        else:
            # Show warning/error with details
            message = f"❌ Verification failed ({confidence:.0%})"
            if duration_ms > 0:
                message += f" • {duration_ms}ms"
            message += f"\n{reason[:60]}"
            self.warning(message)

        # Show mini screenshot overlay if screenshot provided
        if screenshot:
            try:
                self._show_screenshot_overlay(screenshot, self.duration)
            except Exception as e:
                logger.warning(f"Failed to show screenshot overlay: {e}")
                logger.debug("Mini screenshot available but could not be displayed")

    def _show_screenshot_overlay(self, screenshot, duration: int = 3000):
        """
        Show mini screenshot overlay
        
        Args:
            screenshot: PIL Image object to display
            duration: How long to show screenshot (ms)
        """
        try:
            from PIL import Image, ImageTk
        except ImportError:
            logger.warning("PIL not available - cannot show screenshot overlay")
            return

        # Create a simple toplevel window for screenshot if needed
        if self.screenshot_window is None:
            if self.window and self.window.winfo_exists():
                self.screenshot_window = tk.Toplevel(self.window)
                self.screenshot_window.overrideredirect(True)
                self.screenshot_window.attributes("-topmost", True)
                
                try:
                    self.screenshot_window.attributes("-alpha", 0.95)
                except tk.TclError:
                    pass
                
                self.screenshot_label = tk.Label(
                    self.screenshot_window,
                    bg="#1e1e1e",
                    borderwidth=2,
                    relief="solid"
                )
                self.screenshot_label.pack(padx=2, pady=2)
            else:
                logger.debug("Main window not available for screenshot overlay")
                return

        # Resize screenshot to fit configured max size
        img = screenshot
        if isinstance(screenshot, str):
            img = Image.open(screenshot)
        
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
        
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        
        # Keep reference and display
        self.screenshot_label.image = photo
        self.screenshot_label.configure(image=photo)
        
        # Calculate position based on screenshot_position
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
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
        self.screenshot_window.deiconify()
        
        # Auto-hide after duration
        if self.window:
            self.window.after(duration, self._hide_screenshot_overlay)

    def _hide_screenshot_overlay(self):
        """Hide the screenshot overlay window"""
        if self.screenshot_window:
            try:
                if self.screenshot_window.winfo_exists():
                    self.screenshot_window.withdraw()
            except tk.TclError:
                pass

    def show_error_detection(self, error_result: Dict[str, Any]):
        """
        Show visual error detection feedback

        Args:
            error_result: Error detection result
        """
        if error_result.get("has_error", False):
            error_type = error_result.get("error_type", "unknown")
            confidence = error_result.get("confidence", 0.0)
            message = f"⚠ Error detected: {error_type} ({confidence:.0%})"
            self.error(message)

    def show_intention(self, intention: str):
        """
        Show detected intention before action execution (TICKET-UX-001)
        Provides optimistic feedback to reassure user immediately
        
        This method is available for use by agents/modules that want to show
        what they're about to do before executing. Currently optional, but enables
        richer feedback (e.g., "Looking for Login button..." before clicking).
        
        Args:
            intention: Description of detected intention (e.g., "Looking for Login button...")
        """
        self.show(f"🔍 {intention}", OverlayStatus.IN_PROGRESS)

    def hide(self):
        """Hide the overlay"""
        if self.window:
            self.message_queue.put(("", OverlayStatus.IN_PROGRESS))
            self.window.after(0, self._hide_window)
            self._hide_screenshot_overlay()

    def destroy(self):
        """Destroy the overlay window"""
        # Destroy screenshot window first
        if self.screenshot_window:
            try:
                self.screenshot_window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy screenshot window: {e}")
                pass
            self.screenshot_window = None

        # Destroy main window
        if self.window:
            try:
                self.window.quit()
                self.window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy overlay window: {e}")
                pass
            self.window = None
