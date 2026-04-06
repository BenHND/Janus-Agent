# Strict Action Contract - CORE-FOUNDATION-001

> **Status**: ✅ Implemented (December 2024)  
> **Related**: [ActionCoordinator](./14-action-coordinator.md), [Module Action Schema](../../janus/core/module_action_schema.py)

---

## Overview

The **Strict Action Contract** ensures that all actions in Janus follow a single, validated format throughout the system. This eliminates inconsistencies, bugs, and routing errors that previously occurred from "loose" action formats and heuristic module deduction.

### The Problem (Before)

Previously, the system had multiple issues:

1. **Loose Action Format**: ActionCoordinator accepted formats like `{"action": "open_application", "args": {...}}` without a module field
2. **Heuristic Module Deduction**: The system tried to deduce the module from the action name using string splitting:
   - `action.split("_")[0]` → `"open_application"` became module `"open"` ❌
   - `action.split(".")[0]` → `"browser.open_url"` sometimes worked ⚠️
3. **Incomplete Code**: Buggy logic like `if "." in action` without proper handling
4. **Silent Failures**: Actions routed to wrong agents or failed silently

**Result**: Even simple commands like "open Safari" could fail due to incorrect routing.

### The Solution (Now)

**One strict contract** throughout the runtime:

```json
{
  "module": "system",
  "action": "open_application",
  "args": {"app_name": "Safari"},
  "reasoning": "Opening Safari as requested"
}
```

**Required Fields:**
- `module`: Must be a valid module from the schema (system, browser, ui, files, messaging, crm, code, llm)
- `action`: Must be a valid action for that module
- `args`: Dictionary of action parameters (validated against schema)

**Optional Fields:**
- `reasoning`: Explanation of why this action was chosen
- `needs_vision`: Whether visual context is required
- `confidence`: Confidence score (0.0-1.0)
- `stop_when`: Condition for stopping iteration (for future burst mode)

---

## Implementation

### 1. ActionCoordinator._parse_response

**Strict Validation** against `module_action_schema.py`:

```python
def _parse_response(self, response):
    """
    Parse LLM response with STRICT validation.
    
    Returns:
        Valid action: {"module": "...", "action": "...", "args": {...}}
        Error: {"action": "error", "error": "...", "error_type": "..."}
    """
    # Extract JSON
    data = json.loads(response)
    
    # STRICT: Require module field
    if "module" not in data:
        return {
            "action": "error",
            "error": f"Missing 'module'. Available: {get_all_module_names()}",
            "error_type": "invalid_action_schema"
        }
    
    # STRICT: Require action field
    if "action" not in data:
        return {
            "action": "error",
            "error": f"Missing 'action'. Available for '{module}': {get_all_actions_for_module(module)}",
            "error_type": "invalid_action_schema"
        }
    
    # Validate against schema
    is_valid, error_msg = validate_action_step({
        "module": data["module"],
        "action": data["action"],
        "args": data.get("args", {})
    })
    
    if not is_valid:
        return {
            "action": "error",
            "error": error_msg,
            "error_type": "unknown_module" | "unknown_action" | "invalid_parameters"
        }
    
    return data  # Valid!
```

**Error Types:**
- `invalid_json`: Response is not valid JSON
- `invalid_action_schema`: Missing required fields (module, action)
- `unknown_module`: Module not in schema
- `unknown_action`: Action not valid for module
- `invalid_parameters`: Parameters don't match schema

### 2. ActionCoordinator._act

**No More Module Deduction:**

```python
async def _act(self, action_plan, memory, start_time, system_state):
    """
    Execute action using strict module/action contract.
    NO heuristic module deduction!
    """
    # Extract validated fields
    module = action_plan["module"]   # Already validated!
    action = action_plan["action"]   # Already validated!
    args = action_plan["args"]       # Already validated!
    
    # Route directly to AgentRegistry
    result = await self.agent_registry.execute_async(
        module=module,
        action=action,
        args=args,
        context=ctx
    )
    
    return ActionResult(
        action_type=f"{module}.{action}",  # e.g., "system.open_application"
        success=result.get("status") == "success",
        ...
    )
```

**Before (Buggy):**
```python
# ❌ Heuristic deduction
module = action["action"].split("_")[0] if "_" in action["action"] else "system"
if "." in action["action"]: 
    module = action["action"].split(".")[0]
```

**After (Strict):**
```python
# ✅ Direct from validated data
module = action_plan["module"]
```

### 3. ActionCoordinator.execute_goal - Re-Ask Mechanism

When validation fails, the error is added to the action history so the LLM can see what went wrong and try again:

```python
# 3. DECIDE
action_plan = self._decide(context, language)

# Handle validation errors - add to history for re-ask
if action_plan.get("action") == "error":
    error_type = action_plan.get("error_type", "unknown")
    error_msg = action_plan.get("error", "Unknown error")
    
    logger.warning(f"❌ Invalid action schema ({error_type}): {error_msg}")
    
    # Add error to history so reasoner can see what went wrong
    error_result = ActionResult(
        action_type=f"validation_error.{error_type}",
        success=False,
        message=f"Validation failed: {error_msg}",
        recoverable=True
    )
    result.add_result(error_result)
    
    # Continue to next iteration for re-ask
    continue
```

**Example Re-Ask Flow:**

```
Iteration 1:
  DECIDE: {"action": "open_application", "args": {"app_name": "Safari"}}  ❌ Missing module
  VALIDATE: ERROR - "Missing required field 'module'"
  HISTORY: [validation_error.invalid_action_schema: "Validation failed: Missing 'module'"]
  
Iteration 2:
  DECIDE: {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}  ✅
  ACT: Success
  Result: Safari opened
```

### 4. ReasonerLLM Prompts

The prompt now includes the schema and strict format requirements:

```python
def _build_prompt(self, ctx, lang):
    # Get schema section for LLM prompt
    schema_section = get_prompt_schema_section(language=lang)
    
    prompt = f"""You are a GUI expert.
GOAL: {ctx['user_goal']}

{schema_section}

⚠️ REQUIRED RESPONSE FORMAT:
You MUST respond in JSON with this EXACT structure:
{{
  "module": "module_name",
  "action": "action_name",
  "args": {{}},
  "reasoning": "optional explanation"
}}

IMPORTANT:
- "module" is REQUIRED and must be one of: system, browser, ui, files, messaging, crm, code, llm
- "action" is REQUIRED and must be a valid action from the module schema above
- "args" contains action parameters
- If goal is achieved, use {{"module": "system", "action": "done", "args": {{}}}}

What is the next action?"""
```

---

## Module Action Schema

All valid modules and actions are defined in `janus/core/module_action_schema.py`.

### The 8 Universal Modules

1. **system** - System actions (open_application, close_application, switch_application)
2. **browser** - Web navigation (open_url, navigate_back, refresh, search)
3. **ui** - UI interactions (click, type, copy, paste)
4. **files** - File operations (open_file, save_file, search_files, delete_file)
5. **messaging** - Communication (send_message, open_thread, search_messages)
6. **crm** - CRM operations (open_record, search_records, update_field)
7. **code** - Code editing (open_file, goto_line, find_text, save_file)
8. **llm** - AI operations (summarize, rewrite, extract_keywords, analyze_error)

### Example Action Definitions

```python
SYSTEM_MODULE = ModuleDefinition(
    name=ModuleName.SYSTEM,
    description="Actions système macOS",
    actions=[
        ActionDefinition(
            name="open_application",
            description="Ouvrir une application",
            parameters=[
                ActionParameter("app_name", "string", required=True, 
                    description="Nom de l'application (Safari, Chrome, VSCode, etc.)")
            ],
            examples=[
                '{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}',
            ],
            aliases=["open_app", "launch", "launch_app"]
        ),
        ...
    ]
)
```

### Validation Functions

```python
# Check if module exists
is_valid_module("system")  # True
is_valid_module("invalid")  # False

# Check if action exists for module
is_valid_action("system", "open_application")  # True
is_valid_action("system", "invalid_action")    # False

# Validate complete action step
validate_action_step({
    "module": "system",
    "action": "open_application",
    "args": {"app_name": "Safari"}
})  # (True, None)

validate_action_step({
    "module": "system",
    "action": "open_application",
    "args": {}  # Missing required app_name
})  # (False, "Missing required parameter: app_name")
```

---

## Testing

### Unit Tests (test_ticket_core_foundation_001.py)

**17 comprehensive tests** covering all aspects of the strict contract:

#### Validation Tests

```python
def test_parse_valid_action_with_module():
    """✅ Valid action with module, action, args passes"""
    response = json.dumps({
        "module": "system",
        "action": "open_application",
        "args": {"app_name": "Safari"}
    })
    result = coordinator._parse_response(response)
    assert result["module"] == "system"
    assert result["action"] == "open_application"

def test_parse_rejects_action_without_module():
    """❌ Action without module field is rejected"""
    response = json.dumps({
        "action": "open_application",
        "args": {"app_name": "Safari"}
    })
    result = coordinator._parse_response(response)
    assert result["action"] == "error"
    assert result["error_type"] == "invalid_action_schema"

def test_parse_rejects_unknown_module():
    """❌ Unknown module triggers validation error"""
    response = json.dumps({
        "module": "nonexistent_module",
        "action": "some_action",
        "args": {}
    })
    result = coordinator._parse_response(response)
    assert result["error_type"] == "unknown_module"
```

#### Routing Tests

```python
def test_act_routes_to_correct_agent():
    """✅ Action routes to correct agent without module deduction"""
    action_plan = {
        "module": "system",
        "action": "open_application",
        "args": {"app_name": "Safari"}
    }
    result = await coordinator._act(action_plan, ...)
    assert result.success
    assert result.action_type == "system.open_application"

def test_act_no_module_deduction_from_action_name():
    """✅ NO LONGER deduce module from action name with underscore"""
    action_plan = {
        "module": "system",  # Explicitly provided
        "action": "open_application",  # Has underscore, but we don't split it
        "args": {"app_name": "Safari"}
    }
    result = await coordinator._act(action_plan, ...)
    # Should route to SystemAgent (not "open" agent)
    assert result.action_type == "system.open_application"
```

#### Re-Ask Tests

```python
def test_execute_goal_reask_on_invalid_action():
    """✅ Invalid action triggers re-ask (added to history for next iteration)"""
    # Mock reasoner returns invalid action first, then valid
    responses = [
        json.dumps({"action": "open_application", "args": {...}}),  # Missing module
        json.dumps({"module": "system", "action": "done", "args": {}})  # Valid
    ]
    
    result = await coordinator.execute_goal(...)
    
    # Should have 2 results: validation error + done
    assert len(result.action_results) == 2
    assert "validation_error" in result.action_results[0].action_type
    assert result.action_results[1].action_type == "done"
```

---

## Definition of Done (DoD)

All requirements from CORE-FOUNDATION-001 ticket:

- ✅ Test proves `{"module":"system","action":"open_application","args":{"app_name":"Safari"}}` routes to SystemAgent
- ✅ Test proves `{"action":"open_application","args":...}` without module is rejected and triggers re-ask
- ✅ No more silent normalization of `action_name/parameters` formats
- ✅ Module deduction logic removed from `_act` (no more split on "_" or ".")
- ✅ Validation against `module_action_schema.py`
- ✅ Re-ask mechanism implemented (errors added to history)
- ✅ All 17 unit tests passing

---

## Migration Guide

### For LLM Prompts

**Before:**
```python
# Loose format - sometimes worked, sometimes didn't
"""
Return:
{
  "action": "open_application",  // Missing module!
  "parameters": {"app_name": "Safari"}
}
"""
```

**After:**
```python
# Strict format - always works
"""
You MUST respond in JSON with this EXACT structure:
{
  "module": "system",
  "action": "open_application",
  "args": {"app_name": "Safari"},
  "reasoning": "Opening Safari"
}
"""
```

### For Action Routing

**Before:**
```python
# ❌ Heuristic deduction (buggy)
module = action["action"].split("_")[0]  # "open_application" → module "open" 💥
```

**After:**
```python
# ✅ Direct from validated data
module = action_plan["module"]  # Validated by schema
```

### For Error Handling

**Before:**
```python
# Silent failure or unclear errors
if not validate_action(action):
    logger.error("Invalid action")
    # What's invalid? How to fix?
```

**After:**
```python
# Structured errors with guidance
if action_plan.get("action") == "error":
    error_type = action_plan["error_type"]  # e.g., "invalid_action_schema"
    error_msg = action_plan["error"]         # e.g., "Missing 'module'. Available: system, browser, ..."
    # Error added to history → LLM sees it → LLM fixes it
```

---

## Benefits

### 1. Robustness

- **No more routing errors**: Actions always go to the correct agent
- **No more silent failures**: Invalid actions are caught and corrected
- **No more heuristics**: Module is explicitly provided and validated

### 2. Debuggability

- **Clear error messages**: "Missing 'module'" vs "Action failed"
- **Error types**: `invalid_action_schema`, `unknown_module`, `unknown_action`
- **Re-ask visibility**: See validation errors in action history

### 3. Consistency

- **Single source of truth**: `module_action_schema.py` defines all valid actions
- **Single format**: `{module, action, args}` everywhere
- **Single validation**: `validate_action_step()` used by all components

### 4. Extensibility

- **Easy to add modules**: Define in schema, register agent
- **Easy to add actions**: Add to module definition in schema
- **Schema-driven**: Tools can generate UI, docs, tests from schema

---

## Example: "Open Safari" Use Case

### Before (Buggy)

```
User: "Ouvre Safari"

ReasonerLLM: {"action": "open_application", "parameters": {"app_name": "Safari"}}
              ❌ Missing module field

ActionCoordinator._parse_response: Normalizes to {"action": "open_application", "args": {...}}
                                     ⚠️ Still no module

ActionCoordinator._act: module = "open_application".split("_")[0] = "open"
                         ❌ Tries to route to "open" agent (doesn't exist)

Result: FAILURE - "Module 'open' not registered"
```

### After (Robust)

```
User: "Ouvre Safari"

ReasonerLLM: {"action": "open_application", "args": {"app_name": "Safari"}}
              ❌ Missing module field

ActionCoordinator._parse_response: VALIDATE
                                     → Returns ERROR: "Missing 'module'. Available: system, browser, ..."

ActionCoordinator.execute_goal: Add validation error to history
                                  Continue to next iteration (re-ask)

Iteration 2:

ReasonerLLM (sees error in history): {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}
                                       ✅ Correct format

ActionCoordinator._parse_response: VALIDATE → PASS

ActionCoordinator._act: module = "system"  (from validated data)
                         ✅ Routes to SystemAgent

Result: SUCCESS - Safari opened
```

---

## See Also

- [ActionCoordinator](./14-action-coordinator.md) - OODA Loop implementation
- [Module Action Schema](../../janus/core/module_action_schema.py) - Complete schema definitions
- [Agent Registry](../../janus/core/agent_registry.py) - Agent routing
- [Tests](../../tests/test_ticket_core_foundation_001.py) - Comprehensive test suite

---

**Document Version:** 1.0  
**Last Updated:** December 2024  
**Ticket:** CORE-FOUNDATION-001  
**Status:** ✅ Implemented and Tested
