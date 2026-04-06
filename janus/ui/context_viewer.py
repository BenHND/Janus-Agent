"""
Context Viewer UI - Visualize current context state
Part of TICKET-010: Context Engine Full Integration

Displays:
- System state (active window, apps, URLs)
- Session context (recent actions)
- Memory context (last commands, apps, files)
- Calendar and email context (if enabled)
"""

import json
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk
from typing import Any, Dict, Optional


class ContextViewerUI:
    """
    UI window to visualize current context

    Features:
    - Real-time context display
    - Auto-refresh option
    - Collapsible sections
    - Copy context to clipboard
    """

    def __init__(self, refresh_interval: int = 5000):
        """
        Initialize context viewer UI

        Args:
            refresh_interval: Auto-refresh interval in milliseconds (0 to disable)
        """
        self.refresh_interval = refresh_interval
        self.window: Optional[tk.Tk] = None
        self.text_widget: Optional[scrolledtext.ScrolledText] = None
        self.auto_refresh_var = tk.BooleanVar(value=refresh_interval > 0)
        self.refresh_timer = None

    def create_window(self):
        """Create and configure the viewer window"""
        self.window = tk.Tk()
        self.window.title("Janus - Context Viewer")
        self.window.geometry("800x600")

        # Create toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Refresh", command=self.refresh_context).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            toolbar,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(toolbar, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Button(toolbar, text="Clear Context", command=self.clear_context).pack(
            side=tk.RIGHT, padx=2
        )

        # Create text display area
        text_frame = ttk.Frame(self.window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("Monaco", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_label = ttk.Label(self.window, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Initial refresh
        self.refresh_context()

    def refresh_context(self):
        """Refresh and display current context"""
        try:
            from janus.runtime.api.context_api import get_context

            self.status_label.config(text="Fetching context...")
            self.window.update()

            # Get context
            context = get_context(include_ocr=False, include_apps=True)

            # Format and display
            formatted = self._format_context(context)

            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, formatted)

            # Update status
            perf = context.get("performance_ms", 0)
            self.status_label.config(
                text=f"Last updated: {datetime.now().strftime('%H:%M:%S')} (took {perf}ms)"
            )

        except Exception as e:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, f"Error fetching context: {e}")
            self.status_label.config(text=f"Error: {e}")

        # Schedule next refresh if auto-refresh is enabled
        if self.auto_refresh_var.get() and self.refresh_interval > 0:
            self.refresh_timer = self.window.after(self.refresh_interval, self.refresh_context)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary for display"""
        lines = []
        lines.append("=" * 70)
        lines.append("SPECTRA CONTEXT VIEWER")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {context.get('timestamp', 'N/A')}")
        lines.append(f"Performance: {context.get('performance_ms', 0)}ms")
        lines.append("")

        # System State
        lines.append("─" * 70)
        lines.append("SYSTEM STATE")
        lines.append("─" * 70)
        system = context.get("system_state", {})

        active_window = system.get("active_window")
        if active_window:
            lines.append(f"Active Window: {active_window.get('name', 'Unknown')}")
        else:
            lines.append("Active Window: None")

        apps = system.get("open_applications", [])
        lines.append(f"Open Applications: {len(apps)}")
        for app in apps[:5]:
            lines.append(f"  • {app.get('name', 'Unknown')}")
        if len(apps) > 5:
            lines.append(f"  ... and {len(apps) - 5} more")

        urls = system.get("urls", [])
        lines.append(f"Open URLs: {len(urls)}")
        for url_data in urls[:3]:
            lines.append(f"  • {url_data.get('browser')}: {url_data.get('url', '')[:60]}")
        if len(urls) > 3:
            lines.append(f"  ... and {len(urls) - 3} more")

        lines.append("")

        # Session Context
        lines.append("─" * 70)
        lines.append("SESSION CONTEXT")
        lines.append("─" * 70)
        session = context.get("session", {})
        lines.append(f"Total Actions: {session.get('total_actions', 0)}")
        lines.append(f"Duration: {session.get('session_duration_seconds', 0):.1f}s")
        lines.append(f"Last Opened App: {session.get('last_opened_app', 'None')}")
        lines.append(f"Has Copied Content: {session.get('has_copied_content', False)}")
        lines.append(f"Has Click Position: {session.get('has_click_position', False)}")
        lines.append("")

        # Memory Context
        lines.append("─" * 70)
        lines.append("MEMORY CONTEXT")
        lines.append("─" * 70)
        memory = context.get("memory", {})
        lines.append(f"Last App: {memory.get('last_app', 'None')}")
        lines.append(f"Last File: {memory.get('last_file', 'None')}")
        lines.append(f"Last URL: {memory.get('last_url', 'None')}")

        commands = memory.get("last_commands", [])
        lines.append(f"\nRecent Commands ({len(commands)}):")
        for cmd in commands:
            lines.append(f"  • {cmd.get('command', '')} ({cmd.get('intent', '')})")

        lines.append("")

        # Calendar Context
        lines.append("─" * 70)
        lines.append("CALENDAR CONTEXT")
        lines.append("─" * 70)
        calendar = context.get("calendar", {})
        if calendar.get("enabled"):
            lines.append(f"In Meeting: {calendar.get('is_in_meeting', False)}")
            current = calendar.get("current_event")
            if current:
                lines.append(f"Current Event: {current.get('title', 'N/A')}")
            next_evt = calendar.get("next_event")
            if next_evt:
                lines.append(f"Next Event: {next_evt.get('title', 'N/A')}")
        else:
            lines.append("Calendar provider disabled")

        lines.append("")

        # Email Context
        lines.append("─" * 70)
        lines.append("EMAIL CONTEXT")
        lines.append("─" * 70)
        email = context.get("email", {})
        if email.get("enabled"):
            lines.append(f"Unread Count: {email.get('unread_count', 0)}")
            lines.append(f"Has Unread: {email.get('has_unread', False)}")
            senders = email.get("recent_senders", [])
            if senders:
                lines.append(f"Recent Senders: {', '.join(senders[:3])}")
        else:
            lines.append("Email provider disabled")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off"""
        if self.auto_refresh_var.get():
            self.refresh_context()
        else:
            if self.refresh_timer:
                self.window.after_cancel(self.refresh_timer)
                self.refresh_timer = None

    def copy_to_clipboard(self):
        """Copy current context to clipboard"""
        try:
            from janus.runtime.api.context_api import get_context

            context = get_context(include_ocr=False, include_apps=True)

            # Copy as JSON
            json_str = json.dumps(context, indent=2, default=str)
            self.window.clipboard_clear()
            self.window.clipboard_append(json_str)

            self.status_label.config(text="Context copied to clipboard")
        except Exception as e:
            self.status_label.config(text=f"Error copying: {e}")

    def clear_context(self):
        """Clear context memory"""
        try:
            from tkinter import messagebox

            from janus.runtime.api.context_api import clear_context

            if messagebox.askyesno(
                "Clear Context",
                "Are you sure you want to clear the context memory?\nThis will reset session and memory data.",
            ):
                clear_context(clear_memory=True, clear_session=True, clear_persistence=False)
                self.status_label.config(text="Context cleared")
                self.refresh_context()
        except Exception as e:
            self.status_label.config(text=f"Error clearing: {e}")

    def show(self):
        """Show the context viewer window"""
        if not self.window:
            self.create_window()

        self.window.mainloop()


def show_context_viewer():
    """Convenience function to show context viewer"""
    viewer = ContextViewerUI(refresh_interval=5000)
    viewer.show()
