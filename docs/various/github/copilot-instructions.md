# Janus AI Coding Agent Instructions

## Project Overview
Janus is a **voice-controlled macOS automation agent** using a unified async pipeline: `speech → reasoning → action → vision`. The codebase follows a **lazy-loading architecture** with optional AI features (LLM, Vision, TTS) that gracefully degrade when unavailable.

## Architecture & Core Pipeline

### Central Pipeline Flow
All commands flow through `janus/core/pipeline.py` (`JanusPipeline`):
1. **STT** (`janus/stt/whisper_stt.py`) - Whisper-based transcription with phonetic corrections
2. **NLU** (`janus/core/deterministic_nlu.py`) - Deterministic intent parsing OR LLM reasoning (`janus/reasoning/reasoner_llm.py`)
3. **Planner** (`janus/core/deterministic_planner.py`) - Generates `ActionPlan` with sequenced steps
4. **Executor** (`janus/automation/action_executor.py`) - Routes actions to module adapters
5. **Vision** (`janus/vision/`) - Optional OCR/AI verification of action success
6. **Memory** (`janus/core/memory_service.py`) - Logs to SQLite for history/undo/learning

### Key Architectural Principles
- **Lazy loading**: Components (STT, Vision, TTS) load only when first used - check `@property` getters in `JanusPipeline`
- **Async-first**: Use `async def` and `await` for all I/O operations (audio, LLM, vision)
- **Dual pipeline**: UI streaming (visual feedback) runs in parallel with command pipeline (execution) - see `ARCHITECTURE_DIAGRAM.md`
- **Settings as truth**: `config.ini` is the single source of truth; `janus/core/settings.py` loads it

## Configuration & Installation

### config.ini Structure
- **`[features]`**: Feature flags (`enable_llm_reasoning`, `enable_vision`, `enable_learning`) - all default `true`
- **`[whisper]`**: Model size, corrections, context buffer, semantic correction paths
- **`[audio]`**: Sample rate (16000 Hz), chunk duration (20ms)
- **`[llm]`**: Provider, model, temperature, API keys
- **`[vision]`**: OCR engine, confidence thresholds, AI models
- **`[tts]`**: Voice, rate, enabled status

### Installation & Setup
```bash
# Unified installer - installs base + LLM + Vision + models
./install.sh  # ~15-30 min, requires 15GB disk space

# Individual requirements files (pip-compile pattern)
requirements.in          # Base voice control
requirements-llm.in      # LLM providers (OpenAI, Anthropic, Mistral, Ollama)
requirements-vision.in   # PyTorch, Transformers, Tesseract, EasyOCR
```

**Critical**: Run `janus/config/model_paths.py::setup_model_paths()` FIRST (before any imports) to configure Whisper model paths for macOS packaging.

## Module Development

### Adapter-Based Architecture
New app integrations inherit from `janus/orchestrator/base_module.py::BaseModule`:
```python
class MyAppModule(BaseModule):
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # Return {"status": "success"|"error", "data": ..., "error": ...}
```

Register in `janus/orchestrator/module_registry.py::ModuleRegistry`. See `janus/modules/chrome_module.py` for reference.

### Action Result Conventions (CRITICAL)
Follow `janus/core/contracts.py` types:
- **Return types**: `ActionResult` with `status`, `data`, `error` fields
- **Success**: `{"status": "success", "data": {...}}`
- **Errors**: `{"status": "error", "error": "description"}`
- **Validation**: Never raise exceptions - return error dicts

See `docs/developer/25-return-value-conventions.md` for full patterns.

## Testing & Validation

### Test Execution
```bash
./run_tests.sh           # All tests with pytest (if available) or unittest
python3 -m pytest tests/ --timeout=10  # Direct pytest with timeout
```

### Test Organization
- **151 test files** in `tests/` covering all components
- **`conftest.py`**: Skips UI tests (`test_overlay.py`, `test_config_ui.py`) when PySide6 unavailable
- **Naming**: `test_<component>.py` or `test_<ticket>_<feature>.py`
- **Fixtures**: Use `@pytest.fixture` for mocks; avoid `unittest.mock` patches in new code

### Known Test Patterns
- UI tests are excluded by default (PySide6 dependency)
- Tests marked with `@pytest.mark.skipif` for platform-specific features (macOS AppleScript)
- Integration tests often use `test_*_integration.py` naming

## Code Quality & Conventions

### Import Style
- **Absolute imports**: `from janus.core.pipeline import JanusPipeline`
- **Relative imports**: Allowed within package (`from .base_module import BaseModule`)
- **Lazy imports**: Import heavy deps (PyTorch, transformers) inside methods for lazy loading

### Type Hints (MANDATORY)
```python
from typing import Optional, Dict, Any, List
async def execute_action(self, action: Dict[str, Any]) -> ActionResult:
```
See `docs/developer/27-type-hints-style-guide.md`.

### Formatting
- **Black**: 100 chars line length (see `pyproject.toml`)
- **isort**: Profile "black" for import sorting
- No manual formatting - let tools handle it

### Exception Handling
- **NEVER raise in executors** - return `{"status": "error", "error": msg}`
- Log with `logger.error()` then return error dict
- See `docs/developer/12-exception-handling.md`

## LLM & Reasoning

### ReasonerLLM (The "Ferrari")
- **Location**: `janus/reasoning/reasoner_llm.py`
- **Purpose**: Advanced command understanding when deterministic NLU fails
- **Integration**: Called by `UnifiedCommandParser` only for ambiguous commands
- **Providers**: Supports OpenAI, Anthropic, Mistral, Ollama (see `janus/llm/llm_service.py`)

### LLM Configuration
API keys loaded from **environment variables** (not config.ini):
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`
- Ollama requires local server at `http://localhost:11434`

## Vision & OCR

### Vision Pipeline
1. **Screenshot** (`janus/vision/screenshot_engine.py`)
2. **OCR** - Tesseract (fast) OR EasyOCR (accurate, slow)
3. **Element Locator** (`janus/vision/element_locator.py`) - Find UI elements by text
4. **AI Vision** (optional) - BLIP-2 for image understanding, CLIP for semantic matching

### Vision as Fallback
Vision activates when:
- Standard automation fails (`execute` returns error)
- User explicitly requests visual actions ("click on the text...")
- Action verification enabled in settings

## Common Workflows

### Running Janus
```bash
python3 main.py              # GUI mode with mic button
python3 main.py -t "command" # Text-only mode (no voice)
python3 main.py --debug      # Enable debug logging
python3 main.py --model small --lang fr  # Override config
```

### Debugging Pipeline
1. Check `config.ini` feature flags
2. Run with `--debug` for verbose logging
3. Check `audio_logs/` for audio/transcription recordings (if `audio_logging.enable_logging=true`)
4. Use `memory.get_command_history(session_id)` to inspect past commands

### Adding a New Feature
1. Update `config.ini` with new settings
2. Modify `janus/core/settings.py` to load settings
3. Implement in appropriate module (`stt/`, `vision/`, `llm/`, `modules/`)
4. Add lazy loading to `JanusPipeline` if optional
5. Write tests in `tests/test_<feature>.py`
6. Update docs in `docs/developer/`

## Key Files Reference

### Must-Read for New Contributors
- `janus/core/pipeline.py` - Central execution flow
- `janus/core/contracts.py` - All data types/protocols
- `main.py` - Entry point and CLI args
- `config.ini` - Configuration source of truth
- `ARCHITECTURE_DIAGRAM.md` - Visual pipeline architecture

### Documentation Hub
- `docs/developer/00-README.md` - Index of all technical docs
- `docs/developer/03-module-development-guide.md` - Adapter development
- `docs/developer/19-unified-pipeline.md` - Pipeline design rationale
- `README.md` - Feature list and project overview
