#!/usr/bin/env python3
"""
Example: Persistent Overlay UI Demo

This example demonstrates the persistent overlay UI (now the default interface)
without the full Janus pipeline. It simulates transcription and status updates
to showcase the overlay functionality.

Note: In Janus, the overlay is now enabled by default. Use --no-ui to disable it.

Usage:
    python examples/overlay_demo.py
"""
import sys
import time
from pathlib import Path

# Add parent directory to path to import janus
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.ui.persistent_overlay import PersistentOverlay


def main():
    """Run the overlay demo"""
    print("=" * 60)
    print("PERSISTENT OVERLAY DEMO")
    print("=" * 60)
    print("\nThis demo showcases the persistent overlay UI features:")
    print("- Draggable window")
    print("- Real-time text updates")
    print("- Status indicators")
    print("- Control buttons")
    print("\nThe window will appear shortly...")
    print("Try dragging it around and clicking the buttons.")
    print("Press Ctrl+C to exit")
    print("=" * 60)

    # Track state
    is_listening = {"value": False}
    demo_running = {"value": True}

    def on_start():
        """Handle start button"""
        is_listening["value"] = True
        overlay.update_status("🎤 Listening...")
        print("[Demo] Start button clicked - listening mode ON")

        # Simulate listening in background
        import threading

        def simulate_listening():
            time.sleep(2)
            if is_listening["value"]:
                overlay.update_transcription("You: Hello Janus")
                overlay.update_status("⚙️ Processing...")
                print("[Demo] Simulated transcription: Hello Janus")

                time.sleep(1)
                if is_listening["value"]:
                    overlay.update_transcription("Action: Opening application...")
                    overlay.update_status("✅ Done")
                    print("[Demo] Simulated action: Opening application")

        threading.Thread(target=simulate_listening, daemon=True).start()

    def on_stop():
        """Handle stop button"""
        is_listening["value"] = False
        overlay.update_status("⏸️ Stopped")
        print("[Demo] Stop button clicked - listening mode OFF")

    def on_config():
        """Handle config button"""
        overlay.update_status("⚙️ Config")
        overlay.update_transcription("Config: This would open settings")
        print("[Demo] Config button clicked")

    def on_clear():
        """Handle clear button"""
        overlay.update_status("Ready")
        print("[Demo] Clear button clicked - transcription cleared")

    # Create overlay with demo callbacks
    overlay = PersistentOverlay(
        on_start=on_start,
        on_stop=on_stop,
        on_config=on_config,
        on_clear=on_clear,
        config_path="overlay_demo_position.json",
    )

    # Show the overlay
    overlay.show()

    # Wait a moment for window to appear
    time.sleep(1)

    # Show some demo content
    overlay.update_status("Ready")
    overlay.update_transcription("Welcome to the Persistent Overlay Demo!")
    overlay.update_transcription("Click the ▶️ Start button to begin")

    print("\n[Demo] Overlay is now visible")
    print("[Demo] Interact with the buttons to see it in action")
    print("[Demo] The window is draggable - try moving it around")

    # Simulate some automatic updates after a delay
    time.sleep(3)
    if overlay.is_running:
        overlay.update_transcription("Tip: Your window position is saved automatically")
        print("[Demo] Sent tip message")

    # Keep running until interrupted or window closed
    try:
        while overlay.is_running and demo_running["value"]:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n[Demo] Interrupted by user")

    # Cleanup
    print("[Demo] Shutting down...")
    overlay.destroy()
    print("[Demo] Demo complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError running demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
