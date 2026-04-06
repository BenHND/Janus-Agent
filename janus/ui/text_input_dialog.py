"""
Text Input Dialog - Styled popup for text-based commands
Allows users to submit commands via text input instead of voice
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QWidget, QGraphicsDropShadowEffect
)
from janus.i18n import t


class StyledTextInputDialog(QDialog):
    """
    Styled popup dialog for text command input.
    
    Features:
    - Modern, styled appearance matching the overlay aesthetic
    - Text input field with placeholder
    - Submit button to process the command
    - Close button (X icon)
    - Enter key triggers submit
    - Escape key closes dialog
    """
    
    # Signal emitted when user submits text
    text_submitted = Signal(str)
    
    def __init__(self, parent=None, dark_mode=False):
        """
        Initialize the text input dialog.
        
        Args:
            parent: Parent widget
            dark_mode: Whether to use dark mode styling
        """
        super().__init__(parent)
        self._dark_mode = dark_mode
        
        # Configure dialog window
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        # Fixed size for the dialog
        self.setFixedSize(400, 180)
        
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Main layout with padding for shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Container frame
        self.container = QWidget()
        self.container.setObjectName("dialog_container")
        self.container.setFixedSize(360, 140)
        
        # Add shadow effect to container
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.container)
        
        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 16, 20, 16)
        container_layout.setSpacing(12)
        
        # Header with title and close button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel(t("ui.text_input_title"))
        self.title_label.setObjectName("dialog_title")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Close button
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("close_btn")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        header_layout.addWidget(self.btn_close)
        
        container_layout.addLayout(header_layout)
        
        # Text input field
        self.text_input = QLineEdit()
        self.text_input.setObjectName("text_input")
        self.text_input.setPlaceholderText(t("ui.text_input_placeholder"))
        self.text_input.setFixedHeight(36)
        self.text_input.returnPressed.connect(self._on_submit)
        container_layout.addWidget(self.text_input)
        
        # Submit button
        self.btn_submit = QPushButton(t("ui.text_input_submit"))
        self.btn_submit.setObjectName("submit_btn")
        self.btn_submit.setFixedHeight(32)
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.clicked.connect(self._on_submit)
        container_layout.addWidget(self.btn_submit)
        
        container_layout.addStretch()
    
    def _apply_styles(self):
        """Apply stylesheet based on theme."""
        if self._dark_mode:
            # Dark mode styling - matching overlay aesthetic
            self.setStyleSheet("""
                QWidget { 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: transparent;
                }
                
                #dialog_container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #3D4147, stop:1 #2C3036);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.2);
                }
                
                #dialog_title {
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }
                
                #text_input {
                    background-color: rgba(255, 255, 255, 0.10);
                    border: 1.5px solid rgba(255, 255, 255, 0.25);
                    border-radius: 10px;
                    color: rgba(255, 255, 255, 0.95);
                    padding: 10px 14px;
                    font-size: 13px;
                    selection-background-color: rgba(100, 181, 246, 0.4);
                }
                
                #text_input:focus {
                    background-color: rgba(255, 255, 255, 0.14);
                    border: 1.5px solid rgba(100, 181, 246, 0.7);
                    outline: none;
                }
                
                #submit_btn {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(100, 181, 246, 0.9), stop:1 rgba(66, 165, 245, 0.9));
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 2px 0px;
                }
                
                #submit_btn:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(100, 181, 246, 1.0), stop:1 rgba(66, 165, 245, 1.0));
                }
                
                #submit_btn:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(66, 165, 245, 1.0), stop:1 rgba(50, 150, 230, 1.0));
                }
                
                #close_btn {
                    background-color: rgba(255, 255, 255, 0.12);
                    color: rgba(255, 255, 255, 0.75);
                    border: none;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                }
                
                #close_btn:hover {
                    background-color: rgba(255, 90, 80, 0.8);
                    color: white;
                }
            """)
        else:
            # Light mode styling - matching overlay aesthetic
            self.setStyleSheet("""
                QWidget { 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: transparent;
                }
                
                #dialog_container {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #E3E6E9, stop:1 #B0B5BB);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.5);
                }
                
                #dialog_title {
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }
                
                #text_input {
                    background-color: rgba(255, 255, 255, 0.65);
                    border: 1.5px solid rgba(255, 255, 255, 0.9);
                    border-radius: 10px;
                    color: rgba(0, 0, 0, 0.9);
                    padding: 10px 14px;
                    font-size: 13px;
                    selection-background-color: rgba(33, 150, 243, 0.3);
                }
                
                #text_input:focus {
                    background-color: rgba(255, 255, 255, 0.9);
                    border: 1.5px solid rgba(33, 150, 243, 0.9);
                    outline: none;
                }
                
                #submit_btn {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(33, 150, 243, 1.0), stop:1 rgba(30, 136, 229, 1.0));
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 2px 0px;
                }
                
                #submit_btn:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(50, 160, 250, 1.0), stop:1 rgba(40, 146, 240, 1.0));
                }
                
                #submit_btn:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(20, 130, 220, 1.0), stop:1 rgba(15, 120, 210, 1.0));
                }
                
                #close_btn {
                    background-color: rgba(255, 255, 255, 0.4);
                    color: rgba(0, 0, 0, 0.65);
                    border: none;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                }
                
                #close_btn:hover {
                    background-color: rgba(255, 90, 80, 0.9);
                    color: white;
                }
            """)
    
    def _on_submit(self):
        """Handle submit button click or Enter key press."""
        text = self.text_input.text().strip()
        if text:
            self.text_submitted.emit(text)
            self.accept()
    
    def showEvent(self, event):
        """Override show event to focus on text input and position dialog."""
        super().showEvent(event)
        # Focus on text input when dialog opens
        self.text_input.setFocus()
        self.text_input.clear()
        
        # Center dialog on parent if available
        if self.parent():
            parent_rect = self.parent().geometry()
            parent_center = parent_rect.center()
            dialog_rect = self.geometry()
            dialog_rect.moveCenter(parent_center)
            self.move(dialog_rect.topLeft())
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
