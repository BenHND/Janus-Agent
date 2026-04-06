"""
Logs Viewer UI - Interactive log file viewer with filtering
Displays logs with search, filter by level/module, and date range selection
"""

import json
import os
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from janus.logging import get_logger
from janus.utils.paths import get_log_dir

logger = get_logger("logs_viewer")


class LogsViewer:
    """
    Interactive logs viewer with filtering and search capabilities
    Displays Janus logs with real-time updates and advanced filtering
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        auto_refresh: bool = True,
        refresh_interval_ms: int = 2000,
    ):
        """
        Initialize logs viewer

        Args:
            log_dir: Directory containing log files (default: platform-specific log directory)
            auto_refresh: Whether to auto-refresh logs
            refresh_interval_ms: Auto-refresh interval in milliseconds
        """
        if log_dir is None:
            # Use cross-platform log directory
            log_dir = get_log_dir()

        self.log_dir = Path(log_dir)
        self.auto_refresh = auto_refresh
        self.refresh_interval_ms = refresh_interval_ms

        self.window: Optional[tk.Tk] = None
        self.is_showing = False
        self._refresh_job_id: Optional[str] = None

        # Current filters
        self.filter_level: Optional[str] = None
        self.filter_module: Optional[str] = None
        self.filter_text: str = ""
        self.filter_start_date: Optional[datetime] = None
        self.filter_end_date: Optional[datetime] = None

        # Log entries cache
        self.log_entries: List[Dict[str, Any]] = []
        self.filtered_entries: List[Dict[str, Any]] = []

        # Available levels and modules
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_modules: List[str] = []

        # Theme colors
        self.theme = "light"
        self.colors = self._get_theme_colors()

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors based on current theme"""
        if self.theme == "dark":
            return {
                "bg": "#1e1e1e",
                "fg": "#d4d4d4",
                "select_bg": "#264f78",
                "select_fg": "#ffffff",
                "debug": "#858585",
                "info": "#4ec9b0",
                "warning": "#ce9178",
                "error": "#f48771",
                "critical": "#f14c4c",
            }
        else:  # light theme
            return {
                "bg": "#ffffff",
                "fg": "#000000",
                "select_bg": "#0078d4",
                "select_fg": "#ffffff",
                "debug": "#808080",
                "info": "#0000ff",
                "warning": "#ff8c00",
                "error": "#ff0000",
                "critical": "#8b0000",
            }

    def set_theme(self, theme: str):
        """
        Set UI theme

        Args:
            theme: Theme name ("light" or "dark")
        """
        self.theme = theme
        self.colors = self._get_theme_colors()
        if self.window:
            self._apply_theme()

    def _apply_theme(self):
        """Apply theme to UI components"""
        if not self.window:
            return

        # Update text widget colors
        self.log_text.config(
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            selectbackground=self.colors["select_bg"],
            selectforeground=self.colors["select_fg"],
        )

        # Re-apply log level tags
        for level in self.log_levels:
            self.log_text.tag_config(level.lower(), foreground=self.colors[level.lower()])

    def _create_window(self):
        """Create the logs viewer window"""
        self.window = tk.Tk()
        self.window.title("Janus - Logs Viewer")

        # Configure window size
        window_width = 1000
        window_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Main container
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(title_frame, text="Logs Viewer", font=("Arial", 14, "bold"))
        title_label.pack(side=tk.LEFT)

        # Theme toggle button
        theme_button = ttk.Button(
            title_frame,
            text="🌙 Dark" if self.theme == "light" else "☀️ Light",
            command=self._toggle_theme,
        )
        theme_button.pack(side=tk.RIGHT)

        # Filter section
        self._create_filter_section(main_container)

        # Log display section
        self._create_log_display(main_container)

        # Status bar
        self._create_status_bar(main_container)

        # Load logs
        self._load_logs()

        # Start auto-refresh if enabled
        if self.auto_refresh:
            self._start_auto_refresh()

        self.is_showing = True

    def _create_filter_section(self, parent: ttk.Frame):
        """Create filter controls section"""
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # First row: Level and Module filters
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=(0, 5))

        # Level filter
        ttk.Label(row1, text="Level:").pack(side=tk.LEFT, padx=(0, 5))
        self.level_var = tk.StringVar(value="All")
        level_combo = ttk.Combobox(
            row1,
            textvariable=self.level_var,
            values=["All"] + self.log_levels,
            state="readonly",
            width=12,
        )
        level_combo.pack(side=tk.LEFT, padx=(0, 15))
        level_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Module filter
        ttk.Label(row1, text="Module:").pack(side=tk.LEFT, padx=(0, 5))
        self.module_var = tk.StringVar(value="All")
        self.module_combo = ttk.Combobox(
            row1, textvariable=self.module_var, values=["All"], state="readonly", width=20
        )
        self.module_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.module_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Clear filters button
        clear_btn = ttk.Button(row1, text="Clear Filters", command=self._clear_filters)
        clear_btn.pack(side=tk.RIGHT)

        # Export button
        export_btn = ttk.Button(row1, text="Export Logs", command=self._export_logs)
        export_btn.pack(side=tk.RIGHT, padx=(0, 5))

        # Second row: Text search
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(row2, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<Return>", lambda e: self._apply_filters())

        search_btn = ttk.Button(row2, text="Search", command=self._apply_filters)
        search_btn.pack(side=tk.LEFT, padx=(5, 0))

    def _create_log_display(self, parent: ttk.Frame):
        """Create log display area"""
        display_frame = ttk.Frame(parent)
        display_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(display_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget for logs
        self.log_text = tk.Text(
            display_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            selectbackground=self.colors["select_bg"],
            selectforeground=self.colors["select_fg"],
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Configure tags for log levels
        for level in self.log_levels:
            self.log_text.tag_config(level.lower(), foreground=self.colors[level.lower()])

        # Make text read-only
        self.log_text.config(state=tk.DISABLED)

    def _create_status_bar(self, parent: ttk.Frame):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=self.auto_refresh)
        auto_refresh_check = ttk.Checkbutton(
            status_frame,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
        )
        auto_refresh_check.pack(side=tk.RIGHT, padx=(5, 0))

        # Refresh button
        refresh_btn = ttk.Button(status_frame, text="Refresh", command=self._load_logs)
        refresh_btn.pack(side=tk.RIGHT)

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()

        # Update theme button text
        for widget in self.window.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):
                        for btn in child.winfo_children():
                            if isinstance(btn, ttk.Button) and (
                                "Dark" in btn.cget("text") or "Light" in btn.cget("text")
                            ):
                                btn.config(text="🌙 Dark" if self.theme == "light" else "☀️ Light")

    def _toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        self.auto_refresh = self.auto_refresh_var.get()
        if self.auto_refresh:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self._refresh_job_id:
            self.window.after_cancel(self._refresh_job_id)

        def refresh_task():
            self._load_logs()
            if self.auto_refresh:
                self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

        self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

    def _stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        if self._refresh_job_id:
            self.window.after_cancel(self._refresh_job_id)
            self._refresh_job_id = None

    def _load_logs(self):
        """Load logs from files"""
        self.log_entries = []
        self.log_modules = []

        if not self.log_dir.exists():
            self._update_status(f"Log directory not found: {self.log_dir}")
            return

        # Find log files
        log_files = list(self.log_dir.glob("*.log")) + list(self.log_dir.glob("*.json"))

        if not log_files:
            self._update_status("No log files found")
            return

        # Load and parse log files
        for log_file in sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        # Try to parse as JSON first
                        try:
                            entry = json.loads(line)
                            if "level" not in entry and "levelname" in entry:
                                entry["level"] = entry["levelname"]
                            if "timestamp" not in entry and "created" in entry:
                                entry["timestamp"] = datetime.fromtimestamp(
                                    entry["created"]
                                ).isoformat()
                        except json.JSONDecodeError:
                            # Parse as plain text log
                            entry = self._parse_text_log_line(line)

                        if entry:
                            entry["file"] = log_file.name
                            entry["line_num"] = line_num
                            self.log_entries.append(entry)

                            # Track modules
                            module = entry.get("module", entry.get("logger", "unknown"))
                            if module and module not in self.log_modules:
                                self.log_modules.append(module)

            except Exception as e:
                logger.error(f"Error loading log file {log_file}: {e}", exc_info=True)

        # Update module filter options
        self.module_combo["values"] = ["All"] + sorted(self.log_modules)

        # Apply filters and display
        self._apply_filters()
        self._update_status(
            f"Loaded {len(self.log_entries)} log entries from {len(log_files)} files"
        )

    def _parse_text_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a plain text log line"""
        # Try to extract timestamp, level, and message
        # Format: YYYY-MM-DD HH:MM:SS LEVEL module - message
        parts = line.split(None, 4)
        if len(parts) >= 4:
            try:
                timestamp = f"{parts[0]} {parts[1]}"
                level = parts[2]
                module = parts[3] if len(parts) > 3 else "unknown"
                message = parts[4] if len(parts) > 4 else ""

                return {
                    "timestamp": timestamp,
                    "level": level,
                    "module": module,
                    "message": message,
                }
            except Exception as e:
                logger.debug(f"Failed to parse log line format: {e}")

        # Fallback: treat entire line as message
        return {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "module": "unknown",
            "message": line,
        }

    def _apply_filters(self):
        """Apply current filters to log entries"""
        self.filter_level = None if self.level_var.get() == "All" else self.level_var.get()
        self.filter_module = None if self.module_var.get() == "All" else self.module_var.get()
        self.filter_text = self.search_var.get().lower()

        # Filter entries
        self.filtered_entries = []
        for entry in self.log_entries:
            # Level filter
            if self.filter_level and entry.get("level") != self.filter_level:
                continue

            # Module filter
            module = entry.get("module", entry.get("logger", ""))
            if self.filter_module and module != self.filter_module:
                continue

            # Text search
            if self.filter_text:
                message = entry.get("message", "").lower()
                if self.filter_text not in message:
                    continue

            self.filtered_entries.append(entry)

        # Display filtered entries
        self._display_logs()

    def _display_logs(self):
        """Display filtered log entries"""
        # Clear text widget
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)

        # Display entries
        for entry in self.filtered_entries[-1000:]:  # Limit to last 1000 entries
            timestamp = entry.get("timestamp", "")
            level = entry.get("level", "INFO")
            module = entry.get("module", entry.get("logger", "unknown"))
            message = entry.get("message", "")

            # Format log line
            log_line = f"[{timestamp}] {level:8s} {module:20s} - {message}\n"

            # Insert with level-specific tag
            self.log_text.insert(tk.END, log_line, level.lower())

        # Make read-only again
        self.log_text.config(state=tk.DISABLED)

        # Auto-scroll to bottom
        self.log_text.see(tk.END)

        # Update status
        total = len(self.log_entries)
        filtered = len(self.filtered_entries)
        if filtered < total:
            self._update_status(f"Showing {filtered} of {total} log entries")
        else:
            self._update_status(f"Showing {total} log entries")

    def _clear_filters(self):
        """Clear all filters"""
        self.level_var.set("All")
        self.module_var.set("All")
        self.search_var.set("")
        self._apply_filters()

    def _export_logs(self):
        """Export filtered logs to file"""
        if not self.filtered_entries:
            messagebox.showwarning("No Logs", "No logs to export")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")],
        )

        if filename:
            try:
                if filename.endswith(".json"):
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(self.filtered_entries, f, indent=2, ensure_ascii=False)
                else:
                    with open(filename, "w", encoding="utf-8") as f:
                        for entry in self.filtered_entries:
                            timestamp = entry.get("timestamp", "")
                            level = entry.get("level", "INFO")
                            module = entry.get("module", "unknown")
                            message = entry.get("message", "")
                            f.write(f"[{timestamp}] {level:8s} {module:20s} - {message}\n")

                messagebox.showinfo(
                    "Success", f"Exported {len(self.filtered_entries)} log entries to {filename}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {e}")

    def _update_status(self, message: str):
        """Update status bar message"""
        if self.status_label:
            self.status_label.config(text=message)

    def show(self):
        """Show the logs viewer window"""
        if self.is_showing:
            self.window.lift()
            return

        self._create_window()
        self.window.mainloop()

    def destroy(self):
        """Destroy the logs viewer window"""
        if self.window:
            self._stop_auto_refresh()
            try:
                self.window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy logs viewer window: {e}")
                pass
            self.window = None
            self.is_showing = False


def show_logs_viewer(log_dir: Optional[str] = None, **kwargs):
    """
    Convenience function to show logs viewer

    Args:
        log_dir: Optional log directory path
        **kwargs: Additional arguments for LogsViewer
    """
    viewer = LogsViewer(log_dir=log_dir, **kwargs)
    viewer.show()
