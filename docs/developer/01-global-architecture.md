# Global Architecture - The Big Picture

Complete overview of Janus V3 architecture with detailed data flow diagrams.

## 📋 Table of Contents

1. [Architecture V3 Diagram](#architecture-v3-diagram)
2. [LLM-First Principle](#llm-first-principle)
3. [Unified Pipeline - Single-Shot Mode](#unified-pipeline---single-shot-mode)
4. [Component Interactions](#component-interactions)

## Architecture V3 Diagram

### Complete Data Flow: Microphone → STT → Pipeline → Reasoner → Executor → OS

```mermaid
graph TB
    subgraph "1. INPUT PIPELINE"
        A1[Microphone<br/>Audio Input]
        A2[Speech-to-Text Engine<br/>Faster-Whisper CPU]
        A3[Text Normalization<br/>Language Detection]
        A4[Semantic Correction LLM<br/>via Ollama<br/>Neutral Reformulation]
        
        A1 --> A2
        A2 --> A3
        A3 --> A4
    end
    
    subgraph "2. PARSING PIPELINE"
        B1[Text Preprocessing<br/>Light Cleaning<br/>No Heuristics]
        B2[ReasonerLLM V3<br/>Core Logic<br/>JSON Structured Plan]
        B3[Plan Validator V3<br/>JSON Structure Check<br/>Step Coherence]
        
        A4 --> B1
        B1 --> B2
        B2 --> B3
    end
    
    subgraph "3. EXECUTION PIPELINE"
        C1[Global Context<br/>Current App/URL<br/>Domain/Surface UI<br/>Thread ID]
        C2[Agent Executor V3<br/>Execute Steps 1 by 1<br/>No Retries<br/>No Replanning]
        C3[Agents V3<br/>Unified Non-Heuristic]
        C4[Action Execution<br/>Strict Actions<br/>No Magic Logic]
        
        B3 --> C1
        C1 --> C2
        C2 --> C3
        C3 --> C4
    end
    
    subgraph "4. AGENTS V3"
        D1[system<br/>system.open_application]
        D2[browser<br/>browser.open_url]
        D3[messaging<br/>messaging.send_message]
        D4[files<br/>files.read]
        D5[code<br/>code.run_command]
        D6[ui<br/>ui.click]
        D7[llm<br/>llm.summarize]
        D8[crm<br/>crm.add_contact]
        
        C3 --> D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8
    end
    
    subgraph "5. OS INTERFACE"
        E1[MacOSBackend<br/>PyAutoGUI<br/>AppleScript]
        E2[System Actions<br/>Click/Type/Open]
        
        D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 --> E1
        E1 --> E2
    end
    
    subgraph "6. OPTIONAL RECOVERY"
        F1[Vision Lazy Loader<br/>BLIP-2/CLIP<br/>On-Demand Only]
        F2[Vision Cognitive Engine<br/>UI Verification<br/>Error Recovery]
        F3[Recovery Decision<br/>Visual Step Failed → Vision<br/>Else → Error]
        
        C4 -.->|UI Error| F1
        F1 --> F2
        F2 --> F3
        F3 -.-> C2
    end
    
    style B2 fill:#90EE90
    style C2 fill:#FFB6C1
    style F2 fill:#87CEEB
```

### Detailed Pipeline Stages

```mermaid
flowchart TD
    Start([User Voice Command]) --> STT[STT Engine<br/>Whisper/MLX]
    STT --> Norm[Text Normalization<br/>+ Language Detection]
    Norm --> Semantic[Semantic Correction<br/>LLM Optional]
    
    Semantic --> Parse{Parser Type}
    Parse -->|Complex| LLM[ReasonerLLM<br/>Generate JSON Plan]
    Parse -->|Simple| DET[Deterministic NLU<br/>Pattern Fallback]
    
    LLM --> Validate[Plan Validator<br/>Check JSON Structure]
    DET --> Validate
    
    Validate -->|Valid| Context[Global Context<br/>App/URL/Domain]
    Validate -->|Invalid| Error1[Error:<br/>Invalid Plan]
    
    Context --> Executor[Agent Executor V3<br/>Single-Shot]
    
    Executor --> Route{Route to Agent}
    Route --> System[System Agent]
    Route --> Browser[Browser Agent]
    Route --> Files[Files Agent]
    Route --> UI[UI Agent]
    Route --> Other[Other Agents...]
    
    System & Browser & Files & UI & Other --> OSInt[OS Interface<br/>MacOS Backend]
    
    OSInt -->|Success| Memory[Memory Service<br/>Log Results]
    OSInt -->|UI Error| Vision{Vision<br/>Enabled?}
    
    Vision -->|Yes| VisionEngine[Vision Engine<br/>OCR + AI]
    Vision -->|No| Error2[Error:<br/>Action Failed]
    
    VisionEngine -->|Found| Memory
    VisionEngine -->|Not Found| Error2
    
    Memory --> TTS[TTS Feedback<br/>Optional]
    TTS --> End([Result Returned])
    Error1 & Error2 --> End
    
    style LLM fill:#90EE90
    style Executor fill:#FFB6C1
    style VisionEngine fill:#87CEEB
```

## LLM-First Principle

### The Anti-Heuristics Policy

**Core Rule: ZERO heuristics, ZERO regex, ZERO pattern matching.**

```mermaid
graph LR
    subgraph "❌ OLD: Heuristic Approach"
        H1[User: 'ouvre Chrome'] --> H2{if 'ouvre' in text}
        H2 --> H3[action = 'open']
        H3 --> H4{if 'Chrome' in text}
        H4 --> H5[app = 'Chrome']
    end
    
    subgraph "✅ NEW: LLM-First"
        L1[User: 'ouvre Chrome'] --> L2[ReasonerLLM]
        L2 --> L3[Understand Intent:<br/>'ouvre' = open<br/>'Chrome' = app name]
        L3 --> L4[Generate Plan:<br/>system.open_application<br/>params: app_name='Chrome']
    end
    
    style H1 fill:#FFB6C1
    style L1 fill:#90EE90
```

### Why LLM-First?

| Traditional Heuristics | LLM-First Approach |
|----------------------|-------------------|
| ❌ Brittle patterns | ✅ Natural understanding |
| ❌ Manual maintenance | ✅ Auto-adaptive |
| ❌ Language-specific | ✅ Multi-language native |
| ❌ Context-blind | ✅ Context-aware |
| ❌ Fails on variations | ✅ Handles variations naturally |

**Example:**
```
Traditional fails on:
- "launch Chrome" (not "open")
- "bring up Chrome" (not "open")
- "ouvre Chrome" (French)
- "lance Chrome" (French)

LLM understands ALL variations without code changes!
```

## Unified Pipeline - Single-Shot Mode

### Single-Shot Execution Model

```mermaid
stateDiagram-v2
    [*] --> Listening: Voice Input
    Listening --> Processing: Audio Captured
    Processing --> Reasoning: Text Parsed
    Reasoning --> Planning: Intent Understood
    Planning --> Executing: Plan Validated
    Executing --> Success: Action Complete
    Executing --> Failed: Action Error
    Success --> [*]
    Failed --> [*]
    
    note right of Executing
        NO AUTOMATIC RETRIES
        NO REPLANNING
        Single-Shot Execution
    end note
```

### Why Single-Shot?

1. **Predictability**: User knows exactly what happens
2. **Speed**: No retry delays
3. **Clarity**: Clear success or failure
4. **Safety**: No unintended repeated actions

### Pipeline Flow Timing

```mermaid
gantt
    title Janus Pipeline Timing (Apple Silicon M1/M2)
    dateFormat  X
    axisFormat  %L ms
    
    section Input
    Voice Capture       :0, 500
    STT (Whisper)      :500, 1500
    
    section Processing
    Text Normalization  :1500, 50
    Semantic Correction :1550, 1000
    
    section Reasoning
    LLM Reasoning      :2550, 2000
    Plan Validation    :4550, 50
    
    section Execution
    Context Gathering  :4600, 100
    Agent Execution    :4700, 500
    
    section Output
    Memory Logging     :5200, 50
    TTS Feedback       :5250, 500
```

**Total latency: ~5-6 seconds** (voice to completion with LLM)

## Component Interactions

### ReasonerLLM V3 - The Core Logic

```mermaid
graph TB
    subgraph "ReasonerLLM V3"
        R1[Input: Raw Text + Context]
        R2[Jinja2 Prompt Template<br/>prompts/reasoner_system.jinja2]
        R3[LLM Backend<br/>Ollama: qwen2.5:7b-instruct<br/>or OpenAI: gpt-4]
        R4[JSON Mode Generation<br/>Structured Output]
        R5[Parse & Validate JSON<br/>Ensure V3 Format]
        R6[Output: ActionPlan<br/>with Steps]
        
        R1 --> R2
        R2 --> R3
        R3 --> R4
        R4 --> R5
        R5 --> R6
    end
    
    R6 --> Exec[Agent Executor V3]
```

### Agent Executor V3 - The Orchestrator

```mermaid
sequenceDiagram
    participant Plan as ActionPlan
    participant Executor as AgentExecutor V3
    participant Router as Agent Router
    participant Agent as Specific Agent
    participant OS as OS Interface
    participant Memory as Memory Service
    
    Plan->>Executor: Execute Plan
    
    loop For each step in plan
        Executor->>Router: Route step.action
        Router->>Agent: Determine agent by prefix
        Agent->>Agent: Validate action + params
        Agent->>OS: Execute via OSInterface
        OS->>Agent: Action result
        Agent->>Executor: Return result
        
        alt Action Failed & is UI
            Executor->>Vision: Try vision recovery
            Vision->>Executor: Recovery result
        end
        
        Executor->>Memory: Log step result
        
        alt Step Failed
            Executor->>Plan: Stop execution
        end
    end
    
    Executor->>Memory: Log final result
    Executor->>Plan: Return ExecutionResult
```

### Vision System Integration

```mermaid
graph TB
    subgraph "Vision Lazy Loading"
        V1{Vision Needed?}
        V2[Load Florence-2<br/>3GB Model]
        V3[Load BLIP-2<br/>4GB Model]
        V4[Vision Engine Ready]
        
        V1 -->|Yes| V2 & V3
        V2 & V3 --> V4
        V1 -->|No| V5[Skip Vision]
    end
    
    subgraph "Vision Recovery Flow"
        W1[UI Action Failed]
        W2[Capture Screenshot]
        W3[OCR Text Extraction]
        W4[AI Vision Analysis<br/>Florence-2]
        W5[Element Location]
        W6[Click Coordinates]
        
        W1 --> W2
        W2 --> W3
        W3 --> W4
        W4 --> W5
        W5 --> W6
    end
    
    V4 --> W1
```

## Key Technical Decisions

### 1. LLM-First (2024 - V3)
**Why:** Traditional heuristics require constant maintenance and break easily. LLMs provide natural understanding without code changes.

### 2. Single-Shot Execution
**Why:** Automatic retries and replanning add complexity and unpredictability. Users prefer clarity over "smart" but confusing behavior.

### 3. Lazy Loading for AI Models
**Why:** Startup time optimization. Whisper, Vision, and LLM models load only when first needed.

### 4. Agent-Based Architecture
**Why:** Clear domain boundaries. Each agent validates and executes actions in its domain without cross-contamination.

### 5. Vision as Recovery Only
**Why:** Vision is slow (500-2000ms). Use standard automation first, vision only when UI automation fails.

---

**Next**: [Development Environment Setup](02-development-environment.md)
