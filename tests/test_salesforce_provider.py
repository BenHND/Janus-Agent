"""
Tests for SalesforceProvider - Salesforce CRM integration
Part of TICKET-BIZ-001: Salesforce Native Connector (CRM)
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from janus.integrations.salesforce_provider import SalesforceProvider


@pytest.fixture
def mock_salesforce():
    """Mock simple_salesforce.Salesforce"""
    sf = Mock()
    sf.sf_instance = "mycompany.my.salesforce.com"
    
    # Mock Contact object
    contact_mock = Mock()
    contact_mock.get.return_value = {
        'Id': '003XXXXXXXXXXXX',
        'Name': 'John Doe',
        'FirstName': 'John',
        'LastName': 'Doe',
        'Title': 'VP of Sales',
        'Email': 'john.doe@acme.com',
        'Phone': '+1-555-0100',
        'AccountId': '001XXXXXXXXXXXX',
        'Department': 'Sales',
        'MailingCity': 'San Francisco',
    }
    sf.Contact = contact_mock
    
    # Mock Opportunity object
    opportunity_mock = Mock()
    opportunity_mock.get.return_value = {
        'Id': '006XXXXXXXXXXXX',
        'Name': 'Acme Corp - Q4 Deal',
        'StageName': 'Negotiation',
        'Amount': 150000,
        'CloseDate': '2024-12-31',
        'Probability': 75,
        'Type': 'New Business',
        'AccountId': '001XXXXXXXXXXXX',
    }
    sf.Opportunity = opportunity_mock
    
    # Mock query method
    sf.query = Mock()
    
    return sf


@pytest.fixture
def mock_contact_query_result():
    """Mock SOQL query result for contacts"""
    return {
        'totalSize': 1,
        'done': True,
        'records': [
            {
                'Id': '003XXXXXXXXXXXX',
                'Name': 'Jane Smith',
                'FirstName': 'Jane',
                'LastName': 'Smith',
                'Title': 'Director of Engineering',
                'Email': 'jane.smith@acme.com',
                'Phone': '+1-555-0200',
                'Account': {
                    'Name': 'Acme Corp',
                },
                'Department': 'Engineering',
                'MailingCity': 'New York',
            }
        ]
    }


@pytest.fixture
def mock_opportunity_query_result():
    """Mock SOQL query result for opportunities"""
    return {
        'totalSize': 2,
        'done': True,
        'records': [
            {
                'Id': '006XXXXXXXXXXXX1',
                'Name': 'Acme - License Renewal',
                'StageName': 'Closed Won',
                'Amount': 200000,
                'CloseDate': '2024-11-15',
                'Probability': 100,
                'Type': 'Existing Business',
                'Account': {
                    'Name': 'Acme Corp',
                },
            },
            {
                'Id': '006XXXXXXXXXXXX2',
                'Name': 'Acme - Expansion Deal',
                'StageName': 'Proposal',
                'Amount': 350000,
                'CloseDate': '2025-01-31',
                'Probability': 60,
                'Type': 'New Business',
                'Account': {
                    'Name': 'Acme Corp',
                },
            },
        ]
    }


class TestSalesforceProviderInit:
    """Test SalesforceProvider initialization"""
    
    def test_init_without_credentials(self):
        """Test initialization without credentials"""
        provider = SalesforceProvider()
        assert provider.enabled is False
        assert provider.sf is None
        assert provider.username is None
    
    def test_init_with_env_credentials(self):
        """Test initialization with environment variables"""
        with patch.dict(os.environ, {
            'SALESFORCE_USERNAME': 'test@example.com',
            'SALESFORCE_PASSWORD': 'testpass',
            'SALESFORCE_SECURITY_TOKEN': 'testtoken',
        }):
            with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
                mock_sf = Mock()
                mock_sf.sf_instance = "test.my.salesforce.com"
                mock_sf_class.return_value = mock_sf
                
                provider = SalesforceProvider()
                
                assert provider.username == 'test@example.com'
                assert provider.password == 'testpass'
                assert provider.security_token == 'testtoken'
                assert provider.sf is not None
                assert provider.instance_url == "https://test.my.salesforce.com"
    
    def test_init_with_parameters(self):
        """Test initialization with explicit parameters"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf = Mock()
            mock_sf.sf_instance = "custom.my.salesforce.com"
            mock_sf_class.return_value = mock_sf
            
            provider = SalesforceProvider(
                username='custom@example.com',
                password='custompass',
                security_token='customtoken',
                domain='test',
            )
            
            assert provider.username == 'custom@example.com'
            assert provider.domain == 'test'
            assert provider.sf is not None
    
    def test_init_handles_import_error(self):
        """Test initialization handles missing simple_salesforce"""
        with patch.dict(os.environ, {
            'SALESFORCE_USERNAME': 'test@example.com',
            'SALESFORCE_PASSWORD': 'testpass',
            'SALESFORCE_SECURITY_TOKEN': 'testtoken',
        }):
            with patch('janus.integrations.salesforce_provider.Salesforce', side_effect=ImportError):
                provider = SalesforceProvider()
                
                assert provider.sf is None
                assert provider.enabled is False


class TestSalesforceProviderContact:
    """Test SalesforceProvider contact operations"""
    
    def test_get_contact_success(self, mock_salesforce, mock_contact_query_result):
        """Test successful contact search"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = mock_contact_query_result
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            contact = provider.get_contact('Jane Smith')
            
            assert contact is not None
            assert contact['name'] == 'Jane Smith'
            assert contact['title'] == 'Director of Engineering'
            assert contact['email'] == 'jane.smith@acme.com'
            assert contact['account_name'] == 'Acme Corp'
            assert 'url' in contact
            assert '/lightning/r/Contact/' in contact['url']
    
    def test_get_contact_not_found(self, mock_salesforce):
        """Test contact search with no results"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = {'totalSize': 0, 'records': []}
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            contact = provider.get_contact('Nonexistent Person')
            
            assert contact is None
    
    def test_get_contact_disabled(self):
        """Test get_contact when provider is disabled"""
        provider = SalesforceProvider()
        
        contact = provider.get_contact('Jane Smith')
        
        assert contact is None
    
    def test_get_contact_by_id_success(self, mock_salesforce):
        """Test get contact by ID"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            contact = provider.get_contact_by_id('003XXXXXXXXXXXX')
            
            assert contact is not None
            assert contact['id'] == '003XXXXXXXXXXXX'
            assert contact['name'] == 'John Doe'


class TestSalesforceProviderOpportunity:
    """Test SalesforceProvider opportunity operations"""
    
    def test_get_opportunity_success(self, mock_salesforce):
        """Test get opportunity by ID"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            opportunity = provider.get_opportunity('006XXXXXXXXXXXX')
            
            assert opportunity is not None
            assert opportunity['id'] == '006XXXXXXXXXXXX'
            assert opportunity['name'] == 'Acme Corp - Q4 Deal'
            assert opportunity['stage'] == 'Negotiation'
            assert opportunity['amount'] == 150000
            assert 'url' in opportunity
            assert '/lightning/r/Opportunity/' in opportunity['url']
    
    def test_search_opportunities_success(self, mock_salesforce, mock_opportunity_query_result):
        """Test search opportunities by account"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = mock_opportunity_query_result
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            opportunities = provider.search_opportunities('Acme Corp')
            
            assert len(opportunities) == 2
            assert opportunities[0]['name'] == 'Acme - License Renewal'
            assert opportunities[1]['name'] == 'Acme - Expansion Deal'
            assert opportunities[0]['account_name'] == 'Acme Corp'


class TestSalesforceProviderAccount:
    """Test SalesforceProvider account operations"""
    
    def test_get_account_success(self, mock_salesforce):
        """Test get account by name"""
        account_query_result = {
            'totalSize': 1,
            'records': [
                {
                    'Id': '001XXXXXXXXXXXX',
                    'Name': 'Acme Corporation',
                    'Industry': 'Technology',
                    'Website': 'https://acme.com',
                    'Phone': '+1-555-1000',
                    'BillingCity': 'San Francisco',
                    'BillingCountry': 'USA',
                    'Type': 'Customer',
                }
            ]
        }
        
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = account_query_result
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            account = provider.get_account('Acme')
            
            assert account is not None
            assert account['name'] == 'Acme Corporation'
            assert account['industry'] == 'Technology'
            assert account['website'] == 'https://acme.com'
            assert 'url' in account


class TestSalesforceProviderURL:
    """Test URL generation"""
    
    def test_generate_contact_url(self, mock_salesforce):
        """Test contact URL generation"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            
            url = provider.generate_contact_url('003XXXXXXXXXXXX')
            
            assert url == "https://mycompany.my.salesforce.com/lightning/r/Contact/003XXXXXXXXXXXX/view"
    
    def test_generate_opportunity_url(self, mock_salesforce):
        """Test opportunity URL generation"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            
            url = provider.generate_opportunity_url('006XXXXXXXXXXXX')
            
            assert url == "https://mycompany.my.salesforce.com/lightning/r/Opportunity/006XXXXXXXXXXXX/view"


class TestSalesforceProviderManagement:
    """Test provider enable/disable"""
    
    def test_enable_with_connection(self, mock_salesforce):
        """Test enable with valid connection"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            assert provider.enabled is True
    
    def test_enable_without_connection(self):
        """Test enable without connection"""
        provider = SalesforceProvider()
        provider.enable()
        
        assert provider.enabled is False
    
    def test_disable(self, mock_salesforce):
        """Test disable provider"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            assert provider.enabled is True
            
            provider.disable()
            assert provider.enabled is False
    
    def test_get_context(self, mock_salesforce):
        """Test get context"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            context = provider.get_context()
            
            assert context['enabled'] is True
            assert context['connected'] is True
            assert context['instance_url'] == "https://mycompany.my.salesforce.com"


class TestSalesforceProviderSecurity:
    """Test security features - SOQL injection prevention"""
    
    def test_escape_soql_string_basic(self):
        """Test basic string sanitization"""
        escaped = SalesforceProvider._escape_soql_string("John Doe")
        assert escaped == "John Doe"
    
    def test_escape_soql_string_with_quotes(self):
        """Test removal of single quotes (whitelist approach)"""
        escaped = SalesforceProvider._escape_soql_string("O'Brien")
        # Quotes are removed by whitelist, not escaped
        assert escaped == "OBrien"
        assert "'" not in escaped
    
    def test_escape_soql_string_with_backslash(self):
        """Test removal of backslashes (whitelist approach)"""
        escaped = SalesforceProvider._escape_soql_string("Test\\Name")
        # Backslashes are removed by whitelist
        assert escaped == "TestName"
        assert "\\" not in escaped
    
    def test_escape_soql_string_removes_dangerous_chars(self):
        """Test removal of potentially dangerous characters"""
        # Characters like ; % < > ' should be removed
        escaped = SalesforceProvider._escape_soql_string("Test;DROP TABLE")
        assert ";" not in escaped
        assert escaped == "TestDROP TABLE"
    
    def test_escape_soql_string_allows_safe_chars(self):
        """Test that safe characters are preserved"""
        test_string = "john.doe@example.com"
        escaped = SalesforceProvider._escape_soql_string(test_string)
        assert "@" in escaped
        assert "." in escaped
        
        # Test hyphen separately
        test_hyphen = "Mary-Jane"
        escaped_hyphen = SalesforceProvider._escape_soql_string(test_hyphen)
        assert "-" in escaped_hyphen  # Hyphen should be allowed
    
    def test_get_contact_with_injection_attempt(self, mock_salesforce, mock_contact_query_result):
        """Test that SQL injection attempts are neutralized"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = mock_contact_query_result
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            # Attempt injection with quote and OR clause
            malicious_input = "' OR '1'='1"
            contact = provider.get_contact(malicious_input)
            
            # Check that the query was called with sanitized input
            call_args = mock_salesforce.query.call_args
            query = call_args[0][0]
            
            # Quotes and OR should be sanitized out (whitelist approach)
            assert "'" not in query
            # The sanitized version would be "OR11" or similar (no quotes, no =)
    
    def test_search_opportunities_limit_validation(self, mock_salesforce):
        """Test that limit parameter is validated"""
        with patch('janus.integrations.salesforce_provider.Salesforce') as mock_sf_class:
            mock_sf_class.return_value = mock_salesforce
            mock_salesforce.query.return_value = {'totalSize': 0, 'records': []}
            
            provider = SalesforceProvider(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
            )
            provider.enable()
            
            # Test with very large limit
            provider.search_opportunities("Acme", limit=999999)
            
            call_args = mock_salesforce.query.call_args
            query = call_args[0][0]
            
            # Should be capped at 2000 (Salesforce max)
            assert "LIMIT 2000" in query
    
    def test_empty_string_escape(self):
        """Test escaping of empty string"""
        escaped = SalesforceProvider._escape_soql_string("")
        assert escaped == ""
    
    def test_none_value_escape(self):
        """Test escaping of None value"""
        escaped = SalesforceProvider._escape_soql_string(None)
        assert escaped == ""
