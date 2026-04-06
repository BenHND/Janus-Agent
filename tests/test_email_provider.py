"""
Tests for EmailProvider - Microsoft 365 integration
Part of TICKET-APP-001: Native Microsoft 365 / Outlook Connector
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from janus.memory.email_provider import EmailProvider


@pytest.fixture
def mock_o365_account():
    """Mock O365 Account"""
    account = Mock()
    account.is_authenticated = True
    
    # Mock mailbox
    mailbox = Mock()
    account.mailbox.return_value = mailbox
    
    return account


@pytest.fixture
def mock_message():
    """Mock O365 Message"""
    message = Mock()
    message.subject = "Important Update"
    message.received = datetime.now() - timedelta(hours=2)
    message.is_read = False
    message.importance = 'normal'
    message.has_attachments = False
    message.body_preview = "This is a preview of the email body..."
    message.body = "This is the full email body text."
    
    # Mock sender
    sender = Mock()
    sender.name = "John Doe"
    sender.address = "john@example.com"
    message.sender = sender
    
    return message


class TestEmailProviderInit:
    """Test EmailProvider initialization"""
    
    def test_init_without_credentials(self):
        """Test initialization without credentials"""
        provider = EmailProvider()
        assert provider.enabled is False
        assert provider.account is None
        assert provider.mailbox is None
    
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
                
                provider = EmailProvider()
                
                assert provider.client_id == 'test-client-id'
                assert provider.client_secret == 'test-client-secret'
                assert provider.account is not None
    
    def test_init_with_parameters(self):
        """Test initialization with explicit parameters"""
        with patch('O365.Account') as mock_account_class:
            mock_account = Mock()
            mock_account.is_authenticated = False
            mock_account_class.return_value = mock_account
            
            provider = EmailProvider(
                max_recent_emails=20,
                client_id='custom-client-id',
                client_secret='custom-secret',
                username='user@example.com'
            )
            
            assert provider.max_recent_emails == 20
            assert provider.client_id == 'custom-client-id'
            assert provider.client_secret == 'custom-secret'
            assert provider.username == 'user@example.com'


class TestEmailProviderAuthentication:
    """Test EmailProvider authentication"""
    
    def test_authenticate_success(self, mock_o365_account):
        """Test successful authentication"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            mock_o365_account.authenticate.return_value = True
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            
            result = provider.authenticate()
            
            assert result is True
            assert provider.mailbox is not None
    
    def test_authenticate_failure(self):
        """Test authentication failure"""
        with patch('O365.Account') as mock_account_class:
            mock_account = Mock()
            mock_account.is_authenticated = False
            mock_account.authenticate.return_value = False
            mock_account_class.return_value = mock_account
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            
            result = provider.authenticate()
            
            assert result is False
    
    def test_authenticate_without_account(self):
        """Test authentication without initialized account"""
        provider = EmailProvider()
        result = provider.authenticate()
        
        assert result is False


class TestEmailProviderEmails:
    """Test EmailProvider email retrieval"""
    
    def test_get_unread_count_disabled(self):
        """Test get_unread_count when disabled"""
        provider = EmailProvider()
        count = provider.get_unread_count()
        
        assert count == 0
    
    def test_fetch_unread_disabled(self):
        """Test fetch_unread when disabled"""
        provider = EmailProvider()
        emails = provider.fetch_unread()
        
        assert emails == []
    
    def test_fetch_unread_success(self, mock_o365_account, mock_message):
        """Test successful retrieval of unread emails"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock mailbox and inbox
            mock_mailbox = mock_o365_account.mailbox()
            mock_inbox = Mock()
            mock_mailbox.inbox_folder.return_value = mock_inbox
            
            # Mock query
            mock_query = Mock()
            mock_inbox.new_query.return_value = mock_query
            mock_query.on_attribute.return_value = mock_query
            mock_query.equals.return_value = mock_query
            mock_inbox.get_messages.return_value = [mock_message]
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            emails = provider.fetch_unread(limit=10)
            
            assert len(emails) == 1
            assert emails[0]['subject'] == "Important Update"
            assert emails[0]['sender_name'] == "John Doe"
            assert emails[0]['is_read'] is False
    
    def test_get_recent_emails_success(self, mock_o365_account, mock_message):
        """Test successful retrieval of recent emails"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock mailbox and inbox
            mock_mailbox = mock_o365_account.mailbox()
            mock_inbox = Mock()
            mock_mailbox.inbox_folder.return_value = mock_inbox
            mock_inbox.get_messages.return_value = [mock_message]
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            emails = provider.get_recent_emails(limit=5)
            
            assert len(emails) == 1
            assert emails[0]['subject'] == "Important Update"
    
    def test_search_emails_success(self, mock_o365_account, mock_message):
        """Test successful email search"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock mailbox and inbox
            mock_mailbox = mock_o365_account.mailbox()
            mock_inbox = Mock()
            mock_mailbox.inbox_folder.return_value = mock_inbox
            
            # Mock query
            mock_query = Mock()
            mock_inbox.new_query.return_value = mock_query
            mock_query.search.return_value = mock_query
            mock_inbox.get_messages.return_value = [mock_message]
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            results = provider.search_emails("Important")
            
            assert len(results) == 1
            assert results[0]['subject'] == "Important Update"
    
    def test_get_recent_senders(self, mock_o365_account, mock_message):
        """Test get_recent_senders"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock mailbox and inbox
            mock_mailbox = mock_o365_account.mailbox()
            mock_inbox = Mock()
            mock_mailbox.inbox_folder.return_value = mock_inbox
            mock_inbox.get_messages.return_value = [mock_message]
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            senders = provider.get_recent_senders(limit=5)
            
            assert len(senders) >= 1
            assert "John Doe" in senders[0]


class TestEmailProviderContext:
    """Test EmailProvider context methods"""
    
    def test_get_context_disabled(self):
        """Test get_context when provider is disabled"""
        provider = EmailProvider()
        context = provider.get_context()
        
        assert context['enabled'] is False
        assert context['unread_count'] == 0
        assert context['recent_emails'] == []
        assert context['recent_senders'] == []
        assert context['has_unread'] is False
    
    def test_get_context_enabled(self, mock_o365_account, mock_message):
        """Test get_context when provider is enabled"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            # Mock mailbox and inbox
            mock_mailbox = mock_o365_account.mailbox()
            mock_inbox = Mock()
            mock_mailbox.inbox_folder.return_value = mock_inbox
            mock_inbox.get_messages.return_value = []
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            # Mock the methods to return concrete values
            with patch.object(provider, 'get_unread_count', return_value=3):
                with patch.object(provider, 'get_recent_emails', return_value=[]):
                    with patch.object(provider, 'get_recent_senders', return_value=[]):
                        context = provider.get_context()
            
            assert context['enabled'] is True
            assert context['unread_count'] == 3
            assert context['has_unread'] is True
    
    def test_enable_without_mailbox(self):
        """Test enable without initialized mailbox"""
        provider = EmailProvider()
        provider.enable()
        
        # Should not enable without mailbox
        assert provider.enabled is False
    
    def test_disable(self, mock_o365_account):
        """Test disable provider"""
        with patch('O365.Account') as mock_account_class:
            mock_account_class.return_value = mock_o365_account
            
            provider = EmailProvider(
                client_id='test-id',
                client_secret='test-secret'
            )
            provider.enabled = True
            
            provider.disable()
            
            assert provider.enabled is False


class TestEmailProviderFormatting:
    """Test EmailProvider message formatting"""
    
    def test_format_email_complete(self, mock_message):
        """Test formatting a complete email"""
        provider = EmailProvider()
        formatted = provider._format_email(mock_message)
        
        assert formatted['subject'] == "Important Update"
        assert formatted['sender_name'] == "John Doe"
        assert formatted['sender_email'] == "john@example.com"
        assert formatted['is_read'] is False
        assert formatted['is_important'] is False
        assert formatted['has_attachments'] is False
        assert 'preview' in formatted['body'].lower()
    
    def test_format_email_minimal(self):
        """Test formatting a minimal email"""
        minimal_message = Mock()
        minimal_message.subject = "Test"
        minimal_message.received = datetime.now()
        minimal_message.sender = None
        minimal_message.body_preview = None
        minimal_message.body = None
        
        provider = EmailProvider()
        formatted = provider._format_email(minimal_message)
        
        assert formatted['subject'] == "Test"
        assert formatted['sender_name'] == "Unknown"
        assert formatted['body'] == ''
    
    def test_format_email_high_importance(self):
        """Test formatting a high importance email"""
        important_message = Mock()
        important_message.subject = "Urgent"
        important_message.received = datetime.now()
        important_message.is_read = False
        important_message.importance = 'high'
        important_message.has_attachments = True
        important_message.body_preview = "Urgent matter"
        
        sender = Mock()
        sender.name = "Boss"
        sender.address = "boss@example.com"
        important_message.sender = sender
        
        provider = EmailProvider()
        formatted = provider._format_email(important_message)
        
        assert formatted['is_important'] is True
        assert formatted['has_attachments'] is True
