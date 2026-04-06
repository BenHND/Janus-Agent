"""
Microsoft Teams Client - Integration with Microsoft Graph API

TICKET-BIZ-002: Unified Messaging API (Slack & Teams)

This module provides integration with Microsoft Teams using the Microsoft Graph API.
It supports posting messages and reading channel history.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class TeamsClient:
    """
    Microsoft Teams API client for messaging operations.
    
    Uses Microsoft Graph API to:
    - Post messages to channels
    - Read channel history
    - Retrieve thread messages
    
    Authentication is done via Azure AD using MSAL (Microsoft Authentication Library).
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize Teams client.
        
        Args:
            client_id: Azure AD application (client) ID. If not provided, reads from TEAMS_CLIENT_ID env var.
            client_secret: Azure AD client secret. If not provided, reads from TEAMS_CLIENT_SECRET env var.
            tenant_id: Azure AD tenant ID. If not provided, reads from TEAMS_TENANT_ID env var.
        """
        self.enabled = False  # Disabled by default until credentials are configured
        self.app = None
        self.access_token = None
        self.msal = None
        
        # Get credentials from parameters or environment variables
        self.client_id = client_id or os.environ.get("TEAMS_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("TEAMS_CLIENT_SECRET")
        self.tenant_id = tenant_id or os.environ.get("TEAMS_TENANT_ID")
        
        self.authority = None
        self.scope = ["https://graph.microsoft.com/.default"]
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
        # Try to initialize Teams connection if credentials are available
        if self.client_id and self.client_secret and self.tenant_id:
            self._init_teams_connection()
    
    def _init_teams_connection(self) -> bool:
        """
        Initialize Teams/Microsoft Graph connection.
        
        Returns:
            True if connection is established, False otherwise
        """
        try:
            import msal
            
            self.msal = msal
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            
            # Initialize MSAL confidential client application
            self.app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            logger.info("TeamsClient initialized successfully")
            return True
        except ImportError:
            logger.warning("msal is not installed. Install it with: pip install 'janus[messaging]'")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Teams connection: {e}")
            return False
    
    def _get_access_token(self) -> str:
        """
        Get or refresh access token for Microsoft Graph API.
        
        Returns:
            Access token string
        
        Raises:
            Exception: If authentication fails
        """
        # Try to get token from cache first
        result = self.app.acquire_token_silent(self.scope, account=None)
        
        if not result:
            # No cached token, acquire new one
            result = self.app.acquire_token_for_client(scopes=self.scope)
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            logger.debug("Successfully acquired access token")
            return self.access_token
        else:
            error = result.get("error", "Unknown error")
            error_desc = result.get("error_description", "No description")
            logger.error(f"Failed to acquire token: {error} - {error_desc}")
            raise Exception(f"Authentication failed: {error}")
    
    def _make_graph_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to graph_endpoint)
            data: Optional JSON data for POST requests
        
        Returns:
            Response JSON dictionary
        
        Raises:
            requests.HTTPError: If the request fails
        """
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.graph_endpoint}/{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def post_message(
        self,
        team_id: str,
        channel_id: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Post a message to a Teams channel.
        
        Args:
            team_id: Teams team ID (GUID)
            channel_id: Channel ID (GUID)
            text: Message text to post
        
        Returns:
            Dictionary with message details including 'id' and 'createdDateTime'
        
        Raises:
            requests.HTTPError: If the Graph API returns an error
        """
        endpoint = f"teams/{team_id}/channels/{channel_id}/messages"
        data = {
            "body": {
                "content": text
            }
        }
        
        try:
            response = self._make_graph_request("POST", endpoint, data)
            logger.info(f"Message posted to Teams channel {channel_id}: {text[:50]}...")
            return {
                "success": True,
                "id": response.get("id"),
                "created_at": response.get("createdDateTime"),
                "message": text
            }
        except requests.HTTPError as e:
            logger.error(f"Failed to post message to Teams channel {channel_id}: {e}")
            raise
    
    def read_channel_history(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Read message history from a Teams channel.
        
        Args:
            team_id: Teams team ID (GUID)
            channel_id: Channel ID (GUID)
            limit: Maximum number of messages to retrieve (default: 50)
        
        Returns:
            List of message dictionaries with 'body', 'from', 'createdDateTime', etc.
        
        Raises:
            requests.HTTPError: If the Graph API returns an error
        """
        endpoint = f"teams/{team_id}/channels/{channel_id}/messages?$top={min(limit, 50)}"
        
        try:
            response = self._make_graph_request("GET", endpoint)
            messages = response.get("value", [])
            logger.info(f"Retrieved {len(messages)} messages from Teams channel {channel_id}")
            return messages
        except requests.HTTPError as e:
            logger.error(f"Failed to read history from Teams channel {channel_id}: {e}")
            raise
    
    def get_channel_messages_since(
        self,
        team_id: str,
        channel_id: str,
        since_time: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a channel since a specific datetime.
        
        Args:
            team_id: Teams team ID (GUID)
            channel_id: Channel ID (GUID)
            since_time: Retrieve messages after this datetime
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        # Format datetime for OData filter (ISO 8601 format)
        since_str = since_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        endpoint = (
            f"teams/{team_id}/channels/{channel_id}/messages"
            f"?$filter=createdDateTime ge '{since_str}'"
            f"&$top={min(limit, 50)}"
        )
        
        try:
            response = self._make_graph_request("GET", endpoint)
            messages = response.get("value", [])
            logger.info(f"Retrieved {len(messages)} messages since {since_str}")
            return messages
        except requests.HTTPError as e:
            logger.error(f"Failed to get messages since {since_str}: {e}")
            raise
    
    def get_channel_messages_today(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a channel since the start of today.
        
        Args:
            team_id: Teams team ID (GUID)
            channel_id: Channel ID (GUID)
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        from datetime import timezone
        today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_channel_messages_since(team_id, channel_id, today_start, limit)
    
    def format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages into a text string suitable for LLM summarization.
        
        Args:
            messages: List of message dictionaries from Graph API
        
        Returns:
            Formatted text string with messages
        """
        if not messages:
            return "No messages found."
        
        formatted = []
        for msg in reversed(messages):  # Reverse to show chronological order
            user = msg.get("from", {}).get("user", {}).get("displayName", "Unknown")
            body = msg.get("body", {}).get("content", "")
            created = msg.get("createdDateTime", "")
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                time_str = "??:??"
            
            formatted.append(f"[{time_str}] {user}: {body}")
        
        return "\n".join(formatted)
    
    def list_teams(self) -> List[Dict[str, Any]]:
        """
        List all teams the app has access to.
        
        Returns:
            List of team dictionaries
        
        Raises:
            requests.HTTPError: If the Graph API returns an error
        """
        try:
            response = self._make_graph_request("GET", "teams")
            teams = response.get("value", [])
            logger.info(f"Retrieved {len(teams)} teams")
            return teams
        except requests.HTTPError as e:
            logger.error(f"Failed to list teams: {e}")
            raise
    
    def list_channels(self, team_id: str) -> List[Dict[str, Any]]:
        """
        List all channels in a team.
        
        Args:
            team_id: Teams team ID (GUID)
        
        Returns:
            List of channel dictionaries
        
        Raises:
            requests.HTTPError: If the Graph API returns an error
        """
        endpoint = f"teams/{team_id}/channels"
        
        try:
            response = self._make_graph_request("GET", endpoint)
            channels = response.get("value", [])
            logger.info(f"Retrieved {len(channels)} channels for team {team_id}")
            return channels
        except requests.HTTPError as e:
            logger.error(f"Failed to list channels for team {team_id}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the Microsoft Graph API connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self._get_access_token()
            logger.info("Teams connection test successful")
            return True
        except Exception as e:
            logger.error(f"Teams connection test failed: {e}")
            return False
    
    def enable(self):
        """Enable Teams client"""
        # Verify connection is available before enabling
        if self.app or self._init_teams_connection():
            self.enabled = True
            logger.info("Teams client enabled")
        else:
            logger.warning(
                "Teams client cannot be enabled - credentials not configured or connection failed"
            )
    
    def disable(self):
        """Disable Teams client"""
        self.enabled = False
        logger.info("Teams client disabled")
