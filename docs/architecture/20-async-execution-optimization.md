# Async Execution Optimization (TICKET-PERF-001)

> **Status**: ✅ Implemented  
> **Related**: [Unified Pipeline](./02-unified-pipeline.md) | [ExecutionEngineV3](../../janus/core/execution_engine_v3.py)

---

## Overview

The Async Execution Optimization feature enables **parallel execution of non-blocking operations** in multi-step action plans, significantly reducing total execution time for scenarios like launching multiple applications simultaneously.

Additionally, the execution engine now supports **ProcessPoolExecutor** for CPU-intensive operations to avoid Python's Global Interpreter Lock (GIL) limitations.

### Problem Statement

Previously, the ExecutionEngine executed all steps **strictly sequentially**, even when steps didn't depend on each other. For example:

```
Command: "Ouvre Calc, Notepad et Chrome"
Old behavior:
  1. Launch Calc → wait for full load → 2-3s
  2. Launch Notepad → wait for full load → 2-3s  
  3. Launch Chrome → wait for full load → 3-4s
  Total: ~8-10 seconds
```

This sequential execution was inefficient for independent operations that don't require context from previous steps.

### Solution

With the `blocking` flag and parallel execution:

```
New behavior:
  1. Launch Calc, Notepad, Chrome in parallel → ~3-4s (max of the three)
  Total: ~3-4 seconds (2-3x faster)
```

## Architecture

### The `blocking` Flag

Steps in an action plan can now include a `blocking` boolean field:

```json
{
  "module": "system",
  "action": "open_application",
  "args": {"app_name": "Chrome"},
  "blocking": false  // ← New field
}
```

**Semantics:**
- `blocking: true` (default): Wait for the action to complete before starting the next step
- `blocking: false`: Start the action and immediately proceed to the next step (optimistic execution)

### Default Behavior

**For backward compatibility, all steps default to `blocking: true`** if the field is omitted. This ensures existing code continues to work safely.

### Step Grouping Algorithm

The ExecutionEngine groups consecutive steps based on their blocking flag:

```python
# Example step sequence:
steps = [
    {"action": "open_calc", "blocking": False},     # Group 1 (parallel)
    {"action": "open_notepad", "blocking": False},  # Group 1 (parallel)
    {"action": "wait_load", "blocking": True},      # Group 2 (sequential)
    {"action": "open_chrome", "blocking": False}    # Group 3 (parallel)
]

# Resulting execution groups:
# Group 1: [open_calc, open_notepad] → asyncio.gather() → parallel
# Group 2: [wait_load] → single execution → blocks
# Group 3: [open_chrome] → single execution → doesn't block next group
```

**Grouping Rules:**
1. Consecutive non-blocking steps are grouped together for parallel execution
2. Blocking steps create a boundary and are executed individually
3. Each group must complete before the next group starts

### Parallel Execution with asyncio.gather()

For each group with multiple steps, the engine uses Python's `asyncio.gather()`:

```python
# Parallel execution of non-blocking group
tasks = [
    self._execute_single_step(step_index, step, context, result, ...)
    for step_index, step in group.steps
]

action_results = await asyncio.gather(*tasks, return_exceptions=True)
```

This allows multiple actions to execute concurrently without waiting for each other.

## Usage

### Manual Plan Creation

When creating multi-step plans programmatically or through configuration:

```python
from janus.core.execution_engine_v3 import ExecutionEngineV3
from janus.core.contracts import Intent

engine = ExecutionEngineV3()

steps = [
    {
        "module": "system",
        "action": "open_application",
        "args": {"app_name": "Calculator"},
        "blocking": False  # Non-blocking: launch and continue
    },
    {
        "module": "system",
        "action": "open_application",
        "args": {"app_name": "TextEdit"},
        "blocking": False  # Non-blocking: launch and continue
    },
    {
        "module": "system",
        "action": "open_application",
        "args": {"app_name": "Chrome"},
        "blocking": False  # Non-blocking: launch and continue
    },
]

intent = Intent(
    action="open_multiple_apps",
    confidence=1.0,
    raw_command="Ouvre Calc, Notepad et Chrome"
)

# All 3 apps will launch in parallel
result = engine.execute_plan(
    steps=steps,
    intent=intent,
    session_id="session123",
    request_id="request456"
)
```

### When to Use Non-Blocking

Use `blocking: false` when:
- ✅ The action doesn't need to complete before the next action
- ✅ Subsequent actions don't depend on this action's output
- ✅ The action is slow (e.g., launching applications, downloading files)
- ✅ Multiple similar actions can run simultaneously

Use `blocking: true` (default) when:
- ⚠️ Subsequent actions need this action's output
- ⚠️ The action must complete for context to be updated
- ⚠️ The action changes system state that affects next actions
- ⚠️ You need to verify success before continuing

### Examples

#### Example 1: Parallel Application Launch

```json
{
  "steps": [
    {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}, "blocking": false},
    {"module": "system", "action": "open_application", "args": {"app_name": "Slack"}, "blocking": false},
    {"module": "system", "action": "open_application", "args": {"app_name": "Spotify"}, "blocking": false}
  ]
}
```

All three apps launch simultaneously.

#### Example 2: Mixed Blocking/Non-Blocking

```json
{
  "steps": [
    // Parallel group: Launch editors
    {"module": "system", "action": "open_application", "args": {"app_name": "VSCode"}, "blocking": false},
    {"module": "system", "action": "open_application", "args": {"app_name": "Terminal"}, "blocking": false},
    
    // Blocking: Wait for Chrome to fully load (needs to navigate)
    {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}, "blocking": true},
    {"module": "browser", "action": "open_url", "args": {"url": "https://github.com"}, "blocking": true},
    
    // Non-blocking: Copy can happen while page loads
    {"module": "ui", "action": "copy_text", "args": {"text": "example"}, "blocking": false}
  ]
}
```

Execution flow:
1. VSCode + Terminal launch in parallel (~2-3s)
2. Chrome launches and waits for full load (~3s)
3. Navigate to GitHub and wait (~1-2s)
4. Copy text immediately

## Implementation Details

### Code Structure

The implementation consists of three main components:

1. **StepValidator**: Validates the `blocking` field (must be boolean if present)
2. **StepGroup**: Data class representing a group of steps to execute together
3. **_group_steps_for_parallel_execution()**: Groups steps based on blocking flag
4. **_execute_single_step()**: Executes a single step (can be called in parallel)

### Validation

The `StepValidator` checks the `blocking` field during step validation:

```python
blocking = step.get("blocking")
if blocking is not None and not isinstance(blocking, bool):
    warnings.append(f"Step 'blocking' should be a boolean, got {type(blocking).__name__}")
```

Invalid values generate warnings but don't fail validation (defaults to `True`).

### Context Safety

**Important**: When steps execute in parallel, they share the same `ExecutionContext`. The implementation ensures:

1. ✅ **Each step has its own result object**: No result conflicts
2. ✅ **Context updates are sequential**: Although steps execute in parallel, context updates happen **after** all steps in the group complete, preventing race conditions
3. ✅ **Task completion guarantees**: All tasks in a parallel group complete execution before the next group starts
4. ⚠️ **No guaranteed order**: Results may complete in any order within a group

**How it works:**
1. Steps execute in parallel using `asyncio.gather()`
2. Each step collects its results independently
3. After **all** steps complete, context updates are applied sequentially
4. Only then does the next group start executing

**Recommendation**: Only use parallel execution for truly independent operations that don't modify shared state or depend on each other's outputs.

## Performance Impact

### Benchmarks

Measured on M4 MacBook Pro (16GB RAM):

| Scenario | Sequential | Parallel | Speedup |
|----------|-----------|----------|---------|
| 3 app launches | ~8-10s | ~3-4s | **2.5x** |
| 5 app launches | ~15-18s | ~4-5s | **3.5x** |
| Mixed (2 parallel + 1 blocking) | ~6-7s | ~4-5s | **1.5x** |

### Trade-offs

**Benefits:**
- ✅ Significant time savings for independent operations
- ✅ Better user experience (faster response)
- ✅ Natural for batch operations (open multiple files, apps, etc.)

**Considerations:**
- ⚠️ Higher resource usage (CPU, memory) during parallel execution
- ⚠️ Potential for race conditions if steps aren't truly independent
- ⚠️ More complex error handling (multiple failures possible)

## ProcessPoolExecutor for CPU-Intensive Operations

### GIL Bottleneck

Python has a **Global Interpreter Lock (GIL)** that prevents true parallel execution of CPU-bound Python code in threads. While `run_in_executor` with the default `ThreadPoolExecutor` works well for I/O-bound operations (like opening applications, network requests, file operations), it provides **no benefit for CPU-intensive tasks** due to the GIL.

### When to Use ProcessPoolExecutor

The execution engine now supports **ProcessPoolExecutor** for scenarios where CPU-intensive processing is needed:

```python
from janus.core.execution_engine_v3 import ExecutionEngineV3

# For CPU-intensive operations (e.g., parsing hundreds of emails, heavy data processing)
engine = ExecutionEngineV3(
    use_process_pool=True,     # Enable ProcessPoolExecutor
    max_workers=4              # Number of worker processes (optional)
)
```

**Use ProcessPoolExecutor when:**
- ✅ Actions perform heavy CPU computations (e.g., parsing large datasets)
- ✅ Processing large volumes of data (e.g., 100+ emails)
- ✅ Running algorithms that are CPU-bound rather than I/O-bound
- ✅ You need true parallelism to utilize multiple CPU cores

**Keep default ThreadPoolExecutor when:**
- ✅ Actions are I/O-bound (network, disk, GUI operations)
- ✅ Actions need to share state or access shared resources
- ✅ Actions are quick and lightweight
- ✅ You want lower overhead (threads are lighter than processes)

### Configuration

```python
# Default: ThreadPoolExecutor (suitable for most operations)
engine_default = ExecutionEngineV3()

# ProcessPoolExecutor for CPU-intensive work
engine_cpu_heavy = ExecutionEngineV3(
    use_process_pool=True,
    max_workers=4  # Limit to 4 worker processes
)

# Don't forget to cleanup when done
engine_cpu_heavy.shutdown()
```

### Trade-offs

| Executor Type | Pros | Cons |
|--------------|------|------|
| **ThreadPoolExecutor** (default) | • Lower overhead<br>• Shared memory<br>• Fast startup<br>• Good for I/O-bound tasks | • Limited by GIL for CPU tasks<br>• No true parallelism for compute |
| **ProcessPoolExecutor** | • True parallelism<br>• No GIL limitations<br>• Good for CPU-bound tasks | • Higher overhead<br>• No shared memory<br>• Slower startup<br>• Objects must be picklable |

### Example Use Case

```python
# Future: Email parsing connector with heavy processing
# This would benefit from ProcessPoolExecutor

# Scenario: Parse 100 emails with LLM-based content analysis
steps = [
    {
        "module": "email",
        "action": "parse_inbox",
        "args": {"folder": "inbox", "limit": 100},
        "blocking": False  # Can process in parallel
    }
]

# With ProcessPoolExecutor, multiple emails can be processed
# in parallel across CPU cores, avoiding GIL bottleneck
engine = ExecutionEngineV3(use_process_pool=True)
result = engine.execute_plan(steps, intent, session_id, request_id)
engine.shutdown()
```

## Future Work and Reasoner Integration

### Current State

The `blocking` flag must currently be specified manually in action plans. The ReAct loop (ActionCoordinator) generates actions one at a time and doesn't use multi-step plans.

### Future: LLM-Predicted Blocking Flag

**Future enhancement**: Teach the LLM reasoner to predict the `blocking` flag automatically:

```python
# Future: LLM generates steps with blocking prediction
# Prompt template addition:
"""
For each action, indicate if it's blocking:
- blocking: true → Must complete before next action
- blocking: false → Can start and continue immediately

Example: Opening applications is typically non-blocking.
"""
```

The reasoner would analyze:
1. **Action type**: `open_application` → likely non-blocking
2. **Dependencies**: Does next action need this action's output?
3. **Context**: Will next action use context from this action?

### Integration with Multi-Step Planning

When/if multi-step planning is re-introduced:

```python
# Future: Reasoner generates full plan with blocking flags
plan = reasoner.generate_plan(
    user_goal="Open Safari, Chrome and Firefox",
    predict_blocking=True  # ← Enable blocking prediction
)

# Generated plan:
# [
#   {"action": "open_app", "args": {"app": "Safari"}, "blocking": false},
#   {"action": "open_app", "args": {"app": "Chrome"}, "blocking": false},
#   {"action": "open_app", "args": {"app": "Firefox"}, "blocking": false}
# ]
```

## Testing

Comprehensive test suite in `tests/test_ticket_perf_001_async_execution.py`:

- ✅ Step grouping logic (10 test cases)
- ✅ Parallel execution timing verification
- ✅ Mixed blocking/non-blocking scenarios
- ✅ Backward compatibility (default blocking behavior)
- ✅ Acceptance criteria validation

Run tests:
```bash
python -m unittest tests.test_ticket_perf_001_async_execution -v
```

## Related Documentation

- [Unified Pipeline](./02-unified-pipeline.md) - OODA Loop and dynamic execution
- [Dynamic ReAct Loop](./13-dynamic-react-loop.md) - One-action-at-a-time approach
- [Action Coordinator](./14-action-coordinator.md) - ReAct loop implementation
- [ExecutionEngineV3 Source](../../janus/core/execution_engine_v3.py) - Implementation

## Summary

The async execution optimization adds intelligent parallelization to Janus's execution engine:

1. **`blocking` flag**: Indicates if action must complete before continuing
2. **Step grouping**: Consecutive non-blocking steps execute in parallel
3. **Backward compatible**: Defaults to sequential execution (blocking=True)
4. **Significant speedup**: 2-3x faster for batch operations
5. **Safe**: Proper error handling and context management
6. **ProcessPoolExecutor support**: Optional process-based execution for CPU-intensive operations to avoid GIL limitations

This feature is particularly valuable for:
- 🚀 Launching multiple applications
- 📁 Opening multiple files
- 🔗 Opening multiple browser tabs
- 🎯 Any batch operation with independent steps
- 🔢 CPU-intensive processing (with ProcessPoolExecutor)

---

**Status**: ✅ Core implementation complete. LLM-based blocking prediction is future work.
