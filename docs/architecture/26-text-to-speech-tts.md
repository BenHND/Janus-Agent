# 26. Text-to-Speech (TTS) Architecture

## Overview

Janus implements a Text-to-Speech (TTS) system that provides voice feedback to users. The TTS architecture is designed to be offline-first, cross-platform, and high-quality, using Piper Neural TTS for natural-sounding voices.

## Core Architecture

### Components Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                    TTSService                           │
│              (Lazy-loaded service layer)                │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │  TTSAdapter       │
         │  (Interface)      │
         └─────────┬─────────┘
                   │
         ┌─────────▼──────────┐
         │ PiperNeuralTTS     │
         │ (Implementation)   │
         └────────────────────┘
```

### Design Principles

1. **Offline-First:** No internet required after model download
2. **Cross-Platform:** Works on Windows, macOS, and Linux
3. **Asynchronous:** Non-blocking operations for smooth UX
4. **Queue-Based:** Handles multiple speech requests efficiently
5. **Lightweight:** Fast inference with ONNX Runtime

## Core Modules

### 1. TTSService (`janus/services/tts_service.py`)

**Purpose:** Service layer that manages TTS lifecycle and configuration

**Features:**
- Lazy initialization of TTS adapter
- Configuration from unified settings
- Voice feedback operations
- Integration with pipeline

**Key Methods:**
```python
@property
def tts():
    """Lazy-load and return TTS adapter"""

def speak(text: str) -> bool:
    """Speak the given text"""

def stop():
    """Stop current TTS playback"""

def is_speaking() -> bool:
    """Check if TTS is currently speaking"""
```

**Usage in Pipeline:**
```python
# Initialize in JanusPipeline
self.tts_service = TTSService(
    settings=self.settings,
    enabled=self.settings.features.tts_enabled,
)

# Use for voice feedback
if self.tts_service.enabled:
    await self.tts_service.speak("Command executed successfully")
```

### 2. TTSAdapter (`janus/tts/adapter.py`)

**Purpose:** Abstract interface for TTS implementations

**Interface:**
```python
class TTSAdapter(ABC):
    @abstractmethod
    def speak(self, text: str, lang: Optional[str] = None) -> None:
        """Speak the given text"""
    
    @abstractmethod
    def stop(self) -> None:
        """Stop current speech"""
    
    @abstractmethod
    def set_rate(self, rate: int) -> None:
        """Set speech rate"""
    
    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set speech volume"""
    
    @abstractmethod
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
```

**Design:** Allows swapping TTS implementations without changing service layer

### 3. PiperNeuralTTSAdapter (`janus/tts/piper_neural_tts.py`)

**Purpose:** High-quality neural TTS using Piper

**Features:**
- **Neural Voice Models:** Natural-sounding speech
- **100% Offline:** No internet after model download
- **Cross-Platform:** Windows, macOS, Linux
- **Fast Inference:** ONNX Runtime optimization
- **Multiple Languages:** Support for French, English, etc.
- **Lightweight:** Faster than Coqui TTS
- **Queue System:** Non-blocking async operations

**Architecture:**

```
User Request → TTSService → PiperNeuralTTSAdapter
                                    ↓
                            [Message Queue]
                                    ↓
                            [Worker Thread]
                                    ↓
                            [Piper Engine]
                                    ↓
                            [Audio Playback]
```

**Configuration:**
```python
adapter = PiperNeuralTTSAdapter(
    model_path="/path/to/piper/model.onnx",
    voice="fr_FR-upmc-medium",
    rate=200,           # Words per minute (150-250)
    volume=0.8,         # 0.0 to 1.0
    lang="fr-FR",       # Default language
    enable_queue=True,  # Use message queue
)
```

**Key Features:**

#### Async Operations (TICKET-04)

All blocking operations are wrapped with `asyncio.to_thread()`:

```python
async def speak(self, text: str, lang: Optional[str] = None) -> None:
    """Non-blocking speak operation"""
    # Queue message asynchronously
    await asyncio.to_thread(self._queue_message, text, lang)
```

#### Message Queue System

```python
@dataclass(order=True)
class TTSMessage:
    priority: int        # Lower = higher priority
    timestamp: float     # For FIFO ordering
    text: str           # Text to speak
    lang: str           # Language code
```

**Queue Behavior:**
- Priority-based (e.g., errors = priority 0, info = priority 10)
- FIFO within same priority
- Worker thread processes queue continuously
- Thread-safe with locks

#### Volume Control

```python
def set_volume(self, volume: float) -> None:
    """Set volume (0.0 to 1.0)"""
    
def mute(self) -> None:
    """Mute TTS (remember previous volume)"""
    
def unmute(self) -> None:
    """Restore previous volume"""
```

#### Model Auto-Detection

```python
def _find_model_path(self) -> Optional[str]:
    """Auto-detect Piper model in standard locations"""
    # Checks:
    # 1. PIPER_MODEL_PATH environment variable
    # 2. ~/.local/share/piper/
    # 3. models/piper/
    # 4. /usr/share/piper/
```

### 4. Orchestrator Integration (`janus/tts/orchestrator_integration.py`)

**Purpose:** Integration with UI orchestrator for user feedback

**Features:**
- User notifications via TTS
- Error announcements
- Command confirmations
- Status updates

**Example:**
```python
# In UI orchestrator
def announce_error(self, error_message: str):
    """Announce error via TTS"""
    if self.tts_service.enabled:
        self.tts_service.speak(f"Erreur: {error_message}")
```

## Data Flow

### Speech Request Pipeline

```
Application/Pipeline
    ↓
[TTSService.speak(text)]
    ↓
[PiperNeuralTTSAdapter.speak(text)]
    ↓
[Message Queue] (Priority Queue)
    ↓
[Worker Thread]
    ↓
[Piper Engine Inference]
    ↓
[Generate WAV Audio]
    ↓
[Audio Playback] (PyAudio/Platform)
    ↓
User Hears Speech
```

### Queue Processing

```python
# Worker thread loop (simplified)
while not self._stop_event.is_set():
    try:
        # Get next message from queue
        message = self._queue.get(timeout=QUEUE_POLL_TIMEOUT)
        
        # Generate audio with Piper
        with self._engine_lock:
            wav_bytes = self._piper_voice.synthesize(message.text)
        
        # Play audio
        self._play_audio(wav_bytes)
        
    except queue.Empty:
        continue
```

## Voice Models

### Piper Neural TTS Models

**French Voices:**
- `fr_FR-upmc-medium` - High quality, natural
- `fr_FR-siwis-medium` - Alternative French voice
- `fr_FR-tom-medium` - Male French voice

**English Voices:**
- `en_US-lessac-medium` - High quality US English
- `en_GB-alan-medium` - British English
- `en_US-amy-medium` - Female US English

**Model Structure:**
```
model_name.onnx        # Neural network model
model_name.onnx.json   # Model configuration
```

**Download:**
```bash
# Models are downloaded automatically on first use
# Or manually:
piper --download-dir ~/.local/share/piper/ --model fr_FR-upmc-medium
```

## Configuration

### Settings Structure

```python
# In unified settings (janus/core/settings.py)
class TTSSettings:
    enabled: bool = True
    voice: str = "fr_FR-upmc-medium"
    rate: int = 200         # Words per minute
    volume: float = 0.8     # 0.0 to 1.0
    lang: str = "fr-FR"
    enable_queue: bool = True
```

### Environment Variables

```bash
# Enable TTS
JANUS_TTS_ENABLED=true

# Voice selection
JANUS_TTS_VOICE=fr_FR-upmc-medium

# Speech rate (150-250 WPM)
JANUS_TTS_RATE=200

# Volume (0.0-1.0)
JANUS_TTS_VOLUME=0.8

# Language
JANUS_TTS_LANG=fr-FR

# Model path (optional)
PIPER_MODEL_PATH=/path/to/models
```

## Performance Characteristics

### Inference Speed

| Text Length | Inference Time | Real-time Factor |
|-------------|----------------|------------------|
| 10 words    | ~100ms         | 10x faster       |
| 50 words    | ~300ms         | 5x faster        |
| 100 words   | ~600ms         | 3x faster        |

**Real-time Factor:** How many times faster than real-time playback
- Lower is better
- Piper achieves 3-10x faster than real-time on modern CPUs

### Memory Usage

- **Base:** ~50MB (ONNX Runtime + model)
- **Per voice model:** ~20-50MB
- **Audio buffer:** ~1-5MB
- **Total:** ~100-150MB typical

### Latency

- **Queue latency:** < 10ms
- **Inference:** 100-600ms (depends on text length)
- **Audio playback start:** < 50ms
- **Total (first word):** ~150-700ms

## Integration Points

### 1. Pipeline Integration

```python
# In JanusPipeline.__init__()
self.tts_service = TTSService(
    settings=self.settings,
    enabled=self.settings.features.tts_enabled,
)

# In command execution
async def execute_command(self, command: str):
    result = await self._execute(command)
    
    # Provide voice feedback
    if result.success:
        await self.tts_service.speak("Commande exécutée avec succès")
    else:
        await self.tts_service.speak(f"Erreur: {result.error}")
```

### 2. UI Integration

```python
# In UI orchestrator
class JanusOrchestrator:
    def __init__(self):
        self.tts_service = TTSService(settings, enabled=True)
    
    def on_command_complete(self, result):
        # Visual feedback
        self.update_ui(result)
        
        # Voice feedback
        self.tts_service.speak(result.message)
```

### 3. Error Handling

```python
try:
    result = await pipeline.process_command(user_input)
except Exception as e:
    logger.error(f"Command failed: {e}")
    
    # Notify user via TTS
    await tts_service.speak(f"Désolé, une erreur s'est produite: {str(e)}")
```

## Advanced Features

### Priority Messaging

```python
# High priority (interrupt current speech)
adapter.speak("ERREUR CRITIQUE", priority=0)

# Normal priority
adapter.speak("Commande terminée", priority=10)

# Low priority (wait for others)
adapter.speak("Information", priority=20)
```

### Language Switching

```python
# Speak in different languages
adapter.speak("Bonjour", lang="fr-FR")
adapter.speak("Hello", lang="en-US")
adapter.speak("Hola", lang="es-ES")
```

### Queue Management

```python
# Check if speaking
if adapter.is_speaking():
    # Wait or interrupt
    adapter.stop()

# Clear queue
adapter.stop()  # Stops current + clears queue
```

## Error Handling

### Graceful Degradation

1. **Piper not available:** TTS disabled, no voice feedback
2. **Model not found:** Falls back to system TTS (if available)
3. **Audio device error:** Logs error, continues without voice
4. **Queue overflow:** Drops low-priority messages

### Logging

```python
# TTS operations are logged
logger.info("TTS adapter loaded successfully")
logger.debug("Speaking: 'Hello world'")
logger.warning("Failed to speak: Audio device not available")
```

## Dependencies

### Required
- `piper-tts` - Neural TTS engine
- `onnxruntime` - Model inference (auto-installed with piper)

### Optional
- `pyaudio` - Audio playback (alternative)
- `sounddevice` - Cross-platform audio (alternative)
- `pydub` - Audio processing

### Installation

```bash
# Install Piper TTS
pip install piper-tts

# Or with UV (modern)
uv pip install piper-tts
```

## Comparison: Piper vs. Alternatives

| Feature            | Piper TTS | Coqui TTS | System TTS | gTTS       |
|--------------------|-----------|-----------|------------|------------|
| **Quality**        | High      | Very High | Medium     | Medium     |
| **Speed**          | Fast      | Slow      | Fast       | N/A        |
| **Offline**        | ✅        | ✅        | ✅         | ❌         |
| **Cross-platform** | ✅        | ✅        | ⚠️         | ✅         |
| **Memory**         | Low       | High      | Low        | N/A        |
| **Languages**      | Many      | Many      | Limited    | Many       |
| **Setup**          | Easy      | Complex   | None       | Easy       |

**Why Piper:**
- Best balance of quality, speed, and ease of use
- Fully offline after model download
- Lightweight and fast
- Cross-platform consistency

## Future Enhancements

### Planned Features

1. **Emotional Speech:** Vary tone based on message type
2. **SSML Support:** Fine-grained control over prosody
3. **Voice Cloning:** Custom user voices
4. **Streaming TTS:** Real-time synthesis for long texts
5. **Multiple Voices:** Character-based voices for different agents

### Potential Improvements

- **Adaptive Rate:** Adjust speed based on message urgency
- **Context-Aware Prosody:** Natural emphasis and pauses
- **Background Music:** Subtle audio cues
- **Spatial Audio:** 3D audio for multi-agent scenarios

## See Also

- [25. Speech-to-Text (STT)](./25-speech-to-text-stt.md)
- [01. Complete System Architecture](./01-complete-system-architecture.md)
- [User Guide: Getting Started](../user/03-getting-started.md)
- [Developer: Core Modules](../developer/03-core-modules.md)
