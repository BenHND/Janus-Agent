#!/usr/bin/env python3
"""
Manual test for semantic memory functionality (TICKET-MEM-001)
"""
import tempfile
import os
from pathlib import Path

from janus.runtime.core.memory_engine import MemoryEngine, SEMANTIC_MEMORY_AVAILABLE

def main():
    print("=" * 60)
    print("TICKET-MEM-001: Semantic Memory Manual Test")
    print("=" * 60)
    
    # Check if semantic memory is available
    print(f"\nSemantic memory available: {SEMANTIC_MEMORY_AVAILABLE}")
    
    if not SEMANTIC_MEMORY_AVAILABLE:
        print("❌ Semantic memory dependencies not installed")
        print("Install with: pip install chromadb sentence-transformers")
        return
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    print(f"\nUsing temporary database: {db_path}")
    
    try:
        # Initialize engine with semantic memory
        print("\n1. Initializing MemoryEngine with semantic memory...")
        engine = MemoryEngine(db_path, enable_semantic_memory=True)
        print(f"   ✓ Semantic memory enabled: {engine._semantic_memory_enabled}")
        
        # Test acceptance criteria
        print("\n2. Testing acceptance criteria...")
        print("   Simulating: User opens 'report.pdf'")
        engine.record_action("open_file", {
            "file_path": "/Users/alice/documents/report.pdf"
        })
        print("   ✓ Action recorded")
        
        # Add some other actions
        print("\n3. Recording additional actions...")
        engine.record_action("open_app", {"app_name": "Safari"})
        engine.record_action("copy", {"content": "some text"})
        engine.record_action("open_file", {"file_path": "/Users/alice/budget_2024.xlsx"})
        print("   ✓ Additional actions recorded")
        
        # Test semantic search
        print("\n4. Testing semantic search...")
        results = engine.search_semantic("PDF document", limit=3)
        print(f"   Query: 'PDF document'")
        print(f"   Results: {len(results)}")
        for i, result in enumerate(results):
            print(f"      {i+1}. {result['description'][:60]}...")
        
        # Test reference resolution with French query
        print("\n5. Testing reference resolution (French)...")
        print("   Query: 'le PDF qu'on a vu tout à l'heure'")
        result = engine.resolve_reference("le PDF qu'on a vu tout à l'heure")
        print(f"   Result: {result}")
        if result and "report.pdf" in str(result).lower():
            print("   ✅ PASS: Found report.pdf!")
        else:
            print("   ⚠️  FAIL: Did not find report.pdf")
        
        # Test reference resolution with English query
        print("\n6. Testing reference resolution (English)...")
        print("   Query: 'the PDF we saw earlier'")
        result = engine.resolve_reference("the PDF we saw earlier")
        print(f"   Result: {result}")
        if result and "report.pdf" in str(result).lower():
            print("   ✅ PASS: Found report.pdf!")
        else:
            print("   ⚠️  FAIL: Did not find report.pdf")
        
        # Test exact keyword still works
        print("\n7. Testing exact keyword resolution...")
        engine.record_action("copy", {"content": "exact match test"})
        result = engine.resolve_reference("it")
        print(f"   Query: 'it'")
        print(f"   Result: {result}")
        if result == "exact match test":
            print("   ✅ PASS: Exact keyword resolution works!")
        else:
            print("   ⚠️  FAIL: Exact keyword resolution failed")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path)
        print(f"\n🧹 Cleaned up temporary files")

if __name__ == "__main__":
    main()
