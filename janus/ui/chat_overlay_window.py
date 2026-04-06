"""
Chat Overlay Window - Scrollable chat interface for Janus
Replaces the simple text input dialog with a modern, scrollable chat interface
inspired by Rovo, showing conversation history, real-time status updates, and control buttons.
"""

from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QTextEdit, QPushButton, QLabel, QFrame, QSizePolicy
)
from PySide6.QtGui import QColor, QKeyEvent


class ChatOverlayWindow(QWidget):
    """
    Scrollable chat interface for Janus. 
    Replaces the simple text input dialog.
    
    Features:
    - View conversation history (user prompts + AI responses)
    - Real-time status tracking (thinking, acting, done)
    - Stop button to interrupt ongoing actions
    - Toggle between voice and text input
    """
    
    # Signals
    text_submitted = Signal(str)  # When user sends a message
    stop_requested = Signal()     # When user clicks Stop
    mic_toggle_requested = Signal(bool)  # Toggle microphone
    
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._is_processing = False
        
        self._setup_window()
        self._create_ui()
        self._apply_styles()
    
    def _setup_window(self):
        """Configure the window"""
        self.setWindowTitle("Janus Assistant")
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(400, 500)
        self.resize(420, 600)
    
    def _create_ui(self):
        """Create the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main container with styling
        self.container = QFrame()
        self.container.setObjectName("chat_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # === HEADER ===
        self._create_header(container_layout)
        
        # === CHAT AREA (Scrollable) ===
        self._create_chat_area(container_layout)
        
        # === INPUT AREA ===
        self._create_input_area(container_layout)
        
        main_layout.addWidget(self.container)
    
    def _create_header(self, parent_layout):
        """Create header with title and window buttons"""
        header = QFrame()
        header.setObjectName("chat_header")
        header.setFixedHeight(50)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        # Title
        title = QLabel("🤖 Janus Assistant")
        title.setObjectName("chat_title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Window buttons
        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setObjectName("window_btn")
        self.btn_minimize.setFixedSize(24, 24)
        self.btn_minimize.clicked.connect(self.showMinimized)
        
        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("close_btn")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self.close)
        
        header_layout.addWidget(self.btn_minimize)
        header_layout.addWidget(self.btn_close)
        
        parent_layout.addWidget(header)
    
    def _create_chat_area(self, parent_layout):
        """Create the scrollable chat area"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("chat_scroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(16, 16, 16, 16)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()  # Push messages to top
        
        self.scroll_area.setWidget(self.messages_container)
        parent_layout.addWidget(self.scroll_area, 1)  # Stretch factor 1
    
    def _create_input_area(self, parent_layout):
        """Create the input area"""
        input_frame = QFrame()
        input_frame.setObjectName("input_frame")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 16)
        input_layout.setSpacing(8)
        
        # Input + Send button
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        
        self.input_field = QTextEdit()
        self.input_field.setObjectName("chat_input")
        self.input_field.setPlaceholderText("Décrivez ce que vous voulez faire...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setMinimumHeight(40)
        # Enter to send (Shift+Enter for new line)
        self.input_field.installEventFilter(self)
        
        self.send_btn = QPushButton("↑")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.clicked.connect(self._on_send)
        
        input_row.addWidget(self.input_field, 1)
        input_row.addWidget(self.send_btn)
        
        input_layout.addLayout(input_row)
        
        # Mic and Stop buttons
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        
        self.mic_btn = QPushButton("🎤 Vocal")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setCheckable(True)
        self.mic_btn.clicked.connect(self._on_mic_toggle)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)  # Disabled by default
        self.stop_btn.clicked.connect(self._on_stop)
        
        buttons_row.addWidget(self.mic_btn)
        buttons_row.addWidget(self.stop_btn)
        buttons_row.addStretch()
        
        input_layout.addLayout(buttons_row)
        
        parent_layout.addWidget(input_frame)
    
    # === PUBLIC METHODS ===
    
    def add_user_message(self, text: str):
        """Add a user message (blue bubble on the right)"""
        bubble = MessageBubble(text, is_user=True, dark_mode=self._dark_mode)
        self._add_message_widget(bubble)
    
    def add_assistant_message(self, text: str):
        """Add an assistant message (grey bubble on the left)"""
        bubble = MessageBubble(text, is_user=False, dark_mode=self._dark_mode)
        self._add_message_widget(bubble)
        return bubble  # Allow updates
    
    def add_status_indicator(self, status: str, text: str):
        """Add a status indicator (thinking, acting, done, error)"""
        indicator = StatusIndicator(status, text, dark_mode=self._dark_mode)
        self._add_message_widget(indicator)
        return indicator
    
    def update_last_status(self, status: str, text: str):
        """Update the last status indicator"""
        # Find the last StatusIndicator and update it
        for i in range(self.messages_layout.count() - 1, -1, -1):
            item = self.messages_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, StatusIndicator):
                    widget.update_status(status, text)
                    return
    
    def set_processing(self, is_processing: bool):
        """Enable/disable processing state"""
        self._is_processing = is_processing
        self.stop_btn.setEnabled(is_processing)
        self.send_btn.setEnabled(not is_processing)
        self.input_field.setEnabled(not is_processing)
    
    def clear_chat(self):
        """Clear all messages"""
        while self.messages_layout.count() > 1:  # Keep stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    # === PRIVATE METHODS ===
    
    def _add_message_widget(self, widget):
        """Add a message widget and scroll to bottom"""
        # Insert before the stretch
        self.messages_layout.insertWidget(
            self.messages_layout.count() - 1, widget
        )
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the chat"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_send(self):
        """Called when user sends a message"""
        text = self.input_field.toPlainText().strip()
        if text:
            self.add_user_message(text)
            self.input_field.clear()
            self.text_submitted.emit(text)
    
    def _on_stop(self):
        """Called when user clicks Stop"""
        self.stop_requested.emit()
    
    def _on_mic_toggle(self):
        """Toggle voice mode"""
        self.mic_toggle_requested.emit(self.mic_btn.isChecked())
    
    def eventFilter(self, obj, event):
        """Handle Enter to send"""
        if obj == self.input_field and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)
    
    def _apply_styles(self):
        """Apply stylesheets based on theme"""
        if self._dark_mode:
            self.setStyleSheet("""
                #chat_container {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #3D4147, stop:1 #2C3036);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.15);
                }
                
                #chat_header {
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }
                
                #chat_title {
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                #chat_scroll {
                    background: transparent;
                    border: none;
                }
                
                #bubble_container_user {
                    background: #007AFF;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                }
                
                #bubble_container_assistant {
                    background: rgba(255,255,255,0.1);
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                }
                
                #bubble_text {
                    color: white;
                    font-size: 13px;
                }
                
                #status_indicator {
                    background: transparent;
                }
                
                #status_text {
                    color: rgba(255,255,255,0.7);
                    font-size: 12px;
                    font-style: italic;
                }
                
                #input_frame {
                    background: rgba(0,0,0,0.2);
                    border-top: 1px solid rgba(255,255,255,0.1);
                }
                
                #chat_input {
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 12px;
                    padding: 8px 12px;
                    color: white;
                    font-size: 13px;
                }
                
                #send_btn {
                    background: #007AFF;
                    border: none;
                    border-radius: 20px;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                }
                
                #send_btn:hover {
                    background: #0056b3;
                }
                
                #send_btn:disabled {
                    background: rgba(255,255,255,0.2);
                }
                
                #stop_btn {
                    background: rgba(255,59,48,0.8);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    padding: 6px 12px;
                }
                
                #stop_btn:hover {
                    background: rgba(255,59,48,1);
                }
                
                #stop_btn:disabled {
                    background: rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.3);
                }
                
                #mic_btn {
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 8px;
                    color: white;
                    padding: 6px 12px;
                }
                
                #mic_btn:checked {
                    background: rgba(32,227,178,0.8);
                    border-color: #20E3B2;
                }
                
                #window_btn {
                    background: rgba(255,255,255,0.1);
                    border: none;
                    border-radius: 12px;
                    color: rgba(255,255,255,0.7);
                    font-size: 16px;
                }
                
                #window_btn:hover {
                    background: rgba(255,255,255,0.2);
                }
                
                #close_btn {
                    background: rgba(255,255,255,0.1);
                    border: none;
                    border-radius: 12px;
                    color: rgba(255,255,255,0.7);
                    font-size: 18px;
                }
                
                #close_btn:hover {
                    background: rgba(255,59,48,0.8);
                    color: white;
                }
            """)
        else:
            # Light mode
            self.setStyleSheet("""
                #chat_container {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #E3E6E9, stop:1 #B0B5BB);
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.4);
                }
                
                #chat_header {
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.3);
                }
                
                #chat_title {
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                #chat_scroll {
                    background: transparent;
                    border: none;
                }
                
                #bubble_container_user {
                    background: #007AFF;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                }
                
                #bubble_container_assistant {
                    background: rgba(255,255,255,0.7);
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                }
                
                #bubble_text {
                    color: white;
                    font-size: 13px;
                }
                
                #status_indicator {
                    background: transparent;
                }
                
                #status_text {
                    color: rgba(255,255,255,0.8);
                    font-size: 12px;
                    font-style: italic;
                }
                
                #input_frame {
                    background: rgba(255,255,255,0.3);
                    border-top: 1px solid rgba(255,255,255,0.4);
                }
                
                #chat_input {
                    background: rgba(255,255,255,0.7);
                    border: 1px solid rgba(255,255,255,0.5);
                    border-radius: 12px;
                    padding: 8px 12px;
                    color: rgba(0,0,0,0.9);
                    font-size: 13px;
                }
                
                #send_btn {
                    background: #007AFF;
                    border: none;
                    border-radius: 20px;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                }
                
                #send_btn:hover {
                    background: #0056b3;
                }
                
                #send_btn:disabled {
                    background: rgba(200,200,200,0.5);
                }
                
                #stop_btn {
                    background: rgba(255,59,48,0.9);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    padding: 6px 12px;
                }
                
                #stop_btn:hover {
                    background: rgba(255,59,48,1);
                }
                
                #stop_btn:disabled {
                    background: rgba(200,200,200,0.5);
                    color: rgba(0,0,0,0.3);
                }
                
                #mic_btn {
                    background: rgba(255,255,255,0.7);
                    border: 1px solid rgba(255,255,255,0.9);
                    border-radius: 8px;
                    color: rgba(0,0,0,0.8);
                    padding: 6px 12px;
                }
                
                #mic_btn:checked {
                    background: rgba(32,227,178,0.9);
                    border-color: #20E3B2;
                    color: white;
                }
                
                #window_btn {
                    background: rgba(255,255,255,0.5);
                    border: none;
                    border-radius: 12px;
                    color: rgba(0,0,0,0.6);
                    font-size: 16px;
                }
                
                #window_btn:hover {
                    background: rgba(255,255,255,0.8);
                }
                
                #close_btn {
                    background: rgba(255,255,255,0.5);
                    border: none;
                    border-radius: 12px;
                    color: rgba(0,0,0,0.6);
                    font-size: 18px;
                }
                
                #close_btn:hover {
                    background: rgba(255,59,48,0.9);
                    color: white;
                }
            """)


class MessageBubble(QFrame):
    """Chat-style message bubble"""
    
    def __init__(self, text: str, is_user: bool, dark_mode: bool = False, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._dark_mode = dark_mode
        
        self.setObjectName("user_bubble" if is_user else "assistant_bubble")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Spacer for alignment
        if is_user:
            layout.addStretch()
        
        # Message label
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(280)
        self.label.setObjectName("bubble_text")
        
        # Container for styling
        bubble_container = QFrame()
        bubble_container.setObjectName("bubble_container_user" if is_user else "bubble_container_assistant")
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.addWidget(self.label)
        
        layout.addWidget(bubble_container)
        
        if not is_user:
            layout.addStretch()
    
    def update_text(self, text: str):
        """Update the message text"""
        self.label.setText(text)


class StatusIndicator(QFrame):
    """Status indicator (thinking, acting, done, error)"""
    
    STATUS_ICONS = {
        "thinking": "🤔",
        "looking": "👁️",
        "acting": "⚡",
        "done": "✅",
        "error": "❌",
    }
    
    def __init__(self, status: str, text: str, dark_mode: bool = False, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        
        self.setObjectName("status_indicator")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        self.icon_label = QLabel(self.STATUS_ICONS.get(status, "•"))
        self.text_label = QLabel(text)
        self.text_label.setObjectName("status_text")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
    
    def update_status(self, status: str, text: str):
        """Update the status"""
        self.icon_label.setText(self.STATUS_ICONS.get(status, "•"))
        self.text_label.setText(text)
