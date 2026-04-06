#!/usr/bin/env python3
"""
Demo script for Correction Dialog and Learning Integration
Shows how the learning module integrates with the pipeline and correction UI
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile

from janus.runtime.core.contracts import Intent
from janus.learning.learning_manager import LearningManager

# Try to import correction dialog, but don't fail if tkinter not available
try:
    from janus.ui.correction_dialog import CorrectionDialog, show_correction_dialog

    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    print("Note: tkinter not available - correction dialog demo will be skipped")


def demo_correction_dialog_basic():
    """Demo: Basic correction dialog usage"""
    print("=" * 60)
    print("DEMO 1: Basic Correction Dialog")
    print("=" * 60)

    if not HAS_GUI:
        print("\n⚠️ Tkinter not available - skipping GUI demo")
        print("   In a GUI environment, this would show an interactive dialog.")
        return

    # Create a wrong intent
    wrong_intent = Intent(
        action="open_app",
        parameters={"app_name": "Chrome"},
        confidence=0.8,
        raw_command="ouvre Firefox",
    )

    print(f"\nCommand: {wrong_intent.raw_command}")
    print(f"Wrong interpretation: {wrong_intent.action} -> {wrong_intent.parameters}")
    print("\nNote: This demo requires a GUI environment with tkinter.")
    print("In a headless environment, the dialog cannot be displayed.")

    try:
        # Show correction dialog
        result = show_correction_dialog(command=wrong_intent.raw_command, wrong_intent=wrong_intent)

        if result and result.corrected:
            print(f"\n✅ User corrected!")
            print(f"   Correct interpretation: {result.correct_interpretation}")
            if result.notes:
                print(f"   Notes: {result.notes}")
        else:
            print("\n❌ User cancelled correction")
    except Exception as e:
        print(f"\n⚠️ Could not show dialog: {e}")
        print("   (This is expected in headless environments)")


def demo_learning_integration():
    """Demo: Learning integration with pipeline"""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Learning Integration")
    print("=" * 60)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        db_path = db_file.name

    try:
        # Initialize learning manager
        manager = LearningManager(db_path=db_path, auto_update=False)
        print("\n✅ Learning Manager initialized")

        # Start a session
        session_id = manager.start_session()
        print(f"✅ Session started: {session_id}")

        # Simulate successful command execution
        print("\n--- Simulating successful command ---")
        intent = Intent(
            action="open_app",
            parameters={"app_name": "Chrome"},
            confidence=0.9,
            raw_command="ouvre Chrome",
        )

        feedback_id = manager.record_feedback(
            text=intent.raw_command, intent=intent, feedback_type="POSITIVE"
        )
        print(f"✅ Positive feedback recorded (ID: {feedback_id})")

        # Simulate failed command execution
        print("\n--- Simulating failed command ---")
        failed_intent = Intent(
            action="unknown",
            parameters={},
            confidence=0.3,
            raw_command="fais quelque chose de bizarre",
        )

        feedback_id = manager.record_feedback(
            text=failed_intent.raw_command, intent=failed_intent, feedback_type="NEGATIVE"
        )
        print(f"✅ Negative feedback recorded (ID: {feedback_id})")

        # Record a user correction
        print("\n--- Recording user correction ---")

        # First record the action that was wrong
        action_record = {
            "action_type": "open_app",
            "parameters": {"app_name": "Chrome"},
            "success": True,
            "timestamp": "2024-01-01T00:00:00",
        }
        manager.correction_listener.record_action(action_record)

        correction = manager.record_user_correction(
            correction_text="non",  # Correction phrase
            language="fr",
            alternative_action={"action": "open_app", "app_name": "Firefox"},
        )

        if correction:
            print("✅ User correction recorded")
            print(f"   Original action: {correction['original_action']}")
            print(f"   Alternative: {correction.get('alternative_action')}")

        # Get learning status
        print("\n--- Learning Status ---")
        status = manager.get_learning_status()
        print(f"Profile: {status['profile']}")
        print(f"Total actions: {status['total_actions']}")
        print(f"Total corrections: {status['total_corrections']}")
        print(f"Session active: {status['session_active']}")

        # Get success rate
        print("\n--- Performance Metrics ---")
        success_rate = manager.get_success_rate(days=30)
        print(f"Success rate (last 30 days): {success_rate:.1f}%")

        # End session
        report = manager.end_session()
        print(f"\n✅ Session ended")
        if report:
            print(f"   Session summary:")
            print(f"   - Total actions: {report['summary']['total_actions']}")
            print(f"   - Success rate: {report['summary']['success_rate']:.1f}%")

    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("\n✅ Cleanup complete")


def demo_pipeline_integration():
    """Demo: How pipeline uses learning"""
    print("\n\n" + "=" * 60)
    print("DEMO 3: Pipeline Integration Concept")
    print("=" * 60)

    print(
        """
The JanusPipeline integrates learning through several mechanisms:

1. AUTOMATIC FEEDBACK RECORDING
   - On successful execution → POSITIVE feedback
   - On failed execution → NEGATIVE feedback
   - Recorded for both command parsing and action execution

2. LEARNING PARSER
   - When enable_learning=True, uses LearningCommandParser
   - Applies learned patterns automatically
   - Provides recommended parameters
   - Detects actions to avoid

3. CORRECTION DIALOG
   - Can be shown when user wants to correct
   - Captures correct interpretation
   - Records alternative actions
   - Feeds back into learning system

Example pipeline flow:
    """
    )

    print(
        """
    User says: "ouvre Chrome"
    ↓
    Pipeline parses with LearningCommandParser
    ↓
    Intent detected: open_app(app_name='Chrome')
    ↓
    Pipeline executes action
    ↓
    If SUCCESS → record_feedback(text, intent, 'POSITIVE')
    If FAILURE → record_feedback(text, intent, 'NEGATIVE')
    ↓
    [Optional] User corrects via CorrectionDialog
    ↓
    Learning system updates patterns
    ↓
    Future commands benefit from learned patterns
    """
    )


def main():
    """Run all demos"""
    print("\n" + "█" * 60)
    print("  SPECTRA LEARNING MODULE DEMO")
    print("  Ticket A7 - Learning Module Integration")
    print("█" * 60)

    # Run demos
    demo_learning_integration()
    demo_pipeline_integration()
    demo_correction_dialog_basic()

    print("\n\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("✅ Automatic feedback recording (POSITIVE/NEGATIVE)")
    print("✅ Learning manager session management")
    print("✅ User correction recording")
    print("✅ Performance metrics tracking")
    print("✅ Pipeline integration architecture")
    print("✅ Correction dialog UI (requires GUI)")

    print("\nFor GUI demo, run in a desktop environment with tkinter installed.")
    print("\nLearning module is now fully integrated! 🎉")


if __name__ == "__main__":
    main()
