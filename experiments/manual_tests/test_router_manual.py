#!/usr/bin/env python3
"""
Manual test for TICKET-ROUTER-001: Zero-shot classification
Demonstrates the acceptance criteria: "Peux-tu check mes mails" should be classified as ACTION
"""

from janus.ai.reasoning.semantic_router import SemanticRouter, EMBEDDINGS_AVAILABLE

def main():
    print("=" * 70)
    print("TICKET-ROUTER-001: Manual Test for Zero-Shot Classification")
    print("=" * 70)
    
    print(f"\n✓ Embeddings available: {EMBEDDINGS_AVAILABLE}")
    
    # Initialize router without LLM (will use embeddings if available, else keywords)
    router = SemanticRouter(reasoner=None, enable_embeddings=True)
    
    print(f"✓ Router initialized")
    print(f"  - Using embeddings: {router._use_embeddings}")
    print(f"  - Using LLM: {router.use_llm}")
    
    # Test acceptance criteria
    print("\n" + "=" * 70)
    print("ACCEPTANCE CRITERIA TEST")
    print("=" * 70)
    
    test_phrase = "Peux-tu check mes mails"
    print(f"\nInput: '{test_phrase}'")
    print("Expected: ACTION (franglais, word 'check' absent from keyword lists)")
    
    result = router.classify_intent(test_phrase)
    print(f"Result: {result}")
    
    if result == "ACTION":
        print("✅ PASS: Correctly classified as ACTION!")
    else:
        print(f"❌ FAIL: Expected ACTION, got {result}")
        if not EMBEDDINGS_AVAILABLE:
            print("   Note: This test requires sentence-transformers to be installed")
            print("   Install with: pip install sentence-transformers chromadb")
    
    # Additional test cases
    print("\n" + "=" * 70)
    print("ADDITIONAL TEST CASES")
    print("=" * 70)
    
    test_cases = [
        ("Merci beaucoup", "NOISE"),
        ("Qui est le président", "CHAT"),
        ("Ouvre Chrome", "ACTION"),
        ("Check my emails", "ACTION"),
        ("Peux-tu ouvrir mon browser", "ACTION"),
    ]
    
    for text, expected in test_cases:
        result = router.classify_intent(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' → {result} (expected: {expected})")
    
    print("\n" + "=" * 70)
    print("Classification Method Used:")
    if router._use_embeddings:
        print("  → Embedding-based (zero-shot semantic classification)")
    elif router.use_llm:
        print("  → LLM-based (JSON mode)")
    else:
        print("  → Keyword-based (fallback)")
    print("=" * 70)

if __name__ == "__main__":
    main()
