#!/usr/bin/env python3
"""
Example: Wake Word Detection Demo
TICKET-P3-02: Mode "Mains Libres" (Wake Word)

This example demonstrates the wake word detection feature in isolation,
showing how to use the WakeWordDetector class directly.

Requirements:
- openwakeword library installed: pip install openwakeword
- Microphone connected and working

Usage:
    python examples/example_wake_word_demo.py
"""

import sys
import time
import signal
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.io.stt.wake_word_detector import create_wake_word_detector


def main():
    """Main demo function"""
    print("=" * 60)
    print("Wake Word Detection Demo (TICKET-P3-02)")
    print("=" * 60)
    print()
    print("This demo shows the wake word detector running in isolation.")
    print("Say 'Hey Janus' to trigger detection.")
    print("Press Ctrl+C to exit.")
    print()
    
    # Create wake word detector
    print("Initializing wake word detector...")
    detector = create_wake_word_detector(
        enable_wake_word=True,
        wake_words=["hey_janus"],
        threshold=0.5,
    )
    
    if not detector:
        print("❌ Failed to create wake word detector")
        print("   Make sure openwakeword is installed: pip install openwakeword")
        return 1
    
    print("✓ Wake word detector initialized")
    print()
    
    # Detection counter
    detection_count = [0]  # Use list for mutable counter in callback
    
    def on_wake_word_detected():
        """Callback when wake word is detected"""
        detection_count[0] += 1
        print(f"\n✓ Wake word detected! (#{detection_count[0]})")
        print("💤 Listening for wake word...\n")
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\n👋 Shutting down...")
        detector.stop()
        print(f"Total detections: {detection_count[0]}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start detection
    print("Starting wake word detection...")
    detector.start(on_wake_word_detected)
    print("✓ Wake word detector started")
    print()
    print("💤 Listening for wake word...")
    print("   Say 'Hey Janus' to trigger detection")
    print("   Press Ctrl+C to stop")
    print()
    
    # Keep running
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        detector.stop()
        print(f"Total detections: {detection_count[0]}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
