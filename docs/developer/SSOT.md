# Single Source of Truth (SSOT) - Janus Architecture

This document defines the canonical locations and responsibilities for key components in the Janus system after the repository restructuring.

## Package Structure

### janus/runtime/
**Core orchestration and pipeline execution**

- `runtime/core/pipeline.py` - Main pipeline orchestrator
- `runtime/core/action_coordinator.py` - Action execution coordination
- `runtime/core/agent_registry.py` - Agent registration and discovery
- `runtime/core/memory_engine.py` - Core memory management
- `runtime/api/pipeline_entry.py` - Public API entry points
- `runtime/api/context_api.py` - Context management API

**SSOT for:** Pipeline execution, action coordination, agent lifecycle, memory engine

### janus/capabilities/
**Agent implementations and tool specifications**

- `capabilities/agents/` - All agent implementations (browser, system, files, etc.)
- `capabilities/tools/` - CLI tools and utilities

**SSOT for:** Agent definitions, tool specifications, capability registries

### janus/ai/
**LLM clients, reasoning engines, and AI logic**

- `ai/llm/unified_client.py` - Unified LLM client interface
- `ai/llm/ollama_client.py` - Ollama provider
- `ai/reasoning/reasoner_llm.py` - Main reasoning engine
- `ai/reasoning/context_router.py` - Context routing logic
- `ai/reasoning/semantic_router.py` - Semantic routing
- `ai/reasoning/prompt_loader.py` - Prompt management

**SSOT for:** LLM clients, reasoning logic, prompt management, AI strategies

### janus/platform/
**OS automation, system integration, and platform-specific code**

- `platform/os/system_bridge.py` - System bridge abstraction
- `platform/os/macos_bridge.py` - macOS implementation
- `platform/os/linux_bridge.py` - Linux implementation
- `platform/os/windows_bridge.py` - Windows implementation
- `platform/clipboard/clipboard_manager.py` - Clipboard operations
- `platform/scripts/` - Platform utility scripts

**SSOT for:** OS automation, system integration, clipboard operations, platform bridges

### janus/io/
**Input/Output - Speech-to-Text and Text-to-Speech**

- `io/stt/whisper_stt.py` - Whisper STT engine
- `io/stt/mlx_stt_engine.py` - MLX-based STT
- `io/stt/wake_word_detector.py` - Wake word detection
- `io/tts/piper_neural_tts.py` - Piper TTS engine
- `io/tts/adapter.py` - TTS adapter layer

**SSOT for:** Speech recognition, text-to-speech, audio I/O, voice processing

### janus/safety/
**Validation, security, and safety mechanisms**

- `safety/validation/unified_action_validator.py` - Main action validator
- `safety/validation/strict_action_validator.py` - Strict validation mode

**SSOT for:** Action validation, security checks, safety mechanisms

### janus/vision/
**Computer vision and screen capture** (unchanged)

- Vision API and implementations remain in `janus/vision/`

**SSOT for:** Screen capture, OCR, visual element detection

### janus/memory/
**Memory systems and persistence** (unchanged)

- Memory systems remain in `janus/memory/`

**SSOT for:** Memory storage, retrieval, persistence

### janus/legacy/
**Deprecated modules maintained for compatibility**

- `legacy/parser/` - Legacy parsers (deprecated)

**Note:** Components in `janus/legacy/` are deprecated and should not be used for new development.

## Import Patterns

### Recommended Import Patterns

```python
# Runtime/Core
from janus.runtime.core import Pipeline, ActionCoordinator
from janus.runtime.api import pipeline_entry

# Capabilities
from janus.capabilities.agents import SystemAgent, BrowserAgent

# AI
from janus.ai.llm import UnifiedLLMClient
from janus.ai.reasoning import ReasonerLLM, ContextRouter

# Platform
from janus.platform.os import SystemBridge
from janus.platform.clipboard import ClipboardManager

# I/O
from janus.io.stt import WhisperSTT
from janus.io.tts import PiperNeuralTTS

# Safety
from janus.safety.validation import UnifiedActionValidator
```

### Deprecated Import Patterns (DO NOT USE)

```python
# ❌ Old patterns - no longer valid
from janus.core import Pipeline  # Use janus.runtime.core
from janus.agents import SystemAgent  # Use janus.capabilities.agents
from janus.llm import UnifiedClient  # Use janus.ai.llm
from janus.stt import WhisperSTT  # Use janus.io.stt
from janus.validation import Validator  # Use janus.safety.validation
```

## System State

**Location:** `janus/runtime/core/pipeline.py`

The pipeline maintains the canonical system state including:
- Active agents and their status
- Current context and history
- Memory engine state
- Execution metrics

## Schema Registry

**Location:** `janus/capabilities/agents/` and `janus/runtime/core/agent_registry.py`

Agent schemas are defined with their implementations in `capabilities/agents/` and registered through the agent registry in `runtime/core/`.

## LLM Client

**Location:** `janus/ai/llm/unified_client.py`

The unified LLM client provides a consistent interface across all providers (Anthropic, OpenAI, Ollama, etc.).

## Vision API

**Location:** `janus/vision/` (unchanged)

Vision capabilities including OCR, screen capture, and visual element detection.

## Entrypoint

**Location:** `apps/cli/main.py`

The official CLI entrypoint for running Janus.

## Build & Installation

**Location:** `scripts/build/` and `scripts/install/`

- Build scripts: `scripts/build/`
- Installation scripts: `scripts/install/`
- Verification scripts: `scripts/verify/`

## Documentation Structure

- `docs/architecture/` - Architectural decision records and design docs
- `docs/developer/` - Developer guides and conventions (including this SSOT)
- `docs/project/` - Project-level docs (audits, changelogs)
- `docs/archive/` - Historical documentation and migration summaries
- `docs/user/` - User-facing documentation

## Experiments & Examples

- `examples/` - Maintained, tested examples that demonstrate features
- `experiments/` - POC code, demos, and manual tests (not production code)
  - `experiments/demos/` - Demo scripts
  - `experiments/manual_tests/` - Manual test scripts
  - `experiments/ui/` - UI experiments

## Data & Artifacts

- `data/` - Versioned, durable data (e.g., persistent databases)
- `artifacts/` - Generated files, logs, caches (git-ignored)
  - `artifacts/audio_logs/`
  - `artifacts/performance_reports/`
  - `artifacts/calibration_profiles/`

## Migration Guide

For code written before this restructuring:

1. Update imports using the patterns above
2. Replace references to `janus.core` with `janus.runtime.core`
3. Replace references to `janus.api` with `janus.runtime.api`
4. Replace `janus.agents` with `janus.capabilities.agents`
5. Replace `janus.llm` with `janus.ai.llm`
6. Replace `janus.reasoning` with `janus.ai.reasoning`
7. Replace `janus.stt`/`janus.tts` with `janus.io.stt`/`janus.io.tts`
8. Replace `janus.os`/`janus.clipboard` with `janus.platform.os`/`janus.platform.clipboard`
9. Replace `janus.validation` with `janus.safety.validation`

## Governance

- **artifacts/** must be git-ignored (only versioned data goes in data/)
- **Legacy code** should not be imported by new code
- **Experiments** should not be imported by production code
- **Each layer** (runtime, capabilities, ai, platform, io, safety) should have clear boundaries

---

**Last Updated:** 2025-12-15
**Version:** 1.0
