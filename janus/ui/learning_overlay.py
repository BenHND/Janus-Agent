"""
Learning Overlay - Visual feedback for learning system
Shows learning status and improvements in real-time
"""

import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any, Dict, Optional

from janus.learning.learning_manager import LearningManager


class LearningOverlay:
    """
    Compact overlay showing learning status
    Displays learning indicators during action execution
    """

    def __init__(
        self,
        learning_manager: Optional[LearningManager] = None,
        position: str = "bottom-right",
        auto_hide_ms: int = 3000,
    ):
        """
        Initialize learning overlay

        Args:
            learning_manager: LearningManager instance
            position: Screen position
            auto_hide_ms: Auto-hide delay in milliseconds
        """
        self.learning_manager = learning_manager
        self.position = position
        self.auto_hide_ms = auto_hide_ms

        self.window: Optional[tk.Tk] = None
        self.is_showing = False
        self._hide_job_id: Optional[str] = None

        # Learning state
        self.learning_active = False
        self.current_message = ""

    def show_learning_feedback(self, message: str, feedback_type: str = "info"):
        """
        Show learning feedback message

        Args:
            message: Message to display
            feedback_type: Type of feedback (info, improvement, correction)
        """
        if not self.is_showing:
            self._create_window()
            self.is_showing = True

        self.current_message = message
        self._update_display(feedback_type)
        self._schedule_auto_hide()

    def show_improvement(self, action_type: str, improvement: str, old_value: Any, new_value: Any):
        """
        Show an improvement notification

        Args:
            action_type: Type of action improved
            improvement: What was improved
            old_value: Previous value
            new_value: New value
        """
        message = f"📈 Learning: {action_type}\n{improvement}: {old_value} → {new_value}"
        self.show_learning_feedback(message, "improvement")

    def show_correction_applied(self, action_type: str, correction_count: int):
        """
        Show that a correction was applied

        Args:
            action_type: Type of action corrected
            correction_count: Number of corrections for this action
        """
        message = f"✓ Correction applied to {action_type}\n({correction_count} corrections learned)"
        self.show_learning_feedback(message, "correction")

    def show_learning_active(self):
        """Show that learning is active for current session"""
        if self.learning_manager:
            status = self.learning_manager.get_learning_status()

            message = (
                f"🧠 Learning Active\n"
                f"Session: {status.get('current_session_id', 'N/A')[:12]}...\n"
                f"Actions: {status.get('total_actions', 0)}"
            )

            self.show_learning_feedback(message, "info")

    def show_recommendation_applied(self, action_type: str, recommended_wait_ms: int):
        """
        Show that a recommendation was applied

        Args:
            action_type: Type of action
            recommended_wait_ms: Recommended wait time
        """
        message = f"⚡ Using learned timing\n{action_type}: {recommended_wait_ms}ms"
        self.show_learning_feedback(message, "info")

    def hide(self):
        """Hide the overlay"""
        if self.window:
            if self._hide_job_id:
                self.window.after_cancel(self._hide_job_id)
                self._hide_job_id = None
            self.window.withdraw()
            self.is_showing = False

    def close(self):
        """Close the overlay"""
        if self.window:
            if self._hide_job_id:
                self.window.after_cancel(self._hide_job_id)
            self.window.destroy()
            self.window = None
            self.is_showing = False

    def _create_window(self):
        """Create the overlay window"""
        if self.window:
            return

        self.window = tk.Tk()
        self.window.withdraw()  # Hide initially

        # Configure window
        self.window.title("Janus Learning")
        self.window.overrideredirect(True)  # Remove decorations
        self.window.attributes("-topmost", True)  # Always on top

        # Set transparency
        try:
            self.window.attributes("-alpha", 0.95)
        except tk.TclError:
            pass

        # Create main frame with border
        self.main_frame = tk.Frame(self.window, bg="#2C3E50", relief=tk.SOLID, borderwidth=2)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Icon label
        self.icon_label = tk.Label(
            self.main_frame, text="🧠", font=("Arial", 24), bg="#2C3E50", fg="white"
        )
        self.icon_label.pack(side=tk.TOP, pady=(10, 5))

        # Message label
        self.message_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 10),
            bg="#2C3E50",
            fg="white",
            justify=tk.CENTER,
            wraplength=250,
        )
        self.message_label.pack(side=tk.TOP, padx=15, pady=(0, 10))

        # Position window
        self._position_window()

        # Show window
        self.window.deiconify()

    def _position_window(self):
        """Position the window on screen"""
        if not self.window:
            return

        self.window.update_idletasks()

        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Get window dimensions
        window_width = 280
        window_height = 120

        # Calculate position
        if self.position == "bottom-right":
            x = screen_width - window_width - 20
            y = screen_height - window_height - 100
        elif self.position == "bottom-left":
            x = 20
            y = screen_height - window_height - 100
        elif self.position == "top-right":
            x = screen_width - window_width - 20
            y = 100
        elif self.position == "top-left":
            x = 20
            y = 100
        else:
            # Center
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _update_display(self, feedback_type: str):
        """Update the display with current message"""
        if not self.window:
            return

        # Update message
        self.message_label.config(text=self.current_message)

        # Update colors based on feedback type
        if feedback_type == "improvement":
            self.main_frame.config(bg="#27AE60")  # Green
            self.icon_label.config(bg="#27AE60", text="📈")
            self.message_label.config(bg="#27AE60")
        elif feedback_type == "correction":
            self.main_frame.config(bg="#3498DB")  # Blue
            self.icon_label.config(bg="#3498DB", text="✓")
            self.message_label.config(bg="#3498DB")
        else:  # info
            self.main_frame.config(bg="#2C3E50")  # Dark blue
            self.icon_label.config(bg="#2C3E50", text="🧠")
            self.message_label.config(bg="#2C3E50")

    def _schedule_auto_hide(self):
        """Schedule automatic hiding"""
        if self._hide_job_id:
            self.window.after_cancel(self._hide_job_id)

        self._hide_job_id = self.window.after(self.auto_hide_ms, self.hide)


class LearningFeedbackIntegration:
    """
    Integration helper for showing learning feedback during action execution
    Use this with your existing execution flow
    """

    def __init__(
        self, learning_manager: LearningManager, overlay: Optional[LearningOverlay] = None
    ):
        """
        Initialize integration

        Args:
            learning_manager: LearningManager instance
            overlay: Optional LearningOverlay instance
        """
        self.learning_manager = learning_manager
        self.overlay = overlay or LearningOverlay(learning_manager)

        # Track last values for improvement detection
        self.last_wait_times: Dict[str, int] = {}

    def on_session_start(self):
        """Call when starting a learning session"""
        self.overlay.show_learning_active()

    def on_command_parsed(self, command, show_recommendations: bool = True):
        """
        Call after parsing a command

        Args:
            command: Parsed command with recommendations
            show_recommendations: Whether to show recommendations
        """
        if not show_recommendations:
            return

        # Show if using learned recommendations
        if hasattr(command, "recommended_params") and command.recommended_params:
            wait_time = command.recommended_params.get("wait_time_ms")
            if wait_time:
                action_type = command.intent.value if hasattr(command, "intent") else "action"
                self.overlay.show_recommendation_applied(action_type, wait_time)

    def on_action_executed(self, action_type: str, success: bool, duration_ms: int):
        """
        Call after executing an action

        Args:
            action_type: Type of action
            success: Whether action succeeded
            duration_ms: Execution duration
        """
        # Check if wait time improved
        if action_type in self.last_wait_times:
            old_wait = self.last_wait_times[action_type]
            recommended = self.learning_manager.get_recommended_parameters(action_type)
            new_wait = recommended.get("wait_time_ms")

            if new_wait and abs(new_wait - old_wait) > 50:  # Significant change
                self.overlay.show_improvement(
                    action_type, "Wait time", f"{old_wait}ms", f"{new_wait}ms"
                )

        # Update last wait time
        recommended = self.learning_manager.get_recommended_parameters(action_type)
        if recommended.get("wait_time_ms"):
            self.last_wait_times[action_type] = recommended["wait_time_ms"]

    def on_user_correction(self, action_type: str):
        """
        Call when user makes a correction

        Args:
            action_type: Type of action corrected
        """
        # Get correction count
        summary = self.learning_manager.get_correction_summary(days=1)
        correction_count = summary.get("total_corrections", 0)

        self.overlay.show_correction_applied(action_type, correction_count)

    def on_heuristics_updated(self, updates: Dict[str, Any]):
        """
        Call when heuristics are updated

        Args:
            updates: Dictionary of updates
        """
        wait_time_updates = updates.get("wait_times", {})

        if wait_time_updates:
            # Show first improvement
            for action_type, update_info in list(wait_time_updates.items())[:1]:
                self.overlay.show_improvement(
                    action_type, "Wait time", f"{update_info['old']}ms", f"{update_info['new']}ms"
                )


# Convenience function
def show_learning_feedback(
    message: str, feedback_type: str = "info", learning_manager: Optional[LearningManager] = None
):
    """
    Quick function to show learning feedback

    Args:
        message: Message to display
        feedback_type: Type of feedback
        learning_manager: Optional learning manager
    """
    overlay = LearningOverlay(learning_manager)
    overlay.show_learning_feedback(message, feedback_type)
