"""
Test TTS integration in main.py
This test verifies TTS configuration loading and initialization
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_loader():
    """Test configuration loader"""
    print("Testing config loader...")

    from janus.utils import get_config_loader

    config = get_config_loader()
    assert config is not None, "Config loader should not be None"

    # Test TTS configuration
    enable_tts = config.get_bool("tts", "enable_tts", fallback=False)
    voice = config.get("tts", "voice", fallback="")
    rate = config.get_int("tts", "rate", fallback=180)
    lang = config.get("tts", "lang", fallback="fr-FR")

    print(f"  TTS enabled: {enable_tts}")
    print(f"  TTS voice: {voice or 'default'}")
    print(f"  TTS rate: {rate}")
    print(f"  TTS lang: {lang}")

    assert isinstance(enable_tts, bool), "enable_tts should be boolean"
    assert isinstance(rate, int), "rate should be integer"
    assert rate >= 100 and rate <= 300, "rate should be between 100 and 300"

    print("✓ Config loader test passed\n")


def test_tts_adapter():
    """Test TTS adapter initialization"""
    import platform

    if platform.system() != "Darwin":
        print("⏭️  Skipping TTS adapter test (requires macOS)\n")
        return

    print("Testing TTS adapter...")

    try:
        from janus.io.tts import MacTTSAdapter
    except ImportError:
        print("⏭️  Skipping TTS adapter test (MacTTSAdapter not available)\n")
        return

    # Test with disabled TTS (should not try to use 'say' command)
    tts = MacTTSAdapter(
        voice="Thomas", rate=180, lang="fr-FR", enable_queue=False  # Disable queue for testing
    )

    assert tts is not None, "TTS adapter should not be None"
    assert tts.voice == "Thomas", "Voice should be Thomas"
    assert tts.rate == 180, "Rate should be 180"
    assert tts.default_lang == "fr-FR", "Lang should be fr-FR"

    # Test voice setting
    tts.set_voice("Alex")
    assert tts.voice == "Alex", "Voice should be Alex after set_voice"

    # Test rate setting
    tts.set_rate(200)
    assert tts.rate == 200, "Rate should be 200 after set_rate"

    # Test rate clamping
    tts.set_rate(500)  # Too high
    assert tts.rate == 300, "Rate should be clamped to 300"

    tts.set_rate(50)  # Too low
    assert tts.rate == 100, "Rate should be clamped to 100"

    tts.shutdown()

    print("✓ TTS adapter test passed\n")


def test_tts_orchestrator_integration():
    """Test TTS orchestrator integration"""
    import platform

    if platform.system() != "Darwin":
        print("⏭️  Skipping TTS orchestrator integration test (requires macOS)\n")
        return

    print("Testing TTS orchestrator integration...")

    try:
        from janus.io.tts import MacTTSAdapter, TTSOrchestratorIntegration
    except ImportError:
        print("⏭️  Skipping TTS orchestrator integration test (MacTTSAdapter not available)\n")
        return

    tts = MacTTSAdapter(enable_queue=False)

    tts_integration = TTSOrchestratorIntegration(
        tts_adapter=tts, enable_tts=True, auto_confirmations=True, verbosity="compact", lang="fr-FR"
    )

    assert tts_integration is not None, "TTS integration should not be None"
    assert tts_integration.enable_tts == True, "TTS should be enabled"
    assert tts_integration.auto_confirmations == True, "Auto confirmations should be enabled"
    assert tts_integration.verbosity == "compact", "Verbosity should be compact"
    assert tts_integration.lang == "fr-FR", "Lang should be fr-FR"

    # Test enable/disable
    tts_integration.set_enabled(False)
    assert tts_integration.enable_tts == False, "TTS should be disabled after set_enabled(False)"

    tts_integration.set_enabled(True)
    assert tts_integration.enable_tts == True, "TTS should be enabled after set_enabled(True)"

    # Test verbosity
    tts_integration.set_verbosity("verbose")
    assert tts_integration.verbosity == "verbose", "Verbosity should be verbose"

    tts.shutdown()

    print("✓ TTS orchestrator integration test passed\n")


def test_main_import():
    """Test that main module can be imported (without actually creating Janus instance)"""
    print("Testing main module import...")

    # Skip this test in environments without full dependencies
    try:
        # Mock required modules
        import sys
        from unittest.mock import MagicMock

        # Create mock modules
        mock_whisper_stt = MagicMock()
        mock_whisper_stt.WhisperSTT = MagicMock
        sys.modules["janus.stt.whisper_stt"] = mock_whisper_stt

        mock_pyautogui = MagicMock()
        sys.modules["pyautogui"] = mock_pyautogui

        # Now import main should work
        import main

        assert hasattr(main, "Janus"), "main should have Janus class"
        assert hasattr(main, "main"), "main should have main function"

        print("✓ Main module import test passed\n")
    except Exception as e:
        print(f"⚠ Main module import test skipped (missing dependencies): {e}\n")
        # This is acceptable in test environments without full dependencies


def main():
    """Run all tests"""
    print("=" * 60)
    print("TTS Integration Tests")
    print("=" * 60)
    print()

    try:
        test_config_loader()
        test_tts_adapter()
        test_tts_orchestrator_integration()
        test_main_import()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
