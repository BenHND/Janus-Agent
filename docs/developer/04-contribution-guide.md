# Contribution Guide - Extending Janus

Guide for contributing new features and modules to Janus.

## 📋 Table of Contents

1. [Creating New Modules](#creating-new-modules)
2. [Adding System Actions](#adding-system-actions)
3. [Code Conventions](#code-conventions)

## Creating New Modules

### Module Structure

Example: Adding a Spotify module

```python
# janus/agents/spotify_agent.py
from .base_agent import BaseAgent
from typing import Dict, List, Any

class SpotifyAgent(BaseAgent):
    """Agent for Spotify automation"""
    
    def __init__(self, settings):
        self.settings = settings
        self.api_client = None  # Lazy load
    
    def get_available_actions(self) -> List[str]:
        return [
            "play",
            "pause",
            "next",
            "previous",
            "search",
            "add_to_playlist"
        ]
    
    def validate_action(self, action: str, params: Dict) -> bool:
        """Validate action before execution"""
        if action not in self.get_available_actions():
            return False
        
        # Validate required parameters
        if action == "play":
            return "track" in params or "playlist" in params
        
        return True
    
    def execute(self, action: str, params: Dict) -> Dict[str, Any]:
        """Execute Spotify action"""
        try:
            if action == "play":
                return self._play(params)
            elif action == "pause":
                return self._pause()
            # ... other actions
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _play(self, params: Dict) -> Dict:
        """Play track or playlist"""
        # Implementation
        return {"status": "success", "data": {"now_playing": "..."}}
```

### Register the Agent

```python
# janus/core/agent_setup.py
from janus.agents.spotify_agent import SpotifyAgent

def setup_agent_registry():
    """Setup agent registry with all available agents"""
    registry = AgentRegistry()
    
    # ... existing agents ...
    registry.register_agent("spotify", SpotifyAgent())
    
    return registry
```

### Update LLM Prompt

```jinja2
{# prompts/reasoner_system.jinja2 #}
AVAILABLE AGENTS:
- system: open_application, close_application, ...
- spotify: play, pause, next, previous, search
```

## Adding System Actions

### Extend OSInterface

```python
# janus/os/macos_backend.py
class MacOSBackend:
    def take_screenshot(self, region=None) -> Image:
        """Take screenshot of screen or region"""
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        return screenshot
```

### Add to System Agent

```python
# janus/agents/system_agent.py
class SystemAgent(BaseAgent):
    def get_available_actions(self) -> List[str]:
        return [
            # ... existing actions ...
            "screenshot"  # NEW
        ]
    
    def execute(self, action: str, params: Dict) -> Dict:
        if action == "screenshot":
            return self._screenshot(params)
```

## Code Conventions

### Python Typing

**ALWAYS use type hints:**

```python
from typing import Dict, List, Optional, Any

def process_command(
    command: str,
    context: Optional[Dict[str, Any]] = None
) -> ExecutionResult:
    """Process user command with optional context"""
    pass
```

### Docstrings

**Use Google-style docstrings:**

```python
def transcribe_audio(
    audio: np.ndarray,
    language: str = "en"
) -> TranscriptionResult:
    """
    Transcribe audio to text using Whisper.
    
    Args:
        audio: Audio data as numpy array (16kHz, mono)
        language: Language code (ISO 639-1)
    
    Returns:
        TranscriptionResult with text and metadata
    
    Raises:
        ValueError: If audio format is invalid
    
    Example:
        >>> result = transcribe_audio(audio_data, language="fr")
        >>> print(result.text)
        "Bonjour le monde"
    """
    pass
```

### Structured Logging

**Use the Janus logger:**

```python
from janus.logging import get_logger

logger = get_logger(__name__)

def my_function():
    logger.info("Starting function")
    logger.debug("Processing data", extra={"data_size": len(data)})
    logger.warning("Something unusual happened")
    logger.error("Error occurred", exc_info=True)
```

### Error Handling

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    return {"status": "error", "error": str(e)}
except Exception as e:
    logger.exception("Unexpected error")
    return {"status": "error", "error": "Internal error"}
```

### Testing

**Write tests for new features:**

```python
# tests/unit/test_spotify_agent.py
import pytest
from janus.agents.spotify_agent import SpotifyAgent

def test_spotify_play():
    agent = SpotifyAgent(Settings())
    result = agent.execute("play", {"track": "test"})
    assert result["status"] == "success"

@pytest.mark.integration
def test_spotify_api_connection():
    agent = SpotifyAgent(Settings())
    # Test with real API...
```

---

**Next**: [Security & Sandbox](05-security-and-sandbox.md)
