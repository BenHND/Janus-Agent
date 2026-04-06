#!/usr/bin/env python3
"""
Complete OverlayUI Demo with Configuration

This example demonstrates the full OverlayUI with configuration window:
- Draggable overlay window
- Microphone button with states
- Real-time transcription
- Configuration mini-window
- Status indicators

Usage:
    python examples/overlay_ui_complete_demo.py
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
    """Run the complete overlay UI demo"""
    print("=" * 60)
    print("OVERLAY UI COMPLETE DEMO")
    print("=" * 60)
    print("\nThis demo showcases the complete PySide6 overlay:")
    print("- Draggable frameless window (400x160px)")
    print("- Microphone button with animated states")
    print("- Real-time transcription display")
    print("- Configuration mini-window")
    print("- Status indicators (listening, thinking, acting)")
    print("\nThe window will appear shortly...")
    print("Try:")
    print("  1. Drag the top area to move the window")
    print("  2. Click the microphone button to toggle listening")
    print("  3. Click the gear icon to open settings")
    print("\nPress Ctrl+C to exit")
    print("=" * 60)

    # Create Qt application
    app = QApplication(sys.argv)

    # Track state
    mic_enabled = {"value": False}

    # Callbacks
    def on_mic_toggle(enabled: bool):
        """Handle mic button toggle"""
        mic_enabled["value"] = enabled
        status = "enabled" if enabled else "disabled"
        print(f"\n[Demo] Microphone {status}")

        if enabled:
            overlay.append_transcript("🎤 Microphone activated")
            overlay.set_status(StatusState.LISTENING)
            # Start demo sequence when mic is enabled
            threading.Thread(target=demo_listening_sequence, daemon=True).start()
        else:
            overlay.append_transcript("⏹ Microphone deactivated")
            overlay.set_status(StatusState.IDLE)

    def on_config():
        """Handle config button"""
        print("\n[Demo] Configuration window opened")
        # The config window is handled internally by OverlayUI

    # Create overlay
    overlay = OverlayUI(
        on_mic_toggle=on_mic_toggle,
        on_config=on_config,
        config_path="complete_demo_overlay_position.json",
    )

    # Show the overlay
    overlay.show()
    print("\n[Demo] Overlay is now visible")

    # Initial instructions
    def show_instructions():
        time.sleep(1)
        overlay.append_transcript("Welcome to Janus Overlay UI!")
        time.sleep(2)
        overlay.append_transcript("Click 🎤 to start listening")
        time.sleep(2)
        overlay.append_transcript("Click ⚙ to configure settings")

    threading.Thread(target=show_instructions, daemon=True).start()

    # Demo sequence when listening
    def demo_listening_sequence():
        """Simulate a voice command workflow"""
        if not mic_enabled["value"]:
            return

        time.sleep(1)

        # Simulate user speech
        overlay.append_transcript("You: Open Chrome and search for Python tutorials")
        print("[Demo] Simulated voice input")
        time.sleep(2)

        # Simulate thinking/processing
        overlay.set_status(StatusState.THINKING)
        overlay.set_mic_state(MicState.THINKING)
        overlay.append_transcript("Processing command...")
        print("[Demo] Status: Thinking")
        time.sleep(2)

        # Simulate action execution
        overlay.set_status(StatusState.ACTING)
        overlay.append_transcript("Opening Chrome browser...")
        print("[Demo] Status: Acting (1/2)")
        time.sleep(2)

        overlay.append_transcript("Searching for 'Python tutorials'...")
        print("[Demo] Status: Acting (2/2)")
        time.sleep(2)

        # Complete
        overlay.set_status(StatusState.IDLE)
        overlay.set_mic_state(MicState.IDLE)
        overlay.append_transcript("✓ Task completed successfully!")
        print("[Demo] Task complete")

        time.sleep(2)
        overlay.append_transcript("Ready for next command")

    # Additional demo features
    def show_advanced_features():
        """Show advanced features after initial demo"""
        time.sleep(15)

        if not overlay.isVisible():
            return

        overlay.append_transcript("\n💡 Tips:")
        time.sleep(1)
        overlay.append_transcript("• Position is saved automatically")
        time.sleep(2)
        overlay.append_transcript("• Try the gear icon for settings")
        time.sleep(2)
        overlay.append_transcript("• Drag from the top to move")

        time.sleep(3)
        print("\n[Demo] Advanced features demonstrated")

    threading.Thread(target=show_advanced_features, daemon=True).start()

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
