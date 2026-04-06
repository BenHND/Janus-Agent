# Salesforce CRM Integration: Native Connector

> **TICKET-BIZ-001**: Salesforce Native Connector (CRM)
> 
> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---

## Overview

The Salesforce CRM integration provides native access to CRM data through the Salesforce API, eliminating the need for screenshot-based data extraction. This significantly improves performance, accuracy, and user experience for CRM-related queries.

**Performance**: Sub-3 seconds (vs. 15+ seconds with browser automation)

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CRM Agent (V3)                            │
├─────────────────────────────────────────────────────────────┤
│  Atomic Operations:                                          │
│  - search_contact                                            │
│  - get_contact                                               │
│  - get_opportunity                                           │
│  - search_opportunities                                      │
│  - get_account                                               │
│  - generate_contact_url                                      │
│  - generate_opportunity_url                                  │
│  └────────┬─────────────────────────────────────────────┘   │
│           │                                                  │
│  ┌────────▼────────────────────────────────────┐            │
│  │      SalesforceProvider                     │            │
│  │                                              │            │
│  │  - Contact search & retrieval                │            │
│  │  - Opportunity data access                   │            │
│  │  - Account information                       │            │
│  │  - URL generation for browser navigation     │            │
│  └────────┬─────────────────────────────────────┘            │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
  ┌─────────────────┐
  │simple-salesforce│
  │    Library      │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Salesforce API  │
  │  (REST/SOAP)    │
  └─────────────────┘
```

### Data Flow

1. **User Query** → "Qui est le contact principal chez Acme Corp ?"
2. **LLM Reasoner** → Routes to CRM Agent with action: search_contact
3. **CRM Agent** → Calls `SalesforceProvider.get_contact('Acme Corp')`
4. **SalesforceProvider** → Queries Salesforce API via simple-salesforce
5. **Salesforce API** → Returns structured contact data
6. **SalesforceProvider** → Formats contact into standard dictionary
7. **CRM Agent** → Returns result to Reasoner
8. **LLM** → Generates natural language response using structured data

**Performance**: 0.5-3 seconds (vs. 15+ seconds with browser automation)

## Components

### SalesforceProvider

**Purpose**: Provides structured access to Salesforce CRM data

**Key Methods**:
- `get_contact(name)` - Search contact by name
- `get_contact_by_id(id)` - Get contact by Salesforce ID
- `get_opportunity(id)` - Get opportunity by ID
- `search_opportunities(account_name, limit)` - Search opportunities by account
- `get_account(account_name)` - Get account information
- `generate_contact_url(id)` - Create direct browser URL to contact
- `generate_opportunity_url(id)` - Create direct browser URL to opportunity

**Contact Data Structure**:
```python
{
    'id': str,              # Salesforce ID (e.g., '003...')
    'name': str,            # Full name
    'first_name': str,      # First name
    'last_name': str,       # Last name
    'title': str,           # Job title
    'email': str,           # Email address
    'phone': str,           # Phone number
    'account_name': str,    # Associated account name
    'department': str,      # Department
    'city': str,           # Mailing city
    'url': str,            # Direct Salesforce URL
}
```

**Opportunity Data Structure**:
```python
{
    'id': str,              # Salesforce ID (e.g., '006...')
    'name': str,            # Opportunity name
    'stage': str,           # Sales stage
    'amount': float,        # Deal amount
    'close_date': str,      # Expected close date
    'probability': int,     # Win probability (0-100)
    'type': str,            # Opportunity type
    'account_name': str,    # Associated account
    'url': str,            # Direct Salesforce URL
}
```

### CRMAgent

**Purpose**: V3 agent providing atomic CRM operations

**Supported Actions**:
- `search_contact` - Find contact by name
- `get_contact` - Get contact by ID
- `get_opportunity` - Get opportunity by ID
- `search_opportunities` - Find opportunities by account
- `get_account` - Get account information
- `generate_contact_url` - Create browser URL for contact
- `generate_opportunity_url` - Create browser URL for opportunity

**Action Arguments**:
```python
# search_contact
{'name': str}

# get_contact
{'contact_id': str}

# get_opportunity
{'opportunity_id': str}

# search_opportunities
{'account_name': str, 'limit': int (optional, default: 10)}

# get_account
{'account_name': str}

# generate_contact_url
{'contact_id': str}

# generate_opportunity_url
{'opportunity_id': str}
```

## Hybrid Mode Architecture

The integration uses a **hybrid approach** optimized for safety and speed:

### Read Operations (API-based)
- Contact search: `get_contact(name)` → Returns structured data
- Opportunity retrieval: `get_opportunity(id)` → Returns structured data
- Account information: `get_account(name)` → Returns structured data
- **Benefits**: Fast (< 3s), accurate, no UI interaction needed

### Write Operations (Browser-based)
- Contact editing: Generate URL → Open in browser → User/Agent completes action
- Opportunity updates: Generate URL → Open in browser → User/Agent completes action
- **Benefits**: Safer (no accidental data corruption), user maintains control

### URL Generation
```python
# Contact URL
https://{instance}.my.salesforce.com/lightning/r/Contact/{id}/view

# Opportunity URL
https://{instance}.my.salesforce.com/lightning/r/Opportunity/{id}/view

# Account URL
https://{instance}.my.salesforce.com/lightning/r/Account/{id}/view
```

## Configuration

### Environment Variables

```bash
# Salesforce credentials
SALESFORCE_USERNAME=your.email@company.com
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_security_token

# Optional: Domain (default: 'login' for production)
SALESFORCE_DOMAIN=login  # or 'test' for sandbox
```

### Installation

```bash
# Install with Salesforce support
pip install 'janus[salesforce]'

# Or install dependency directly
pip install simple-salesforce>=1.12.6
```

### Getting Salesforce Security Token

1. Log in to Salesforce
2. Go to Settings → My Personal Information → Reset My Security Token
3. Click "Reset Security Token"
4. Token will be sent to your email
5. Add to `.env` file as `SALESFORCE_SECURITY_TOKEN`

## Usage Examples

### Example 1: Contact Search
```
User: "Qui est le contact principal chez Acme Corp ?"

LLM Reasoner → CRM Agent
Action: search_contact
Args: {'name': 'Acme Corp'}

Response (< 3 seconds):
"Le contact principal chez Acme Corp est Jane Smith, VP of Sales. 
Email: jane.smith@acme.com, Téléphone: +1-555-0200"
```

### Example 2: Opportunity Information
```
User: "Donne-moi les détails de l'opportunity 006XXXXXXXXXXXX"

LLM Reasoner → CRM Agent
Action: get_opportunity
Args: {'opportunity_id': '006XXXXXXXXXXXX'}

Response:
"L'opportunity 'Acme - Q4 Deal' est au stade Negotiation avec un montant 
de $150,000 et une probabilité de 75%. Date de clôture prévue: 31/12/2024"
```

### Example 3: Hybrid Mode (Edit Contact)
```
User: "Modifie le titre de Jane Smith"

LLM Reasoner → CRM Agent
Action 1: search_contact → Get contact ID
Action 2: generate_contact_url → Get browser URL

LLM Reasoner → Browser Agent
Action: open_url
Args: {'url': 'https://mycompany.my.salesforce.com/lightning/r/Contact/003.../view'}

Result: Browser opens to contact page → User or agent can edit
```

## Performance Comparison

| Operation | Browser Automation | API Integration | Speedup |
|-----------|-------------------|-----------------|---------|
| Find Contact | 15-20s | 0.5-2s | **10x faster** |
| Get Opportunity | 15-20s | 0.5-2s | **10x faster** |
| Search Multiple | 30-60s | 1-3s | **20x faster** |

## Security Considerations

### Credentials Storage
- Credentials stored in `.env` file (not committed to git)
- Support for environment variables
- Security token required in addition to password

### Data Access
- Read-only by default (via API)
- Write operations require explicit browser navigation
- User maintains control over data modifications

### API Permissions
- Requires Salesforce API access
- Respects Salesforce field-level security
- Honors user permissions and role hierarchy

## Error Handling

### Connection Errors
```python
# Provider disabled if connection fails
provider.enabled = False

# Agent returns graceful error
{
    "success": False,
    "contact": None,
    "message": "Salesforce connection not available"
}
```

### Search No Results
```python
{
    "success": False,
    "contact": None,
    "message": "No contact found for: [name]"
}
```

### Missing Arguments
```python
raise AgentExecutionError(
    module="crm",
    action="search_contact",
    details="Missing required argument: name",
    recoverable=False
)
```

## Testing

### Unit Tests
- `tests/test_salesforce_provider.py` - Provider tests (15 test cases)
- `tests/test_crm_agent.py` - Agent tests (20+ test cases)

### Mock Testing
- All tests use mocks (no real Salesforce connection needed)
- Comprehensive coverage of success and error cases
- Async/await support for agent tests

### Running Tests
```bash
# Run all CRM tests
pytest tests/test_salesforce_provider.py tests/test_crm_agent.py -v

# Run with coverage
pytest tests/test_salesforce_provider.py tests/test_crm_agent.py --cov=janus.integrations --cov=janus.agents
```

## Future Enhancements

### Planned Features
- [ ] **Lead management** - Search and retrieve leads
- [ ] **Task creation** - Create tasks/events from voice commands
- [ ] **Report data** - Access Salesforce reports
- [ ] **Custom objects** - Support for custom Salesforce objects
- [ ] **Bulk operations** - Batch queries for multiple records
- [ ] **Real-time notifications** - Salesforce event streaming

### Alternative Integrations
- **Salesforce API v2**: REST API alternative
- **Bulk API**: For large data operations
- **Streaming API**: Real-time event notifications
- **Metadata API**: Schema and configuration access

## Integration Points

### Context API Integration
```python
from janus.integrations.salesforce_provider import SalesforceProvider

# Initialize in context engine
salesforce = SalesforceProvider()
salesforce.enable()

# Get context for LLM
context = salesforce.get_context()
```

### Agent Registry Integration
```python
from janus.agents.crm_agent import CRMAgent

# Register agent
agent_registry.register('crm', CRMAgent)

# Use in execution
result = await crm_agent.execute(
    action='search_contact',
    args={'name': 'Acme Corp'}
)
```

## References
## References

- [Salesforce CRM Setup Guide](../../user/salesforce-crm-setup.md) - User documentation
- [Salesforce API Documentation](https://developer.salesforce.com/docs/apis)
- [simple-salesforce Library](https://github.com/simple-salesforce/simple-salesforce)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [SOQL Reference](https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/)

---

**Status**: ✅ Implemented and tested  
**Performance**: < 3 seconds for contact lookup  
**Test Coverage**: 35+ test cases  
**Dependencies**: `simple-salesforce>=1.12.6`
