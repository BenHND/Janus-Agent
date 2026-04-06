"""
Main Dashboard UI - Central hub for Janus monitoring and control
Combines logs, statistics, action history in a single window

Uses PySide6 to match the app's design guidelines.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from janus.logging import get_logger
from janus.persistence.action_history import ActionHistory
from janus.utils.paths import get_log_dir

logger = get_logger("dashboard")


class DashboardWindow(QDialog):
    """
    Main dashboard window for Janus
    Uses PySide6 with the same design as ConfigMiniWindow
    """

    def __init__(self, parent=None, action_history: Optional[ActionHistory] = None):
        """
        Initialize dashboard

        Args:
            parent: Parent widget
            action_history: ActionHistory instance
        """
        super().__init__(parent)
        
        self.action_history = action_history or ActionHistory()
        self.log_dir = Path(get_log_dir())
        
        # Data caches
        self.log_entries: List[Dict[str, Any]] = []
        self.filtered_log_entries: List[Dict[str, Any]] = []
        self.action_entries: List[Dict[str, Any]] = []
        self.log_modules: List[str] = []
        
        # Drag state for window movement
        self._drag_pos = None
        
        # Load theme setting
        self._dark_mode = self._get_theme_from_config() == "dark"
        
        # Setup window
        self._setup_window()
        self._create_ui()
        self._apply_styles()
        
        # Load initial data
        self._load_all_data()
        
        # Setup auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load_all_data)
        self._refresh_timer.start(5000)  # Refresh every 5 seconds

    def _get_theme_from_config(self) -> str:
        """Load theme setting from config.ini"""
        import configparser
        config = configparser.ConfigParser()
        config_path = Path("config.ini")
        if config_path.exists():
            try:
                config.read(config_path)
                return config.get("ui", "theme", fallback="light")
            except (configparser.Error, OSError):
                pass
        return "light"

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowTitle("Janus Dashboard")
        self.setFixedSize(900, 700)

        # Modal dialog with no frame
        self.setModal(False)
        self.setWindowFlags(
            Qt.Dialog
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Center the window on screen
        self._center_on_screen()
    
    def _center_on_screen(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _add_shadow(self, widget, blur=20, alpha=60):
        """Add a soft shadow effect to a widget"""
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setXOffset(0)
        effect.setYOffset(4)
        effect.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(effect)

    def _create_ui(self):
        """Create UI components with overlay-matching design"""
        # Root layout with margins for shadow
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        
        # Main container with gradient background
        self.container = QFrame()
        self.container.setObjectName("container")
        self._add_shadow(self.container, blur=30, alpha=80)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with title and close button
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        title = QLabel("📈 Dashboard")
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("icon_btn")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Refresh data")
        refresh_btn.clicked.connect(self._load_all_data)
        header_layout.addWidget(refresh_btn)
        
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")
        
        # Create tabs
        self._create_overview_tab()
        self._create_history_tab()
        self._create_scheduled_tasks_tab()  # TICKET-FEAT-002
        self._create_logs_tab()
        self._create_stats_tab()
        
        main_layout.addWidget(self.tabs)
        
        root_layout.addWidget(self.container)

    def _create_overview_tab(self):
        """Create overview tab with quick stats"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Welcome section
        welcome_group = QGroupBox("Welcome to Janus")
        welcome_layout = QVBoxLayout(welcome_group)
        
        welcome_text = QLabel(
            "Janus is your voice-controlled automation assistant.\n\n"
            "Use this dashboard to:\n"
            "• Monitor action history and performance\n"
            "• View detailed logs and debug information\n"
            "• Analyze usage statistics and patterns"
        )
        welcome_text.setWordWrap(True)
        welcome_layout.addWidget(welcome_text)
        layout.addWidget(welcome_group)
        
        # Quick stats
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.stat_total = self._create_stat_card("Total Actions", "0")
        self.stat_success = self._create_stat_card("Successful", "0")
        self.stat_failed = self._create_stat_card("Failed", "0")
        self.stat_avg_duration = self._create_stat_card("Avg Duration", "0ms")
        
        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_success)
        stats_layout.addWidget(self.stat_failed)
        stats_layout.addWidget(self.stat_avg_duration)
        
        layout.addWidget(stats_group)
        
        # Quick navigation
        nav_group = QGroupBox("Quick Navigation")
        nav_layout = QHBoxLayout(nav_group)
        
        btn_history = QPushButton("📋 Action History")
        btn_history.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        nav_layout.addWidget(btn_history)
        
        btn_logs = QPushButton("📝 Logs")
        btn_logs.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        nav_layout.addWidget(btn_logs)
        
        btn_stats = QPushButton("📊 Statistics")
        btn_stats.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        nav_layout.addWidget(btn_stats)
        
        layout.addWidget(nav_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "Overview")

    def _create_stat_card(self, label: str, value: str) -> QFrame:
        """Create a stat card widget"""
        card = QFrame()
        card.setObjectName("stat_card")
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setObjectName("stat_value")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)
        
        text_label = QLabel(label)
        text_label.setObjectName("stat_label")
        text_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(text_label)
        
        # Store reference to value label for updates
        card.value_label = value_label
        
        return card

    def _create_history_tab(self):
        """Create action history tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Status:"))
        self.history_status_filter = QComboBox()
        self.history_status_filter.addItems(["All", "success", "failed", "pending"])
        self.history_status_filter.currentTextChanged.connect(self._load_history)
        filter_layout.addWidget(self.history_status_filter)
        
        filter_layout.addWidget(QLabel("Limit:"))
        self.history_limit = QComboBox()
        self.history_limit.addItems(["50", "100", "200", "500"])
        self.history_limit.setCurrentText("100")
        self.history_limit.currentTextChanged.connect(self._load_history)
        filter_layout.addWidget(self.history_limit)
        
        filter_layout.addStretch()
        
        export_btn = QPushButton("📥 Export JSON")
        export_btn.clicked.connect(self._export_history)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Action Type", "Status", "Duration", "Module"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        
        self.tabs.addTab(tab, "Action History")
    
    def _create_scheduled_tasks_tab(self):
        """Create scheduled tasks tab (TICKET-FEAT-002)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Info section
        info_label = QLabel("📅 Scheduled Tasks - View and manage delayed and recurring tasks")
        info_label.setObjectName("section_title")
        layout.addWidget(info_label)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Status:"))
        self.tasks_status_filter = QComboBox()
        self.tasks_status_filter.addItems(["All", "pending", "running", "completed", "failed", "cancelled"])
        self.tasks_status_filter.currentTextChanged.connect(self._load_scheduled_tasks)
        filter_layout.addWidget(self.tasks_status_filter)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_scheduled_tasks)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # Tasks table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels([
            "Task ID", "Type", "Command", "Status", "Next Run", "Actions"
        ])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setAlternatingRowColors(True)
        layout.addWidget(self.tasks_table)
        
        # Summary label
        self.tasks_summary_label = QLabel("No scheduled tasks")
        self.tasks_summary_label.setObjectName("info_text")
        layout.addWidget(self.tasks_summary_label)
        
        self.tabs.addTab(tab, "⏰ Scheduled Tasks")

    def _create_logs_tab(self):
        """Create logs viewer tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Level:"))
        self.log_level_filter = QComboBox()
        self.log_level_filter.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_filter.currentTextChanged.connect(self._apply_log_filters)
        filter_layout.addWidget(self.log_level_filter)
        
        filter_layout.addWidget(QLabel("Module:"))
        self.log_module_filter = QComboBox()
        self.log_module_filter.addItem("All")
        self.log_module_filter.currentTextChanged.connect(self._apply_log_filters)
        filter_layout.addWidget(self.log_module_filter)
        
        filter_layout.addWidget(QLabel("Search:"))
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("Search logs...")
        self.log_search.textChanged.connect(self._apply_log_filters)
        filter_layout.addWidget(self.log_search)
        
        filter_layout.addStretch()
        
        export_btn = QPushButton("📥 Export")
        export_btn.clicked.connect(self._export_logs)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setObjectName("log_display")
        layout.addWidget(self.log_display)
        
        # Status
        self.log_status = QLabel("Ready")
        self.log_status.setObjectName("status_label")
        layout.addWidget(self.log_status)
        
        self.tabs.addTab(tab, "Logs")

    def _create_stats_tab(self):
        """Create statistics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Period filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Period:"))
        self.stats_period = QComboBox()
        self.stats_period.addItems(["All Time", "Today", "Last 7 Days", "Last 30 Days"])
        self.stats_period.currentTextChanged.connect(self._load_statistics)
        filter_layout.addWidget(self.stats_period)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Stats cards row
        cards_layout = QHBoxLayout()
        self.stats_total = self._create_stat_card("Total", "0")
        self.stats_success_rate = self._create_stat_card("Success Rate", "0%")
        self.stats_avg = self._create_stat_card("Avg Duration", "0ms")
        self.stats_failed = self._create_stat_card("Failed", "0")
        cards_layout.addWidget(self.stats_total)
        cards_layout.addWidget(self.stats_success_rate)
        cards_layout.addWidget(self.stats_avg)
        cards_layout.addWidget(self.stats_failed)
        layout.addLayout(cards_layout)
        
        # Action types table
        types_group = QGroupBox("Action Types")
        types_layout = QVBoxLayout(types_group)
        self.action_types_table = QTableWidget()
        self.action_types_table.setColumnCount(3)
        self.action_types_table.setHorizontalHeaderLabels(["Action Type", "Count", "Percentage"])
        self.action_types_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        types_layout.addWidget(self.action_types_table)
        layout.addWidget(types_group)
        
        # Recent failures
        failures_group = QGroupBox("Recent Failures")
        failures_layout = QVBoxLayout(failures_group)
        self.failures_table = QTableWidget()
        self.failures_table.setColumnCount(3)
        self.failures_table.setHorizontalHeaderLabels(["Timestamp", "Action Type", "Error"])
        self.failures_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        failures_layout.addWidget(self.failures_table)
        layout.addWidget(failures_group)
        
        self.tabs.addTab(tab, "Statistics")

    def _apply_styles(self):
        """Apply modern macOS-inspired styling matching overlay theme"""
        if self._dark_mode:
            # Dark mode styling - matching overlay dark mode colors
            self.setStyleSheet("""
                /* Main container with dark gradient matching overlay */
                #container {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3D4147, stop:1 #2C3036);
                    border-radius: 16px;
                    border: 1px solid rgba(255,255,255,0.15);
                }
                
                /* Header */
                #header {
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.2);
                }
                #title {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 14px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                #close_btn {
                    background: rgba(255,100,100,0.5);
                    border: none;
                    border-radius: 12px;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                }
                #close_btn:hover {
                    background: rgba(255,100,100,0.8);
                }
                #icon_btn {
                    background: rgba(255,255,255,0.1);
                    border: none;
                    border-radius: 14px;
                    color: white;
                    font-size: 13px;
                }
                #icon_btn:hover {
                    background: rgba(255,255,255,0.2);
                }
                
                /* Tab widget */
                QTabWidget::pane {
                    border: none;
                    background: transparent;
                }
                QTabBar::tab {
                    background: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.7);
                    padding: 10px 20px;
                    margin-right: 4px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QTabBar::tab:selected {
                    background: rgba(32, 227, 178, 0.3);
                    color: white;
                }
                QTabBar::tab:hover:!selected {
                    background: rgba(255,255,255,0.15);
                }
                
                /* Group boxes */
                QGroupBox {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 10px;
                    margin-top: 16px;
                    padding-top: 12px;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 12px;
                    padding: 0 6px;
                    color: rgba(255,255,255,0.8);
                }
                
                /* Labels */
                QLabel {
                    color: rgba(255,255,255,0.9);
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                /* Stat cards */
                #stat_card {
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 10px;
                    padding: 12px;
                    min-width: 100px;
                }
                #stat_value {
                    color: #20E3B2;
                    font-size: 24px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                #stat_label {
                    color: rgba(255,255,255,0.6);
                    font-size: 10px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                /* Buttons */
                QPushButton {
                    background-color: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.25);
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: 500;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.2);
                    border-color: rgba(255,255,255,0.4);
                }
                QPushButton:pressed {
                    background-color: rgba(255,255,255,0.25);
                }
                
                /* Combo boxes */
                QComboBox {
                    background-color: rgba(60, 65, 75, 0.9);
                    border: 1px solid rgba(255,255,255,0.25);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 11px;
                    min-width: 80px;
                }
                QComboBox:hover {
                    border-color: #20E3B2;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox QAbstractItemView {
                    background-color: #3D4147;
                    border: 1px solid rgba(255,255,255,0.25);
                    selection-background-color: #20E3B2;
                    color: white;
                }
                
                /* Line edits */
                QLineEdit {
                    background-color: rgba(60, 65, 75, 0.9);
                    border: 1px solid rgba(255,255,255,0.25);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border: 2px solid #20E3B2;
                }
                
                /* Tables */
                QTableWidget {
                    background-color: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 8px;
                    color: white;
                    font-size: 11px;
                    gridline-color: rgba(255,255,255,0.08);
                }
                QTableWidget::item {
                    padding: 6px;
                }
                QTableWidget::item:selected {
                    background-color: rgba(32, 227, 178, 0.3);
                }
                QHeaderView::section {
                    background-color: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.8);
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                    font-size: 10px;
                }
                QTableWidget::item:alternate {
                    background-color: rgba(255,255,255,0.02);
                }
                
                /* Text edit (logs) */
                #log_display {
                    background-color: rgba(0,0,0,0.2);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 8px;
                    color: #e0e0e0;
                    font-family: "SF Mono", "Menlo", "Monaco", monospace;
                    font-size: 11px;
                    padding: 8px;
                }
                
                /* Status label */
                #status_label {
                    color: rgba(255,255,255,0.5);
                    font-size: 10px;
                }
                
                /* Scrollbars */
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 8px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: rgba(255,255,255,0.25);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(255,255,255,0.4);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: transparent;
                    height: 8px;
                }
                QScrollBar::handle:horizontal {
                    background: rgba(255,255,255,0.25);
                    border-radius: 4px;
                }
            """)
        else:
            # Light mode styling - improved contrast with darker grey tones
            self.setStyleSheet("""
                /* Main container with medium grey gradient for better readability */
                #container {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5A5F66, stop:1 #474C54);
                    border-radius: 16px;
                    border: 1px solid rgba(255,255,255,0.2);
                }
                
                /* Header */
                #header {
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.2);
                }
                #title {
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 14px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                #close_btn {
                    background: rgba(255,100,100,0.6);
                    border: none;
                    border-radius: 12px;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                }
                #close_btn:hover {
                    background: rgba(255,100,100,0.85);
                }
                #icon_btn {
                    background: rgba(255,255,255,0.15);
                    border: none;
                    border-radius: 14px;
                    color: white;
                    font-size: 13px;
                }
                #icon_btn:hover {
                    background: rgba(255,255,255,0.25);
                }
                
                /* Tab widget */
                QTabWidget::pane {
                    border: none;
                    background: transparent;
                }
                QTabBar::tab {
                    background: rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.8);
                    padding: 10px 20px;
                    margin-right: 4px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QTabBar::tab:selected {
                    background: rgba(32, 227, 178, 0.4);
                    color: white;
                }
                QTabBar::tab:hover:!selected {
                    background: rgba(255,255,255,0.2);
                }
                
                /* Group boxes */
                QGroupBox {
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 10px;
                    margin-top: 16px;
                    padding-top: 12px;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 12px;
                    padding: 0 6px;
                    color: rgba(255,255,255,0.9);
                }
                
                /* Labels */
                QLabel {
                    color: rgba(255,255,255,0.95);
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                /* Stat cards */
                #stat_card {
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 10px;
                    padding: 12px;
                    min-width: 100px;
                }
                #stat_value {
                    color: #20E3B2;
                    font-size: 24px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                #stat_label {
                    color: rgba(255,255,255,0.7);
                    font-size: 10px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                /* Buttons */
                QPushButton {
                    background-color: rgba(255,255,255,0.12);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: 500;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.22);
                    border-color: rgba(255,255,255,0.45);
                }
                QPushButton:pressed {
                    background-color: rgba(255,255,255,0.28);
                }
                
                /* Combo boxes */
                QComboBox {
                    background-color: rgba(80, 85, 95, 0.9);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 11px;
                    min-width: 80px;
                }
                QComboBox:hover {
                    border-color: #20E3B2;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox QAbstractItemView {
                    background-color: #5A5F66;
                    border: 1px solid rgba(255,255,255,0.3);
                    selection-background-color: #20E3B2;
                    color: white;
                }
                
                /* Line edits */
                QLineEdit {
                    background-color: rgba(80, 85, 95, 0.9);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border: 2px solid #20E3B2;
                }
                
                /* Tables */
                QTableWidget {
                    background-color: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 8px;
                    color: white;
                    font-size: 11px;
                    gridline-color: rgba(255,255,255,0.1);
                }
                QTableWidget::item {
                    padding: 6px;
                }
                QTableWidget::item:selected {
                    background-color: rgba(32, 227, 178, 0.35);
                }
                QHeaderView::section {
                    background-color: rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.85);
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                    font-size: 10px;
                }
                QTableWidget::item:alternate {
                    background-color: rgba(255,255,255,0.03);
                }
                
                /* Text edit (logs) */
                #log_display {
                    background-color: rgba(0,0,0,0.2);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 8px;
                    color: #e0e0e0;
                    font-family: "SF Mono", "Menlo", "Monaco", monospace;
                    font-size: 11px;
                    padding: 8px;
                }
                
                /* Status label */
                #status_label {
                    color: rgba(255,255,255,0.6);
                    font-size: 10px;
                }
                
                /* Scrollbars */
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 8px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: rgba(255,255,255,0.3);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(255,255,255,0.5);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: transparent;
                    height: 8px;
                }
                QScrollBar::handle:horizontal {
                    background: rgba(255,255,255,0.3);
                    border-radius: 4px;
                }
            """)

    # ==================== Data Loading Methods ====================

    def _load_all_data(self):
        """Load all data for all tabs"""
        self._load_overview_stats()
        self._load_history()
        self._load_scheduled_tasks()  # TICKET-FEAT-002
        self._load_logs()
        self._load_statistics()

    def _load_overview_stats(self):
        """Load and display overview statistics"""
        try:
            stats = self.action_history.get_statistics()
            total = stats.get("total_actions", 0)
            by_status = stats.get("by_status", {})
            success = by_status.get("success", 0)
            failed = by_status.get("failed", 0)
            avg_duration = stats.get("avg_duration_ms", 0)

            self.stat_total.value_label.setText(str(total))
            self.stat_success.value_label.setText(str(success))
            self.stat_failed.value_label.setText(str(failed))
            self.stat_avg_duration.value_label.setText(f"{avg_duration}ms")
        except Exception as e:
            logger.error(f"Failed to load overview stats: {e}")

    def _load_history(self):
        """Load and display action history"""
        try:
            status = self.history_status_filter.currentText()
            status = None if status == "All" else status
            limit = int(self.history_limit.currentText())
            
            history = self.action_history.get_history(limit=limit, status=status)
            self.action_entries = history
            
            self.history_table.setRowCount(len(history))
            
            for row, entry in enumerate(history):
                timestamp = entry.get("timestamp", "")[:19]
                action_type = entry.get("action_type", "unknown")
                entry_status = entry.get("status", "unknown")
                duration = entry.get("duration_ms", 0)
                duration_str = f"{duration}ms" if duration else "N/A"
                module = entry.get("module", "N/A")
                
                self.history_table.setItem(row, 0, QTableWidgetItem(timestamp))
                self.history_table.setItem(row, 1, QTableWidgetItem(action_type))
                
                status_item = QTableWidgetItem(entry_status)
                if entry_status == "success":
                    status_item.setForeground(QColor("#20E3B2"))
                elif entry_status == "failed":
                    status_item.setForeground(QColor("#FF6B6B"))
                self.history_table.setItem(row, 2, status_item)
                
                self.history_table.setItem(row, 3, QTableWidgetItem(duration_str))
                self.history_table.setItem(row, 4, QTableWidgetItem(module))
                
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    def _load_scheduled_tasks(self):
        """
        Load and display scheduled tasks (TICKET-FEAT-002)
        
        NOTE: This is a placeholder implementation. The dashboard currently
        runs as a standalone window without access to the pipeline's scheduler.
        Full integration requires:
        1. Passing lifecycle_service or scheduler reference to dashboard
        2. Real-time updates via signals/callbacks
        3. Task management UI (cancel, edit buttons)
        
        Users can verify scheduled tasks are working by:
        - Checking application logs for scheduler messages
        - Waiting for TTS notifications to trigger
        - Using the SchedulerAgent directly via commands
        """
        try:
            self.tasks_table.setRowCount(0)
            self.tasks_summary_label.setText(
                "⚠️ Dashboard integration in progress - tasks are working but not visible here yet. "
                "Check application logs to verify scheduled tasks."
            )
            
        except Exception as e:
            logger.error(f"Failed to load scheduled tasks: {e}")
            self.tasks_summary_label.setText(f"Error loading tasks: {e}")

    def _load_logs(self):
        """Load logs from files"""
        self.log_entries = []
        self.log_modules = []

        if not self.log_dir.exists():
            self.log_status.setText(f"Log directory not found: {self.log_dir}")
            return

        log_files = list(self.log_dir.glob("*.log")) + list(self.log_dir.glob("*.json"))

        if not log_files:
            self.log_status.setText("No log files found")
            return

        for log_file in sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            entry = json.loads(line)
                            if "level" not in entry and "levelname" in entry:
                                entry["level"] = entry["levelname"]
                            if "timestamp" not in entry and "created" in entry:
                                entry["timestamp"] = datetime.fromtimestamp(
                                    entry["created"]
                                ).isoformat()
                        except json.JSONDecodeError:
                            entry = self._parse_text_log_line(line)

                        if entry:
                            entry["file"] = log_file.name
                            self.log_entries.append(entry)
                            module = entry.get("module", entry.get("logger", "unknown"))
                            if module and module not in self.log_modules:
                                self.log_modules.append(module)

            except Exception as e:
                logger.error(f"Error loading log file {log_file}: {e}")

        # Update module filter
        current_module = self.log_module_filter.currentText()
        self.log_module_filter.clear()
        self.log_module_filter.addItem("All")
        self.log_module_filter.addItems(sorted(self.log_modules))
        idx = self.log_module_filter.findText(current_module)
        if idx >= 0:
            self.log_module_filter.setCurrentIndex(idx)

        self._apply_log_filters()
        self.log_status.setText(f"Loaded {len(self.log_entries)} log entries from {len(log_files)} files")

    def _parse_text_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a plain text log line"""
        parts = line.split(None, 4)
        if len(parts) >= 4:
            try:
                return {
                    "timestamp": f"{parts[0]} {parts[1]}",
                    "level": parts[2],
                    "module": parts[3],
                    "message": parts[4] if len(parts) > 4 else "",
                }
            except Exception:
                pass
        return {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "module": "unknown",
            "message": line,
        }

    def _apply_log_filters(self):
        """Apply current filters to log entries"""
        filter_level = self.log_level_filter.currentText()
        filter_level = None if filter_level == "All" else filter_level
        filter_module = self.log_module_filter.currentText()
        filter_module = None if filter_module == "All" else filter_module
        filter_text = self.log_search.text().lower()

        self.filtered_log_entries = []
        for entry in self.log_entries:
            if filter_level and entry.get("level") != filter_level:
                continue
            module = entry.get("module", entry.get("logger", ""))
            if filter_module and module != filter_module:
                continue
            if filter_text:
                message = entry.get("message", "").lower()
                if filter_text not in message:
                    continue
            self.filtered_log_entries.append(entry)

        self._display_logs()

    def _display_logs(self):
        """Display filtered log entries"""
        self.log_display.clear()
        
        # Define colors for log levels
        level_colors = {
            "DEBUG": "#888888",
            "INFO": "#20E3B2",
            "WARNING": "#FFB86C",
            "ERROR": "#FF6B6B",
            "CRITICAL": "#FF5555",
        }
        
        html_lines = []
        for entry in self.filtered_log_entries[-500:]:  # Limit to last 500
            timestamp = entry.get("timestamp", "")
            level = entry.get("level", "INFO")
            module = entry.get("module", "unknown")
            message = entry.get("message", "")
            
            color = level_colors.get(level, "#e0e0e0")
            html_lines.append(
                f'<span style="color:{color}">[{timestamp}] {level:8s} {module:20s} - {message}</span>'
            )
        
        self.log_display.setHtml("<br>".join(html_lines))

    def _load_statistics(self):
        """Load and display statistics"""
        try:
            period = self.stats_period.currentText()
            start_date = None
            
            if period == "Today":
                start_date = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
            elif period == "Last 7 Days":
                start_date = (datetime.now() - timedelta(days=7)).isoformat()
            elif period == "Last 30 Days":
                start_date = (datetime.now() - timedelta(days=30)).isoformat()
            
            stats = self.action_history.get_statistics(start_date, None)
            
            total = stats.get("total_actions", 0)
            by_status = stats.get("by_status", {})
            success_count = by_status.get("success", 0)
            failed_count = by_status.get("failed", 0)
            
            self.stats_total.value_label.setText(str(total))
            
            if total > 0:
                success_rate = (success_count / total) * 100
                self.stats_success_rate.value_label.setText(f"{success_rate:.1f}%")
            else:
                self.stats_success_rate.value_label.setText("N/A")
            
            avg_duration = stats.get("avg_duration_ms", 0)
            self.stats_avg.value_label.setText(f"{avg_duration}ms")
            self.stats_failed.value_label.setText(str(failed_count))
            
            # Update action types table
            by_type = stats.get("by_type", {})
            self.action_types_table.setRowCount(len(by_type))
            for row, (action_type, count) in enumerate(sorted(by_type.items(), key=lambda x: x[1], reverse=True)):
                percentage = (count / total * 100) if total > 0 else 0
                self.action_types_table.setItem(row, 0, QTableWidgetItem(action_type))
                self.action_types_table.setItem(row, 1, QTableWidgetItem(str(count)))
                self.action_types_table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))
            
            # Update recent failures
            try:
                failures = self.action_history.get_recent_failures(limit=10)
                self.failures_table.setRowCount(len(failures))
                for row, failure in enumerate(failures):
                    timestamp = failure.get("timestamp", "")[:19]
                    action_type = failure.get("action_type", "unknown")
                    error = failure.get("error", "No error message")[:50]
                    self.failures_table.setItem(row, 0, QTableWidgetItem(timestamp))
                    self.failures_table.setItem(row, 1, QTableWidgetItem(action_type))
                    self.failures_table.setItem(row, 2, QTableWidgetItem(error))
            except Exception as e:
                logger.error(f"Failed to load recent failures: {e}")
                
        except Exception as e:
            logger.error(f"Failed to load statistics: {e}")

    # ==================== Export Methods ====================

    def _export_history(self):
        """Export history to JSON file"""
        if not self.action_entries:
            QMessageBox.warning(self, "No Data", "No actions to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export History", "", "JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.action_entries, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", f"Exported {len(self.action_entries)} actions")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def _export_logs(self):
        """Export filtered logs to file"""
        if not self.filtered_log_entries:
            QMessageBox.warning(self, "No Data", "No logs to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "", "JSON Files (*.json);;Text Files (*.txt)"
        )
        if filename:
            try:
                if filename.endswith(".json"):
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(self.filtered_log_entries, f, indent=2, ensure_ascii=False)
                else:
                    with open(filename, "w", encoding="utf-8") as f:
                        for entry in self.filtered_log_entries:
                            timestamp = entry.get("timestamp", "")
                            level = entry.get("level", "INFO")
                            module = entry.get("module", "unknown")
                            message = entry.get("message", "")
                            f.write(f"[{timestamp}] {level:8s} {module:20s} - {message}\n")
                QMessageBox.information(self, "Success", f"Exported {len(self.filtered_log_entries)} log entries")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    # ==================== Window Drag Support ====================

    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self._drag_pos = None
        event.accept()

    def closeEvent(self, event):
        """Handle window close"""
        self._refresh_timer.stop()
        event.accept()


def show_dashboard(action_history: Optional[ActionHistory] = None):
    """
    Convenience function to show dashboard
    
    Args:
        action_history: Optional ActionHistory instance
    """
    # For standalone usage
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    dashboard = DashboardWindow(action_history=action_history)
    dashboard.exec()


# Alias for convenience
Dashboard = DashboardWindow
