# Janus AI Models Directory

This directory contains the AI models used by Janus for voice recognition and computer vision.

**✨ NEW**: As of the latest version, Janus automatically manages model storage in this directory. All models are downloaded here instead of `~/.cache`, making the project portable and self-contained.

## 📁 Directory Structure

```
models/
├── whisper/          # Standard Whisper speech-to-text models
│   ├── tiny.pt       # ~40MB - Fastest, least accurate
│   ├── base.pt       # ~140MB - Balanced (default)
│   ├── small.pt      # ~460MB - Better accuracy
│   ├── medium.pt     # ~1.4GB - High accuracy
│   └── large.pt      # ~2.9GB - Highest accuracy
├── torch/            # PyTorch model cache (auto-managed)
├── transformers/     # HuggingFace Transformers cache (auto-managed)
│   ├── models--Salesforce--blip2-opt-2.7b/  # BLIP-2 models
│   └── models--openai--clip-vit-base-patch32/  # CLIP models
├── huggingface/      # HuggingFace Hub cache (auto-managed)
├── xdg_cache/        # faster-whisper cache (auto-managed, Linux/Mac)
└── vision/           # Legacy vision models directory
```

## 🎯 Automatic Cache Management

Janus now automatically configures all AI libraries to use local cache directories:

- **TORCH_HOME** → `models/torch/`
- **TRANSFORMERS_CACHE** → `models/transformers/`
- **HF_HOME** → `models/huggingface/`
- **XDG_CACHE_HOME** → `models/xdg_cache/` (Linux/Mac)

**Benefits:**
- ✅ No more `~/.cache` pollution
- ✅ Project is self-contained and portable
- ✅ Easy cleanup - just delete the `models/` directory
- ✅ Models are removed when you delete Janus
- ✅ Multiple Janus installations can coexist

## 🔽 Downloading Models

### Automatic Download (Recommended)

Models are downloaded automatically on first use. Just run Janus and it will download what it needs.

You can also pre-download models using the download script:

```bash
# Download base Whisper model only (140MB)
./scripts/download_models.sh

# Download specific Whisper model
./scripts/download_models.sh --whisper small

# Download Whisper + vision models (5-10GB)
./scripts/download_models.sh --with-vision
```

### Manual Download

You can also download models manually using Python:

```python
import whisper

# Janus automatically configures the cache directory
# Just import janus first to set up paths
import janus

# Download Whisper model (will use local cache)
model = whisper.load_model('base')
# Model is saved to: models/whisper/base.pt
```

## 📊 Model Sizes and Performance

### Whisper Models

| Model  | Size   | Speed (M1) | Accuracy | Use Case |
|--------|--------|------------|----------|----------|
| tiny   | ~40MB  | ~10x       | Low      | Testing, embedded systems |
| base   | ~140MB | ~7x        | Good     | **Default - balanced** |
| small  | ~460MB | ~4x        | Better   | Better accuracy needed |
| medium | ~1.4GB | ~2x        | High     | Professional use |
| large  | ~2.9GB | ~1x        | Highest  | Maximum accuracy |

**Recommendation**: Use `base` for most cases. Upgrade to `small` if you experience transcription errors.

### Vision Models (Optional)

| Model  | Size  | Purpose | Speed (M1) |
|--------|-------|---------|------------|
| BLIP-2 | ~2GB  | Image captioning, visual Q&A | ~1-2s |
| CLIP   | ~1.5GB| Image-text matching | ~0.5-1s |

**Note**: Vision models are only needed if you use OCR and visual automation features.

## 🔧 Configuration

### Environment Variables (Automatic)

Janus automatically sets up these environment variables on startup:

```bash
TORCH_HOME=./models/torch
TRANSFORMERS_CACHE=./models/transformers
HF_HOME=./models/huggingface
HF_HUB_CACHE=./models/huggingface
XDG_CACHE_HOME=./models/xdg_cache  # Linux/Mac only
SPECTRA_MODELS_DIR=./models/whisper  # Legacy support
SPECTRA_VISION_MODELS_DIR=./models/vision  # Legacy support
```

**You don't need to set these manually** - Janus handles it automatically when you:
1. Import the `janus` package, or
2. Run `main.py`

### Manual Override (Optional)

If you need to use a custom models directory, you can override the default by setting environment variables before running Janus:

```bash
export SPECTRA_MODELS_DIR="/custom/path/whisper"
export SPECTRA_VISION_MODELS_DIR="/custom/path/vision"
python main.py
```

## 🚀 First Launch Setup

On first launch, Janus will:

1. **Automatically configure cache directories** in `models/`
2. Check if models exist
3. If not found, automatically download the default model (base) on first use
4. Show download progress
5. Cache models for future use - all within the `models/` directory

You can verify the configuration with:

```bash
python scripts/demo_model_paths.py
```

Or pre-download models before first launch:

```bash
./scripts/download_models.sh
```

## 💾 Disk Space Requirements

### Minimum (Base Only)
- **Whisper base**: 140MB
- **Total**: ~200MB

### Recommended (Base + Small Vision)
- **Whisper base**: 140MB
- **Vision models**: 5GB
- **Total**: ~5.2GB

### Full (All Models)
- **All Whisper models**: ~5GB
- **Vision models**: 5GB
- **Total**: ~10GB

## 🔄 Updating Models

Models are periodically updated by their creators. To get the latest versions:

1. Delete old models:
   ```bash
   # Remove specific model types
   rm -rf models/whisper/*
   rm -rf models/transformers/*
   rm -rf models/torch/*

   # Or remove all cached models
   rm -rf models/*/
   # Keep directory structure
   python -c "from janus.config.model_paths import setup_model_paths; setup_model_paths()"
   ```

2. Re-download:
   ```bash
   ./scripts/download_models.sh --with-vision
   ```

Models will be re-downloaded automatically on next use.

## 🗑️ Removing Models

To free up disk space, you can remove models you don't need:

```bash
# Remove specific Whisper model
rm models/whisper/large.pt

# Remove all HuggingFace transformers cache
rm -rf models/transformers/*

# Remove all models (will re-download on next use)
rm -rf models/whisper/*
rm -rf models/torch/*
rm -rf models/transformers/*
rm -rf models/huggingface/*
rm -rf models/xdg_cache/*

# To completely reset and remove Janus with all models:
rm -rf models/
```

**Note**: With the new cache management, removing the entire `models/` directory will completely clean up all AI models, unlike the old system where models would remain in `~/.cache`.

## 🔒 Security Notes

- Models are downloaded from official sources:
  - Whisper: OpenAI
  - BLIP-2: Salesforce/HuggingFace
  - CLIP: OpenAI/HuggingFace
- Downloads use HTTPS
- Models are cached locally - no internet needed after download
- No telemetry or usage data is sent

## 🐛 Troubleshooting

### Models Still Going to ~/.cache

**Problem**: Models are still downloaded to `~/.cache` instead of `models/`

**Solutions**:
1. Ensure you're importing janus before loading models: `import janus` before `import whisper`
2. Check environment variables: `python -c "import os; import janus; print(os.environ.get('TORCH_HOME'))"`
3. Run the test: `python scripts/test_model_paths.py`
4. Clear old cache: `rm -rf ~/.cache/whisper ~/.cache/torch ~/.cache/huggingface`

### Models Not Downloading

**Problem**: Download script fails or hangs

**Solutions**:
- Check internet connection
- Ensure sufficient disk space
- Check firewall settings
- Try a different mirror (for HuggingFace models)

### "Model Not Found" Error

**Problem**: Janus can't find downloaded models

**Solutions**:
1. Verify models exist: `ls -lh models/whisper/`
2. Check environment variables: `python scripts/demo_model_paths.py`
3. Re-download: `./scripts/download_models.sh`

### Out of Disk Space

**Problem**: Not enough space to download models

**Solutions**:
- Use smaller model: `./scripts/download_models.sh --whisper tiny`
- Skip vision models (use base features only)
- Free up disk space
- Use external drive

### Slow Download Speed

**Problem**: Download takes very long

**Solutions**:
- Use wired internet connection
- Download during off-peak hours
- Use download resume capability
- Consider pre-downloading on faster connection

## 📚 Additional Resources

- [Whisper Documentation](https://github.com/openai/whisper)
- [BLIP-2 Documentation](https://huggingface.co/Salesforce/blip-image-captioning-base)
- [CLIP Documentation](https://github.com/openai/CLIP)
- [HuggingFace Models](https://huggingface.co/models)

---

**Note**: This directory is excluded from git via `.gitignore` due to large file sizes. Models must be downloaded separately.
