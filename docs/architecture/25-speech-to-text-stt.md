# 25. Speech-to-Text (STT) Architecture

## Overview

Janus implements a sophisticated Speech-to-Text system that converts voice input into text commands. The STT architecture is modular, supports multiple engines, and includes advanced features like semantic correction, voice adaptation, and wake word detection.

## Core Architecture

### Components Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                    STTService                           │
│              (Lazy-loaded service layer)                │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   STT Factory     │
         │ (Auto-selection)  │
         └─────────┬─────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
  ┌─────▼─────┐      ┌───────▼────────┐
  │ MLX STT   │      │ Realtime STT   │
  │ (Apple M) │      │ (faster-whisper│
  └───────────┘      │  / whisper)    │
                     └────────────────┘
```

### STT Engine Selection

The system automatically selects the best STT engine based on hardware:

1. **MLX Whisper** (Apple Silicon M1/M2/M3/M4)
   - Ultra-fast inference (< 500ms for 5s audio)
   - Uses Apple's MLX framework
   - Optimal for macOS on Apple Silicon

2. **faster-whisper** (CUDA/CPU)
   - 4x faster than standard Whisper
   - Uses CTranslate2 for acceleration
   - Optimal for systems with CUDA GPU

3. **Standard Whisper** (Fallback)
   - OpenAI's original implementation
   - Works on all platforms
   - Baseline implementation

**Factory Function:** `janus.stt.stt_factory.create_stt_engine()`

## Core Modules

### 1. STTService (`janus/services/stt_service.py`)

**Purpose:** Service layer that manages STT lifecycle and configuration

**Features:**
- Lazy initialization of STT engine
- Configuration from unified settings
- Integration with LLM for semantic correction
- Voice input transcription

**Key Methods:**
```python
@property
def stt() -> WhisperSTT:
    """Lazy-load and return STT engine"""

def transcribe(audio_path: str) -> str:
    """Transcribe audio file to text"""
```

### 2. WhisperSTT (`janus/stt/whisper_stt.py`)

**Purpose:** Main STT engine with advanced features

**Capabilities:**
- Multiple engine backends (MLX, faster-whisper, standard)
- Context buffer for improved accuracy
- Semantic correction using LLM
- Custom correction dictionary
- Text normalization
- Audio logging for debugging

**Configuration:**
```python
WhisperSTT(
    enable_context_buffer=True,      # Remember previous transcriptions
    enable_semantic_correction=True,  # Use LLM for corrections
    enable_corrections=True,          # Apply correction dictionary
    enable_normalization=True,        # Normalize output text
    llm_service=unified_llm_client,  # Optional LLM for semantic correction
    language="fr",                    # Target language
)
```

### 3. STT Factory (`janus/stt/stt_factory.py`)

**Purpose:** Automatic engine selection and creation

**API:**
```python
# Get best available engine type
engine_type = get_best_stt_engine_type()  # "mlx", "faster-whisper", "whisper"

# Create optimal engine automatically
engine = create_stt_engine(
    model_size="base",
    language="fr",
    use_mlx=None,  # Auto-detect
)

# Get engine information
info = get_stt_engine_info()
```

### 4. MLXSTTEngine (`janus/stt/mlx_stt_engine.py`)

**Purpose:** Apple Silicon optimized STT using MLX framework

**Features:**
- Lightning-fast inference (< 500ms)
- Batch processing support
- Quantization for memory efficiency
- Apple Neural Engine utilization

**Usage:**
```python
from janus.stt import MLXSTTEngine, is_mlx_available

if is_mlx_available():
    engine = MLXSTTEngine(
        model_size="base",
        language="fr",
        batch_size=12,
        quant="int8",  # Optional quantization
    )
```

### 5. RealtimeSTTEngine (`janus/stt/realtime_stt_engine.py`)

**Purpose:** Real-time STT with faster-whisper or standard Whisper

**Features:**
- Streaming audio support
- Partial transcriptions
- GPU acceleration (CUDA)
- Voice Activity Detection (VAD)

**Configuration:**
```python
engine = RealtimeSTTEngine(
    model_size="base",
    device="cuda",  # or "cpu", "mps"
    compute_type="float16",
    language="fr",
    use_faster_whisper=True,
)
```

## Advanced Features

### Context Buffer (`janus/stt/context_buffer.py`)

**Purpose:** Maintain conversation context for improved accuracy

- Stores recent transcriptions
- Provides context to Whisper for better recognition
- Configurable window size
- Automatic cleanup of old entries

### Semantic Correction (`janus/stt/semantic_corrector.py`)

**Purpose:** Use LLM to fix transcription errors

**Modes:**
1. **LLM-based:** Uses unified LLM client for intelligent corrections
2. **Local model:** Uses dedicated local model for offline correction
3. **Rule-based fallback:** Simple corrections when LLM unavailable

**Example:**
```
Raw transcription: "ouvre le fichier Excel sur le bureau"
Semantic correction: "ouvre le fichier Excel sur le bureau"
(Corrects case, punctuation, technical terms)
```

### Correction Dictionary (`janus/stt/correction_dictionary.py`)

**Purpose:** Domain-specific term corrections

- Predefined corrections for common terms
- Technical vocabulary (Excel, PowerPoint, etc.)
- User-configurable
- Applied post-transcription

### Text Normalization (`janus/stt/text_normalizer.py`)

**Purpose:** Clean and standardize transcription output

- Remove filler words ("euh", "um")
- Normalize punctuation
- Fix capitalization
- Language-specific rules

### Neural VAD (`janus/stt/neural_vad.py`)

**Purpose:** Voice Activity Detection using neural networks

- Detects speech vs. silence
- Reduces processing of non-speech audio
- Improves efficiency and accuracy
- Silero VAD integration

### Wake Word Detection (`janus/stt/wake_word_detector.py`)

**Purpose:** Trigger Janus with voice command

- Detects "Hey Janus" or custom wake words
- Low-latency detection
- Configurable sensitivity
- Integration with voice input pipeline

### Voice Adaptation (`janus/stt/voice_adaptation_cache.py`)

**Purpose:** Adapt to individual user's voice

- Caches voice characteristics
- Improves accuracy over time
- Per-user profiles
- Automatic adaptation

### Speaker Verification (`janus/stt/speaker_verifier.py`)

**Purpose:** Verify speaker identity

- Voice fingerprinting
- Multi-user support
- Security features
- Optional authentication

### Calibration (`janus/stt/calibration_manager.py`)

**Purpose:** Audio input calibration

- Microphone sensitivity adjustment
- Noise floor detection
- Optimal threshold calculation
- Per-device profiles

## Data Flow

### Voice Input Pipeline

```
Microphone Input
    ↓
[Wake Word Detection] (Optional)
    ↓
[Audio Capture]
    ↓
[Neural VAD] (Voice Activity Detection)
    ↓
[Audio Preprocessing]
    ↓
[STT Engine] (MLX/faster-whisper/whisper)
    ↓
[Text Normalization]
    ↓
[Correction Dictionary]
    ↓
[Semantic Correction] (Optional, uses LLM)
    ↓
[Context Buffer Update]
    ↓
Final Transcription → JanusAgent
```

## Configuration

### Settings Structure

```python
# In unified settings (janus/core/settings.py)
class WhisperSettings:
    enable_context_buffer: bool = True
    enable_semantic_correction: bool = True
    semantic_correction_model_path: str = ""  # Empty = use main LLM
    enable_corrections: bool = True
    models_dir: str = "models/whisper"
```

### Environment Variables

```bash
# Enable voice input
JANUS_VOICE_ENABLED=true

# STT Engine selection
JANUS_STT_ENGINE=auto  # auto, mlx, faster-whisper, whisper

# Whisper model size
JANUS_WHISPER_MODEL=base  # tiny, base, small, medium, large

# Language
JANUS_LANGUAGE=fr

# Advanced features
JANUS_STT_SEMANTIC_CORRECTION=true
JANUS_STT_CONTEXT_BUFFER=true
```

## Performance Characteristics

### Inference Speed (5s audio)

| Engine           | Platform          | Latency    |
|------------------|-------------------|------------|
| MLX Whisper      | M1/M2/M3/M4      | < 500ms    |
| faster-whisper   | CUDA GPU          | ~1-2s      |
| faster-whisper   | CPU (8 cores)     | ~3-5s      |
| Standard Whisper | CPU (8 cores)     | ~10-15s    |

### Memory Usage

| Model Size | RAM Required | VRAM (GPU) |
|------------|--------------|------------|
| tiny       | ~500MB       | ~1GB       |
| base       | ~800MB       | ~1.5GB     |
| small      | ~1.5GB       | ~2GB       |
| medium     | ~3GB         | ~5GB       |
| large      | ~6GB         | ~10GB      |

## Integration Points

### 1. JanusPipeline

STTService is initialized in the pipeline:

```python
# janus/core/janus_pipeline.py
self.stt_service = STTService(
    settings=self.settings,
    enabled=self.settings.features.voice_enabled,
    unified_llm_client=self.unified_llm_client,
)
```

### 2. Voice Input Flow

```python
# User speaks
audio_data = capture_microphone()

# Transcribe
if self.stt_service.enabled:
    text = await self.stt_service.stt.transcribe_async(audio_data)
    
    # Process as normal command
    result = await self.process_command_async(text)
```

### 3. Configuration UI

Voice settings are exposed in the UI:
- Enable/disable voice input
- Select STT engine
- Configure semantic correction
- Adjust audio thresholds

## Error Handling

### Graceful Degradation

1. **No STT available:** Falls back to text-only input
2. **Semantic correction fails:** Uses raw transcription
3. **Context buffer error:** Continues without context
4. **VAD unavailable:** Processes all audio

### Logging and Debugging

- **Audio Logger:** Saves audio files for debugging
- **Transcription logs:** Records all transcriptions
- **Performance metrics:** Tracks latency and accuracy
- **Error reporting:** Detailed error messages

## Dependencies

### Required
- `openai-whisper` or `faster-whisper` (STT engine)

### Optional
- `lightning-whisper-mlx` (Apple Silicon acceleration)
- `transformers` (Semantic correction)
- `silero-vad` (Neural VAD)
- `pyaudio` (Microphone input)
- `pydub` (Audio processing)

## See Also

- [26. Text-to-Speech (TTS)](./26-text-to-speech-tts.md)
- [01. Complete System Architecture](./01-complete-system-architecture.md)
- [17. Memory Engine](./17-memory-engine.md)
- [User Guide: Wake Word Training](../user/08-wake-word-training.md)
- [User Guide: Voice Fingerprinting](../user/09-voice-fingerprinting.md)
