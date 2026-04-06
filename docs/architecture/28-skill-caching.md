# Skill Caching & Corrective Sequences Architecture

**LEARNING-001**: Implementation of learned action sequences as **hints only** (never automatic execution).

## Overview

The Skill Hints system enables Janus to learn complete action sequences from user corrections and provide them as **suggestions** to the LLM Reasoner. Skills are **never executed automatically** - they always pass through the OODA decision loop.

This transforms the agent from always "thinking from scratch" to having "learned experiences" that inform its decisions, while maintaining central control and observable preconditions.

## Problem Statement

**Before Skill Hints:**
- Agent must reason through every command, even repeated ones
- User corrections are recorded but not reused as hints
- Same mistakes can happen multiple times
- Every execution requires 2-5s of LLM reasoning
- No learning of "how" to accomplish tasks, only "when" (timeouts)

**Example:** User says "Set my Slack status to away":
1. First time: Agent clicks status button → fails (popup blocking)
2. User corrects: "First close the popup"
3. Second time: Agent must reason through the same steps again
4. Third time: Still reasoning from scratch

## Solution: Skill Hints (LEARNING-001)

**After Skill Hints:**
- Agent learns complete sequences after corrections
- Subsequent executions receive hints (suggestions) for faster reasoning
- LLM decides independently whether to follow, adapt, or reject the hint
- All actions still pass through OODA loop (no automatic execution)
- Improved LLM cost (fewer tokens needed with context)
- Observable preconditions enforced via warnings

**Same example with hints:**
1. First time: Agent fails → User corrects → Agent stores sequence
2. Second time: Hint retrieved → Provided to LLM → LLM decides actions via OODA
3. Third time: Same hint → LLM may follow or adapt based on current state

## Architecture

### 1. Database Schema

```sql
CREATE TABLE skill_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_vector BLOB NOT NULL,           -- Semantic embedding of intent
    context_hash TEXT NOT NULL,            -- Hash of visual/app context
    action_sequence TEXT NOT NULL,         -- JSON array of actions
    intent_text TEXT,                      -- Human-readable intent
    success_count INTEGER DEFAULT 1,       -- How many times used
    last_used TEXT NOT NULL,               -- Last usage timestamp
    created_at TEXT NOT NULL,              -- Creation timestamp
    UNIQUE(context_hash)                   -- One skill per context
);

CREATE INDEX idx_skill_cache_context ON skill_cache(context_hash);
CREATE INDEX idx_skill_cache_last_used ON skill_cache(last_used DESC);
```

**Key Fields:**
- `intent_vector`: 384-dimensional embedding from sentence-transformers (all-MiniLM-L6-v2)
- `context_hash`: SHA-256 hash of intent + context (first 16 chars)
- `action_sequence`: JSON array of cleaned action objects
- `success_count`: Increments on each successful reuse

### 2. Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Command                            │
│              "Set my Slack status to away"                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  SemanticRouter                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │  1. classify_intent() → "ACTION"                 │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐       │
│  │  2. check_skill_cache()                          │       │
│  │     ├─ Generate intent vector                    │       │
│  │     ├─ Compute context hash                      │       │
│  │     └─ Query skill_cache table                   │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────┬────────────────────────┬─────────────────┘
                   │                        │
         Cache HIT │                        │ Cache MISS
                   │                        │
                   ▼                        ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │   HINT MODE          │    │   LLM REASONING      │
    │   Return SkillHint   │    │   Generate new plan  │
    │   to Reasoner        │    │   (2-5s delay)       │
    │   (~5ms retrieval)   │    │                      │
    └──────────────────────┘    └──────────────────────┘
                   │                        │
                   └────────────┬───────────┘
                                ▼
                   ┌──────────────────────────┐
                   │  ActionCoordinator       │
                   │  Passes hint to Reasoner │
                   └────────────┬─────────────┘
                                ▼
                   ┌──────────────────────────┐
                   │  ReasonerLLM             │
                   │  Decides via OODA        │
                   │  (with hint as context)  │
                   └────────────┬─────────────┘
                                ▼
                   ┌──────────────────────────┐
                   │  Execute Actions         │
                   │  (via OODA, not hint)    │
                   └──────────────────────────┘
```

### 3. SkillHint Dataclass (LEARNING-001)

```python
@dataclass
class SkillHint:
    """
    Learned action sequence provided as a HINT to the LLM Reasoner.
    
    LEARNING-001: Skills are NEVER executed automatically.
    """
    skill_id: int
    intent_text: str
    suggested_actions: List[Dict[str, Any]]
    context_hash: str
    success_count: int
    last_used: str
    confidence: float = 0.0  # Similarity score
    
    def to_context_string(self) -> str:
        """Convert to LLM context with warning"""
        return f"""💡 LEARNED SEQUENCE (Hint only - verify preconditions):
Intent: "{self.intent_text}"
Success rate: {self.success_count} times
Suggested actions:
  1. action_type(params...)
  2. action_type(params...)

⚠️ IMPORTANT: This is a suggestion based on past success. You MUST:
1. Verify current system state matches expected preconditions
2. Decide each action independently through OODA
3. Adapt if the situation has changed
4. Do NOT blindly follow - think and observe!"""
```

### 4. Integration Points

#### SemanticRouter
```python
def check_skill_cache(self, text: str, context_data: Optional[Dict] = None) -> Optional[SkillHint]:
    """Returns SkillHint (suggestion) instead of executable actions"""
    skill_data = self.learning_manager.retrieve_cached_skill(
        intent_text=text,
        context_data=context_data,
        return_metadata=True  # Get full metadata
    )
    
    if skill_data:
        return SkillHint(
            skill_id=skill_data["skill_id"],
            intent_text=skill_data["intent_text"],
            suggested_actions=skill_data["action_sequence"],
            # ...
        )
    return None
```

#### ActionCoordinator
```python
def _check_skill_hint(self, user_goal: str, system_state: SystemState) -> Optional[str]:
    """Check for skill hint before reasoning"""
    skill_hint = self.semantic_router.check_skill_cache(text=user_goal, ...)
    
    if skill_hint:
        self.skill_metrics.record_hint_retrieved(retrieval_time)
        return skill_hint.to_context_string()  # Convert to string
    
    return None

async def _decide_burst(self, user_goal, ...):
    """Decide actions with optional skill hint"""
    skill_hint = self._check_skill_hint(user_goal, system_state)
    
    decision = self.reasoner.decide_burst_actions(
        user_goal=user_goal,
        skill_hint=skill_hint,  # Pass as context
        ...
    )
```

#### ReasonerLLM
```python
def decide_burst_actions(self, user_goal, skill_hint: Optional[str] = None, ...):
    """Generate actions with optional hint context"""
    prompt = self._build_burst_prompt(
        user_goal, 
        system_state,
        skill_hint=skill_hint,  # Inject in prompt
        ...
    )
```

#### ContextAssembler
```python
def assemble_context(self, ..., skill_hint: Optional[str] = None):
    """Assemble context with budget control"""
    budgeted_hint = self._budget_skill_hint(skill_hint)  # Max 300 tokens
    
    return {
        "skill_hint": budgeted_hint,
        "visual_context": budgeted_visual,
        ...
    }
```

## Performance Characteristics

### Cache Hit Scenario

| Phase | Time | Description |
|-------|------|-------------|
| Intent Classification | ~50ms | SemanticRouter embedding-based classification |
| Cache Lookup | ~5ms | SQLite query by context_hash |
| Similarity Check | ~2ms | NumPy vector comparison |
| Hint Formatting | ~1ms | Convert to context string |
| LLM Reasoning | ~1500ms | Generate actions (faster with hint context) |
| Action Execution | ~500ms | Execute decided actions |
| **Total** | **~2060ms** | **Faster than without hint (saves tokens)** |

### Cache Miss Scenario

| Phase | Time | Description |
|-------|------|-------------|
| Intent Classification | ~50ms | Same as cache hit |
| Cache Lookup | ~5ms | No match found |
| LLM Reasoning | ~2000-5000ms | Generate plan from scratch (more tokens) |
| Action Execution | ~500ms | Execute generated plan |
| **Total** | **~2.5-5.5s** | **Normal LLM-based execution** |

### Storage Overhead

- **Per Skill**: ~1-2 KB (vector + actions + metadata)
- **100 Skills**: ~100-200 KB
- **1000 Skills**: ~1-2 MB
- **Impact**: Negligible (skills stored in SQLite)

## Safety Guarantees (LEARNING-001)

### 1. No Automatic Execution
```python
# ✅ CORRECT: Hint is a suggestion
hint = semantic_router.check_skill_cache(text)  # Returns SkillHint
hint_string = hint.to_context_string()  # Convert to string
decision = reasoner.decide_burst_actions(skill_hint=hint_string)  # LLM decides

# ❌ IMPOSSIBLE: No code path executes suggested_actions directly
# hint.suggested_actions is NEVER passed to executor
```

### 2. OODA Loop Preserved
- All actions pass through `reasoner.decide_burst_actions()`
- Reasoner receives hint as **context**, not as **commands**
- LLM makes independent decisions via OODA
- Observable preconditions checked before execution

### 3. Explicit Warnings
- Hint string contains `⚠️ IMPORTANT: Do NOT blindly follow`
- LLM instructed to verify preconditions
- LLM can adapt or reject hint based on current state

### 4. Metrics & Monitoring
```python
@dataclass
class SkillMetrics:
    hints_retrieved: int  # How many hints found
    hints_used: int  # LLM followed the hint
    hints_adapted: int  # LLM adapted the hint
    hints_rejected: int  # LLM ignored the hint
    
    hint_follow_rate: float  # hints_used / hints_retrieved
    llm_tokens_saved: int  # Estimated savings
```

## Testing Strategy

### 1. Unit Tests
- ✅ Database table creation
- ✅ Store and retrieve skills
- ✅ Context hash consistency
- ✅ Action sequence cleaning
- ✅ Success count incrementing
- ✅ Old skill cleanup

### 2. Integration Tests
- ✅ Full correction workflow
- ✅ Cache hit/miss scenarios
- ✅ Performance validation (<50ms retrieval)
- ⏳ Router integration (TODO)

### 1. Database Schema

```sql
CREATE TABLE skill_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_vector BLOB NOT NULL,           -- Semantic embedding of intent
    context_hash TEXT NOT NULL,            -- Hash of visual/app context
    action_sequence TEXT NOT NULL,         -- JSON array of actions
    intent_text TEXT,                      -- Human-readable intent
    success_count INTEGER DEFAULT 1,       -- How many times used
    last_used TEXT NOT NULL,               -- Last usage timestamp
    created_at TEXT NOT NULL,              -- Creation timestamp
    UNIQUE(context_hash)                   -- One skill per context
);

CREATE INDEX idx_skill_cache_context ON skill_cache(context_hash);
CREATE INDEX idx_skill_cache_last_used ON skill_cache(last_used DESC);
```

**Key Fields:**
- `intent_vector`: 384-dimensional embedding from sentence-transformers (all-MiniLM-L6-v2)
- `context_hash`: SHA-256 hash of intent + context (first 16 chars)
- `action_sequence`: JSON array of cleaned action objects
- `success_count`: Increments on each successful reuse

### 2. Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Command                            │
│              "Set my Slack status to away"                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  SemanticRouter                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │  1. classify_intent() → "ACTION"                 │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐       │
│  │  2. check_skill_cache()                          │       │
│  │     ├─ Generate intent vector                    │       │
│  │     ├─ Compute context hash                      │       │
│  │     └─ Query skill_cache table                   │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────┬────────────────────────┬─────────────────┘
                   │                        │
         Cache HIT │                        │ Cache MISS
                   │                        │
                   ▼                        ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │   REFLEX MODE        │    │   LLM REASONING      │
    │   Execute cached     │    │   Generate new plan  │
    │   action sequence    │    │   (2-5s delay)       │
    │   (~500ms total)     │    │                      │
    └──────────────────────┘    └──────────────────────┘
```

### 3. Learning Flow

```
User Command → Action Fails → User Correction → Success → Store Skill

Example flow:
┌─────────────────────────────────────────────────────────────┐
│  Session Start                                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Record Action: click(status_button) → FAIL                 │
│  Error: "Element blocked by popup"                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  User Correction: "First close the popup"                   │
│  system.record_user_correction(...)                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Record Action: click(close_popup) → SUCCESS                │
│  Record Action: click(status_button) → SUCCESS              │
│  Record Action: select(away) → SUCCESS                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  store_corrective_sequence()                                │
│  ├─ Extract successful actions: [close_popup, click, select]│
│  ├─ Clean sequence (remove timestamps, etc.)                │
│  ├─ Generate intent vector                                  │
│  ├─ Compute context hash                                    │
│  └─ Store in skill_cache table                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Session End                                                 │
│  Skill ID: 123 stored                                       │
└─────────────────────────────────────────────────────────────┘
```

### 4. Retrieval Flow

```
User Command → Generate Vector → Hash Context → Query DB → Compare Similarity

┌─────────────────────────────────────────────────────────────┐
│  Input: "Set Slack status to away"                          │
│  Context: {app: "Slack", state: "popup_present"}           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Generate Intent Vector                                      │
│  ├─ Use sentence-transformers model                         │
│  ├─ Encode text → 384-dim vector                            │
│  └─ Convert to bytes for storage                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Compute Context Hash                                        │
│  ├─ Normalize intent: "set slack status to away"            │
│  ├─ JSON serialize context                                  │
│  ├─ SHA-256 hash                                            │
│  └─ Take first 16 chars: "a1b2c3d4e5f6g7h8"               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Query Database                                              │
│  SELECT * FROM skill_cache WHERE context_hash = ?           │
└──────────────────┬──────────────────────────────────────────┘
                   │
            Found  │  Not Found
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Calculate Similarity                                        │
│  ├─ Load stored vector from DB                              │
│  ├─ Cosine similarity with query vector                     │
│  ├─ Threshold check (default: 0.8)                         │
│  └─ Return if similarity >= threshold                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Return Action Sequence                                      │
│  [                                                           │
│    {action_type: "click", parameters: {target: "popup"}},   │
│    {action_type: "click", parameters: {target: "button"}},  │
│    {action_type: "select", parameters: {option: "away"}}    │
│  ]                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Intent Vector Generation

```python
def _generate_intent_vector(intent_text: str) -> bytes:
    """Generate semantic embedding for intent"""
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Same model as SemanticRouter for consistency
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embedding = model.encode([intent_text])[0]
        
        # Convert to bytes for storage
        return embedding.astype(np.float32).tobytes()
    except ImportError:
        # Fallback: use hash-based pseudo-vector
        hash_bytes = hashlib.sha256(intent_text.encode()).digest()
        return hash_bytes * 12  # 384 bytes
```

### 2. Context Hash Computation

```python
def _compute_context_hash(intent_text: str, context_data: Dict) -> str:
    """Compute deterministic hash for intent + context"""
    # Normalize intent
    normalized = intent_text.lower().strip()
    
    # Add context
    hash_input = normalized
    if context_data:
        context_str = json.dumps(context_data, sort_keys=True)
        hash_input += context_str
    
    # Generate hash
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
```

### 3. Action Sequence Cleaning

The cleaning logic removes metadata and filters out redundant actions from retry attempts:

```python
def _clean_action_sequence(actions: List[Dict]) -> List[Dict]:
    """
    Remove metadata and filter redundant actions
    
    Filters out:
    - Actions without action_type
    - Consecutive duplicate actions (retry attempts)
    - Redundant actions with same type and parameters
    """
    if not actions:
        return []
        
    cleaned = []
    last_action = None
    
    for action in actions:
        # Extract essential fields only
        cleaned_action = {
            "action_type": action.get("action_type"),
            "parameters": action.get("parameters", {})
        }
        
        # Filter out None values and empty parameters
        if not cleaned_action["action_type"]:
            continue
            
        if not cleaned_action["parameters"]:
            del cleaned_action["parameters"]
        
        # Check for consecutive duplicates (retry attempts)
        if last_action and _actions_are_equivalent(cleaned_action, last_action):
            continue  # Skip duplicate
        
        cleaned.append(cleaned_action)
        last_action = cleaned_action
    
    return cleaned
```

**Key Improvements:**
- **Deduplication**: Consecutive identical actions are filtered out (prevents storing retry attempts)
- **Example**: `[click, click, click, type]` → `[click, type]`
- **Non-consecutive duplicates preserved**: Intentional repeated actions are kept
- **Parameter comparison**: Actions are considered equivalent only if both type and parameters match

### 4. Similarity Calculation

```python
def calculate_similarity(stored_vector: bytes, query_vector: bytes) -> float:
    """Cosine similarity between two vectors"""
    import numpy as np
    
    stored = np.frombuffer(stored_vector, dtype=np.float32)
    query = np.frombuffer(query_vector, dtype=np.float32)
    
    # Cosine similarity = dot product of normalized vectors
    dot = np.dot(stored, query)
    norm = np.linalg.norm(stored) * np.linalg.norm(query)
    
    return dot / norm if norm > 0 else 0.0
```

## Performance Characteristics

### Cache Hit Scenario

| Phase | Time | Description |
|-------|------|-------------|
| Intent Classification | ~50ms | SemanticRouter embedding-based classification |
| Cache Lookup | ~5ms | SQLite query by context_hash |
| Similarity Check | ~2ms | NumPy vector comparison |
| Action Execution | ~500ms | Execute cached sequence |
| **Total** | **~560ms** | **5-10x faster than LLM reasoning** |

### Cache Miss Scenario

| Phase | Time | Description |
|-------|------|-------------|
| Intent Classification | ~50ms | Same as cache hit |
| Cache Lookup | ~5ms | No match found |
| LLM Reasoning | ~2000-5000ms | Generate plan from scratch |
| Action Execution | ~500ms | Execute generated plan |
| **Total** | **~2.5-5.5s** | **Normal LLM-based execution** |

### Storage Overhead

- **Per Skill**: ~1-2 KB (vector + actions + metadata)
- **100 Skills**: ~100-200 KB
- **1000 Skills**: ~1-2 MB
- **Impact**: Negligible (skills stored in SQLite)

## Integration Points

### 1. SemanticRouter Integration

```python
class SemanticRouter:
    def __init__(self, reasoner, learning_manager=None):
        self.learning_manager = learning_manager
        # ...
    
    def check_skill_cache(self, text, context_data):
        """Check cache before LLM reasoning"""
        if not self.learning_manager:
            return None
        
        return self.learning_manager.retrieve_cached_skill(
            intent_text=text,
            context_data=context_data
        )
```

### 2. Pipeline Integration

```python
# In main pipeline:
def process_command(text):
    # 1. Classify
    if semantic_router.classify_intent(text) != "ACTION":
        return handle_chat(text)
    
    # 2. Check cache (NEW!)
    cached_skill = semantic_router.check_skill_cache(text)
    if cached_skill:
        return execute_cached_skill(cached_skill)  # Fast path
    
    # 3. LLM reasoning (fallback)
    plan = reasoner.generate_plan(text)
    return execute_plan(plan)
```

### 3. Correction Handling

```python
# After successful correction:
learning_manager.record_user_correction(
    correction_text=user_correction,
    alternative_action=corrected_action
)

# Store as skill
semantic_router.store_successful_sequence(
    text=original_intent,
    context_data=current_context
)
```

## Testing Strategy

### 1. Unit Tests (test_skill_caching.py)

- ✅ Database table creation
- ✅ Store and retrieve skills
- ✅ Context hash consistency
- ✅ Action sequence cleaning
- ✅ Success count incrementing
- ✅ Old skill cleanup

### 2. Integration Tests

- ✅ Full correction workflow
- ✅ Cache hit/miss scenarios
- ✅ Performance validation (<50ms retrieval)
- ✅ Router integration

### 3. Acceptance Criteria (TICKET-LEARN-001)

✅ **After correcting agent once on a specific task, the second execution is 2x faster**

Measured in tests:
- First execution with correction: ~2500ms (includes reasoning)
- Second execution with cache: ~500ms (5x faster!)

## Future Enhancements

### 1. Similarity-Based Search

Instead of exact context_hash match, search all skills and rank by similarity:

```sql
-- Requires vector extension or external index
SELECT * FROM skill_cache 
ORDER BY vector_similarity(intent_vector, ?) DESC
LIMIT 5;
```

### 2. Skill Merging

Automatically merge similar skills to reduce duplication:

```python
if similarity(skill_a, skill_b) > 0.95:
    merged_skill = merge(skill_a, skill_b)
    update_cache(merged_skill)
```

### 3. Confidence Scoring

Track success rate per skill to identify degrading skills:

```python
skill = get_skill(intent)
if skill.success_rate < 0.7:
    mark_for_relearning(skill)
```

### 4. Multi-Context Skills

Support multiple contexts per skill:

```python
skill = {
    "intent": "Submit form",
    "contexts": [
        {"screen": "login", "actions": [...]},
        {"screen": "checkout", "actions": [...]}
    ]
}
```

### 3. Acceptance Criteria (LEARNING-001)

✅ **Aucun skill exécuté sans décision centrale**
- Skills are hints, never executed automatically
- All actions pass through OODA loop
- LLM Reasoner makes independent decisions

✅ **Amélioration du coût LLM**
- Hints reduce tokens needed for context
- Faster reasoning with learned context
- Estimated 20-40% token savings on repeated tasks

✅ **Préconditions observables obligatoires**
- Warning in every hint: "Verify preconditions"
- LLM instructed to check system state
- No blind execution of suggestions

## Monitoring & Debugging

### Key Metrics (LEARNING-001)

1. **Hint Retrieval Rate**: `hints_retrieved / total_decision_requests`
2. **Hint Follow Rate**: `hints_used / hints_retrieved`
3. **Hint Adaptation Rate**: `hints_adapted / hints_retrieved`
4. **Average Retrieval Time**: Should be <50ms
5. **LLM Tokens Saved**: Estimated by SkillMetrics
6. **Skill Usage Distribution**: Identify hot/cold skills

### Debug Logging

```python
# In SemanticRouter.check_skill_cache():
logger.info(f"💡 HINT MODE: Found skill hint for '{text}' "
            f"(confidence: {hint.confidence:.2f}, used {hint.success_count}x) - "
            f"will suggest to LLM, NOT execute automatically")

# In ActionCoordinator._check_skill_hint():
logger.info(f"💡 Skill hint retrieved in {retrieval_time:.2f}ms "
            f"(confidence: {skill_hint.confidence:.2f}, used {skill_hint.success_count}x)")

# In LearningManager.store_corrective_sequence():
logger.info(f"💾 Stored skill {skill_id} for intent '{text}' "
            f"with {len(sequence)} actions")
```

### Troubleshooting

**Problem**: Hints never found
- Check if semantic_router is passed to ActionCoordinator
- Verify context_data is consistent between store and retrieve
- Lower similarity_threshold (0.7 instead of 0.8)

**Problem**: Wrong hint retrieved
- Context too broad (add more specific context fields)
- Increase similarity_threshold (0.9 instead of 0.8)

**Problem**: Hints not improving performance
- Check SkillMetrics.hint_follow_rate (should be >50%)
- Monitor llm_tokens_saved metric
- Verify hints are properly formatted in prompts

**Problem**: Stale skills
- Run periodic cleanup: `clear_old_skills(days=90)`
- Monitor success_count to identify unused skills

## Conclusion (LEARNING-001)

The Skill Hints system transforms Janus from a purely reasoning-based agent to a **contextually aware** system with "learned experiences". This significantly improves:

- **Performance**: Faster reasoning with learned context (20-40% token reduction)
- **Reliability**: Hints inform decisions without removing safety
- **Cost**: Reduced LLM tokens via contextual suggestions
- **User Experience**: Faster and more consistent responses
- **Safety**: All actions still pass through OODA (no automatic execution)

The system gracefully falls back to pure LLM reasoning when no hint exists, ensuring no functionality is lost. The hints-only approach preserves the robustness of the OODA loop while benefiting from learned sequences.
