# Native OCR Architecture (TICKET-OCR-NATIVE)

## Overview

This directory contains the new platform-native OCR architecture that replaces the monolithic EasyOCR/Tesseract implementation with lightweight, platform-specific OCR engines.

## Architecture

### Core Components

1. **`interface.py`** - Abstract base class and common interfaces
   - `OCREngine`: Abstract base class all engines must implement
   - `OCRResult`: Unified result dataclass

2. **`factory.py`** - Platform-specific engine selection
   - Automatically detects platform (macOS/Windows/Linux)
   - Returns the optimal engine for the current platform
   - TICKET-CLEANUP-VISION: No Tesseract fallback (simpler, cleaner)

3. **Platform-Specific Engines**:
   - **`macos_engine.py`** - Apple Vision framework (macOS 10.13+)
   - **`windows_engine.py`** - Windows.Media.Ocr (Windows 10+)
   - **`linux_engine.py`** - RapidOCR with ONNX runtime

## Performance Targets

| Platform | Engine | RAM Overhead | Latency | GPU Acceleration |
|----------|--------|--------------|---------|------------------|
| macOS | Vision.framework | ~10-20 MB | 50-100ms | Neural Engine |
| Windows | Windows.Media.Ocr | ~15-30 MB | 100-200ms | DirectX |
| Linux | RapidOCR (ONNX) | ~50-80 MB | 150-300ms | CPU-optimized |

**Previous (EasyOCR)**: ~2 GB RAM, 1000ms+ latency  
**TICKET-CLEANUP-VISION**: Tesseract fallback removed for cleaner architecture

## Usage

### Basic Usage (Recommended)

```python
from janus.vision.ocr import get_ocr_engine

# Get platform-appropriate engine
engine = get_ocr_engine()
engine.initialize()

# Process image
from PIL import Image
image = Image.open("screenshot.png")
results = engine.process_image(image)

for result in results:
    print(f"{result.text} (confidence: {result.confidence}%)")
    print(f"  Location: {result.bbox}")
```

### Using with Legacy Code

The old `OCREngine` class still works and automatically uses native engines when `backend="auto"` (recommended):

```python
from janus.vision.ocr_engine import OCREngine

# Automatically uses platform-native engine (RECOMMENDED)
engine = OCREngine(backend="auto")
text = engine.recognize_text(image)

# DEPRECATED: Tesseract backend is no longer recommended
# Use native OCR instead for better performance and lower RAM usage
```

### Direct Engine Usage

```python
# macOS only
from janus.vision.ocr.macos_engine import MacOSEngine
engine = MacOSEngine(recognition_level="accurate")  # or "fast"
engine.initialize()
results = engine.process_image(image)

# Windows only
from janus.vision.ocr.windows_engine import WindowsEngine
engine = WindowsEngine()
engine.initialize()
results = engine.process_image(image)

# Linux only
from janus.vision.ocr.linux_engine import LinuxEngine
engine = LinuxEngine()
engine.initialize()
results = engine.process_image(image)
```

## Installation

### Platform-Specific Dependencies

Dependencies are automatically installed based on platform via `pyproject.toml`:

**macOS:**
```bash
pip install pyobjc-framework-Vision pyobjc-framework-Quartz
```

**Windows:**
```bash
pip install winsdk
```

**Linux:**
```bash
pip install rapidocr-onnxruntime
```

**TICKET-CLEANUP-VISION: Tesseract fallback removed**
Native OCR is now the only supported method. Tesseract is no longer installed or recommended.

## Key Benefits

### Memory Efficiency
- **10-50x reduction** in RAM usage vs EasyOCR
- No PyTorch models loaded in Python process for OCR
- Native frameworks handle memory management
- TICKET-CLEANUP-VISION: No Tesseract dependency = simpler installation

### Performance
- **5-10x faster** on supported platforms
- GPU/Neural Engine acceleration where available
- Sub-200ms latency on modern hardware
- No external model downloads needed

### Platform Integration
- Uses OS-native OCR capabilities
- Automatic updates with OS patches
- Better language support (system-wide language packs)

### Simplified Architecture
- Single OCR engine per platform (no fallback chain)
- Clear error messages if OCR fails
- Faster response time to LLM on unreadable images

## Migration Guide

### For Existing Code

No changes needed! The old `OCREngine` class is fully backward compatible:

```python
# Old code with Tesseract (DEPRECATED)
from janus.vision.ocr_engine import OCREngine
engine = OCREngine(backend="tesseract")  # Will show deprecation warning

# New code (RECOMMENDED)
from janus.vision.ocr_engine import OCREngine
engine = OCREngine(backend="auto")  # Uses native engine
```

### For New Code

Use the factory directly for cleaner code:

```python
from janus.vision.ocr import get_ocr_engine

engine = get_ocr_engine()
engine.initialize()
results = engine.process_image(image)
```

## Testing

Run OCR tests:
```bash
python -m unittest tests.test_ocr_engine
python -m unittest tests.test_native_ocr
```

## Implementation Details

### Coordinate Systems

All engines return bounding boxes in the same format:
- Origin: Top-left corner
- Format: `(x, y, width, height)`
- Coordinates: Absolute pixels

**Note**: macOS Vision framework uses bottom-left origin internally, but this is converted automatically.

### Confidence Scores

- All engines return confidence as 0-100 (percentage)
- EasyOCR results are converted: `confidence * 100`
- Windows OCR doesn't provide per-line confidence (uses default 90.0)

### Error Handling

- Engines return empty list `[]` on failure (fail-fast)
- Initialization failures fallback to Tesseract
- All exceptions are logged and handled gracefully

## Future Improvements

- [ ] Implement caching in native engines
- [ ] Add async processing support for native engines
- [ ] Performance benchmarking suite
- [ ] Support for multiple languages in native engines
- [ ] GPU acceleration options for Linux (CUDA/ROCm)
