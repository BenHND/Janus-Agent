"""
TICKET-BIZ-002: Unified Messaging API (Slack & Teams)

MessagingAgent - Messaging Platform Automation

TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

This agent handles messaging operations for Teams and Slack including:
- Posting messages to channels
- Reading channel history
- Summarizing channel discussions

The agent automatically selects the appropriate backend (Slack or Teams)
based on configuration or context.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action


class MessagingAgent(BaseAgent):
    """
    Agent for messaging platform automation.
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Supported actions:
    - post_message(platform, channel, text, team_id=None)
    - read_channel_history(platform, channel, limit=50, team_id=None)
    - summarize_thread(platform, channel, since_time=None, team_id=None)
    
    Platforms:
    - slack: Requires SLACK_BOT_TOKEN
    - teams: Requires TEAMS_CLIENT_ID, TEAMS_CLIENT_SECRET, TEAMS_TENANT_ID
    """
    
    def __init__(
        self,
        slack_token: Optional[str] = None,
        teams_client_id: Optional[str] = None,
        teams_client_secret: Optional[str] = None,
        teams_tenant_id: Optional[str] = None,
        llm_client: Optional[Any] = None,
        provider: str = "slack"
    ):
        """
        Initialize MessagingAgent.
        
        Args:
            slack_token: Slack bot token (optional, reads from env if not provided)
            teams_client_id: Teams client ID (optional, reads from env if not provided)
            teams_client_secret: Teams client secret (optional, reads from env if not provided)
            teams_tenant_id: Teams tenant ID (optional, reads from env if not provided)
            llm_client: LLM client for summarization (optional, uses default if not provided)
            provider: Default messaging provider ("slack", "teams", "discord", "telegram")
        """
        super().__init__("messaging")
        
        self.provider = provider
        self.slack_client = None
        self.teams_client = None
        self.llm_client = llm_client
        
        # Initialize Slack client - follows Salesforce/O365 pattern
        try:
            from janus.integrations.slack_client import SlackClient
            self.slack_client = SlackClient(bot_token=slack_token)
            # Enable if credentials are available
            if self.slack_client.client:
                self.slack_client.enable()
                self.logger.info("Messaging Agent initialized with Slack connection")
        except Exception as e:
            self.logger.warning(f"Slack client not available: {e}")
        
        # Initialize Teams client - follows Salesforce/O365 pattern
        try:
            from janus.integrations.teams_client import TeamsClient
            self.teams_client = TeamsClient(
                client_id=teams_client_id,
                client_secret=teams_client_secret,
                tenant_id=teams_tenant_id
            )
            # Enable if credentials are available
            if self.teams_client.app:
                self.teams_client.enable()
                self.logger.info("Messaging Agent initialized with Teams connection")
        except Exception as e:
            self.logger.warning(f"Teams client not available: {e}")
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a messaging action by routing to decorated methods."""
        # P2: Dry-run mode - preview without sending messages (prevents accidental spam)
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would send message via '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": False,  # Message sending is not reversible
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
    
    def _get_client(self, platform: str):
        """Get the appropriate messaging client."""
        if platform.lower() == "slack":
            if not self.slack_client or not self.slack_client.enabled:
                raise AgentExecutionError(
                    module=self.agent_name,
                    action="get_client",
                    details="Slack client not initialized. Set SLACK_BOT_TOKEN environment variable.",
                    recoverable=False
                )
            return self.slack_client
        elif platform.lower() == "teams":
            if not self.teams_client or not self.teams_client.enabled:
                raise AgentExecutionError(
                    module=self.agent_name,
                    action="get_client",
                    details="Teams client not initialized. Set TEAMS_CLIENT_ID, TEAMS_CLIENT_SECRET, and TEAMS_TENANT_ID environment variables.",
                    recoverable=False
                )
            return self.teams_client
        else:
            raise AgentExecutionError(
                module=self.agent_name,
                action="get_client",
                details=f"Unsupported platform: {platform}. Supported platforms: slack, teams",
                recoverable=False
            )
    
    @agent_action(
        description="Post a message to a messaging channel",
        required_args=["platform", "channel", "text"],
        optional_args={"team_id": None, "thread_ts": None},
        providers=["slack", "teams", "discord", "telegram"],
        examples=[
            "messaging.post_message(platform='slack', channel='#general', text='Hello team!')",
            "messaging.post_message(platform='teams', channel='general', text='Hi!', team_id='team123')"
        ]
    )
    async def _post_message(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Post a message to a channel."""
        platform = args["platform"]
        channel = args["channel"]
        text = args["text"]
        team_id = args.get("team_id")
        thread_ts = args.get("thread_ts")
        
        client = self._get_client(platform)
        
        if platform.lower() == "slack":
            result = client.post_message(channel=channel, text=text, thread_ts=thread_ts)
        else:  # teams
            if not team_id:
                raise AgentExecutionError(
                    module=self.agent_name,
                    action="post_message",
                    details="team_id is required for Teams platform",
                    recoverable=False
                )
            result = client.post_message(team_id=team_id, channel_id=channel, text=text)
        
        return self._success_result(data=result)
    
    # Alias for post_message
    _send_message = _post_message
    
    @agent_action(
        description="Read message history from a channel",
        required_args=["platform", "channel"],
        optional_args={"limit": 50, "team_id": None},
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.read_channel_history(platform='slack', channel='#general', limit=100)"]
    )
    async def _read_channel_history(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Read channel history."""
        platform = args["platform"]
        channel = args["channel"]
        limit = args["limit"]
        team_id = args.get("team_id")
        
        client = self._get_client(platform)
        
        if platform.lower() == "slack":
            messages = client.read_channel_history(channel=channel, limit=limit)
        else:  # teams
            if not team_id:
                raise AgentExecutionError(
                    module=self.agent_name,
                    action="read_channel_history",
                    details="team_id is required for Teams platform",
                    recoverable=False
                )
            messages = client.read_channel_history(team_id=team_id, channel_id=channel, limit=limit)
        
        return self._success_result(data={"messages": messages, "count": len(messages)})
    
    @agent_action(
        description="Summarize a channel thread using AI",
        required_args=["platform", "channel"],
        optional_args={"since_time": None, "limit": 50, "team_id": None},
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.summarize_thread(platform='slack', channel='#general', since_time='today')"]
    )
    async def _summarize_thread(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize a channel thread using LLM."""
        platform = args["platform"]
        channel = args["channel"]
        since_time = args.get("since_time")
        limit = args["limit"]
        team_id = args.get("team_id")
        
        client = self._get_client(platform)
            
        # Get messages
        if since_time == "today":
            if platform.lower() == "slack":
                messages = client.get_channel_messages_today(channel=channel, limit=limit)
            else:  # teams
                if not team_id:
                    raise AgentExecutionError(
                        module=self.agent_name,
                        action="summarize_thread",
                        details="team_id is required for Teams platform",
                        recoverable=False
                    )
                messages = client.get_channel_messages_today(team_id=team_id, channel_id=channel, limit=limit)
        elif isinstance(since_time, datetime):
            if platform.lower() == "slack":
                messages = client.get_channel_messages_since(channel=channel, since_time=since_time, limit=limit)
            else:  # teams
                if not team_id:
                    raise AgentExecutionError(
                        module=self.agent_name,
                        action="summarize_thread",
                        details="team_id is required for Teams platform",
                        recoverable=False
                    )
                messages = client.get_channel_messages_since(team_id=team_id, channel_id=channel, since_time=since_time, limit=limit)
        else:
            # Get recent messages
            if platform.lower() == "slack":
                messages = client.read_channel_history(channel=channel, limit=limit)
            else:  # teams
                if not team_id:
                    raise AgentExecutionError(
                        module=self.agent_name,
                        action="summarize_thread",
                        details="team_id is required for Teams platform",
                        recoverable=False
                    )
                messages = client.read_channel_history(team_id=team_id, channel_id=channel, limit=limit)
        
        # Format messages for summarization
        formatted_messages = client.format_messages_for_summary(messages)
        
        # Generate summary using LLM if available
        if self.llm_client:
            summary = await self._generate_summary(formatted_messages, channel)
        else:
            summary = f"Retrieved {len(messages)} messages. LLM not available for summarization."
        
        return self._success_result(data={
            "summary": summary,
            "message_count": len(messages),
            "messages": formatted_messages
        })
    
    async def _generate_summary(self, messages: str, channel: str) -> str:
        """Generate a summary of messages using LLM."""
        try:
            # Skip LLM summary if no LLM client available
            if not self.llm_client:
                message_count = len(messages.split('\n'))
                return f"Retrieved {message_count} messages. LLM not available for summarization."
            
            prompt = f"""Summarize the following discussion from channel {channel}. 
Provide a concise summary of the main topics, key decisions, and action items mentioned.

Messages:
{messages}

Summary:"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            return response.strip()
        except Exception as e:
            self.logger.warning(f"Failed to generate LLM summary: {e}")
            message_count = len(messages.split('\n'))
            return f"Summary generation failed. {message_count} messages retrieved."
    
    @agent_action(
        description="Open a chat or thread (placeholder)",
        required_args=["user_or_thread"],
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.open_chat(user_or_thread='@username')"]
    )
    async def _open_chat(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Open a chat or thread (legacy support)."""
        return self._error_result(
            error="open_chat is not yet implemented for API-based messaging. Use post_message instead.",
            recoverable=False
        )
    
    # Alias
    _open_thread = _open_chat
    
    async def _send_message(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message (alias for post_message)."""
        return await self._post_message(args, context)
    
    @agent_action(
        description="Join a call (placeholder)",
        required_args=[],
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.join_call()"]
    )
    async def _join_call(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Join a call."""
        return self._error_result(
            error="join_call not yet implemented",
            recoverable=False
        )
    
    @agent_action(
        description="Leave a call (placeholder)",
        required_args=[],
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.leave_call()"]
    )
    async def _leave_call(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Leave a call."""
        return self._error_result(
            error="leave_call not yet implemented",
            recoverable=False
        )
    
    @agent_action(
        description="Search for messages in channels (placeholder)",
        required_args=["query"],
        optional_args={"platform": None},
        providers=["slack", "teams", "discord", "telegram"],
        examples=["messaging.search_messages(query='project update', platform='slack')"]
    )
    async def _search_messages(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search for messages in channels."""
        return self._error_result(
            error="search_messages not yet fully implemented",
            recoverable=False
        )
