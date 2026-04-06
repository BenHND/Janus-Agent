# MemoryEngine: Unified Memory System

> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---


- Single Memory System for Janus

## Overview

MemoryEngine replaces 6 fragmented memory systems with a single, unified API:

**Replaced Systems:**
1.   MemoryService   → MemoryEngine (SQLite persistence)
2.   UnifiedMemory/UnifiedMemoryManager   → MemoryEngine (facade layer)
3.   ContextMemory   → MemoryEngine (context tracking)
4.   ConversationManager   → MemoryEngine (conversations)
5.   SessionContext   → MemoryEngine (short-term memory)
6.   UnifiedStore   → MemoryEngine (persistence backend)

## Why MemoryEngine?

**Before (6 systems):**
- Confusing: Which system to use when?
- Duplicated data across systems
- Multiple DB accesses hurting performance
- Inconsistent APIs

**After (1 system):**
- Clear: One system for all memory
- Single source of truth
- One DB access
- Simple, consistent API (<10 methods)

## Core API (11 Methods - Token-Aware by Default)

> **NEW in TICKET-MEM-001:** Semantic memory with vector-based search for natural language reference resolution. See [Semantic Memory Guide](../SEMANTIC_MEMORY.md) for detailed documentation.

> **BREAKING CHANGE in TICKET-LLM-001:** `get_history()` and `get_context()` now use token-aware retrieval by default (max_tokens parameter instead of limit). This prevents LLM context overflow when handling large text. See [Token-Aware Context Management](../TOKEN_AWARE_CONTEXT.md) for migration guide.

### 1. store(key, value) - Store Any Data
```python
from janus.core import MemoryEngine

memory = MemoryEngine()

# Store simple values
memory.store("user_name", "John")
memory.store("config", {"theme": "dark", "lang": "en"})
memory.store("tasks", ["task1", "task2", "task3"])
```

### 2. retrieve(key, default) - Retrieve Data
```python
# Retrieve with optional default
name = memory.retrieve("user_name")  # "John"
theme = memory.retrieve("config")["theme"]  # "dark"
missing = memory.retrieve("nonexistent", "default_value")  # "default_value"
```

### 3. add_context(type, data) - Add Contextual Information
```python
# Track user actions
memory.add_context("user_action", {
    "action": "click",
    "target": "submit_button",
    "timestamp": "2024-01-01T12:00:00"
})

# Track app state
memory.add_context("app_state", {
    "app": "Safari",
    "url": "https://github.com",
    "title": "GitHub"
})

# Track intent
memory.add_context("intent", {
    "intent": "open_file",
    "confidence": 0.95,
    "parameters": {"file_path": "/path/to/file.txt"}
})
```

### 4. get_context(max_tokens, filters) - Get Recent Context (Token-Aware)

**TICKET-LLM-001:** Default behavior is now token-aware to prevent LLM context overflow.

```python
# Get context within token budget (default: 2000 tokens)
recent = memory.get_context(max_tokens=2000)

# Filter by type
actions = memory.get_context(max_tokens=1000, context_type="user_action")

# Filter by relevance
important = memory.get_context(max_tokens=500, min_relevance=0.8)

# Each context item has:
# - type: context type
# - data: context data
# - timestamp: when it was added
# - relevance: relevance score (with temporal decay)
```

> **Important:** `get_context()` now uses token-aware retrieval by default. It stacks items from newest to oldest, stopping when the token budget is reached. This prevents LLM context overflow. See [Token-Aware Context Management](../TOKEN_AWARE_CONTEXT.md) for details.

### 5. record_action(type, data, result) - Record Actions
```python
# Record commands
memory.record_action("command", {
    "command": "open Safari",
    "intent": "open_app",
    "parameters": {"app_name": "Safari"}
}, result={"status": "success"})

# Record clicks
memory.record_action("click", {
    "x": 100,
    "y": 200,
    "target": "button"
})

# Record copies
memory.record_action("copy", {
    "content": "copied text",
    "source": "Safari"
})
```

### 6. get_history(max_tokens, type) - Get Action History (Token-Aware)

**TICKET-LLM-001:** Default behavior is now token-aware to prevent LLM context overflow.

```python
# Get history within token budget (default: 4000 tokens)
history = memory.get_history(max_tokens=4000)

# Filter by action type
commands = memory.get_history(max_tokens=2000, action_type="command")

# Use smaller budget for quick operations
recent = memory.get_history(max_tokens=500)

# Each history item has:
# - type: action type
# - data: action data
# - result: execution result (if any)
# - timestamp: when it was recorded
```

> **Important:** `get_history()` now uses token-aware retrieval by default. It stacks messages from newest to oldest, stopping when the token budget is reached. This prevents crashes when users paste large amounts of text. See [Token-Aware Context Management](../TOKEN_AWARE_CONTEXT.md) for details.

### 7. start_conversation() - Start Multi-Turn Conversation
```python
# Start a conversation
conv_id = memory.start_conversation()

# Add turns
memory.add_conversation_turn(conv_id, 
    user_input="Hello, open Safari",
    system_response="Opening Safari..."
)

memory.add_conversation_turn(conv_id,
    user_input="Now go to GitHub", 
    system_response="Navigating to GitHub"
)

# Get conversation history
turns = memory.get_conversation_history(conv_id)
# [{"turn_number": 1, "user_input": "...", "system_response": "...", "timestamp": "..."}, ...]
```

### 8. end_conversation(id, reason) - End Conversation
```python
# End normally
memory.end_conversation(conv_id, reason="completed")

# End due to timeout
memory.end_conversation(conv_id, reason="timeout")

# End due to error
memory.end_conversation(conv_id, reason="error")
```

### 9. resolve_reference(ref) - Resolve "it", "that", etc.

**ENHANCED in TICKET-MEM-001:** Now uses semantic search as fallback for natural language queries.

```python
# Record some actions first
memory.record_action("copy", {"content": "test data"})
memory.record_action("click", {"x": 100, "y": 200})
memory.record_action("open_app", {"app_name": "Safari"})
memory.record_action("open_file", {"file_path": "/path/to/report.pdf"})

# Exact keyword matching (original behavior)
memory.resolve_reference("it")        # "test data" (last copied)
memory.resolve_reference("that")      # "test data"
memory.resolve_reference("here")      # (100, 200) (last click)
memory.resolve_reference("that app")  # "Safari"
memory.resolve_reference("the file")  # "/path/to/report.pdf"

# NEW: Natural language resolution via semantic search
memory.resolve_reference("the PDF we opened earlier")  # → "/path/to/report.pdf"
memory.resolve_reference("le fichier PDF")            # → "/path/to/report.pdf"
memory.resolve_reference("the browser application")   # → "Safari"
```

> **Note:** Semantic search requires `chromadb` and `sentence-transformers`. Install with: `pip install chromadb sentence-transformers`

### 10. search_semantic(query, limit) - Semantic Search

**NEW in TICKET-MEM-001:** Search action history using natural language queries.

```python
# Initialize with semantic memory enabled
memory = MemoryEngine(enable_semantic_memory=True)

# Record various actions
memory.record_action("open_file", {"file_path": "/docs/budget_2024.xlsx"})
memory.record_action("open_file", {"file_path": "/docs/report.pdf"})
memory.record_action("open_app", {"app_name": "Safari"})

# Search using natural language
results = memory.search_semantic("PDF document", limit=5)
# Returns: [{"id": "...", "type": "open_file", "data": {...}, 
#            "description": "Opened report.pdf file...", 
#            "similarity": 0.92}]

# Multi-lingual search
results = memory.search_semantic("le fichier budget", limit=3)

# Temporal queries
results = memory.search_semantic("the file we opened earlier", limit=1)

# Each result includes:
# - id: Action ID
# - type: Action type
# - data: Action data
# - description: Human-readable description
# - timestamp: When action occurred
# - similarity: Similarity score (0.0-1.0)
```

> **Requirements:** `chromadb>=0.4.0` and `sentence-transformers>=2.2.0`  
> **Performance:** ~50-200ms per query, ~10-50ms per action vectorization  
> **Storage:** ~1KB per action

### 11. cleanup(days_old) - Clean Up Old Data
```python
# Clean up data older than 7 days (default)
stats = memory.cleanup(days_old=7)
# {"context_deleted": 45, "history_deleted": 102, "storage_deleted": 0}

# Clean up data older than 30 days
stats = memory.cleanup(days_old=30)

# Clean up only current session
stats = memory.cleanup(days_old=7, session_id=memory.session_id)
```

## Semantic Memory (TICKET-MEM-001)

> **Detailed Documentation:** See [Semantic Memory Guide](../SEMANTIC_MEMORY.md) for complete technical details, examples, and troubleshooting.

### Overview

Semantic memory adds vector-based search to MemoryEngine, enabling natural language reference resolution beyond exact keyword matching.

**Key Features:**
- **Vector Database**: ChromaDB for persistent semantic search
- **Auto-Vectorization**: Actions automatically embedded using sentence-transformers
- **Multi-lingual**: Supports English, French, and other languages
- **Smart Fallback**: Semantic search when exact keywords don't match
- **Optional**: Can be disabled with `enable_semantic_memory=False`

### Quick Start

```python
from janus.core.memory_engine import MemoryEngine

# Enable semantic memory (requires dependencies)
memory = MemoryEngine("my_memory.db", enable_semantic_memory=True)

# Record actions - automatically vectorized
memory.record_action("open_file", {"file_path": "/docs/report.pdf"})

# Later: resolve using natural language
result = memory.resolve_reference("the PDF we opened earlier")
# → "/docs/report.pdf"

# Or search directly
results = memory.search_semantic("PDF document", limit=5)
```

### How It Works

1. **Action Recording**: When `record_action()` is called, the action is:
   - Stored in SQLite (standard behavior)
   - Converted to human-readable description (e.g., "Opened report.pdf file")
   - Vectorized using all-MiniLM-L6-v2 embedding model
   - Stored in ChromaDB with metadata

2. **Reference Resolution**: When `resolve_reference()` is called:
   - First tries exact keyword matching ("it", "that", "here")
   - If no match, falls back to semantic search
   - Returns the most semantically similar action data

3. **Semantic Search**: `search_semantic()` directly queries the vector database
   - Embeds the query using the same model
   - Finds most similar action descriptions
   - Returns ranked results with similarity scores

### Installation

```bash
pip install chromadb sentence-transformers
```

Or add to `requirements.in`:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

### Configuration

```python
# Enable semantic memory (default if dependencies installed)
memory = MemoryEngine(enable_semantic_memory=True)

# Disable semantic memory (fallback to keyword matching only)
memory = MemoryEngine(enable_semantic_memory=False)
```

### Graceful Degradation

If dependencies are not installed:
- MemoryEngine initializes normally
- `record_action()` works but doesn't vectorize
- `search_semantic()` returns empty list with warning
- `resolve_reference()` uses exact keywords only
- No crashes or errors

### Performance

- **Model Loading**: ~5-10 seconds first time (cached afterward)
- **Action Vectorization**: ~10-50ms per action
- **Semantic Search**: ~50-200ms per query
- **Storage Overhead**: ~1KB per action (embedding + metadata)
- **Model Size**: ~80MB (all-MiniLM-L6-v2)

### Examples

#### Example 1: Temporal Reference
```python
# User opens a file
memory.record_action("open_file", {"file_path": "/docs/report.pdf"})

# Much later...
memory.record_action("open_app", {"app_name": "Safari"})
memory.record_action("copy", {"content": "some text"})

# User asks for "the PDF from earlier"
result = memory.resolve_reference("the PDF from earlier")
# → "/docs/report.pdf"
```

#### Example 2: Multi-lingual
```python
memory.record_action("open_file", {"file_path": "/docs/budget_2024.xlsx"})

# French query
result = memory.resolve_reference("le fichier budget")
# → "/docs/budget_2024.xlsx"

# Or search in French
results = memory.search_semantic("le fichier d'hier", limit=5)
```

#### Example 3: Semantic vs Keyword
```python
# Exact keywords still work (fast path)
memory.record_action("copy", {"content": "test"})
memory.resolve_reference("it")  # → "test" (keyword match, no search)

# Natural language uses semantic search (fallback)
memory.record_action("open_file", {"file_path": "/report.pdf"})
memory.resolve_reference("the PDF we saw")  # → semantic search → "/report.pdf"
```

### Acceptance Criteria (TICKET-MEM-001)

✅ **Requirement:** User opens "report.pdf". Later says "Renvoie le PDF qu'on a vu tout à l'heure" (Return the PDF we saw earlier). Agent retrieves "report.pdf".

**Implementation:**
```python
# Step 1: User opens report.pdf
memory.record_action("open_file", {"file_path": "/docs/report.pdf"})

# Step 2: Some time passes, other actions...
memory.record_action("open_app", {"app_name": "Safari"})
memory.record_action("copy", {"content": "some text"})

# Step 3: User asks in French
result = memory.resolve_reference("le PDF qu'on a vu tout à l'heure")

# Result: "/docs/report.pdf" or action data containing it
assert "report.pdf" in str(result).lower()  # ✅ Pass
```

### Technical Details

**Embedding Model:** sentence-transformers/all-MiniLM-L6-v2
- Lightweight (80MB)
- Fast inference (~10-50ms)
- Multi-lingual support
- Good quality/performance balance

**Vector Storage:** ChromaDB
- Persistent local storage
- Stored in `{db_path}_chroma/` directory
- Includes metadata (action type, data, timestamp)
- Efficient similarity search

**Action Descriptions:**
- `open_file`: "Opened report.pdf file at /path/to/report.pdf"
- `open_app`: "Opened Safari application"
- `open_url`: "Opened website https://github.com"
- `copy`: "Copied text: [content preview]"
- `click`: "Clicked on button at position (100, 200)"

### Troubleshooting

**Model not downloading?**
- Check internet connection
- Pre-download: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"`
- Model cached in `~/.cache/huggingface/`

**ChromaDB errors?**
- Delete chroma directory: `rm -rf /path/to/janus_memory_chroma/`
- Collection recreated on next initialization

**Slow performance?**
- First run downloads model (~80MB)
- Subsequent runs use cached model
- Consider `enable_semantic_memory=False` if not needed

### Security

✅ **CodeQL Scan:** Passed with 0 vulnerabilities  
✅ **Dependencies:** chromadb and sentence-transformers - no known vulnerabilities  
✅ **Privacy:** All processing local, no cloud dependencies  

## Session Management

```python
# Create new session
new_session_id = memory.create_session()

# Switch between sessions
memory.switch_session(other_session_id)

# Store data in specific session
memory.store("key", "value", session_id=specific_session)

# Get statistics
stats = memory.get_statistics()
# {
#   "total_sessions": 5,
#   "context_items": 120,
#   "history_items": 450,
#   "stored_items": 23,
#   "active_conversations": 1,
#   "db_size_mb": 1.2
# }
```

## Migration Guide

### From MemoryService

```python
# OLD (MemoryService)
from janus.core import MemoryEngine, DatabaseSettings

settings = DatabaseSettings(path="janus.db")
memory = MemoryEngine(settings)
memory.create_session()
memory.store_command(session_id, request_id, command, intent)
memory.get_command_history(session_id)

# NEW (MemoryEngine)
from janus.core import MemoryEngine

memory = MemoryEngine("janus_memory.db")
memory.record_action("command", {"command": command, "intent": intent})
memory.get_history(limit=50, action_type="command")
```

### From ContextMemory

```python
# OLD (ContextMemory)
from janus.reasoning import ContextMemory

context = ContextMemory()
context.add_command(command_text, intent, parameters, result)
context.get_context("last_app")

# NEW (MemoryEngine)
from janus.core import MemoryEngine

memory = MemoryEngine()
memory.add_context("command", {"command": command_text, "intent": intent})
memory.resolve_reference("last app")
```

### From ConversationManager

```python
# OLD (ConversationManager)
from janus.core import ConversationManager, MemoryService

conv_mgr = ConversationManager(memory_service)
conv = conv_mgr.start_conversation(session_id)
conv_mgr.add_turn(conv_id, command, intent, result)
conv_mgr.complete_conversation(conv_id)

# NEW (MemoryEngine)
from janus.core import MemoryEngine

memory = MemoryEngine()
conv_id = memory.start_conversation()
memory.add_conversation_turn(conv_id, command, system_response)
memory.end_conversation(conv_id)
```

### From SessionContext

```python
# OLD (SessionContext)
from janus.memory import SessionContext

session = SessionContext()
session.record_command(command, intent, params, result)
session.record_copy(content, source)
session.resolve_reference("it")

# NEW (MemoryEngine)
from janus.core import MemoryEngine

memory = MemoryEngine()
memory.record_action("command", {"command": command, "intent": intent})
memory.record_action("copy", {"content": content, "source": source})
memory.resolve_reference("it")
```

### From UnifiedStore

```python
# OLD (UnifiedStore)
from janus.persistence import UnifiedStore

store = UnifiedStore("store.db")
store.add_clipboard_entry(content, content_type)
store.get_clipboard_history(limit=50)

# NEW (MemoryEngine)
from janus.core import MemoryEngine

memory = MemoryEngine()
memory.record_action("copy", {"content": content, "type": content_type})
memory.get_history(limit=50, action_type="copy")
```

## Performance Benefits

### Previous Approach: (6 systems)
```python
# Multiple DB accesses for one operation
memory_service.store_command(...)  # DB write #1
context_memory.add_command(...)    # DB write #2
session_context.record_command(...) # In-memory only
unified_store.save_context(...)    # DB write #3
conv_manager.add_turn(...)         # DB write #4
```

### Current Approach: (1 system)
```python
# Single DB access
memory.record_action("command", {...})  # DB write #1 (only)
# Context, session tracking, and history all updated in one transaction
```

**Performance improvement:** ~75% reduction in DB operations

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              MemoryEngine                             │
│       Simple 11-method public API                    │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Storage  │  │ Context  │  │ Semantic │         │
│  │ (K-V)    │  │ (Decay)  │  │ (Vector) │  NEW!  │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                       │
│  ┌──────────┐  ┌──────────┐                        │
│  │ History  │  │  Convo   │                        │
│  │ (Actions)│  │ (Turns)  │                        │
│  └──────────┘  └──────────┘                        │
│                                                       │
├──────────────────────────────────────────────────────┤
│      Single SQLite Database          ChromaDB       │
│  (WAL mode, thread-safe, indexed)   (Vector Store)  │
└──────────────────────────────────────────────────────┘

Components:
  • Storage: Key-value persistence
  • Context: Temporal context with decay
  • History: Action recording and retrieval
  • Conversations: Multi-turn dialogue tracking
  • Semantic (NEW): Vector-based semantic search
    - Auto-vectorization of actions
    - Natural language query support
    - Multi-lingual reference resolution
```

## Best Practices

1. **Use MemoryEngine for everything** - Don't mix old and new systems
2. **One engine per application** - Reuse the same instance
3. **Session isolation** - Use separate sessions for different contexts
4. **Regular cleanup** - Call `cleanup()` periodically
5. **Relevance scoring** - Use context relevance for intelligent retrieval
6. **Semantic memory** (TICKET-MEM-001):
   - Enable for natural language reference resolution
   - Disable (`enable_semantic_memory=False`) for minimal installations
   - Install dependencies: `pip install chromadb sentence-transformers`
   - First run downloads ~80MB model (one-time, then cached)
7. **Token-aware by default** (TICKET-LLM-001):
   - `get_history()` and `get_context()` now use max_tokens parameter
   - Prevents context window overflow with large text inputs automatically
   - Default budgets: 4000 tokens for history, 2000 tokens for context
   - Adjust max_tokens based on your LLM's context window
   - See [Token-Aware Context Management](../TOKEN_AWARE_CONTEXT.md) for guidelines

## Thread Safety

MemoryEngine is thread-safe:

```python
import threading
from janus.core import MemoryEngine

memory = MemoryEngine()

def worker(i):
    memory.store(f"key{i}", f"value{i}")
    memory.record_action("work", {"worker": i})

threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# All data safely stored
```

## Examples

### Example 1: Command Execution with Context

```python
memory = MemoryEngine()

# User: "Open Safari"
memory.record_action("command", {"command": "open Safari"})
memory.add_context("app_state", {"app": "Safari", "state": "open"})

# User: "Go to GitHub" (implicit: in Safari)
last_app = memory.resolve_reference("that app")  # "Safari"
memory.record_action("command", {"command": "go to GitHub", "app": last_app})
```

### Example 2: Multi-Turn Conversation

```python
memory = MemoryEngine()
conv_id = memory.start_conversation()

# Turn 1
memory.add_conversation_turn(conv_id, 
    "Find the CEO's email on LinkedIn",
    "Searching LinkedIn..."
)

# Turn 2
memory.add_conversation_turn(conv_id,
    "Copy it to clipboard",
    "Copied: ceo@company.com"
)
memory.record_action("copy", {"content": "ceo@company.com"})

# Turn 3
memory.add_conversation_turn(conv_id,
    "Paste it in Salesforce",
    "Pasted in Salesforce contact field"
)

# End conversation
memory.end_conversation(conv_id, "completed")

# Review conversation
turns = memory.get_conversation_history(conv_id)
```

### Example 3: Cross-Window Data Passing

```python
memory = MemoryEngine()

# Window 1: LinkedIn
memory.record_action("extract", {
    "source": "LinkedIn",
    "field": "CEO name",
    "value": "John Smith"
})
memory.store("ceo_name", "John Smith")

# Window 2: Salesforce
ceo_name = memory.retrieve("ceo_name")
memory.record_action("fill", {
    "destination": "Salesforce",
    "field": "Contact Name",
    "value": ceo_name
})
```

## FAQ

**Q: What is MemoryEngine?**  
A: MemoryEngine is the unified memory system that consolidates all memory operations.

**Q: What happens to my existing data?**  
A: MemoryEngine uses a new schema. Migration scripts are provided.

**Q: How do I migrate my code?**  
A: See the Migration Guide section above.

**Q: Is MemoryEngine faster?**  
A: Yes, ~75% fewer DB operations and single transaction model.

**Q: Can I use MemoryEngine with the old systems?**  
A: Not recommended. Choose one or the other to avoid data inconsistency.

## See Also

- **[Token-Aware Context Management](../TOKEN_AWARE_CONTEXT.md)** - Prevent LLM context overflow (TICKET-LLM-001)
- **[Semantic Memory Guide](../SEMANTIC_MEMORY.md)** - Complete semantic memory documentation (TICKET-MEM-001)
- [Architecture Audit](../old/development/ARCHITECTURE_AUDIT_COMPREHENSIVE_EN.md)
- [Unified Pipeline](02-unified-pipeline.md)
- [API Reference](15-janus-agent-api.md)
- [Complete System Architecture](01-complete-system-architecture.md)
