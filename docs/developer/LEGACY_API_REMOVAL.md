# Migration Complete: Legacy API Removed

## Summary

The legacy single-action API has been **completely removed** in favor of the modern burst OODA mode.

## What Was Removed

### 1. ActionPlan.add_action()
**Removed**: `ActionPlan.add_action(action_type, **kwargs)`

**Replacement**: Use `ActionPlan.add_step(module, action, args)`

```python
# ❌ REMOVED - No longer available
plan.add_action("click", x=100, y=200)

# ✅ Use this instead
plan.add_step(module="ui", action="click", args={"x": 100, "y": 200})
```

### 2. ActionCoordinator Legacy Methods
**Removed**:
- `_orient()` - Legacy context preparation
- `_decide()` - Legacy single-action decision
- `_act()` - Legacy single-action execution
- `_decide_single()` - Legacy fallback wrapper
- `_build_prompt()` - Legacy prompt builder
- `_parse_response()` - Legacy response parser

**Replacement**: Burst OODA mode is now always active

The burst mode methods are:
- `_decide_burst()` - Generates 2-6 actions per LLM call
- `_execute_burst()` - Executes burst sequentially
- `_act_single()` - Executes individual actions within burst

### 3. ActionCoordinator Constructor
**Removed**: `enable_burst_mode` parameter

```python
# ❌ REMOVED - No longer available
coordinator = ActionCoordinator(enable_burst_mode=False)

# ✅ Burst mode is always enabled
coordinator = ActionCoordinator()
```

## Modern Burst OODA Mode

### How It Works

1. **Observe**: Capture system state (cheap, via SystemBridge)
2. **Observe Visual** (if needed): Capture visual context via Set-of-Marks or accessibility
3. **Decide Burst**: LLM generates 2-6 actions with stop conditions
4. **Execute Burst**: Actions execute sequentially
5. **Check Stop Conditions**: Re-observe if conditions are met
6. **Repeat**: Continue until goal achieved or max iterations

### Benefits

- **2-6x fewer LLM calls**: Batch actions per decision
- **Better performance**: Fewer network round trips
- **Stop conditions**: Automatic re-observation when needed
- **Stagnation detection**: Automatic recovery from stuck states
- **Context propagation**: Better multi-step workflows

### Stop Conditions

Burst decisions can include stop conditions for adaptive re-observation:

```python
{
    "actions": [
        {"module": "chrome", "action": "navigate", "args": {"url": "example.com"}},
        {"module": "ui", "action": "click", "args": {"element_id": "button_1"}}
    ],
    "stop_when": [
        {
            "type": "url_contains",
            "value": "example.com",
            "description": "Wait for navigation to complete"
        }
    ],
    "needs_vision": False,
    "reasoning": "Navigate to example.com"
}
```

**Supported stop conditions**:
- `url_contains` / `url_equals` - URL matching
- `app_active` - Application focus
- `window_title_contains` - Window title matching
- `clipboard_contains` - Clipboard content matching
- `ui_element_visible` - Vision-based element detection
- `ui_element_contains_text` - Vision-based text detection

## Migration Examples

### Example 1: Simple Action Plan

```python
from janus.runtime.core.contracts import ActionPlan, Intent

intent = Intent(action="click_button", confidence=0.9)
plan = ActionPlan(intent=intent)

# Modern API - explicit module and action
plan.add_step(
    module="ui",
    action="click",
    args={"x": 100, "y": 200},
    step_id="click_1"
)
```

### Example 2: Multi-Step Plan with Context

```python
# Step 1: Navigate to website
plan.add_step(
    module="chrome",
    action="navigate",
    args={"url": "https://example.com"},
    step_id="navigate",
    context=None
)

# Step 2: Extract text (using output from step 1)
plan.add_step(
    module="ui",
    action="extract_text",
    args={"element_id": "header_1", "input_from": "navigate"},
    step_id="extract"
)
```

### Example 3: Conditional Steps

```python
plan.add_conditional_step(
    condition="app_not_open('Chrome')",
    if_true=[{"module": "chrome", "action": "open_app"}],
    if_false=[{"module": "chrome", "action": "switch_tab"}],
    step_id="ensure_chrome"
)
```

### Example 4: Loops

```python
# Repeat action 3 times
plan.add_loop(
    repeat=3,
    steps=[{"module": "terminal", "action": "execute", "args": {"cmd": "echo {{index}}"}}],
    step_id="loop_1"
)

# For each item in collection
plan.add_for_each(
    items=["file1.txt", "file2.txt", "file3.txt"],
    steps=[{"module": "vscode", "action": "open_file", "args": {"path": "{{item}}"}}],
    step_id="open_files"
)
```

## Testing Updates

Tests using legacy methods have been removed or updated:

```python
# ❌ Old tests (removed)
def test_orient_prepares_context(self):
    context = self.coordinator._orient(...)

def test_decide_calls_reasoner(self):
    action = self.coordinator._decide(...)

# ✅ New tests
def test_burst_mode_always_enabled(self):
    coordinator = ActionCoordinator()
    self.assertTrue(hasattr(coordinator, '_decide_burst'))
    self.assertFalse(hasattr(coordinator, '_decide'))  # Legacy removed
```

## Breaking Changes

This is a **breaking change** for code that:
- Uses `ActionPlan.add_action()`
- Passes `enable_burst_mode=False` to ActionCoordinator
- Directly calls `_orient()`, `_decide()`, or `_act()` methods
- Relies on single-action mode

**Migration path**: Update all code to use the modern burst OODA API as shown in examples above.

## See Also

- [ActionCoordinator Architecture](../architecture/14-action-coordinator.md)
- [Burst OODA Mode](../architecture/CORE-FOUNDATION-002-burst-ooda.md)
- [Multi-Module Plans](../architecture/TICKET-2-multi-module-plans.md)
