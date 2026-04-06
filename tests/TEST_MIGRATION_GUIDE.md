# Test Migration Guide: Static Planning → Dynamic ReAct Loop

## Overview

**TICKET-ARCH-007** introduces a fundamental shift in how Janus tests its execution logic. This guide helps you migrate tests from the old static planning architecture to the new dynamic ReAct/OODA loop architecture.

## Quick Summary

| Old Architecture | New Architecture |
|------------------|------------------|
| `generate_structured_plan()` | `decide_next_action()` |
| Returns full plan: `[step1, step2, ...]` | Returns single action: `{action, args, reasoning}` |
| Static, predictable steps | Dynamic, adaptive decisions |
| Site-specific logic (YouTube, etc.) | Generic, works anywhere |

## Migration Patterns

### Pattern 1: Simple Command → Action Test

**OLD WAY** ❌
```python
def test_open_app_command(self):
    """Test planning for app opening"""
    reasoner = ReasonerLLM(backend="mock")
    plan = reasoner.generate_structured_plan("Open Safari", language="en")
    
    # Validate plan structure
    self.assertEqual(len(plan["steps"]), 1)
    self.assertEqual(plan["steps"][0]["module"], "system")
    self.assertEqual(plan["steps"][0]["action"], "open_app")
    self.assertEqual(plan["steps"][0]["args"]["app_name"], "Safari")
```

**NEW WAY** ✅
```python
def test_open_app_decision(self):
    """Test next action decision for app opening"""
    reasoner = ReasonerLLM(backend="mock")
    
    action = reasoner.decide_next_action(
        user_goal="Open Safari",
        system_state={"active_app": "Finder", "url": "", "clipboard": ""},
        visual_context="[]",
        memory={},
        language="en"
    )
    
    # Validate single action
    self.assertIn("action", action)
    self.assertIn("args", action)
    self.assertIn("reasoning", action)
    # Action should be a string, not a list
    self.assertIsInstance(action["action"], str)
```

### Pattern 2: Multi-Step Workflow Test

**OLD WAY** ❌
```python
def test_browser_search_workflow(self):
    """Test complete browser search workflow"""
    reasoner = ReasonerLLM(backend="mock")
    plan = reasoner.generate_structured_plan(
        "Open Safari, go to YouTube and search for Python",
        language="en"
    )
    
    # Validate all 3 steps upfront
    self.assertEqual(len(plan["steps"]), 3)
    self.assertEqual(plan["steps"][0]["action"], "open_app")
    self.assertEqual(plan["steps"][1]["action"], "open_url")
    self.assertEqual(plan["steps"][2]["action"], "search")
```

**NEW WAY** ✅
```python
def test_browser_search_workflow(self):
    """Test multi-iteration browser search workflow"""
    reasoner = ReasonerLLM(backend="mock")
    
    # Iteration 1: Decide first action
    action1 = reasoner.decide_next_action(
        user_goal="Search for Python tutorials",
        system_state={"active_app": "Finder", "url": "", "clipboard": ""},
        visual_context="[]",
        memory={},
        language="en"
    )
    self.assertIsNotNone(action1)
    self.assertIn("action", action1)
    
    # Iteration 2: Browser open, decide next
    action2 = reasoner.decide_next_action(
        user_goal="Search for Python tutorials",
        system_state={"active_app": "Safari", "url": "https://youtube.com", "clipboard": ""},
        visual_context='[{"id": "search_box", "type": "input"}]',
        memory={},
        language="en"
    )
    self.assertIsNotNone(action2)
    
    # Test validates the PATTERN, not specific actions
    # (mock backend may return different actions)
```

### Pattern 3: Testing with Memory

**OLD WAY** ❌
```python
def test_data_extraction_plan(self):
    """Test plan for extracting data"""
    # Old architecture didn't have memory concept
    plan = reasoner.generate_structured_plan(
        "Find the CEO name",
        context={"url": "https://acme.com/about"},
        language="en"
    )
    # Would return full plan including extract_data step
```

**NEW WAY** ✅
```python
def test_data_extraction_with_memory(self):
    """Test data extraction updates memory"""
    reasoner = ReasonerLLM(backend="mock")
    
    # Before extraction: Empty memory
    action = reasoner.decide_next_action(
        user_goal="Find the CEO name",
        system_state={"active_app": "Safari", "url": "https://acme.com/about"},
        visual_context='[{"id": "ceo_name", "type": "text", "content": "Jane Smith"}]',
        memory={},
        language="en"
    )
    # Should decide to extract or navigate
    
    # After extraction: Memory populated
    action_done = reasoner.decide_next_action(
        user_goal="Find the CEO name",
        system_state={"active_app": "Safari", "url": "https://acme.com/about"},
        visual_context="[]",
        memory={"CEO_name": "Jane Smith"},
        language="en"
    )
    # Should return "done" since goal is achieved
    self.assertEqual(action_done["action"], "done")
```

### Pattern 4: NO Site-Specific Tests

**OLD WAY** ❌ - DO NOT MIGRATE
```python
def test_youtube_search_workflow(self):
    """Test YouTube-specific search workflow"""
    plan = reasoner.generate_structured_plan(
        "Go to YouTube and search for cats",
        language="en"
    )
    # Validates YouTube-specific URL patterns
    self.assertIn("youtube.com", plan["steps"][0]["args"]["url"])
```

**NEW WAY** ✅ - Generic Test
```python
def test_generic_web_search(self):
    """Test generic web navigation and search"""
    reasoner = ReasonerLLM(backend="mock")
    
    # Test with ANY website, not YouTube-specific
    action = reasoner.decide_next_action(
        user_goal="Search for information",
        system_state={"active_app": "Safari", "url": "https://example.com"},
        visual_context='[{"id": "search_input", "type": "input"}]',
        memory={},
        language="en"
    )
    
    # Validate action structure, not specific service
    self.assertIn("action", action)
    # Don't assert specific URLs or services
```

## Common Mistakes to Avoid

### ❌ Don't Test Multi-Step Plans
```python
# WRONG: Expecting multiple steps from decide_next_action
action = reasoner.decide_next_action(...)
self.assertIsInstance(action["action"], list)  # ❌ WRONG
```

### ❌ Don't Hardcode Service Names
```python
# WRONG: Testing YouTube-specific logic
self.assertIn("youtube.com", action["args"]["url"])  # ❌ WRONG
self.assertEqual(action["args"]["query"], "Burial")  # ❌ Too specific
```

### ❌ Don't Use Deprecated Methods in New Tests
```python
# WRONG: Using old planning method
plan = reasoner.generate_structured_plan(...)  # ❌ DEPRECATED
```

### ✅ Do Test Generic Behavior
```python
# RIGHT: Testing generic action structure
action = reasoner.decide_next_action(...)
self.assertIsInstance(action, dict)  # ✅ Single action
self.assertIn("action", action)      # ✅ Has action field
self.assertIsInstance(action["action"], str)  # ✅ Action is string
```

### ✅ Do Test OODA Loop Pattern
```python
# RIGHT: Test multiple iterations with state changes
for iteration in range(3):
    action = reasoner.decide_next_action(
        user_goal=goal,
        system_state=current_state,  # Changes each iteration
        visual_context=current_screen,  # Changes each iteration
        memory=memory,  # Accumulates data
        language="en"
    )
    # Execute action, update state, repeat
```

## Test Examples

See these files for complete examples:
- `tests/test_arch_001_decide_next_action.py` - Unit tests for decide_next_action
- `tests/test_arch_003_ooda_loop.py` - OODA loop integration tests
- `tests/test_arch_007_ooda_scenarios.py` - Comprehensive scenario tests

## What to Archive vs. What to Update

### Archive These Tests
- Tests validating specific JSON plan structures
- Tests with hardcoded service names (YouTube, Google, Spotify, etc.)
- Tests expecting multi-step plans from a single reasoner call
- Tests validating site-specific navigation patterns

→ Move to `tests/_archived_legacy_planning/`

### Update These Tests
- Tests of reasoner availability and initialization
- Tests of language support (FR/EN)
- Tests of error handling
- Tests that can be converted to test single action decisions

## Need Help?

Questions about migrating a specific test? Check:
1. Is it testing site-specific logic? → Archive it
2. Is it testing multi-step planning? → Rewrite as OODA loop
3. Is it testing reasoner basics? → Update to use decide_next_action
4. Not sure? → Ask the team or reference existing migrated tests

## Summary Checklist

When migrating a test file:
- [ ] Replace `generate_structured_plan()` with `decide_next_action()`
- [ ] Change assertions from validating plans to validating single actions
- [ ] Remove hardcoded service names (YouTube, Google, etc.)
- [ ] Add system_state, visual_context, and memory parameters
- [ ] Test behavior patterns, not specific outputs
- [ ] Consider multiple iterations for workflow tests
- [ ] Mark integration tests that need platform dependencies
- [ ] Update test docstrings to reflect new architecture
