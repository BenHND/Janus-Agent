# Developer Documentation

Complete technical documentation for Janus developers.

## 📚 Table of Contents

1. **[01-global-architecture.md](01-global-architecture.md)** - The Big Picture
   - Complete V3 Architecture Diagram
   - LLM-First Principle & Anti-Heuristics Policy  
   - Unified Pipeline in Single-Shot Mode

2. **[02-development-environment.md](02-development-environment.md)** - Development Setup
   - Repository Cloning & Virtual Environment
   - Dependencies (requirements.txt vs requirements-llm.txt)
   - Pre-commit Configuration
   - Local Models Management (Ollama, Whisper, Florence-2)
   - Running Tests (unit tests vs E2E)

3. **[03-core-modules.md](03-core-modules.md)** - Core Modules Technical Details
   - STT & Audio (MLXSTTEngine vs WhisperSTT, VAD, Buffering)
   - Reasoning - The Brain (ReasonerLLM, Jinja2 Prompts, JSON V3)
   - Vision - The Eyes (LightVisionEngine, Florence-2, VisionActionMapper)
   - Execution - The Hands (AgentExecutorV3, OSInterface, MacOSBackend)

4. **[04-contribution-guide.md](04-contribution-guide.md)** - Extending Janus
   - Creating New Modules
   - Adding System Actions
   - Code Conventions (Typing, Docstrings, Structured Logging)

5. **[05-security-and-sandbox.md](05-security-and-sandbox.md)** - Security & Sandbox
   - Action Validation (StrictActionValidator)
   - PII Visual Filter (Data Leak Prevention)
   - Secrets Management (Log Filtering)

6. **[06-deployment-and-packaging.md](06-deployment-and-packaging.md)** - Deployment & Packaging
   - Build Process (build_mac.sh)
   - macOS Code Signing and Notarization

7. **[07-uv-package-management.md](07-uv-package-management.md)** - UV Package Management
   - Modern dependency management with UV
   - 10-100x faster than pip
   - Dependency groups and lockfile management
   - Migration from pip/requirements.txt

8. **[08-binary-distribution.md](08-binary-distribution.md)** - Binary Distribution
   - Building standalone executables with Nuitka
   - Cross-platform builds (Windows, macOS, Linux)
   - CI/CD integration for automated builds
   - Code signing and distribution

---

## 🎯 Quick Start

New to Janus development? Start here:

1. Read [Global Architecture](01-global-architecture.md) to understand the system
2. Follow [Development Environment](02-development-environment.md) to set up your dev environment
3. Study [Core Modules](03-core-modules.md) to understand the technical details
4. Check [Contribution Guide](04-contribution-guide.md) when ready to contribute

## 🔗 Related Documentation

- **[/docs/architecture/](/docs/architecture/)** - Detailed system architecture diagrams
- **[/docs/user/](/docs/user/)** - End-user documentation
- **[/docs/project/](/docs/project/)** - Project management and contribution guidelines

---

**Language**: English  
**Last Updated**: December 2024  
**Version**: V3 (LLM-First Architecture)
