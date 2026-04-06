#!/usr/bin/env python3
"""
Example demonstrating WhisperRecorder with pre-roll functionality (TICKET-XX)

This script shows how the new ring buffer and threading architecture work:
- Continuous audio capture in background thread
- Pre-roll buffer maintains last 300ms of audio
- No fade-in at recording start
- Clean thread lifecycle management

Note: This requires PyAudio to be installed and a microphone available.
For testing without hardware, see tests/test_whisper_recorder_preroll.py
"""

import sys
import time

# Mock dependencies for testing environments
try:
    import pyaudio
except ImportError:
    print("WARNING: PyAudio not installed. This example requires audio hardware.")
    print("Install with: pip install pyaudio")
    sys.exit(1)

from janus.io.stt.whisper_recorder import WhisperRecorder


def main():
    """Demonstrate WhisperRecorder pre-roll functionality"""
    print("=" * 60)
    print("WhisperRecorder Pre-roll Example")
    print("=" * 60)
    print()

    # Create recorder with default settings
    # - 16kHz sample rate
    # - 20ms chunks
    # - 300ms pre-roll buffer (15 chunks)
    print("1. Initializing WhisperRecorder...")
    recorder = WhisperRecorder(
        sample_rate=16000,
        chunk_duration_ms=20,
        preroll_duration_ms=300,  # 300ms of pre-roll
    )
    print("   ✓ Persistent stream opened")
    print("   ✓ Reader thread started")
    print("   ✓ Ring buffer created (300ms capacity)")
    print()

    # Wait a moment for ring buffer to fill
    print("2. Filling pre-roll buffer...")
    time.sleep(0.5)
    print("   ✓ Ring buffer filled with background audio")
    print()

    # Simulate multiple recording cycles
    print("3. Recording cycles demonstration:")
    print()

    for cycle in range(1, 4):
        print(f"   Cycle {cycle}:")
        recorder.start_listening()
        print("   - Speak now (recording will auto-stop after silence)...")

        # Record audio
        # This will:
        # 1. Clear recording queue
        # 2. Get pre-roll snapshot (last 300ms)
        # 3. Start consuming from queue
        # 4. Stop on silence or max_duration
        audio_path, error = recorder.record_audio(max_duration=5)

        if audio_path:
            print(f"   ✓ Recording saved to: {audio_path}")
            print(f"   ✓ Pre-roll included (no audio lost at start)")

            # Check debug recording
            import os

            if os.path.exists("audio_logs/debug_recording.wav"):
                print(f"   ✓ Debug WAV saved to: audio_logs/debug_recording.wav")
        else:
            print(f"   ✗ Error: {error}")

        print()
        time.sleep(1)

    # Cleanup
    print("4. Cleanup:")
    print("   - Closing recorder...")
    recorder.close()
    print("   ✓ Thread stopped")
    print("   ✓ Stream closed")
    print()

    print("=" * 60)
    print("Key Features Demonstrated:")
    print("- Persistent PyAudio stream (opened once)")
    print("- Background reader thread (continuous capture)")
    print("- Ring buffer pre-roll (300ms before recording starts)")
    print("- No fade-in at recording start")
    print("- Multiple recording cycles without re-opening stream")
    print("- Clean thread shutdown")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
