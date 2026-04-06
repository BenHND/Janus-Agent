"""
Persistent Overlay with Start/Stop Controls - Ticket #UI-001
Draggable overlay window with real-time transcription, action status, and control buttons.
"""

import json
import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class PersistentOverlay:
    """
    Persistent draggable overlay window (300x150px) with:
    - Real-time speech-to-text transcription display
    - Action status messages
    - Start/Stop, Config, and Clear buttons
    - Position persistence between sessions
    """

    def __init__(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        on_config: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        config_path: str = "overlay_position.json",
    ):
        """
        Initialize persistent overlay

        Args:
            on_start: Callback when start button is clicked
            on_stop: Callback when stop button is clicked
            on_config: Callback when config button is clicked
            on_clear: Callback when clear button is clicked
            config_path: Path to save/load window position
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_config = on_config
        self.on_clear = on_clear
        self.config_path = config_path

        # Window state
        self.window: Optional[tk.Tk] = None
        self.is_running = False
        self.is_listening = False

        # UI components
        self.transcription_text: Optional[tk.Text] = None
        self.status_label: Optional[ttk.Label] = None
        self.start_stop_btn: Optional[ttk.Button] = None

        # Message queue for thread-safe updates
        self.message_queue = queue.Queue()

        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Thread
        self._thread: Optional[threading.Thread] = None

    def _load_position(self) -> Dict[str, int]:
        """Load saved window position"""
        default_pos = {"x": None, "y": None}  # Will use default bottom-right

        try:
            if Path(self.config_path).exists():
                with open(self.config_path, "r") as f:
                    pos = json.load(f)
                    logger.debug(f"Loaded overlay position: {pos}")
                    return pos
        except Exception as e:
            logger.warning(f"Failed to load overlay position: {e}")

        return default_pos

    def _save_position(self):
        """Save current window position"""
        if not self.window:
            return

        try:
            x = self.window.winfo_x()
            y = self.window.winfo_y()

            with open(self.config_path, "w") as f:
                json.dump({"x": x, "y": y}, f)

            logger.debug(f"Saved overlay position: x={x}, y={y}")
        except Exception as e:
            logger.warning(f"Failed to save overlay position: {e}")

    def _create_window(self):
        """Create the overlay window"""
        self.window = tk.Tk()
        self.window.title("Janus")

        # Set window size - make it larger and more visible
        self.window.geometry("350x200")
        self.window.resizable(False, False)

        # Configure window appearance
        self.window.configure(bg="#f0f0f0")  # Light gray background

        # Always on top
        self.window.attributes("-topmost", True)

        # Try to set transparency (may not work on all systems)
        try:
            self.window.attributes("-alpha", 0.95)
        except tk.TclError:
            pass

        # Position window
        pos = self._load_position()
        if pos["x"] is not None and pos["y"] is not None:
            self.window.geometry(f"350x200+{pos['x']}+{pos['y']}")
        else:
            # Default: top-right instead of bottom-right for better visibility
            self.window.update_idletasks()
            screen_width = self.window.winfo_screenwidth()
            x = screen_width - 370  # 350 + margin
            y = 50  # Top of screen
            self.window.geometry(f"350x200+{x}+{y}")

        # Create UI
        self._create_ui()

        # Make window draggable
        self._make_draggable()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Force update to ensure visibility
        self.window.update_idletasks()

    def _create_ui(self):
        """Create the UI components"""
        # Main container with padding and background
        main_frame = ttk.Frame(self.window, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        title_label = ttk.Label(
            main_frame, text="Janus Voice Control", font=("Arial", 12, "bold"), foreground="navy"
        )
        title_label.pack(fill=tk.X, pady=(0, 8))

        # Top section: Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 8))

        # Start/Stop button - make it more prominent
        self.start_stop_btn = ttk.Button(
            button_frame, text="▶️ Start Listening", command=self._on_start_stop, width=15
        )
        self.start_stop_btn.pack(side=tk.LEFT, padx=3)

        # Config button
        config_btn = ttk.Button(
            button_frame, text="⚙️ Config", command=self._on_config_clicked, width=8
        )
        config_btn.pack(side=tk.LEFT, padx=3)

        # Clear button
        clear_btn = ttk.Button(
            button_frame, text="🔄 Clear", command=self._on_clear_clicked, width=8
        )
        clear_btn.pack(side=tk.LEFT, padx=3)

        # Middle section: Status label with better styling
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(status_frame, text="Status:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        self.status_label = ttk.Label(
            status_frame, text="Ready", font=("Arial", 10), foreground="green"
        )
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # Bottom section: Transcription display with label
        ttk.Label(main_frame, text="Transcription:", font=("Arial", 9, "bold")).pack(anchor=tk.W)

        transcription_frame = ttk.Frame(main_frame)
        transcription_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Scrollbar
        scrollbar = ttk.Scrollbar(transcription_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget for transcription with better styling
        self.transcription_text = tk.Text(
            transcription_frame,
            height=6,
            wrap=tk.WORD,
            font=("Arial", 9),
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED,
            bg="white",
            fg="black",
            relief="sunken",
            borderwidth=2,
        )
        self.transcription_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.transcription_text.yview)

        # Add initial content to make it visible
        self.transcription_text.config(state=tk.NORMAL)
        self.transcription_text.insert(
            tk.END, "Janus Voice Control Ready\nClick 'Start Listening' to begin\n"
        )
        self.transcription_text.config(state=tk.DISABLED)

    def _make_draggable(self):
        """Make the window draggable without trembling"""

        def start_drag(event):
            self._drag_start_x = event.x_root - self.window.winfo_x()
            self._drag_start_y = event.y_root - self.window.winfo_y()

        def on_drag(event):
            x = event.x_root - self._drag_start_x
            y = event.y_root - self._drag_start_y
            self.window.geometry(f"+{x}+{y}")

        def end_drag(event):
            self._save_position()

        # Bind to title area only, not the whole window
        title_label = self.window.children.get("!frame").children.get("!label")
        if title_label:
            title_label.bind("<Button-1>", start_drag)
            title_label.bind("<B1-Motion>", on_drag)
            title_label.bind("<ButtonRelease-1>", end_drag)

        # Also bind to main frame for dragging
        main_frame = self.window.children.get("!frame")
        if main_frame:
            main_frame.bind("<Button-1>", start_drag)
            main_frame.bind("<B1-Motion>", on_drag)
            main_frame.bind("<ButtonRelease-1>", end_drag)

    def _on_start_stop(self):
        """Handle start/stop button click"""
        if not self.is_listening:
            # Start listening
            self.is_listening = True
            self.start_stop_btn.config(text="⏸️ Stop")
            self.update_status("Listening...")
            if self.on_start:
                threading.Thread(target=self.on_start, daemon=True).start()
        else:
            # Stop listening
            self.is_listening = False
            self.start_stop_btn.config(text="▶️ Start")
            self.update_status("Stopped")
            if self.on_stop:
                threading.Thread(target=self.on_stop, daemon=True).start()

    def _on_config_clicked(self):
        """Handle config button click"""
        if self.on_config:
            threading.Thread(target=self.on_config, daemon=True).start()

    def _on_clear_clicked(self):
        """Handle clear button click"""
        self.clear_transcription()
        if self.on_clear:
            threading.Thread(target=self.on_clear, daemon=True).start()

    def _on_close(self):
        """Handle window close event"""
        self._save_position()
        self.is_running = False
        if self.window:
            self.window.quit()

    def _check_message_queue(self):
        """Check message queue for updates (called from UI thread)"""
        try:
            while not self.message_queue.empty():
                msg_type, msg_data = self.message_queue.get_nowait()

                if msg_type == "transcription":
                    self._update_transcription_ui(msg_data)
                elif msg_type == "status":
                    self._update_status_ui(msg_data)
                elif msg_type == "clear":
                    self._clear_transcription_ui()
        except queue.Empty:
            pass

        # Schedule next check
        if self.window and self.is_running:
            self.window.after(100, self._check_message_queue)

    def _update_transcription_ui(self, text: str):
        """Update transcription text (called from UI thread)"""
        if self.transcription_text:
            self.transcription_text.config(state=tk.NORMAL)
            self.transcription_text.insert(tk.END, text + "\n")
            self.transcription_text.see(tk.END)
            self.transcription_text.config(state=tk.DISABLED)

    def _update_status_ui(self, text: str):
        """Update status label (called from UI thread)"""
        if self.status_label:
            self.status_label.config(text=text)

    def _clear_transcription_ui(self):
        """Clear transcription text (called from UI thread)"""
        if self.transcription_text:
            self.transcription_text.config(state=tk.NORMAL)
            self.transcription_text.delete(1.0, tk.END)
            self.transcription_text.config(state=tk.DISABLED)

    # Public API

    def show(self):
        """Show the overlay window (must run on main thread)"""
        # Create window directly on main thread instead of using a separate thread
        if self.window is None:
            self._create_window()
            self.is_running = True

            # Start message queue checking
            self._check_message_queue()

            logger.info("Persistent overlay started on main thread")

    def run_main_loop(self):
        """Run the main UI loop (call this on main thread)"""
        if self.window:
            try:
                self.window.mainloop()
            except Exception as e:
                logger.error(f"Error in overlay main loop: {e}", exc_info=True)
            finally:
                self.is_running = False

    def hide(self):
        """Hide the overlay window"""
        if self.window:
            self.window.withdraw()

    def update_transcription(self, text: str):
        """
        Update the transcription display (thread-safe)

        Args:
            text: Transcribed text to display
        """
        self.message_queue.put(("transcription", text))

    def update_status(self, text: str):
        """
        Update the status label (thread-safe)

        Args:
            text: Status text to display
        """
        self.message_queue.put(("status", text))

    def clear_transcription(self):
        """Clear the transcription display (thread-safe)"""
        self.message_queue.put(("clear", None))

    def destroy(self):
        """Destroy the overlay window"""
        self._save_position()
        if self.window:
            try:
                self.window.quit()
                self.window.destroy()
            except Exception as e:
                logger.debug(f"Error destroying overlay: {e}")
            self.window = None
        self.is_running = False


# Example usage
if __name__ == "__main__":
    import time

    def on_start():
        print("Start button clicked")
        overlay.update_status("Listening...")

    def on_stop():
        print("Stop button clicked")
        overlay.update_status("Stopped")

    def on_config():
        print("Config button clicked")

    def on_clear():
        print("Clear button clicked")

    # Create and show overlay
    overlay = PersistentOverlay(
        on_start=on_start, on_stop=on_stop, on_config=on_config, on_clear=on_clear
    )
    overlay.show()

    # Simulate transcription updates
    time.sleep(2)
    overlay.update_transcription("Test transcription 1")
    overlay.update_status("Processing...")

    time.sleep(2)
    overlay.update_transcription("Test transcription 2")
    overlay.update_status("✅ Done")

    # Keep running
    try:
        overlay.run_main_loop()
    except KeyboardInterrupt:
        pass

    overlay.destroy()
