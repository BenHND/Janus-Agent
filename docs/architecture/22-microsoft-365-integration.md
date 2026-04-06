# Microsoft 365 Integration: Native Calendar & Email Providers

> **TICKET-APP-001**: Native Microsoft 365 / Outlook Connector
> 
> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---

## Overview

The Microsoft 365 integration provides native access to calendar and email data through structured APIs, eliminating the need for screenshot-based data extraction. This significantly improves performance, accuracy, and user experience for calendar and email-related queries.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Context Engine                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │ CalendarProvider │        │  EmailProvider   │          │
│  │                  │        │                  │          │
│  │ - O365 Account   │        │ - O365 Account   │          │
│  │ - Schedule API   │        │ - Mailbox API    │          │
│  │ - Event queries  │        │ - Message queries│          │
│  └────────┬─────────┘        └────────┬─────────┘          │
│           │                           │                     │
│           └───────────┬───────────────┘                     │
│                       │                                     │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  O365 Library   │
              │  (python-o365)  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Microsoft Graph │
              │      API        │
              └─────────────────┘
```

### Data Flow

1. **User Query** → "What's my next meeting?"
2. **LLM Reasoner** → Requests calendar context
3. **Context Engine** → Calls `CalendarProvider.get_upcoming_events()`
4. **CalendarProvider** → Queries Microsoft Graph API via O365
5. **Microsoft Graph** → Returns structured event data
6. **CalendarProvider** → Formats events into standard dictionary
7. **Context Engine** → Injects structured data into LLM context
8. **LLM** → Generates response using structured data

**Performance**: 100-300ms (vs. 2-5s with screenshot + OCR)

## Components

### CalendarProvider

**Purpose**: Provides structured access to Microsoft 365 calendar events

**Key Methods**:
- `get_upcoming_events(limit=5)` - Retrieve next N events
- `get_current_event()` - Detect active meetings
- `get_next_event()` - Get immediate next event
- `authenticate()` - OAuth2 authentication flow
- `get_context()` - Full calendar context for LLM

**Event Data Structure**:
```python
{
    'title': str,           # Meeting title
    'start': str,          # ISO 8601 timestamp
    'end': str,            # ISO 8601 timestamp
    'location': str,       # Location or online meeting link
    'attendees': [         # List of participants
        {
            'name': str,
            'email': str
        }
    ],
    'organizer': {         # Meeting organizer
        'name': str,
        'email': str
    },
    'is_online_meeting': bool,
    'body': str           # First 200 chars of description
}
```

### EmailProvider

**Purpose**: Provides structured access to Microsoft 365 emails

**Key Methods**:
- `fetch_unread(limit=10)` - Retrieve unread emails
- `get_recent_emails(limit)` - Access recent inbox messages
- `search_emails(query, limit)` - Search by subject/sender/content
- `get_recent_senders(limit)` - Track recent senders
- `get_unread_count()` - Count unread messages
- `authenticate()` - OAuth2 authentication flow
- `get_context()` - Full email context for LLM

**Email Data Structure**:
```python
{
    'subject': str,        # Email subject
    'sender': str,         # "Name <email@example.com>"
    'sender_name': str,    # Sender display name
    'sender_email': str,   # Sender email address
    'timestamp': str,      # ISO 8601 timestamp
    'is_read': bool,       # Read status
    'is_important': bool,  # Importance flag
    'body': str,           # Preview text (first 500 chars)
    'has_attachments': bool
}
```

## Authentication & Security

### OAuth2 Flow

1. **App Registration**: User registers app in Azure Portal
2. **Credentials**: Client ID + Client Secret configured
3. **Scopes**: Delegated permissions (Calendars.Read, Mail.Read)
4. **Authentication**: One-time OAuth2 authorization code flow
5. **Token Storage**: Cached locally for subsequent requests

### Security Features

- **Delegated Permissions**: Access user data on behalf of user
- **Environment Variables**: Credentials never hardcoded
- **Token Caching**: Reduces authentication overhead
- **Graceful Degradation**: Works without O365 if not configured
- **No Data Logging**: Email/calendar data not logged

### Configuration

**Environment Variables** (legacy - for backward compatibility):
```bash
O365_CLIENT_ID=your-application-client-id
O365_CLIENT_SECRET=your-client-secret
O365_USERNAME=your-email@example.com  # Optional
```

**Configuration UI** (recommended):
- Settings → Microsoft 365 Integration
- Secure credential storage
- Test connection button
- Status indicators

## Integration Points

### Context Engine

Both providers integrate with `ContextEngine`:

```python
from janus.api.context_api import ContextEngine

# Enable providers
context = ContextEngine(
    enable_calendar=True,
    enable_email=True
)

# Get unified context
context_data = context.get_context()

# Access calendar data
calendar_info = context_data['calendar']
# {
#   'enabled': True,
#   'current_event': {...},
#   'next_event': {...},
#   'upcoming_events': [...],
#   'is_in_meeting': bool
# }

# Access email data  
email_info = context_data['email']
# {
#   'enabled': True,
#   'unread_count': int,
#   'recent_emails': [...],
#   'recent_senders': [...],
#   'has_unread': bool
# }
```

### LLM Context Injection

Calendar and email data automatically enriches LLM context:

**Before (screenshot-based)**:
```
User: "What's my next meeting?"
LLM Context: [Screenshot of Outlook calendar, 2048 tokens]
Accuracy: ~85% (OCR errors, incomplete data)
Latency: 2-5 seconds
```

**After (structured data)**:
```
User: "What's my next meeting?"
LLM Context: {
  "next_event": {
    "title": "Team Standup",
    "start": "2025-12-13T14:00:00",
    "attendees": ["John", "Jane", "Alice"]
  }
}
Accuracy: ~100%
Latency: 100-300ms
```

## Performance Optimization

### Caching Strategy

- **Token Cache**: OAuth tokens cached locally
- **Event Cache**: Recent events cached (TTL: 5 minutes)
- **Email Cache**: Inbox metadata cached (TTL: 2 minutes)

### Query Optimization

- **Selective Fields**: Only fetch required fields
- **Time Windows**: Limit queries to relevant time ranges
- **Pagination**: Use limit parameter to control data volume

### Error Handling

- **Network Errors**: Retry with exponential backoff
- **Auth Errors**: Clear cache and re-authenticate
- **API Limits**: Respect rate limits
- **Graceful Degradation**: Return empty data on failure

## Usage Examples

### Calendar Queries

```python
from janus.memory.calendar_provider import CalendarProvider

calendar = CalendarProvider()
calendar.authenticate()  # One-time
calendar.enable()

# Voice: "What's my next meeting?"
next_event = calendar.get_next_event()
# Response: "Your next meeting is Team Standup at 2 PM"

# Voice: "Do I have meetings today?"
events = calendar.get_upcoming_events(limit=10)
# Response: "You have 3 meetings today: ..."
```

### Email Queries

```python
from janus.memory.email_provider import EmailProvider

email = EmailProvider()
email.authenticate()  # One-time
email.enable()

# Voice: "Summarize my unread emails"
unread = email.fetch_unread(limit=5)
# Response: "You have 3 unread emails: ..."

# Voice: "Did John send me any emails?"
results = email.search_emails("from:john@example.com")
# Response: "John sent you 2 emails today: ..."
```

## Extensibility

### Future Providers

The architecture supports additional calendar/email providers:

```python
class AppleCalendarProvider(CalendarProvider):
    """macOS Calendar via AppleScript"""
    
class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar API"""
    
class GmailProvider(EmailProvider):
    """Gmail API"""
    
class IMAPProvider(EmailProvider):
    """Generic IMAP/POP3 access"""
```

### Provider Selection

```python
# Automatic provider selection based on platform
def get_calendar_provider(platform='auto'):
    if platform == 'auto':
        platform = detect_platform()
    
    providers = {
        'microsoft365': CalendarProvider,
        'google': GoogleCalendarProvider,
        'macos': AppleCalendarProvider
    }
    
    return providers.get(platform, CalendarProvider)
```

## Troubleshooting

### Common Issues

1. **"O365 library not installed"**
   - Solution: `pip install janus[office365]`

2. **"Authentication failed"**
   - Verify Client ID and Secret
   - Check API permissions in Azure
   - Ensure delegated permissions granted

3. **"No calendar/mailbox found"**
   - Complete OAuth flow
   - Verify Microsoft 365 account active

4. **"Token expired"**
   - Delete cached token
   - Re-run authentication

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

calendar = CalendarProvider()
# Detailed logs show API calls and responses
```

## Migration Guide

### From Screenshot-Based Approach

**Before**:
```python
# Screenshot + OCR approach
screenshot = take_screenshot("Outlook")
text = ocr_extract(screenshot)
events = parse_calendar_text(text)  # Error-prone
```

**After**:
```python
# Structured API approach
calendar = CalendarProvider()
calendar.enable()
events = calendar.get_upcoming_events()  # Reliable
```

### Backward Compatibility

- Old code continues to work without O365
- Providers return empty data when disabled
- No breaking changes to existing APIs

## Monitoring & Metrics

### Key Metrics

- **Query Latency**: Target <300ms
- **Success Rate**: Target >99%
- **Cache Hit Rate**: Target >80%
- **Token Refresh**: Monitor expiration

### Logging

```python
# Structured logging
logger.info("Calendar query", extra={
    'method': 'get_upcoming_events',
    'limit': 5,
    'duration_ms': 150,
    'events_found': 3
})
```

## References

- [Microsoft 365 Setup Guide](../../user/microsoft-365-setup.md) - User documentation
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/) - API reference
- [O365 Library](https://github.com/O365/python-o365) - Python client
- [Context Engine](./17-memory-engine.md) - Memory system architecture

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: 2025-12-13
