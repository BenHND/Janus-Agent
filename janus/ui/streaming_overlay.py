"""
Streaming STT Overlay - Progressive text display for real-time transcription (TICKET LOCAL-4)

Features:
- Progressive text display as user speaks
- Typing animation effect
- Smooth updates without flickering
- Sentence-by-sentence display
- Confidence indicators
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import font, ttk
from typing import Callable, Optional

from janus.logging import get_logger

logger = get_logger("streaming_overlay")


class StreamingOverlay:
    """
    Overlay window for displaying progressive transcription

    Features:
    - Text appears progressively as transcription proceeds
    - Smooth animations
    - Auto-positioning
    - Minimal flickering
    """

    def __init__(
        self,
        position: str = "top-center",
        max_width: int = 600,
        max_lines: int = 5,
        auto_hide_delay: float = 3.0,
    ):
        """
        Initialize streaming overlay

        Args:
            position: Position on screen ('top-center', 'bottom-center', etc.)
            max_width: Maximum width in pixels
            max_lines: Maximum number of text lines to display
            auto_hide_delay: Seconds before auto-hiding after final result
        """
        self.position = position
        self.max_width = max_width
        self.max_lines = max_lines
        self.auto_hide_delay = auto_hide_delay

        self.window: Optional[tk.Tk] = None
        self.text_widget: Optional[tk.Text] = None
        self.is_showing = False
        self.message_queue = queue.Queue()

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # State
        self.current_text = ""
        self.last_update_time = 0
        self.hide_timer = None

    def start(self):
        """Start the overlay window"""
        if self._thread and self._thread.is_alive():
            logger.warning("Overlay already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_window, daemon=True)
        self._thread.start()

        # Wait for window to be ready
        time.sleep(0.5)

        logger.info("StreamingOverlay started")

    def stop(self):
        """Stop the overlay window"""
        self._stop_event.set()

        if self.window:
            try:
                self.window.quit()
            except:
                pass

        if self._thread:
            self._thread.join(timeout=2.0)

        logger.info("StreamingOverlay stopped")

    def update_text(self, text: str, is_final: bool = False, confidence: float = 1.0):
        """
        Update displayed text

        Args:
            text: Text to display
            is_final: Whether this is the final result
            confidence: Confidence score (0-1)
        """
        self.message_queue.put(
            {
                "type": "update",
                "text": text,
                "is_final": is_final,
                "confidence": confidence,
                "timestamp": time.time(),
            }
        )

    def show(self):
        """Show the overlay"""
        self.message_queue.put({"type": "show"})

    def hide(self):
        """Hide the overlay"""
        self.message_queue.put({"type": "hide"})

    def clear(self):
        """Clear the text"""
        self.message_queue.put({"type": "clear"})

    def _run_window(self):
        """Run the Tkinter event loop (in thread)"""
        try:
            self._create_window()
            self._process_queue()
            self.window.mainloop()
        except Exception as e:
            logger.error(f"Error in overlay window: {e}", exc_info=True)

    def _create_window(self):
        """Create the overlay window"""
        self.window = tk.Tk()
        self.window.withdraw()  # Hide initially

        # Configure window
        self.window.title("Janus - Transcription")
        self.window.overrideredirect(True)  # Remove decorations
        self.window.attributes("-topmost", True)  # Always on top

        # Transparency
        try:
            self.window.attributes("-alpha", 0.95)
        except tk.TclError:
            pass

        # Configure colors
        bg_color = "#2C2C2C"
        fg_color = "#FFFFFF"

        self.window.configure(bg=bg_color)

        # Create frame
        self.frame = tk.Frame(
            self.window,
            bg=bg_color,
            padx=15,
            pady=12,
        )
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Status indicator
        self.status_label = tk.Label(
            self.frame,
            text="🎤",
            font=("Arial", 14),
            bg=bg_color,
            fg=fg_color,
        )
        self.status_label.pack(side=tk.TOP, anchor=tk.W, pady=(0, 5))

        # Text widget for transcription
        text_font = font.Font(family="Arial", size=12)

        self.text_widget = tk.Text(
            self.frame,
            font=text_font,
            bg=bg_color,
            fg=fg_color,
            wrap=tk.WORD,
            height=self.max_lines,
            width=50,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=5,
            pady=5,
            cursor="",
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # Disable editing
        self.text_widget.config(state=tk.DISABLED)

        # Configure text tags for styling
        self.text_widget.tag_config("partial", foreground="#CCCCCC")
        self.text_widget.tag_config("final", foreground="#FFFFFF")
        self.text_widget.tag_config("low_confidence", foreground="#999999")

        # Position window
        self._position_window()

    def _position_window(self):
        """Position the window on screen"""
        self.window.update_idletasks()

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        window_width = min(self.max_width, screen_width - 40)
        window_height = self.window.winfo_reqheight()

        # Calculate position based on preference
        if self.position == "top-center":
            x = (screen_width - window_width) // 2
            y = 20
        elif self.position == "bottom-center":
            x = (screen_width - window_width) // 2
            y = screen_height - window_height - 80
        elif self.position == "top-right":
            x = screen_width - window_width - 20
            y = 20
        else:
            # Default to top-center
            x = (screen_width - window_width) // 2
            y = 20

        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _process_queue(self):
        """Process message queue"""
        try:
            # Process all pending messages
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self._handle_message(message)

            # Schedule next check
            if not self._stop_event.is_set():
                self.window.after(50, self._process_queue)

        except Exception as e:
            logger.error(f"Error processing queue: {e}", exc_info=True)

    def _handle_message(self, message: dict):
        """Handle a message from the queue"""
        msg_type = message.get("type")

        if msg_type == "update":
            self._update_text_display(message["text"], message["is_final"], message["confidence"])
        elif msg_type == "show":
            self._show_window()
        elif msg_type == "hide":
            self._hide_window()
        elif msg_type == "clear":
            self._clear_text()

    def _update_text_display(self, text: str, is_final: bool, confidence: float):
        """Update the text display"""
        if not self.text_widget:
            return

        # Cancel hide timer if active
        if self.hide_timer:
            self.window.after_cancel(self.hide_timer)
            self.hide_timer = None

        # Show window if hidden
        if not self.is_showing:
            self._show_window()

        # Update status indicator
        if is_final:
            self.status_label.config(text="✓")
        else:
            self.status_label.config(text="…")

        # Update text
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)

        # Determine tag based on state
        if is_final:
            tag = "final"
        elif confidence < 0.5:
            tag = "low_confidence"
        else:
            tag = "partial"

        self.text_widget.insert("1.0", text, tag)
        self.text_widget.config(state=tk.DISABLED)

        # Auto-scroll to end
        self.text_widget.see(tk.END)

        self.current_text = text
        self.last_update_time = time.time()

        # Schedule auto-hide if final
        if is_final and self.auto_hide_delay > 0:
            self.hide_timer = self.window.after(int(self.auto_hide_delay * 1000), self._hide_window)

    def _show_window(self):
        """Show the window"""
        if not self.is_showing:
            self.window.deiconify()
            self.window.lift()
            self.is_showing = True
            logger.debug("Overlay shown")

    def _hide_window(self):
        """Hide the window"""
        if self.is_showing:
            self.window.withdraw()
            self.is_showing = False
            logger.debug("Overlay hidden")

    def _clear_text(self):
        """Clear the text"""
        if self.text_widget:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.config(state=tk.DISABLED)
            self.current_text = ""


def create_streaming_overlay(**kwargs) -> StreamingOverlay:
    """
    Factory function to create a StreamingOverlay

    Args:
        **kwargs: Arguments for StreamingOverlay

    Returns:
        StreamingOverlay instance
    """
    return StreamingOverlay(**kwargs)
