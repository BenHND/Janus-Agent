# Conversation Mode - Developer Guide

## Overview

The conversation mode enables multi-turn dialogues with context carryover, clarification questions, and implicit reference resolution. This guide explains how the system works and how to integrate it.

## Architecture

### Components

1. **ConversationManager** (`janus/runtime/core/conversation_manager.py`)
   - Manages conversation lifecycle and state
   - Handles clarification generation and resolution
   - Resolves implicit references
   - Persists conversations to database

2. **Pipeline Integration** (`janus/runtime/core/_pipeline_impl.py`)
   - `process_command_with_conversation()` orchestrates conversation flow
   - Detects clarification responses
   - Passes conversation context to command processing

3. **UI Integration** (`janus/modes/ui_mode.py`)
   - Displays clarification questions in overlay
   - Speaks clarifications via TTS
   - Re-enables microphone for user response

### Data Flow

```
User Command
    ↓
process_command_with_conversation()
    ↓
├─ Check if clarification response → Resolve → Process with context
├─ Resolve implicit references ("it", "that", etc.)
├─ Get conversation context
    ↓
process_command() with extra_context
    ↓
├─ Intent has needs_clarification=True?
│   ├─ Yes → Generate clarification → Return to UI
│   └─ No → Execute command → Add turn to conversation
    ↓
Result + Optional Clarification
```

## State Machine

```
ACTIVE (normal conversation)
    ↓
NEEDS_CLARIFICATION (waiting for user response)
    ↓
ACTIVE (after resolution) or COMPLETED
```

## Usage Examples

### Starting a Conversation

```python
from janus.runtime.core.conversation_manager import ConversationManager

manager = ConversationManager(memory_engine)
conversation = manager.start_conversation(session_id)
```

### Adding a Turn

```python
intent = Intent(
    action="open_file",
    confidence=0.9,
    parameters={"file_path": "/path/to/file.txt"},
    raw_command="open file.txt"
)

turn = manager.add_turn(
    conversation.conversation_id,
    "open file.txt",
    intent=intent
)
```

### Generating Clarification

```python
# When ambiguity is detected in intent
if intent.parameters.get("needs_clarification"):
    clarification = manager.generate_clarification(
        original_command="open chrome",
        ambiguity_type="ambiguous_app",
        options=["Google Chrome", "Chrome Canary", "Chromium"]
    )
    
    # Add turn with clarification
    manager.add_turn(
        conversation.conversation_id,
        "open chrome",
        intent=intent,
        clarification=clarification,
        state=ConversationState.NEEDS_CLARIFICATION
    )
    
    # Return clarification to UI
    formatted = f"{clarification.question}\n"
    for i, option in enumerate(clarification.options, 1):
        formatted += f"{i}. {option}\n"
    
    return result, formatted
```

### Resolving Clarification

```python
# User responds with "1" or "Google Chrome"
success, context = manager.resolve_clarification(
    conversation.conversation_id,
    user_response="1"
)

if success:
    # context["selected_option"] = "Google Chrome"
    # context["original_command"] = "open chrome"
    
    # Process with resolved context
    result = process_command(
        context["original_command"],
        extra_context=context
    )
```

### Implicit Reference Resolution

```python
# Turn 1: "open document.txt"
# Turn 2: "save it"

resolved = manager.resolve_implicit_references(
    "save it",
    conversation.conversation_id
)
# Result: "save document.txt"
```

## Integration Points

### 1. NLU/Reasoner Integration

To detect ambiguities and trigger clarifications, the NLU/Reasoner should:

```python
# In reasoner or NLU module
if detect_ambiguity(command):
    intent.parameters["needs_clarification"] = True
    intent.parameters["ambiguity_type"] = "ambiguous_app"  # or "multiple_files", etc.
    intent.parameters["options"] = ["Option 1", "Option 2", "Option 3"]
```

### 2. UI Display Integration

The UI mode already handles clarifications in `on_command_finished()`:

```python
def on_command_finished(result, clarification):
    if clarification:
        # Display in overlay
        overlay.signals.append_transcript_signal.emit(f"❓ {clarification}")
        
        # Speak via TTS
        asyncio.run_coroutine_threadsafe(
            speak_feedback(tts, clarification),
            listening_state.event_loop
        )
        
        # Re-enable microphone for response
        listening_state.active = True
        overlay.mic_enabled = True
        start_recording_worker()
```

### 3. Context Usage

Commands receive conversation context via `extra_context`:

```python
extra_context = {
    "conversation_history": ["open vscode", "open main.py"],
    "recent_entities": {
        "app_name": "vscode",
        "file_path": "/project/main.py"
    },
    "selected_option": "Google Chrome"  # from clarification
}

result = process_command(command, extra_context=extra_context)
```

## Database Schema

Conversations are persisted using MemoryEngine's conversation tables:

```sql
-- Conversations
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Conversation turns
CREATE TABLE conversation_turns (
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    system_response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Testing

### Unit Tests

```bash
# Run ConversationManager tests
python3 -m unittest tests.test_conversation_manager -v

# Run integration tests
python3 -m unittest tests.test_conversation_integration -v
```

### Test Coverage

- ✅ Conversation lifecycle (start, add_turn, complete)
- ✅ Clarification generation and resolution (numeric + text)
- ✅ Implicit reference resolution with word boundaries
- ✅ Context carryover between turns
- ✅ Multiple clarifications in sequence
- ✅ Edge cases (empty responses, invalid selections)

## Best Practices

### 1. Clarification Questions

- Keep questions clear and concise
- Provide 2-5 options maximum
- Support both numeric (1, 2, 3) and text matching
- Use French language for questions

### 2. Implicit References

- Prioritize entity types: file_path > app_name > url > target
- Use word boundary matching to avoid partial replacements
- Log all reference resolutions for debugging

### 3. Context Management

- Track last 5 commands for context
- Extract entities from intent parameters
- Clear context when conversation completes

### 4. Error Handling

- Gracefully handle failed clarifications
- Provide fallback behavior when context is missing
- Log warnings for persistence failures

## Troubleshooting

### Clarification Not Working

1. Check intent has `needs_clarification=True` in parameters
2. Verify `options` list is provided
3. Check UI is displaying clarification text
4. Verify microphone re-enables after TTS

### Implicit References Not Resolving

1. Check conversation has previous turns
2. Verify last turn has intent with parameters
3. Check reference keywords match ("it", "that", etc.)
4. Review logs for resolution attempts

### Context Not Carrying Over

1. Verify conversation is active (not completed)
2. Check turns are being added successfully
3. Review `get_context_for_command()` output
4. Ensure `extra_context` is passed to `process_command()`

## Performance Considerations

- ConversationManager operations: <5ms (in-memory)
- Database persistence: <10ms (async)
- Reference resolution: <1ms (regex matching)
- Context retrieval: <5ms (recent turns only)

## Future Enhancements

Potential improvements:

1. **Semantic Reference Resolution** - Use LLM for better context understanding
2. **Conversation Analytics** - Track patterns and success rates
3. **Multi-session Context** - Carry context across app restarts
4. **Proactive Clarification** - Detect ambiguity before execution
5. **Conversation Branching** - Support undo/redo in conversations

## API Reference

See `janus/runtime/core/conversation_manager.py` for complete API documentation.

### Key Methods

- `start_conversation(session_id)` - Begin new conversation
- `add_turn(conv_id, command, intent, ...)` - Add command to conversation
- `generate_clarification(command, type, options)` - Create clarification question
- `resolve_clarification(conv_id, response)` - Process user's clarification response
- `resolve_implicit_references(command, conv_id)` - Replace "it", "that", etc.
- `get_context_for_command(conv_id)` - Get conversation context summary
- `complete_conversation(conv_id)` - End conversation

## Related Files

- `janus/runtime/core/conversation_manager.py` - Core implementation
- `janus/runtime/core/_pipeline_impl.py` - Pipeline integration
- `janus/modes/ui_mode.py` - UI integration
- `tests/test_conversation_manager.py` - Unit tests
- `tests/test_conversation_integration.py` - Integration tests
