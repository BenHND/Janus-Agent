import sys
import math
import json
import configparser
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import (
    QByteArray, QObject, QPoint, QSize, Qt, QTimer, Signal, 
    QPropertyAnimation, QEasingCurve, Property, QRectF
)
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPixmap, QLinearGradient, QBrush, QPen
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, 
    QPushButton, QVBoxLayout, QWidget, QFrame
)

# Import overlay types (MicState, StatusState)
from .overlay_types import MicState, StatusState
from .overlay_constants import get_status_text as get_status_text_i18n, MIC_OFF_SVG, MIC_ON_SVG

# --- CONFIGURATION FALLBACK ---
try:
    from janus.ui.config_mini_window import ConfigMiniWindow
except ImportError:
    ConfigMiniWindow = None


# Valid theme values
VALID_THEMES = ("light", "dark")


def get_theme_from_config(config_path: str = "config.ini") -> str:
    """
    Load theme setting from config.ini.
    
    Args:
        config_path: Path to config.ini file (default: "config.ini" in current directory)
    
    Returns:
        Theme string ("light" or "dark"). Defaults to "light" if not found or invalid.
    """
    config = configparser.ConfigParser()
    path = Path(config_path)
    if path.exists():
        try:
            config.read(path)
            theme = config.get("ui", "theme", fallback="light")
            # Validate theme value
            if theme in VALID_THEMES:
                return theme
        except (configparser.Error, OSError):
            pass
    return "light"

# --- SVG RESOURCES ---
SVG_MIC = """<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>"""
SVG_SETTINGS = """<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>"""
SVG_CHAT = """<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/></svg>"""

# --- HELPERS ---
def add_diffuse_shadow(widget, blur=25, x=0, y=0, alpha=80):
    """Add a diffuse shadow effect to a widget (centered by default when x,y=0)"""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(x)
    eff.setYOffset(y)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return eff

# --- CUSTOM WIDGETS ---

class MacOsBtn(QPushButton):
    """Bouton traffic light sans bordure"""
    def __init__(self, color, hover_color, symbol, size=12):
        super().__init__()
        self.setFixedSize(size, size)
        self.symbol = symbol
        self.color = color
        self.hover_color = hover_color
        self.base_style = f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: {size//2}px;
                color: rgba(0, 0, 0, 0.5); 
                font-weight: 900;
                font-size: 9px;
                padding-bottom: 2px;
                text-align: center;
            }}
        """
        self.setStyleSheet(self.base_style)
        self.setText("") 

    def enterEvent(self, event):
        self.setText(self.symbol)
        self.setStyleSheet(self.base_style.replace(self.color, self.hover_color))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setText("")
        self.setStyleSheet(self.base_style)
        super().leaveEvent(event)

class AnimatedMicBtn(QPushButton):
    """
    Microphone button with squircle shape and:
    1. Metallic gradient (Silver) or dark mode styling
    2. Smooth color transition on hover (animation)
    """
    def __init__(self, icon_pixmap, parent=None, dark_mode=False):
        super().__init__(parent)
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        self.icon_pixmap = icon_pixmap
        self.icon_pixmap_off = None  # Will be set later for mic off state
        self.icon_pixmap_on = None   # Will be set later for mic on state
        self._hover_progress = 0.0 # 0.0 = Idle, 1.0 = Hover
        self._dark_mode = dark_mode

        # Animation pour la transition de couleur
        self.anim = QPropertyAnimation(self, b"hover_progress")
        self.anim.setDuration(200) # 200ms transition
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
    
    def set_dark_mode(self, dark_mode: bool):
        """Set dark mode and trigger repaint"""
        self._dark_mode = dark_mode
        self.update()
    
    def set_icon(self, icon_pixmap):
        """Update the icon displayed on the button"""
        self.icon_pixmap = icon_pixmap
        self.update()  # Trigger repaint

    @Property(float)
    def hover_progress(self): return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, value):
        self._hover_progress = value
        self.update() # Redessiner

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- 1. DESSIN DU FOND (GRADIENT ANIMÉ) ---
        if self._dark_mode:
            # Dark mode colors (based on provided mockup)
            idle_start = QColor("#5A5F66")  # Darker grey top
            idle_end = QColor("#3D4147")    # Darker grey bottom
            hover_start = QColor("#686D75") # Slightly lighter on hover
            hover_end = QColor("#4A4F57")
            border_color = QColor(255, 255, 255, 60)  # Subtle white border
        else:
            # Light mode colors (original)
            idle_start = QColor("#F7F8FA")
            idle_end = QColor("#C4C9D0")
            hover_start = QColor("#FFFFFF")
            hover_end = QColor("#DCE1E8")
            border_color = QColor(255, 255, 255, 150)

        # Interpolation des couleurs selon hover_progress
        def interpolate(c1, c2, ratio):
            r = c1.red() + (c2.red() - c1.red()) * ratio
            g = c1.green() + (c2.green() - c1.green()) * ratio
            b = c1.blue() + (c2.blue() - c1.blue()) * ratio
            return QColor(int(r), int(g), int(b))

        current_start = interpolate(idle_start, hover_start, self._hover_progress)
        current_end = interpolate(idle_end, hover_end, self._hover_progress)

        # Création du Gradient Vertical
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, current_start)
        grad.setColorAt(1, current_end)

        # Dessin du Squircle (Rectangle arrondi)
        rect = self.rect().adjusted(1, 1, -1, -1) # Marge pour border
        
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 17, 17) # Radius 17px

        # --- 2. DESSIN DE L'ICONE ---
        if not self.icon_pixmap.isNull():
            icon_size = 24
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            painter.drawPixmap(x, y, icon_size, icon_size, self.icon_pixmap)

        painter.end()

    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover_progress); self.anim.setEndValue(1.0); self.anim.start()
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover_progress); self.anim.setEndValue(0.0); self.anim.start()


class SharpRotatingSettingsBtn(QPushButton):
    """Roue dentée NETTE (Rendu HD + Smooth Transform)"""
    
    # Icon sizing constant (proportion of button size)
    ICON_SIZE_RATIO = 0.8
    
    def __init__(self, svg_content, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        
        renderer = QSvgRenderer(QByteArray(svg_content.encode()))
        self.hd_pixmap = QPixmap(128, 128) 
        self.hd_pixmap.fill(Qt.transparent)
        p = QPainter(self.hd_pixmap)
        renderer.render(p)
        p.end()

        self._rotation = 0
        self.setCursor(Qt.PointingHandCursor)
        self.anim = QPropertyAnimation(self, b"rotation")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(float)
    def rotation(self): return self._rotation

    @rotation.setter
    def rotation(self, angle):
        self._rotation = angle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._rotation)
        
        # Scale icon size proportionally to button size
        target_size = min(self.width(), self.height()) * self.ICON_SIZE_RATIO
        offset = target_size / 2
        painter.drawPixmap(QRectF(-offset, -offset, target_size, target_size), self.hd_pixmap, QRectF(self.hd_pixmap.rect()))
        painter.end()

    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._rotation); self.anim.setEndValue(90); self.anim.start()
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._rotation); self.anim.setEndValue(0); self.anim.start()


class AnimatedChatBtn(QPushButton):
    """
    Chat button with smooth hover animation.
    Similar to settings button but with scale animation instead of rotation.
    """
    def __init__(self, svg_content, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        
        renderer = QSvgRenderer(QByteArray(svg_content.encode()))
        self.hd_pixmap = QPixmap(128, 128) 
        self.hd_pixmap.fill(Qt.transparent)
        p = QPainter(self.hd_pixmap)
        renderer.render(p)
        p.end()

        self._scale = 1.0
        self.setCursor(Qt.PointingHandCursor)
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(float)
    def scale(self): return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        
        target_size = 22
        offset = target_size / 2
        painter.drawPixmap(QRectF(-offset, -offset, target_size, target_size), self.hd_pixmap, QRectF(self.hd_pixmap.rect()))
        painter.end()

    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._scale); self.anim.setEndValue(1.15); self.anim.start()
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._scale); self.anim.setEndValue(1.0); self.anim.start()

# --- SIGNALS ---

class OverlaySignals(QObject):
    set_status_signal = Signal(tuple)  # Changed: now sends (status, text) tuple for i18n
    append_transcript_signal = Signal(str)
    set_mic_state_signal = Signal(object)
    wake_word_detected_signal = Signal()
    clear_transcript_signal = Signal()
    show_eco_mode_signal = Signal()  # TICKET-PERF-002: Show eco mode indicator
    hide_eco_mode_signal = Signal()  # TICKET-PERF-002: Hide eco mode indicator

# --- MAIN CLASS ---

class OverlayUI(QWidget):
    def __init__(self, on_mic_toggle=None, on_config=None, on_text_submit=None, config_path="overlay_pos.json"):
        super().__init__()
        self.on_mic_toggle = on_mic_toggle
        self.on_config = on_config
        self.on_text_submit = on_text_submit  # NEW: Callback for text input submission
        self.config_path = config_path
        self.chat_window = None  # NEW: Reference to chat window (set from ui_mode.py)
        
        self.mic_enabled = False
        self.mic_state = MicState.IDLE
        self._drag_pos = None  # Use None instead of QPoint() to properly detect drag state
        
        # Load theme from config
        self._dark_mode = get_theme_from_config() == "dark"
        
        self.signals = OverlaySignals()
        self.signals.set_status_signal.connect(lambda data: self.set_status(*data) if isinstance(data, tuple) else self.set_status(data))
        self.signals.append_transcript_signal.connect(self.append_transcript)
        self.signals.set_mic_state_signal.connect(self.set_mic_state)
        self.signals.clear_transcript_signal.connect(self.clear_transcript)
        self.signals.show_eco_mode_signal.connect(self.show_eco_mode)
        self.signals.hide_eco_mode_signal.connect(self.hide_eco_mode)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate)
        self.anim_phase = 0
        
        # Assets - Create pixmaps for both mic states
        self.svg_settings_white = SVG_SETTINGS.replace("currentColor", "#FFFFFF")
        self.svg_chat_white = SVG_CHAT.replace("currentColor", "#FFFFFF")
        self.pix_mic_off = self._svg_to_pixmap(MIC_OFF_SVG, "#FFFFFF")  # Outline version
        self.pix_mic_on = self._svg_to_pixmap(MIC_ON_SVG, "#FFFFFF")    # Solid version

        self._setup_window()
        self._init_ui()
        self._load_pos()

    def _svg_to_pixmap(self, svg, color_hex):
        svg = svg.replace("currentColor", color_hex)
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pix = QPixmap(96, 96)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p)
        p.end()
        return pix

    def _setup_window(self):
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(305, 165)  # Reduced width by 5px (from 310) 

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- CONTAINER (243x100) ---
        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setFixedSize(243, 100)  # Reduced width by 5px (from 248)
        
        # 1. OMBRE FENETRE : Douce et moins axée bas
        # TICKET-PERF-005: reduced blur from 30 to 15 for better GPU performance
        add_diffuse_shadow(self.container, blur=15, x=0, y=6, alpha=40)
        
        self.root_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 8, 14, 12)  # Reduced top margin from 12 to 8
        layout.setSpacing(0)

        # --- HEADER ---
        header = QHBoxLayout()
        header.setSpacing(6)
        header.setAlignment(Qt.AlignVCenter)  # Align items vertically centered
        
        # Icones Traffic
        self.btn_close = MacOsBtn(color="#ff9892", hover_color="#ff8580", symbol="✕", size=12) 
        self.btn_close.clicked.connect(self.close)
        header.addWidget(self.btn_close, 0, Qt.AlignVCenter)

        self.btn_min = MacOsBtn(color="#fddb92", hover_color="#fcce72", symbol="−", size=12)
        self.btn_min.clicked.connect(self.showMinimized)
        header.addWidget(self.btn_min, 0, Qt.AlignVCenter)
        
        header.addStretch()
        
        # 2. Titre : "AI-Powered Assistant"
        self.title = QLabel("AI-Powered Assistant")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName("title_label")
        # Ombre très diffuse
        add_diffuse_shadow(self.title, blur=8, x=0, y=0, alpha=60)
        header.addWidget(self.title, 0, Qt.AlignVCenter)
        
        header.addStretch()
        
        # NEW: Settings button in top-right (smaller, 24x24 instead of 30x30)
        self.btn_conf = SharpRotatingSettingsBtn(self.svg_settings_white)
        self.btn_conf.setObjectName("btn_settings")
        self.btn_conf.setFixedSize(24, 24)  # Smaller size for top-right placement
        self.btn_conf.clicked.connect(self._handle_config)
        # Ombre diffuse
        add_diffuse_shadow(self.btn_conf, blur=5, x=0, y=0, alpha=60)
        header.addWidget(self.btn_conf, 0, Qt.AlignVCenter)
        
        layout.addLayout(header)
        layout.addStretch()

        # --- CONTENU ---
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setContentsMargins(0, 0, 0, 2)
        row.setAlignment(Qt.AlignVCenter)  # Align items vertically centered
        
        # 3. Bloc Micro Animé (Custom Widget)
        self.btn_mic = AnimatedMicBtn(self.pix_mic_off, dark_mode=self._dark_mode)  # Start with outline (off state)
        self.btn_mic.icon_pixmap_off = self.pix_mic_off
        self.btn_mic.icon_pixmap_on = self.pix_mic_on
        self.btn_mic.setObjectName("btn_mic") # Pour css éventuel
        self.btn_mic.clicked.connect(self._toggle_mic)
        
        # Ombre du bloc micro : Encore plus légère
        # blur=25, alpha=40
        # TICKET-PERF-005: reduced blur from 25 to 12 for better GPU performance
        self.mic_shadow = add_diffuse_shadow(self.btn_mic, blur=12, x=0, y=0, alpha=40)
        
        row.addWidget(self.btn_mic, 0, Qt.AlignVCenter)
        
        # 4. Texte Central
        text_area = QWidget()
        t_layout = QVBoxLayout(text_area)
        t_layout.setContentsMargins(0,0,0,0)
        t_layout.setAlignment(Qt.AlignVCenter)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("status_label")
        # Ombre très diffuse
        add_diffuse_shadow(self.lbl_status, blur=12, x=0, y=0, alpha=80)
        
        self.lbl_trans = QLabel()
        self.lbl_trans.setVisible(False)
        self.lbl_trans.setWordWrap(True)
        self.lbl_trans.setObjectName("trans_label")
        
        # TICKET-PERF-002: Eco mode indicator
        self.lbl_eco_mode = QLabel("🔋 Mode Éco actif")
        self.lbl_eco_mode.setVisible(False)
        self.lbl_eco_mode.setObjectName("eco_mode_label")
        self.lbl_eco_mode.setAlignment(Qt.AlignCenter)
        # Ombre diffuse
        add_diffuse_shadow(self.lbl_eco_mode, blur=8, x=0, y=0, alpha=60)
        
        t_layout.addWidget(self.lbl_status)
        t_layout.addWidget(self.lbl_trans)
        t_layout.addWidget(self.lbl_eco_mode)
        row.addWidget(text_area, 1, Qt.AlignVCenter)
        
        # NEW: Chat button in content area (replaces settings button position)
        self.btn_chat = AnimatedChatBtn(self.svg_chat_white)
        self.btn_chat.setObjectName("btn_chat")
        self.btn_chat.clicked.connect(self._handle_text_input)
        # Diffuse shadow
        add_diffuse_shadow(self.btn_chat, blur=8, x=0, y=0, alpha=70)
        
        row.addWidget(self.btn_chat, 0, Qt.AlignVCenter)
        layout.addLayout(row)
        
        self._apply_styles()

    def _apply_styles(self):
        if self._dark_mode:
            # Dark mode styling (based on provided mockup)
            self.setStyleSheet("""
                QWidget { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: transparent; }
                
                #container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3D4147, stop:1 #2C3036);
                    border-radius: 22px;
                    border: 1px solid rgba(255,255,255,0.15);
                }

                #title_label { 
                    color: rgba(255, 255, 255, 0.9); 
                    font-size: 11px; 
                    font-weight: 400; 
                    padding-right: 12px;
                }
                
                #status_label { 
                    color: rgba(255, 255, 255, 0.9); 
                    font-size: 16px; 
                    font-weight: 400; 
                }
                #trans_label { color: rgba(255, 255, 255, 0.85); font-size: 14px; }
                #eco_mode_label { 
                    color: rgba(32, 227, 178, 0.95); 
                    font-size: 10px; 
                    font-weight: 500;
                    padding-top: 2px;
                }
                
                #btn_settings { border: none; }
                #dash { background-color: rgba(255,255,255,0.4); border-radius: 1px; }
            """)
        else:
            # Light mode styling (original)
            self.setStyleSheet("""
                QWidget { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: transparent; }
                
                #container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E6E9, stop:1 #B0B5BB);
                    border-radius: 22px;
                    border: 1px solid rgba(255,255,255,0.4);
                }

                #title_label { 
                    color: white; 
                    font-size: 11px; 
                    font-weight: 400; 
                    padding-right: 12px;
                }
                
                #status_label { 
                    color: white; 
                    font-size: 16px; 
                    font-weight: 400; 
                }
                #trans_label { color: rgba(255, 255, 255, 0.95); font-size: 14px; }
                #eco_mode_label { 
                    color: rgba(32, 227, 178, 1.0); 
                    font-size: 10px; 
                    font-weight: 500;
                    padding-top: 2px;
                }
                
                #btn_settings { border: none; }
                #dash { background-color: rgba(255,255,255,0.6); border-radius: 1px; }
            """)

    def get_status_text(self, key):
        """Get status text for the given key using i18n settings"""
        # Handle both enum and string keys for compatibility
        if hasattr(key, 'value'):
            key_str = key.value
        else:
            key_str = key
        
        # Use the centralized i18n function from overlay_constants
        # Get language from janus.i18n module settings (defaults to "fr")
        from janus.i18n import get_language
        language = get_language()
        
        return get_status_text_i18n(key_str, language)

    def _handle_config(self):
        if self.on_config: self.on_config()
        if ConfigMiniWindow:
            # ConfigMiniWindow loads settings from config.ini automatically
            self.cw = ConfigMiniWindow(parent=self)
            # Connect config_changed signal to update theme dynamically
            self.cw.config_changed.connect(self._on_config_changed)
            self.cw.show()

    def _handle_text_input(self):
        """Open text input interface (chat window if available, otherwise dialog)"""
        # If chat window is available, use it
        if self.chat_window:
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
        else:
            # Fallback to simple text input dialog
            from janus.ui.text_input_dialog import StyledTextInputDialog
            
            dialog = StyledTextInputDialog(parent=self, dark_mode=self._dark_mode)
            dialog.text_submitted.connect(self._on_text_submitted)
            dialog.exec()
    
    def _on_text_submitted(self, text: str):
        """Handle text submission from the dialog"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Text input submitted: {text}")
        
        # Emit the text through the transcript signal to show it in the UI
        self.signals.append_transcript_signal.emit(text)
        
        # Call the callback if provided (same as voice transcription)
        if self.on_text_submit:
            self.on_text_submit(text)

    def _on_config_changed(self, config: dict):
        """Handle configuration changes from ConfigMiniWindow"""
        if "theme" in config:
            self.set_theme(config["theme"])

    def _toggle_mic(self):
        self.mic_enabled = not self.mic_enabled
        if self.mic_enabled: self.set_mic_state(MicState.LISTENING)
        else: self.set_mic_state(MicState.MUTED)
        if self.on_mic_toggle: self.on_mic_toggle(self.mic_enabled)

    def _animate(self):
        # Handle both enum and string for mic_state
        state_str = self.mic_state.value if hasattr(self.mic_state, 'value') else self.mic_state
        
        # Define colors for each animated state
        # Colors: (R, G, B, base_alpha, max_alpha)
        state_colors = {
            "listening": (32, 227, 178, 100, 200),   # Green/Teal
            "thinking": (255, 126, 219, 100, 200),   # Pink
            "loading": (0, 191, 255, 80, 180),       # Blue/Cyan
            "error": (255, 59, 48, 120, 220),        # Red
        }
        
        if state_str not in state_colors:
            return
            
        self.anim_phase += 0.15
        val = (math.sin(self.anim_phase) + 1) / 2 
        
        r, g, b, base_alpha, max_alpha = state_colors[state_str]
        color = QColor(r, g, b)
        color.setAlpha(int(base_alpha + (max_alpha - base_alpha) * val))
        self.mic_shadow.setColor(color)
        # TICKET-PERF-005: Reduced blur variation from 20+10*val to 10+5*val for better GPU performance
        self.mic_shadow.setBlurRadius(10 + 5 * val)
        
        # Update status text with animated dots for listening, thinking, and loading states
        # These states should display animated "..." to indicate activity
        animated_text_states = ["listening", "thinking", "loading"]
        if state_str in animated_text_states:
            dots = "." * (int(self.anim_phase * 2) % 4)
            base_text = self.get_status_text(state_str)
            self.lbl_status.setText(f"{base_text}{dots}")

    def set_mic_state(self, state):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"set_mic_state called: state={state}")
        
        self.mic_state = state
        # Handle both enum and string states
        state_str = state.value if hasattr(state, 'value') else state
        logger.debug(f"set_mic_state: state_str={state_str}")
        
        # Update the microphone icon based on state
        # Mic is "on" (solid icon) when listening, thinking, or acting
        # Mic is "off" (outline icon) when idle, muted, loading, or error
        if state_str in ["listening", "thinking", "acting"]:
            self.btn_mic.set_icon(self.pix_mic_on)  # Solid icon for active states
        else:
            self.btn_mic.set_icon(self.pix_mic_off)  # Outline icon for inactive states
        
        # States that should have animated halos
        animated_states = ["listening", "thinking", "loading", "error"]
        
        if state_str in animated_states:
            logger.debug(f"Starting animation timer for state: {state_str}")
            # TICKET-PERF-005: Reduced from 50ms (20 FPS) to 100ms (10 FPS) for better CPU performance
            self.anim_timer.start(100)
            self.mic_shadow.setYOffset(0)
            self.mic_shadow.setXOffset(0)
        else:
            logger.debug(f"Stopping animation timer (state={state_str})")
            self.anim_timer.stop()
            # IDLE: Ombre très légère (alpha 40), centrée, diffuse
            self.mic_shadow.setColor(QColor(0, 0, 0, 40))
            self.mic_shadow.setBlurRadius(25)
            self.mic_shadow.setXOffset(0)
            self.mic_shadow.setYOffset(0)

    def set_status(self, status, text=None):
        """Set status with optional custom text (i18n support)"""
        # Add debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"set_status called: status={status}, text={text}")
        
        self.lbl_trans.setVisible(False)
        self.lbl_status.setVisible(True)
        
        # Handle both enum and string status values
        status_str = status.value if hasattr(status, 'value') else status
        logger.debug(f"status_str={status_str}")
        
        # Set mic state FIRST to stop animation timer before setting text
        # This prevents race condition where animation overwrites the text
        if status_str == "listening": 
            logger.debug("Setting mic state to LISTENING")
            self.set_mic_state(MicState.LISTENING)
        elif status_str in ["thinking", "acting"]: 
            logger.debug(f"Setting mic state to THINKING (status_str={status_str})")
            self.set_mic_state(MicState.THINKING)
        elif status_str == "loading":
            self.set_mic_state(MicState.LOADING)
        elif status_str == "error":
            self.set_mic_state(MicState.ERROR)
        else:
            logger.debug(f"Setting mic state to IDLE (status_str={status_str})")
            self.set_mic_state(MicState.IDLE)
        
        # Now set the text after mic state is updated
        if text:
            logger.debug(f"Setting label text to: '{text}'")
            self.lbl_status.setText(text)
        else:
            text_to_set = self.get_status_text(status)
            logger.debug(f"Setting label text to (from get_status_text): '{text_to_set}'")
            self.lbl_status.setText(text_to_set)
        
        logger.debug(f"set_status completed. Final label text: '{self.lbl_status.text()}'")


    def append_transcript(self, text):
        self.lbl_status.setVisible(False)
        self.lbl_trans.setVisible(True)
        self.lbl_trans.setText(text.lower())

    def clear_transcript(self):
        self.lbl_trans.setVisible(False)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Ready")

    def set_theme(self, theme: str):
        """
        Set the overlay theme and update UI.
        
        Args:
            theme: Theme name ("light" or "dark"). Invalid values are treated as "light".
        """
        if theme not in VALID_THEMES:
            import logging
            logging.getLogger(__name__).warning(
                f"Invalid theme '{theme}', using 'light'. Valid themes: {VALID_THEMES}"
            )
            theme = "light"
        self._dark_mode = theme == "dark"
        self.btn_mic.set_dark_mode(self._dark_mode)
        self._apply_styles()

    def set_loading(self, text=None):
        """Set the UI to loading state and disable mic button"""
        self.mic_enabled = False
        self.btn_mic.setEnabled(False)
        self.set_mic_state(MicState.LOADING)
        self.set_status(StatusState.LOADING, text or "Loading...")
        
    def enable_mic_button(self):
        """Enable the mic button after loading is complete"""
        self.btn_mic.setEnabled(True)
        self.mic_enabled = False  # Not currently listening, but button is available
        self.set_mic_state(MicState.IDLE)
    
    def show_eco_mode(self):
        """
        Show eco mode indicator in UI.
        TICKET-PERF-002: Mode Économie d'Énergie
        """
        self.lbl_eco_mode.setVisible(True)
    
    def hide_eco_mode(self):
        """
        Hide eco mode indicator in UI.
        TICKET-PERF-002: Mode Économie d'Énergie
        """
        self.lbl_eco_mode.setVisible(False)

    def show_screenshot(self, screenshot_path: str, duration: int = 3000):
        """
        Show mini screenshot preview overlay (TICKET-FEAT-003)
        
        Port of the Tkinter screenshot overlay to PySide6.
        Displays a small preview of a screenshot in a corner of the screen.
        
        Args: 
            screenshot_path: Path to screenshot image file
            duration: How long to show (ms), default 3000ms (3 seconds)
        """
        from PySide6.QtWidgets import QLabel
        from PySide6.QtGui import QPixmap, QScreen
        from PySide6.QtCore import QTimer
        
        # Load config settings for screenshot overlay
        config = configparser.ConfigParser()
        config_path = Path("config.ini")
        if config_path.exists():
            try:
                config.read(config_path)
            except (configparser.Error, OSError) as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not read config.ini: {e}")
        
        # Get settings from config_manager defaults
        screenshot_max_size = 200  # Default
        screenshot_position = "bottom-right"  # Default
        
        # Try to load from config.json (config_manager settings)
        try:
            config_json_path = Path("config.json")
            if config_json_path.exists():
                with open(config_json_path, "r") as f:
                    cfg = json.load(f)
                    if "ui" in cfg:
                        if "screenshot_max_size" in cfg["ui"]:
                            screenshot_max_size = cfg["ui"]["screenshot_max_size"].get("value", 200)
                        if "screenshot_position" in cfg["ui"]:
                            screenshot_position = cfg["ui"]["screenshot_position"].get("value", "bottom-right")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not load screenshot config from config.json: {e}")
        
        # Create screenshot window if it doesn't exist
        if not hasattr(self, 'screenshot_window') or self.screenshot_window is None:
            self.screenshot_window = QWidget()
            self.screenshot_window.setWindowFlags(
                Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            )
            self.screenshot_window.setAttribute(Qt.WA_TranslucentBackground)
            self.screenshot_window.setStyleSheet("""
                QWidget {
                    background-color: rgba(30, 30, 30, 240);
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 8px;
                }
            """)
            
            # Create label for image
            self.screenshot_label = QLabel(self.screenshot_window)
            self.screenshot_label.setAlignment(Qt.AlignCenter)
            self.screenshot_label.setStyleSheet("border: none; background: transparent;")
        
        # Load and scale the screenshot
        pixmap = QPixmap(screenshot_path)
        if pixmap.isNull():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load screenshot from {screenshot_path}")
            return
        
        # Calculate resize dimensions (maintain aspect ratio)
        width = pixmap.width()
        height = pixmap.height()
        
        if width > height:
            if width > screenshot_max_size:
                new_width = screenshot_max_size
                new_height = int((screenshot_max_size / width) * height)
            else:
                new_width, new_height = width, height
        else:
            if height > screenshot_max_size:
                new_height = screenshot_max_size
                new_width = int((screenshot_max_size / height) * width)
            else:
                new_width, new_height = width, height
        
        # Scale pixmap
        scaled_pixmap = pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Set the image
        self.screenshot_label.setPixmap(scaled_pixmap)
        self.screenshot_label.setFixedSize(new_width, new_height)
        
        # Add padding around the image
        padding = 4
        self.screenshot_window.setFixedSize(new_width + padding * 2, new_height + padding * 2)
        
        # Position the screenshot window based on config
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            
            # Calculate position based on screenshot_position setting
            if screenshot_position == "bottom-right":
                x = screen_width - new_width - padding * 2 - 20
                y = screen_height - new_height - padding * 2 - 80
            elif screenshot_position == "bottom-left":
                x = 20
                y = screen_height - new_height - padding * 2 - 80
            elif screenshot_position == "top-right":
                x = screen_width - new_width - padding * 2 - 20
                y = 20
            elif screenshot_position == "top-left":
                x = 20
                y = 20
            else:
                # Default to bottom-right
                x = screen_width - new_width - padding * 2 - 20
                y = screen_height - new_height - padding * 2 - 80
            
            self.screenshot_window.move(x, y)
        
        # Position label with padding
        self.screenshot_label.move(padding, padding)
        
        # Show the screenshot window
        self.screenshot_window.show()
        self.screenshot_window.raise_()
        
        # Auto-hide after duration
        if duration > 0:
            QTimer.singleShot(duration, self.hide_screenshot)
    
    def hide_screenshot(self):
        """
        Hide the screenshot overlay window (TICKET-FEAT-003)
        """
        if hasattr(self, 'screenshot_window') and self.screenshot_window is not None:
            self.screenshot_window.hide()

    def _thread_safe_set_status(self, s): self.set_status(s)
    def _thread_safe_append_transcript(self, t): self.append_transcript(t)
    def _thread_safe_set_mic_state(self, s): self.set_mic_state(s)
    def _thread_safe_clear_transcript(self): self.clear_transcript()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            c = self.childAt(e.position().toPoint())
            # Only allow dragging from container background or labels (not buttons)
            if c and (c is self.container or isinstance(c, QLabel) or c.objectName() == "container"):
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                e.accept()
            else:
                # Reset drag position when clicking on non-draggable areas
                self._drag_pos = None
                
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()
            
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(e)
    def _load_pos(self):
        try: self.move(json.loads(Path(self.config_path).read_text())["x"], json.loads(Path(self.config_path).read_text())["y"])
        except: pass
    def closeEvent(self, e):
        try: Path(self.config_path).write_text(json.dumps({"x": self.x(), "y": self.y()}))
        except: pass; super().closeEvent(e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OverlayUI(); w.show(); sys.exit(app.exec())