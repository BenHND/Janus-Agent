"""
Statistics Panel UI - Detailed usage statistics and analytics
Displays action statistics, performance metrics, and usage patterns
"""

import json
import logging
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from janus.persistence.action_history import ActionHistory

logger = logging.getLogger(__name__)


class StatsPanel:
    """
    Statistics panel showing detailed usage analytics
    Displays action statistics, performance metrics, and trends
    """

    def __init__(
        self,
        action_history: Optional[ActionHistory] = None,
        auto_refresh: bool = True,
        refresh_interval_ms: int = 5000,
    ):
        """
        Initialize statistics panel

        Args:
            action_history: ActionHistory instance
            auto_refresh: Whether to auto-refresh statistics
            refresh_interval_ms: Auto-refresh interval in milliseconds
        """
        self.action_history = action_history or ActionHistory()
        self.auto_refresh = auto_refresh
        self.refresh_interval_ms = refresh_interval_ms

        self.window: Optional[tk.Tk] = None
        self.is_showing = False
        self._refresh_job_id: Optional[str] = None

        # Current period filter
        self.period = "all"  # all, today, week, month

        # Theme
        self.theme = "light"
        self.colors = self._get_theme_colors()

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors based on current theme"""
        if self.theme == "dark":
            return {
                "bg": "#1e1e1e",
                "fg": "#d4d4d4",
                "card_bg": "#252526",
                "accent": "#0e639c",
                "success": "#4ec9b0",
                "warning": "#ce9178",
                "error": "#f48771",
            }
        else:  # light theme
            return {
                "bg": "#ffffff",
                "fg": "#000000",
                "card_bg": "#f5f5f5",
                "accent": "#0078d4",
                "success": "#107c10",
                "warning": "#ff8c00",
                "error": "#e81123",
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
        # Theme application would update colors of all widgets
        # For now, a simple placeholder
        pass

    def _create_window(self):
        """Create the statistics panel window"""
        self.window = tk.Tk()
        self.window.title("Janus - Usage Statistics")

        # Configure window size
        window_width = 900
        window_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Main container with scrollbar
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Content frame
        content_frame = ttk.Frame(scrollable_frame, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Title and controls
        self._create_header(content_frame)

        # Statistics sections
        self._create_overview_section(content_frame)
        self._create_action_types_section(content_frame)
        self._create_modules_section(content_frame)
        self._create_performance_section(content_frame)
        self._create_failures_section(content_frame)

        # Load initial stats
        self._load_statistics()

        # Start auto-refresh if enabled
        if self.auto_refresh:
            self._start_auto_refresh()

        self.is_showing = True

    def _create_header(self, parent: ttk.Frame):
        """Create header with title and controls"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Title
        title_label = ttk.Label(header_frame, text="Usage Statistics", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)

        # Period filter
        period_frame = ttk.Frame(header_frame)
        period_frame.pack(side=tk.RIGHT)

        ttk.Label(period_frame, text="Period:").pack(side=tk.LEFT, padx=(0, 5))

        self.period_var = tk.StringVar(value="all")
        period_combo = ttk.Combobox(
            period_frame,
            textvariable=self.period_var,
            values=["all", "today", "week", "month"],
            state="readonly",
            width=10,
        )
        period_combo.pack(side=tk.LEFT, padx=(0, 10))
        period_combo.bind("<<ComboboxSelected>>", lambda e: self._load_statistics())

        # Refresh button
        refresh_btn = ttk.Button(period_frame, text="Refresh", command=self._load_statistics)
        refresh_btn.pack(side=tk.LEFT)

    def _create_overview_section(self, parent: ttk.Frame):
        """Create overview statistics section"""
        section_frame = ttk.LabelFrame(parent, text="Overview", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 15))

        # Create grid for stat cards
        stats_frame = ttk.Frame(section_frame)
        stats_frame.pack(fill=tk.X)

        # Total actions
        self.total_actions_label = self._create_stat_card(stats_frame, "Total Actions", "0", 0, 0)

        # Success rate
        self.success_rate_label = self._create_stat_card(stats_frame, "Success Rate", "0%", 0, 1)

        # Avg duration
        self.avg_duration_label = self._create_stat_card(stats_frame, "Avg Duration", "0ms", 0, 2)

        # Failed actions
        self.failed_actions_label = self._create_stat_card(stats_frame, "Failed Actions", "0", 0, 3)

    def _create_stat_card(
        self, parent: ttk.Frame, label: str, value: str, row: int, col: int
    ) -> ttk.Label:
        """Create a statistics card"""
        card_frame = ttk.Frame(parent, relief=tk.RAISED, borderwidth=1, padding=10)
        card_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        parent.columnconfigure(col, weight=1)

        label_widget = ttk.Label(card_frame, text=label, font=("Arial", 9), foreground="gray")
        label_widget.pack()

        value_widget = ttk.Label(card_frame, text=value, font=("Arial", 20, "bold"))
        value_widget.pack()

        return value_widget

    def _create_action_types_section(self, parent: ttk.Frame):
        """Create action types breakdown section"""
        section_frame = ttk.LabelFrame(parent, text="Action Types", padding=15)
        section_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create treeview for action types
        columns = ("count", "percentage", "avg_duration")
        self.action_types_tree = ttk.Treeview(
            section_frame, columns=columns, show="tree headings", height=8
        )

        # Configure columns
        self.action_types_tree.heading("#0", text="Action Type")
        self.action_types_tree.heading("count", text="Count")
        self.action_types_tree.heading("percentage", text="Percentage")
        self.action_types_tree.heading("avg_duration", text="Avg Duration")

        self.action_types_tree.column("#0", width=200)
        self.action_types_tree.column("count", width=100, anchor=tk.CENTER)
        self.action_types_tree.column("percentage", width=100, anchor=tk.CENTER)
        self.action_types_tree.column("avg_duration", width=120, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            section_frame, orient=tk.VERTICAL, command=self.action_types_tree.yview
        )
        self.action_types_tree.configure(yscrollcommand=scrollbar.set)

        self.action_types_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_modules_section(self, parent: ttk.Frame):
        """Create modules usage section"""
        section_frame = ttk.LabelFrame(parent, text="Modules Usage", padding=15)
        section_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create treeview for modules
        columns = ("count", "percentage")
        self.modules_tree = ttk.Treeview(
            section_frame, columns=columns, show="tree headings", height=6
        )

        # Configure columns
        self.modules_tree.heading("#0", text="Module")
        self.modules_tree.heading("count", text="Actions")
        self.modules_tree.heading("percentage", text="Percentage")

        self.modules_tree.column("#0", width=250)
        self.modules_tree.column("count", width=120, anchor=tk.CENTER)
        self.modules_tree.column("percentage", width=120, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            section_frame, orient=tk.VERTICAL, command=self.modules_tree.yview
        )
        self.modules_tree.configure(yscrollcommand=scrollbar.set)

        self.modules_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_performance_section(self, parent: ttk.Frame):
        """Create performance metrics section"""
        section_frame = ttk.LabelFrame(parent, text="Performance Metrics", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 15))

        # Performance stats grid
        perf_frame = ttk.Frame(section_frame)
        perf_frame.pack(fill=tk.X)

        # Min duration
        self.min_duration_label = self._create_stat_card(perf_frame, "Min Duration", "0ms", 0, 0)

        # Max duration
        self.max_duration_label = self._create_stat_card(perf_frame, "Max Duration", "0ms", 0, 1)

        # Total time
        self.total_time_label = self._create_stat_card(perf_frame, "Total Time", "0s", 0, 2)

    def _create_failures_section(self, parent: ttk.Frame):
        """Create recent failures section"""
        section_frame = ttk.LabelFrame(parent, text="Recent Failures", padding=15)
        section_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview for failures
        columns = ("timestamp", "action_type", "error")
        self.failures_tree = ttk.Treeview(section_frame, columns=columns, show="headings", height=6)

        # Configure columns
        self.failures_tree.heading("timestamp", text="Timestamp")
        self.failures_tree.heading("action_type", text="Action Type")
        self.failures_tree.heading("error", text="Error")

        self.failures_tree.column("timestamp", width=180)
        self.failures_tree.column("action_type", width=150)
        self.failures_tree.column("error", width=400)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            section_frame, orient=tk.VERTICAL, command=self.failures_tree.yview
        )
        self.failures_tree.configure(yscrollcommand=scrollbar.set)

        self.failures_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _get_date_range(self) -> tuple[Optional[str], Optional[str]]:
        """Get date range based on selected period"""
        period = self.period_var.get()
        end_date = datetime.now().isoformat()

        if period == "today":
            start_date = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        elif period == "week":
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
        elif period == "month":
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        else:  # all
            start_date = None
            end_date = None

        return start_date, end_date

    def _load_statistics(self):
        """Load and display statistics"""
        try:
            start_date, end_date = self._get_date_range()
            stats = self.action_history.get_statistics(start_date, end_date)

            # Update overview
            total = stats.get("total_actions", 0)
            by_status = stats.get("by_status", {})
            success_count = by_status.get("success", 0)
            failed_count = by_status.get("failed", 0)

            self.total_actions_label.config(text=str(total))

            if total > 0:
                success_rate = (success_count / total) * 100
                self.success_rate_label.config(text=f"{success_rate:.1f}%")
            else:
                self.success_rate_label.config(text="N/A")

            avg_duration = stats.get("avg_duration_ms", 0)
            self.avg_duration_label.config(text=f"{avg_duration}ms")

            self.failed_actions_label.config(text=str(failed_count))

            # Update action types
            self._update_action_types(stats.get("by_type", {}), total)

            # Update modules
            self._update_modules(stats.get("by_module", {}), total)

            # Update performance metrics
            self._update_performance_metrics()

            # Update recent failures
            self._update_recent_failures()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load statistics: {e}")

    def _update_action_types(self, by_type: Dict[str, int], total: int):
        """Update action types treeview"""
        # Clear existing items
        for item in self.action_types_tree.get_children():
            self.action_types_tree.delete(item)

        # Add action types
        for action_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0

            # Get average duration for this action type (simplified)
            avg_duration = "N/A"

            self.action_types_tree.insert(
                "", tk.END, text=action_type, values=(count, f"{percentage:.1f}%", avg_duration)
            )

    def _update_modules(self, by_module: Dict[str, int], total: int):
        """Update modules treeview"""
        # Clear existing items
        for item in self.modules_tree.get_children():
            self.modules_tree.delete(item)

        # Add modules
        for module, count in sorted(by_module.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0

            self.modules_tree.insert(
                "", tk.END, text=module or "N/A", values=(count, f"{percentage:.1f}%")
            )

    def _update_performance_metrics(self):
        """Update performance metrics"""
        # Get history with durations
        start_date, end_date = self._get_date_range()
        history = self.action_history.get_history(
            limit=10000, start_date=start_date, end_date=end_date
        )

        durations = [h["duration_ms"] for h in history if h.get("duration_ms") is not None]

        if durations:
            self.min_duration_label.config(text=f"{min(durations)}ms")
            self.max_duration_label.config(text=f"{max(durations)}ms")
            total_time = sum(durations) / 1000  # Convert to seconds
            self.total_time_label.config(text=f"{total_time:.1f}s")
        else:
            self.min_duration_label.config(text="N/A")
            self.max_duration_label.config(text="N/A")
            self.total_time_label.config(text="N/A")

    def _update_recent_failures(self):
        """Update recent failures treeview"""
        # Clear existing items
        for item in self.failures_tree.get_children():
            self.failures_tree.delete(item)

        # Get recent failures
        failures = self.action_history.get_recent_failures(limit=20)

        for failure in failures:
            timestamp = failure.get("timestamp", "")[:19]  # Truncate to seconds
            action_type = failure.get("action_type", "unknown")
            error = failure.get("error", "No error message")[:80]  # Truncate long errors

            self.failures_tree.insert("", tk.END, values=(timestamp, action_type, error))

    def _start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self._refresh_job_id:
            self.window.after_cancel(self._refresh_job_id)

        def refresh_task():
            self._load_statistics()
            if self.auto_refresh:
                self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

        self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

    def _stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        if self._refresh_job_id:
            self.window.after_cancel(self._refresh_job_id)
            self._refresh_job_id = None

    def show(self):
        """Show the statistics panel window"""
        if self.is_showing:
            self.window.lift()
            return

        self._create_window()
        self.window.mainloop()

    def destroy(self):
        """Destroy the statistics panel window"""
        if self.window:
            self._stop_auto_refresh()
            try:
                self.window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy stats panel window: {e}")
                pass
            self.window = None
            self.is_showing = False


def show_stats_panel(action_history: Optional[ActionHistory] = None, **kwargs):
    """
    Convenience function to show statistics panel

    Args:
        action_history: Optional ActionHistory instance
        **kwargs: Additional arguments for StatsPanel
    """
    panel = StatsPanel(action_history=action_history, **kwargs)
    panel.show()
