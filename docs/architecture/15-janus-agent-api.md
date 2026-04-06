# JanusAgent - Single Entry Point API

> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---


**Unify to Single Entry Point**

This document describes the new unified API for Janus through the `JanusAgent` class.

## Overview

`JanusAgent` is the **ONLY** public API for Janus. All other classes (`JanusPipeline`, `ExecutionEngine`, `AgentExecutor`, etc.) are internal implementation details.

### Why JanusAgent?

- 5+ different entry points (Pipeline, ExecutionEngine, AgentExecutor, Reasoner, Orchestrators)
- Confusion about which to use when
- Duplicated initialization and error handling
- Difficult to test all paths

- Single entry point: `JanusAgent`
- Simple initialization
- Clear method signatures
- All features accessible through one interface

## Quick Start

### Basic Usage

```python
from janus.core import JanusAgent

# Initialize agent
agent = JanusAgent()

# Execute command
result = await agent.execute("open Calculator")

# Check result
if result.success:
    print(f"Success: {result.message}")
else:
    print(f"Failed: {result.message}")
```

### With Context Manager

```python
from janus.core import JanusAgent

async with JanusAgent() as agent:
    result = await agent.execute("open Safari and go to example.com")
    print(f"Success: {result.success}")
```

### One-Shot Execution

```python
from janus.core import execute_command

# Execute single command with automatic setup/cleanup
result = await execute_command("open Calculator")
```

## Initialization

### Default Configuration

```python
agent = JanusAgent()
```

Uses default configuration from `config.ini`.

### Custom Configuration File

```python
agent = JanusAgent(config_path="my_config.ini")
```

### Feature Flags

```python
agent = JanusAgent(
    enable_voice=False,      # Disable voice input (text only)
    enable_llm=True,         # Enable LLM reasoning
    enable_vision=True,      # Enable vision verification
    enable_learning=False,   # Disable learning
    enable_tts=False,        # Disable text-to-speech
)
```

### Language Selection

```python
agent = JanusAgent(language="en")  # English
agent = JanusAgent(language="fr")  # French (default)
```

### Session Management

```python
# Auto-generated session ID
agent = JanusAgent()
print(f"Session: {agent.session_id}")

# Custom session ID
agent = JanusAgent(session_id="my-session-123")
```

## Execution

### Simple Execution

```python
result = await agent.execute("open Calculator")
```

### With Request ID

```python
result = await agent.execute(
    "search for Python",
    request_id="req-123"
)
```

### With Extra Context

```python
result = await agent.execute(
    "send email",
    extra_context={
        "recipient": "user@example.com",
        "subject": "Test",
        "body": "Hello"
    }
)
```

## Result Handling

### ExecutionResult Structure

```python
result = await agent.execute("open Calculator")

# Check success
if result.success:
    print("✓ Command succeeded")
else:
    print("✗ Command failed")

# Get details
print(f"Message: {result.message}")
print(f"Duration: {result.total_duration_ms}ms")
print(f"Session: {result.session_id}")
print(f"Request: {result.request_id}")

# Get intent information
print(f"Action: {result.intent.action}")
print(f"Confidence: {result.intent.confidence}")

# Get execution steps (if available)
if result.steps:
    for step in result.steps:
        print(f"  Step: {step}")
```

### Error Handling

```python
try:
    result = await agent.execute("open Calculator")
    
    if not result.success:
        print(f"Command failed: {result.message}")
        
except ValueError as e:
    print(f"Invalid input: {e}")
    
except RuntimeError as e:
    print(f"Agent error: {e}")
```

## Multiple Commands

### Sequential Execution

```python
async with JanusAgent() as agent:
    commands = [
        "open TextEdit",
        "write 'Hello World'",
        "save as test.txt"
    ]
    
    for command in commands:
        result = await agent.execute(command)
        if not result.success:
            print(f"Failed at: {command}")
            break
```

### With Memory

Commands executed in the same session share memory

```python
async with JanusAgent() as agent:
    # First command
    result1 = await agent.execute("open Safari")
    
    # Second command can reference first
    result2 = await agent.execute("go to example.com")
    
    # Third command can reference state
    result3 = await agent.execute("take screenshot")
```

## Configuration Options

### Available Features

| Feature | Flag | Default | Description |
|---------|------|---------|-------------|
| Voice Input | `enable_voice` | `False` | Enable STT for voice commands |
| LLM Reasoning | `enable_llm` | `True` | Use LLM for complex command parsing |
| Vision | `enable_vision` | `True` | Enable visual verification |
| Learning | `enable_learning` | `True` | Learn from user corrections |
| TTS | `enable_tts` | `False` | Enable text-to-speech feedback |

### Configuration File Example

Create `config.ini`

```ini
[llm]
provider = ollama
model = qwen2.5:7b-instruct
temperature = 0.1

[features]
enable_llm_reasoning = true
enable_vision = true
enable_learning = false

[language]
default = en
```

Then use

```python
agent = JanusAgent(config_path="config.ini")
```

## Best Practices

### 1. Use Context Manager

```python
# ✓ Good - automatic cleanup
async with JanusAgent() as agent:
    result = await agent.execute("open Calculator")

# ✗ Avoid - manual cleanup needed
agent = JanusAgent()
result = await agent.execute("open Calculator")
await agent.cleanup()  # Don't forget!
```

### 2. Check Availability

```python
agent = JanusAgent()
if agent.available:
    result = await agent.execute("open Calculator")
else:
    print("Agent not available - check logs")
```

### 3. Handle Errors Gracefully

```python
async with JanusAgent() as agent:
    result = await agent.execute("open Calculator")
    
    if not result.success:
        # Log error and continue
        logger.error(f"Command failed: {result.message}")
    else:
        # Process success
        logger.info(f"Command succeeded: {result.message}")
```

### 4. Reuse Agent for Multiple Commands

```python
# ✓ Good - one agent, multiple commands
async with JanusAgent() as agent:
    for command in commands:
        await agent.execute(command)

# ✗ Avoid - creating agent for each command
for command in commands:
    async with JanusAgent() as agent:
        await agent.execute(command)
```

## Testing

### Mock Mode

For testing without actual execution

```python
agent = JanusAgent(
    enable_llm=True,      # Will use mock backend if LLM unavailable
    enable_vision=False,  # Faster tests
    enable_learning=False,
)

result = await agent.execute("open Calculator")
```

### Unit Tests

```python
import pytest
from janus.core import JanusAgent

@pytest.mark.asyncio
async def test_basic_execution():
    async with JanusAgent() as agent:
        result = await agent.execute("open Calculator")
        assert result.success
        assert result.message

@pytest.mark.asyncio
async def test_invalid_command():
    async with JanusAgent() as agent:
        with pytest.raises(ValueError):
            await agent.execute("")
```

## Migration Guide

### From JanusPipeline

```python
from janus.core.pipeline import JanusPipeline
from janus.core.settings import Settings
from janus.core import MemoryEngine

settings = Settings()
memory = MemoryEngine(settings.database)
pipeline = JanusPipeline(settings, memory)
result = await pipeline.process_command_async("open Calculator")
```

```python
from janus.core import JanusAgent

async with JanusAgent() as agent:
    result = await agent.execute("open Calculator")
```

### From ExecutionEngine

```python
from janus.core.execution_engine_v3 import ExecutionEngineV3

engine = ExecutionEngineV3()
result = await engine.execute_plan(plan)
```

```python
from janus.core import JanusAgent

async with JanusAgent() as agent:
    result = await agent.execute("open Calculator")
```

## Architecture

### Component Integration

```
JanusAgent (Public API)
    ↓
JanusPipeline (Internal)
    ↓
ActionCoordinator (OODA Loop)
    ↓
┌─────────────────────────────────────┐
│ Reasoner → Validator → AgentExecutor│
└─────────────────────────────────────┘
    ↓
Specialized Agents (Chrome, Finder, System, etc.)
```

### Internal Components

All these are internal - DO NOT use directly

- ❌ `JanusPipeline` - Internal implementation
- ❌ `ExecutionEngine` - Internal implementation
- ❌ `AgentExecutor` - Internal implementation
- ❌ `ActionCoordinator` - Internal coordination
- ✅ `JanusAgent` - **USE THIS**

## Advanced Usage

### Custom Settings Override

```python
agent = JanusAgent(
    config_path="config.ini",
    enable_vision=True,
    # Override specific settings
    llm_temperature=0.2,
    max_retries=3,
)
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

agent = JanusAgent()
result = await agent.execute("open Calculator")
# Detailed logs will be printed
```

### Session Continuity

```python
# Session 1
async with JanusAgent(session_id="session-1") as agent:
    await agent.execute("open Safari")
    await agent.execute("go to example.com")

# Session 2 (later) - can reference session 1 context
async with JanusAgent(session_id="session-2") as agent:
    # Memory can recall what happened in session 1
    await agent.execute("go back to the website from earlier")
```

## Examples

See `examples/example_janus_agent.py` for complete working examples

1. Basic usage with context manager
2. Custom configuration
3. Multiple commands in one session
4. Commands with additional context
5. One-shot execution
6. Error handling

## Troubleshooting

### Agent Not Available

```python
agent = JanusAgent()
if not agent.available:
    # Check logs for initialization errors
    # Common issues:
    # - LLM backend not installed
    # - Config file missing
    # - Database connection failed
```

### Command Fails

```python
result = await agent.execute("open Calculator")
if not result.success:
    print(f"Failure reason: {result.message}")
    # Check:
    # - Is the app name correct?
    # - Does the agent have permissions?
    # - Is the command clear?
```

### Performance Issues

```python
# Disable heavy features for speed
agent = JanusAgent(
    enable_vision=False,   # Faster without vision
    enable_learning=False, # Faster without learning
)
```

## FAQ

**Q: Can I still use JanusPipeline directly?**
A: No. JanusPipeline is now an internal implementation detail. Use JanusAgent instead.

**Q: What happened to ExecutionEngine?**
A: It's integrated into JanusPipeline, which is used internally by JanusAgent.

**Q: How do I migrate existing code?**
A: See the Migration Guide section above.

**Q: Should I use JanusPipeline or JanusAgent?**
A: JanusAgent is the recommended public API. JanusPipeline provides internal implementation details.

**Q: Can I customize the execution flow?**
A: Yes, through configuration flags and extra context. For advanced customization, you can subclass JanusAgent.


## See Also

- [Complete System Architecture](./01-complete-system-architecture.md) - Full system overview
- [Action Coordinator](./14-action-coordinator.md) - Internal orchestration
- [Agent Registry](./06-module-registry.md) - Action routing
