"""
Configuration Mini-Window for OverlayUI

A simple configuration dialog that can be opened from the overlay.
Provides settings for:
- Feature toggles (LLM Reasoning, Vision, Learning, Semantic Correction, TTS)
- LLM Provider and Model
- STT Model (Whisper)
- Language settings
- Quick access to Logs and History viewers

Design matches the overlay UI's modern macOS-inspired styling.
"""

import configparser
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Constants
CONFIG_INI_PATH = "config.ini"

class ConfigMiniWindow(QDialog):
    """
    Configuration mini-window for OverlayUI settings

    Signals:
        config_changed: Emitted when configuration is saved
    """

    config_changed = Signal(dict)

    def __init__(self, parent=None, current_config: Optional[dict] = None):
        """
        Initialize configuration window

        Args:
            parent: Parent widget (typically the overlay)
            current_config: Dictionary with current configuration values
        """
        super().__init__(parent)

        # Current configuration
        self.config = current_config or {}
        
        # Drag state for window movement
        self._drag_pos = None
        
        # Load config.ini settings
        self._load_ini_config()
        
        # Load theme setting
        self._dark_mode = self.ini_config.get("ui", "theme", fallback="light") == "dark"

        # Setup window
        self._setup_window()
        self._create_ui()
        self._load_config()

    def _load_ini_config(self):
        """Load settings from config.ini"""
        import logging
        logger = logging.getLogger(__name__)
        
        self.ini_config = configparser.ConfigParser()
        config_path = Path(CONFIG_INI_PATH)
        if config_path.exists():
            try:
                self.ini_config.read(config_path)
            except configparser.Error as e:
                logger.warning(f"Failed to parse config.ini: {e}")
            except OSError as e:
                logger.warning(f"Failed to read config.ini: {e}")

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowTitle("Janus Configuration")
        self.setFixedSize(420, 580)

        # Modal dialog that stays on top with no frame
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
        
        title = QLabel("⚙️ Configuration")
        title.setObjectName("title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("scroll_area")

        # Content widget
        content = QWidget()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Quick Access Section
        quick_access_group = QGroupBox("Quick Access")
        quick_access_layout = QHBoxLayout()
        quick_access_layout.setSpacing(8)

        self.dashboard_btn = QPushButton("📈 Dashboard")
        self.dashboard_btn.setToolTip("Open main dashboard with logs, history, stats")
        self.dashboard_btn.clicked.connect(self._open_dashboard)
        quick_access_layout.addWidget(self.dashboard_btn)

        self.full_config_btn = QPushButton("⚙️ config.ini")
        self.full_config_btn.setToolTip("Open config.ini in text editor")
        self.full_config_btn.clicked.connect(self._open_config_file)
        quick_access_layout.addWidget(self.full_config_btn)

        quick_access_group.setLayout(quick_access_layout)
        layout.addWidget(quick_access_group)

        # Core Features Section (from config.ini [features])
        features_group = QGroupBox("Core Features")
        features_layout = QVBoxLayout()
        features_layout.setSpacing(8)

        # Get defaults from config.ini
        enable_llm = self.ini_config.getboolean("features", "enable_llm_reasoning", fallback=True)
        enable_vision = self.ini_config.getboolean("features", "enable_vision", fallback=True)
        enable_learning = self.ini_config.getboolean("features", "enable_learning", fallback=True)
        enable_semantic = self.ini_config.getboolean("features", "enable_semantic_correction", fallback=True)

        self.llm_feature_toggle = QCheckBox("LLM Reasoning")
        self.llm_feature_toggle.setChecked(enable_llm)
        self.llm_feature_toggle.setToolTip("Use LLM for advanced command understanding and planning")
        features_layout.addWidget(self.llm_feature_toggle)

        self.vision_feature_toggle = QCheckBox("Vision/OCR")
        self.vision_feature_toggle.setChecked(enable_vision)
        self.vision_feature_toggle.setToolTip("Screen analysis and visual element detection with Florence-2")
        features_layout.addWidget(self.vision_feature_toggle)

        self.learning_feature_toggle = QCheckBox("Continuous Learning")
        self.learning_feature_toggle.setChecked(enable_learning)
        self.learning_feature_toggle.setToolTip("System learns from your corrections and history")
        features_layout.addWidget(self.learning_feature_toggle)

        self.semantic_correction_toggle = QCheckBox("Semantic Correction")
        self.semantic_correction_toggle.setChecked(enable_semantic)
        self.semantic_correction_toggle.setToolTip("LLM-based correction for STT transcription errors")
        features_layout.addWidget(self.semantic_correction_toggle)

        features_group.setLayout(features_layout)
        layout.addWidget(features_group)

        # LLM Settings (from config.ini [llm])
        llm_group = QGroupBox("LLM Configuration")
        llm_layout = QFormLayout()
        llm_layout.setSpacing(8)

        # Get defaults from config.ini
        current_provider = self.ini_config.get("llm", "provider", fallback="ollama")
        current_model = self.ini_config.get("llm", "model", fallback="llama3.2")

        self.llm_provider = QComboBox()
        self.llm_provider.addItems([
            "ollama",
            "openai", 
            "anthropic",
            "mistral",
        ])
        # Set current provider
        idx = self.llm_provider.findText(current_provider)
        if idx >= 0:
            self.llm_provider.setCurrentIndex(idx)
        llm_layout.addRow("Provider:", self.llm_provider)

        self.llm_model = QLineEdit()
        self.llm_model.setText(current_model)
        self.llm_model.setPlaceholderText("e.g., llama3.2, gpt-4, claude-3-opus")
        llm_layout.addRow("Model:", self.llm_model)

        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        # Speech Recognition Settings (from config.ini [whisper])
        stt_group = QGroupBox("Speech Recognition")
        stt_layout = QFormLayout()
        stt_layout.setSpacing(8)

        current_stt_model = self.ini_config.get("whisper", "model_size", fallback="small")

        self.stt_model = QComboBox()
        self.stt_model.addItems(["tiny", "base", "small", "medium", "large"])
        idx = self.stt_model.findText(current_stt_model)
        if idx >= 0:
            self.stt_model.setCurrentIndex(idx)
        stt_layout.addRow("Whisper Model:", self.stt_model)

        # Language selection
        current_lang = self.ini_config.get("language", "default", fallback="fr")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["fr", "en"])
        idx = self.language_combo.findText(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        stt_layout.addRow("Language:", self.language_combo)

        stt_group.setLayout(stt_layout)
        layout.addWidget(stt_group)

        # TTS Settings (from config.ini [tts])
        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QVBoxLayout()
        tts_layout.setSpacing(8)

        enable_tts = self.ini_config.getboolean("tts", "enable_tts", fallback=True)
        self.tts_feature_toggle = QCheckBox("Enable Voice Responses")
        self.tts_feature_toggle.setChecked(enable_tts)
        self.tts_feature_toggle.setToolTip("Agent speaks confirmations and feedback using Piper TTS")
        tts_layout.addWidget(self.tts_feature_toggle)

        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)

        # Integrations Section (TICKET-FEAT-001: Credentials management)
        integrations_group = QGroupBox("Integrations")
        integrations_layout = QVBoxLayout()
        integrations_layout.setSpacing(8)
        
        # Salesforce button
        salesforce_btn = QPushButton("🌩️  Configure Salesforce")
        salesforce_btn.setToolTip("Set Salesforce credentials (username, password, security token, domain)")
        salesforce_btn.clicked.connect(self._open_salesforce_config)
        integrations_layout.addWidget(salesforce_btn)
        
        # Microsoft Teams button
        teams_btn = QPushButton("👥 Configure Microsoft Teams")
        teams_btn.setToolTip("Set Teams credentials (client ID, client secret, tenant ID)")
        teams_btn.clicked.connect(self._open_teams_config)
        integrations_layout.addWidget(teams_btn)
        
        # Slack button
        slack_btn = QPushButton("💬 Configure Slack")
        slack_btn.setToolTip("Set Slack bot token")
        slack_btn.clicked.connect(self._open_slack_config)
        integrations_layout.addWidget(slack_btn)
        
        # Microsoft 365 button
        m365_btn = QPushButton("📧 Configure Microsoft 365")
        m365_btn.setToolTip("Set Microsoft 365 credentials (client ID, client secret, username)")
        m365_btn.clicked.connect(self._open_m365_config)
        integrations_layout.addWidget(m365_btn)
        
        integrations_group.setLayout(integrations_layout)
        layout.addWidget(integrations_group)
        
        # Visual Feedback Section (TICKET-FEAT-004: UI configuration)
        visual_group = QGroupBox("Visual Feedback")
        visual_layout = QFormLayout()
        visual_layout.setSpacing(8)
        
        # Load visual feedback settings from config.json
        visual_config = self._load_visual_config()
        
        # Screenshot overlay position
        self.screenshot_position_combo = QComboBox()
        self.screenshot_position_combo.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])
        current_pos = visual_config.get("screenshot_position", "bottom-right")
        idx = self.screenshot_position_combo.findText(current_pos)
        if idx >= 0:
            self.screenshot_position_combo.setCurrentIndex(idx)
        self.screenshot_position_combo.setToolTip("Position of the screenshot preview overlay")
        visual_layout.addRow("Screenshot Position:", self.screenshot_position_combo)
        
        # Screenshot max size slider
        from PySide6.QtWidgets import QSlider
        self.screenshot_size_slider = QSlider(Qt.Horizontal)
        self.screenshot_size_slider.setMinimum(100)
        self.screenshot_size_slider.setMaximum(400)
        self.screenshot_size_slider.setValue(visual_config.get("screenshot_max_size", 200))
        self.screenshot_size_slider.setToolTip("Maximum size for screenshot preview (pixels)")
        
        self.screenshot_size_label = QLabel(f"{self.screenshot_size_slider.value()} px")
        self.screenshot_size_slider.valueChanged.connect(
            lambda v: self.screenshot_size_label.setText(f"{v} px")
        )
        
        size_row = QHBoxLayout()
        size_row.addWidget(self.screenshot_size_slider, 1)
        size_row.addWidget(self.screenshot_size_label)
        visual_layout.addRow("Screenshot Max Size:", size_row)
        
        # Highlight color picker (simplified - just show the value as text for now)
        self.highlight_color_input = QLineEdit()
        self.highlight_color_input.setText(visual_config.get("highlight_color", "#FF0000"))
        self.highlight_color_input.setPlaceholderText("#FF0000")
        self.highlight_color_input.setToolTip("Color for UI element highlights (hex format)")
        self.highlight_color_input.setMaxLength(7)
        visual_layout.addRow("Highlight Color:", self.highlight_color_input)
        
        # Highlight width slider
        self.highlight_width_slider = QSlider(Qt.Horizontal)
        self.highlight_width_slider.setMinimum(1)
        self.highlight_width_slider.setMaximum(10)
        self.highlight_width_slider.setValue(visual_config.get("highlight_width", 3))
        self.highlight_width_slider.setToolTip("Width of element highlight borders")
        
        self.highlight_width_label = QLabel(f"{self.highlight_width_slider.value()} px")
        self.highlight_width_slider.valueChanged.connect(
            lambda v: self.highlight_width_label.setText(f"{v} px")
        )
        
        width_row = QHBoxLayout()
        width_row.addWidget(self.highlight_width_slider, 1)
        width_row.addWidget(self.highlight_width_label)
        visual_layout.addRow("Highlight Width:", width_row)
        
        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)

        # Appearance Settings (from config.ini [ui])
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(8)

        current_theme = self.ini_config.get("ui", "theme", fallback="light")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.setToolTip("Choose between light and dark overlay theme")
        appearance_layout.addRow("Overlay Theme:", self.theme_combo)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        layout.addStretch()

        # Set content to scroll area
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Buttons at bottom
        button_container = QFrame()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(16, 12, 16, 16)
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary_btn")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.setObjectName("primary_btn")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)

        main_layout.addWidget(button_container)

        root_layout.addWidget(self.container)
        
        # Apply overlay-matching styles
        self._apply_styles()

    def _apply_styles(self):
        """Apply overlay-matching styles to the configuration window"""
        if self._dark_mode:
            # Dark mode styling matching overlay dark mode
            self.setStyleSheet("""
                /* Main container with dark gradient */
                #container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #3D4147, stop:1 #2C3036);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.15);
                }
                
                /* Header styling */
                #header {
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.2);
                }
                
                #title {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 14px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                #close_btn {
                    background: rgba(255, 152, 146, 0.9);
                    border: none;
                    border-radius: 12px;
                    color: rgba(0, 0, 0, 0.5);
                    font-size: 12px;
                    font-weight: bold;
                }
                #close_btn:hover {
                    background: #ff8580;
                    color: rgba(0, 0, 0, 0.8);
                }
                
                /* Scroll area */
                #scroll_area {
                    background: transparent;
                }
                #content {
                    background: transparent;
                }
                
                /* Group boxes */
                QGroupBox {
                    font-weight: 600;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    letter-spacing: 0.03em;
                    border: 1px solid rgba(255,255,255,0.25);
                    border-radius: 10px;
                    margin-top: 14px;
                    padding: 8px 10px;
                    padding-top: 12px;
                    background: rgba(255,255,255,0.08);
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 6px;
                    color: rgba(255, 255, 255, 0.9);
                    background: transparent;
                }
                
                /* Labels */
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                /* Combo boxes and line edits */
                QComboBox, QLineEdit {
                    background-color: rgba(60, 65, 75, 0.9);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: white;
                    font-size: 11px;
                    selection-background-color: #20E3B2;
                }
                QComboBox:hover, QLineEdit:hover {
                    border-color: #20E3B2;
                    background-color: rgba(70, 75, 85, 0.95);
                }
                QComboBox:focus, QLineEdit:focus {
                    border: 2px solid #20E3B2;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox QAbstractItemView {
                    background-color: #3D4147;
                    border: 1px solid rgba(255,255,255,0.3);
                    selection-background-color: #20E3B2;
                    selection-color: white;
                    color: white;
                }
                
                /* Buttons */
                QPushButton {
                    background-color: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: 500;
                    font-size: 11px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.2);
                    border-color: rgba(255,255,255,0.5);
                }
                QPushButton:pressed {
                    background-color: rgba(255,255,255,0.25);
                }
                
                /* Primary button (Save) */
                #primary_btn {
                    background-color: rgba(32, 227, 178, 0.8);
                    border: 1px solid #20E3B2;
                    color: white;
                }
                #primary_btn:hover {
                    background-color: rgba(32, 227, 178, 0.95);
                    border-color: #3DFFD6;
                }
                
                /* Secondary button (Cancel) */
                #secondary_btn {
                    background-color: rgba(255,255,255,0.08);
                }
                
                /* Checkboxes */
                QCheckBox {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 11px;
                    spacing: 8px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid rgba(255,255,255,0.4);
                    border-radius: 5px;
                    background-color: rgba(255,255,255,0.1);
                }
                QCheckBox::indicator:hover {
                    border-color: #20E3B2;
                }
                QCheckBox::indicator:checked {
                    background-color: rgba(32, 227, 178, 0.8);
                    border-color: #20E3B2;
                }
                
                /* Button container */
                #button_container {
                    background: transparent;
                    border-top: 1px solid rgba(255,255,255,0.2);
                }
                
                /* Scrollbar styling */
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
            """)
        else:
            # Light mode styling - improved contrast with darker grey tones
            self.setStyleSheet("""
                /* Main container with medium grey gradient for better readability */
                #container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #5A5F66, stop:1 #474C54);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.2);
                }
                
                /* Header styling */
                #header {
                background: transparent;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }
            
            #title {
                color: rgba(255, 255, 255, 0.95);
                font-size: 14px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            
            #close_btn {
                background: rgba(255, 152, 146, 0.9);
                border: none;
                border-radius: 12px;
                color: rgba(0, 0, 0, 0.5);
                font-size: 12px;
                font-weight: bold;
            }
            #close_btn:hover {
                background: #ff8580;
                color: rgba(0, 0, 0, 0.8);
            }
            
            /* Scroll area */
            #scroll_area {
                background: transparent;
            }
            #content {
                background: transparent;
            }
            
            /* Group boxes */
            QGroupBox {
                font-weight: 600;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                letter-spacing: 0.03em;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 10px;
                margin-top: 14px;
                padding: 8px 10px;
                padding-top: 12px;
                background: rgba(255,255,255,0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: rgba(255, 255, 255, 0.95);
                background: transparent;
            }
            
            /* Labels */
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            
            /* Combo boxes and line edits */
            QComboBox, QLineEdit {
                background-color: rgba(80, 85, 95, 0.9);
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 6px;
                padding: 6px 10px;
                color: white;
                font-size: 11px;
                selection-background-color: #20E3B2;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: #20E3B2;
                background-color: rgba(90, 95, 105, 0.95);
            }
            QComboBox:focus, QLineEdit:focus {
                border: 2px solid #20E3B2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #5A5F66;
                border: 1px solid rgba(255,255,255,0.3);
                selection-background-color: #20E3B2;
                selection-color: white;
                color: white;
            }
            
            /* Buttons */
            QPushButton {
                background-color: rgba(255,255,255,0.15);
                border: 1px solid rgba(255,255,255,0.35);
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.25);
                border-color: rgba(255,255,255,0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,0.3);
            }
            
            /* Primary button (Save) */
            #primary_btn {
                background-color: rgba(32, 227, 178, 0.8);
                border: 1px solid #20E3B2;
                color: white;
            }
            #primary_btn:hover {
                background-color: rgba(32, 227, 178, 0.95);
                border-color: #3DFFD6;
            }
            
            /* Secondary button (Cancel) */
            #secondary_btn {
                background-color: rgba(255,255,255,0.1);
            }
            
            /* Checkboxes */
            QCheckBox {
                color: rgba(255, 255, 255, 0.95);
                font-size: 11px;
                spacing: 8px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(255,255,255,0.5);
                border-radius: 5px;
                background-color: rgba(255,255,255,0.15);
            }
            QCheckBox::indicator:hover {
                border-color: #20E3B2;
            }
            QCheckBox::indicator:checked {
                background-color: rgba(32, 227, 178, 0.8);
                border-color: #20E3B2;
            }
            
            /* Button container */
            #button_container {
                background: transparent;
                border-top: 1px solid rgba(255,255,255,0.2);
            }
            
            /* Scrollbar styling */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.35);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

    def _load_config(self):
        """Load current configuration into UI from passed config dict"""
        # Override with passed config if present
        if "llm_provider" in self.config:
            index = self.llm_provider.findText(self.config["llm_provider"])
            if index >= 0:
                self.llm_provider.setCurrentIndex(index)

        if "llm_model" in self.config:
            self.llm_model.setText(self.config["llm_model"])

        if "stt_model" in self.config:
            index = self.stt_model.findText(self.config["stt_model"], Qt.MatchContains)
            if index >= 0:
                self.stt_model.setCurrentIndex(index)

        if "language" in self.config:
            index = self.language_combo.findText(self.config["language"])
            if index >= 0:
                self.language_combo.setCurrentIndex(index)

        # Load feature toggles from config dict if present
        if "llm_feature_enabled" in self.config:
            self.llm_feature_toggle.setChecked(self.config["llm_feature_enabled"])

        if "vision_feature_enabled" in self.config:
            self.vision_feature_toggle.setChecked(self.config["vision_feature_enabled"])

        if "learning_feature_enabled" in self.config:
            self.learning_feature_toggle.setChecked(self.config["learning_feature_enabled"])

        if "semantic_correction_enabled" in self.config:
            self.semantic_correction_toggle.setChecked(self.config["semantic_correction_enabled"])

        if "tts_feature_enabled" in self.config:
            self.tts_feature_toggle.setChecked(self.config["tts_feature_enabled"])

        if "theme" in self.config:
            index = self.theme_combo.findText(self.config["theme"])
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)

    def _open_dashboard(self):
        """
        Open main dashboard window
        
        Since the Dashboard now uses PySide6 (same as ConfigMiniWindow),
        it can be opened directly within the same process.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from janus.ui.dashboard import DashboardWindow
            
            logger.info("Opening dashboard...")
            self._dashboard = DashboardWindow(parent=None)
            self._dashboard.show()
        except Exception as e:
            logger.error(f"Failed to open dashboard: {e}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Error Opening Dashboard")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Could not open dashboard")
            msg.setInformativeText(str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def _open_config_file(self):
        """Open config.ini file in default text editor"""
        import subprocess
        import sys
        import logging
        
        logger = logging.getLogger(__name__)
        config_path = Path(CONFIG_INI_PATH).absolute()
        
        # Validate the file is a .ini file and exists
        if not config_path.exists():
            msg = QMessageBox(self)
            msg.setWindowTitle("Config File Not Found")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("config.ini not found")
            msg.setInformativeText(f"Expected location: {config_path}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return
        
        # Validate the file has .ini extension for security
        if config_path.suffix.lower() != ".ini":
            logger.warning(f"Refusing to open non-.ini file: {config_path}")
            return
        
        try:
            if sys.platform == "darwin":  # macOS
                # Use shell=False explicitly for security
                subprocess.run(["open", "-e", str(config_path)], shell=False, check=False)
            elif sys.platform == "win32":  # Windows
                # os.startfile is safe for opening known file types
                os.startfile(str(config_path))
            else:  # Linux
                # Try xdg-open first (most portable)
                try:
                    subprocess.run(["xdg-open", str(config_path)], shell=False, check=False)
                except FileNotFoundError:
                    # Fall back to common editors
                    opened = False
                    for editor in ["gedit", "kate", "nano", "vim"]:
                        try:
                            subprocess.run([editor, str(config_path)], shell=False, check=False)
                            opened = True
                            break
                        except FileNotFoundError:
                            continue
                    if not opened:
                        raise FileNotFoundError("No suitable text editor found")
        except FileNotFoundError as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error Opening Config")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Could not open config.ini")
            msg.setInformativeText(f"No suitable text editor found.\n\nPath: {config_path}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
        except OSError as e:
            logger.error(f"OS error opening config file: {e}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Error Opening Config")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Could not open config.ini")
            msg.setInformativeText(f"Error: {e}\n\nPath: {config_path}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def _save_config(self):
        """Save configuration to config.ini and emit signal"""
        config_path = Path(CONFIG_INI_PATH)
        
        # Update config.ini with new values
        try:
            # Update [features] section
            if not self.ini_config.has_section("features"):
                self.ini_config.add_section("features")
            self.ini_config.set("features", "enable_llm_reasoning", 
                               str(self.llm_feature_toggle.isChecked()).lower())
            self.ini_config.set("features", "enable_vision", 
                               str(self.vision_feature_toggle.isChecked()).lower())
            self.ini_config.set("features", "enable_learning", 
                               str(self.learning_feature_toggle.isChecked()).lower())
            self.ini_config.set("features", "enable_semantic_correction", 
                               str(self.semantic_correction_toggle.isChecked()).lower())
            
            # Update [llm] section
            if not self.ini_config.has_section("llm"):
                self.ini_config.add_section("llm")
            self.ini_config.set("llm", "provider", self.llm_provider.currentText())
            self.ini_config.set("llm", "model", self.llm_model.text())
            
            # Update [whisper] section
            if not self.ini_config.has_section("whisper"):
                self.ini_config.add_section("whisper")
            self.ini_config.set("whisper", "model_size", self.stt_model.currentText())
            
            # Update [language] section
            if not self.ini_config.has_section("language"):
                self.ini_config.add_section("language")
            self.ini_config.set("language", "default", self.language_combo.currentText())
            
            # Update [tts] section
            if not self.ini_config.has_section("tts"):
                self.ini_config.add_section("tts")
            self.ini_config.set("tts", "enable_tts", 
                               str(self.tts_feature_toggle.isChecked()).lower())
            
            # Update [ui] section (theme)
            if not self.ini_config.has_section("ui"):
                self.ini_config.add_section("ui")
            self.ini_config.set("ui", "theme", self.theme_combo.currentText())
            
            # Write to file
            with open(config_path, "w") as f:
                self.ini_config.write(f)
            
            # Save visual feedback settings to config.json (TICKET-FEAT-004)
            self._save_visual_config()
            
            # Show success message
            msg = QMessageBox(self)
            msg.setWindowTitle("Configuration Saved")
            msg.setIcon(QMessageBox.Information)
            msg.setText("✅ Configuration saved successfully!")
            msg.setInformativeText(
                "Changes have been saved to config.ini.\n\n"
                "Theme changes apply immediately. Some other changes may require a restart."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error Saving Configuration")
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Failed to save configuration")
            msg.setInformativeText(f"Error: {e}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return

        # Emit config change signal with new values
        config = self.get_config()
        self.config_changed.emit(config)
        self.accept()

    def get_config(self) -> dict:
        """Get current configuration from UI widgets"""
        return {
            "llm_provider": self.llm_provider.currentText(),
            "llm_model": self.llm_model.text(),
            "stt_model": self.stt_model.currentText(),
            "language": self.language_combo.currentText(),
            "llm_feature_enabled": self.llm_feature_toggle.isChecked(),
            "vision_feature_enabled": self.vision_feature_toggle.isChecked(),
            "learning_feature_enabled": self.learning_feature_toggle.isChecked(),
            "semantic_correction_enabled": self.semantic_correction_toggle.isChecked(),
            "tts_feature_enabled": self.tts_feature_toggle.isChecked(),
            "theme": self.theme_combo.currentText(),
        }
    
    def _load_visual_config(self) -> dict:
        """
        Load visual feedback configuration from config.json
        TICKET-FEAT-004: Visual feedback settings
        """
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        visual_config = {
            "screenshot_position": "bottom-right",
            "screenshot_max_size": 200,
            "highlight_color": "#FF0000",
            "highlight_width": 3,
        }
        
        try:
            config_json_path = Path("config.json")
            if config_json_path.exists():
                with open(config_json_path, "r") as f:
                    cfg = json.load(f)
                    if "ui" in cfg:
                        if "screenshot_position" in cfg["ui"]:
                            visual_config["screenshot_position"] = cfg["ui"]["screenshot_position"].get("value", "bottom-right")
                        if "screenshot_max_size" in cfg["ui"]:
                            visual_config["screenshot_max_size"] = cfg["ui"]["screenshot_max_size"].get("value", 200)
                        if "highlight_color" in cfg["ui"]:
                            visual_config["highlight_color"] = cfg["ui"]["highlight_color"].get("value", "#FF0000")
                        if "highlight_width" in cfg["ui"]:
                            visual_config["highlight_width"] = cfg["ui"]["highlight_width"].get("value", 3)
        except Exception as e:
            logger.debug(f"Could not load visual config from config.json: {e}")
        
        return visual_config
    
    def _save_visual_config(self):
        """
        Save visual feedback configuration to config.json
        TICKET-FEAT-004: Visual feedback settings
        """
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            config_json_path = Path("config.json")
            
            # Load existing config or create new
            cfg = {}
            if config_json_path.exists():
                with open(config_json_path, "r") as f:
                    cfg = json.load(f)
            
            # Ensure ui section exists
            if "ui" not in cfg:
                cfg["ui"] = {}
            
            # Update visual settings
            cfg["ui"]["screenshot_position"] = {
                "value": self.screenshot_position_combo.currentText(),
                "options": ["top-right", "top-left", "bottom-right", "bottom-left"],
                "label": "Screenshot Overlay Position",
            }
            cfg["ui"]["screenshot_max_size"] = {
                "value": self.screenshot_size_slider.value(),
                "min": 100,
                "max": 400,
                "label": "Screenshot Max Size (px)",
            }
            cfg["ui"]["highlight_color"] = {
                "value": self.highlight_color_input.text(),
                "label": "Highlight Color",
            }
            cfg["ui"]["highlight_width"] = {
                "value": self.highlight_width_slider.value(),
                "min": 1,
                "max": 10,
                "label": "Highlight Width",
            }
            
            # Save back to file
            with open(config_json_path, "w") as f:
                json.dump(cfg, f, indent=2)
            
            logger.info("Visual feedback config saved to config.json")
            
        except Exception as e:
            logger.error(f"Failed to save visual config: {e}")
    
    def _open_salesforce_config(self):
        """Open Salesforce credentials dialog (TICKET-FEAT-001)"""
        from janus.ui.config_ui_settings import CredentialDialog
        
        # Load current credentials from config.ini
        current = {
            "username": self.ini_config.get("salesforce", "username", fallback=""),
            "password": self.ini_config.get("salesforce", "password", fallback=""),
            "security_token": self.ini_config.get("salesforce", "security_token", fallback=""),
            "domain": self.ini_config.get("salesforce", "domain", fallback="login.salesforce.com"),
        }
        
        dialog = CredentialDialog(
            parent=self,
            title="Salesforce Credentials",
            fields=[
                ("Username:", "username", current.get("username", "")),
                ("Password:", "password", current.get("password", ""), True),
                ("Security Token:", "security_token", current.get("security_token", ""), True),
                ("Domain:", "domain", current.get("domain", "login.salesforce.com")),
            ]
        )
        
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            
            # Save to config.ini
            if not self.ini_config.has_section("salesforce"):
                self.ini_config.add_section("salesforce")
            
            self.ini_config.set("salesforce", "username", values.get("username", ""))
            self.ini_config.set("salesforce", "password", values.get("password", ""))
            self.ini_config.set("salesforce", "security_token", values.get("security_token", ""))
            self.ini_config.set("salesforce", "domain", values.get("domain", "login.salesforce.com"))
            
            # Write to file
            with open(CONFIG_INI_PATH, "w") as f:
                self.ini_config.write(f)
            
            QMessageBox.information(self, "Success", "✅ Salesforce credentials saved!")
    
    def _open_teams_config(self):
        """Open Microsoft Teams credentials dialog (TICKET-FEAT-001)"""
        from janus.ui.config_ui_settings import CredentialDialog
        
        # Load current credentials
        current = {
            "client_id": self.ini_config.get("messaging", "teams_client_id", fallback=""),
            "client_secret": self.ini_config.get("messaging", "teams_client_secret", fallback=""),
            "tenant_id": self.ini_config.get("messaging", "teams_tenant_id", fallback=""),
        }
        
        dialog = CredentialDialog(
            parent=self,
            title="Microsoft Teams Credentials",
            fields=[
                ("Client ID:", "client_id", current.get("client_id", "")),
                ("Client Secret:", "client_secret", current.get("client_secret", ""), True),
                ("Tenant ID:", "tenant_id", current.get("tenant_id", "")),
            ]
        )
        
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            
            # Save to config.ini
            if not self.ini_config.has_section("messaging"):
                self.ini_config.add_section("messaging")
            
            self.ini_config.set("messaging", "teams_client_id", values.get("client_id", ""))
            self.ini_config.set("messaging", "teams_client_secret", values.get("client_secret", ""))
            self.ini_config.set("messaging", "teams_tenant_id", values.get("tenant_id", ""))
            
            # Write to file
            with open(CONFIG_INI_PATH, "w") as f:
                self.ini_config.write(f)
            
            QMessageBox.information(self, "Success", "✅ Teams credentials saved!")
    
    def _open_slack_config(self):
        """Open Slack credentials dialog (TICKET-FEAT-001)"""
        from janus.ui.config_ui_settings import CredentialDialog
        
        # Load current credentials
        current_token = self.ini_config.get("messaging", "slack_bot_token", fallback="")
        
        dialog = CredentialDialog(
            parent=self,
            title="Slack Credentials",
            fields=[
                ("Bot Token:", "bot_token", current_token, True),
            ]
        )
        
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            
            # Save to config.ini
            if not self.ini_config.has_section("messaging"):
                self.ini_config.add_section("messaging")
            
            self.ini_config.set("messaging", "slack_bot_token", values.get("bot_token", ""))
            
            # Write to file
            with open(CONFIG_INI_PATH, "w") as f:
                self.ini_config.write(f)
            
            QMessageBox.information(self, "Success", "✅ Slack credentials saved!")
    
    def _open_m365_config(self):
        """Open Microsoft 365 credentials dialog (TICKET-FEAT-001)"""
        from janus.ui.config_ui_settings import CredentialDialog
        
        # Load current credentials
        current = {
            "client_id": self.ini_config.get("microsoft365", "client_id", fallback=""),
            "client_secret": self.ini_config.get("microsoft365", "client_secret", fallback=""),
            "username": self.ini_config.get("microsoft365", "username", fallback=""),
        }
        
        dialog = CredentialDialog(
            parent=self,
            title="Microsoft 365 Credentials",
            fields=[
                ("Client ID:", "client_id", current.get("client_id", "")),
                ("Client Secret:", "client_secret", current.get("client_secret", ""), True),
                ("Username:", "username", current.get("username", "")),
            ]
        )
        
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            
            # Save to config.ini
            if not self.ini_config.has_section("microsoft365"):
                self.ini_config.add_section("microsoft365")
            
            self.ini_config.set("microsoft365", "client_id", values.get("client_id", ""))
            self.ini_config.set("microsoft365", "client_secret", values.get("client_secret", ""))
            self.ini_config.set("microsoft365", "username", values.get("username", ""))
            
            # Write to file
            with open(CONFIG_INI_PATH, "w") as f:
                self.ini_config.write(f)
            
            QMessageBox.information(self, "Success", "✅ Microsoft 365 credentials saved!")
    
    def mousePressEvent(self, event):
        """Enable dragging the window"""
        from PySide6.QtCore import QPoint
        if event.button() == Qt.LeftButton:
            # Use globalPosition() with proper type handling for PySide6
            global_pos = event.globalPosition()
            self._drag_pos = QPoint(int(global_pos.x()), int(global_pos.y())) - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        from PySide6.QtCore import QPoint
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            global_pos = event.globalPosition()
            new_pos = QPoint(int(global_pos.x()), int(global_pos.y())) - self._drag_pos
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Reset drag position on release"""
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# Example usage
if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Example config matching the new structure
    current_config = {
        "llm_provider": "ollama",
        "llm_model": "llama3.2",
        "stt_model": "small",
        "language": "fr",
        "llm_feature_enabled": True,
        "vision_feature_enabled": True,
        "learning_feature_enabled": True,
        "semantic_correction_enabled": True,
        "tts_feature_enabled": True,
    }

    dialog = ConfigMiniWindow(current_config=current_config)

    def on_config_changed(config):
        print("Configuration saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")

    dialog.config_changed.connect(on_config_changed)
    dialog.exec()

    sys.exit(0)
