"""
Learning Dashboard UI - Visualize and manage learned corrections
Interactive UI for monitoring learning progress and managing heuristics
"""

import json
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from janus.learning.learning_manager import LearningManager
from janus.logging import get_logger


class LearningDashboard:
    """
    Interactive dashboard for learning system
    Displays performance metrics, corrections, and heuristics
    """

    def __init__(
        self,
        learning_manager: Optional[LearningManager] = None,
        auto_refresh: bool = True,
        refresh_interval_ms: int = 5000,
    ):
        """
        Initialize learning dashboard

        Args:
            learning_manager: LearningManager instance
            auto_refresh: Whether to auto-refresh metrics
            refresh_interval_ms: Auto-refresh interval in milliseconds
        """
        self.logger = get_logger("learning_dashboard")
        self.learning_manager = learning_manager or LearningManager()
        self.auto_refresh = auto_refresh
        self.refresh_interval_ms = refresh_interval_ms

        self.window: Optional[tk.Tk] = None
        self.is_showing = False
        self._refresh_job_id: Optional[str] = None

    def show(self):
        """Show the learning dashboard"""
        if self.is_showing:
            self.window.lift()
            return

        self._create_window()
        self._create_widgets()
        self._load_data()

        if self.auto_refresh:
            self._schedule_refresh()

        self.is_showing = True
        self.window.mainloop()

    def hide(self):
        """Hide the learning dashboard"""
        if self.window:
            if self._refresh_job_id:
                self.window.after_cancel(self._refresh_job_id)
            self.window.withdraw()
            self.is_showing = False

    def close(self):
        """Close the learning dashboard"""
        if self.window:
            if self._refresh_job_id:
                self.window.after_cancel(self._refresh_job_id)
            self.window.destroy()
            self.window = None
            self.is_showing = False

    def _create_window(self):
        """Create the main dashboard window"""
        self.window = tk.Tk()
        self.window.title("Janus Learning Dashboard")
        self.window.geometry("900x700")

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # Configure grid weights
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

    def _create_widgets(self):
        """Create dashboard widgets"""
        # Header
        header_frame = ttk.Frame(self.window, padding=10)
        header_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(header_frame, text="Learning Dashboard", font=("Arial", 16, "bold")).pack(
            side=tk.LEFT
        )

        ttk.Button(header_frame, text="Refresh", command=self._load_data).pack(
            side=tk.RIGHT, padx=5
        )

        ttk.Button(header_frame, text="Export", command=self._export_data).pack(
            side=tk.RIGHT, padx=5
        )

        ttk.Button(header_frame, text="Import", command=self._import_data).pack(
            side=tk.RIGHT, padx=5
        )

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        self._create_overview_tab()
        self._create_corrections_tab()
        self._create_heuristics_tab()
        self._create_performance_tab()
        self._create_errors_tab()

    def _create_overview_tab(self):
        """Create overview tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Overview")

        # Status section
        status_frame = ttk.LabelFrame(tab, text="Learning Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.status_text = tk.Text(
            status_frame, height=15, width=80, font=("Courier", 10), wrap=tk.WORD
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)

        # Make text read-only
        self.status_text.config(state=tk.DISABLED)

        # Quick stats section
        stats_frame = ttk.LabelFrame(tab, text="Quick Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.stats_labels = {}
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.BOTH, expand=True)

        # Configure grid
        for i in range(3):
            stats_grid.grid_columnconfigure(i, weight=1)

        # Create stat labels
        stat_names = [
            "Total Actions",
            "Total Corrections",
            "Learning Updates",
            "Success Rate",
            "Active Heuristics",
            "Session Active",
        ]

        for idx, name in enumerate(stat_names):
            row = idx // 3
            col = idx % 3

            frame = ttk.Frame(stats_grid)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

            ttk.Label(frame, text=name + ":", font=("Arial", 10, "bold")).pack(anchor=tk.W)

            value_label = ttk.Label(frame, text="--", font=("Arial", 12))
            value_label.pack(anchor=tk.W)

            self.stats_labels[name] = value_label

    def _create_corrections_tab(self):
        """Create corrections tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Corrections")

        # Summary section
        summary_frame = ttk.LabelFrame(tab, text="Corrections Summary", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        self.corrections_summary_text = tk.Text(summary_frame, height=6, font=("Courier", 10))
        self.corrections_summary_text.pack(fill=tk.X)
        self.corrections_summary_text.config(state=tk.DISABLED)

        # Corrections list
        list_frame = ttk.LabelFrame(tab, text="Recent Corrections", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create treeview for corrections
        columns = ("Timestamp", "Action Type", "Context")
        self.corrections_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )

        for col in columns:
            self.corrections_tree.heading(col, text=col)
            self.corrections_tree.column(col, width=200)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.corrections_tree.yview
        )
        self.corrections_tree.configure(yscrollcommand=scrollbar.set)

        self.corrections_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_heuristics_tab(self):
        """Create heuristics tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Heuristics")

        # Controls
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(controls_frame, text="Update Heuristics", command=self._update_heuristics).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(controls_frame, text="Days:").pack(side=tk.LEFT, padx=5)

        self.heuristic_days_var = tk.StringVar(value="7")
        ttk.Entry(controls_frame, textvariable=self.heuristic_days_var, width=10).pack(side=tk.LEFT)

        # Heuristics display
        display_frame = ttk.LabelFrame(tab, text="Current Heuristics", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook for heuristic categories
        self.heuristics_notebook = ttk.Notebook(display_frame)
        self.heuristics_notebook.pack(fill=tk.BOTH, expand=True)

        # Wait times tab
        self.wait_times_text = self._create_heuristic_category_tab("Wait Times")

        # Retry counts tab
        self.retry_counts_text = self._create_heuristic_category_tab("Retry Counts")

        # Success probabilities tab
        self.success_prob_text = self._create_heuristic_category_tab("Success Probabilities")

    def _create_heuristic_category_tab(self, title: str) -> tk.Text:
        """Create a tab for a heuristic category"""
        tab = ttk.Frame(self.heuristics_notebook)
        self.heuristics_notebook.add(tab, text=title)

        text_widget = tk.Text(tab, font=("Courier", 10), wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.config(state=tk.DISABLED)

        return text_widget

    def _create_performance_tab(self):
        """Create performance tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Performance")

        # Time range selector
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(controls_frame, text="Days to analyze:").pack(side=tk.LEFT, padx=5)

        self.perf_days_var = tk.StringVar(value="30")
        ttk.Entry(controls_frame, textvariable=self.perf_days_var, width=10).pack(side=tk.LEFT)

        ttk.Button(controls_frame, text="Refresh", command=self._load_performance_data).pack(
            side=tk.LEFT, padx=10
        )

        # Performance metrics
        metrics_frame = ttk.LabelFrame(tab, text="Performance Metrics", padding=10)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.performance_text = tk.Text(metrics_frame, font=("Courier", 10), wrap=tk.WORD)
        self.performance_text.pack(fill=tk.BOTH, expand=True)
        self.performance_text.config(state=tk.DISABLED)

    def _create_errors_tab(self):
        """Create recurring errors tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Errors")

        # Controls
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(controls_frame, text="Min occurrences:").pack(side=tk.LEFT, padx=5)

        self.error_min_var = tk.StringVar(value="3")
        ttk.Entry(controls_frame, textvariable=self.error_min_var, width=10).pack(side=tk.LEFT)

        ttk.Button(controls_frame, text="Refresh", command=self._load_errors_data).pack(
            side=tk.LEFT, padx=10
        )

        # Errors list
        list_frame = ttk.LabelFrame(tab, text="Recurring Errors", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("Action Type", "Error Type", "Count", "Last Occurrence")
        self.errors_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.errors_tree.heading(col, text=col)
            self.errors_tree.column(col, width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.errors_tree.yview)
        self.errors_tree.configure(yscrollcommand=scrollbar.set)

        self.errors_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_data(self):
        """Load all dashboard data"""
        self._load_status_data()
        self._load_corrections_data()
        self._load_heuristics_data()
        self._load_performance_data()
        self._load_errors_data()

    def _load_status_data(self):
        """Load learning status data"""
        try:
            status = self.learning_manager.get_learning_status()

            # Update status text
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete(1.0, tk.END)

            status_lines = [
                f"Profile: {status.get('profile', 'N/A')}",
                f"Session Active: {status.get('session_active', False)}",
                f"Current Session: {status.get('current_session_id', 'None')}",
                f"",
                f"Total Actions: {status.get('total_actions', 0)}",
                f"Total Corrections: {status.get('total_corrections', 0)}",
                f"Learning Updates: {status.get('learning_updates', 0)}",
                f"Heuristics Count: {status.get('heuristics_count', 0)}",
                f"",
                f"Auto-Update: {'Enabled' if status.get('auto_update_enabled') else 'Disabled'}",
                f"Last Update: {status.get('last_heuristic_update', 'Never')}",
                f"Hours Since Update: {status.get('hours_since_last_update', 0):.1f}",
            ]

            self.status_text.insert(1.0, "\n".join(status_lines))
            self.status_text.config(state=tk.DISABLED)

            # Update quick stats
            success_rate = self.learning_manager.get_success_rate()

            self.stats_labels["Total Actions"].config(text=f"{status.get('total_actions', 0):,}")
            self.stats_labels["Total Corrections"].config(
                text=f"{status.get('total_corrections', 0):,}"
            )
            self.stats_labels["Learning Updates"].config(
                text=f"{status.get('learning_updates', 0):,}"
            )
            self.stats_labels["Success Rate"].config(text=f"{success_rate:.1f}%")
            self.stats_labels["Active Heuristics"].config(
                text=f"{status.get('heuristics_count', 0)}"
            )
            self.stats_labels["Session Active"].config(
                text="Yes" if status.get("session_active") else "No"
            )

        except Exception as e:
            self.logger.error(f"Error loading status data: {e}", exc_info=True)

    def _load_corrections_data(self):
        """Load corrections data"""
        try:
            summary = self.learning_manager.get_correction_summary()

            # Update summary
            self.corrections_summary_text.config(state=tk.NORMAL)
            self.corrections_summary_text.delete(1.0, tk.END)

            summary_lines = [
                f"Total Corrections: {summary.get('total_corrections', 0)}",
                f"Period: {summary.get('period_days', 0)} days",
                f"Patterns Tracked: {summary.get('patterns_tracked', 0)}",
                f"Preferences Tracked: {summary.get('preferences_tracked', 0)}",
                f"",
                f"By Type: {json.dumps(summary.get('corrections_by_type', {}), indent=2)}",
            ]

            self.corrections_summary_text.insert(1.0, "\n".join(summary_lines))
            self.corrections_summary_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Error loading corrections data: {e}", exc_info=True)

    def _load_heuristics_data(self):
        """Load heuristics data"""
        try:
            heuristics = self.learning_manager.heuristic_updater.get_heuristics_summary()

            # Update wait times
            self._update_text_widget(
                self.wait_times_text, json.dumps(heuristics.get("wait_times", {}), indent=2)
            )

            # Update retry counts
            self._update_text_widget(
                self.retry_counts_text, json.dumps(heuristics.get("retry_counts", {}), indent=2)
            )

            # Update success probabilities
            self._update_text_widget(
                self.success_prob_text,
                json.dumps(heuristics.get("success_probabilities", {}), indent=2),
            )

        except Exception as e:
            self.logger.error(f"Error loading heuristics data: {e}", exc_info=True)

    def _load_performance_data(self):
        """Load performance data"""
        try:
            days = int(self.perf_days_var.get())
            performance = self.learning_manager.get_performance_summary(days)

            self.performance_text.config(state=tk.NORMAL)
            self.performance_text.delete(1.0, tk.END)

            # Format performance data
            perf_text = json.dumps(performance, indent=2, ensure_ascii=False)
            self.performance_text.insert(1.0, perf_text)
            self.performance_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Error loading performance data: {e}", exc_info=True)

    def _load_errors_data(self):
        """Load recurring errors data"""
        try:
            min_occurrences = int(self.error_min_var.get())
            errors = self.learning_manager.get_recurring_errors(min_occurrences=min_occurrences)

            # Clear existing items
            for item in self.errors_tree.get_children():
                self.errors_tree.delete(item)

            # Add errors
            for error in errors:
                self.errors_tree.insert(
                    "",
                    tk.END,
                    values=(
                        error.get("action_type", ""),
                        error.get("error_type", ""),
                        error.get("occurrence_count", 0),
                        error.get("last_occurrence", ""),
                    ),
                )

        except Exception as e:
            self.logger.error(f"Error loading errors data: {e}", exc_info=True)

    def _update_text_widget(self, widget: tk.Text, text: str):
        """Update a text widget with new content"""
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(1.0, text)
        widget.config(state=tk.DISABLED)

    def _update_heuristics(self):
        """Manually update heuristics"""
        try:
            days = int(self.heuristic_days_var.get())
            updates = self.learning_manager.update_all_heuristics(days)

            messagebox.showinfo(
                "Heuristics Updated",
                f"Successfully updated heuristics using {days} days of data.\n\n"
                f"Updates applied: {len(updates)}",
            )

            self._load_heuristics_data()

        except Exception as e:
            messagebox.showerror("Update Error", f"Error updating heuristics: {e}")

    def _export_data(self):
        """Export learning data to file"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Learning Data",
            )

            if file_path:
                success = self.learning_manager.export_heuristics(file_path)
                if success:
                    messagebox.showinfo(
                        "Export Successful", f"Learning data exported to:\n{file_path}"
                    )
                else:
                    messagebox.showerror("Export Failed", "Failed to export learning data")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting data: {e}")

    def _import_data(self):
        """Import learning data from file"""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Learning Data",
            )

            if file_path:
                success = self.learning_manager.import_heuristics(file_path)
                if success:
                    messagebox.showinfo(
                        "Import Successful", f"Learning data imported from:\n{file_path}"
                    )
                    self._load_data()  # Refresh display
                else:
                    messagebox.showerror("Import Failed", "Failed to import learning data")
        except Exception as e:
            messagebox.showerror("Import Error", f"Error importing data: {e}")

    def _schedule_refresh(self):
        """Schedule automatic refresh"""
        if self.window and self.auto_refresh:
            self._load_data()
            self._refresh_job_id = self.window.after(
                self.refresh_interval_ms, self._schedule_refresh
            )


def launch_learning_dashboard(learning_manager: Optional[LearningManager] = None):
    """
    Convenience function to launch the learning dashboard

    Args:
        learning_manager: Optional LearningManager instance
    """
    dashboard = LearningDashboard(learning_manager)
    dashboard.show()
