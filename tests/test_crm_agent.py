"""
Tests for CRMAgent - Salesforce CRM operations
Part of TICKET-BIZ-001: Salesforce Native Connector (CRM)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from janus.capabilities.agents.base_agent import AgentExecutionError
from janus.capabilities.agents.crm_agent import CRMAgent


@pytest.fixture
def mock_salesforce_provider():
    """Mock SalesforceProvider"""
    provider = Mock()
    provider.sf = Mock()  # Simulate connection
    provider.enabled = True
    provider.instance_url = "https://mycompany.my.salesforce.com"
    
    # Mock contact data
    provider.get_contact.return_value = {
        'id': '003XXXXXXXXXXXX',
        'name': 'Jane Smith',
        'title': 'VP of Sales',
        'email': 'jane.smith@acme.com',
        'phone': '+1-555-0200',
        'account_name': 'Acme Corp',
        'url': 'https://mycompany.my.salesforce.com/lightning/r/Contact/003XXXXXXXXXXXX/view',
    }
    
    provider.get_contact_by_id.return_value = {
        'id': '003XXXXXXXXXXXX',
        'name': 'Jane Smith',
        'title': 'VP of Sales',
        'email': 'jane.smith@acme.com',
    }
    
    # Mock opportunity data
    provider.get_opportunity.return_value = {
        'id': '006XXXXXXXXXXXX',
        'name': 'Acme - Q4 Deal',
        'stage': 'Negotiation',
        'amount': 150000,
        'close_date': '2024-12-31',
        'probability': 75,
        'url': 'https://mycompany.my.salesforce.com/lightning/r/Opportunity/006XXXXXXXXXXXX/view',
    }
    
    # Mock opportunities search
    provider.search_opportunities.return_value = [
        {
            'id': '006XXXXXXXXXXXX1',
            'name': 'Acme - License Renewal',
            'stage': 'Closed Won',
            'amount': 200000,
        },
        {
            'id': '006XXXXXXXXXXXX2',
            'name': 'Acme - Expansion',
            'stage': 'Proposal',
            'amount': 350000,
        },
    ]
    
    # Mock account data
    provider.get_account.return_value = {
        'id': '001XXXXXXXXXXXX',
        'name': 'Acme Corporation',
        'industry': 'Technology',
        'website': 'https://acme.com',
    }
    
    # Mock URL generation
    provider.generate_contact_url.return_value = 'https://mycompany.my.salesforce.com/lightning/r/Contact/003XXXXXXXXXXXX/view'
    provider.generate_opportunity_url.return_value = 'https://mycompany.my.salesforce.com/lightning/r/Opportunity/006XXXXXXXXXXXX/view'
    
    return provider


@pytest.fixture
def crm_agent(mock_salesforce_provider):
    """Create CRM agent with mocked provider"""
    with patch('janus.agents.crm_agent.SalesforceProvider') as mock_provider_class:
        mock_provider_class.return_value = mock_salesforce_provider
        agent = CRMAgent(
            username='test@example.com',
            password='testpass',
            security_token='testtoken',
        )
        return agent


class TestCRMAgentInit:
    """Test CRM Agent initialization"""
    
    def test_init_with_credentials(self, mock_salesforce_provider):
        """Test initialization with credentials"""
        with patch('janus.agents.crm_agent.SalesforceProvider') as mock_provider_class:
            mock_provider_class.return_value = mock_salesforce_provider
            
            agent = CRMAgent(
                username='test@example.com',
                password='testpass',
                security_token='testtoken',
                domain='login',
            )
            
            assert agent.salesforce is not None
            assert agent.salesforce.enabled is True
    
    def test_init_without_credentials(self):
        """Test initialization without credentials"""
        with patch('janus.agents.crm_agent.SalesforceProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.sf = None
            mock_provider.enabled = False
            mock_provider_class.return_value = mock_provider
            
            agent = CRMAgent()
            
            assert agent.salesforce is not None
            assert agent.salesforce.enabled is False


class TestCRMAgentSearchContact:
    """Test search_contact action"""
    
    @pytest.mark.asyncio
    async def test_search_contact_success(self, crm_agent):
        """Test successful contact search"""
        result = await crm_agent.execute(
            action='search_contact',
            args={'name': 'Jane Smith'},
        )
        
        assert result['success'] is True
        assert result['contact'] is not None
        assert result['contact']['name'] == 'Jane Smith'
        assert result['contact']['title'] == 'VP of Sales'
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_search_contact_not_found(self, crm_agent, mock_salesforce_provider):
        """Test contact search with no results"""
        mock_salesforce_provider.get_contact.return_value = None
        
        result = await crm_agent.execute(
            action='search_contact',
            args={'name': 'Nonexistent Person'},
        )
        
        assert result['success'] is False
        assert result['contact'] is None
        assert 'No contact found' in result['message']
    
    @pytest.mark.asyncio
    async def test_search_contact_missing_name(self, crm_agent):
        """Test search_contact without name argument"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='search_contact',
                args={},
            )
        
        assert exc_info.value.module == 'crm'
        assert exc_info.value.action == 'search_contact'
        assert 'Missing required argument: name' in exc_info.value.details


class TestCRMAgentGetContact:
    """Test get_contact action"""
    
    @pytest.mark.asyncio
    async def test_get_contact_success(self, crm_agent):
        """Test get contact by ID"""
        result = await crm_agent.execute(
            action='get_contact',
            args={'contact_id': '003XXXXXXXXXXXX'},
        )
        
        assert result['success'] is True
        assert result['contact'] is not None
        assert result['contact']['id'] == '003XXXXXXXXXXXX'
    
    @pytest.mark.asyncio
    async def test_get_contact_missing_id(self, crm_agent):
        """Test get_contact without contact_id"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='get_contact',
                args={},
            )
        
        assert 'Missing required argument: contact_id' in exc_info.value.details


class TestCRMAgentGetOpportunity:
    """Test get_opportunity action"""
    
    @pytest.mark.asyncio
    async def test_get_opportunity_success(self, crm_agent):
        """Test get opportunity by ID"""
        result = await crm_agent.execute(
            action='get_opportunity',
            args={'opportunity_id': '006XXXXXXXXXXXX'},
        )
        
        assert result['success'] is True
        assert result['opportunity'] is not None
        assert result['opportunity']['id'] == '006XXXXXXXXXXXX'
        assert result['opportunity']['name'] == 'Acme - Q4 Deal'
    
    @pytest.mark.asyncio
    async def test_get_opportunity_missing_id(self, crm_agent):
        """Test get_opportunity without opportunity_id"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='get_opportunity',
                args={},
            )
        
        assert 'Missing required argument: opportunity_id' in exc_info.value.details


class TestCRMAgentSearchOpportunities:
    """Test search_opportunities action"""
    
    @pytest.mark.asyncio
    async def test_search_opportunities_success(self, crm_agent):
        """Test search opportunities by account"""
        result = await crm_agent.execute(
            action='search_opportunities',
            args={'account_name': 'Acme Corp'},
        )
        
        assert result['success'] is True
        assert len(result['opportunities']) == 2
        assert result['count'] == 2
        assert result['opportunities'][0]['name'] == 'Acme - License Renewal'
    
    @pytest.mark.asyncio
    async def test_search_opportunities_with_limit(self, crm_agent, mock_salesforce_provider):
        """Test search opportunities with custom limit"""
        await crm_agent.execute(
            action='search_opportunities',
            args={'account_name': 'Acme Corp', 'limit': 5},
        )
        
        mock_salesforce_provider.search_opportunities.assert_called_once_with('Acme Corp', limit=5)
    
    @pytest.mark.asyncio
    async def test_search_opportunities_missing_account(self, crm_agent):
        """Test search_opportunities without account_name"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='search_opportunities',
                args={},
            )
        
        assert 'Missing required argument: account_name' in exc_info.value.details


class TestCRMAgentGetAccount:
    """Test get_account action"""
    
    @pytest.mark.asyncio
    async def test_get_account_success(self, crm_agent):
        """Test get account by name"""
        result = await crm_agent.execute(
            action='get_account',
            args={'account_name': 'Acme Corp'},
        )
        
        assert result['success'] is True
        assert result['account'] is not None
        assert result['account']['name'] == 'Acme Corporation'
    
    @pytest.mark.asyncio
    async def test_get_account_missing_name(self, crm_agent):
        """Test get_account without account_name"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='get_account',
                args={},
            )
        
        assert 'Missing required argument: account_name' in exc_info.value.details


class TestCRMAgentGenerateURLs:
    """Test URL generation actions"""
    
    @pytest.mark.asyncio
    async def test_generate_contact_url(self, crm_agent):
        """Test generate contact URL"""
        result = await crm_agent.execute(
            action='generate_contact_url',
            args={'contact_id': '003XXXXXXXXXXXX'},
        )
        
        assert result['success'] is True
        assert 'url' in result
        assert '/lightning/r/Contact/' in result['url']
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_generate_opportunity_url(self, crm_agent):
        """Test generate opportunity URL"""
        result = await crm_agent.execute(
            action='generate_opportunity_url',
            args={'opportunity_id': '006XXXXXXXXXXXX'},
        )
        
        assert result['success'] is True
        assert 'url' in result
        assert '/lightning/r/Opportunity/' in result['url']
    
    @pytest.mark.asyncio
    async def test_generate_contact_url_missing_id(self, crm_agent):
        """Test generate_contact_url without ID"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='generate_contact_url',
                args={},
            )
        
        assert 'Missing required argument: contact_id' in exc_info.value.details


class TestCRMAgentErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_unsupported_action(self, crm_agent):
        """Test unsupported action"""
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='unsupported_action',
                args={},
            )
        
        assert exc_info.value.module == 'crm'
        assert exc_info.value.action == 'unsupported_action'
        assert 'Unsupported action' in exc_info.value.details
        assert exc_info.value.recoverable is False
    
    @pytest.mark.asyncio
    async def test_provider_exception(self, crm_agent, mock_salesforce_provider):
        """Test handling of provider exceptions"""
        mock_salesforce_provider.get_contact.side_effect = Exception("Connection error")
        
        with pytest.raises(AgentExecutionError) as exc_info:
            await crm_agent.execute(
                action='search_contact',
                args={'name': 'Jane Smith'},
            )
        
        assert exc_info.value.module == 'crm'
        assert exc_info.value.recoverable is True
        assert 'Connection error' in exc_info.value.details
