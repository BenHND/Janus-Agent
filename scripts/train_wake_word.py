#!/usr/bin/env python3
"""
Custom Wake Word Model Training Script for Janus
TICKET-P3-02: Create custom "Hey Janus" wake word model

This script helps users create a custom wake word model for "Hey Janus"
using the openWakeWord toolkit.

Requirements:
- openwakeword installed with training tools
- 20-30 audio samples of "Hey Janus" spoken clearly
- Background noise samples (optional but recommended)

Usage:
    python scripts/train_wake_word.py --wake-word "hey janus" --samples-dir audio_samples/
"""

import argparse
import os
import sys
from pathlib import Path

print("""
╔════════════════════════════════════════════════════════════════╗
║  Janus Custom Wake Word Training Tool                         ║
║  TICKET-P3-02: Train "Hey Janus" wake word model              ║
╚════════════════════════════════════════════════════════════════╝
""")


def check_dependencies():
    """Check if required dependencies are installed"""
    print("📦 Checking dependencies...")
    
    try:
        import openwakeword
        print("  ✓ openwakeword installed")
    except ImportError:
        print("  ✗ openwakeword not installed")
        print("    Install with: pip install openwakeword")
        return False
    
    try:
        import sounddevice
        print("  ✓ sounddevice installed")
    except ImportError:
        print("  ⚠️  sounddevice not installed (optional, for recording)")
        print("    Install with: pip install sounddevice")
    
    try:
        import scipy
        print("  ✓ scipy installed")
    except ImportError:
        print("  ⚠️  scipy not installed (optional, for audio processing)")
    
    return True


def record_samples(output_dir: str, num_samples: int = 30):
    """
    Record audio samples for wake word training
    
    Args:
        output_dir: Directory to save recordings
        num_samples: Number of samples to record
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    except ImportError:
        print("❌ Recording requires sounddevice and soundfile")
        print("   Install with: pip install sounddevice soundfile")
        return False
    
    print(f"\n🎤 Recording {num_samples} samples of 'Hey Janus'")
    print("=" * 60)
    print()
    print("Instructions:")
    print("  1. Speak 'Hey Janus' clearly when prompted")
    print("  2. Vary your tone, speed, and distance from mic")
    print("  3. Include some samples with background noise")
    print("  4. Press Enter when ready for each recording")
    print()
    
    os.makedirs(output_dir, exist_ok=True)
    
    sample_rate = 16000  # 16kHz recommended for wake word
    duration = 2.0  # 2 seconds per sample
    
    for i in range(num_samples):
        input(f"Sample {i+1}/{num_samples} - Press Enter and say 'Hey Janus': ")
        print(f"  🔴 Recording...")
        
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        
        filename = os.path.join(output_dir, f"hey_janus_{i+1:03d}.wav")
        sf.write(filename, audio, sample_rate)
        print(f"  ✓ Saved: {filename}")
    
    print()
    print(f"✅ Recorded {num_samples} samples in {output_dir}")
    return True


def generate_synthetic_samples(output_dir: str, num_samples: int = 30):
    """
    Generate synthetic training samples using TTS
    
    Note: This function is a placeholder. Synthetic sample generation
    is not yet fully implemented. Real voice recordings are strongly
    recommended for accuracy.
    """
    print(f"\n🤖 Synthetic sample generation...")
    print("⚠️  Feature not yet implemented")
    print("   Real voice recordings strongly recommended for accuracy")
    print("   Use: python scripts/train_wake_word.py --action record")
    
    return False


def train_model(samples_dir: str, output_model: str, wake_word: str = "hey janus"):
    """
    Provide instructions for training wake word model using openWakeWord toolkit
    
    Note: This function provides guidance and validation only. Actual training
    must be done using the openWakeWord training toolkit (see instructions).
    
    Args:
        samples_dir: Directory containing training samples
        output_model: Path where trained model should be saved
        wake_word: Wake word phrase
    """
    print(f"\n🎯 Training instructions for '{wake_word}' model...")
    print("=" * 60)
    
    print("""
⚠️  Note: Full model training requires the openWakeWord training toolkit
    
To train a production-quality model:
    
1. Install training dependencies:
   pip install openwakeword[train]
   
2. Prepare your data:
   - 20-30 positive samples (saying "Hey Janus")
   - Background noise samples (optional but recommended)
   
3. Use openWakeWord's training tools:
   https://github.com/dscripka/openWakeWord#training-new-models
   
4. Place trained model in: models/wake_word/hey_janus.tflite
   
5. Update config.ini:
   wake_word_models = hey_janus
   
For now, you can:
- Use 'hey_jarvis' as a similar-sounding alternative
- Or use the pre-trained model if provided in the repo
""")
    
    # Check if samples exist
    if not os.path.exists(samples_dir):
        print(f"❌ Samples directory not found: {samples_dir}")
        return False
    
    sample_files = list(Path(samples_dir).glob("*.wav"))
    if len(sample_files) < 10:
        print(f"⚠️  Only {len(sample_files)} samples found")
        print("   Recommend at least 20-30 samples for good accuracy")
    
    print(f"Found {len(sample_files)} training samples")
    
    # Training would happen here with openWakeWord toolkit
    print("\n✋ Automatic training not yet implemented")
    print("   Please follow the manual training guide above")
    
    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Train custom wake word model for Janus"
    )
    parser.add_argument(
        "--wake-word",
        default="hey janus",
        help="Wake word phrase (default: 'hey janus')"
    )
    parser.add_argument(
        "--action",
        choices=["record", "synthetic", "train", "info"],
        default="info",
        help="Action to perform (default: info)"
    )
    parser.add_argument(
        "--samples-dir",
        default="audio_samples/hey_janus",
        help="Directory for audio samples"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=30,
        help="Number of samples to record/generate"
    )
    parser.add_argument(
        "--output-model",
        default="models/wake_word/hey_janus.tflite",
        help="Output model path"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Missing required dependencies")
        return 1
    
    if args.action == "record":
        success = record_samples(args.samples_dir, args.num_samples)
        if success:
            print("\n✅ Next steps:")
            print(f"   1. Review samples in: {args.samples_dir}")
            print(f"   2. Run: python {sys.argv[0]} --action train --samples-dir {args.samples_dir}")
    
    elif args.action == "synthetic":
        success = generate_synthetic_samples(args.samples_dir, args.num_samples)
        if success:
            print("\n✅ Next steps:")
            print(f"   1. Run: python {sys.argv[0]} --action train --samples-dir {args.samples_dir}")
    
    elif args.action == "train":
        train_model(args.samples_dir, args.output_model, args.wake_word)
    
    else:  # info
        print("""
📖 Wake Word Training Information
═══════════════════════════════════════════════════════════════

Current Situation:
  • OpenWakeWord doesn't include a pre-trained "Hey Janus" model
  • Available models: alexa, hey_mycroft, hey_jarvis, timer, weather
  • Custom models require training with your voice samples

Quick Solutions:
  
  1. Use 'hey_jarvis' (similar pronunciation):
     • Change wake_word_models = hey_jarvis in config.ini
     • Should recognize ~70-80% of "Hey Janus" attempts
  
  2. Train custom 'hey_janus' model (recommended):
     • Record samples: python scripts/train_wake_word.py --action record
     • Follow training guide (see documentation)
     • Higher accuracy for "Hey Janus" specifically

Training Steps:
  
  Step 1: Record samples
    python scripts/train_wake_word.py --action record --num-samples 30
  
  Step 2: Install training tools
    pip install openwakeword[train]
  
  Step 3: Follow openWakeWord training guide
    https://github.com/dscripka/openWakeWord#training-new-models
  
  Step 4: Place model in models/wake_word/
    cp hey_janus.tflite models/wake_word/
  
  Step 5: Update config.ini
    wake_word_models = hey_janus

Alternative: Use pre-trained similar model
  • Set wake_word_models = hey_jarvis
  • Jarvis ≈ Janus (phonetically similar)
  • Works immediately, no training needed

For more info: docs/user/08-wake-word-training.md
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
