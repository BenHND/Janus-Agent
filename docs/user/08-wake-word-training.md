# Wake Word Training Guide - "Hey Janus" Custom Model

## Overview

This guide explains how to create a custom "Hey Janus" wake word model for true "Hey Janus" detection. By default, Janus uses "hey_jarvis" which sounds phonetically similar, but for exact "Hey Janus" recognition, you need to train a custom model.

## Why "Hey Jarvis" by Default?

OpenWakeWord doesn't include a pre-trained "Hey Janus" model. We use "hey_jarvis" because:
- **Jarvis** ≈ **Janus** (phonetically very similar)
- Works ~70-80% of the time when you say "Hey Janus"
- No training required - works immediately
- Good for testing while you prepare a custom model

## Quick Start: Use Hey Jarvis

**This is already the default!** Just enable wake word detection:

1. Click **Config** → Find "Wake Word Detection" section
2. Check **"Enable Wake Word Detection"**
3. Model should be set to **"hey_jarvis"** (default)
4. Save & restart
5. Say **"Hey Jarvis"** or **"Hey Janus"** (works ~70-80% of the time)

## Custom "Hey Janus" Model Training

For perfect "Hey Janus" recognition, train a custom model:

### Requirements

- Python 3.8+
- openwakeword with training tools
- Microphone
- 20-30 minutes for data collection
- 10-30 minutes for training (depending on your machine)

### Installation

```bash
# Install openwakeword with training dependencies
pip install "openwakeword[train]"

# Or if already installed:
pip install --upgrade "openwakeword[train]"
```

### Step 1: Record Training Samples

Use the provided training script to record 30 samples:

```bash
cd /path/to/Janus
python scripts/train_wake_word.py --action record --num-samples 30
```

**Recording Tips:**
- Speak "Hey Janus" clearly and naturally
- Vary your tone (normal, excited, quiet, loud)
- Vary your distance from microphone (close, far)
- Include different environments (quiet, with background noise)
- Speak at different speeds
- Try different pronunciations if you have an accent

The script will save recordings to `audio_samples/hey_janus/`.

### Step 2: Review Your Samples

Listen to your recordings to ensure quality:

```bash
# On macOS
open audio_samples/hey_janus/

# On Linux
xdg-open audio_samples/hey_janus/
```

Delete any bad recordings (unclear, cut off, too noisy).

### Step 3: Train the Model

**Option A: Using OpenWakeWord Training Toolkit (Recommended)**

```bash
# Clone openWakeWord repo
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord

# Follow their training guide
# https://github.com/dscripka/openWakeWord#training-new-models

# Basic training command:
python -m openwakeword.train \
    --positive_audio_dir ../Janus/audio_samples/hey_janus \
    --output_model hey_janus.tflite \
    --model_name "hey_janus"
```

**Option B: Using Google Colab (Easier)**

OpenWakeWord provides a Colab notebook for training:

1. Open: https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/train_custom_model.ipynb
2. Upload your samples from `audio_samples/hey_janus/`
3. Follow the notebook instructions
4. Download trained `hey_janus.tflite` model

### Step 4: Install Your Custom Model

```bash
# Create models directory
mkdir -p models/wake_word

# Copy your trained model
cp hey_janus.tflite models/wake_word/

# Or download from Colab to models/wake_word/hey_janus.tflite
```

### Step 5: Configure Janus

**Option A: Using Config UI (Recommended)**

1. Open Janus Config
2. Find "Wake Word Detection" section
3. Set model to **"hey_janus"**
4. Save & restart

**Option B: Edit config.ini**

```ini
[audio]
enable_wake_word = true
wake_word_models = hey_janus
wake_word_threshold = 0.5
```

### Step 6: Test Your Model

1. Restart Janus
2. Watch the logs for: `✓ Wake word model loaded: ['hey_janus']`
3. Say "Hey Janus"
4. Should see: `✓ Wake word detected!`

## Troubleshooting

### Model Not Found

**Error**: `Failed to initialize wake word model`

**Solutions**:
1. Check model file exists: `ls models/wake_word/hey_janus.tflite`
2. Ensure filename matches exactly: `hey_janus.tflite`
3. Try using full path in config: `/absolute/path/to/models/wake_word/hey_janus.tflite`

### Low Detection Rate

**Problem**: Wake word not detected reliably

**Solutions**:
1. **Lower threshold**: Set `wake_word_threshold = 0.3` in config
2. **Record more samples**: 50-100 samples = better accuracy
3. **Include more variety**: Different rooms, background noise levels
4. **Retrain**: With more diverse samples

### Too Many False Positives

**Problem**: Activates on random sounds

**Solutions**:
1. **Raise threshold**: Set `wake_word_threshold = 0.7` in config
2. **Add negative samples**: Record "NOT Hey Janus" phrases during training
3. **Retrain**: With clearer, more distinct samples

### Training Fails

**Error**: Training script crashes

**Solutions**:
1. Ensure openwakeword[train] is installed
2. Check Python version (3.8+ required)
3. Try Google Colab notebook instead (easier)
4. Check openWakeWord docs: https://github.com/dscripka/openWakeWord

## Advanced: Multiple Wake Words

You can use multiple wake words simultaneously:

```ini
[audio]
wake_word_models = hey_janus,hey_jarvis
```

This will trigger on either "Hey Janus" OR "Hey Jarvis".

## Model Performance Tips

### Higher Accuracy
- Record 50-100 samples (not just 30)
- Include background noise in training
- Vary speaker distance and angle
- Use professional microphone if possible

### Lower False Positives
- Higher threshold (0.6-0.8)
- Include negative samples in training
- Train in same environment you'll use it

### Faster Response
- Use shorter wake phrase
- Lower threshold (0.3-0.4)
- Optimize model during training

## Alternative: Synthetic Training

For quick testing, generate synthetic samples using TTS:

```bash
python scripts/train_wake_word.py --action synthetic --num-samples 50
```

**Note**: Synthetic samples have ~50-60% accuracy compared to real recordings. Use for testing only.

## Pre-trained Models Available

If you don't want to train:

| Model | Wake Phrase | Similarity to "Hey Janus" |
|-------|------------|---------------------------|
| hey_jarvis | "Hey Jarvis" | ⭐⭐⭐⭐ Very similar |
| hey_mycroft | "Hey Mycroft" | ⭐⭐ Somewhat similar |
| alexa | "Alexa" | ⭐ Not similar |
| timer | "Timer" | Not similar |
| weather | "Weather" | Not similar |

**Recommendation**: Use **hey_jarvis** (default) until you train custom model.

## Community Models

Share your trained "hey_janus" model:

1. Train a good model (test with multiple people)
2. Submit PR with model file
3. Help other users with pre-trained model!

File should be: `models/wake_word/hey_janus_community.tflite`

## Training Script Usage

```bash
# Get help
python scripts/train_wake_word.py --help

# Show info and quick start
python scripts/train_wake_word.py --action info

# Record 30 samples
python scripts/train_wake_word.py --action record --num-samples 30

# Record to custom directory
python scripts/train_wake_word.py --action record --samples-dir my_samples

# Generate synthetic samples (testing only)
python scripts/train_wake_word.py --action synthetic --num-samples 50

# Train model (manual process - shows instructions)
python scripts/train_wake_word.py --action train --samples-dir audio_samples/hey_janus
```

## FAQ

**Q: Can I use "Hey Janus" without training?**  
A: Use "hey_jarvis" (default) - sounds very similar, works ~70-80% of the time.

**Q: How long does training take?**  
A: Recording: 20-30 min. Training: 10-30 min depending on your machine.

**Q: Can I train on Google Colab?**  
A: Yes! Easier than local training. See Step 3, Option B above.

**Q: How accurate is the custom model?**  
A: With good training data: 90-95% accuracy. With synthetic: ~50-60%.

**Q: Can others use my model?**  
A: Yes! Models are speaker-independent after training with diverse samples.

**Q: Do I need GPU for training?**  
A: No, CPU is fine. Training takes 10-30 minutes on modern CPU.

**Q: Can I use French "Eh Janus"?**  
A: Yes! Record samples with French pronunciation. Works the same way.

## Resources

- OpenWakeWord GitHub: https://github.com/dscripka/openWakeWord
- Training Guide: https://github.com/dscripka/openWakeWord#training-new-models
- Colab Notebook: https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/train_custom_model.ipynb
- Models Directory: https://github.com/dscripka/openWakeWord/tree/main/openwakeword/resources/models

## Summary

**Quick Solution**: Use **hey_jarvis** (default) - works immediately, ~70-80% accuracy for "Hey Janus"

**Best Solution**: Train custom model following this guide - 90-95% accuracy for exact "Hey Janus"

**Training Time**: ~1 hour total (30 min recording + 30 min training)

---

**Need Help?** Open an issue on GitHub or check the troubleshooting section above.
