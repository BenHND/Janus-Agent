"""
Slack Client - Integration with Slack API

TICKET-BIZ-002: Unified Messaging API (Slack & Teams)

This module provides integration with Slack using the official Slack SDK.
It supports posting messages and reading channel history.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SlackClient:
    """
    Slack API client for messaging operations.
    
    Provides methods to:
    - Post messages to channels
    - Read channel history
    - Retrieve thread messages
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Slack client.
        
        Args:
            bot_token: Slack bot token. If not provided, reads from SLACK_BOT_TOKEN env var.
        """
        self.enabled = False  # Disabled by default until credentials are configured
        self.client = None
        self.SlackApiError = None
        
        # Get credentials from parameters or environment variables
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
        
        # Try to initialize Slack connection if credentials are available
        if self.bot_token:
            self._init_slack_connection()
    
    def _init_slack_connection(self) -> bool:
        """
        Initialize Slack connection.
        
        Returns:
            True if connection is established, False otherwise
        """
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            self.SlackApiError = SlackApiError
            self.client = WebClient(token=self.bot_token)
            logger.info("SlackClient initialized successfully")
            return True
        except ImportError:
            logger.warning("slack_sdk is not installed. Install it with: pip install 'janus[messaging]'")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Slack connection: {e}")
            return False
    
    def post_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """
        Post a message to a Slack channel.
        
        Args:
            channel: Channel ID or name (e.g., "#general" or "C1234567890")
            text: Message text to post
            thread_ts: Optional thread timestamp to reply in a thread
        
        Returns:
            Dictionary with message details including 'ts' (timestamp) and 'channel'
        
        Raises:
            SlackApiError: If the Slack API returns an error
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            logger.info(f"Message posted to {channel}: {text[:50]}...")
            return {
                "success": True,
                "ts": response["ts"],
                "channel": response["channel"],
                "message": text
            }
        except self.SlackApiError as e:
            logger.error(f"Failed to post message to {channel}: {e.response['error']}")
            raise
    
    def read_channel_history(
        self,
        channel: str,
        limit: int = 50,
        oldest: Optional[float] = None,
        latest: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Read message history from a Slack channel.
        
        Args:
            channel: Channel ID or name (e.g., "#general" or "C1234567890")
            limit: Maximum number of messages to retrieve (default: 50, max: 1000)
            oldest: Only messages after this Unix timestamp (inclusive)
            latest: Only messages before this Unix timestamp (exclusive)
        
        Returns:
            List of message dictionaries with 'text', 'user', 'ts' (timestamp), etc.
        
        Raises:
            SlackApiError: If the Slack API returns an error
        """
        try:
            response = self.client.conversations_history(
                channel=channel,
                limit=min(limit, 1000),  # Slack API limit
                oldest=oldest,
                latest=latest
            )
            messages = response["messages"]
            logger.info(f"Retrieved {len(messages)} messages from {channel}")
            return messages
        except self.SlackApiError as e:
            logger.error(f"Failed to read history from {channel}: {e.response['error']}")
            raise
    
    def get_channel_messages_since(
        self,
        channel: str,
        since_time: datetime,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a channel since a specific datetime.
        
        Args:
            channel: Channel ID or name
            since_time: Retrieve messages after this datetime
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        oldest = since_time.timestamp()
        return self.read_channel_history(channel=channel, limit=limit, oldest=oldest)
    
    def get_channel_messages_today(self, channel: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get messages from a channel since the start of today.
        
        Args:
            channel: Channel ID or name
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        from datetime import timezone
        today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_channel_messages_since(channel, today_start, limit)
    
    def format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages into a text string suitable for LLM summarization.
        
        Args:
            messages: List of message dictionaries from Slack API
        
        Returns:
            Formatted text string with messages
        """
        if not messages:
            return "No messages found."
        
        formatted = []
        for msg in reversed(messages):  # Reverse to show chronological order
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            ts = msg.get("ts", "")
            
            # Format timestamp
            try:
                dt = datetime.fromtimestamp(float(ts))
                time_str = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                time_str = "??:??"
            
            formatted.append(f"[{time_str}] {user}: {text}")
        
        return "\n".join(formatted)
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information from Slack.
        
        Args:
            user_id: Slack user ID
        
        Returns:
            User information dictionary
        
        Raises:
            SlackApiError: If the Slack API returns an error
        """
        try:
            response = self.client.users_info(user=user_id)
            return response["user"]
        except self.SlackApiError as e:
            logger.error(f"Failed to get user info for {user_id}: {e.response['error']}")
            raise
    
    def enable(self):
        """Enable Slack client"""
        # Verify connection is available before enabling
        if self.client or self._init_slack_connection():
            self.enabled = True
            logger.info("Slack client enabled")
        else:
            logger.warning(
                "Slack client cannot be enabled - credentials not configured or connection failed"
            )
    
    def disable(self):
        """Disable Slack client"""
        self.enabled = False
        logger.info("Slack client disabled")
    
    def test_connection(self) -> bool:
        """
        Test the Slack API connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.client.auth_test()
            logger.info(f"Slack connection test successful. Bot: {response['user']}")
            return True
        except self.SlackApiError as e:
            logger.error(f"Slack connection test failed: {e.response['error']}")
            return False
