# Changelog

All notable changes to Janus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cross-Platform System Bridges** (TICKET-AUDIT-007)
  - Basic Windows bridge implementation with subprocess and optional pywinauto/pyautogui support
  - Basic Linux bridge implementation with standard Linux tools (xdotool, wmctrl, xclip)
  - Clipboard operations for Windows (tkinter) and Linux (xclip/xsel)
  - Window management for Windows (pywinauto) and Linux (wmctrl/xdotool)
  - UI interactions for Windows and Linux (pyautogui, xdotool)
  - System notifications for Windows (PowerShell) and Linux (notify-send)
  - Script execution for Windows (PowerShell) and Linux (bash)
  - Graceful degradation when optional dependencies are missing
  - Comprehensive documentation in `docs/architecture/18-platform-bridges.md`
  - 48+ unit tests for platform bridge functionality
- **Internationalization (i18n) System**
  - Centralized translation system for all user-facing messages
  - French (default) and English language support
  - Helper functions for TTS feedback (`tts_done()`, `tts_error()`, etc.)
  - Helper functions for overlay status (`status_listening()`, `status_thinking()`, etc.)
  - Generic translation function `t()` with parameter interpolation
  - Integration in terminal mode, UI mode, and overlay
  - Demo script (`examples/example_i18n_demo.py`) for testing translations
  - Comprehensive documentation (`docs/developer/I18N_SYSTEM.md`)
- Version management system with `--version` CLI flag
- Version display in logs and UI on startup
- Comprehensive CHANGELOG.md following Keep a Changelog format
- Release process documentation

### Changed
- Updated system bridge factory to reflect Windows/Linux implementation status
- Improved platform detection logging for clarity

### Fixed
- Windows and Linux system operations no longer return NOT_AVAILABLE for basic features
- System bridge tests updated to reflect new implementation status

## [1.0.0] - 2024-11-14

### Added
- **Phase 0 (MVP)** - Core Foundation
  - Speech-to-Text with Whisper integration and Voice Activity Detection
  - Command parser with natural language understanding (French & English)
  - Basic automation via PyAutoGUI and AppleScript (macOS)
  - Session memory for context-aware commands

- **Phase 1** - Multi-Application Workflows
  - Workflow orchestrator with dependency management
  - Chrome module for browser automation
  - VSCode module for code editor automation
  - Terminal module for shell command execution
  - Global clipboard manager with history

- **Phase 2** - LLM & Advanced Understanding
  - LLM integration (GPT-4, GPT-3.5-turbo, mock mode)
  - Advanced natural language understanding
  - Content analysis (code review, summarization, debugging)
  - Risk-based validation and dangerous command detection
  - Intelligent action plan generation

- **Phase 3** - Vision / OCR Fallback
  - Screenshot engine for screen/window capture
  - OCR engine with Tesseract and EasyOCR support
  - Element locator for finding UI elements by text
  - Automatic OCR fallback when standard automation fails
  - Support for non-scriptable applications

- **Phase 4** - Persistent Memory & Complex Workflows
  - SQLite-based persistent storage
  - Complete action history with search and analytics
  - Undo/redo system with comprehensive logging
  - Workflow pause and resumption
  - Context-aware command execution

- **Phase 5** - Specific Modules & Extensions
  - Enhanced VSCode API integration (line positioning, code structure analysis)
  - Chrome DOM manipulation via JavaScript injection
  - Advanced Terminal features (JSON parsing, environment variables)
  - Finder module for macOS file management
  - Slack module for team communication

- **Phase 6** - UX / Polish
  - Visual feedback overlay with status indicators
  - Risk-based confirmation dialogs
  - Performance optimization with OCR and element caching (500x-2000x speedup)
  - Configuration UI for module management

- **Phase 10** - Enhanced UI / Feedback
  - Enhanced visual overlay with element coordinates display
  - Real-time visual highlighting of UI elements
  - Configuration module interface with runtime management
  - Rendering throttling for performance optimization

- **Phase 11** - Packaging & Release
  - macOS standalone packaging with py2app
  - Complete .app bundle with Python runtime
  - DMG installer creation
  - Comprehensive technical logging with rotation
  - macOS compatibility verification

- **Phase 14** - Enhanced Speech-to-Text
  - Whisper v3 support (v3-turbo, v3-large)
  - Automatic correction dictionary for phonetic errors
  - Text normalization (filler words, punctuation, contractions)
  - Enhanced Voice Activity Detection
  - Microphone calibration with 5-phrase personalization
  - Audio/text logging for error auditing

- **Phase 20B** - Cognitive Planner (LLM Reasoner)
  - ReasonerLLM wrapper for local LLMs (llama-cpp-python, Ollama)
  - Optimized for Mistral 7B Q4 and Phi-3 mini models
  - Natural language command parsing to JSON intents
  - Context-aware execution plan generation
  - French and English prompt templates

- **Phase 22** - Vision Cognitive & Perception
  - AI-powered vision understanding with BLIP-2
  - Intelligent element detection with CLIP
  - Visual error detection (404, crashes, dialogs)
  - Action verification via screen content analysis
  - Visual Q&A ("What do you see?", "Is there an error?")
  - Multi-language error pattern recognition (French, English)

- **TTS** - Voice Response / Text-to-Speech
  - Local TTS using macOS native `say` command
  - Orchestrator hooks for automatic feedback
  - Multi-language support (French, English)
  - Priority queue with interruption support
  - Configurable verbosity and voice settings

### Infrastructure
- 260+ comprehensive tests covering all modules
- Modular installation system (base, LLM, vision, full)
- Unified core pipeline architecture
- SQLite-based memory service with thread-safe operations
- Configuration system with environment variables and CLI overrides
- Structured logging with session and request IDs
- Optional CI/CD workflow (disabled by default)

### Documentation
- Complete user documentation (installation, guides, troubleshooting)
- Developer documentation (architecture, features, API)
- Development history (22+ phase summaries)
- Enhanced STT guide
- TTS guide
- Configuration guide

## [0.1.0] - 2024-01-XX

### Added
- Initial proof of concept
- Basic voice control functionality
- Simple command execution

---

## Version History Notes

### Versioning Scheme

Janus follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (1.X.0): New functionality in a backward-compatible manner
- **PATCH** version (1.0.X): Backward-compatible bug fixes

### Release Types

- **[Unreleased]**: Changes in development, not yet released
- **[X.Y.Z]**: Released version with date (YYYY-MM-DD)

### Change Categories

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

[Unreleased]: https://github.com/BenHND/Janus/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/BenHND/Janus/releases/tag/v1.0.0
[0.1.0]: https://github.com/BenHND/Janus/releases/tag/v0.1.0
