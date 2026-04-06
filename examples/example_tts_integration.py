"""
Example: Using Janus with TTS enabled
Demonstrates TTS integration in the main application
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def example_tts_disabled():
    """Example 1: TTS disabled (default)"""
    print("\n=== Example 1: TTS Disabled (Default) ===\n")

    try:
        from main import Janus

        # Initialize Janus with TTS disabled
        app = Janus(
            model_size="tiny", language="fr", tts_override=False  # Explicitly disable TTS
        )

        # Process a command
        print("Processing command: 'ouvre Safari'")
        result = app.process_command("ouvre Safari")
        print(f"Result: {'Success' if result else 'Failed'}")

        # Note: No voice feedback with TTS disabled
        print("\nNote: TTS is disabled, so no voice feedback was given.")

        # Cleanup
        app.cleanup()

    except ImportError as e:
        print(f"⚠ Skipped: Missing dependencies ({e})")
        print("  This example requires full Janus installation")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


def example_tts_enabled():
    """Example 2: TTS enabled"""
    print("\n=== Example 2: TTS Enabled ===\n")

    try:
        from main import Janus

        # Initialize Janus with TTS enabled
        app = Janus(
            model_size="tiny", language="fr", tts_override=True  # Override config to enable TTS
        )

        # Check if TTS is initialized
        if app.tts_adapter:
            print("✓ TTS is initialized and ready")
            print(f"  Voice: {app.tts_adapter.voice or 'default'}")
            print(f"  Rate: {app.tts_adapter.rate} WPM")
            print(f"  Language: {app.tts_adapter.default_lang}")
        else:
            print("✗ TTS failed to initialize (may not be available on this system)")

        # Process a command
        print("\nProcessing command: 'ouvre Safari'")
        result = app.process_command("ouvre Safari")
        print(f"Result: {'Success' if result else 'Failed'}")

        if app.tts_integration:
            print("\nNote: TTS should have spoken 'C'est fait' or 'Erreur'")
            print("      (You would hear this on macOS with speakers enabled)")

        # Cleanup
        app.cleanup()

    except ImportError as e:
        print(f"⚠ Skipped: Missing dependencies ({e})")
        print("  This example requires full Janus installation")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


def example_tts_from_config():
    """Example 3: TTS from config.ini"""
    print("\n=== Example 3: TTS from config.ini ===\n")

    from janus.utils import get_config_loader

    # Load config
    config = get_config_loader()

    print("Current TTS configuration:")
    print(f"  Enabled: {config.get_bool('tts', 'enable_tts', fallback=False)}")
    print(f"  Voice: {config.get('tts', 'voice', fallback='default')}")
    print(f"  Rate: {config.get_int('tts', 'rate', fallback=180)} WPM")
    print(f"  Language: {config.get('tts', 'lang', fallback='fr-FR')}")
    print(f"  Verbosity: {config.get('tts', 'verbosity', fallback='compact')}")

    print("\nTo enable TTS, edit config.ini and set:")
    print("  [tts]")
    print("  enable_tts = true")
    print("  voice = Thomas")
    print("  rate = 180")


def example_manual_tts():
    """Example 4: Manual TTS usage"""
    print("\n=== Example 4: Manual TTS Usage ===\n")

    try:
        from janus.io.tts import MacTTSAdapter

        print("Creating TTS adapter...")
        tts = MacTTSAdapter(
            voice="Thomas", rate=180, lang="fr-FR", enable_queue=False  # Synchronous for demo
        )

        print("Available voices (first 5):")
        voices = tts.get_available_voices()[:5]
        for voice in voices:
            print(f"  - {voice}")

        print("\nSpeaking test message...")
        print("Text: 'Bonjour, ceci est un test'")

        # This will work on macOS with the 'say' command
        # On other systems, it will fail gracefully
        success = tts.speak("Bonjour, ceci est un test", lang="fr")

        if success:
            print("✓ Message queued successfully")
            print("  (You would hear this on macOS)")
        else:
            print("✗ Message failed (system may not support TTS)")

        # Cleanup
        tts.shutdown()

    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: TTS requires macOS with the 'say' command")


def main():
    """Run all examples"""
    print("=" * 60)
    print("Janus TTS Integration Examples")
    print("=" * 60)

    # Run examples that don't require full dependencies
    example_tts_from_config()
    example_manual_tts()

    # These examples require full Janus dependencies
    print("\n" + "=" * 60)
    print("Testing with full Janus dependencies...")
    print("=" * 60)

    example_tts_disabled()
    example_tts_enabled()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nTo test TTS integration:")
    print("  1. Edit config.ini and set enable_tts = true")
    print("  2. Run: python main.py --enable-tts")
    print("  3. Speak a command or use --once flag")
    print("\nFor more examples, see: examples/example_tts_usage.py")


if __name__ == "__main__":
    main()
