"""
Tests for MessagingAgent - Slack & Teams integration
Part of TICKET-BIZ-002: Unified Messaging API (Slack & Teams)
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import sys

import pytest

# Mock pyautogui to avoid X11/Display issues in headless environments
sys.modules['pyautogui'] = Mock()
sys.modules['mouseinfo'] = Mock()

from janus.capabilities.agents.base_agent import AgentExecutionError
from janus.capabilities.agents.messaging_agent import MessagingAgent


@pytest.fixture
def mock_slack_client():
    """Mock SlackClient"""
    client = Mock()
    client.enabled = True
    
    # Mock post_message
    client.post_message.return_value = {
        "success": True,
        "ts": "1234567890.123456",
        "channel": "C1234567890",
        "message": "Test message"
    }
    
    # Mock read_channel_history
    client.read_channel_history.return_value = [
        {
            "user": "U1234567890",
            "text": "Hello from Slack!",
            "ts": "1234567890.123456"
        },
        {
            "user": "U0987654321",
            "text": "Reply to message",
            "ts": "1234567890.234567"
        }
    ]
    
    # Mock get_channel_messages_today
    client.get_channel_messages_today.return_value = [
        {
            "user": "U1234567890",
            "text": "Today's message",
            "ts": "1234567890.123456"
        }
    ]
    
    # Mock format_messages_for_summary
    client.format_messages_for_summary.return_value = "[10:30] User1: Hello\n[10:31] User2: Hi there"
    
    # Mock test_connection
    client.test_connection.return_value = True
    
    return client


@pytest.fixture
def mock_teams_client():
    """Mock TeamsClient"""
    client = Mock()
    client.enabled = True
    
    # Mock post_message
    client.post_message.return_value = {
        "success": True,
        "id": "1234567890",
        "created_at": "2024-12-13T10:30:00Z",
        "message": "Test message"
    }
    
    # Mock read_channel_history
    client.read_channel_history.return_value = [
        {
            "from": {"user": {"displayName": "John Doe"}},
            "body": {"content": "Hello from Teams!"},
            "createdDateTime": "2024-12-13T10:30:00Z"
        },
        {
            "from": {"user": {"displayName": "Jane Smith"}},
            "body": {"content": "Reply to message"},
            "createdDateTime": "2024-12-13T10:31:00Z"
        }
    ]
    
    # Mock get_channel_messages_today
    client.get_channel_messages_today.return_value = [
        {
            "from": {"user": {"displayName": "John Doe"}},
            "body": {"content": "Today's message"},
            "createdDateTime": "2024-12-13T10:30:00Z"
        }
    ]
    
    # Mock format_messages_for_summary
    client.format_messages_for_summary.return_value = "[10:30] John Doe: Hello\n[10:31] Jane Smith: Hi there"
    
    # Mock test_connection
    client.test_connection.return_value = True
    
    return client


@pytest.fixture
def messaging_agent_slack(mock_slack_client):
    """Create MessagingAgent with mocked Slack client"""
    with patch('janus.integrations.slack_client.SlackClient') as mock_slack_class:
        mock_slack_class.return_value = mock_slack_client
        agent = MessagingAgent(slack_token="xoxb-test-token")
        return agent


@pytest.fixture
def messaging_agent_teams(mock_teams_client):
    """Create MessagingAgent with mocked Teams client"""
    with patch('janus.integrations.teams_client.TeamsClient') as mock_teams_class:
        mock_teams_class.return_value = mock_teams_client
        agent = MessagingAgent(
            teams_client_id="test-client-id",
            teams_client_secret="test-client-secret",
            teams_tenant_id="test-tenant-id"
        )
        return agent


class TestMessagingAgentInit:
    """Test MessagingAgent initialization"""
    
    def test_init_without_credentials(self):
        """Test initialization without any credentials"""
        agent = MessagingAgent()
        assert agent.agent_name == "messaging"
        # Clients are created but disabled without credentials
        if agent.slack_client:
            assert not agent.slack_client.enabled
        if agent.teams_client:
            assert not agent.teams_client.enabled
    
    def test_init_with_slack_credentials(self, mock_slack_client):
        """Test initialization with Slack credentials"""
        with patch('janus.integrations.slack_client.SlackClient') as mock_slack_class:
            mock_slack_class.return_value = mock_slack_client
            agent = MessagingAgent(slack_token="xoxb-test-token")
            assert agent.slack_client is not None
            assert agent.slack_client.enabled
    
    def test_init_with_teams_credentials(self, mock_teams_client):
        """Test initialization with Teams credentials"""
        with patch('janus.integrations.teams_client.TeamsClient') as mock_teams_class:
            mock_teams_class.return_value = mock_teams_client
            agent = MessagingAgent(
                teams_client_id="test-client-id",
                teams_client_secret="test-client-secret",
                teams_tenant_id="test-tenant-id"
            )
            assert agent.teams_client is not None
            assert agent.teams_client.enabled


class TestMessagingAgentSlack:
    """Test MessagingAgent with Slack backend"""
    
    @pytest.mark.asyncio
    async def test_post_message_slack(self, messaging_agent_slack, mock_slack_client):
        """Test posting message to Slack"""
        result = await messaging_agent_slack.execute(
            action="post_message",
            args={
                "platform": "slack",
                "channel": "#general",
                "text": "Test message"
            },
            context={}
        )
        
        assert result["status"] == "success"
        mock_slack_client.post_message.assert_called_once_with(
            channel="#general",
            text="Test message",
            thread_ts=None
        )
    
    @pytest.mark.asyncio
    async def test_post_message_slack_with_thread(self, messaging_agent_slack, mock_slack_client):
        """Test posting message to Slack thread"""
        result = await messaging_agent_slack.execute(
            action="post_message",
            args={
                "platform": "slack",
                "channel": "#general",
                "text": "Reply message",
                "thread_ts": "1234567890.123456"
            },
            context={}
        )
        
        assert result["status"] == "success"
        mock_slack_client.post_message.assert_called_once_with(
            channel="#general",
            text="Reply message",
            thread_ts="1234567890.123456"
        )
    
    @pytest.mark.asyncio
    async def test_read_channel_history_slack(self, messaging_agent_slack, mock_slack_client):
        """Test reading Slack channel history"""
        result = await messaging_agent_slack.execute(
            action="read_channel_history",
            args={
                "platform": "slack",
                "channel": "#general",
                "limit": 50
            },
            context={}
        )
        
        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert len(result["data"]["messages"]) == 2
        mock_slack_client.read_channel_history.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_thread_slack_today(self, messaging_agent_slack, mock_slack_client):
        """Test summarizing Slack thread for today"""
        result = await messaging_agent_slack.execute(
            action="summarize_thread",
            args={
                "platform": "slack",
                "channel": "#general",
                "since_time": "today"
            },
            context={}
        )
        
        assert result["status"] == "success"
        assert "message_count" in result["data"]
        assert "messages" in result["data"]
        mock_slack_client.get_channel_messages_today.assert_called_once()


class TestMessagingAgentTeams:
    """Test MessagingAgent with Teams backend"""
    
    @pytest.mark.asyncio
    async def test_post_message_teams(self, messaging_agent_teams, mock_teams_client):
        """Test posting message to Teams"""
        result = await messaging_agent_teams.execute(
            action="post_message",
            args={
                "platform": "teams",
                "team_id": "team-123",
                "channel": "channel-456",
                "text": "Test message"
            },
            context={}
        )
        
        assert result["status"] == "success"
        mock_teams_client.post_message.assert_called_once_with(
            team_id="team-123",
            channel_id="channel-456",
            text="Test message"
        )
    
    @pytest.mark.asyncio
    async def test_post_message_teams_missing_team_id(self, messaging_agent_teams):
        """Test posting message to Teams without team_id raises error"""
        result = await messaging_agent_teams.execute(
            action="post_message",
            args={
                "platform": "teams",
                "channel": "channel-456",
                "text": "Test message"
            },
            context={}
        )
        
        assert result["status"] == "error"
        assert "team_id is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_read_channel_history_teams(self, messaging_agent_teams, mock_teams_client):
        """Test reading Teams channel history"""
        result = await messaging_agent_teams.execute(
            action="read_channel_history",
            args={
                "platform": "teams",
                "team_id": "team-123",
                "channel": "channel-456",
                "limit": 50
            },
            context={}
        )
        
        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert len(result["data"]["messages"]) == 2
        mock_teams_client.read_channel_history.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_thread_teams_today(self, messaging_agent_teams, mock_teams_client):
        """Test summarizing Teams thread for today"""
        result = await messaging_agent_teams.execute(
            action="summarize_thread",
            args={
                "platform": "teams",
                "team_id": "team-123",
                "channel": "channel-456",
                "since_time": "today"
            },
            context={}
        )
        
        assert result["status"] == "success"
        assert "message_count" in result["data"]
        assert "messages" in result["data"]
        mock_teams_client.get_channel_messages_today.assert_called_once()


class TestMessagingAgentErrors:
    """Test MessagingAgent error handling"""
    
    @pytest.mark.asyncio
    async def test_unsupported_platform(self, messaging_agent_slack):
        """Test error when using unsupported platform"""
        result = await messaging_agent_slack.execute(
            action="post_message",
            args={
                "platform": "discord",
                "channel": "#general",
                "text": "Test message"
            },
            context={}
        )
        
        assert result["status"] == "error"
        assert "Unsupported platform" in result["error"]
    
    @pytest.mark.asyncio
    async def test_platform_not_initialized(self):
        """Test error when platform client not initialized"""
        agent = MessagingAgent()  # No credentials
        
        result = await agent.execute(
            action="post_message",
            args={
                "platform": "slack",
                "channel": "#general",
                "text": "Test message"
            },
            context={}
        )
        
        assert result["status"] == "error"
        assert "not initialized" in result["error"]
    
    @pytest.mark.asyncio
    async def test_missing_required_args(self, messaging_agent_slack):
        """Test error when required arguments are missing"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await messaging_agent_slack.execute(
                action="post_message",
                args={
                    "platform": "slack"
                    # Missing channel and text
                },
                context={}
            )
        
        assert "Missing required argument" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unknown_action(self, messaging_agent_slack):
        """Test error when action is unknown"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await messaging_agent_slack.execute(
                action="unknown_action",
                args={},
                context={}
            )
        
        assert "Unknown action" in str(exc_info.value)


class TestLegacyActions:
    """Test legacy action support"""
    
    @pytest.mark.asyncio
    async def test_open_chat_not_implemented(self, messaging_agent_slack):
        """Test that open_chat returns error"""
        result = await messaging_agent_slack.execute(
            action="open_chat",
            args={"user_or_thread": "test"},
            context={}
        )
        
        assert result["status"] == "error"
        assert "not yet implemented" in result["error"]
    
    @pytest.mark.asyncio
    async def test_join_call_not_implemented(self, messaging_agent_slack):
        """Test that join_call returns error"""
        result = await messaging_agent_slack.execute(
            action="join_call",
            args={},
            context={}
        )
        
        assert result["status"] == "error"
        assert "not yet implemented" in result["error"]
    
    @pytest.mark.asyncio
    async def test_leave_call_not_implemented(self, messaging_agent_slack):
        """Test that leave_call returns error"""
        result = await messaging_agent_slack.execute(
            action="leave_call",
            args={},
            context={}
        )
        
        assert result["status"] == "error"
        assert "not yet implemented" in result["error"]
