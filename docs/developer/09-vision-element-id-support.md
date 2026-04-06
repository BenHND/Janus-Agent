# Vision Element ID Support (VISION-FOUNDATION-001)

## Overview

This document describes the element_id support system that enables the vision stack to resolve Set-of-Marks (SOM) element IDs to clickable screen coordinates.

**Ticket**: VISION-FOUNDATION-001 — Vision exploitable: Support element_id (SOM) end-to-end

## Problem Statement

Previously, when the vision system generated element IDs (e.g., `text_22`, `button_5`) via Set-of-Marks, the action execution layer couldn't use them directly. The `click_viz` function would treat them as text to search for, which would fail since element IDs aren't visible text on screen.

This created a disconnect: **vision could identify elements, but execution couldn't act on them**.

## Solution

The solution implements end-to-end element_id support across the vision stack:

1. **ElementFinder.find_element_by_id()** - Resolves element IDs using SOM cache
2. **ActionExecutor** - Detects and handles element IDs in click/select/extract
3. **VisionActionMapper** - Passes SOM engine and element_id through the chain
4. **UIAgent** - Accepts and forwards element_id from LLM actions

## Architecture

### Component Flow

```
SetOfMarksEngine (SOM Cache)
    ↓ (holds element_id → bbox mapping)
ElementFinder.find_element_by_id()
    ↓ (converts InteractiveElement → ElementMatch)
ActionExecutor.click_viz()
    ↓ (detects element_id pattern, uses find_element_by_id)
VisionActionMapper
    ↓ (passes element_id parameter)
UIAgent._click()
    ↓ (extracts element_id from args)
ActionCoordinator._act()
    ↓ (injects vision_engine in context)
LLM Reasoner
```

### Data Flow

```json
// LLM generates action with element_id
{
  "module": "ui",
  "action": "click",
  "args": {
    "element_id": "button_5"
  }
}

// ActionCoordinator passes vision_engine in context
context = {
  "vision_engine": <SetOfMarksEngine instance>
}

// UIAgent extracts element_id and passes to VisionActionMapper
mapper = VisionActionMapper(som_engine=context["vision_engine"])
result = mapper.click_viz(target="button_5", element_id="button_5")

// ActionExecutor detects element_id
if element_id:
    element = element_finder.find_element_by_id(element_id)

// ElementFinder resolves via SOM
som_element = som_engine.get_element_by_id("button_5")
# Returns InteractiveElement with bbox=(x, y, width, height)

// Convert to ElementMatch and click
element_match = ElementMatch(x=x, y=y, width=w, height=h, ...)
pyautogui.click(element_match.center_x, element_match.center_y)
```

## API Reference

### ElementFinder.find_element_by_id()

```python
def find_element_by_id(
    self,
    element_id: str,
    region: Optional[Tuple[int, int, int, int]] = None,
    scroll_if_not_found: bool = False,
) -> Optional[ElementMatch]:
    """
    Find UI element by Set-of-Marks ID

    Args:
        element_id: Element ID from Set-of-Marks (e.g., "text_22", "button_5")
        region: Optional region (not used for ID lookup, kept for API consistency)
        scroll_if_not_found: If True, attempt scrolling (not currently implemented)

    Returns:
        ElementMatch if found, None otherwise
    """
```

**Example:**

```python
from janus.vision.element_finder import ElementFinder
from janus.vision.set_of_marks import SetOfMarksEngine

som_engine = SetOfMarksEngine()
finder = ElementFinder(som_engine=som_engine)

# Find element by ID
element = finder.find_element_by_id("button_5")
if element:
    print(f"Found: {element.text} at ({element.center_x}, {element.center_y})")
```

### ActionExecutor.click_viz() with element_id

```python
def click_viz(
    self,
    target: str,
    region: Optional[Tuple[int, int, int, int]] = None,
    verify: bool = True,
    element_id: Optional[str] = None
) -> ActionResult:
    """
    Vision-based click action - finds and clicks an element

    Args:
        target: Text or element_id to click
        region: Optional region to search
        verify: Enable post-action verification
        element_id: Explicit element ID from Set-of-Marks

    Returns:
        ActionResult with details
    """
```

**Example:**

```python
from janus.vision.action_executor import ActionExecutor
from janus.vision.element_finder import ElementFinder

finder = ElementFinder(som_engine=som_engine)
executor = ActionExecutor(element_finder=finder)

# Method 1: Explicit element_id parameter
result = executor.click_viz(target="button_5", element_id="button_5")

# Method 2: Auto-detection (target matches pattern)
result = executor.click_viz(target="text_22")

# Method 3: Regular text (fallback)
result = executor.click_viz(target="Submit Button")
```

## Element ID Pattern Detection

The system automatically detects element IDs using this pattern:

```python
# Pattern: word_number (e.g., "text_22", "button_5")
has_underscore = "_" in target
last_part_has_digit = any(c.isdigit() for c in target.split("_")[-1])
is_element_id = has_underscore and last_part_has_digit
```

**Detected as element_id:**
- `text_22` ✓
- `button_5` ✓
- `icon_3` ✓
- `link_100` ✓
- `input_1` ✓

**NOT detected as element_id:**
- `Submit Button` ✗
- `Click here` ✗
- `text` ✗ (no number)
- `button` ✗ (no number)
- `22_text` ✗ (number before underscore)

## Fallback Mechanism

The system implements a robust fallback chain:

```
1. Try explicit element_id parameter
   ↓ (if fails or not provided)
2. Try auto-detect ID pattern in target
   ↓ (if detected, lookup in SOM)
3. If ID lookup fails, fallback to text search
   ↓ (if still not found)
4. Return error
```

**Example:**

```python
# If LLM provides element_id="text_22" but it's not in SOM cache,
# the system will automatically try text search for "text_22"
result = executor.click_viz(target="text_22", element_id="text_22")
# First: tries find_element_by_id("text_22") → fails
# Then: tries find_element_by_text("text_22") → may succeed if text is visible
```

## Integration Points

### 1. ActionCoordinator

ActionCoordinator injects the `vision_engine` into the execution context:

```python
# In ActionCoordinator._act()
ctx = {
    "vision_engine": self._vision_engine,  # SetOfMarksEngine instance
    # ... other context
}

result = await agent.execute(
    action=action_step["action"],
    args=action_step.get("args", {}),
    context=ctx
)
```

### 2. UIAgent

UIAgent extracts `element_id` from args and passes it to VisionActionMapper:

```python
# In UIAgent._click()
element_id = args.get("element_id")
som_engine = context.get("vision_engine")

mapper = VisionActionMapper(som_engine=som_engine)
result = mapper.click_viz(
    target=target_name,
    element_id=element_id,
    verify=True
)
```

### 3. LLM Actions

The LLM can now use element_id in actions:

```json
{
  "module": "ui",
  "action": "click",
  "args": {
    "element_id": "button_5"
  }
}
```

Or for backward compatibility:

```json
{
  "module": "ui",
  "action": "click",
  "args": {
    "text": "text_22"
  }
}
```

## Testing

### Unit Tests

```bash
python -m unittest tests.test_vision_element_id_support
```

### Manual Testing

```bash
python test_element_id_manual.py
```

### Integration Testing

Create a script that:
1. Initializes SetOfMarksEngine
2. Captures elements from screen
3. Tries to click using element_id
4. Verifies the click succeeded

```python
from janus.vision.set_of_marks import SetOfMarksEngine
from janus.vision.vision_action_mapper import VisionActionMapper

# Initialize SOM
som = SetOfMarksEngine()
elements = som.capture_elements()

# Print available elements
for elem in elements:
    print(f"{elem.element_id}: {elem.text} at {elem.bbox}")

# Click using element_id
mapper = VisionActionMapper(som_engine=som)
result = mapper.click_viz(target="button_5", element_id="button_5")
print(f"Click result: {result.success}")
```

## Performance Considerations

### SOM Cache

- SetOfMarksEngine caches captured elements for 2 seconds by default
- This prevents redundant screen captures and OCR operations
- Cache is automatically invalidated after actions that change screen state

### Lookup Performance

- `find_element_by_id()` is **O(n)** where n = number of cached elements
- Typically < 50 elements → very fast lookup
- Much faster than OCR-based text search

### Memory Usage

- Each InteractiveElement: ~200-500 bytes
- Typical cache size: 30-50 elements = 10-25 KB
- Negligible memory overhead

## Troubleshooting

### Element ID not found

**Symptom**: `find_element_by_id()` returns None

**Possible causes:**
1. Element not in SOM cache (screen changed)
2. SOM engine not initialized
3. Vision components not available

**Solution:**
```python
# Check if SOM is available
if som_engine and som_engine.is_available():
    # Force refresh SOM cache
    elements = som_engine.capture_elements(force_refresh=True)
    
    # Check if element exists
    element = som_engine.get_element_by_id("button_5")
    if element:
        print(f"Found: {element}")
    else:
        print("Element not in cache")
else:
    print("SOM engine not available")
```

### Clicking wrong element

**Symptom**: Click occurs but at wrong location

**Possible causes:**
1. Bounding box coordinates are window-relative, not screen-relative
2. Screen resolution/scaling issues
3. Multiple monitors

**Solution:**
- Verify bbox coordinates match actual element position
- Check if coordinate conversion is needed for your platform
- Ensure screenshot capture matches click coordinate space

### Fallback not working

**Symptom**: Text fallback doesn't trigger when ID fails

**Possible causes:**
1. ID pattern detected but text search not attempted
2. Logic error in fallback chain

**Solution:**
```python
# In ActionExecutor.click_viz(), ensure fallback logic:
if element_id:
    element = self.element_finder.find_element_by_id(element_id)
elif "_" in target and any(c.isdigit() for c in target.split("_")[-1]):
    element = self.element_finder.find_element_by_id(target)
    if not element:  # ← FALLBACK
        element = self.element_finder.find_element_by_text(target)
else:
    element = self.element_finder.find_element_by_text(target)
```

## Future Improvements

### Planned Enhancements

1. **Spatial context**: Use element proximity for disambiguation
2. **Confidence thresholding**: Skip low-confidence elements
3. **Multi-screen support**: Handle multiple monitors correctly
4. **Caching strategy**: Smarter cache invalidation
5. **Performance metrics**: Track ID resolution success rate

### Known Limitations

1. **No scrolling support**: `scroll_if_not_found` not implemented for ID lookup
2. **Cache staleness**: 2-second cache may be stale for rapidly changing UIs
3. **Pattern ambiguity**: Some legitimate text like "step_1" might be detected as ID

## References

- [Set-of-Marks Paper](https://github.com/microsoft/SoM)
- [VISION-FOUNDATION-001 Issue](../../)
- [ElementFinder Source](../../janus/vision/element_finder.py)
- [ActionExecutor Source](../../janus/vision/action_executor.py)
- [Tests](../../tests/test_vision_element_id_support.py)
