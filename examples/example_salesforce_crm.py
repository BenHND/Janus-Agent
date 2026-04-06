#!/usr/bin/env python3
"""
Example: Salesforce CRM Integration
TICKET-BIZ-001: Demonstrate Salesforce Native Connector usage

This example shows how to:
1. Initialize the Salesforce provider
2. Search for contacts
3. Get opportunity information
4. Generate URLs for browser navigation

Prerequisites:
- Install: pip install 'janus[salesforce]'
- Set environment variables in .env:
  - SALESFORCE_USERNAME
  - SALESFORCE_PASSWORD
  - SALESFORCE_SECURITY_TOKEN
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.integrations.salesforce_provider import SalesforceProvider
from janus.capabilities.agents.crm_agent import CRMAgent


async def example_salesforce_provider():
    """Example 1: Using SalesforceProvider directly"""
    print("\n" + "="*80)
    print("Example 1: SalesforceProvider - Direct API Access")
    print("="*80)
    
    # Initialize provider (credentials from environment)
    provider = SalesforceProvider()
    
    if not provider.sf:
        print("❌ Salesforce connection not available.")
        print("   Set SALESFORCE_USERNAME, SALESFORCE_PASSWORD, and SALESFORCE_SECURITY_TOKEN")
        return
    
    # Enable the provider
    provider.enable()
    
    # Get context
    context = provider.get_context()
    print(f"\n✓ Connected to: {context['instance_url']}")
    
    # Example 1.1: Search for a contact
    print("\n--- Search Contact ---")
    contact = provider.get_contact("Smith")
    
    if contact:
        print(f"✓ Found contact:")
        print(f"  Name: {contact['name']}")
        print(f"  Title: {contact['title']}")
        print(f"  Email: {contact['email']}")
        print(f"  Account: {contact['account_name']}")
        print(f"  URL: {contact['url']}")
    else:
        print("❌ No contact found")
    
    # Example 1.2: Search opportunities
    print("\n--- Search Opportunities ---")
    opportunities = provider.search_opportunities("Acme", limit=5)
    
    print(f"✓ Found {len(opportunities)} opportunities:")
    for opp in opportunities:
        print(f"  - {opp['name']}: {opp['stage']} (${opp['amount']:,.0f})")
    
    # Example 1.3: Get account information
    print("\n--- Get Account ---")
    account = provider.get_account("Acme")
    
    if account:
        print(f"✓ Account: {account['name']}")
        print(f"  Industry: {account['industry']}")
        print(f"  Website: {account['website']}")


async def example_crm_agent():
    """Example 2: Using CRMAgent with V3 architecture"""
    print("\n" + "="*80)
    print("Example 2: CRMAgent - V3 Atomic Operations")
    print("="*80)
    
    # Initialize CRM agent
    agent = CRMAgent()
    
    if not agent.salesforce.sf:
        print("❌ Salesforce connection not available.")
        return
    
    # Example 2.1: Search contact action
    print("\n--- Action: search_contact ---")
    result = await agent.execute(
        action='search_contact',
        args={'name': 'Smith'}
    )
    
    if result['success']:
        contact = result['contact']
        print(f"✓ {result['message']}")
        print(f"  Title: {contact['title']}")
        print(f"  Email: {contact['email']}")
    else:
        print(f"❌ {result['message']}")
    
    # Example 2.2: Search opportunities action
    print("\n--- Action: search_opportunities ---")
    result = await agent.execute(
        action='search_opportunities',
        args={'account_name': 'Acme', 'limit': 3}
    )
    
    print(f"✓ Found {result['count']} opportunities")
    for opp in result['opportunities'][:3]:
        print(f"  - {opp['name']}: {opp['stage']}")
    
    # Example 2.3: Generate URL for browser navigation
    if result['opportunities']:
        opp_id = result['opportunities'][0]['id']
        print(f"\n--- Action: generate_opportunity_url ---")
        url_result = await agent.execute(
            action='generate_opportunity_url',
            args={'opportunity_id': opp_id}
        )
        print(f"✓ {url_result['message']}")
        print(f"  (Open this URL in browser to edit the opportunity)")


async def example_hybrid_mode():
    """Example 3: Hybrid mode - API for reads, URLs for writes"""
    print("\n" + "="*80)
    print("Example 3: Hybrid Mode - Fast Reads, Safe Writes")
    print("="*80)
    
    agent = CRMAgent()
    
    if not agent.salesforce.sf:
        print("❌ Salesforce connection not available.")
        return
    
    # Read operation: Fast API call (< 3 seconds)
    print("\n--- Read: Get contact info (API) ---")
    import time
    start = time.time()
    
    result = await agent.execute(
        action='search_contact',
        args={'name': 'Smith'}
    )
    
    elapsed = time.time() - start
    print(f"✓ Retrieved contact in {elapsed:.2f}s")
    
    if result['success']:
        contact = result['contact']
        contact_id = contact['id']
        
        # Write operation: Generate URL for browser (safe)
        print("\n--- Write: Edit contact (Browser URL) ---")
        url_result = await agent.execute(
            action='generate_contact_url',
            args={'contact_id': contact_id}
        )
        
        print("✓ Generated Salesforce URL for editing:")
        print(f"  {url_result['url']}")
        print("\n  → Open in browser: User or agent can edit safely")
        print("  → No risk of accidental data corruption")
        print("  → User maintains full control")


async def main():
    """Run all examples"""
    print("\n🚀 Janus - Salesforce CRM Integration Examples")
    print("TICKET-BIZ-001: Native Connector Demo")
    
    # Check for credentials
    has_credentials = all([
        os.environ.get('SALESFORCE_USERNAME'),
        os.environ.get('SALESFORCE_PASSWORD'),
        os.environ.get('SALESFORCE_SECURITY_TOKEN'),
    ])
    
    if not has_credentials:
        print("\n⚠️  Salesforce credentials not configured!")
        print("\nTo run these examples:")
        print("1. Copy .env.example to .env")
        print("2. Fill in your Salesforce credentials:")
        print("   - SALESFORCE_USERNAME=your-email@company.com")
        print("   - SALESFORCE_PASSWORD=your-password")
        print("   - SALESFORCE_SECURITY_TOKEN=your-token")
        print("3. Get security token:")
        print("   Settings → My Personal Information → Reset My Security Token")
        print("\n4. Install dependencies:")
        print("   pip install 'janus[salesforce]'")
        print("\nRunning examples with mock data...\n")
    
    try:
        # Run examples
        await example_salesforce_provider()
        await example_crm_agent()
        await example_hybrid_mode()
        
        print("\n" + "="*80)
        print("✓ Examples completed successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables")
    
    # Run examples
    asyncio.run(main())
