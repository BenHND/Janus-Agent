# Dependency Management Structure

This document explains the modular dependency management system in Janus.

## Overview

Janus uses a modular dependency system that separates core dependencies from optional features. This allows users to install only what they need, reducing installation time and disk space usage.

## File Structure

### Source Files (`.in`)

These files define the direct dependencies:

- **`requirements.in`** - Core base dependencies (14 packages)
  - Voice recognition (Whisper)
  - Basic automation (PyAutoGUI, AppleScript)
  - System monitoring
  - File watching

- **`requirements-llm.in`** - LLM integration (6 packages)
  - OpenAI, Anthropic, Mistral APIs
  - Local LLM support (llama-cpp-python)
  - Enhanced STT (faster-whisper)
  - Voice cache encryption

- **`requirements-vision.in`** - Vision and AI (8 packages)
  - OCR (Tesseract, EasyOCR)
  - Computer vision (OpenCV)
  - AI models (PyTorch, Transformers, BLIP-2, CLIP)

### Lockfiles (`.txt`)

These files pin all dependencies (direct + transitive) for reproducibility:

- **`requirements.txt`** - Base lockfile (~50 packages)
- **`requirements-llm.txt`** - LLM lockfile (~30 packages)
- **`requirements-vision.txt`** - Vision lockfile (~40 packages)

## Installation Scripts

Convenient shell scripts for different installation scenarios:

- **`install-base.sh`** - Base installation (~500MB, 2-5 min)
- **`install-llm.sh`** - Add LLM features (~+500MB, 2-5 min)
- **`install-vision.sh`** - Add Vision/AI (~+5-10GB, 10-20 min)
- **`install-full.sh`** - Complete installation (~10-15GB, 15-30 min)

## Updating Dependencies

### Update a Single Package

```bash
# Edit the appropriate .in file
vim requirements.in  # or requirements-llm.in, requirements-vision.in

# Regenerate lockfile
pip-compile requirements.in

# Install updated dependencies
pip install -r requirements.txt
```

### Update All Packages

```bash
# Update base dependencies
pip-compile requirements.in --upgrade

# Update LLM dependencies
pip-compile requirements-llm.in --upgrade

# Update vision dependencies
pip-compile requirements-vision.in --upgrade

# Reinstall
./install-base.sh
./install-llm.sh
./install-vision.sh
```

### Add a New Dependency

1. Add to appropriate `.in` file:
   ```bash
   echo "new-package>=1.0.0  # Description" >> requirements.in
   ```

2. Regenerate lockfile:
   ```bash
   pip-compile requirements.in
   ```

3. Install:
   ```bash
   pip install -r requirements.txt
   ```

## Verification

Use the verification script to check your installation:

```bash
python verify-installation.py
```

This will show:
- ✅ Which base dependencies are installed
- ⚠️  Which optional dependencies are missing
- 💡 Suggestions for completing installation

## Design Principles

1. **Separation of Concerns**
   - Base: Core voice control functionality
   - LLM: Advanced language understanding (optional)
   - Vision: OCR and AI vision (optional)

2. **Reproducibility**
   - Lockfiles pin all dependencies (including transitive)
   - Same versions across all installations
   - No surprises from dependency updates

3. **Flexibility**
   - Install only what you need
   - Add features incrementally
   - Easy to customize for specific use cases

4. **Performance**
   - Fast base installation without heavy AI dependencies
   - PyTorch/Transformers (~5GB) only when needed
   - Reduced initial setup time

## Common Scenarios

### Minimal Installation (Development/Testing)
```bash
./install-base.sh
```
- Voice control
- Basic automation
- ~500MB, 2-5 minutes

### Professional Use (With APIs)
```bash
./install-base.sh
./install-llm.sh
```
- Everything above, plus:
- GPT-4, Claude, Mistral integration
- Enhanced command understanding
- ~1GB, 5-10 minutes

### Complete Features (AI/Vision)
```bash
./install-full.sh
```
- Everything
- OCR, computer vision, AI models
- ~10-15GB, 15-30 minutes

### Custom Installation
```bash
# Base + Vision only (no LLM APIs)
./install-base.sh
./install-vision.sh
```

## Troubleshooting

### Lockfile Out of Sync

If you manually edited dependencies:

```bash
# Regenerate all lockfiles
pip-compile requirements.in
pip-compile requirements-llm.in
pip-compile requirements-vision.in
```

### Dependency Conflicts

```bash
# Clean install
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

### Version Mismatch

```bash
# Force reinstall with exact versions
pip install --force-reinstall -r requirements.txt
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install base dependencies
  run: |
    pip install -r requirements.txt

- name: Install LLM dependencies (optional)
  if: matrix.features == 'full'
  run: |
    pip install -r requirements-llm.txt

- name: Install vision dependencies (optional)
  if: matrix.features == 'full'
  run: |
    pip install -r requirements-vision.txt
```

## Related Files

- `setup.py` - Package configuration with `extras_require`
- `INSTALL.md` - User-facing installation guide
- `verify-installation.py` - Installation verification script

## Benefits

✅ **Reproducible**: Lockfiles ensure same versions everywhere
✅ **Fast**: Base installation takes minutes, not hours
✅ **Modular**: Install only what you need
✅ **Professional**: Industry-standard dependency management
✅ **Maintainable**: Easy to update and audit dependencies
