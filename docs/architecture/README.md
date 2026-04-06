# Janus Architecture Documentation

> **Version:** V3 Multi-Layer OODA Loop Architecture  
> **Last Updated:** December 2024  
> **Status:** Refactored - Services Extracted, ActionCoordinator Primary

Complete technical architecture documentation for Janus, a voice-controlled computer automation system built on AI-powered reasoning.

## Overview

Janus is a **local voice assistant** that controls your computer entirely through voice commands. It uses an **OODA Loop** (Observe-Orient-Decide-Act) architecture powered by Large Language Models to understand natural language, observe the screen, make intelligent decisions, and execute actions.

### Core Design Principles

1. **OODA Loop Architecture**: Dynamic execution cycle - observe current state, orient/analyze context, decide next action, act and repeat
2. **LLM-First Philosophy**: AI reasoning replaces traditional pattern matching and heuristics  
3. **Visual Grounding**: Set-of-Marks computer vision for precise element identification
4. **Multi-Layer Execution**: Clear separation between orchestration, execution, and action layers
5. **Modular Agents**: Domain-specific agents (system, browser, files, UI, etc.) handle atomic operations
6. **Privacy-First**: All processing happens locally - no mandatory cloud dependencies
7. **Type Safety**: Strong typing with dataclasses throughout the system
8. **Graceful Degradation**: Optional features (LLM, Vision, TTS) work independently

## Quick Start for Developers

```python
from janus.core import JanusAgent

# Initialize the agent
agent = JanusAgent()

# Execute a command
result = await agent.execute("open Calculator and compute 15 + 27")

if result.success:
    print(f"Success: {result.message}")
```

## Complete System Architecture

### Execution Flow (High-Level)

```
Voice/Text Input
    ↓
Speech-to-Text (Whisper)
    ↓
JanusAgent (Entry Point)
    ↓
ActionCoordinator (OODA Loop)
    ├─→ Observe: Vision + System State
    ├─→ Orient: Context Analysis  
    ├─→ Decide: ReasonerLLM chooses next action
    └─→ Act: Execute via execution layer
         ↓
AgentExecutorV3 (Orchestration ~786 lines)
    ├─→ ValidatorAgent (Pre-validation)
    ├─→ Execution Services:
    │   ├─→ VisionRecoveryService (Error recovery)
    │   ├─→ ReplanningService (LLM replanning)
    │   ├─→ ExecutionService (Retry/self-healing)
    │   ├─→ ContextManagementService (Context mgmt)
    │   └─→ PreconditionService (Precondition validation)
    └─→ Routes to AgentRegistry
         ↓
AgentRegistry (Action Routing)
    ↓
Domain Agents (Execution)
    ├─→ SystemAgent
    ├─→ BrowserAgent
    ├─→ FilesAgent
    ├─→ UIAgent
    └─→ etc.
         ↓
OS Interface (macOS/Windows/Linux)
    ↓
Result + Memory Update
```

### Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                 INPUT LAYER                          │
│  • Voice (Microphone → Whisper STT)                 │
│  • Text (Direct command string)                      │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           ORCHESTRATION LAYER                       │
│  ┌───────────────────────────────────────────┐     │
│  │  JanusAgent (Public API)                  │     │
│  │    - execute(command)                     │     │
│  │    - Session management                   │     │
│  │    - Settings & configuration             │     │
│  └────────────────┬──────────────────────────┘     │
│                   │                                 │
│  ┌────────────────▼──────────────────────────┐     │
│  │  ActionCoordinator (OODA Loop)            │     │
│  │    - Observe (vision + state)             │     │
│  │    - Orient (context analysis)            │     │
│  │    - Decide (ReasonerLLM)                 │     │
│  │    - Act (execution)                      │     │
│  └───────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           EXECUTION LAYER                           │
│  ┌───────────────────────────────────────────┐     │
│  │  AgentExecutorV3 (Orchestration ~786L)    │     │
│  │    - ValidatorAgent (pre-validation)      │     │
│  │    - Routes to AgentRegistry              │     │
│  │    - Delegates to execution services      │     │
│  └────────┬──────────────────┬───────────────┘     │
│           │                  │                      │
│  ┌────────▼──────────────────▼──────────────┐     │
│  │  Execution Services (REFACTOR-003)       │     │
│  │  • VisionRecoveryService                 │     │
│  │  • ReplanningService                     │     │
│  │  • ExecutionService                      │     │
│  │  • ContextManagementService              │     │
│  │  • PreconditionService                   │     │
│  └──────────────────────────────────────────┘     │
│                   │                                 │
│  ┌────────────────▼──────────────────────────┐     │
│  │  AgentRegistry (Action Routing)           │     │
│  │    - Maps actions to agents               │     │
│  │    - Agent lifecycle management           │     │
│  └───────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│             AGENT LAYER                             │
│  ┌─────────────────────────────────────────────┐   │
│  │  Domain-Specific Agents                     │   │
│  │  • SystemAgent  • BrowserAgent              │   │
│  │  • FilesAgent   • UIAgent                   │   │
│  │  • MessagingAgent • CodeAgent               │   │
│  │  • LLMAgent • ValidatorAgent                │   │
│  └─────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│            SUPPORT SYSTEMS                          │
│  • Vision Engine: Screen analysis & element detect  │
│  • Memory Engine: Session & conversation tracking   │
│  • OS Interface: System automation (click, type...) │
│  • ReasonerLLM: AI decision making                  │
│  • TTS Engine: Voice feedback (optional)            │
└─────────────────────────────────────────────────────┘
```

## Core Components

### 1. JanusAgent - Single Entry Point

The only public API for Janus. Provides simple initialization and a single `execute()` method.

**Responsibilities:**
- Public API for all commands
- Session initialization and management
- Settings and configuration handling
- Delegates execution to ActionCoordinator

**Key Methods:**
- `execute(command)` - Execute a natural language command
- `__init__(config_path, session_id, ...)` - Initialize with settings

**Location:** `janus/core/janus_agent.py`

### 2. ActionCoordinator - OODA Loop Orchestration

Implements the observe-orient-decide-act cycle. Orchestrates the high-level execution flow.

**Responsibilities:**
- Execute OODA loop iterations (max 20 by default)
- Observe: Capture screen state and visual context
- Orient: Analyze context and understand goal
- Decide: Call ReasonerLLM to choose next action
- Act: Execute action via AgentExecutorV3

**Key Methods:**
- `execute_goal(user_goal, intent, session_id, ...)` - Main OODA loop
- `_observe()` - Capture system and visual state
- `_orient()` - Analyze context
- `_decide()` - Get next action from Reasoner
- `_act()` - Execute action

**Location:** `janus/core/action_coordinator.py`

### 3. AgentExecutorV3 - Step Execution Engine

**Refactored (TICKET-REFACTOR-003)**: Reduced from 2172 to 786 lines by extracting specialized services.

Orchestrates static action plan execution with pre-validation and context management.

**Core Responsibilities:**
- ✅ Pre-validate actions with ValidatorAgent
- ✅ Route actions to agents via AgentRegistry
- ✅ Manage global execution context (app, URL, domain, etc.)

**Delegates to Services:**
- **VisionRecoveryService**: Vision-based error recovery
- **ReplanningService**: LLM-based replanning after failures
- **ExecutionService**: Step execution with retry and self-healing
- **ContextManagementService**: Context initialization, validation, updates
- **PreconditionService**: Precondition validation and waiting

**Location:** `janus/core/agent_executor_v3.py` (~786 lines)
**Services:** `janus/services/` (vision_recovery_service.py, replanning_service.py, execution_service.py, context_management_service.py, precondition_service.py)

### 4. ValidatorAgent - Action Validation

Validates actions before execution to prevent errors.

**Responsibilities:**
- Validate action parameters
- Check preconditions (e.g., app is open)
- Ensure context is appropriate
- Prevent invalid operations

**Location:** `janus/agents/validator_agent.py`

### 5. AgentRegistry - Action Routing

Central registry that routes actions to appropriate agents.

**Responsibilities:**
- Map action prefixes to agents (e.g., `system.*` → SystemAgent)
- Agent lifecycle management
- Action dispatch

**Location:** `janus/core/agent_registry.py`

### 6. Domain-Specific Agents

Modular agents handle execution in specific domains. Each agent provides atomic operations.

**Available Agents:**
- **SystemAgent**: Launch apps, system operations (`system.open_app`)
- **BrowserAgent**: Web navigation, URL handling (`browser.navigate`)
- **FilesAgent**: File operations, path handling (`files.read`)
- **UIAgent**: Generic UI interaction (`ui.click`, `ui.type`)
- **MessagingAgent**: Email, Slack, Teams (`messaging.send`)
- **CodeAgent**: Terminal commands (`code.run_command`)
- **LLMAgent**: LLM operations (`llm.summarize`)

**Location:** `janus/agents/`

### 7. ReasonerLLM - AI Decision Making

Large Language Model that makes intelligent decisions about what action to take next.

**Capabilities:**
- Understand natural language commands
- Analyze current screen state
- Choose appropriate actions
- Handle ambiguity and missing information
- Decide next step in OODA loop

**Methods:**
- `decide_next_action()` - Choose next action based on context (ReAct Loop)
- `generate_structured_plan()` - Generate multi-step action plan

**Location:** `janus/reasoning/reasoner_llm.py`

### 8. Vision Engine - Screen Understanding

Computer vision system using Set-of-Marks for element detection.

**Capabilities:**
- Capture screenshots
- Detect UI elements with Set-of-Marks tagging
- Provide visual context to the reasoner
- Enable element-based interaction

**Key Components:**
- SetOfMarksEngine - Element detection and tagging
- AsyncVisionMonitor - Background screen monitoring
- Element locators and OCR

**Location:** `janus/vision/`

### 9. Memory Engine - State & History

Unified memory system for state management with **semantic search** (TICKET-MEM-001).

**Capabilities:**
- Session management
- Conversation history tracking
- Command history
- Reference resolution ("it", "that", "the previous file")
- **NEW: Semantic memory** - Natural language reference resolution
  - Vector-based search (ChromaDB)
  - Multi-lingual support (English, French, etc.)
  - Resolves queries like "the PDF from earlier" or "le fichier d'hier"
- Cross-session memory

**API:** 11 core methods (10 original + `search_semantic`)

**Location:** `janus/core/memory_engine.py`  
**Documentation:** [Memory Engine Guide](17-memory-engine.md) | [Semantic Memory Details](../SEMANTIC_MEMORY.md)

### 10. Pipeline (Internal Implementation)

JanusPipeline provides internal pipeline processing implementation.

**Architecture After Refactoring:**
- **Primary path**: JanusAgent → ActionCoordinator (OODA loop) → AgentExecutorV3
- **Pipeline role**: Internal coordinator for backward compatibility
- **Services extracted**: STT, Vision, Memory, TTS, Lifecycle

**Implementation Split:**
- `pipeline.py` (292 lines): Core class definition
- `_pipeline_impl.py` (871 lines): Implementation mixin  
- `_pipeline_properties.py` (397 lines): Lazy-loading properties

**Extracted Services** (`janus/services/`):
- `STTService`: Speech-to-text processing
- `VisionService`: Screen capture and verification
- `MemoryServiceWrapper`: Context management for pipeline
- `TTSService`: Text-to-speech feedback
- `LifecycleService`: Init, cleanup, warmup, monitoring

**Note:** ActionCoordinator is now the default execution mode (`use_dynamic_execution: True`)

## Key Architectural Patterns

### OODA Loop (Observe-Orient-Decide-Act)

The core execution pattern. Instead of planning all steps upfront, Janus:
1. **Observes** the current screen state with Vision Engine
2. **Orients** by analyzing context (current app, URL, memory, etc.)
3. **Decides** the single next action to take using ReasonerLLM
4. **Acts** by executing that action via AgentExecutorV3
5. **Loops** back to observe the result

This makes Janus adaptive to unexpected UI states and robust to failures.

### Multi-Layer Execution

The architecture has clear separation of concerns:
- **Orchestration Layer**: High-level goal management (JanusAgent, ActionCoordinator)
- **Execution Layer**: Step execution and validation (AgentExecutorV3, AgentRegistry)
- **Agent Layer**: Domain-specific atomic operations (Agents)
- **OS Layer**: Low-level system interaction

### LLM-First Philosophy

Traditional automation relies on pattern matching (regex, if-statements). Janus uses LLM reasoning instead:

**Traditional:**
```python
if "click" in command and "button" in command:
    # Find button...
```

**Janus:**
```python
# LLM analyzes full context and decides:
action = await reasoner.decide_next_action(
    user_goal="click submit button",
    visual_context=screen_elements,
    system_state=current_state
)
```

### Visual Grounding with Set-of-Marks

Instead of CSS selectors or hardcoded coordinates:
1. Vision engine tags each interactive element with an ID
2. Provides list of elements to LLM: `[ID 1] Button "Submit" (x=100, y=200)`
3. LLM references elements by ID in actions
4. AgentExecutorV3 uses exact coordinates of that element

This works on any application without automation APIs.

### Validation and Error Recovery

**Pre-Execution Validation:**
- ValidatorAgent checks preconditions before execution
- Prevents errors before they happen

**Vision-Based Recovery:**
- If action fails, AgentExecutorV3 captures screen
- Analyzes actual state with Vision Engine
- ReasonerLLM generates recovery steps
- Executes recovery (one attempt, fail fast)

## Documentation Index

### 📚 Start Here
1. **[01-complete-system-architecture.md](01-complete-system-architecture.md)** - **Complete overview with diagrams**
2. **[15-janus-agent-api.md](15-janus-agent-api.md)** - Public API reference
3. **[02-unified-pipeline.md](02-unified-pipeline.md)** - OODA Loop execution flow

### 🏗️ Core Architecture
- **[13-dynamic-react-loop.md](13-dynamic-react-loop.md)** - OODA/ReAct Loop implementation details
- **[14-action-coordinator.md](14-action-coordinator.md)** - ActionCoordinator orchestration logic (SOLE RUNTIME)
- **[29-burst-ooda-mode.md](29-burst-ooda-mode.md)** - Burst OODA execution optimization
- **[31-runtime-ssot-ooda-adr.md](31-runtime-ssot-ooda-adr.md)** - **ADR: Runtime SSOT & V3 Removal** ✅ Complete
- **[04-agent-architecture.md](04-agent-architecture.md)** - Domain-specific agent system
- **[03-llm-first-principle.md](03-llm-first-principle.md)** - Anti-heuristics policy and LLM reasoning
- **[30-hal-consolidation-adr.md](30-hal-consolidation-adr.md)** - ADR: Hardware Abstraction Layer consolidation

### 🔧 Core Components
- **[17-memory-engine.md](17-memory-engine.md)** - Unified memory and persistence system
- **[22-microsoft-365-integration.md](22-microsoft-365-integration.md)** - Native calendar & email providers (TICKET-APP-001)
- **[23-salesforce-crm-integration.md](23-salesforce-crm-integration.md)** - Salesforce CRM native connector (TICKET-BIZ-001)
- **[24-messaging-integration.md](24-messaging-integration.md)** - Slack & Teams integration (TICKET-BIZ-002)
- **[27-proactive-vision-integration.md](27-proactive-vision-integration.md)** - Set-of-Marks vision system
- **[19-system-bridge.md](19-system-bridge.md)** - OS abstraction and automation layer
- **[08-reasoner-v4-think-first.md](08-reasoner-v4-think-first.md)** - ReasonerLLM decision making
- **[25-speech-to-text-stt.md](25-speech-to-text-stt.md)** - Speech-to-Text (STT) architecture and engines
- **[26-text-to-speech-tts.md](26-text-to-speech-tts.md)** - Text-to-Speech (TTS) architecture

### 🤖 AI/LLM Features
- **[32-arch-002-unified-llm-stack.md](32-arch-002-unified-llm-stack.md)** - ARCH-002: Unified LLM Stack (Single SSOT)
- **[ARCH-003-strict-json-validation.md](ARCH-003-strict-json-validation.md)** - ARCH-003: Strict JSON Validation (No Regex Repair)
- **Tool RAG (TICKET-FEAT-TOOL-RAG)** - Dynamic tool selection via semantic search
  - **Location**: `janus/services/tool_retrieval_service.py`, `janus/config/tools_registry.py`
  - **Purpose**: Automatically selects 3-5 most relevant tools from 50+ available based on user query
  - **Technology**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
  - **Performance**: <30ms avg retrieval, supports 100+ tools without prompt modifications
  - **Integration**: Integrated in ActionCoordinator `_build_react_prompt()`, injected into Jinja2 templates
  - **Tools Covered**: CRM (Salesforce), Messaging (Slack/Teams), Microsoft 365 (Calendar/Email), System, Browser, Files, UI, Code, LLM, Scheduler
  - **Solves**: Token explosion problem when scaling to many backend integrations
- **[28-skill-caching.md](28-skill-caching.md)** - Learning from user corrections (TICKET-LEARN-001)

### 📊 Data & Flow
- **[05-data-flow.md](05-data-flow.md)** - Data flow patterns and contracts
- **[06-module-registry.md](06-module-registry.md)** - Agent registry and action routing
- **[09-system-context-grounding.md](09-system-context-grounding.md)** - System context and grounding
- **[21-smart-clipboard.md](21-smart-clipboard.md)** - Smart Clipboard automatic capture (TICKET-FEAT-001)

### 🛡️ Advanced Features
- **[12-smart-self-healing.md](12-smart-self-healing.md)** - Error recovery and vision fallback
- **[07-semantic-gatekeeper.md](07-semantic-gatekeeper.md)** - Validation and safety checks
- **[10-missing-info-feedback.md](10-missing-info-feedback.md)** - Handling ambiguity
- **[11-generic-tooling-standardization.md](11-generic-tooling-standardization.md)** - Tool interfaces
- **[20-async-execution-optimization.md](20-async-execution-optimization.md)** - Parallel execution with blocking flag (TICKET-PERF-001)
- **[28-skill-caching.md](28-skill-caching.md)** - Skill caching and corrective sequences (TICKET-LEARN-001)

### 📝 Technical Notes
- **[16-prompt-cleanup-audit-004.md](16-prompt-cleanup-audit-004.md)** - Prompt engineering audit
- **[18-platform-bridges.md](18-platform-bridges.md)** - Platform-specific integrations

## Technology Stack

**Core:**
- Python 3.8+
- PyAutoGUI - Cross-platform automation
- PyObjC - macOS integration

**AI/ML:**
- OpenAI Whisper - Speech recognition
- LLM Backends: OpenAI GPT, Anthropic Claude, Ollama (local)
- Computer Vision: BLIP-2, CLIP, Tesseract OCR

**Infrastructure:**
- SQLite - Local data persistence
- PySide6 - Configuration UI
- AppleScript - macOS system control

## Version

Current Architecture: **V3 (Multi-Layer OODA Loop Architecture)**
Last Updated: December 2024

