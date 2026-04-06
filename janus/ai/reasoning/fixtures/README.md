# Mock Reasoner Fixtures

This directory contains JSON fixture files used by the MockReasoner for deterministic testing of the ReasonerLLM without requiring a real LLM backend.

## Purpose

The fixtures provide pre-configured responses for different types of prompts, enabling:

1. **Fast, deterministic tests** - No need for actual LLM inference
2. **Easy maintenance** - Update mock responses by editing JSON files
3. **Clear documentation** - Each fixture file documents expected response formats
4. **Isolation** - Mock logic is separate from production code

## Fixture Files

### `parse_command.json`
Mock responses for command parsing prompts (`parse_command()` method).

**Patterns:**
- `open_app` - Opening applications (Chrome, Safari, VSCode)
- `paste` - Paste commands
- `copy` - Copy commands
- `default` - Fallback for unknown commands

**Example:**
```json
{
  "patterns": {
    "open_app": {
      "keywords": ["ouvre", "lance", "open", "launch"],
      "apps": ["chrome", "safari", "vscode"],
      "response_template": {
        "intents": [...]
      }
    }
  }
}
```

### `react_decision.json`
Mock responses for ReAct decision prompts.

**Patterns:**
- `react_prompt` - Matches prompts with "ta décision", "your decision", etc.

### `burst_decision.json`
Mock responses for burst mode action generation.

**Patterns:**
- `burst_prompt` - Returns mock burst actions with stop conditions

### `reflex_action.json`
Mock responses for reflex system prompts.

**Patterns:**
- `reflex_prompt` - Quick reflex actions after failures

### `structured_plan.json`
Mock responses for V3 structured planning prompts.

**Patterns:**
- `plan_prompt` - Returns plan steps with module/action/args structure

### `v4_analysis.json`
Mock responses for V4 analysis format prompts.

**Patterns:**
- `v4_prompt` - Returns analysis + plan structure

## Usage

The MockReasoner automatically loads these fixtures during initialization:

```python
from janus.ai.reasoning.mock_reasoner import MockReasoner

# Fixtures loaded automatically from this directory
mock = MockReasoner()

# Generate response based on prompt content
response = mock.generate_response("Commande: ouvre Chrome")
```

## Adding New Fixtures

To add a new fixture pattern:

1. Edit the appropriate JSON file (or create a new one)
2. Add your pattern under `patterns` with:
   - `keywords`: List of trigger words
   - `response`: The JSON response to return
   - `response_template` (optional): Template with `{placeholders}` for dynamic values
3. Update `MockReasoner._load_fixtures()` if adding a new file
4. Add tests in `tests/test_mock_reasoner.py`

## Structure

Each fixture file follows this structure:

```json
{
  "description": "Brief description of this fixture",
  "patterns": {
    "pattern_name": {
      "keywords": ["keyword1", "keyword2"],
      "response": {
        // JSON response object
      }
    }
  }
}
```

## Notes

- Pattern matching is **case-insensitive**
- Patterns are checked in **priority order** (see `MockReasoner.generate_response()`)
- Template placeholders use `{variable_name}` syntax
- All responses must be valid JSON that matches the expected schema

## Testing

Run tests for the mock reasoner:

```bash
python3 -m unittest tests.test_mock_reasoner -v
```

## Maintenance

When updating mock responses:

1. **Update the fixture JSON** - Edit the appropriate pattern
2. **Run tests** - Ensure existing tests still pass
3. **Update tests** - Add tests for new patterns or behaviors
4. **Document** - Update this README if adding new files or patterns
