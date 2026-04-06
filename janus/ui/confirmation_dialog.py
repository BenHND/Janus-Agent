"""
Confirmation Dialog - User confirmation for critical actions
Displays modal dialog for high-risk actions requiring explicit user approval

SAFETY-001: Updated to use RiskLevel from module_action_schema.py (SSOT)
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

from janus.runtime.core.module_action_schema import RiskLevel

logger = logging.getLogger(__name__)


class ConfirmationDialog:
    """
    Modal dialog for confirming critical actions
    Integrates with UnifiedActionValidator for risk-based confirmation
    """

    def __init__(self, timeout: int = 30000):
        """
        Initialize confirmation dialog

        Args:
            timeout: Timeout in milliseconds before auto-deny (0 = no timeout)
        """
        self.timeout = timeout
        self.result_queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def confirm(
        self,
        action: str,
        risk_level: RiskLevel,
        warning_message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> bool:
        """
        Show confirmation dialog and get user response

        Args:
            action: Action name/description
            risk_level: Risk level of the action
            warning_message: Warning message to display
            details: Additional details about the action

        Returns:
            True if user confirmed, False if denied or timeout
        """
        # Start UI thread
        self._thread = threading.Thread(
            target=self._show_dialog,
            args=(action, risk_level, warning_message, details),
            daemon=True,
        )
        self._thread.start()

        # Wait for result with timeout
        try:
            timeout_seconds = self.timeout / 1000.0 if self.timeout > 0 else None
            result = self.result_queue.get(timeout=timeout_seconds)
            return result
        except queue.Empty:
            # Timeout - deny action
            return False

    def _show_dialog(
        self,
        action: str,
        risk_level: RiskLevel,
        warning_message: Optional[str],
        details: Optional[str],
    ):
        """Create and show the confirmation dialog"""
        window = tk.Tk()
        window.title("Janus - Confirmation Required")

        # Configure window
        window.attributes("-topmost", True)
        window.resizable(False, False)

        # Center window
        window.update_idletasks()
        window_width = 450
        window_height = 250
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Main frame with padding
        main_frame = ttk.Frame(window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Risk level colors (SAFETY-001: Updated to use RiskLevel)
        risk_colors = {
            RiskLevel.LOW: "#8BC34A",
            RiskLevel.MEDIUM: "#FF9800",
            RiskLevel.HIGH: "#FF5722",
            RiskLevel.CRITICAL: "#F44336",
        }

        # Header with risk indicator
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # Risk indicator
        canvas = tk.Canvas(
            header_frame, width=30, height=30, bg=window.cget("bg"), highlightthickness=0
        )
        canvas.pack(side=tk.LEFT, padx=(0, 10))
        canvas.create_oval(2, 2, 28, 28, fill=risk_colors.get(risk_level, "#999999"), outline="")

        # Title
        title_label = ttk.Label(
            header_frame,
            text=f"Confirm {risk_level.value.upper()} Risk Action",
            font=("Arial", 12, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        # Action description
        action_label = ttk.Label(
            main_frame, text=f"Action: {action}", font=("Arial", 10), wraplength=400
        )
        action_label.pack(anchor=tk.W, pady=(0, 10))

        # Warning message
        if warning_message:
            warning_frame = ttk.Frame(main_frame, relief=tk.SOLID, borderwidth=1)
            warning_frame.pack(fill=tk.X, pady=(0, 10))

            warning_label = ttk.Label(
                warning_frame,
                text=f"⚠️ {warning_message}",
                font=("Arial", 9),
                wraplength=400,
                foreground="#FF5722",
            )
            warning_label.pack(padx=10, pady=10)

        # Details
        if details:
            details_label = ttk.Label(
                main_frame, text=details, font=("Arial", 9), wraplength=400, foreground="#666666"
            )
            details_label.pack(anchor=tk.W, pady=(0, 15))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def on_confirm():
            self.result_queue.put(True)
            window.destroy()

        def on_deny():
            self.result_queue.put(False)
            window.destroy()

        def on_close():
            """Handle window close button"""
            self.result_queue.put(False)
            window.destroy()

        # Deny button (left)
        deny_button = ttk.Button(button_frame, text="Deny", command=on_deny)
        deny_button.pack(side=tk.LEFT, padx=(0, 10))

        # Confirm button (right)
        confirm_button = ttk.Button(button_frame, text="Confirm", command=on_confirm)
        confirm_button.pack(side=tk.RIGHT)

        # Handle window close
        window.protocol("WM_DELETE_WINDOW", on_close)

        # Focus confirm button for critical/high risk (SAFETY-001: Updated to RiskLevel)
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            deny_button.focus()
        else:
            confirm_button.focus()

        # Auto-deny on timeout
        if self.timeout > 0:
            window.after(self.timeout, lambda: on_deny() if window.winfo_exists() else None)

        # Run main loop
        try:
            window.mainloop()
        except Exception as e:
            logger.error(f"Error in confirmation dialog main loop: {e}")
            # Ensure result is set even on error
            if self.result_queue.empty():
                self.result_queue.put(False)
