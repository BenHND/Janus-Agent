# Janus Examples

This directory contains example files demonstrating Janus's features across all development phases.

## 🚀 Getting Started

### Basic Examples
- **[examples.py](examples.py)** - Basic usage examples for core features

### Phase-Specific Examples

#### Foundation Phases
- **[examples_phase1.py](examples_phase1.py)** - Multi-application workflows
  - Workflow orchestration
  - Chrome, VSCode, Terminal modules
  - Clipboard management

- **[examples_phase2.py](examples_phase2.py)** - LLM & Advanced Understanding
  - Natural language understanding
  - Content analysis
  - Action validation

- **[examples_phase3.py](examples_phase3.py)** - Vision/OCR Fallback
  - Screenshot capture
  - OCR text recognition
  - Element location
  - Vision-based automation

#### Memory & Persistence
- **[examples_phase4.py](examples_phase4.py)** - Persistent Memory & Complex Workflows
  - SQLite database usage
  - Action history
  - Undo/redo system
  - Workflow persistence

- **[examples_phase5.py](examples_phase5.py)** - Specific Modules & Extensions
  - Enhanced VSCode features
  - Chrome DOM manipulation
  - Advanced Terminal features
  - Finder and Slack modules

#### Polish & UI
- **[examples_phase6.py](examples_phase6.py)** - UX/Polish
  - Visual feedback overlay
  - Confirmation dialogs
  - Performance optimization
  - Configuration UI

- **[examples_phase7.py](examples_phase7.py)** - Additional enhancements
  - Phase 7 specific features

#### Advanced Features
- **[examples_phase10.py](examples_phase10.py)** - Enhanced UI/Feedback
  - Enhanced overlay with coordinates
  - Element highlighting
  - Configuration manager API
  - Performance optimization

- **[examples_phase11.py](examples_phase11.py)** - Packaging & Release
  - Application packaging
  - Logging and diagnostics
  - Compatibility checking

#### Sandbox & Extensibility
- **[examples_phase12_sandbox.py](examples_phase12_sandbox.py)** - Module sandbox
  - Isolated module execution
  - Hot-reload capabilities

- **[examples_phase12_memory.py](examples_phase12_memory.py)** - Memory management
  - Multi-session memory
  - Context management

- **[examples_phase12_crash_recovery.py](examples_phase12_crash_recovery.py)** - Crash recovery
  - Automatic recovery
  - State restoration

#### Enhanced Speech Recognition
- **[examples_enhanced_stt.py](examples_enhanced_stt.py)** - Enhanced STT features
  - Correction dictionary
  - Text normalization
  - Microphone calibration

- **[examples_phase15.py](examples_phase15.py)** - Phase 15 quality improvements
  - Context buffer
  - Semantic correction

- **[examples_phase15_integration.py](examples_phase15_integration.py)** - Phase 15 integration
  - Complete pipeline integration

- **[examples_phase15_quality.py](examples_phase15_quality.py)** - Phase 15 quality features
  - Quality metrics
  - Performance testing

- **[examples_phase16.py](examples_phase16.py)** - Voice Understanding Rebuild
  - Realtime STT engine
  - Natural reformatter
  - Voice adaptation cache

## 🏃 Running Examples

### Prerequisites
1. Install dependencies: `pip install -r requirements.txt`
2. Configure microphone access (macOS System Preferences)
3. Download Whisper model (automatic on first run)

### Running an Example
```bash
# Navigate to project root
cd /path/to/Janus

# Run a specific example
python examples/examples.py

# Run phase-specific examples
python examples/examples_phase1.py
python examples/examples_phase3.py
python examples/examples_phase10.py
```

### Example Structure

Most example files follow this pattern:

```python
"""
Phase X Examples
Demonstrates features: feature1, feature2, feature3
"""

def example_1():
    """Demonstrate feature 1"""
    # Setup
    # Execute
    # Display results

def example_2():
    """Demonstrate feature 2"""
    # ...

if __name__ == "__main__":
    # Run all examples
    example_1()
    example_2()
```

## 📚 Additional Resources

- **Documentation**: See [../docs/](../docs/) for detailed guides
- **Main README**: See [../README.md](../README.md) for overview
- **Phase Summaries**: See individual `PHASE*_SUMMARY.md` files in [docs/](../docs/)

## 🎯 Example Categories

### By Feature Area

**Voice Control & STT**
- examples.py
- examples_enhanced_stt.py
- examples_phase15.py
- examples_phase16.py

**Computer Automation**
- examples_phase1.py (Chrome, VSCode, Terminal)
- examples_phase3.py (Vision/OCR)
- examples_phase5.py (Enhanced modules)

**Memory & Persistence**
- examples_phase4.py
- examples_phase12_memory.py

**User Interface**
- examples_phase6.py
- examples_phase10.py
- **[overlay_demo.py](overlay_demo.py)** - PersistentOverlay demo (tkinter)
- **[overlay_ui_demo.py](overlay_ui_demo.py)** - New PySide6 OverlayUI demo ⭐
- **[overlay_ui_pipeline_integration.py](overlay_ui_pipeline_integration.py)** - Pipeline integration example ⭐

**Advanced Features**
- examples_phase2.py (LLM)
- examples_phase12_sandbox.py (Modules)
- examples_phase12_crash_recovery.py (Recovery)

## ⚠️ Important Notes

1. **Microphone Required**: Most examples require a working microphone
2. **macOS Optimized**: Some features are macOS-specific (AppleScript, PyObjC)
3. **Dependencies**: Some examples require optional dependencies (Tesseract, EasyOCR)
4. **API Keys**: LLM examples may require OpenAI API key (or use mock mode)

## 🐛 Troubleshooting

If examples fail to run:
1. Verify all dependencies are installed: `pip install -r requirements.txt`
2. Check microphone permissions in System Preferences
3. Ensure Tesseract is installed for vision examples: `brew install tesseract`
4. Review error messages and consult [docs/INSTALLATION.md](../docs/INSTALLATION.md)

---

**For questions or issues**: Please open an issue on GitHub
