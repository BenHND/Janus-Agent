# Developer Quick Start

Quick guide to understanding and contributing to Janus.

## Overview

Janus is a voice-controlled computer automation system that uses AI to understand commands and control your computer. It's built in Python with a focus on local processing and privacy.

## Architecture in 5 Minutes

### The OODA Loop

Janus uses a dynamic execution loop:

1. **Observe** - Take screenshot, detect UI elements
2. **Orient** - Analyze context (what app is active, what's on screen)
3. **Decide** - LLM chooses next action
4. **Act** - Execute action via agent
5. **Loop** - Repeat until goal achieved

### Key Components

```
JanusAgent (Entry Point)
    ↓
ActionCoordinator (OODA Loop)
    ↓
ReasonerLLM (AI Decision Making)
    ↓
AgentRegistry (Execute Actions)
    ├── SystemAgent (Launch apps)
    ├── BrowserAgent (Web navigation)
    ├── UIAgent (Click, type, scroll)
    └── FilesAgent (File operations)
```

### Data Flow

```
Voice → Whisper STT → Text → ReasonerLLM → Action Plan → Agent → OS
```

## Quick Start

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/BenHND/Janus.git
cd Janus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Optional: Install AI features
pip install -r requirements-llm.txt  # For LLM reasoning
pip install -r requirements-vision.txt  # For vision capabilities

# Run tests
pytest tests/
```

### Your First Command

```python
from janus.core import JanusAgent
import asyncio

async def main():
    # Create agent
    agent = JanusAgent()
    
    # Execute command
    result = await agent.execute("open Calculator")
    
    # Check result
    if result.success:
        print(f"Success: {result.message}")
    else:
        print(f"Failed: {result.message}")

# Run
asyncio.run(main())
```

## Project Structure

```
Janus/
├── janus/                  # Main package
│   ├── core/               # Core components
│   │   ├── janus_agent.py  # Main entry point
│   │   ├── action_coordinator.py  # OODA loop
│   │   ├── pipeline.py     # Execution pipeline
│   │   └── memory_engine.py  # Memory/session management
│   │
│   ├── reasoning/          # AI decision making
│   │   └── reasoner_llm.py  # LLM-based reasoning
│   │
│   ├── agents/             # Domain-specific agents
│   │   ├── system_agent.py
│   │   ├── browser_agent.py
│   │   ├── files_agent.py
│   │   └── ui_agent.py
│   │
│   ├── vision/             # Computer vision
│   │   └── set_of_marks.py  # Element detection
│   │
│   ├── stt/                # Speech recognition
│   ├── automation/         # OS automation
│   └── ui/                 # Configuration UI
│
├── tests/                  # Test suite
├── docs/                   # Documentation
└── examples/               # Usage examples
```

## Key Concepts

### 1. LLM-First Philosophy

**Don't write this:**
```python
# ❌ Pattern matching - brittle
if "open" in command and "chrome" in command:
    open_app("Chrome")
```

**Do this:**
```python
# ✅ Let the LLM understand
action = await reasoner.decide_next_action(
    user_goal=command,
    context=current_context
)
```

The LLM handles all the variations: "open Chrome", "launch Chrome", "start Chrome", "ouvre Chrome" (French), etc.

### 2. Atomic Agent Operations

Agents provide simple, atomic operations:

```python
class SystemAgent:
    def open_app(self, name: str) -> ActionResult:
        """Launch an application."""
        # Simple, atomic operation
        # No complex logic - that's in the Reasoner
```

### 3. Visual Grounding

Instead of CSS selectors or coordinates, use Set-of-Marks:

```python
# Elements are detected and tagged with IDs
elements = [
    {"id": "btn_42", "type": "button", "text": "Submit"},
    {"id": "input_17", "type": "input", "label": "Email"}
]

# LLM references by ID
action = {"action": "click", "args": {"element_id": "btn_42"}}
```

## Making Changes

### Adding a New Agent

1. Create agent file in `janus/agents/`
2. Inherit from `BaseAgent`
3. Implement required methods
4. Register in `agent_registry.py`

```python
# janus/agents/my_agent.py
from janus.core.contracts import ActionResult, BaseAgent

class MyAgent(BaseAgent):
    """Agent for X domain."""
    
    def my_action(self, param: str) -> ActionResult:
        """Perform my action."""
        try:
            # Do something
            return ActionResult(success=True, message="Done")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
```

### Adding a New Action

1. Add action to agent
2. Update action schema if needed
3. Add tests
4. Document in API reference

### Modifying the OODA Loop

The OODA loop is in `ActionCoordinator`. Be very careful modifying it:
- Keep it simple and generic
- Don't add site-specific logic
- Test thoroughly

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_janus_agent.py

# Run with coverage
pytest --cov=janus tests/

# Run specific test pattern
pytest -k "test_open_app"
```

## Code Style

- Use type hints everywhere
- Write docstrings for public APIs
- Follow PEP 8
- Run pre-commit hooks: `pre-commit install`

## Common Tasks

### Debug a Command

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run command
agent = JanusAgent()
result = await agent.execute("your command")
```

### Test Vision Detection

```python
from janus.vision import SetOfMarksEngine

vision = SetOfMarksEngine()
elements = await vision.detect_elements()

for elem in elements:
    print(f"{elem['id']}: {elem['type']} - {elem.get('text', '')}")
```

### Mock LLM for Testing

```python
from janus.reasoning import ReasonerLLM

# Use mock backend
reasoner = ReasonerLLM(backend="mock")
```

## Resources

### Documentation
- [Architecture Overview](../architecture/README.md)
- [OODA Loop Details](../architecture/13-dynamic-react-loop.md)
- [Agent System](../architecture/04-agent-architecture.md)
- [API Reference](../architecture/15-janus-agent-api.md)

### Examples
- See `examples/` directory for practical examples
- Check `tests/` for usage patterns

### Getting Help
- Read the docs first
- Check existing issues on GitHub
- Ask in discussions if you're stuck

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit pull request

See [CONTRIBUTING.md](../project/CONTRIBUTING.md) for detailed guidelines.

## Performance Tips

### Lazy Loading
Components load on first use. Don't initialize what you don't need:

```python
# Good - loads only when needed
agent = JanusAgent(enable_vision=False)

# Vision won't load unless explicitly needed
```

### Caching
Vision uses smart caching. Don't disable it unless testing:

```python
vision = SetOfMarksEngine(
    cache_ttl=2.0,  # Cache for 2 seconds
    enable_cache=True  # Default
)
```

### LLM Backends
Use local LLMs for development to avoid API costs:

```python
# Use Ollama locally
reasoner = ReasonerLLM(backend="ollama")
```

## Debugging Common Issues

### "Agent not found"
- Check agent is registered in `agent_registry.py`
- Verify agent module is imported

### "LLM connection failed"
- Check API keys in config
- Try mock backend: `backend="mock"`
- Verify network connectivity

### "Vision detection failed"
- Check screen permissions (macOS)
- Verify application is visible
- Check cache isn't stale

### "Action execution timeout"
- Increase timeout in agent
- Check if application is responding
- Look for modal dialogs blocking execution

## Next Steps

1. Read the [Architecture Documentation](../architecture/README.md)
2. Try the [Examples](../../examples/)
3. Check the [Agent Architecture Guide](../architecture/04-agent-architecture.md)
4. Review [Contribution Guidelines](../project/CONTRIBUTING.md)

## Quick Reference

### Import Paths
```python
from janus.core import JanusAgent
from janus.core.action_coordinator import ActionCoordinator
from janus.reasoning import ReasonerLLM
from janus.vision import SetOfMarksEngine
from janus.agents import SystemAgent, BrowserAgent
```

### Key Files
- `janus/core/janus_agent.py` - Main entry point
- `janus/core/action_coordinator.py` - OODA loop
- `janus/reasoning/reasoner_llm.py` - AI decisions
- `janus/core/agent_registry.py` - Agent routing

### Configuration
- `config.ini` - Main configuration file
- Settings loaded via `Settings` class
- Override with environment variables

Happy coding! 🚀
