"""
Tests for CalendarProvider - Microsoft 365 integration
Part of TICKET-APP-001: Native Microsoft 365 / Outlook Connector
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from janus.memory.calendar_provider import CalendarProvider


@pytest.fixture
def mock_o365_account():
    """Mock O365 Account"""
    account = Mock()
    account.is_authenticated = True
    
    # Mock schedule and calendar
    schedule = Mock()
    calendar = Mock()
    schedule.get_default_calendar.return_value = calendar
    account.schedule.return_value = schedule
    
    return account


@pytest.fixture
def mock_event():
    """Mock O365 Event"""
    event = Mock()
    event.subject = "Team Standup"
    event.start = datetime.now() + timedelta(hours=2)
    event.end = datetime.now() + timedelta(hours=2, minutes=30)
    event.location = {"displayName": "Conference Room A"}
    event.body = "Daily standup meeting"
    event.is_online_meeting = False
    
    # Mock attendees
    attendee1 = Mock()
    attendee1.name = "John Doe"
    attendee1.address = "john@example.com"
    
    attendee2 = Mock()
    attendee2.name = "Jane Smith"
    attendee2.address = "jane@example.com"
    
    event.attendees = [attendee1, attendee2]
    
    # Mock organizer
    organizer = Mock()
    organizer.name = "Alice Manager"
    organizer.address = "alice@example.com"
    event.organizer = organizer
    
    return event


class TestCalendarProviderInit:
    """Test CalendarProvider initialization"""
    
    def test_init_without_credentials(self):
        """Test initialization without credentials"""
        provider = CalendarProvider()
        assert provider.enabled is False
        assert provider.account is None
        assert provider.calendar is None
    
    def test_init_with_credentials(self):
        """Test initialization with credentials"""
        with patch.dict(os.environ, {
            'O365_CLIENT_ID': 'test-client-id',
            'O365_CLIENT_SECRET': 'test-client-secret',
        }):
            with patch('O365.Account') as mock_account_class:
                mock_account = Mock()
                mock_account.is_authenticated = False
                mock_account_class.return_value = mock_account
                
                provider = CalendarProvider()
                
                assert provider.client_id == 'test-client-id'
                assert provider.client_secret == 'test-client-secret'
                assert provider.account is not None
    
    def test_init_with_parameters(self):
        """Test initialization with explicit parameters"""
        with patch('O365.Account') as mock_account_class:
            mock_account = Mock()
            mock_account.is_authenticated = False
            mock_account_class.return_value = mock_account
            
            provider = CalendarProvider(
                client_id='custom-client-id',
                client_secret='custom-secret',
                username='user@example.com'
            )
            
            assert provider.client_id == 'custom-client-id'
            assert provider.client_secret == 'custom-secret'
            assert provider.username == 'user@example.com'


class TestCalendarProviderAuthentication:
    """Test CalendarProvider authentication"""
    
    def test_authenticate_success(self, mock_o365_account):
        """Test successful authentication"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            mock_o365_account.authenticate.return_value = True
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            
            result = provider.authenticate()
            
            assert result is True
            assert provider.calendar is not None
    
    def test_authenticate_failure(self):
        """Test authentication failure"""
        with patch('O365.Account') as mock_account_class:
            mock_account = Mock()
            mock_account.is_authenticated = False
            mock_account.authenticate.return_value = False
            mock_account_class.return_value = mock_account
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            
            result = provider.authenticate()
            
            assert result is False
    
    def test_authenticate_without_account(self):
        """Test authentication without initialized account"""
        provider = CalendarProvider()
        result = provider.authenticate()
        
        assert result is False


class TestCalendarProviderEvents:
    """Test CalendarProvider event retrieval"""
    
    def test_get_upcoming_events_disabled(self):
        """Test get_upcoming_events when disabled"""
        provider = CalendarProvider()
        events = provider.get_upcoming_events()
        
        assert events == []
    
    def test_get_upcoming_events_success(self, mock_o365_account, mock_event):
        """Test successful retrieval of upcoming events"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock calendar query
            mock_calendar = mock_o365_account.schedule().get_default_calendar()
            mock_query = Mock()
            mock_calendar.new_query.return_value = mock_query
            mock_query.chain.return_value = Mock()
            mock_calendar.get_events.return_value = [mock_event]
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            events = provider.get_upcoming_events(limit=5)
            
            assert len(events) == 1
            assert events[0]['title'] == "Team Standup"
            assert len(events[0]['attendees']) == 2
            assert events[0]['attendees'][0]['name'] == "John Doe"
    
    def test_get_current_event_none(self, mock_o365_account):
        """Test get_current_event when no event is active"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock calendar query returning no events
            mock_calendar = mock_o365_account.schedule().get_default_calendar()
            mock_query = Mock()
            mock_calendar.new_query.return_value = mock_query
            mock_query.chain.return_value = Mock()
            mock_calendar.get_events.return_value = []
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            current = provider.get_current_event()
            
            assert current is None
    
    def test_get_next_event(self, mock_o365_account, mock_event):
        """Test get_next_event"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock calendar query
            mock_calendar = mock_o365_account.schedule().get_default_calendar()
            mock_query = Mock()
            mock_calendar.new_query.return_value = mock_query
            mock_query.chain.return_value = Mock()
            mock_calendar.get_events.return_value = [mock_event]
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            next_event = provider.get_next_event()
            
            assert next_event is not None
            assert next_event['title'] == "Team Standup"


class TestCalendarProviderContext:
    """Test CalendarProvider context methods"""
    
    def test_get_context_disabled(self):
        """Test get_context when provider is disabled"""
        provider = CalendarProvider()
        context = provider.get_context()
        
        assert context['enabled'] is False
        assert context['current_event'] is None
        assert context['next_event'] is None
        assert context['upcoming_events'] == []
        assert context['is_in_meeting'] is False
    
    def test_get_context_enabled(self, mock_o365_account, mock_event):
        """Test get_context when provider is enabled"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock calendar query
            mock_calendar = mock_o365_account.schedule().get_default_calendar()
            mock_query = Mock()
            mock_calendar.new_query.return_value = mock_query
            mock_query.chain.return_value = Mock()
            mock_calendar.get_events.return_value = [mock_event]
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            context = provider.get_context()
            
            assert context['enabled'] is True
            assert len(context['upcoming_events']) == 1
            assert context['next_event']['title'] == "Team Standup"
    
    def test_enable_without_calendar(self):
        """Test enable without initialized calendar"""
        provider = CalendarProvider()
        provider.enable()
        
        # Should not enable without calendar
        assert provider.enabled is False
    
    def test_disable(self, mock_o365_account):
        """Test disable provider"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            provider = CalendarProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            provider.disable()
            
            assert provider.enabled is False


class TestCalendarProviderFormatting:
    """Test CalendarProvider event formatting"""
    
    def test_format_event_complete(self, mock_event):
        """Test formatting a complete event"""
        provider = CalendarProvider()
        formatted = provider._format_event(mock_event)
        
        assert formatted['title'] == "Team Standup"
        assert formatted['location'] == "Conference Room A"
        assert formatted['is_online_meeting'] is False
        assert len(formatted['attendees']) == 2
        assert formatted['organizer']['name'] == "Alice Manager"
    
    def test_format_event_minimal(self):
        """Test formatting a minimal event"""
        minimal_event = Mock()
        minimal_event.subject = "Quick Sync"
        minimal_event.start = datetime.now()
        minimal_event.end = datetime.now() + timedelta(minutes=15)
        minimal_event.location = None
        minimal_event.attendees = []
        minimal_event.organizer = None
        minimal_event.body = None
        
        provider = CalendarProvider()
        formatted = provider._format_event(minimal_event)
        
        assert formatted['title'] == "Quick Sync"
        assert formatted['location'] == ''
        assert formatted['attendees'] == []
        assert formatted['organizer'] is None
