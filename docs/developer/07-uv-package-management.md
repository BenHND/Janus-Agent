# 📦 UV Installation Guide

**TICKET-OPS-001: Modern Package Management with UV**

This guide explains how to install and manage Janus using the modern UV package manager, which provides faster dependency resolution and guaranteed reproducible builds.

---

## Why UV?

UV is a next-generation Python package manager that offers:

- ⚡ **10-100x faster** than pip
- 🔒 **Strict lockfiles** for reproducible builds
- 📦 **All-in-one** package and project management
- 🎯 **Better dependency resolution** with clear conflict reporting
- 💾 **Disk space efficient** with shared package cache

---

## Installation Methods

### Method 1: Using install-uv.sh (Recommended)

The easiest way to install Janus with UV:

```bash
# Clone the repository
git clone https://github.com/BenHND/Janus.git
cd Janus

# Run the UV installation script
./install-uv.sh
```

The script will:
1. Check system requirements
2. Install UV if not present
3. Install system dependencies (macOS/Linux)
4. Sync Python dependencies
5. Configure language preferences
6. Set up models and directories

### Method 2: Manual UV Installation

For more control over the installation process:

#### Step 1: Install UV

```bash
# Install UV via pip
pip install uv

# Or use the official installer (requires internet access to astral.sh)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Step 2: Install System Dependencies

**macOS:**
```bash
brew install portaudio ffmpeg tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev ffmpeg tesseract-ocr
```

**Windows:**
- Download and install system dependencies manually
- Or use Chocolatey: `choco install ffmpeg tesseract`

**Note:** `portaudio` is required only if you plan to use microphone input (`--extra audio`). It's needed for the `pyaudio` package to compile.

#### Step 3: Sync Dependencies

```bash
# Install base dependencies only
uv sync

# Install with specific features
uv sync --extra llm        # Add LLM support
uv sync --extra vision     # Add vision/OCR support
uv sync --extra test       # Add testing tools
uv sync --extra dev        # Add development tools

# Install everything
uv sync --all-extras
```

---

## Understanding pyproject.toml

Janus uses a modern `pyproject.toml` file that consolidates all configuration:

```toml
[project]
name = "janus"
version = "1.0.0"
requires-python = ">=3.10"

# Core dependencies (always installed)
dependencies = [
    "openai-whisper==20231117",
    "faster-whisper>=1.2.1",
    "torch>=2.0.0,<2.5",
    # ... more core deps
]

# Optional feature groups
[project.optional-dependencies]
llm = [
    "openai>=1.54.4",
    "anthropic>=0.39.0",
    # ... LLM dependencies
]

vision = [
    "pytesseract>=0.3.13",
    "opencv-python>=4.10.0.84",
    # ... vision dependencies
]
```

### Dependency Groups

| Group | Purpose | Install Command |
|-------|---------|----------------|
| **base** | Core voice control (no audio) | `uv sync` |
| **audio** | Microphone support (pyaudio) | `uv sync --extra audio` |
| **llm** | AI language models | `uv sync --extra llm` |
| **vision** | OCR and AI vision | `uv sync --extra vision` |
| **semantic** | Vector search & RAG | `uv sync --extra semantic` |
| **test** | Testing framework | `uv sync --extra test` |
| **dev** | Development tools | `uv sync --extra dev` |
| **full** | All features | `uv sync --all-extras` |

---

## The uv.lock File

The `uv.lock` file contains exact versions of all dependencies and sub-dependencies:

- **Guaranteed reproducibility** - same versions on all machines
- **Platform-specific** - different locks for macOS/Linux/Windows
- **Version controlled** - committed to git
- **Auto-generated** - don't edit manually

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade

# Update specific package
uv lock --upgrade-package numpy

# Sync to updated lockfile
uv sync
```

---

## Common UV Commands

### Installation and Sync

```bash
# Install from lockfile (fast, reproducible)
uv sync

# Install with dev dependencies
uv sync --dev

# Install specific extras
uv sync --extra llm --extra vision

# Install everything
uv sync --all-extras
```

### Package Management

```bash
# Add a new dependency
uv add numpy

# Add to specific group
uv add --optional llm openai

# Remove a dependency
uv remove numpy

# Update dependencies
uv lock --upgrade
```

### Running Scripts

```bash
# Run Python script in UV environment
uv run python main.py

# Run with specific extras
uv run --extra llm python main.py

# Run pytest
uv run pytest tests/
```

### Environment Information

```bash
# Show installed packages
uv pip list

# Show dependency tree
uv tree

# Verify lockfile is up to date
uv lock --check
```

---

## Migrating from pip/requirements.txt

If you have an existing Janus installation:

### 1. Remove old virtual environment

```bash
rm -rf venv/
```

### 2. Install UV

```bash
pip install uv
```

### 3. Sync with UV

```bash
# This reads pyproject.toml and uv.lock
uv sync --all-extras
```

### 4. Update your workflow

**Old way (pip):**
```bash
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-llm.txt
python main.py
```

**New way (uv):**
```bash
uv sync --all-extras
uv run python main.py
```

No virtual environment activation needed! UV manages it automatically.

---

## Troubleshooting

### UV not found after installation

```bash
# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

### Dependency resolution conflicts

UV will clearly report conflicts:

```
× No solution found when resolving dependencies:
  ╰─▶ Because package-a==1.0 depends on package-b>=2.0
      and package-c==1.0 depends on package-b<2.0,
      we can conclude that package-a==1.0 and package-c==1.0 are incompatible.
```

Fix by adjusting version constraints in `pyproject.toml`.

### Lock file out of sync

```bash
# Regenerate lockfile
uv lock

# Or force sync
uv sync --refresh
```

### Slow dependency resolution

First run is slower as UV downloads packages. Subsequent runs are much faster thanks to caching.

```bash
# Clear cache if needed
uv cache clean
```

---

## Advantages over Old System

### Before (pip + requirements.txt)

- ❌ Multiple requirements files to manage
- ❌ Version conflicts between files
- ❌ Slow installation
- ❌ No guarantee of reproducibility
- ❌ Manual dependency tracking

### After (uv + pyproject.toml)

- ✅ Single source of truth (pyproject.toml)
- ✅ Strict lockfile (uv.lock)
- ✅ 10-100x faster installation
- ✅ Guaranteed reproducibility
- ✅ Optional feature groups
- ✅ Better conflict resolution

---

## Integration with Development Tools

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: uv-lock
        name: Check uv.lock is up to date
        entry: uv lock --check
        language: system
        pass_filenames: false
```

### VS Code

Install the Python extension and configure:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python"
}
```

UV will create `.venv` automatically when you run `uv sync`.

### CI/CD

See `.github/workflows/build-binaries.yml.example` for CI integration.

---

## Next Steps

- [Quick Start Guide](03-getting-started.md) - Start using Janus
- [Configuration Guide](09-configuration-guide.md) - Customize settings
- [Binary Distribution Guide](08-binary-distribution.md) - Build standalone binaries

---

## Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [PEP 621](https://peps.python.org/pep-0621/) - Project metadata standard

---

**Need Help?**

- Check [Troubleshooting Guide](08-troubleshooting.md)
- Open an issue on [GitHub](https://github.com/BenHND/Janus/issues)
- Read the [UV FAQ](https://docs.astral.sh/uv/faq/)
