#!/usr/bin/env python3
"""
Pipeline Integration Example for OverlayUI

This example demonstrates how to integrate the new PySide6 overlay
with the Janus pipeline for real-time feedback during command processing.

Usage:
    python examples/overlay_ui_pipeline_integration.py
"""
import sys
import threading
import time
from pathlib import Path

# Add parent directory to path to import janus
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from janus.ui.overlay_ui import MicState, OverlayUI, StatusState


class OverlayPipelineIntegration:
    """
    Example integration showing how to connect the overlay UI
    to the Janus pipeline events
    """

    def __init__(self):
        self.overlay = None
        self.is_listening = False

    def initialize(self):
        """Initialize the overlay UI"""
        self.overlay = OverlayUI(
            on_mic_toggle=self.handle_mic_toggle,
            on_config=self.handle_config,
            config_path="pipeline_overlay_position.json",
        )
        self.overlay.show()

    def handle_mic_toggle(self, enabled: bool):
        """Handle microphone toggle - start/stop listening"""
        self.is_listening = enabled
        if enabled:
            print("[Pipeline] Starting speech recognition...")
            self.overlay.append_transcript("🎤 Listening for commands...")
            # In real implementation, start STT here
        else:
            print("[Pipeline] Stopping speech recognition...")
            self.overlay.append_transcript("⏹ Stopped listening")
            # In real implementation, stop STT here

    def handle_config(self):
        """Handle config button - open settings"""
        print("[Pipeline] Opening configuration...")
        self.overlay.append_transcript("⚙ Opening settings...")
        # In real implementation, open config UI here

    # Pipeline event handlers
    def on_stt_start(self):
        """Called when STT starts processing"""
        self.overlay.set_status(StatusState.LISTENING)
        self.overlay.set_mic_state(MicState.LISTENING)

    def on_transcription(self, text: str):
        """Called when transcription is received"""
        self.overlay.append_transcript(f"You: {text}")

    def on_llm_start(self):
        """Called when LLM starts processing"""
        self.overlay.set_status(StatusState.THINKING)
        self.overlay.set_mic_state(MicState.THINKING)

    def on_action_start(self, action: str):
        """Called when action executor starts"""
        self.overlay.set_status(StatusState.ACTING)
        self.overlay.append_transcript(f"Action: {action}")

    def on_action_complete(self, success: bool, message: str = ""):
        """Called when action is complete"""
        self.overlay.set_status(StatusState.IDLE)
        self.overlay.set_mic_state(MicState.IDLE)
        if success:
            self.overlay.append_transcript(f"✓ {message or 'Done'}")
        else:
            self.overlay.append_transcript(f"✗ {message or 'Failed'}")

    def on_error(self, error: str):
        """Called when an error occurs"""
        self.overlay.set_status(StatusState.IDLE)
        self.overlay.set_mic_state(MicState.IDLE)
        self.overlay.append_transcript(f"❌ Error: {error}")


def simulate_pipeline_workflow(integration: OverlayPipelineIntegration):
    """Simulate a typical pipeline workflow"""
    time.sleep(2)

    # Welcome message
    integration.overlay.append_transcript("Welcome to Janus!")
    integration.overlay.append_transcript("Click the microphone to start")

    time.sleep(3)

    # Simulate voice command workflow
    print("\n[Demo] Simulating workflow 1: Open Chrome")
    integration.on_stt_start()
    time.sleep(1)

    integration.on_transcription("open Chrome")
    time.sleep(1)

    integration.on_llm_start()
    time.sleep(2)

    integration.on_action_start("Opening Chrome browser")
    time.sleep(2)

    integration.on_action_complete(True, "Chrome opened successfully")
    time.sleep(3)

    # Simulate another workflow
    print("\n[Demo] Simulating workflow 2: Search query")
    integration.on_stt_start()
    time.sleep(1)

    integration.on_transcription("search for the latest sales report")
    time.sleep(1)

    integration.on_llm_start()
    time.sleep(2)

    integration.on_action_start("Searching for 'latest sales report'")
    time.sleep(2)

    integration.on_action_complete(True, "Search completed")
    time.sleep(3)

    # Simulate error
    print("\n[Demo] Simulating workflow 3: Error case")
    integration.on_stt_start()
    time.sleep(1)

    integration.on_transcription("open nonexistent app")
    time.sleep(1)

    integration.on_llm_start()
    time.sleep(1)

    integration.on_error("Application not found")
    time.sleep(3)

    # Done
    integration.overlay.append_transcript("\n✨ Demo complete!")
    print("\n[Demo] Simulation complete")


def main():
    """Run the pipeline integration demo"""
    print("=" * 60)
    print("OVERLAY UI - PIPELINE INTEGRATION DEMO")
    print("=" * 60)
    print("\nThis demo shows how to integrate the overlay UI with")
    print("the Janus pipeline for real-time feedback.")
    print("\nMapping:")
    print("  STT start     → set_status('listening')")
    print("  Transcription → append_transcript()")
    print("  LLM           → set_status('thinking')")
    print("  Action        → set_status('acting')")
    print("  Complete      → set_status('idle')")
    print("\nPress Ctrl+C to exit")
    print("=" * 60)

    # Create Qt application
    app = QApplication(sys.argv)

    # Create integration
    integration = OverlayPipelineIntegration()
    integration.initialize()

    print("\n[Demo] Overlay initialized")

    # Start simulation in background
    demo_thread = threading.Thread(
        target=simulate_pipeline_workflow, args=(integration,), daemon=True
    )
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
