"""
EmailAgent - Email Operations and Management

TICKET-P1-E2E: Email agent for Extract→Process→Output pipeline

This agent handles email operations including:
- Reading emails (inbox, unread)
- Sending emails
- Searching emails
- Email management

Wraps EmailProvider to provide consistent agent interface.
"""

import asyncio
from typing import Any, Dict, List, Optional

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.memory.email_provider import EmailProvider


class EmailAgent(BaseAgent):
    """
    Agent for email operations.
    
    Supported actions:
    - get_recent_emails(limit=10) - Get recent emails from inbox
    - get_unread_emails(limit=10) - Get unread emails
    - send_email(to, subject, body, cc=None, bcc=None) - Send an email
    - search_emails(query, limit=10) - Search emails by content
    - get_unread_count() - Get count of unread emails
    
    Providers:
    - outlook: Microsoft 365 / Outlook
    - gmail: Gmail (future)
    - apple: Apple Mail via AppleScript (future)
    - imap: Generic IMAP (future)
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        provider: str = "outlook"
    ):
        """
        Initialize EmailAgent.
        
        Args:
            client_id: OAuth client ID (for O365)
            client_secret: OAuth client secret (for O365)
            username: User email address
            provider: Email provider ("outlook", "gmail", "apple", "imap")
        """
        super().__init__("email")
        self.provider = provider
        
        # Initialize email provider (currently only O365 supported)
        self.email_provider = EmailProvider(
            client_id=client_id,
            client_secret=client_secret,
            username=username
        )
        
        # Enable if credentials are available
        if self.email_provider.account and self.email_provider.account.is_authenticated:
            self.email_provider.enable()
            self.logger.info("Email Agent initialized with authenticated connection")
        elif client_id and client_secret:
            self.logger.info("Email Agent initialized but not authenticated. Call authenticate() first.")
        else:
            self.logger.warning("Email Agent initialized without credentials. Set O365_CLIENT_ID and O365_CLIENT_SECRET environment variables.")
    
    def authenticate(self, scopes: Optional[List[str]] = None) -> bool:
        """
        Authenticate with email provider.
        
        Args:
            scopes: List of required OAuth scopes (default: Mail.Read, Mail.Send)
            
        Returns:
            True if authentication succeeded
        """
        if scopes is None:
            scopes = ['Mail.Read', 'Mail.Send']
        
        return self.email_provider.authenticate(scopes=scopes)
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute an email action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing (prevents sending emails accidentally)
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would send email or perform email action '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": False,  # Email sending is not reversible
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        # Route to decorated method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        else:
            raise AgentExecutionError(
                module=self.agent_name,
                action=action,
                details=f"Unsupported action: {action}",
                recoverable=False
            )
    
    @agent_action(
        description="Get recent emails from inbox",
        required_args=[],
        optional_args={"limit": 10},
        providers=["outlook", "gmail", "apple", "imap"],
        examples=["email.get_recent_emails(limit=20)"]
    )
    async def _get_recent_emails(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent emails."""
        limit = args.get("limit", 10)
        
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(
            None,
            self.email_provider.get_recent_emails,
            limit
        )
        
        return self._success_result(
            data={"emails": emails, "count": len(emails)},
            message=f"Retrieved {len(emails)} recent emails"
        )
    
    @agent_action(
        description="Get unread emails",
        required_args=[],
        optional_args={"limit": 10},
        providers=["outlook", "gmail", "apple", "imap"],
        examples=["email.get_unread_emails(limit=5)"]
    )
    async def _get_unread_emails(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get unread emails."""
        limit = args.get("limit", 10)
        
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(
            None,
            self.email_provider.fetch_unread,
            limit
        )
        
        return self._success_result(
            data={"emails": emails, "count": len(emails)},
            message=f"Retrieved {len(emails)} unread emails"
        )
    
    @agent_action(
        description="Send an email",
        required_args=["to", "subject", "body"],
        optional_args={"cc": None, "bcc": None, "body_type": "text"},
        providers=["outlook", "gmail", "apple", "imap"],
        examples=[
            "email.send_email(to='user@example.com', subject='Hello', body='Test message')",
            "email.send_email(to='user@example.com', subject='Report', body='<h1>Report</h1>', body_type='html')"
        ]
    )
    async def _send_email(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email."""
        to = args["to"]
        subject = args["subject"]
        body = args["body"]
        cc = args.get("cc")
        bcc = args.get("bcc")
        body_type = args.get("body_type", "text")
        
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            self.email_provider.send_email,
            to,
            subject,
            body,
            cc,
            bcc,
            body_type
        )
        
        if success:
            recipient_str = to if isinstance(to, str) else ", ".join(to)
            return self._success_result(
                data={"to": to, "subject": subject},
                message=f"Email sent successfully to {recipient_str}"
            )
        else:
            return self._error_result(
                error="Failed to send email. Check email provider configuration.",
                recoverable=True
            )
    
    @agent_action(
        description="Search emails by query",
        required_args=["query"],
        optional_args={"limit": 10},
        providers=["outlook", "gmail", "apple", "imap"],
        examples=["email.search_emails(query='project update', limit=20)"]
    )
    async def _search_emails(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search emails."""
        query = args["query"]
        limit = args.get("limit", 10)
        
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(
            None,
            self.email_provider.search_emails,
            query,
            limit
        )
        
        return self._success_result(
            data={"emails": emails, "count": len(emails), "query": query},
            message=f"Found {len(emails)} emails matching '{query}'"
        )
    
    @agent_action(
        description="Get count of unread emails",
        required_args=[],
        providers=["outlook", "gmail", "apple", "imap"],
        examples=["email.get_unread_count()"]
    )
    async def _get_unread_count(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get unread email count."""
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(
            None,
            self.email_provider.get_unread_count
        )
        
        return self._success_result(
            data={"count": count},
            message=f"{count} unread emails"
        )
    
    @agent_action(
        description="Get recent email senders",
        required_args=[],
        optional_args={"limit": 5},
        providers=["outlook", "gmail", "apple", "imap"],
        examples=["email.get_recent_senders(limit=10)"]
    )
    async def _get_recent_senders(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent email senders."""
        limit = args.get("limit", 5)
        
        loop = asyncio.get_event_loop()
        senders = await loop.run_in_executor(
            None,
            self.email_provider.get_recent_senders,
            limit
        )
        
        return self._success_result(
            data={"senders": senders, "count": len(senders)},
            message=f"Retrieved {len(senders)} recent senders"
        )
