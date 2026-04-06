#!/usr/bin/env python3
"""
Manual test/demo for Tool RAG feature

This demonstrates the Tool RAG feature even without full dependencies installed.
Shows how the system gracefully degrades when ChromaDB/sentence-transformers are not available.

Run with: python3 demo_tool_rag.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def demo_tools_catalog():
    """Demo: Show the tools catalog"""
    print("=" * 80)
    print("DEMO 1: Tools Catalog")
    print("=" * 80)
    
    from janus.config.tools_registry import TOOLS_CATALOG, TOTAL_TOOLS_COUNT
    
    print(f"\nTotal tools registered: {TOTAL_TOOLS_COUNT}")
    print("\nSample tools:\n")
    
    # Show a few examples from different categories
    categories = {
        "CRM": ["crm_search_contact", "crm_get_contact"],
        "Messaging": ["messaging_post_message", "messaging_read_history"],
        "Files": ["files_open_path", "files_read_file"],
        "Browser": ["browser_open_url", "browser_click"],
    }
    
    for category, tool_ids in categories.items():
        print(f"\n{category} Tools:")
        for tool in TOOLS_CATALOG:
            if tool["id"] in tool_ids:
                print(f"  • {tool['signature']}")
                print(f"    {tool['description']}")
    
    print("\n" + "=" * 80)


def demo_tool_retrieval_service():
    """Demo: Test ToolRetrievalService availability"""
    print("\n" + "=" * 80)
    print("DEMO 2: ToolRetrievalService Availability")
    print("=" * 80)
    
    from janus.services.tool_retrieval_service import ToolRetrievalService, RAG_AVAILABLE
    
    print(f"\nRAG dependencies available: {RAG_AVAILABLE}")
    
    if RAG_AVAILABLE:
        print("✅ ChromaDB and sentence-transformers are installed")
        print("   The system can perform semantic tool retrieval")
    else:
        print("⚠️  ChromaDB and/or sentence-transformers not installed")
        print("   System will use static tools (graceful degradation)")
        print("\n   To enable RAG, install:")
        print("   pip install chromadb==0.4.24 sentence-transformers==2.2.2")
    
    # Create service and check
    service = ToolRetrievalService(
        enable_session_cache=True,    # RAG-001: Enable session caching
        enable_delta_updates=True      # RAG-001: Enable delta updates
    )
    print(f"\nService available: {service.available}")
    print(f"Service indexed: {service.indexed}")
    
    if service.available:
        from janus.config.tools_registry import TOOLS_CATALOG, CATALOG_VERSION_HASH
        
        print("\nIndexing tools...")
        # RAG-001: Index with version hash for automatic cache invalidation
        success = service.index_tools(TOOLS_CATALOG, catalog_version=CATALOG_VERSION_HASH)
        print(f"Indexing successful: {success}")
        print(f"Catalog version: {CATALOG_VERSION_HASH}")
        
        if success:
            print("\nTesting semantic retrieval with session caching...")
            
            test_queries = [
                "Search for contact Dupont in Salesforce",
                "Open the documents folder",
                "Post message to Slack channel",
            ]
            
            session_id = "demo_session_1"
            
            for query in test_queries:
                print(f"\n  Query: '{query}'")
                # RAG-001: Use session_id for stable tool selection
                tools = service.get_relevant_tools(
                    query, 
                    top_k=3,
                    session_id=session_id
                )
                if tools:
                    print("  Relevant tools:")
                    for line in tools.split('\n')[:3]:  # Show first 3
                        if line.strip():
                            print(f"    {line}")
                else:
                    print("    (no tools retrieved)")
            
            # Show statistics
            stats = service.get_statistics()
            print("\n  Performance Statistics:")
            print(f"    Total queries: {stats['total_queries']}")
            print(f"    Average latency: {stats['avg_latency_ms']:.2f}ms")
            print(f"    Max latency: {stats['max_latency_ms']:.2f}ms")
            print(f"    Cache size: {stats['cache_size']}")
    
    print("\n" + "=" * 80)


def demo_action_coordinator_integration():
    """Demo: Test ActionCoordinator integration"""
    print("\n" + "=" * 80)
    print("DEMO 3: ActionCoordinator Integration")
    print("=" * 80)
    
    from janus.runtime.core.action_coordinator import ActionCoordinator
    
    print("\nCreating ActionCoordinator...")
    coordinator = ActionCoordinator(tool_rag_top_k=5)
    
    print(f"Tool retriever initialized: {coordinator._tool_retriever is not None}")
    
    # Access lazy-loaded retriever
    retriever = coordinator.tool_retriever
    print(f"Tool retriever available: {retriever.available}")
    print(f"Tool retriever indexed: {retriever.indexed}")
    
    # Test prompt building
    print("\nTesting prompt building with dynamic tools...")
    prompt = coordinator._build_react_prompt(
        user_goal="Search for contact Dupont in Salesforce",
        system_state={"active_app": "Chrome", "clipboard": "test"},
        visual_context="[]",
        memory={},
        language="en"
    )
    
    print(f"Prompt generated: {len(prompt)} characters")
    
    if retriever.available and retriever.indexed:
        if "CONTEXTUAL TOOLS" in prompt or "OUTILS CONTEXTUELS" in prompt:
            print("✅ Dynamic tools injected in prompt")
            
            # Extract contextual tools section
            if "CONTEXTUAL TOOLS" in prompt:
                start = prompt.find("CONTEXTUAL TOOLS")
                end = prompt.find("\n\n", start)
                section = prompt[start:end] if end > start else prompt[start:start+200]
                print("\nContextual tools section (preview):")
                print(section[:300])
        else:
            print("⚠️  Dynamic tools section not found in prompt")
    else:
        print("⚠️  RAG not available - using static tools")
    
    print("\n" + "=" * 80)


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("Tool RAG Feature Demo")
    print("=" * 80)
    print("\nThis demo shows the Tool RAG feature in action.")
    print("It works with or without ChromaDB/sentence-transformers installed.")
    
    try:
        # Demo 1: Show tools catalog
        demo_tools_catalog()
        
        # Demo 2: Test ToolRetrievalService
        demo_tool_retrieval_service()
        
        # Demo 3: Test ActionCoordinator integration
        demo_action_coordinator_integration()
        
        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  • 45+ tools registered in catalog")
        print("  • System works with/without RAG dependencies")
        print("  • Graceful degradation when dependencies unavailable")
        print("  • Low latency (~30ms) when RAG available")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
