"""
Salesforce Context Provider - Provides CRM data from Salesforce
Part of TICKET-BIZ-001: Salesforce Native Connector (CRM)

This module provides Salesforce CRM context for better command understanding:
- Contact search and retrieval
- Opportunity data access
- Account information

Integration:
- Salesforce (via simple-salesforce library)
- Hybrid mode: API for reads, browser URLs for writes
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SalesforceProvider:
    """
    Salesforce CRM context provider

    Provides information about:
    - Contacts (search by name, get by ID)
    - Opportunities (get by ID)
    - Accounts (get by name or ID)
    - Generate direct URLs for browser navigation

    Integration points:
    - Salesforce API (via simple-salesforce) - PRIMARY for reads
    - Browser navigation for writes/edits (safer)
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        domain: str = 'login',
        instance_url: Optional[str] = None,
    ):
        """
        Initialize Salesforce provider

        Args:
            username: Salesforce username (email)
            password: Salesforce password
            security_token: Salesforce security token
            domain: Salesforce domain ('login' for production, 'test' for sandbox)
            instance_url: Optional instance URL (e.g., https://mycompany.my.salesforce.com)
        """
        self.enabled = False  # Disabled by default until credentials are configured
        self.sf = None
        self.instance_url = instance_url

        # Get credentials from parameters or environment variables
        self.username = username or os.environ.get("SALESFORCE_USERNAME")
        self.password = password or os.environ.get("SALESFORCE_PASSWORD")
        self.security_token = security_token or os.environ.get("SALESFORCE_SECURITY_TOKEN")
        self.domain = domain or os.environ.get("SALESFORCE_DOMAIN", "login")

        # Try to initialize Salesforce connection if credentials are available
        if self.username and self.password and self.security_token:
            self._init_salesforce_connection()

    def _init_salesforce_connection(self) -> bool:
        """
        Initialize Salesforce connection

        Returns:
            True if connection is established, False otherwise
        """
        try:
            from simple_salesforce import Salesforce

            self.sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                domain=self.domain,
            )

            # Store instance URL for generating links
            if self.sf and hasattr(self.sf, 'sf_instance'):
                self.instance_url = f"https://{self.sf.sf_instance}"
            
            logger.info(f"Salesforce connection established to {self.instance_url}")
            return True

        except ImportError:
            logger.warning(
                "simple-salesforce library not installed. Install with: pip install 'janus[salesforce]'"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Salesforce connection: {e}")
            return False

    @staticmethod
    def _escape_soql_string(value: Optional[str]) -> str:
        """
        Sanitize string values for SOQL queries to prevent injection
        
        Uses a whitelist approach: only allows safe characters
        Safe characters: alphanumeric (including underscore), spaces, @, dot, hyphen
        
        Args:
            value: String value to sanitize (can be None)
            
        Returns:
            Sanitized string safe for SOQL queries
        """
        if not value:
            return ""
        
        # Whitelist approach: only keep safe characters
        # \w = letters, numbers, underscore
        # \s = whitespace
        # @ . - = common punctuation for names and emails
        # This prevents injection without needing complex escaping
        safe_value = re.sub(r"[^\w\s@.\-]", "", value)
        
        return safe_value

    def get_contact(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a contact by name

        Args:
            name: Contact name to search for

        Returns:
            Contact dictionary or None if not found
        """
        if not self.enabled or not self.sf:
            return None

        try:
            # Sanitize input to prevent SOQL injection
            safe_name = self._escape_soql_string(name)
            
            # SOQL query to search contacts by Name field
            # Note: Salesforce's Name field contains the full name (FirstName + LastName)
            query = f"""
                SELECT Id, FirstName, LastName, Name, Title, Email, Phone, 
                       AccountId, Account.Name, Department, MailingCity
                FROM Contact
                WHERE Name LIKE '%{safe_name}%'
                LIMIT 1
            """
            
            results = self.sf.query(query)
            
            if results['totalSize'] > 0:
                contact = results['records'][0]
                return self._format_contact(contact)
            
            return None

        except Exception as e:
            logger.error(f"Error searching contact '{name}': {e}")
            return None

    def get_contact_by_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get contact by Salesforce ID

        Args:
            contact_id: Salesforce Contact ID (e.g., '003...')

        Returns:
            Contact dictionary or None if not found
        """
        if not self.enabled or not self.sf:
            return None

        try:
            contact = self.sf.Contact.get(contact_id)
            return self._format_contact(contact)

        except Exception as e:
            logger.error(f"Error getting contact by ID '{contact_id}': {e}")
            return None

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get opportunity by Salesforce ID

        Args:
            opportunity_id: Salesforce Opportunity ID (e.g., '006...')

        Returns:
            Opportunity dictionary or None if not found
        """
        if not self.enabled or not self.sf:
            return None

        try:
            opportunity = self.sf.Opportunity.get(opportunity_id)
            return self._format_opportunity(opportunity)

        except Exception as e:
            logger.error(f"Error getting opportunity '{opportunity_id}': {e}")
            return None

    def search_opportunities(self, account_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search opportunities by account name

        Args:
            account_name: Account name to search
            limit: Maximum number of results

        Returns:
            List of opportunity dictionaries
        """
        if not self.enabled or not self.sf:
            return []

        try:
            # Escape input to prevent SOQL injection
            safe_account_name = self._escape_soql_string(account_name)
            # Ensure limit is a valid integer
            safe_limit = max(1, min(int(limit), 2000))  # Salesforce max is 2000
            
            query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate, 
                       AccountId, Account.Name, Probability, Type
                FROM Opportunity
                WHERE Account.Name LIKE '%{safe_account_name}%'
                ORDER BY CloseDate DESC
                LIMIT {safe_limit}
            """
            
            results = self.sf.query(query)
            
            opportunities = []
            for opp in results['records']:
                opportunities.append(self._format_opportunity(opp))
            
            return opportunities

        except Exception as e:
            logger.error(f"Error searching opportunities for '{account_name}': {e}")
            return []

    def _format_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a Salesforce contact to a standard dictionary

        Args:
            contact: Salesforce Contact record

        Returns:
            Formatted contact dictionary
        """
        try:
            contact_id = contact.get('Id', '')
            
            # Extract Account information if available
            account_name = None
            if 'Account' in contact and contact['Account']:
                account_name = contact['Account'].get('Name')
            elif 'Account.Name' in contact:
                account_name = contact.get('Account.Name')
            
            formatted = {
                'id': contact_id,
                'name': contact.get('Name', 'Unknown'),
                'first_name': contact.get('FirstName', ''),
                'last_name': contact.get('LastName', ''),
                'title': contact.get('Title', ''),
                'email': contact.get('Email', ''),
                'phone': contact.get('Phone', ''),
                'account_name': account_name,
                'department': contact.get('Department', ''),
                'city': contact.get('MailingCity', ''),
                'url': self.generate_contact_url(contact_id) if contact_id else None,
            }
            
            return formatted

        except Exception as e:
            logger.error(f"Error formatting contact: {e}")
            return {
                'id': '',
                'name': 'Unknown Contact',
                'title': '',
                'email': '',
                'url': None,
            }

    def _format_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a Salesforce opportunity to a standard dictionary

        Args:
            opportunity: Salesforce Opportunity record

        Returns:
            Formatted opportunity dictionary
        """
        try:
            opp_id = opportunity.get('Id', '')
            
            # Extract Account information if available
            account_name = None
            if 'Account' in opportunity and opportunity['Account']:
                account_name = opportunity['Account'].get('Name')
            elif 'Account.Name' in opportunity:
                account_name = opportunity.get('Account.Name')
            
            formatted = {
                'id': opp_id,
                'name': opportunity.get('Name', 'Unknown'),
                'stage': opportunity.get('StageName', ''),
                'amount': opportunity.get('Amount', 0),
                'close_date': opportunity.get('CloseDate', ''),
                'probability': opportunity.get('Probability', 0),
                'type': opportunity.get('Type', ''),
                'account_name': account_name,
                'url': self.generate_opportunity_url(opp_id) if opp_id else None,
            }
            
            return formatted

        except Exception as e:
            logger.error(f"Error formatting opportunity: {e}")
            return {
                'id': '',
                'name': 'Unknown Opportunity',
                'stage': '',
                'amount': 0,
                'url': None,
            }

    def generate_contact_url(self, contact_id: str) -> str:
        """
        Generate direct URL to contact record in Salesforce Lightning

        Args:
            contact_id: Salesforce Contact ID

        Returns:
            URL string for browser navigation
        """
        if not self.instance_url:
            return f"https://login.salesforce.com/{contact_id}"
        
        return f"{self.instance_url}/lightning/r/Contact/{contact_id}/view"

    def generate_opportunity_url(self, opportunity_id: str) -> str:
        """
        Generate direct URL to opportunity record in Salesforce Lightning

        Args:
            opportunity_id: Salesforce Opportunity ID

        Returns:
            URL string for browser navigation
        """
        if not self.instance_url:
            return f"https://login.salesforce.com/{opportunity_id}"
        
        return f"{self.instance_url}/lightning/r/Opportunity/{opportunity_id}/view"

    def get_account(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for an account by name

        Args:
            account_name: Account name to search

        Returns:
            Account dictionary or None if not found
        """
        if not self.enabled or not self.sf:
            return None

        try:
            # Escape input to prevent SOQL injection
            safe_account_name = self._escape_soql_string(account_name)
            
            query = f"""
                SELECT Id, Name, Industry, Website, Phone, 
                       BillingCity, BillingCountry, Type
                FROM Account
                WHERE Name LIKE '%{safe_account_name}%'
                LIMIT 1
            """
            
            results = self.sf.query(query)
            
            if results['totalSize'] > 0:
                account = results['records'][0]
                account_id = account.get('Id', '')
                
                return {
                    'id': account_id,
                    'name': account.get('Name', 'Unknown'),
                    'industry': account.get('Industry', ''),
                    'website': account.get('Website', ''),
                    'phone': account.get('Phone', ''),
                    'city': account.get('BillingCity', ''),
                    'country': account.get('BillingCountry', ''),
                    'type': account.get('Type', ''),
                    'url': f"{self.instance_url}/lightning/r/Account/{account_id}/view" if account_id and self.instance_url else None,
                }
            
            return None

        except Exception as e:
            logger.error(f"Error searching account '{account_name}': {e}")
            return None

    def get_context(self) -> Dict[str, Any]:
        """
        Get Salesforce context for LLM

        Returns:
            Dictionary with Salesforce connection status
        """
        return {
            "enabled": self.enabled,
            "connected": self.sf is not None,
            "instance_url": self.instance_url,
        }

    def enable(self):
        """Enable Salesforce provider"""
        # Verify connection is available before enabling
        if self.sf or self._init_salesforce_connection():
            self.enabled = True
            logger.info("Salesforce provider enabled")
        else:
            logger.warning(
                "Salesforce provider cannot be enabled - credentials not configured or connection failed"
            )

    def disable(self):
        """Disable Salesforce provider"""
        self.enabled = False
        logger.info("Salesforce provider disabled")
