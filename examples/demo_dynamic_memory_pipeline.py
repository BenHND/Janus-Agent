#!/usr/bin/env python3
"""
TICKET-ARCH-005 Demonstration: Dynamic Memory Pipeline

This script demonstrates the new dynamic memory feature that enables
variable passing between actions and applications.

Example scenario: "Take the CEO name from LinkedIn and put it in Salesforce"
"""

from janus.memory.session_context import SessionContext

def demonstrate_memory_pipeline():
    """Demonstrate the dynamic memory pipeline"""
    
    print("=" * 70)
    print("TICKET-ARCH-005: Dynamic Memory Pipeline Demonstration")
    print("=" * 70)
    print()
    
    # Initialize session context
    context = SessionContext()
    print("✅ SessionContext initialized")
    print()
    
    # Scenario: Extract data from LinkedIn
    print("📍 Scenario: Multi-Application Data Transfer")
    print("-" * 70)
    print("Step 1: Extract CEO name from LinkedIn")
    print()
    
    # Agent extracts data and saves to memory
    context.save_to_memory("CEO_name", "John Smith")
    context.save_to_memory("CEO_title", "Chief Executive Officer")
    context.save_to_memory("company", "Acme Corp")
    
    print("  Agent extracts data:")
    print("    • CEO Name: John Smith")
    print("    • CEO Title: Chief Executive Officer")
    print("    • Company: Acme Corp")
    print()
    print("  ✅ Data saved to memory")
    print()
    
    # Show memory state
    print("Step 2: Memory state (available to all subsequent actions)")
    print()
    all_memory = context.get_all_memory()
    print(f"  Current memory: {all_memory}")
    print()
    
    # Switch to Salesforce (simulated)
    print("Step 3: Switch to Salesforce")
    print()
    print("  Agent opens Salesforce contact form...")
    print()
    
    # Get memory for ReAct loop
    print("Step 4: Memory automatically injected into ReAct prompt")
    print()
    loop_context = context.get_context_for_chaining()
    memory_data = loop_context.get("memory", {})
    
    print("  ReAct prompt receives:")
    print("  **Mémoire (données mémorisées)** :")
    print("  {")
    for key, value in memory_data.items():
        print(f'    "{key}": "{value}"')
    print("  }")
    print()
    
    # Retrieve specific value
    print("Step 5: Agent uses stored data to fill form")
    print()
    ceo_name = context.get_from_memory("CEO_name")
    ceo_title = context.get_from_memory("CEO_title")
    company = context.get_from_memory("company")
    
    print(f"  Filling 'Name' field with: {ceo_name}")
    print(f"  Filling 'Title' field with: {ceo_title}")
    print(f"  Filling 'Company' field with: {company}")
    print()
    
    print("  ✅ Data successfully transferred from LinkedIn to Salesforce!")
    print()
    
    # Show statistics
    print("Step 6: Session statistics")
    print()
    stats = context.get_statistics()
    print(f"  Total actions: {stats['total_actions']}")
    print(f"  Memory items: {stats['dynamic_memory_items']}")
    print()
    
    # Demonstrate memory types
    print("-" * 70)
    print("Additional Feature: Multiple data types supported")
    print()
    
    context.save_to_memory("employee_count", 150)
    context.save_to_memory("annual_revenue", 10000000.50)
    context.save_to_memory("is_public", True)
    context.save_to_memory("departments", ["Sales", "Engineering", "Marketing"])
    
    print("  Stored various types:")
    print(f"    • String: {context.get_from_memory('CEO_name')}")
    print(f"    • Integer: {context.get_from_memory('employee_count')}")
    print(f"    • Float: ${context.get_from_memory('annual_revenue'):,.2f}")
    print(f"    • Boolean: {context.get_from_memory('is_public')}")
    print(f"    • List: {context.get_from_memory('departments')}")
    print()
    
    print("=" * 70)
    print("✅ Demonstration Complete!")
    print("=" * 70)
    print()
    print("Key Benefits:")
    print("  • No OS clipboard dependency")
    print("  • Works across applications")
    print("  • Supports complex data types")
    print("  • Automatic ReAct loop integration")
    print("  • Zero hardcoded site-specific logic")
    print()


if __name__ == "__main__":
    demonstrate_memory_pipeline()
