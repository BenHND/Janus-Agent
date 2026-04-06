# The OODA Loop: Dynamic Execution Architecture

> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---


## Overview

Janus uses a **Dynamic OODA Loop** (Observe-Orient-Decide-Act) for command execution. Instead of planning all steps upfront, the system makes decisions one at a time based on what it actually sees on screen.

## Why Dynamic Execution?

### Traditional Approach: Static Planning

Traditional automation tries to predict all steps before executing:

```python
# Plan everything upfront
plan = create_plan("Find CEO of Acme Corp")
# Returns: [step1, step2, step3, ...]
# Execute all steps blindly
```

**Problems:**
- **Brittle**: Fails when UI differs from expectations
- **Rigid**: Cannot adapt to unexpected results
- **Blind**: Doesn't see what's actually on screen
- **Site-Specific**: Requires hardcoded rules for each website

### Janus Approach: OODA Loop

Janus decides one action at a time based on current observation:

```python
# Decide next action based on what's visible NOW
action = decide_next_action(
    user_goal="Find CEO of Acme Corp",
    screen_elements=[...],  # What's actually visible
    system_state={...},      # Current app, URL, etc.
    memory={...}             # What we learned so far
)
# Returns ONE action
# Execute it, observe result, decide again
```

**Benefits:**
- **Adaptive**: Adjusts to actual UI state
- **Visual**: Uses real visible elements
- **Generic**: Works on any website/application
- **Recoverable**: Handles unexpected states naturally

## The OODA Loop Cycle

```
┌─────────────────────────────────────┐
│          User Command               │
│    "Find CEO of Acme Corp"          │
└────────────┬────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  1. OBSERVE        │
    │  • Screenshot      │
    │  • Detect elements │
    │  • Read state      │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │  2. ORIENT         │
    │  • Analyze context │
    │  • Review memory   │
    │  • Understand goal │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │  3. DECIDE         │
    │  • LLM chooses     │
    │    ONE next action │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │  4. ACT            │
    │  • Execute action  │
    │  • Update memory   │
    └────────┬───────────┘
             │
             ▼
        Goal achieved?
             │
      ┌──────┴──────┐
     Yes            No
      │              │
   DONE       Loop to OBSERVE
```

## Loop Components

### 1. Observe - Screen Analysis

The system captures what's visible:

**Screen Elements:**
```json
[
  {
    "id": "search_box_1",
    "type": "input",
    "label": "Search",
    "position": {"x": 100, "y": 50}
  },
  {
    "id": "ceo_name_7",
    "type": "text",
    "content": "John Smith, CEO"
  },
  {
    "id": "submit_btn_3",
    "type": "button",
    "label": "Submit"
  }
]
```

**System State:**
```json
{
  "active_app": "Safari",
  "window_title": "About Us - Acme Corp",
  "url": "https://acme.com/about",
  "clipboard": ""
}
```

### 2. Orient - Context Analysis

The system reviews:
- User's original goal
- Current screen state
- What it learned so far (memory)
- Previous actions taken

### 3. Decide - LLM Reasoning

The LLM decides the next single action:

```json
{
  "action": "extract_data",
  "args": {
    "element_id": "ceo_name_7",
    "data_name": "CEO_name"
  },
  "reasoning": "Found the CEO name in element ceo_name_7. Extracting it to memory."
}
```

### 4. Act - Execute & Update

The system:
1. Executes the chosen action
2. Updates memory with results
3. Prepares for next observation

## Available Actions

The reasoner can choose from these atomic actions:

### UI Interaction
- **click** - Click an element
  ```json
  {"action": "click", "args": {"element_id": "btn_123"}}
  ```

- **type_text** - Type into input field
  ```json
  {"action": "type_text", "args": {"element_id": "input_456", "text": "query"}}
  ```

- **scroll** - Scroll the page
  ```json
  {"action": "scroll", "args": {"direction": "down", "amount": 500}}
  ```

### Application Control
- **open_app** - Launch application
  ```json
  {"action": "open_app", "args": {"app_name": "Chrome"}}
  ```

- **navigate** - Go to URL
  ```json
  {"action": "navigate", "args": {"url": "https://example.com"}}
  ```

### Data Operations
- **extract_data** - Save visible information
  ```json
  {"action": "extract_data", "args": {"element_id": "text_789", "data_name": "CEO_name"}}
  ```

- **read_clipboard** - Get clipboard content
  ```json
  {"action": "read_clipboard", "args": {}}
  ```

### Control Flow
- **done** - Task complete
  ```json
  {"action": "done", "args": {"message": "Found CEO: John Smith"}}
  ```

- **fail** - Cannot proceed
  ```json
  {"action": "fail", "args": {"reason": "CEO information not found on page"}}
  ```

## Example Execution

Let's see the OODA loop in action for: "Find CEO of Acme Corp"

### Iteration 1
**Observe:**
- Safari is open
- No specific page loaded

**Orient:**
- Need to find company website first

**Decide:**
```json
{"action": "navigate", "args": {"url": "https://acme.com/about"}}
```

**Act:**
- Navigate to Acme Corp about page

### Iteration 2
**Observe:**
- About page loaded
- See heading "Leadership Team"
- See text "John Smith, CEO"

**Orient:**
- Found potential CEO name
- Should extract it

**Decide:**
```json
{"action": "extract_data", "args": {"element_id": "ceo_text_42", "data_name": "CEO"}}
```

**Act:**
- Save "John Smith" to memory

### Iteration 3
**Observe:**
- Memory now contains CEO name
- Goal achieved

**Orient:**
- Have all required information

**Decide:**
```json
{"action": "done", "args": {"message": "CEO is John Smith"}}
```

**Act:**
- Complete execution
- Return success

## Key Advantages

### Adaptability
The loop adapts to any UI state. If a page takes time to load, or displays differently than expected, the next observation will see the actual state and decide accordingly.

### Visual Grounding
Actions reference actual visible elements by ID. No guessing about selectors or coordinates - the system sees what the user sees.

### Generic Architecture
Zero site-specific code. The same loop works on:
- Any website (Google, Amazon, GitHub, etc.)
- Any application (Finder, Terminal, Excel, etc.)
- Any UI framework (web, native, electron, etc.)

### Error Recovery
If an action fails, the next observation will see the error state and the reasoner can choose a recovery action or alternative approach.

### Transparency
Each iteration has clear reasoning. You can see:
- What the system observed
- Why it chose that action
- What happened when it executed

## Implementation

### ActionCoordinator
The `ActionCoordinator` class orchestrates the OODA loop:

```python
from janus.core import ActionCoordinator

coordinator = ActionCoordinator()

result = await coordinator.execute_goal(
    user_goal="Find CEO of Acme Corp",
    intent=parsed_intent,
    session_id="session_123",
    request_id="req_456"
)
```

### ReasonerLLM
The `ReasonerLLM` makes decisions:

```python
from janus.reasoning import ReasonerLLM

reasoner = ReasonerLLM()

action = await reasoner.decide_next_action(
    user_goal=user_goal,
    visual_context=elements,
    system_state=state,
    memory=memory
)
```

### Vision Engine
The vision system provides observations:

```python
from janus.vision import SetOfMarksEngine

vision = SetOfMarksEngine()

elements = await vision.detect_elements()
# Returns list of interactive elements with IDs
```

## Configuration

### Max Iterations
Prevent infinite loops:

```python
coordinator = ActionCoordinator(max_iterations=20)
```

### Vision Settings
Control element detection:

```python
vision = SetOfMarksEngine(
    cache_ttl=2.0,  # Cache screenshots for 2 seconds
    enable_cache=True
)
```

## Best Practices

### For Users
- Be specific about your goals
- The system will figure out the steps
- Trust the loop to adapt to UI changes

### For Developers
- Keep actions atomic (one clear purpose)
- Let the reasoner handle complex logic
- Don't add site-specific workarounds
- Trust visual grounding over selectors

## Troubleshooting

**Loop takes many iterations:**
- Usually means the goal is complex
- Check if intermediate steps are working
- Review the reasoning at each step

**Loop hits max iterations:**
- Goal might be impossible
- UI might have changed significantly
- Check if elements are actually visible

**Actions fail repeatedly:**
- Element IDs might be unstable
- Vision detection might need tuning
- Check if page is fully loaded

## See Also

- [ActionCoordinator](14-action-coordinator.md) - Implementation details
- [Visual Grounding](12-smart-self-healing.md) - Set-of-Marks system
- [Agent Architecture](04-agent-architecture.md) - Action execution
- [LLM-First Principle](03-llm-first-principle.md) - Design philosophy
