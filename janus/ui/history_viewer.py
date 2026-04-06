"""
Action History Viewer UI - Interactive action history browser
Displays action history with search, filtering, timeline view, and export capabilities
"""

import csv
import json
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from janus.logging import get_logger
from janus.persistence.action_history import ActionHistory

logger = get_logger("history_viewer")


class HistoryViewer:
    """
    Interactive action history viewer with filtering and export capabilities
    Displays action history with timeline view and advanced filtering
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        auto_refresh: bool = True,
        refresh_interval_ms: int = 3000,
    ):
        """
        Initialize history viewer

        Args:
            db_path: Path to history database (default: janus_data.db)
            auto_refresh: Whether to auto-refresh history
            refresh_interval_ms: Auto-refresh interval in milliseconds
        """
        if db_path is None:
            db_path = "janus_data.db"

        self.db_path = db_path
        self.auto_refresh = auto_refresh
        self.refresh_interval_ms = refresh_interval_ms

        self.window: Optional[tk.Tk] = None
        self.is_showing = False
        self._refresh_job_id: Optional[str] = None

        # Action history manager
        self.history = ActionHistory(db_path=self.db_path)

        # Current filters
        self.filter_type: Optional[str] = None
        self.filter_status: Optional[str] = None
        self.filter_module: Optional[str] = None
        self.filter_text: str = ""
        self.filter_start_date: Optional[str] = None
        self.filter_end_date: Optional[str] = None

        # Action entries cache
        self.action_entries: List[Dict[str, Any]] = []
        self.filtered_entries: List[Dict[str, Any]] = []

        # Available types, statuses, and modules
        self.action_types: List[str] = []
        self.action_statuses: List[str] = []
        self.action_modules: List[str] = []

        # Theme colors
        self.theme = "light"
        self.colors = self._get_theme_colors()

        # View mode: list or timeline
        self.view_mode = "list"

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors based on current theme"""
        if self.theme == "dark":
            return {
                "bg": "#1e1e1e",
                "fg": "#d4d4d4",
                "select_bg": "#264f78",
                "select_fg": "#ffffff",
                "success": "#4ec9b0",
                "failed": "#f48771",
                "pending": "#dcdcaa",
                "header": "#569cd6",
            }
        else:  # light theme
            return {
                "bg": "#ffffff",
                "fg": "#000000",
                "select_bg": "#0078d4",
                "select_fg": "#ffffff",
                "success": "#008000",
                "failed": "#ff0000",
                "pending": "#ff8c00",
                "header": "#0000ff",
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

        # Update text/tree widget colors
        if hasattr(self, "history_tree"):
            self.history_tree.config(
                background=self.colors["bg"],
                foreground=self.colors["fg"],
                selectbackground=self.colors["select_bg"],
                selectforeground=self.colors["select_fg"],
            )

        if hasattr(self, "details_text"):
            self.details_text.config(
                bg=self.colors["bg"],
                fg=self.colors["fg"],
                selectbackground=self.colors["select_bg"],
                selectforeground=self.colors["select_fg"],
            )

    def _create_window(self):
        """Create the history viewer window"""
        self.window = tk.Tk()
        self.window.title("Janus - Action History Viewer")

        # Configure window size
        window_width = 1200
        window_height = 800
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Main container
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title bar
        self._create_title_bar(main_container)

        # Filter section
        self._create_filter_section(main_container)

        # Content area with paned window (list + details)
        self._create_content_area(main_container)

        # Status bar
        self._create_status_bar(main_container)

        # Load history
        self._load_history()

        # Start auto-refresh if enabled
        if self.auto_refresh:
            self._start_auto_refresh()

        self.is_showing = True

    def _create_title_bar(self, parent: ttk.Frame):
        """Create title bar with buttons"""
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(
            title_frame, text="Action History Viewer", font=("Arial", 14, "bold")
        )
        title_label.pack(side=tk.LEFT)

        # View mode toggle
        view_mode_frame = ttk.Frame(title_frame)
        view_mode_frame.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Label(view_mode_frame, text="View:").pack(side=tk.LEFT, padx=(0, 5))

        self.view_mode_var = tk.StringVar(value="list")
        list_radio = ttk.Radiobutton(
            view_mode_frame,
            text="List",
            variable=self.view_mode_var,
            value="list",
            command=self._change_view_mode,
        )
        list_radio.pack(side=tk.LEFT, padx=2)

        timeline_radio = ttk.Radiobutton(
            view_mode_frame,
            text="Timeline",
            variable=self.view_mode_var,
            value="timeline",
            command=self._change_view_mode,
        )
        timeline_radio.pack(side=tk.LEFT, padx=2)

        # Theme toggle button
        theme_button = ttk.Button(
            title_frame,
            text="🌙 Dark" if self.theme == "light" else "☀️ Light",
            command=self._toggle_theme,
        )
        theme_button.pack(side=tk.RIGHT)

    def _create_filter_section(self, parent: ttk.Frame):
        """Create filter controls section"""
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # First row: Type, Status, Module filters
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=(0, 5))

        # Action type filter
        ttk.Label(row1, text="Type:").pack(side=tk.LEFT, padx=(0, 5))
        self.type_var = tk.StringVar(value="All")
        self.type_combo = ttk.Combobox(
            row1, textvariable=self.type_var, values=["All"], state="readonly", width=15
        )
        self.type_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Status filter
        ttk.Label(row1, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        self.status_var = tk.StringVar(value="All")
        self.status_combo = ttk.Combobox(
            row1,
            textvariable=self.status_var,
            values=["All", "success", "failed", "pending"],
            state="readonly",
            width=12,
        )
        self.status_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Module filter
        ttk.Label(row1, text="Module:").pack(side=tk.LEFT, padx=(0, 5))
        self.module_var = tk.StringVar(value="All")
        self.module_combo = ttk.Combobox(
            row1, textvariable=self.module_var, values=["All"], state="readonly", width=15
        )
        self.module_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.module_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Clear filters button
        clear_btn = ttk.Button(row1, text="Clear Filters", command=self._clear_filters)
        clear_btn.pack(side=tk.RIGHT)

        # Export buttons
        export_frame = ttk.Frame(row1)
        export_frame.pack(side=tk.RIGHT, padx=(0, 5))

        ttk.Button(
            export_frame, text="Export CSV", command=lambda: self._export_history("csv")
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            export_frame, text="Export JSON", command=lambda: self._export_history("json")
        ).pack(side=tk.LEFT, padx=2)

        # Second row: Text search and date range
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(row2, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self._apply_filters())

        search_btn = ttk.Button(row2, text="Search", command=self._apply_filters)
        search_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Date range (simple text for now)
        ttk.Label(row2, text="Date Range:").pack(side=tk.LEFT, padx=(0, 5))

        date_options = ["All Time", "Today", "Last 7 Days", "Last 30 Days"]
        self.date_range_var = tk.StringVar(value="All Time")
        date_combo = ttk.Combobox(
            row2, textvariable=self.date_range_var, values=date_options, state="readonly", width=15
        )
        date_combo.pack(side=tk.LEFT)
        date_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_date_filter())

    def _create_content_area(self, parent: ttk.Frame):
        """Create content area with history list and details pane"""
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left pane: History list
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=2)

        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(list_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        tree_scroll_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview for actions
        columns = ("timestamp", "type", "status", "module", "duration")
        self.history_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            selectmode="browse",
        )

        # Configure columns
        self.history_tree.heading("timestamp", text="Timestamp")
        self.history_tree.heading("type", text="Action Type")
        self.history_tree.heading("status", text="Status")
        self.history_tree.heading("module", text="Module")
        self.history_tree.heading("duration", text="Duration (ms)")

        self.history_tree.column("timestamp", width=150)
        self.history_tree.column("type", width=120)
        self.history_tree.column("status", width=80)
        self.history_tree.column("module", width=100)
        self.history_tree.column("duration", width=100)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tree_scroll_y.config(command=self.history_tree.yview)
        tree_scroll_x.config(command=self.history_tree.xview)

        # Bind selection event
        self.history_tree.bind("<<TreeviewSelect>>", self._on_action_selected)

        # Right pane: Details view
        details_frame = ttk.LabelFrame(paned, text="Action Details", padding=10)
        paned.add(details_frame, weight=1)

        # Scrolled text for details
        details_scroll = ttk.Scrollbar(details_frame)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.details_text = tk.Text(
            details_frame,
            wrap=tk.WORD,
            yscrollcommand=details_scroll.set,
            font=("Courier", 10),
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            selectbackground=self.colors["select_bg"],
            selectforeground=self.colors["select_fg"],
        )
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.config(command=self.details_text.yview)

        # Make text read-only
        self.details_text.config(state=tk.DISABLED)

    def _create_status_bar(self, parent: ttk.Frame):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Statistics label
        self.stats_label = ttk.Label(status_frame, text="", relief=tk.SUNKEN, anchor=tk.E)
        self.stats_label.pack(side=tk.RIGHT, padx=(5, 0))

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
        refresh_btn = ttk.Button(status_frame, text="Refresh", command=self._load_history)
        refresh_btn.pack(side=tk.RIGHT)

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()

    def _change_view_mode(self):
        """Change view mode between list and timeline"""
        self.view_mode = self.view_mode_var.get()
        self._display_history()

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
            self._load_history()
            if self.auto_refresh:
                self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

        self._refresh_job_id = self.window.after(self.refresh_interval_ms, refresh_task)

    def _stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        if self._refresh_job_id:
            self.window.after_cancel(self._refresh_job_id)
            self._refresh_job_id = None

    def _load_history(self):
        """Load action history from database"""
        try:
            # Get all actions
            self.action_entries = self.history.get_history(limit=10000)

            # Extract unique types, statuses, and modules
            types_set = set()
            statuses_set = set()
            modules_set = set()

            for entry in self.action_entries:
                types_set.add(entry.get("action_type", "unknown"))
                statuses_set.add(entry.get("status", "unknown"))
                module = entry.get("module")
                if module:
                    modules_set.add(module)

            self.action_types = sorted(list(types_set))
            self.action_statuses = sorted(list(statuses_set))
            self.action_modules = sorted(list(modules_set))

            # Update filter combo boxes
            self.type_combo["values"] = ["All"] + self.action_types
            self.status_combo["values"] = ["All"] + self.action_statuses
            self.module_combo["values"] = ["All"] + self.action_modules

            # Apply filters and display
            self._apply_filters()

            # Update status
            self._update_status(f"Loaded {len(self.action_entries)} actions")
            self._update_statistics()

        except Exception as e:
            logger.error(f"Error loading history: {e}", exc_info=True)
            self._update_status(f"Error loading history: {e}")

    def _apply_date_filter(self):
        """Apply date range filter"""
        date_range = self.date_range_var.get()
        now = datetime.now()

        if date_range == "All Time":
            self.filter_start_date = None
            self.filter_end_date = None
        elif date_range == "Today":
            self.filter_start_date = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            self.filter_end_date = None
        elif date_range == "Last 7 Days":
            self.filter_start_date = (now - timedelta(days=7)).isoformat()
            self.filter_end_date = None
        elif date_range == "Last 30 Days":
            self.filter_start_date = (now - timedelta(days=30)).isoformat()
            self.filter_end_date = None

        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters to action entries"""
        self.filter_type = None if self.type_var.get() == "All" else self.type_var.get()
        self.filter_status = None if self.status_var.get() == "All" else self.status_var.get()
        self.filter_module = None if self.module_var.get() == "All" else self.module_var.get()
        self.filter_text = self.search_var.get().lower()

        # Filter entries
        self.filtered_entries = []
        for entry in self.action_entries:
            # Type filter
            if self.filter_type and entry.get("action_type") != self.filter_type:
                continue

            # Status filter
            if self.filter_status and entry.get("status") != self.filter_status:
                continue

            # Module filter
            if self.filter_module and entry.get("module") != self.filter_module:
                continue

            # Date filter
            if self.filter_start_date:
                entry_time = entry.get("timestamp", "")
                if entry_time < self.filter_start_date:
                    continue

            if self.filter_end_date:
                entry_time = entry.get("timestamp", "")
                if entry_time > self.filter_end_date:
                    continue

            # Text search
            if self.filter_text:
                searchable = json.dumps(entry.get("action_data", {})).lower()
                if self.filter_text not in searchable:
                    continue

            self.filtered_entries.append(entry)

        # Display filtered entries
        self._display_history()
        self._update_statistics()

    def _display_history(self):
        """Display filtered action entries"""
        # Clear tree
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        if self.view_mode == "timeline":
            self._display_timeline()
        else:
            self._display_list()

    def _display_list(self):
        """Display actions in list view"""
        for entry in self.filtered_entries[-1000:]:  # Limit to last 1000
            timestamp = entry.get("timestamp", "")
            # Format timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                display_time = timestamp

            action_type = entry.get("action_type", "unknown")
            status = entry.get("status", "unknown")
            module = entry.get("module", "-")
            duration = entry.get("duration_ms", "-")

            # Insert into tree
            item_id = self.history_tree.insert(
                "",
                0,  # Insert at beginning (most recent first)
                values=(display_time, action_type, status, module, duration),
                tags=(status,),
            )

            # Store full entry in item
            self.history_tree.item(item_id, tags=(status, str(entry.get("id"))))

        # Configure tags for status colors
        self.history_tree.tag_configure("success", foreground=self.colors["success"])
        self.history_tree.tag_configure("failed", foreground=self.colors["failed"])
        self.history_tree.tag_configure("pending", foreground=self.colors["pending"])

    def _display_timeline(self):
        """Display actions in timeline view (grouped by date)"""
        # Group entries by date
        timeline: Dict[str, List[Dict[str, Any]]] = {}

        for entry in self.filtered_entries:
            timestamp = entry.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp)
                date_key = dt.strftime("%Y-%m-%d")
            except:
                date_key = "Unknown"

            if date_key not in timeline:
                timeline[date_key] = []
            timeline[date_key].append(entry)

        # Display timeline (most recent dates first)
        for date_key in sorted(timeline.keys(), reverse=True):
            entries = timeline[date_key]

            # Insert date header
            date_item = self.history_tree.insert(
                "",
                tk.END,
                text=date_key,
                values=(f"📅 {date_key}", f"{len(entries)} actions", "", "", ""),
                tags=("header",),
            )

            # Insert actions for this date
            for entry in entries:
                timestamp = entry.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(timestamp)
                    display_time = dt.strftime("%H:%M:%S")
                except:
                    display_time = timestamp

                action_type = entry.get("action_type", "unknown")
                status = entry.get("status", "unknown")
                module = entry.get("module", "-")
                duration = entry.get("duration_ms", "-")

                item_id = self.history_tree.insert(
                    date_item,
                    tk.END,
                    values=(display_time, action_type, status, module, duration),
                    tags=(status,),
                )

                self.history_tree.item(item_id, tags=(status, str(entry.get("id"))))

        # Configure tags
        self.history_tree.tag_configure(
            "header", foreground=self.colors["header"], font=("Arial", 10, "bold")
        )
        self.history_tree.tag_configure("success", foreground=self.colors["success"])
        self.history_tree.tag_configure("failed", foreground=self.colors["failed"])
        self.history_tree.tag_configure("pending", foreground=self.colors["pending"])

    def _on_action_selected(self, event):
        """Handle action selection in tree"""
        selection = self.history_tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.history_tree.item(item, "tags")

        # Extract action ID from tags
        action_id = None
        for tag in tags:
            if tag.isdigit():
                action_id = int(tag)
                break

        if action_id:
            # Find the action in filtered entries
            action = None
            for entry in self.filtered_entries:
                if entry.get("id") == action_id:
                    action = entry
                    break

            if action:
                self._display_action_details(action)

    def _display_action_details(self, action: Dict[str, Any]):
        """Display details of selected action"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)

        lines = []
        lines.append("=" * 60)
        lines.append("ACTION DETAILS")
        lines.append("=" * 60)
        lines.append(f"ID: {action.get('id', 'N/A')}")
        lines.append(f"Timestamp: {action.get('timestamp', 'N/A')}")
        lines.append(f"Type: {action.get('action_type', 'N/A')}")
        lines.append(f"Status: {action.get('status', 'N/A')}")
        lines.append(f"Module: {action.get('module', 'N/A')}")
        lines.append(f"Duration: {action.get('duration_ms', 'N/A')} ms")

        workflow_id = action.get("workflow_id")
        if workflow_id:
            lines.append(f"Workflow ID: {workflow_id}")

        step_id = action.get("step_id")
        if step_id:
            lines.append(f"Step ID: {step_id}")

        lines.append("")
        lines.append("─" * 60)
        lines.append("ACTION DATA")
        lines.append("─" * 60)
        action_data = action.get("action_data", {})
        lines.append(json.dumps(action_data, indent=2))

        result = action.get("result")
        if result:
            lines.append("")
            lines.append("─" * 60)
            lines.append("RESULT")
            lines.append("─" * 60)
            lines.append(json.dumps(result, indent=2))

        error = action.get("error")
        if error:
            lines.append("")
            lines.append("─" * 60)
            lines.append("ERROR")
            lines.append("─" * 60)
            lines.append(error)

        metadata = action.get("metadata")
        if metadata:
            lines.append("")
            lines.append("─" * 60)
            lines.append("METADATA")
            lines.append("─" * 60)
            lines.append(json.dumps(metadata, indent=2))

        lines.append("")
        lines.append("=" * 60)

        self.details_text.insert(1.0, "\n".join(lines))
        self.details_text.config(state=tk.DISABLED)

    def _clear_filters(self):
        """Clear all filters"""
        self.type_var.set("All")
        self.status_var.set("All")
        self.module_var.set("All")
        self.search_var.set("")
        self.date_range_var.set("All Time")
        self.filter_start_date = None
        self.filter_end_date = None
        self._apply_filters()

    def _export_history(self, format: str):
        """
        Export filtered history to file

        Args:
            format: Export format ("csv" or "json")
        """
        if not self.filtered_entries:
            messagebox.showwarning("No Data", "No actions to export")
            return

        # Get filename from user
        if format == "csv":
            filename = filedialog.asksaveasfilename(
                title="Export History as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
        else:  # json
            filename = filedialog.asksaveasfilename(
                title="Export History as JSON",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )

        if not filename:
            return

        try:
            if format == "csv":
                self._export_csv(filename)
            else:
                self._export_json(filename)

            messagebox.showinfo(
                "Success", f"Exported {len(self.filtered_entries)} actions to {filename}"
            )
        except Exception as e:
            logger.error(f"Error exporting history: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to export history: {e}")

    def _export_csv(self, filename: str):
        """Export history to CSV file"""
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "ID",
                    "Timestamp",
                    "Action Type",
                    "Status",
                    "Module",
                    "Duration (ms)",
                    "Workflow ID",
                    "Step ID",
                    "Action Data",
                    "Result",
                    "Error",
                ]
            )

            # Write data
            for entry in self.filtered_entries:
                writer.writerow(
                    [
                        entry.get("id", ""),
                        entry.get("timestamp", ""),
                        entry.get("action_type", ""),
                        entry.get("status", ""),
                        entry.get("module", ""),
                        entry.get("duration_ms", ""),
                        entry.get("workflow_id", ""),
                        entry.get("step_id", ""),
                        json.dumps(entry.get("action_data", {})),
                        json.dumps(entry.get("result", {})) if entry.get("result") else "",
                        entry.get("error", ""),
                    ]
                )

    def _export_json(self, filename: str):
        """Export history to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.filtered_entries, f, indent=2, ensure_ascii=False)

    def _update_status(self, message: str):
        """Update status bar message"""
        if self.status_label:
            self.status_label.config(text=message)

    def _update_statistics(self):
        """Update statistics display"""
        if not self.stats_label:
            return

        total = len(self.action_entries)
        filtered = len(self.filtered_entries)

        # Count by status in filtered entries
        success_count = sum(1 for e in self.filtered_entries if e.get("status") == "success")
        failed_count = sum(1 for e in self.filtered_entries if e.get("status") == "failed")

        if filtered < total:
            stats_text = f"Showing {filtered}/{total} | ✓ {success_count} | ✗ {failed_count}"
        else:
            stats_text = f"Total: {total} | ✓ {success_count} | ✗ {failed_count}"

        self.stats_label.config(text=stats_text)

    def show(self):
        """Show the history viewer window"""
        if self.is_showing:
            self.window.lift()
            return

        self._create_window()
        self.window.mainloop()

    def destroy(self):
        """Destroy the history viewer window"""
        if self.window:
            self._stop_auto_refresh()
            try:
                self.window.destroy()
            except tk.TclError as e:
                logger.debug(f"Failed to destroy history viewer window: {e}")
                pass
            self.window = None
            self.is_showing = False


def show_history_viewer(db_path: Optional[str] = None, **kwargs):
    """
    Convenience function to show history viewer

    Args:
        db_path: Optional database path
        **kwargs: Additional arguments for HistoryViewer
    """
    viewer = HistoryViewer(db_path=db_path, **kwargs)
    viewer.show()
