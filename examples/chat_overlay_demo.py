#!/usr/bin/env python3
"""
Demo of the Chat Overlay Window component.

This demo shows how to use the ChatOverlayWindow independently
without the full Janus pipeline.

Usage:
    python examples/chat_overlay_demo.py
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


def main():
    """Run the chat overlay demo."""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from janus.ui.chat_overlay_window import ChatOverlayWindow
    
    # Create chat window in dark mode
    chat = ChatOverlayWindow(dark_mode=True)
    
    # Connect signals to demo handlers
    def on_text_submitted(text: str):
        """Handle text submission."""
        print(f"User submitted: {text}")
        chat.set_processing(True)
        chat.add_status_indicator("thinking", "Analyzing your request...")
        
        # Simulate processing with a timer
        QTimer.singleShot(2000, lambda: simulate_response(text))
    
    def simulate_response(original_text: str):
        """Simulate an AI response."""
        chat.update_last_status("acting", "Executing action...")
        
        # Add some response messages
        responses = [
            f"I understand you want to: {original_text}",
            "Processing your request...",
            "Action completed successfully!"
        ]
        
        for i, response in enumerate(responses):
            QTimer.singleShot(1000 * (i + 1), lambda r=response: chat.add_assistant_message(r))
        
        # Show completion status
        QTimer.singleShot(4000, lambda: chat.add_status_indicator("done", "✅ Task completed"))
        QTimer.singleShot(4500, lambda: chat.set_processing(False))
    
    def on_stop_requested():
        """Handle stop button click."""
        print("Stop requested by user")
        chat.set_processing(False)
        chat.add_status_indicator("error", "⚠️ Stopped by user")
    
    def on_mic_toggle(enabled: bool):
        """Handle microphone toggle."""
        state = "enabled" if enabled else "disabled"
        print(f"Microphone {state}")
        chat.add_assistant_message(f"🎤 Voice input is now {state}")
    
    # Connect signals
    chat.text_submitted.connect(on_text_submitted)
    chat.stop_requested.connect(on_stop_requested)
    chat.mic_toggle_requested.connect(on_mic_toggle)
    
    # Add some initial messages
    chat.add_assistant_message("👋 Welcome to Janus Chat!")
    chat.add_assistant_message("Type a command below or click the mic button for voice input.")
    
    # Show the window
    chat.show()
    
    print("Chat overlay demo running...")
    print("- Type a message and press Enter to see it in action")
    print("- Click Stop to interrupt processing")
    print("- Toggle the mic button to see voice mode")
    print("- Close the window to exit")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
