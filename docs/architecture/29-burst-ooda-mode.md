# Burst OODA Mode: Reduced LLM Calls with Adaptive Execution

> **Ticket**: CORE-FOUNDATION-002  
> **Enhancement**: See [Dynamic OODA Loop](./13-dynamic-react-loop.md) for base architecture

---

## Overview

The **Burst OODA Mode** is an optimization of the standard OODA loop that reduces LLM calls by 60-80% while maintaining adaptability. Instead of calling the LLM for each single action, it generates **bursts of 2-6 actions** that can be executed together before re-observing.

## The Problem: Too Many LLM Calls

### Standard OODA Loop Pattern

```
Observe → LLM → 1 action → Observe → LLM → 1 action → ...
```

**Issue**: For a task like "Open Safari → Navigate to YouTube → Search for 'Forgive by Burial' → Play first result", this requires:
- ~8-12 LLM calls (one per atomic action)
- Total time: 10-20 seconds (even with fast models on M4)
- User experience: "robot lente" (slow robot)

**Root Cause**: Each LLM call adds latency:
- Model inference: 200-500ms
- Context switching: 50-100ms
- Re-observation: 100-200ms

Even with a fast local model (Qwen2.5:7b), 10 LLM calls = **3-5 seconds minimum**.

## The Solution: Burst OODA Mode

### Burst Pattern

```
Observe → LLM → [2-6 actions] → Execute all → Observe → ...
```

**Benefits**:
- Reduces LLM calls by 60-80% (from 8-12 to 2-3)
- Maintains adaptability (re-observes after each burst)
- Handles unexpected states (cookies, popups) via stagnation detection
- Total time: ≤ 5s for typical tasks

### Key Components

1. **Burst Decision**: LLM generates 2-6 actions in one call
2. **Stop Conditions**: Generic conditions to know when to re-observe
3. **Stagnation Detection**: Detects when we're stuck in same state
4. **Instrumentation**: Comprehensive metrics tracking

## Burst Decision Format

The LLM returns a burst with this structure:

```json
{
  "actions": [
    {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}, "reasoning": "Launch browser"},
    {"module": "browser", "action": "navigate", "args": {"url": "https://youtube.com"}, "reasoning": "Go to YouTube"},
    {"module": "browser", "action": "type_text", "args": {"text": "Forgive Burial", "element_id": "search_box"}, "reasoning": "Search for song"}
  ],
  "stop_when": [
    {"type": "url_contains", "value": "youtube.com"},
    {"type": "ui_element_visible", "value": "Search"}
  ],
  "needs_vision": false,
  "reasoning": "Open browser, navigate, and start search"
}
```

### Fields

- **actions**: List of 2-6 atomic actions (minimum 2, maximum 6)
  - Each action has: `module`, `action`, `args`, `reasoning`
  - Validated against `module_action_schema.py`
  - Special case: Single "done" action is allowed
  
- **stop_when**: List of generic stop conditions
  - Evaluated after burst execution
  - If any condition met, re-observe immediately
  - Types: `url_contains`, `url_equals`, `app_active`, `window_title_contains`, `clipboard_contains`, `ui_element_visible`
  
- **needs_vision**: Boolean flag
  - `true`: Require vision (Set-of-Marks) after burst
  - `false`: Cheap observation (SystemBridge only)
  - Can be forced by stagnation detection
  
- **reasoning**: Overall explanation of the burst strategy

## Stop Conditions

Stop conditions are **generic, observable** checks that don't require app-specific knowledge.

### Supported Types

| Type | Description | Example |
|------|-------------|---------|
| `url_contains` | URL contains substring | `{"type": "url_contains", "value": "youtube.com"}` |
| `url_equals` | URL exactly matches | `{"type": "url_equals", "value": "https://youtube.com"}` |
| `app_active` | Application is frontmost | `{"type": "app_active", "value": "Safari"}` |
| `window_title_contains` | Window title contains text | `{"type": "window_title_contains", "value": "YouTube"}` |
| `clipboard_contains` | Clipboard contains text | `{"type": "clipboard_contains", "value": "copied"}` |
| `ui_element_visible` | Visual element visible (requires vision) | `{"type": "ui_element_visible", "value": "Search"}` |

### When to Use

- **Navigation**: `url_contains` to verify page loaded
- **App switching**: `app_active` to confirm app focus
- **Data extraction**: `clipboard_contains` to verify copy
- **UI verification**: `ui_element_visible` for visual confirmation

## Stagnation Detection

### The Problem

Without stagnation detection, the system can loop infinitely:
```
Try to click button → Button not visible → Try again → Still not visible → ...
```

Common causes:
- Cookie consent popups blocking the UI
- Unexpected dialogs or errors
- Page still loading
- Element actually not present

### The Solution

Track system state hash across observations:

```python
state_hash = hash(active_app + window_title + url + clipboard[:100])
```

If state is **identical** for N consecutive observations (default N=3):
1. **Stagnation detected** ⚠️
2. Force `needs_vision=true` for next decision
3. Increment `stagnation_events` counter
4. LLM gets full visual context to diagnose and adapt

### State Hash Components

- `active_app`: Current foreground application
- `window_title`: Window title text
- `url`: Browser URL (if applicable)
- `clipboard`: First 100 chars of clipboard

**Why these?** They're cheap to observe (via SystemBridge) and capture most state changes.

### Example: Cookie Popup

```
Iteration 1: Navigate to site → URL changes → State hash A
Iteration 2: Try to click search → State unchanged → State hash A
Iteration 3: Try to click search → State unchanged → State hash A
→ Stagnation detected! Force vision.
Iteration 4: (with vision) → See cookie popup → Click "Accept" → State hash B
```

## Execution Flow

### Burst Mode Enabled (Default)

```
┌─────────────────────────────────┐
│     User Goal: "Play song"      │
└───────────┬─────────────────────┘
            │
            ▼
    ┌───────────────────┐
    │  1. OBSERVE       │
    │  • SystemBridge   │◄──────────┐
    │  • Cheap (no vision) │        │
    └──────┬────────────┘           │
           │                         │
           ▼                         │
    ┌───────────────────┐           │
    │  Stagnation?      │           │
    │  (State hash)     │           │
    └──────┬────────────┘           │
           │ No                      │
           ▼                         │
    ┌───────────────────┐           │
    │  2. VISION        │           │
    │  (if needed)      │           │
    └──────┬────────────┘           │
           │                         │
           ▼                         │
    ┌───────────────────┐           │
    │  3. DECIDE        │           │
    │  • LLM burst      │           │
    │  • 2-6 actions    │           │
    └──────┬────────────┘           │
           │                         │
           ▼                         │
    ┌───────────────────┐           │
    │  4. EXECUTE       │           │
    │  • All actions    │           │
    │  • Sequential     │           │
    │  • 50ms pauses    │           │
    └──────┬────────────┘           │
           │                         │
           ▼                         │
    ┌───────────────────┐           │
    │  Stop conditions? │           │
    └──────┬────────────┘           │
           │ Met                     │
           └─────────────────────────┘
           │ Not met
           ▼
       Goal done?
           │
        ┌──┴──┐
       Yes   No → Continue
        │
     DONE
```

## Implementation

### Data Structures

```python
# janus/core/contracts.py

@dataclass
class StopCondition:
    type: StopConditionType  # url_contains, app_active, etc.
    value: str
    description: Optional[str] = None

@dataclass
class BurstDecision:
    actions: List[Dict[str, Any]]  # 2-6 actions
    stop_when: List[StopCondition]
    needs_vision: bool
    reasoning: str

@dataclass
class BurstMetrics:
    llm_calls: int = 0
    burst_actions_executed: int = 0
    vision_calls: int = 0
    stagnation_events: int = 0
    t_llm_ms: float = 0.0
    t_observe_ms: float = 0.0
    t_act_ms: float = 0.0
    t_vision_ms: float = 0.0
```

### ReasonerLLM

```python
# janus/reasoning/reasoner_llm.py

def decide_burst_actions(
    self,
    user_goal: str,
    system_state: Dict[str, Any],
    visual_context: str,
    action_history: List[Any],
    language: str = "fr",
    force_vision: bool = False
) -> Dict[str, Any]:
    """Generate a burst of 2-6 actions"""
    prompt = self._build_burst_prompt(...)
    response = self.run_inference(prompt, max_tokens=512, json_mode=True)
    return self._parse_burst_response(response, force_vision)
```

### ActionCoordinator

```python
# janus/core/action_coordinator.py

class ActionCoordinator:
    def __init__(
        self,
        enable_burst_mode: bool = True,
        stagnation_threshold: int = 3,
        ...
    ):
        self.enable_burst_mode = enable_burst_mode
        self.stagnation_threshold = stagnation_threshold
        self._state_history: List[str] = []
    
    async def execute_goal(...) -> ExecutionResult:
        # 1. Cheap observe
        system_state = await self._observe_system_state()
        
        # 2. Stagnation detection
        state_hash = self._compute_state_hash(system_state)
        is_stagnant = self._detect_stagnation(state_hash, metrics)
        
        # 3. Vision (only if needed)
        if force_vision or is_stagnant or iteration == 1:
            visual_context = await self._observe_visual_context()
        
        # 4. Burst decision
        decision = await self._decide_burst(...)
        
        # 5. Execute burst
        await self._execute_burst(decision, ...)
        
        # 6. Check stop conditions
        if self._evaluate_stop_conditions(decision["stop_when"], state):
            continue  # Re-observe
```

## Metrics & Instrumentation

### Tracked Metrics

```python
class BurstMetrics:
    # Counters
    llm_calls: int              # Total LLM calls
    burst_actions_executed: int # Total actions executed
    vision_calls: int           # Times vision was invoked
    stagnation_events: int      # Times stagnation detected
    
    # Timings (milliseconds)
    t_llm_ms: float            # Time in LLM inference
    t_observe_ms: float        # Time in SystemBridge observation
    t_act_ms: float            # Time executing actions
    t_vision_ms: float         # Time in vision processing
    
    # Derived
    total_bursts: int          # Number of bursts
    avg_actions_per_burst: float  # Actions per burst average
```

### Logging

```python
# Execution summary
logger.info(f"📊 Burst Metrics: {result.burst_metrics.to_dict()}")

# Example output:
{
  "llm_calls": 3,
  "burst_actions_executed": 8,
  "vision_calls": 2,
  "stagnation_events": 1,
  "t_llm_ms": 1234.5,
  "t_observe_ms": 345.2,
  "t_act_ms": 456.7,
  "t_vision_ms": 678.9,
  "total_bursts": 3,
  "avg_actions_per_burst": 2.67
}
```

## Acceptance Criteria

### Task: "Ouvre Safari → YouTube → joue Forgive de Burial"

**Warm Run** (model already loaded):
- ✅ ≤ 3 LLM calls
- ✅ Total time ≤ 5s (goal: ≤ 3s achievable on M4)

**Cold Run** (first model load):
- ≤ 5 LLM calls
- Total time ≤ 8s (acceptable)

### Cookie Popup Handling

**Scenario**: Site shows cookie consent popup

Expected behavior:
1. Burst 1: Navigate → Try to interact
2. Stagnation detected (same state 3x)
3. Burst 2 (with vision): See popup → Accept → Continue
4. ✅ No infinite loop
5. ✅ Successfully completes task

## Configuration

### Enable/Disable Burst Mode

```python
coordinator = ActionCoordinator(
    enable_burst_mode=True,  # Default: True
    stagnation_threshold=3,  # Default: 3 identical states
    max_iterations=20
)
```

### Environment Variables

```ini
# config.ini or .env
ENABLE_BURST_MODE=true
STAGNATION_THRESHOLD=3
```

## Performance Comparison

### Standard OODA Loop

Task: "Navigate to YouTube and play song"

| Metric | Value |
|--------|-------|
| LLM Calls | 10-12 |
| Total Time | 10-15s |
| Vision Calls | 10-12 |
| Average latency per decision | 1-1.5s |

### Burst OODA Mode

Same task:

| Metric | Value | Improvement |
|--------|-------|-------------|
| LLM Calls | 2-3 | **75% reduction** |
| Total Time | 3-5s | **60-70% faster** |
| Vision Calls | 2-3 | **75% reduction** |
| Average latency per burst | 0.5-0.8s | **40% faster** |

## Best Practices

### For LLM Prompt Engineering

1. **Encourage bursts**: Prompt explicitly asks for 2-6 actions
2. **Atomic actions**: Each action should be independently executable
3. **Logical grouping**: Actions should be part of coherent sequence
4. **Stop conditions**: Include observable conditions for re-observation

### For Action Design

1. **Idempotent**: Actions should be safe to execute multiple times
2. **Fast**: Keep individual actions quick (<500ms ideal)
3. **Observable**: State changes should be detectable by SystemBridge
4. **Recoverable**: Failures should be gracefully handled

### For Stagnation Threshold

- **Too low** (1-2): False positives, excessive vision calls
- **Optimal** (3): Good balance of detection and patience
- **Too high** (5+): Slow to detect actual stagnation

## Edge Cases

### Single "Done" Action

Allowed exception to 2-6 rule:
```json
{
  "actions": [{"module": "system", "action": "done", "args": {}}],
  "stop_when": [],
  "needs_vision": false,
  "reasoning": "Goal already achieved"
}
```

### Burst Size Limits

- **Minimum**: 2 actions (except "done")
- **Maximum**: 6 actions (enforced by parser)
- **Truncation**: If LLM generates >6, truncate to 6 with warning

### Vision Override

Stagnation detection forces vision even if `needs_vision=false`:
```python
force_vision = is_stagnant or force_vision
```

## Future Enhancements

1. **Adaptive burst size**: Learn optimal burst size per task type
2. **Parallel execution**: Execute independent actions in parallel
3. **Predictive stagnation**: Predict stagnation before it happens
4. **Smart stop conditions**: Learn which conditions are most reliable

## See Also

- [Dynamic OODA Loop](./13-dynamic-react-loop.md) - Base architecture
- [ActionCoordinator](./14-action-coordinator.md) - Implementation details
- [Strict Action Contract](./15-strict-action-contract.md) - Action validation
- [Reasoner V4](./08-reasoner-v4-think-first.md) - LLM reasoning engine
