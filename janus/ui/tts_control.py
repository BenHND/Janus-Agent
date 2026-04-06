"""
TTS Control UI - Mini control panel for TTS
Ticket TICKET-MAC-03: TTS Activation and Stabilization

Provides a mini UI with mute/unmute button and volume/rate controls.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TTSControlPanel:
    """
    Mini control panel for TTS

    Features:
    - Mute/unmute button
    - Volume slider
    - Rate slider
    - Status indicator
    - Compact, always-on-top window
    """

    def __init__(
        self,
        tts_adapter,
        position: str = "bottom-right",
        on_mute_change: Optional[Callable[[bool], None]] = None,
    ):
        """
        Initialize TTS control panel

        Args:
            tts_adapter: MacTTSAdapter instance to control
            position: Position on screen ('top-right', 'bottom-right', etc.)
            on_mute_change: Optional callback when mute state changes
        """
        self.tts = tts_adapter
        self.position = position
        self.on_mute_change = on_mute_change

        self.window: Optional[tk.Tk] = None
        self.is_visible = False

        # UI elements
        self.mute_button = None
        self.volume_slider = None
        self.rate_slider = None
        self.status_label = None

    def create_window(self):
        """Create the control panel window"""
        self.window = tk.Tk()
        self.window.title("TTS Controls")
        self.window.overrideredirect(True)  # Remove window decorations
        self.window.attributes("-topmost", True)  # Always on top

        # Set transparency
        try:
            self.window.attributes("-alpha", 0.9)
        except tk.TclError:
            pass

        # Create main frame
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="TTS Controls", font=("Arial", 10, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))

        # Mute/Unmute button
        self.mute_button = ttk.Button(
            main_frame,
            text="🔊 Mute" if not self.tts.is_muted() else "🔇 Unmute",
            command=self._toggle_mute,
        )
        self.mute_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)

        # Volume control
        volume_label = ttk.Label(main_frame, text="Volume:")
        volume_label.grid(row=2, column=0, sticky="w", pady=2)

        self.volume_slider = ttk.Scale(
            main_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            command=self._on_volume_change,
            length=150,
        )
        self.volume_slider.set(self.tts.get_volume())
        self.volume_slider.grid(row=2, column=1, sticky="ew", pady=2)

        # Rate control
        rate_label = ttk.Label(main_frame, text="Rate (WPM):")
        rate_label.grid(row=3, column=0, sticky="w", pady=2)

        self.rate_slider = ttk.Scale(
            main_frame,
            from_=100,
            to=300,
            orient=tk.HORIZONTAL,
            command=self._on_rate_change,
            length=150,
        )
        self.rate_slider.set(self.tts.rate)
        self.rate_slider.grid(row=3, column=1, sticky="ew", pady=2)

        # Status indicator
        self.status_label = ttk.Label(
            main_frame, text="● Ready", foreground="green", font=("Arial", 9)
        )
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(5, 0))

        # Close button
        close_button = ttk.Button(main_frame, text="×", command=self.hide, width=3)
        close_button.grid(row=0, column=2, sticky="ne")

        # Position window
        self._position_window()

        # Update status periodically
        self._update_status()

    def _position_window(self):
        """Position the window on screen"""
        self.window.update_idletasks()

        # Get window size
        width = self.window.winfo_width()
        height = self.window.winfo_height()

        # Get screen size
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Calculate position
        if self.position == "top-right":
            x = screen_width - width - 20
            y = 20
        elif self.position == "top-left":
            x = 20
            y = 20
        elif self.position == "bottom-right":
            x = screen_width - width - 20
            y = screen_height - height - 60
        elif self.position == "bottom-left":
            x = 20
            y = screen_height - height - 60
        else:
            x = screen_width - width - 20
            y = screen_height - height - 60

        self.window.geometry(f"+{x}+{y}")

    def _toggle_mute(self):
        """Toggle mute state"""
        if self.tts.is_muted():
            self.tts.unmute()
            self.mute_button.config(text="🔊 Mute")
            logger.info("TTS unmuted via control panel")
        else:
            self.tts.mute()
            self.mute_button.config(text="🔇 Unmute")
            logger.info("TTS muted via control panel")

        # Call callback if provided
        if self.on_mute_change:
            self.on_mute_change(self.tts.is_muted())

    def _on_volume_change(self, value):
        """Handle volume slider change"""
        volume = float(value)
        self.tts.set_volume(volume)
        logger.debug(f"TTS volume changed to {volume:.2f} via control panel")

    def _on_rate_change(self, value):
        """Handle rate slider change"""
        rate = int(float(value))
        self.tts.set_rate(rate)
        logger.debug(f"TTS rate changed to {rate} WPM via control panel")

    def _update_status(self):
        """Update status indicator"""
        if not self.window or not self.status_label:
            return

        try:
            if self.tts.is_speaking():
                self.status_label.config(text="● Speaking", foreground="blue")
            elif self.tts.is_muted():
                self.status_label.config(text="● Muted", foreground="orange")
            else:
                self.status_label.config(text="● Ready", foreground="green")

            # Schedule next update
            self.window.after(100, self._update_status)
        except tk.TclError as e:
            logger.debug(f"Failed to update TTS control status: {e}")
            pass

    def show(self):
        """Show the control panel"""
        if not self.window:
            self.create_window()

        self.window.deiconify()
        self.is_visible = True
        logger.info("TTS control panel shown")

    def hide(self):
        """Hide the control panel"""
        if self.window:
            self.window.withdraw()
            self.is_visible = False
            logger.info("TTS control panel hidden")

    def toggle_visibility(self):
        """Toggle control panel visibility"""
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def destroy(self):
        """Destroy the control panel"""
        if self.window:
            self.window.destroy()
            self.window = None
            self.is_visible = False
            logger.info("TTS control panel destroyed")

    def run(self):
        """Run the control panel (blocking)"""
        if not self.window:
            self.create_window()

        self.show()

        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.destroy()
