#!/usr/bin/env python3
"""
OverlayUI Demo - PySide6 Cross-Platform Overlay

This example demonstrates the new PySide6-based overlay UI with:
- Draggable, frameless window (400x160px)
- Microphone button with animated states
- Real-time transcription display
- Configuration button
- Status indicators (listening, thinking, acting)

Usage:
    python examples/overlay_ui_demo.py
"""
import sys
import threading
import time
from pathlib import Path

# Add parent directory to path to import janus
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from janus.ui.overlay_ui import MicState, OverlayUI, StatusState


def main():
    """Run the overlay UI demo"""
    print("=" * 60)
    print("OVERLAY UI DEMO (PySide6)")
    print("=" * 60)
    print("\nThis demo showcases the new PySide6 overlay features:")
    print("- Frameless, draggable window")
    print("- Microphone button with states (idle, listening, thinking, muted)")
    print("- Real-time transcription display")
    print("- Configuration button")
    print("- Status indicators (listening, thinking, acting)")
    print("\nThe window will appear shortly...")
    print("Try dragging the top area and clicking the buttons.")
    print("Press Ctrl+C to exit")
    print("=" * 60)

    # Create Qt application
    app = QApplication(sys.argv)

    # Callbacks
    def on_mic_toggle(enabled: bool):
        """Handle mic button toggle"""
        status = "enabled" if enabled else "disabled"
        print(f"[Demo] Microphone {status}")
        overlay.append_transcript(f"Mic {status}")

    def on_config():
        """Handle config button"""
        print("[Demo] Config button clicked")
        overlay.append_transcript("Opening configuration...")

    # Create overlay
    overlay = OverlayUI(
        on_mic_toggle=on_mic_toggle, on_config=on_config, config_path="demo_overlay_position.json"
    )

    # Show the overlay
    overlay.show()
    print("\n[Demo] Overlay is now visible")
    print("[Demo] Drag the top bar to move the window")
    print("[Demo] Click the microphone button to toggle listening")

    # Demo sequence in background thread
    def demo_sequence():
        """Simulate a typical workflow"""
        time.sleep(2)

        # Initial message
        overlay.append_transcript("Welcome to Janus Overlay UI!")
        print("[Demo] Sent welcome message")

        time.sleep(2)

        # Simulate listening state
        overlay.set_status(StatusState.LISTENING)
        overlay.set_mic_state(MicState.LISTENING)
        print("[Demo] Status: Listening")

        time.sleep(1.5)
        overlay.append_transcript("You: Search for the latest sales report from yesterday...")
        print("[Demo] Simulated user speech")

        time.sleep(2)

        # Simulate thinking state
        overlay.set_status(StatusState.THINKING)
        overlay.set_mic_state(MicState.THINKING)
        print("[Demo] Status: Thinking")

        time.sleep(2)
        overlay.append_transcript("Assistant: Processing your request...")
        print("[Demo] Simulated processing")

        time.sleep(1)

        # Simulate acting state
        overlay.set_status(StatusState.ACTING)
        print("[Demo] Status: Acting")

        time.sleep(1.5)
        overlay.append_transcript("Opening Chrome and navigating to dashboard...")
        print("[Demo] Simulated action execution")

        time.sleep(2)

        # Back to idle
        overlay.set_status(StatusState.IDLE)
        overlay.set_mic_state(MicState.IDLE)
        overlay.append_transcript("✓ Task completed successfully!")
        print("[Demo] Status: Idle (complete)")

        time.sleep(3)

        # Show more examples
        overlay.append_transcript("\nTip: Click the gear icon for settings")
        print("[Demo] Sent tip message")

        time.sleep(2)
        overlay.append_transcript("Tip: The window position is saved automatically")
        print("[Demo] Sent position tip")

    # Start demo sequence in background
    demo_thread = threading.Thread(target=demo_sequence, daemon=True)
    demo_thread.start()

    # Run Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Demo] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
