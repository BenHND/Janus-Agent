"""
UI components for Janus - Phase 6 & Phase 10
Provides visual feedback, overlays, and configuration interfaces
"""

# Import configuration manager (doesn't require tkinter)
from janus.ui.config_manager import ConfigManager, get_config_manager

# Lazy imports for tkinter-dependent modules
_overlay_imported = False
_enhanced_overlay_imported = False
_confirmation_dialog_imported = False
_correction_dialog_imported = False
_config_ui_imported = False
_learning_dashboard_imported = False
_learning_overlay_imported = False
_logs_viewer_imported = False
_history_viewer_imported = False
_stats_panel_imported = False
_dashboard_imported = False
_tts_control_imported = False
_overlay_ui_imported = False


def _import_overlay():
    global _overlay_imported, ActionOverlay
    if not _overlay_imported:
        from janus.ui.overlay import ActionOverlay as _ActionOverlay

        ActionOverlay = _ActionOverlay
        _overlay_imported = True
    return ActionOverlay


def _import_enhanced_overlay():
    global _enhanced_overlay_imported, EnhancedOverlay
    if not _enhanced_overlay_imported:
        from janus.ui.enhanced_overlay import EnhancedOverlay as _EnhancedOverlay

        EnhancedOverlay = _EnhancedOverlay
        _enhanced_overlay_imported = True
    return EnhancedOverlay


def _import_confirmation_dialog():
    global _confirmation_dialog_imported, ConfirmationDialog
    if not _confirmation_dialog_imported:
        from janus.ui.confirmation_dialog import ConfirmationDialog as _ConfirmationDialog

        ConfirmationDialog = _ConfirmationDialog
        _confirmation_dialog_imported = True
    return ConfirmationDialog


def _import_correction_dialog():
    global _correction_dialog_imported, CorrectionDialog
    if not _correction_dialog_imported:
        from janus.ui.correction_dialog import CorrectionDialog as _CorrectionDialog

        CorrectionDialog = _CorrectionDialog
        _correction_dialog_imported = True
    return CorrectionDialog


def _import_config_ui():
    global _config_ui_imported, ConfigUI
    if not _config_ui_imported:
        from janus.ui.config_ui import ConfigUI as _ConfigUI

        ConfigUI = _ConfigUI
        _config_ui_imported = True
    return ConfigUI


def _import_learning_dashboard():
    global _learning_dashboard_imported, LearningDashboard
    if not _learning_dashboard_imported:
        from janus.ui.learning_dashboard import LearningDashboard as _LearningDashboard

        LearningDashboard = _LearningDashboard
        _learning_dashboard_imported = True
    return LearningDashboard


def _import_learning_overlay():
    global _learning_overlay_imported, LearningOverlay
    if not _learning_overlay_imported:
        from janus.ui.learning_overlay import LearningOverlay as _LearningOverlay

        LearningOverlay = _LearningOverlay
        _learning_overlay_imported = True
    return LearningOverlay


def _import_logs_viewer():
    global _logs_viewer_imported, LogsViewer
    if not _logs_viewer_imported:
        from janus.ui.logs_viewer import LogsViewer as _LogsViewer

        LogsViewer = _LogsViewer
        _logs_viewer_imported = True
    return LogsViewer


def _import_history_viewer():
    global _history_viewer_imported, HistoryViewer
    if not _history_viewer_imported:
        from janus.ui.history_viewer import HistoryViewer as _HistoryViewer

        HistoryViewer = _HistoryViewer
        _history_viewer_imported = True
    return HistoryViewer


def _import_stats_panel():
    global _stats_panel_imported, StatsPanel
    if not _stats_panel_imported:
        from janus.ui.stats_panel import StatsPanel as _StatsPanel

        StatsPanel = _StatsPanel
        _stats_panel_imported = True
    return StatsPanel


def _import_dashboard():
    global _dashboard_imported, Dashboard
    if not _dashboard_imported:
        from janus.ui.dashboard import Dashboard as _Dashboard

        Dashboard = _Dashboard
        _dashboard_imported = True
    return Dashboard


def _import_tts_control():
    global _tts_control_imported, TTSControlPanel
    if not _tts_control_imported:
        from janus.ui.tts_control import TTSControlPanel as _TTSControlPanel

        TTSControlPanel = _TTSControlPanel
        _tts_control_imported = True
    return TTSControlPanel


def _import_overlay_ui():
    global _overlay_ui_imported, OverlayUI, MicState, StatusState
    if not _overlay_ui_imported:
        from janus.ui.overlay_ui import MicState as _MicState
        from janus.ui.overlay_ui import OverlayUI as _OverlayUI
        from janus.ui.overlay_ui import StatusState as _StatusState

        OverlayUI = _OverlayUI
        MicState = _MicState
        StatusState = _StatusState
        _overlay_ui_imported = True
    return OverlayUI, MicState, StatusState


# IMPORTANT: Do NOT import tkinter-dependent modules at package load time!
# This causes crashes on macOS when Qt is already running.
# Use the lazy import functions defined above instead.
# These placeholders are set to None and will be lazily imported when needed.
ActionOverlay = None
EnhancedOverlay = None
ConfirmationDialog = None
CorrectionDialog = None
ConfigUI = None
LearningDashboard = None
LearningOverlay = None
LogsViewer = None
HistoryViewer = None
StatsPanel = None
Dashboard = None
TTSControlPanel = None

# Try to import PySide6-dependent modules (new overlay UI)
try:
    from janus.ui.overlay_types import MicState, StatusState
    from janus.ui.overlay_ui import OverlayUI
    from janus.ui.chat_overlay_window import ChatOverlayWindow
except (ImportError, ModuleNotFoundError):
    # Define placeholder classes that will be lazily imported when needed
    OverlayUI = None
    ChatOverlayWindow = None

# Always import overlay types (they don't require PySide6)
try:
    from janus.ui.overlay_types import MicState, StatusState
except ImportError:
    MicState = None
    StatusState = None

__all__ = [
    "ActionOverlay",
    "ConfirmationDialog",
    "CorrectionDialog",
    "ConfigUI",
    "EnhancedOverlay",
    "LearningDashboard",
    "LearningOverlay",
    "LogsViewer",
    "HistoryViewer",
    "StatsPanel",
    "Dashboard",
    "TTSControlPanel",
    "ConfigManager",
    "get_config_manager",
    "OverlayUI",
    "MicState",
    "StatusState",
    "ChatOverlayWindow",
]
