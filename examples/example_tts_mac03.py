"""
Example demonstrating new TTS controls (TICKET-MAC-03)
- Volume control
- Mute/unmute
- TTS Control Panel UI
- Timing statistics
"""
import os
import sys
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.io.tts import MacTTSAdapter
from janus.ui import TTSControlPanel


def example_1_volume_control():
    """Example 1: Volume control"""
    print("\n=== Example 1: Volume Control ===")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False)

    # Test different volumes
    print("Speaking at 30% volume...")
    tts.set_volume(0.3)
    tts.speak("Message à faible volume")
    time.sleep(2)

    print("Speaking at 70% volume...")
    tts.set_volume(0.7)
    tts.speak("Message à volume moyen")
    time.sleep(2)

    print("Speaking at 100% volume...")
    tts.set_volume(1.0)
    tts.speak("Message à volume élevé")
    time.sleep(2)

    tts.shutdown()
    print("✓ Example 1 complete\n")


def example_2_mute_unmute():
    """Example 2: Mute/unmute functionality"""
    print("\n=== Example 2: Mute/Unmute ===")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False)

    print("Speaking normally...")
    tts.speak("Ceci est un message normal")
    time.sleep(2)

    print("Muting TTS...")
    tts.mute()
    print(f"Is muted: {tts.is_muted()}")

    print("Attempting to speak while muted (should be silent)...")
    tts.speak("Ce message ne devrait pas être entendu")
    time.sleep(1)

    print("Unmuting TTS...")
    tts.unmute()
    print(f"Is muted: {tts.is_muted()}")

    print("Speaking after unmute...")
    tts.speak("TTS est maintenant actif")
    time.sleep(2)

    tts.shutdown()
    print("✓ Example 2 complete\n")


def example_3_timing_statistics():
    """Example 3: Timing and duration tracking"""
    print("\n=== Example 3: Timing Statistics ===")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False)

    # Initial stats
    stats = tts.get_timing_stats()
    print(f"Initial stats: {stats}")

    # Speak multiple messages
    print("\nSpeaking 3 messages...")
    for i in range(3):
        tts.speak(f"Message numéro {i+1}")
        time.sleep(1.5)

    # Final stats
    stats = tts.get_timing_stats()
    print(f"\nFinal statistics:")
    print(f"  Total speeches: {stats['speech_count']}")
    print(f"  Total time: {stats['total_speech_time']:.2f}s")
    print(f"  Average duration: {stats['average_duration']:.2f}s")

    tts.shutdown()
    print("✓ Example 3 complete\n")


def example_4_dynamic_adjustments():
    """Example 4: Dynamic rate and volume adjustments"""
    print("\n=== Example 4: Dynamic Adjustments ===")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False)

    print("Normal speed and volume...")
    tts.speak("Vitesse et volume normaux")
    time.sleep(2)

    print("Increasing rate to 250 WPM...")
    tts.set_rate(250)
    tts.speak("Vitesse augmentée")
    time.sleep(1.5)

    print("Decreasing rate to 120 WPM and lowering volume...")
    tts.set_rate(120)
    tts.set_volume(0.5)
    tts.speak("Vitesse et volume réduits")
    time.sleep(3)

    print("Back to normal...")
    tts.set_rate(180)
    tts.set_volume(0.7)
    tts.speak("Retour à la normale")
    time.sleep(2)

    tts.shutdown()
    print("✓ Example 4 complete\n")


def example_5_control_panel_ui():
    """Example 5: TTS Control Panel UI"""
    print("\n=== Example 5: TTS Control Panel UI ===")
    print("Opening TTS control panel...")
    print("Use the UI to control volume, rate, and mute/unmute.")
    print("Close the panel to exit this example.")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=True)

    # Create control panel
    control_panel = TTSControlPanel(
        tts_adapter=tts,
        position="bottom-right",
        on_mute_change=lambda muted: print(
            f"Mute state changed: {'Muted' if muted else 'Unmuted'}"
        ),
    )

    # Speak messages in background while UI is active
    def background_speaker():
        time.sleep(2)
        for i in range(5):
            if not tts.is_muted():
                tts.speak(f"Message automatique numéro {i+1}")
            time.sleep(4)

    speaker_thread = threading.Thread(target=background_speaker, daemon=True)
    speaker_thread.start()

    # Run control panel (blocking until closed)
    try:
        control_panel.run()
    except KeyboardInterrupt:
        pass

    tts.shutdown()
    print("✓ Example 5 complete\n")


def example_6_feedback_loop_prevention():
    """Example 6: TTS/STT feedback loop prevention"""
    print("\n=== Example 6: Feedback Loop Prevention ===")
    print("Demonstrating how TTS stops when STT starts...")

    tts = MacTTSAdapter(voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=True)

    # Queue multiple messages
    print("Queueing multiple messages...")
    tts.speak("Premier message de longue durée")
    tts.speak("Deuxième message de longue durée")
    tts.speak("Troisième message de longue durée")

    time.sleep(1.5)

    # Simulate STT starting
    print("\nSimulating STT start - stopping TTS to avoid feedback loop...")
    if tts.is_speaking():
        print("TTS is speaking, stopping it now...")
        tts.stop()
        print("TTS stopped successfully")

    time.sleep(1)

    print("\nSTT would listen here...")
    time.sleep(1)

    print("STT complete, resuming TTS...")
    tts.speak("TTS reprend après STT")
    time.sleep(2)

    tts.shutdown()
    print("✓ Example 6 complete\n")


def main():
    """Run all examples"""
    print("=" * 60)
    print("TTS Enhanced Controls Examples (TICKET-MAC-03)")
    print("=" * 60)

    try:
        example_1_volume_control()
        example_2_mute_unmute()
        example_3_timing_statistics()
        example_4_dynamic_adjustments()

        # Ask before showing UI (as it's blocking)
        print("\nExample 5 will open a GUI control panel.")
        response = input("Run Example 5 (TTS Control Panel UI)? [y/N]: ")
        if response.lower() in ["y", "yes"]:
            example_5_control_panel_ui()
        else:
            print("Skipping Example 5")

        example_6_feedback_loop_prevention()

        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
