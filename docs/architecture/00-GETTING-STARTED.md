# Getting Started with Janus Architecture

> **New to Janus?** Start here for a quick introduction to the architecture.

## 🎯 Quick Start

Janus is a voice-controlled computer automation agent that uses AI to control your computer through natural language.

**Entry Point:** One simple API
```python
from janus.core import JanusAgent

agent = JanusAgent()
result = await agent.execute("open Calculator and compute 15 + 27")
```

## 📖 Reading Guide

### If you want to...

**Understand the overall system:**
→ Start with **[01-complete-system-architecture.md](01-complete-system-architecture.md)**
- Complete overview with diagrams
- All 6 architecture layers
- Component relationships
- Technology stack

**Use Janus in your code:**
→ Read **[15-janus-agent-api.md](15-janus-agent-api.md)**
- Public API reference
- Code examples
- Configuration options
- Common patterns

**Understand how commands execute:**
→ See **[13-dynamic-react-loop.md](13-dynamic-react-loop.md)** and **[02-unified-pipeline.md](02-unified-pipeline.md)**
- OODA Loop (Observe-Orient-Decide-Act)
- Dynamic execution model
- Visual grounding with Set-of-Marks

**Create a new agent:**
→ Check **[04-agent-architecture.md](04-agent-architecture.md)**
- Agent system design
- Creating custom agents
- Agent interfaces

**Understand the AI reasoning:**
→ Read **[03-llm-first-principle.md](03-llm-first-principle.md)** and **[08-reasoner-v4-think-first.md](08-reasoner-v4-think-first.md)**
- LLM-first philosophy
- Anti-heuristics policy
- Decision making process

## 🏗️ Architecture in 60 Seconds

### The Big Picture
```
Voice/Text → STT → JanusAgent → OODA Loop → Domain Agents → OS
                                     ↓
                                 Memory + Vision + AI
```

### OODA Loop (The Core)
1. **Observe** - Capture screen + system state
2. **Orient** - Analyze context
3. **Decide** - AI chooses ONE next action
4. **Act** - Execute and loop

### Key Components
- **JanusAgent** - Single entry point (public API)
- **ActionCoordinator** - OODA loop orchestrator
- **ReasonerLLM** - AI decision maker
- **Domain Agents** - Execute actions (System, Browser, Files, UI, etc.)
- **VisionEngine** - Set-of-Marks element detection
- **MemoryEngine** - Session and conversation tracking

## 🔑 Key Concepts

### 1. Dynamic Execution
Unlike traditional automation, Janus decides **ONE action at a time** based on what it actually sees on screen.

**Traditional:** Plan all steps → Execute blindly → Fail on unexpected UI
**Janus:** Observe → Decide next step → Act → Observe result → Adapt

### 2. Visual Grounding
No CSS selectors or XPath! Vision engine tags elements with IDs:
```
[1] Button "Submit" at (100, 200)
[2] Input "Email" at (100, 150)
[3] Link "Help" at (50, 300)
```
AI references by ID, executor uses coordinates.

### 3. LLM-First
No regex, no pattern matching. AI understands commands:
```python
# ❌ Traditional: if "click" in command and "button" in command: ...
# ✅ Janus: LLM analyzes context and decides what to do
```

### 4. Multi-Layer Architecture
- **Layer 1:** Input (Voice or Text)
- **Layer 2:** STT (Optional - Whisper)
- **Layer 3:** Orchestration (JanusAgent + ActionCoordinator)
- **Layer 4:** Execution (AgentExecutorV3 + Registry)
- **Layer 5:** Agents (Domain-specific)
- **Layer 6:** OS (PyAutoGUI, AppleScript)

## 📚 Documentation Map

### Core (Read First)
1. [01-complete-system-architecture.md](01-complete-system-architecture.md) - Full overview
2. [15-janus-agent-api.md](15-janus-agent-api.md) - How to use Janus
3. [13-dynamic-react-loop.md](13-dynamic-react-loop.md) - OODA Loop explained

### Components
4. [04-agent-architecture.md](04-agent-architecture.md) - Agent system
5. [17-memory-engine.md](17-memory-engine.md) - Memory & persistence
6. [18-proactive-vision-integration.md](18-proactive-vision-integration.md) - Vision system
7. [19-system-bridge.md](19-system-bridge.md) - OS abstraction

### Advanced
8. [03-llm-first-principle.md](03-llm-first-principle.md) - Design philosophy
9. [12-smart-self-healing.md](12-smart-self-healing.md) - Error recovery
10. [02-unified-pipeline.md](02-unified-pipeline.md) - Pipeline details

### Reference
- [README.md](README.md) - Full documentation index
- [05-data-flow.md](05-data-flow.md) - Data structures
- [06-module-registry.md](06-module-registry.md) - Agent registry

## 🚀 Next Steps

1. **Try it out:** See [../user/README.md](../user/README.md) for installation
2. **Run examples:** Check [../../examples/](../../examples/)
3. **Read architecture:** Start with file 01
4. **Explore code:** Browse [../../janus/](../../janus/)

## 🤔 Common Questions

**Q: Where do I start reading?**
A: Start with [01-complete-system-architecture.md](01-complete-system-architecture.md) for the big picture.

**Q: How do I use Janus in my code?**
A: Read [15-janus-agent-api.md](15-janus-agent-api.md) - it has all the code examples.

**Q: What's the OODA Loop?**
A: It's our execution model. Read [13-dynamic-react-loop.md](13-dynamic-react-loop.md).

**Q: Can I create custom agents?**
A: Yes! See [04-agent-architecture.md](04-agent-architecture.md).

**Q: Is there a diagram of the whole system?**
A: Yes! In [01-complete-system-architecture.md](01-complete-system-architecture.md), section "Complete Architecture Diagram".

## 📞 Need Help?

- **User docs:** [../user/](../user/)
- **Developer docs:** [../developer/](../developer/)
- **Examples:** [../../examples/](../../examples/)
- **Issues:** [GitHub Issues](https://github.com/BenHND/Janus/issues)

---

**Version:** V3 Multi-Layer OODA Loop  
**Last Updated:** December 2024
