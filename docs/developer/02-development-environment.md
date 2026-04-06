# Development Environment Setup

Complete guide to setting up your Janus development environment.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Repository Cloning](#repository-cloning)
3. [Virtual Environment Setup](#virtual-environment-setup)
4. [Dependencies](#dependencies)
5. [Pre-commit Configuration](#pre-commit-configuration)
6. [Local Models Management](#local-models-management)
7. [Running Tests](#running-tests)

## Prerequisites

### System Requirements

- **macOS** 11.0 (Big Sur) or later
- **Python** 3.8 or later (3.10+ recommended)
- **Git** 2.x
- **Homebrew** (for macOS dependencies)

### Recommended Hardware

- Apple Silicon (M1/M2/M3) for optimal performance
- 16GB RAM minimum (32GB recommended for vision models)
- 20GB free disk space (for models)

## Repository Cloning

### Clone the Repository

```bash
# Clone via HTTPS
git clone https://github.com/BenHND/Janus.git
cd Janus

# Or clone via SSH
git clone git@github.com:BenHND/Janus.git
cd Janus
```

### Repository Structure

```
Janus/
├── janus/              # Main Python package
│   ├── agents/         # V3 agent system
│   ├── automation/     # Action execution
│   ├── core/           # Pipeline & contracts
│   ├── reasoning/      # ReasonerLLM
│   ├── stt/            # Speech-to-Text
│   ├── vision/         # Vision system
│   └── ...
├── docs/               # Documentation
├── tests/              # Test suite
├── scripts/            # Utility scripts
├── requirements.txt    # Core dependencies
├── requirements-llm.txt   # LLM dependencies
├── requirements-vision.txt # Vision dependencies
└── requirements-test.txt  # Test dependencies
```

## Virtual Environment Setup

### Create Virtual Environment

```bash
# Using venv (recommended)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
```

### Verify Virtual Environment

```bash
# Should show path to venv/bin/python
which python

# Should show Python 3.8+
python --version
```

## Dependencies

Janus uses multiple requirements files for different features:

### Dependency Files Explained

| File | Purpose | Required |
|------|---------|----------|
| `requirements.txt` | Core Janus functionality | ✅ Yes |
| `requirements-llm.txt` | Local LLM support (Ollama, llama-cpp) | ⚠️ Recommended |
| `requirements-vision.txt` | Vision AI (Florence-2, BLIP-2) | ⚠️ Optional |
| `requirements-test.txt` | Testing framework | ✅ Yes (dev only) |

### Install Core Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Upgrade pip if needed
pip install --upgrade pip
```

### Install LLM Dependencies (Recommended)

```bash
# For local LLM reasoning
pip install -r requirements-llm.txt

# This includes:
# - ollama (local LLM server)
# - llama-cpp-python (GGUF model loading)
# - openai (cloud LLM fallback)
```

### Install Vision Dependencies (Optional)

```bash
# For vision system (OCR + AI)
pip install -r requirements-vision.txt

# Warning: Large download (~5GB)
# This includes:
# - torch (PyTorch)
# - transformers (Hugging Face)
# - pillow (image processing)
# - tesseract/easyocr (OCR engines)
```

### Install Test Dependencies

```bash
# For running tests
pip install -r requirements-test.txt

# This includes:
# - pytest
# - pytest-asyncio
# - pytest-mock
```

### Verify Installation

```bash
# Test core imports
python -c "from janus.core.pipeline import JanusPipeline; print('✓ Core OK')"

# Test LLM imports (if installed)
python -c "from janus.reasoning.reasoner_llm import ReasonerLLM; print('✓ LLM OK')"

# Test vision imports (if installed)
python -c "from janus.vision.light_vision_engine import LightVisionEngine; print('✓ Vision OK')"
```

## Pre-commit Configuration

Pre-commit hooks ensure code quality before committing.

### Install Pre-commit

```bash
# Install pre-commit tool
pip install pre-commit

# Install git hooks
pre-commit install
```

### Pre-commit Checks

The `.pre-commit-config.yaml` file configures:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **trailing-whitespace**: Whitespace cleanup

### Run Pre-commit Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Update pre-commit hooks
pre-commit autoupdate
```

## Local Models Management

Janus uses local AI models for better privacy and offline capability.

### Download Models Script

```bash
# Download all models
./scripts/download_models.sh

# This downloads:
# - Whisper models (STT)
# - Ollama models (LLM)
# - Florence-2 (Vision)
```

### Whisper Models (STT)

```bash
# Download specific Whisper model
./scripts/download_models.sh whisper base

# Available sizes:
# - tiny   (~75 MB, fast but less accurate)
# - base   (~150 MB, balanced)
# - small  (~500 MB, good accuracy)
# - medium (~1.5 GB, high accuracy)
# - large  (~3 GB, best accuracy)
```

**Recommendation**: Use `base` for development, `small` for production.

### Ollama Setup (LLM)

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# Download Qwen 2.5 7B Instruct (default model - superior reasoning)
ollama pull qwen2.5:7b-instruct

# Test Ollama
ollama run qwen2.5:7b-instruct "Hello, how are you?"
```

**Alternative Models**:
```bash
# Llama 3.2 (smaller, faster but less capable)
ollama pull llama3.2

# Mistral 7B (good alternative)
ollama pull mistral

# Phi-3 Mini (smaller, faster)
ollama pull phi3:mini
```

### Florence-2 Setup (Vision)

Florence-2 downloads automatically on first use:

```bash
# Test vision system (downloads model if needed)
python -c "
from janus.vision.light_vision_engine import LightVisionEngine
engine = LightVisionEngine()
print('✓ Florence-2 ready')
"
```

**Note**: Florence-2 is ~3GB. First download takes several minutes.

### Model Storage Locations

```bash
# Whisper models
~/.cache/whisper/

# Ollama models
~/.ollama/models/

# Hugging Face models (Florence-2, BLIP-2)
~/.cache/huggingface/

# Total storage: ~10-15GB for all models
```

## Running Tests

Janus has comprehensive test coverage with both unit and E2E tests.

### Quick Test Run

```bash
# Run all tests (fastest)
./run_tests.sh

# Or use pytest directly
pytest
```

### Unit Tests vs E2E Tests

| Test Type | Location | Purpose | Speed |
|-----------|----------|---------|-------|
| Unit | `tests/unit/` | Individual component testing | Fast (seconds) |
| E2E | `tests/e2e/` | End-to-end workflow testing | Slow (minutes) |

### Run Specific Tests

```bash
# Run unit tests only
pytest tests/unit/

# Run E2E tests only
pytest tests/e2e/

# Run specific test file
pytest tests/unit/test_reasoner_llm.py

# Run specific test function
pytest tests/unit/test_reasoner_llm.py::test_generate_plan

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=janus --cov-report=html
```

### Test Categories

```bash
# Core pipeline tests
pytest tests/unit/test_pipeline.py

# Agent tests
pytest tests/unit/agents/

# STT tests
pytest tests/unit/test_whisper_stt.py

# Vision tests (requires models)
pytest tests/unit/test_vision_engine.py

# Integration tests
pytest tests/integration/
```

### Running Tests with Markers

```bash
# Run only fast tests
pytest -m "not slow"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Test Configuration

Edit `pytest.ini` to configure test behavior:

```ini
[pytest]
# Minimum test coverage required
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (skip in CI)
```

### Continuous Testing

Use `pytest-watch` for continuous testing during development:

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw -- tests/unit/
```

## Development Workflow

### Typical Development Session

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Pull latest changes
git pull origin main

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Create feature branch
git checkout -b feature/my-feature

# 5. Make changes...
# (edit code)

# 6. Run tests
pytest tests/unit/

# 7. Run pre-commit checks
pre-commit run --all-files

# 8. Commit changes
git add .
git commit -m "feat: add my feature"

# 9. Push changes
git push origin feature/my-feature

# 10. Create pull request on GitHub
```

### IDE Configuration

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Black Formatter
- isort
- GitLens

`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

#### PyCharm

1. Set Python interpreter to `venv/bin/python`
2. Enable Black formatter in Settings → Tools → Black
3. Configure pytest as test runner
4. Enable type checking

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError: No module named 'janus'`**
```bash
# Solution: Install in development mode
pip install -e .
```

**Issue: Ollama not found**
```bash
# Solution: Install Ollama
brew install ollama
ollama serve
```

**Issue: Pre-commit failing**
```bash
# Solution: Run auto-fixes
black .
isort .
pre-commit run --all-files
```

**Issue: Tests failing**
```bash
# Solution: Update dependencies
pip install -r requirements-test.txt
pytest --cache-clear
```

---

**Next**: [Core Modules Technical Details](03-core-modules.md)
