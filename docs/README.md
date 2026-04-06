# Janus Documentation

Welcome to the complete Janus documentation! This documentation is organized to serve multiple audiences: end users, developers, architects, and contributors.

## 📄 Application Overview

**🆕 NEW: Comprehensive Application Overview for Business & Technical Audiences**

- **[Application Overview (English)](APPLICATION_OVERVIEW.md)** - Complete overview covering architecture, features, security, performance, maintenance, and more
- **[Vue d'Ensemble Application (Français)](VUE_ENSEMBLE_APPLICATION.md)** - Présentation complète de l'application en français

**Perfect for:**
- 🤝 Business presentations and sales discussions
- 💼 Client and stakeholder communication
- 🎯 Project evaluation and due diligence
- 📊 Technical and non-technical audiences
- 🌍 Multilingual documentation needs

**Topics Covered:**
- Pipeline / Maintenance / Updates
- Privacy & Data Protection
- Architecture & Design Philosophy
- Performance & Optimization
- Security & Safety Features
- Complete Feature Catalog
- Evolution & Upgrade Possibilities
- Scalability & Reliability
- Market Position & Competitive Advantages

---

## 📚 Documentation Structure

The documentation is organized into six main sections:

### 🏗️ [Architecture Documentation](architecture/) - **NEW: System Design** 
*Complete technical architecture with detailed diagrams and design principles*

**Start here if you want to understand how Janus works internally!**

**Core Architecture:**
- Complete system architecture with Mermaid diagrams
- Unified async pipeline: speech → reasoning → action → vision
- LLM-First philosophy and anti-heuristics policy
- Agent-based execution system (V3)
- Data flow and transformations
- Module registry and extensibility

**Why Read This:**
- Understand the "big picture" of how Janus works
- Learn the design principles (LLM-First, anti-heuristics, lazy loading)
- See how all components fit together
- Discover the unified pipeline architecture

**Start here:** [Architecture Overview](architecture/README.md)

---

### 👥 [User Documentation](user/) - For End Users
*Simple, non-technical guides for people using the Janus app*

**Getting Started:**
- Installation guide
- Quick start guide (get running in 5 minutes)
- Complete user guide with voice command examples

**Features:**
- Voice commands and use cases
- Personalization and configuration
- Wake word detection and training
- Voice fingerprinting for security

**Support:**
- Troubleshooting common issues
- FAQ

**Start here:** [User Documentation Overview](user/README.md)

**Note:** User documentation is written for non-technical users - no coding knowledge required!

---

### 💻 [Developer Documentation](developer/) - For Contributors
*Technical documentation for developers working on Janus*

**Getting Started:**
- Development environment setup
- Project structure and code organization
- Code conventions and standards

**Technical Guides:**
- Core modules overview
- Security and sandbox
- Deployment and packaging
- UV package management
- Binary distribution

**Start here:** [Developer Documentation Overview](developer/README.md)

**💡 Tip:** Read [Architecture Documentation](architecture/) first to understand the system design, then refer to Developer Documentation for implementation details!

---

### 🔒 [Security Documentation](../SECURITY.md) - Security Policies
*Security guidelines and best practices*

**Contents:**
- Secrets management
- Security policies
- Vulnerability reporting

**Start here:** [Security Guidelines](security/secrets-management.md)

---

### 🏗️ [Project Documentation](project/) - Project Management
*Documentation about contributing, testing, and project policies*

**Contributing:**
- Contribution guidelines
- Code review process
- Pull request standards

**Quality Assurance:**
- Testing guide
- Security guidelines
- Dependencies documentation

**Release Management:**
- Release process
- Version management
- Distribution guidelines

**Start here:** [Contributing Guide](project/CONTRIBUTING.md)

---

## 🎯 Quick Start by Role

### 🙋 I'm an End User
**Goal:** Install and use Janus for voice control

1. Start with [Main README](../README.md) - Understand what Janus does
2. Follow [Installation Guide](user/02-installation.md) - Get Janus installed
3. Try [Getting Started](user/03-getting-started.md) - Get running in 5 minutes
4. Explore [Use Cases](user/04-use-cases.md) - Learn all features
5. If issues: [Troubleshooting](user/06-faq-troubleshooting.md)

**→ Go to [User Documentation](user/README.md)**

---

### 👨‍💻 I'm a Developer/Contributor
**Goal:** Understand the codebase and contribute

1. Start with [Architecture Overview](architecture/README.md) - **Understand the big picture**
2. Read [Complete System Architecture](architecture/01-complete-system-architecture.md) - See all components
3. Study [Unified Pipeline](architecture/02-unified-pipeline.md) - Understand data flow
4. Read [LLM-First Principle](architecture/03-llm-first-principle.md) - Grasp design philosophy
5. Follow [Development Environment](developer/02-development-environment.md) - Set up dev environment
6. Review [Core Modules](developer/03-core-modules.md) - Learn implementation details
7. Check [Contribution Guide](developer/04-contribution-guide.md) - Follow the process

**→ Go to [Architecture Documentation](architecture/README.md) first, then [Developer Documentation](developer/README.md)**

---

### 🏛️ I'm an Architect/Researcher
**Goal:** Understand system design and architecture decisions

1. Start with [Architecture Overview](architecture/README.md) - Complete system design
2. Study [Complete System Architecture](architecture/01-complete-system-architecture.md) - Detailed diagrams
3. Read [Unified Pipeline](architecture/02-unified-pipeline.md) - Pipeline design
4. Understand [LLM-First Principle](architecture/03-llm-first-principle.md) - Design philosophy
5. Review [Agent Architecture](architecture/04-agent-architecture.md) - Agent system
6. Check [Data Flow](architecture/05-data-flow.md) - Data transformations
7. Explore [Module Registry](architecture/06-module-registry.md) - Extensibility

**→ Go to [Architecture Documentation](architecture/README.md)**

---

## 📖 Documentation Standards

All documentation in this repository follows these standards:

- **Format:** Markdown (.md files)
- **Language:** English (with occasional French examples for commands)
- **Structure:** Clear headers with table of contents
- **Examples:** Code samples with syntax highlighting
- **Practical:** Real-world usage examples
- **Versioned:** Updated with each release

## 🗂️ File Organization

Documentation files follow a numbering system for reading order:
- `00-README.md` - Overview and index
- `01-`, `02-`, etc. - Sequential reading order
- Unnumbered files - Reference documents (accessed as needed)

## 🔗 Quick Links

### By Audience
- 🏗️ [Architecture Documentation](architecture/README.md) - **System design**
- 👥 [User Documentation](user/README.md)
- 💻 [Developer Documentation](developer/README.md)
- 📜 [Legacy Documentation](archive/) - Archived historical docs
- 🔒 [Security Documentation](../SECURITY.md)
- 🏗️ [Contributing Guide](project/CONTRIBUTING.md)

### Key Resources
- 📖 [Main README](../README.md) - Project overview
- 🎯 [Code Examples](../examples/) - Working code samples
- 🧪 [Tests](../tests/) - 260+ unit tests
- 📝 [CHANGELOG](../CHANGELOG.md) - Version history

### Getting Help
- 🐛 [Report Issues](https://github.com/BenHND/Janus/issues)
- 💬 [Discussions](https://github.com/BenHND/Janus/discussions)
- 📖 [Troubleshooting Guide](user/08-troubleshooting.md)
- 🔒 [Security Guidelines](project/SECURITY_GUIDELINES.md)

## 🌟 Documentation Highlights

### Most Popular Pages
1. **[Architecture Overview](architecture/README.md)** - Complete system design
2. [User Guide: Getting Started](user/03-getting-started.md) - First steps
3. [Installation Guide](user/02-installation.md) - Get started
4. [Core Modules](developer/03-core-modules.md) - Technical reference
5. [Developer Overview](developer/README.md) - Technical documentation

### Recently Updated (December 2024)
- ✅ **Created comprehensive architecture documentation** with detailed Mermaid diagrams
- ✅ **Documented unified async pipeline** (speech → reasoning → action → vision)
- ✅ **Explained LLM-First principle** and anti-heuristics policy
- ✅ **Documented agent-based architecture** (V3)
- ✅ **Moved legacy documentation to archive** (/docs/legacy)
- ✅ **Complete documentation restructure** for clarity and navigation
- ✅ **Documented Skill Caching & Reflex Mode** (TICKET-LEARN-001) - Agent learns from corrections and executes 5-10x faster on repeated tasks

---

## 📞 Support & Community

**Need help?** Check in this order:
1. [Troubleshooting Guide](user/06-faq-troubleshooting.md)
2. [GitHub Issues](https://github.com/BenHND/Janus/issues) (search existing)
3. [GitHub Discussions](https://github.com/BenHND/Janus/discussions)
4. Open a new issue with details

**Want to contribute?**
1. Read [Contributing Guide](developer/04-contribution-guide.md)
2. Check [Developer Documentation](developer/README.md)
3. Review [Architecture Documentation](architecture/README.md)

---

**Janus** - Local voice-controlled automation for macOS 🎤✨
