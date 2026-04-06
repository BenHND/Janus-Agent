"""
CRM Agent - Salesforce CRM Operations
Part of TICKET-BIZ-001: Salesforce Native Connector (CRM)
TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

This agent provides atomic CRM operations following V3 architecture:
- Search contacts
- Get opportunity data
- Generate URLs for browser navigation
- Hybrid mode: API reads, browser writes

ATOMIC OPERATION PRINCIPLES:
1. Each operation < 20 lines of code
2. No business logic or heuristics
3. No retry loops or fallbacks
4. No multi-step workflows
5. Dumb execution only - intelligence in Reasoner
"""

import logging
from typing import Any, Dict, Optional

from janus.capabilities.agents.base_agent import AgentExecutionError, BaseAgent
from janus.capabilities.agents.decorators import agent_action
from janus.integrations.salesforce_provider import SalesforceProvider

logger = logging.getLogger(__name__)


class CRMAgent(BaseAgent):
    """
    CRM Agent for Salesforce operations
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Provides atomic operations for CRM data access:
    - search_contact: Find contact by name
    - get_contact: Get contact by ID
    - get_opportunity: Get opportunity by ID
    - search_opportunities: Find opportunities by account
    - get_account: Get account by name
    - generate_contact_url: Create browser URL for contact
    - generate_opportunity_url: Create browser URL for opportunity
    
    Hybrid Mode:
    - Reads: Via API (fast, structured data)
    - Writes/Edits: Generate URL and open in browser for user action
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        domain: str = 'login',
        provider: str = "salesforce"
    ):
        """
        Initialize CRM Agent
        
        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Salesforce security token
            domain: Salesforce domain ('login' or 'test')
            provider: CRM provider ("salesforce", "hubspot", "dynamics365")
        """
        super().__init__("crm")
        self.provider = provider
        self.salesforce = SalesforceProvider(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain,
        )
        
        # Enable if credentials are available
        if self.salesforce.sf:
            self.salesforce.enable()
            logger.info("CRM Agent initialized with Salesforce connection")
        else:
            logger.warning("CRM Agent initialized without Salesforce connection")

    async def execute(
        self, action: str, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute CRM action by routing to decorated methods.
        
        TICKET-ARCH-AGENT: Migrated to use @agent_action decorator pattern.
        
        Args:
            action: Action name (search_contact, get_opportunity, etc.)
            args: Action arguments
            context: Optional execution context
            dry_run: If True, preview action without executing (P2 feature)
            
        Returns:
            Action result dictionary
            
        Raises:
            AgentExecutionError: If action fails or is unsupported
        """
        # P2: Dry-run mode - preview without executing CRM operations
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would execute CRM action '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": action in ["create_contact", "update_contact", "create_opportunity"],
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        # Route to decorated method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context or {})
        else:
            raise AgentExecutionError(
                module="crm",
                action=action,
                details=f"Unsupported action: {action}",
                recoverable=False,
            )

    @agent_action(
        description="Search for a contact by name",
        required_args=["name"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.search_contact(name='John Doe')"]
    )
    async def _search_contact(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search for contact by name"""
        name = args.get("name")
        if not name:
            raise AgentExecutionError(
                module="crm",
                action="search_contact",
                details="Missing required argument: name",
                recoverable=False,
            )
        
        contact = self.salesforce.get_contact(name)
        
        if contact:
            return {
                "success": True,
                "contact": contact,
                "message": f"Found contact: {contact['name']}",
            }
        else:
            return {
                "success": False,
                "contact": None,
                "message": f"No contact found for: {name}",
            }

    @agent_action(
        description="Get contact by ID",
        required_args=["contact_id"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.get_contact(contact_id='003xxxx')"]
    )
    async def _get_contact(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get contact by ID"""
        contact_id = args.get("contact_id")
        if not contact_id:
            raise AgentExecutionError(
                module="crm",
                action="get_contact",
                details="Missing required argument: contact_id",
                recoverable=False,
            )
        
        contact = self.salesforce.get_contact_by_id(contact_id)
        
        if contact:
            return {
                "success": True,
                "contact": contact,
            }
        else:
            return {
                "success": False,
                "contact": None,
                "message": f"Contact not found: {contact_id}",
            }

    @agent_action(
        description="Get opportunity by ID",
        required_args=["opportunity_id"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.get_opportunity(opportunity_id='006xxxx')"]
    )
    async def _get_opportunity(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get opportunity by ID"""
        opportunity_id = args.get("opportunity_id")
        if not opportunity_id:
            raise AgentExecutionError(
                module="crm",
                action="get_opportunity",
                details="Missing required argument: opportunity_id",
                recoverable=False,
            )
        
        opportunity = self.salesforce.get_opportunity(opportunity_id)
        
        if opportunity:
            return {
                "success": True,
                "opportunity": opportunity,
            }
        else:
            return {
                "success": False,
                "opportunity": None,
                "message": f"Opportunity not found: {opportunity_id}",
            }

    @agent_action(
        description="Search opportunities by account name",
        required_args=["account_name"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.search_opportunities(account_name='Acme Corp')"]
    )
    async def _search_opportunities(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search opportunities by account name"""
        account_name = args.get("account_name")
        if not account_name:
            raise AgentExecutionError(
                module="crm",
                action="search_opportunities",
                details="Missing required argument: account_name",
                recoverable=False,
            )
        
        limit = args.get("limit", 10)
        opportunities = self.salesforce.search_opportunities(account_name, limit=limit)
        
        return {
            "success": True,
            "opportunities": opportunities,
            "count": len(opportunities),
        }

    @agent_action(
        description="Get account by name",
        required_args=["account_name"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.get_account(account_name='Acme Corp')"]
    )
    async def _get_account(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get account by name"""
        account_name = args["account_name"]
        
        account = self.salesforce.get_account(account_name)
        
        if account:
            return {
                "success": True,
                "account": account,
            }
        else:
            return {
                "success": False,
                "account": None,
                "message": f"Account not found: {account_name}",
            }

    @agent_action(
        description="Generate Salesforce URL for contact",
        required_args=["contact_id"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.generate_contact_url(contact_id='003xxxx')"]
    )
    async def _generate_contact_url(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Salesforce URL for contact"""
        contact_id = args.get("contact_id")
        if not contact_id:
            raise AgentExecutionError(
                module="crm",
                action="generate_contact_url",
                details="Missing required argument: contact_id",
                recoverable=False,
            )
        
        url = self.salesforce.generate_contact_url(contact_id)
        
        return {
            "success": True,
            "url": url,
            "message": f"Contact URL: {url}",
        }

    @agent_action(
        description="Generate Salesforce URL for opportunity",
        required_args=["opportunity_id"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.generate_opportunity_url(opportunity_id='006xxxx')"]
    )
    async def _generate_opportunity_url(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Salesforce URL for opportunity"""
        opportunity_id = args.get("opportunity_id")
        if not opportunity_id:
            raise AgentExecutionError(
                module="crm",
                action="generate_opportunity_url",
                details="Missing required argument: opportunity_id",
                recoverable=False,
            )
        
        url = self.salesforce.generate_opportunity_url(opportunity_id)
        
        return {
            "success": True,
            "url": url,
            "message": f"Opportunity URL: {url}",
        }
    
    @agent_action(
        description="Open a CRM record in browser",
        required_args=["record_id", "record_type"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.open_record(record_id='003xxxx', record_type='contact')"]
    )
    async def _open_record(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Open a CRM record by delegating to type-specific handlers"""
        record_id = args.get("record_id")
        record_type = args.get("record_type", "account").lower()
        
        if not record_id:
            raise AgentExecutionError(
                module="crm",
                action="open_record",
                details="Missing required argument: record_id",
                recoverable=False,
            )
        
        # Delegate to appropriate handler based on type
        if record_type == "contact":
            return await self._get_contact({"contact_id": record_id})
        elif record_type == "opportunity":
            return await self._get_opportunity({"opportunity_id": record_id})
        elif record_type == "account":
            return await self._get_account({"account_id": record_id})
        else:
            raise AgentExecutionError(
                module="crm",
                action="open_record",
                details=f"Unsupported record type: {record_type}",
                recoverable=False,
            )
    
    @agent_action(
        description="Search CRM records",
        required_args=["record_type", "query"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.search_records(record_type='contact', query='John')"]
    )
    async def _search_records(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generic record search - delegates based on record_type"""
        query = args.get("query")
        record_type = args.get("record_type", "contact").lower()
        
        if not query:
            raise AgentExecutionError(
                module="crm",
                action="search_records",
                details="Missing required argument: query",
                recoverable=False,
            )
        
        # Delegate to specific search handler
        if record_type == "contact":
            return await self._search_contact({"name": query})
        elif record_type == "opportunity":
            return await self._search_opportunities({"query": query})
        else:
            raise AgentExecutionError(
                module="crm",
                action="search_records",
                details=f"Unsupported record type for search: {record_type}",
                recoverable=False,
            )
    
    @agent_action(
        description="Update a field on a CRM record",
        required_args=["record_id", "record_type", "field_name", "value"],
        providers=["salesforce", "hubspot", "dynamics365"],
        examples=["crm.update_field(record_id='003xxxx', record_type='contact', field_name='Email', value='new@email.com')"]
    )
    async def _update_field(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Update a field on a CRM record"""
        # This is a placeholder - actual implementation would require Salesforce API calls
        field_name = args.get("field_name")
        value = args.get("value")
        record_id = args.get("record_id")
        
        if not field_name or value is None:
            raise AgentExecutionError(
                module="crm",
                action="update_field",
                details="Missing required arguments: field_name, value",
                recoverable=False,
            )
        
        # For now, return not implemented
        return {
            "status": "error",
            "error": "update_field not yet implemented - requires Salesforce update API",
            "recoverable": False,
        }
