# Unified Pipeline Workflows

**Extract → Process → Output**

Janus implements a unified pipeline that can extract data from any source, process it with LLM, and send it to any destination. This document describes the key workflows enabled by this architecture.

## Overview

The unified pipeline consists of three main stages:

1. **Extract**: Get data from any source (web, Teams, Slack, Email, native apps)
2. **Process**: Transform the data using LLM (summarize, analyze, rewrite, extract keywords)
3. **Output**: Send results to any destination (clipboard, email, messaging, file)

### Pipeline Chaining with `input_from`

Workflows use the `input_from` parameter to chain outputs from one step to the next:

```json
{
  "steps": [
    {"module": "browser", "action": "get_page_content", "step_id": "extract"},
    {"module": "llm", "action": "summarize", "args": {"input_from": "extract"}},
    {"module": "ui", "action": "paste"}
  ]
}
```

The `ExecutionContext` automatically resolves `input_from` references:
- `"last_output"` - Gets the most recent output
- `"step.0"` - Gets output from step 0
- `"extract"` - Gets output from step with id "extract"

## Implemented Workflows

### 1. Web → LLM → Clipboard

**Use Case**: "Summarize this article and paste it in Notes"

Extract clean text from a web page, summarize it with LLM, and paste the summary.

**Pipeline**:
```json
{
  "steps": [
    {
      "module": "browser",
      "action": "get_page_content",
      "args": {},
      "step_id": "web_extract"
    },
    {
      "module": "llm",
      "action": "summarize",
      "args": {
        "input_from": "web_extract",
        "max_length": 200
      },
      "step_id": "summary"
    },
    {
      "module": "ui",
      "action": "paste",
      "args": {}
    }
  ]
}
```

**Components**:
- **Extract**: `browser.get_page_content()` - Uses trafilatura for clean HTML parsing
- **Process**: `llm.summarize()` - Generates concise summary
- **Output**: `ui.paste()` - Pastes to active application

**Performance**: < 5s (excluding LLM processing time)

---

### 2. Teams → LLM → Email

**Use Case**: "Summarize the Teams conversation and email it to my manager"

Read Teams channel history, generate summary, and send via email.

**Pipeline**:
```json
{
  "steps": [
    {
      "module": "messaging",
      "action": "summarize_thread",
      "args": {
        "platform": "teams",
        "channel": "general",
        "team_id": "team123",
        "limit": 50
      },
      "step_id": "teams_summary"
    },
    {
      "module": "email",
      "action": "send",
      "args": {
        "to": "manager@example.com",
        "subject": "Teams Discussion Summary",
        "input_from": "teams_summary"
      }
    }
  ]
}
```

**Components**:
- **Extract**: `messaging.summarize_thread()` - Reads and summarizes Teams messages
- **Output**: `email.send()` - Sends summary via Microsoft 365

**Note**: Requires Teams and O365 authentication configured.

---

### 3. Native App → LLM → Clipboard

**Use Case**: "Copy the text from this window and summarize it"

Extract text from any native application (Notes, TextEdit, etc.), summarize, and paste.

**Pipeline**:
```json
{
  "steps": [
    {
      "module": "ui",
      "action": "extract_text",
      "args": {},
      "step_id": "app_text"
    },
    {
      "module": "llm",
      "action": "summarize",
      "args": {
        "input_from": "app_text",
        "max_length": 150
      },
      "step_id": "summary"
    },
    {
      "module": "ui",
      "action": "paste",
      "args": {}
    }
  ]
}
```

**Components**:
- **Extract**: `ui.extract_text()` - Uses Accessibility APIs or clipboard fallback
- **Process**: `llm.summarize()` - Generates summary
- **Output**: `ui.paste()` - Pastes summary

**Supported Apps**: Any macOS application with accessibility support (Notes, TextEdit, Pages, etc.)

---

### 4. Email → LLM → Slack

**Use Case**: "Summarize recent emails from John and post to #team channel"

Fetch emails, generate summary, and post to Slack.

**Pipeline**:
```json
{
  "steps": [
    {
      "module": "email",
      "action": "get_recent_emails",
      "args": {
        "sender": "john@example.com",
        "limit": 10
      },
      "step_id": "emails"
    },
    {
      "module": "llm",
      "action": "summarize",
      "args": {
        "input_from": "emails",
        "max_length": 250
      },
      "step_id": "email_summary"
    },
    {
      "module": "messaging",
      "action": "post_message",
      "args": {
        "platform": "slack",
        "channel": "#team",
        "input_from": "email_summary"
      }
    }
  ]
}
```

**Components**:
- **Extract**: `email.get_recent_emails()` - Fetches emails from O365
- **Process**: `llm.summarize()` - Creates summary
- **Output**: `messaging.post_message()` - Posts to Slack channel

**Note**: Requires both O365 and Slack authentication configured.

---

## Advanced Features

### Multi-Step Processing

You can chain multiple processing steps:

```json
{
  "steps": [
    {"module": "browser", "action": "get_page_content", "step_id": "raw"},
    {"module": "llm", "action": "extract_keywords", "args": {"input_from": "raw", "count": 5}, "step_id": "keywords"},
    {"module": "llm", "action": "summarize", "args": {"input_from": "raw", "max_length": 200}, "step_id": "summary"},
    {"module": "llm", "action": "rewrite", "args": {"input_from": "summary", "style": "professional"}, "step_id": "polished"},
    {"module": "ui", "action": "paste", "args": {"input_from": "polished"}}
  ]
}
```

### Conditional Workflows

Use conditional steps for adaptive behavior:

```json
{
  "steps": [
    {
      "type": "conditional",
      "condition": "app_not_open('Notes')",
      "if_true": [
        {"module": "system", "action": "open_app", "args": {"app_name": "Notes"}}
      ]
    },
    {"module": "ui", "action": "extract_text"},
    {"module": "llm", "action": "summarize", "args": {"input_from": "last_output"}},
    {"module": "ui", "action": "paste"}
  ]
}
```

### Parallel Extraction

Extract from multiple sources simultaneously:

```json
{
  "steps": [
    {
      "type": "parallel",
      "steps": [
        {"module": "browser", "action": "get_page_content", "step_id": "web"},
        {"module": "messaging", "action": "read_channel_history", "args": {"platform": "slack", "channel": "#general"}, "step_id": "slack"}
      ]
    },
    {
      "module": "llm",
      "action": "analyze",
      "args": {
        "text": "Combine web and slack: {web} and {slack}"
      }
    }
  ]
}
```

## Implementation Details

### Trafilatura Integration

The `browser.get_page_content()` action now uses [trafilatura](https://github.com/adbar/trafilatura) for intelligent HTML parsing:

- Extracts main content while removing navigation, ads, and boilerplate
- Preserves article structure and readability
- Falls back to simple `innerText` if trafilatura is unavailable

### Accessibility-Based Text Extraction

The `ui.extract_text()` action uses a two-tier approach:

1. **Primary**: Accessibility APIs (macOS AXUIElement)
   - Fast (< 100ms)
   - Reliable for apps with proper accessibility support
   
2. **Fallback**: Clipboard method (Cmd+A, Cmd+C)
   - Works with any application
   - Slightly slower (< 300ms)
   - May modify user's clipboard temporarily

### Email Integration

The `EmailProvider` now supports sending emails via Microsoft 365:

```python
email_provider.send_email(
    to="recipient@example.com",
    subject="Summary",
    body=summary_text,
    cc=["cc@example.com"],  # Optional
    body_type="text"  # or "html"
)
```

## Testing

Comprehensive E2E tests are available in `tests/test_workflows_e2e.py`:

```bash
# Run all workflow tests
pytest tests/test_workflows_e2e.py -v

# Run specific workflow test
pytest tests/test_workflows_e2e.py::test_workflow_web_to_llm_to_clipboard -v
```

## Performance Benchmarks

| Workflow | Typical Latency | Notes |
|----------|----------------|-------|
| Web → LLM → Clipboard | 3-5s | Excluding LLM processing |
| App → LLM → Clipboard | 2-4s | Excluding LLM processing |
| Teams → LLM → Email | 4-6s | Excluding LLM processing |
| Email → LLM → Slack | 5-7s | Excluding LLM processing |

**Note**: LLM processing time varies by model and content length (typically 2-10s for local models, 1-3s for API-based models).

## Dependencies

- **trafilatura**: Web content extraction (optional but recommended)
  ```bash
  pip install trafilatura
  ```

- **O365**: Microsoft 365 integration for email and Teams
  ```bash
  pip install O365
  ```

- **Slack SDK**: Slack integration
  ```bash
  pip install slack-sdk
  ```

## Future Enhancements

See the [issue tracker](https://github.com/BenHND/Janus/issues) for planned features:

- Windows UIAutomation support for `ui.extract_text()`
- Gmail API integration
- Discord and Telegram support
- Notion and Obsidian integration
- File system workflows (read → process → save)

## See Also

- [Architecture Overview](../architecture/README.md)
- [Agent System](../architecture/05-agent-architecture.md)
- [ExecutionContext](../developer/execution-context.md)
- [Test Guide](../../TESTING_GUIDE_TICKET_1.md)
