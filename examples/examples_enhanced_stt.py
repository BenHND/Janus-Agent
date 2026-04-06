#!/usr/bin/env python3
"""
Example demonstrating the enhanced speech-to-text features in Janus
Shows usage of correction dictionary, text normalization, audio logging, and calibration
"""

import os
import sys

# Ensure janus module is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from janus.io.stt import AudioLogger, CalibrationManager, CorrectionDictionary, TextNormalizer


def example_correction_dictionary():
    """Demonstrate correction dictionary usage"""
    print("=" * 60)
    print("EXAMPLE 1: Correction Dictionary")
    print("=" * 60)

    # Create correction dictionary
    dict = CorrectionDictionary()

    # Test common corrections
    test_phrases = [
        "ouvre vs code",
        "lance fire fox",
        "ferme visual studio code",
        "ouvre v s cold",
    ]

    print("\nCorrecting common phonetic errors:")
    for phrase in test_phrases:
        corrected = dict.correct_text(phrase)
        print(f"  '{phrase}' → '{corrected}'")

    # Add custom correction
    print("\nAdding custom correction:")
    dict.add_correction("git lab", "gitlab")
    test = "ouvre git lab"
    corrected = dict.correct_text(test)
    print(f"  '{test}' → '{corrected}'")

    # Save corrections
    dict.save_to_file("custom_corrections.json")
    print("\n✓ Corrections saved to custom_corrections.json")

    print()


def example_text_normalizer():
    """Demonstrate text normalization"""
    print("=" * 60)
    print("EXAMPLE 2: Text Normalizer")
    print("=" * 60)

    normalizer = TextNormalizer()

    # Test normalization
    test_cases = [
        "euh ouvre euh le navigateur",
        "j'ouvre l'application chrome",
        "um open like the browser you know",
        "ouvre ouvre le terminal",
        "ouvre trois fenêtres",
    ]

    print("\nNormalizing text:")
    for text in test_cases:
        normalized = normalizer.normalize(text)
        print(f"  '{text}'")
        print(f"  → '{normalized}'")
        print()

    # Test command cleaning
    print("Command-specific cleaning:")
    command = "euh, ouvre le navigateur chrome."
    cleaned = normalizer.clean_command_text(command)
    print(f"  '{command}'")
    print(f"  → '{cleaned}'")

    print()


def example_audio_logger():
    """Demonstrate audio logging"""
    print("=" * 60)
    print("EXAMPLE 3: Audio Logger")
    print("=" * 60)

    # Create logger
    logger = AudioLogger(log_dir="demo_audio_logs", max_logs=100)

    # Simulate logging transcriptions
    print("\nLogging transcriptions:")

    # Log successful transcription
    log_id1 = logger.log_transcription(
        audio_path="dummy_audio.wav",
        raw_transcription="euh ouvre vs code",
        corrected_transcription="euh ouvre vscode",
        normalized_transcription="Ouvre vscode",
        language="fr",
        model="base",
        confidence=0.95,
    )
    print(f"  ✓ Logged successful transcription: {log_id1}")

    # Log failed transcription
    log_id2 = logger.log_transcription(
        audio_path="dummy_audio2.wav",
        raw_transcription="",
        language="fr",
        model="base",
        error="Audio quality too poor",
    )
    print(f"  ✓ Logged failed transcription: {log_id2}")

    # Get statistics
    print("\nLogger Statistics:")
    stats = logger.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get recent logs
    print("\nRecent Logs:")
    recent = logger.get_recent_logs(count=2)
    for log in recent:
        status = "✓ Success" if log["success"] else "✗ Failed"
        print(f"  {status} - {log['timestamp']}")
        print(f"    Raw: {log['raw_transcription'][:50]}")

    print()


def example_calibration():
    """Demonstrate calibration system"""
    print("=" * 60)
    print("EXAMPLE 4: Calibration Manager")
    print("=" * 60)

    manager = CalibrationManager(profile_dir="demo_calibration")

    # Get calibration phrases
    print("\nCalibration Phrases (French):")
    phrases_fr = manager.get_calibration_phrases("fr")
    for i, phrase in enumerate(phrases_fr, 1):
        print(f"  {i}. {phrase}")

    print("\nCalibration Phrases (English):")
    phrases_en = manager.get_calibration_phrases("en")
    for i, phrase in enumerate(phrases_en, 1):
        print(f"  {i}. {phrase}")

    # Simulate calibration with sample data
    print("\nSimulating calibration with sample audio data:")
    audio_samples = [
        (b"\x00\x00" * 1000, 50.0),  # Low energy (ambient)
        (b"\x00\x00" * 1000, 500.0),  # High energy (speech)
        (b"\x00\x00" * 1000, 480.0),
        (b"\x00\x00" * 1000, 520.0),
        (b"\x00\x00" * 1000, 510.0),
    ]

    profile = manager.calibrate_from_samples(
        user_id="demo_user", audio_samples=audio_samples, language="fr"
    )

    print("\nCalibration Results:")
    print(f"  User: {profile.user_id}")
    print(f"  Silence Threshold: {profile.silence_threshold} chunks (~{profile.silence_threshold * 20 / 1000:.1f}s)")
    print(f"  Ambient Noise Level: {profile.ambient_noise_level:.1f}")
    print(f"  Language: {profile.language}")
    print(f"\n  Note: Recording starts immediately (no activation wait)")
    print(f"        Silence threshold used to stop recording only")

    # Generate report
    print("\n" + manager.generate_calibration_report(profile))

    # List profiles
    print("Saved Profiles:")
    profiles = manager.list_profiles()
    for profile_id in profiles:
        print(f"  - {profile_id}")

    print()


def example_integration():
    """Demonstrate full integration"""
    print("=" * 60)
    print("EXAMPLE 5: Full Integration")
    print("=" * 60)

    print("\nThis example shows how all components work together:")
    print("1. Audio is recorded")
    print("2. Whisper transcribes it (raw)")
    print("3. CorrectionDictionary fixes phonetic errors")
    print("4. TextNormalizer cleans and reformulates")
    print("5. AudioLogger saves everything for audit")
    print("6. CalibrationProfile optimizes future recordings")

    # Simulate the pipeline
    print("\n--- Simulated Pipeline ---")

    raw_text = "euh ouvre vs code"
    print(f"1. Raw transcription: '{raw_text}'")

    dict = CorrectionDictionary()
    corrected_text = dict.correct_text(raw_text)
    print(f"2. After corrections: '{corrected_text}'")

    normalizer = TextNormalizer()
    normalized_text = normalizer.normalize(corrected_text)
    print(f"3. After normalization: '{normalized_text}'")

    logger = AudioLogger(log_dir="demo_logs")
    log_id = logger.log_transcription(
        audio_path="demo.wav",
        raw_transcription=raw_text,
        corrected_transcription=corrected_text,
        normalized_transcription=normalized_text,
        language="fr",
        model="base",
    )
    print(f"4. Logged as: {log_id}")

    print(f"\n✓ Final result: '{normalized_text}'")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("SPECTRA ENHANCED SPEECH-TO-TEXT EXAMPLES")
    print("=" * 60 + "\n")

    try:
        example_correction_dictionary()
        example_text_normalizer()
        example_audio_logger()
        example_calibration()
        example_integration()

        print("=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
