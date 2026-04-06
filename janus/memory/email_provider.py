"""
Email Context Provider - Provides email information and recent communications
Part of TICKET-APP-001: Native Microsoft 365 / Outlook Connector

This module provides email context for better command understanding:
- Recent emails
- Unread count
- Important senders
- Email search

Integration:
- Microsoft 365 (via O365 library)
- Future: macOS Mail app via AppleScript, Gmail API
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailProvider:
    """
    Email context provider

    Provides information about:
    - Recent emails (inbox)
    - Unread email count
    - Important/priority emails
    - Recent senders

    Integration points:
    - Microsoft 365 (via O365 library) - PRIMARY
    - macOS Mail app via AppleScript (future)
    - Gmail API (future)
    - IMAP/POP3 access (future)
    """

    def __init__(
        self,
        max_recent_emails: int = 10,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
    ):
        """
        Initialize email provider

        Args:
            max_recent_emails: Maximum number of recent emails to track
            client_id: Microsoft 365 Application (client) ID
            client_secret: Microsoft 365 client secret
            username: Microsoft 365 user email address
        """
        self.max_recent_emails = max_recent_emails
        self.enabled = False  # Disabled by default until integration is configured
        self.account = None
        self.mailbox = None

        # Get credentials from parameters or environment variables
        self.client_id = client_id or os.environ.get("O365_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("O365_CLIENT_SECRET")
        self.username = username or os.environ.get("O365_USERNAME")

        # Try to initialize O365 connection if credentials are available
        if self.client_id and self.client_secret:
            self._init_o365_connection()

    def _init_o365_connection(self) -> bool:
        """
        Initialize O365 connection and authenticate if needed
        
        Returns:
            True if connection is established, False otherwise
        """
        try:
            from O365 import Account

            credentials = (self.client_id, self.client_secret)
            self.account = Account(
                credentials,
                username=self.username,
            )

            # Check if already authenticated
            if self.account.is_authenticated:
                self.mailbox = self.account.mailbox()
                logger.info("O365 mailbox connection established (already authenticated)")
                return True
            else:
                logger.info("O365 mailbox not authenticated. Call authenticate() or enable() with auth.")
                return False

        except ImportError:
            logger.warning(
                "O365 library not installed. Install with: pip install 'janus[office365]'"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize O365 connection: {e}")
            return False

    def authenticate(self, scopes: Optional[List[str]] = None) -> bool:
        """
        Authenticate with Microsoft 365

        Args:
            scopes: List of required scopes (default: Mail.Read)

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self.account:
            logger.error("O365 account not initialized. Check credentials.")
            return False

        try:
            # Default scopes for email access
            if scopes is None:
                scopes = ['Mail.Read']

            # Perform authentication flow
            if self.account.authenticate(requested_scopes=scopes):
                self.mailbox = self.account.mailbox()
                logger.info("O365 mailbox authenticated successfully")
                return True
            else:
                logger.error("O365 authentication failed")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_unread_count(self) -> int:
        """
        Get count of unread emails

        Returns:
            Number of unread emails
        """
        if not self.enabled or not self.mailbox:
            return 0

        try:
            inbox = self.mailbox.inbox_folder()
            query = inbox.new_query().on_attribute('isRead').equals(False)
            messages = inbox.get_messages(query=query, limit=1)
            
            # Count unread messages
            count = 0
            for _ in messages:
                count += 1
                
            # Get total count if available
            if hasattr(inbox, 'get_message_count'):
                return inbox.get_message_count(query=query)
            
            return count

        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of email dictionaries with subject, sender, body, etc.
        """
        if not self.enabled or not self.mailbox:
            return []

        try:
            inbox = self.mailbox.inbox_folder()
            query = inbox.new_query().on_attribute('isRead').equals(False)
            messages = inbox.get_messages(
                query=query, limit=limit, order_by='receivedDateTime desc'
            )

            formatted_emails = []
            for message in messages:
                formatted_emails.append(self._format_email(message))

            return formatted_emails

        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
            return []

    def get_recent_emails(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent emails from inbox

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of email dictionaries with:
            - subject: Email subject
            - sender: Sender email/name
            - timestamp: When email was received
            - is_read: Whether email has been read
            - is_important: Whether email is marked important
            - body: Email body text (plain text)
        """
        if not self.enabled or not self.mailbox:
            return []

        if limit is None:
            limit = self.max_recent_emails

        try:
            inbox = self.mailbox.inbox_folder()
            messages = inbox.get_messages(limit=limit, order_by='receivedDateTime desc')

            formatted_emails = []
            for message in messages:
                formatted_emails.append(self._format_email(message))

            return formatted_emails

        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []

    def _format_email(self, message) -> Dict[str, Any]:
        """
        Format an O365 message to a standard dictionary

        Args:
            message: O365 Message object

        Returns:
            Formatted email dictionary
        """
        try:
            # Extract sender information
            sender_name = message.sender.name if message.sender else 'Unknown'
            sender_email = message.sender.address if message.sender else 'unknown@example.com'

            # Get body text (prefer plain text over HTML)
            body_text = ''
            if hasattr(message, 'body_preview'):
                body_text = message.body_preview or ''
            elif message.body:
                body_text = message.body[:500]  # First 500 chars

            return {
                'subject': message.subject or 'No Subject',
                'sender': f"{sender_name} <{sender_email}>",
                'sender_name': sender_name,
                'sender_email': sender_email,
                'timestamp': message.received.isoformat() if message.received else None,
                'is_read': message.is_read if hasattr(message, 'is_read') else False,
                'is_important': message.importance == 'high' if hasattr(message, 'importance') else False,
                'body': body_text,
                'has_attachments': message.has_attachments if hasattr(message, 'has_attachments') else False,
            }

        except Exception as e:
            logger.error(f"Error formatting email: {e}")
            return {
                'subject': 'Unknown Email',
                'sender': 'Unknown',
                'timestamp': None,
                'is_read': False,
                'is_important': False,
                'body': '',
            }

    def get_recent_senders(self, limit: int = 5) -> List[str]:
        """
        Get list of recent email senders

        Args:
            limit: Maximum number of senders to return

        Returns:
            List of sender names/emails
        """
        if not self.enabled or not self.mailbox:
            return []

        try:
            # Get recent emails and extract unique senders
            recent_emails = self.get_recent_emails(limit=limit * 2)  # Get more to find unique senders
            
            senders = []
            seen = set()
            
            for email in recent_emails:
                sender = email.get('sender', '')
                if sender and sender not in seen:
                    senders.append(sender)
                    seen.add(sender)
                    
                    if len(senders) >= limit:
                        break
            
            return senders

        except Exception as e:
            logger.error(f"Error getting recent senders: {e}")
            return []

    def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search emails by subject, sender, or content

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching email dictionaries
        """
        if not self.enabled or not self.mailbox:
            return []

        try:
            inbox = self.mailbox.inbox_folder()
            # Search in subject and body
            search_query = inbox.new_query().search(query)
            messages = inbox.get_messages(
                query=search_query, limit=limit, order_by='receivedDateTime desc'
            )

            formatted_emails = []
            for message in messages:
                formatted_emails.append(self._format_email(message))

            return formatted_emails

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def get_context(self) -> Dict[str, Any]:
        """
        Get complete email context

        Returns:
            Dictionary with email information:
            - unread_count: Number of unread emails
            - recent_emails: List of recent emails
            - recent_senders: List of recent senders
            - has_unread: Boolean indicating if there are unread emails
        """
        unread_count = self.get_unread_count()
        recent_emails = self.get_recent_emails(limit=5)
        recent_senders = self.get_recent_senders(limit=5)

        return {
            "unread_count": unread_count,
            "recent_emails": recent_emails,
            "recent_senders": recent_senders,
            "has_unread": unread_count > 0,
            "enabled": self.enabled,
        }
    
    def send_email(
        self, 
        to: str | List[str], 
        subject: str, 
        body: str,
        cc: Optional[str | List[str]] = None,
        bcc: Optional[str | List[str]] = None,
        body_type: str = "text"
    ) -> bool:
        """
        Send an email via Microsoft 365
        
        Args:
            to: Recipient email address(es) - can be string or list
            subject: Email subject
            body: Email body content
            cc: CC recipient(s) - optional
            bcc: BCC recipient(s) - optional
            body_type: Body type - "text" or "html" (default: "text")
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled or not self.mailbox:
            logger.error("Email provider not enabled or mailbox not available")
            return False
        
        try:
            # Create new message
            message = self.mailbox.new_message()
            
            # Set recipients
            if isinstance(to, str):
                message.to.add(to)
            else:
                for recipient in to:
                    message.to.add(recipient)
            
            # Set CC if provided
            if cc:
                if isinstance(cc, str):
                    message.cc.add(cc)
                else:
                    for recipient in cc:
                        message.cc.add(recipient)
            
            # Set BCC if provided
            if bcc:
                if isinstance(bcc, str):
                    message.bcc.add(bcc)
                else:
                    for recipient in bcc:
                        message.bcc.add(recipient)
            
            # Set subject and body
            message.subject = subject
            
            if body_type.lower() == "html":
                message.body_type = "HTML"
                message.body = body
            else:
                message.body_type = "Text"
                message.body = body
            
            # Send the message
            message.send()
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def enable(self):
        """Enable email provider"""
        # Verify mailbox is available before enabling
        if self.mailbox or self._init_o365_connection():
            self.enabled = True
            logger.info("Email provider enabled")
        else:
            logger.warning(
                "Email provider cannot be enabled - O365 not configured or authenticated"
            )

    def disable(self):
        """Disable email provider"""
        self.enabled = False
        logger.info("Email provider disabled")


# Example integration code for future use:
"""
# macOS Mail via AppleScript:
def _get_macos_mail_unread(self):
    script = '''
    tell application "Mail"
        count of (messages of inbox whose read status is false)
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return int(result.stdout.strip())

def _get_macos_mail_recent(self, limit=10):
    script = f'''
    tell application "Mail"
        set recentMsgs to messages 1 thru {limit} of inbox
        set msgList to {{}}
        repeat with msg in recentMsgs
            set end of msgList to {{subject of msg, sender of msg, date received of msg, read status of msg}}
        end repeat
        return msgList
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    # Parse and return messages

# Gmail API:
def _get_gmail_unread(self):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(
        userId='me',
        labelIds=['UNREAD'],
        maxResults=1
    ).execute()

    return results.get('resultSizeEstimate', 0)
"""
