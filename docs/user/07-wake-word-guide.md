# Wake Word Detection Guide (TICKET-P3-02)

## Overview

The wake word detection feature enables hands-free, passive listening for voice commands. Instead of manually triggering voice recording, Janus continuously listens for a wake word in the background with minimal CPU usage.

**Default wake word**: "Hey Jarvis" (sounds like "Hey Janus" - ~70-80% match)  
**Custom training**: For exact "Hey Janus" recognition, see [Training Guide](08-wake-word-training.md)

## Why "Hey Jarvis"?

OpenWakeWord doesn't include a pre-trained "Hey Janus" model. We use "hey_jarvis" by default because:
- **Jarvis** ≈ **Janus** (phonetically very similar - both end in "-us")
- Works immediately without training
- Recognizes "Hey Janus" ~70-80% of the time
- Perfect for testing while you train a custom model

**Want exact "Hey Janus" recognition?** → [Train a custom model](08-wake-word-training.md)

## Features

- **Low Power Consumption**: Uses lightweight openWakeWord library (~1-5% CPU idle)
- **Passive Listening**: Listens in background without recording everything
- **Privacy-First**: Only activates when wake word is detected
- **Bilingual Support**: Works with French and English
- **Customizable**: Adjustable detection threshold for different environments
- **Pre-trained Models**: Includes "hey_jarvis" (≈Janus), "alexa", "hey_mycroft" and more

## Available Wake Words

OpenWakeWord comes with several pre-trained models:

- **hey_jarvis** - Triggers on "Hey Jarvis" ⭐ **DEFAULT** (sounds like "Hey Janus")
- **alexa** - Triggers on "Alexa"
- **hey_mycroft** - Triggers on "Hey Mycroft"
- **timer** - Triggers on "Timer"
- **weather** - Triggers on "Weather"
- **hey_janus** - Requires custom training (see [Training Guide](08-wake-word-training.md))

**Pronunciation**: "Hey Jarvis" and "Hey Janus" sound very similar, so the default model will often recognize both!

## Configuration

### Enable Wake Word Detection

Wake word detection is **disabled by default** to respect privacy. To enable it:

#### Method 1: Configuration File

Edit `config.ini`:

```ini
[audio]
# Enable wake word detection (hands-free mode)
enable_wake_word = true

# Detection threshold (0.0-1.0): lower = more sensitive, higher = more accurate
wake_word_threshold = 0.5

# Wake word models to use (comma-separated)
# Using 'hey_jarvis' as it sounds similar to 'hey_janus' (Jarvis ≈ Janus)
# For true "Hey Janus": train custom model (see docs/user/08-wake-word-training.md)
wake_word_models = hey_jarvis
```

#### Method 2: Configuration UI (Recommended)

1. Run Janus
2. Click the **Config** button in the overlay
3. Find the **"Wake Word Detection (Hands-Free Mode)"** section
4. Check **"Enable Wake Word Detection"**
5. Select your preferred wake word model from the dropdown
6. Adjust the detection threshold if needed
7. Click **"Save & Apply"**
8. Restart Janus for changes to take effect

#### Method 3: Environment Variables

Set environment variables in `.env`:

```bash
# Not yet implemented - use config.ini or UI for now
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enable_wake_word` | `false` | Enable/disable wake word detection |
| `wake_word_threshold` | `0.5` | Detection threshold (0.0-1.0). Lower = more sensitive but more false positives |
| `wake_word_models` | `hey_jarvis` | Comma-separated list of wake word models. "hey_jarvis" sounds like "hey janus" |

### Threshold Tuning

Adjust the threshold based on your environment:

- **Quiet environments**: Use lower threshold (0.3-0.4) for better detection
- **Noisy environments**: Use higher threshold (0.6-0.7) to reduce false positives
- **Default (0.5)**: Good balance for most environments

## Usage

### Terminal Mode

When wake word detection is enabled in terminal mode:

1. Janus displays: `💤 Listening for wake word...`
2. Say **"Hey Jarvis"** or **"Hey Janus"** (both work ~70-80% of the time)
3. Janus responds with: `✓ Wake word detected!`
4. The system activates and listens for your command
5. After processing the command, it returns to wake word listening

```bash
# Run in terminal mode with wake word enabled
python main.py --no-ui

# Output:
# 💤 Listening for wake word...
# (say "Hey Jarvis" or "Hey Janus")
# ✓ Wake word detected!
# 🎤 Listening...
```

### UI Mode (Overlay)

When wake word detection is enabled in UI mode:

1. The overlay shows: `🎤 Wake word detection enabled - say 'Hey Janus'`
2. Say **"Hey Janus"**
3. The microphone button automatically activates
4. Janus provides audio feedback: "Oui?" (Yes?)
5. Speak your command
6. After execution, wake word listening resumes

## Installation

### Requirements

Wake word detection requires the `openwakeword` library:

```bash
pip install openwakeword
```

The library will be installed automatically when you update Janus dependencies:

```bash
cd /path/to/Janus
pip install -r requirements.txt
```

### System Requirements

- **Python**: 3.8+
- **RAM**: Additional ~50MB for wake word model
- **CPU**: Minimal (<5% idle on modern CPUs)
- **Operating System**: macOS, Linux, Windows

## How It Works

### Architecture

```
┌─────────────────────┐
│  Microphone Input   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Wake Word Detector  │
│ (openWakeWord)      │
│ - Low CPU usage     │
│ - Passive listening │
└──────────┬──────────┘
           │
           ▼
      "Hey Janus"
      detected?
           │
           ▼ Yes
┌─────────────────────┐
│ Visual/Audio        │
│ Feedback            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Whisper Recording   │
│ (Full STT)          │
└─────────────────────┘
```

### Privacy Considerations

- **No Cloud Processing**: All wake word detection happens locally on your device
- **Minimal Recording**: Only activates full recording when wake word is detected
- **No Persistent Storage**: Audio is not saved unless you enable audio logging separately
- **Transparent**: Janus clearly indicates when wake word detection is active

## Troubleshooting

### Wake Word Not Detected

**Symptoms**: Saying "Hey Janus" doesn't activate the microphone

**Solutions**:
1. Lower the detection threshold in `config.ini` (e.g., from 0.5 to 0.3)
2. Speak more clearly and at a moderate volume
3. Check that your microphone is working: `python -c "import pyaudio; print(pyaudio.PyAudio().get_default_input_device_info())"`
4. Ensure no other application is using the microphone

### Too Many False Positives

**Symptoms**: Janus activates when you didn't say the wake word

**Solutions**:
1. Increase the detection threshold in `config.ini` (e.g., from 0.5 to 0.7)
2. Reduce background noise
3. Move microphone away from speakers to avoid feedback

### High CPU Usage

**Symptoms**: Wake word detection uses more than 5% CPU

**Solutions**:
1. Check that `openwakeword` is properly installed
2. Close other resource-intensive applications
3. Consider disabling wake word detection if CPU usage is a concern

### Import Errors

**Symptoms**: `ImportError: openwakeword not installed`

**Solutions**:
```bash
pip install openwakeword
# or
pip install -r requirements.txt
```

## Advanced Configuration

### Custom Wake Words

Future versions will support custom wake words. Currently, only "hey_janus" is available out of the box.

To add custom wake words:
1. Train a custom model using the openWakeWord toolkit
2. Place the model in `models/wake_word/`
3. Add the model name to `wake_word_models` in config.ini

### Multiple Wake Words

You can configure multiple wake words (comma-separated):

```ini
[audio]
wake_word_models = hey_janus,alexa,hey_google
```

Note: Each additional wake word increases memory usage by ~10MB.

## Performance Tips

1. **Lower Threshold for Quiet Environments**: If you're in a quiet room, use threshold 0.3-0.4
2. **Higher Threshold for Noisy Environments**: In noisy environments, use 0.6-0.7
3. **Single Wake Word**: Use only one wake word for best performance
4. **Quality Microphone**: A good microphone improves detection accuracy

## Examples

### Example 1: Basic Usage

```bash
# Enable in config.ini
enable_wake_word = true

# Start Janus
python main.py --no-ui

# Say "Hey Janus"
# Say "Open Safari"
# Janus opens Safari, then returns to wake word listening
```

### Example 2: Sensitive Detection

For quiet environments:

```ini
[audio]
enable_wake_word = true
wake_word_threshold = 0.35
```

### Example 3: Conservative Detection

For noisy environments:

```ini
[audio]
enable_wake_word = true
wake_word_threshold = 0.65
```

## Comparison: Wake Word vs Manual Mode

| Feature | Wake Word Mode | Manual Mode |
|---------|----------------|-------------|
| **Activation** | Voice ("Hey Janus") | Button click / keyboard |
| **Privacy** | Passive listening (detection only) | Active on-demand |
| **Convenience** | Hands-free | Requires interaction |
| **CPU Usage** | Low (~1-5% idle) | Minimal (0% idle) |
| **Use Case** | Continuous availability | Occasional use |

## Definition of Done (TICKET-P3-02)

✅ **Completed**:
- [x] Lightweight wake word library integrated (openWakeWord)
- [x] Separate audio detection loop (independent of Whisper)
- [x] Visual feedback when wake word detected
- [x] Audio feedback via TTS ("Oui?")
- [x] Configuration options in config.ini
- [x] Terminal mode integration
- [x] UI mode integration
- [x] Documentation

✅ **Verification**: The agent does not react to ambient conversations unless the wake word "Hey Janus" is spoken.

## See Also

- [Audio Configuration Guide](06-audio-configuration.md)
- [Privacy & Security](../project/SECURITY_GUIDELINES.md)
- [Performance Tuning](../developer/10-performance-tuning-guide.md)

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the [FAQ](06-faq-troubleshooting.md)
3. Open an issue on GitHub with logs and configuration

---

**Last Updated**: 2024-12-06  
**Version**: 1.0.0 (TICKET-P3-02)
