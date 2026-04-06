"""
Example: Hybrid LLM Optimization (TICKET: P1) - FULL MIGRATION

Demonstrates the MANDATORY dual-model architecture for Ollama:
- Reasoner (Brain): qwen2.5:7b-instruct-q3_k_m (~3.8 GB)
- Reflex (Fast): qwen2.5:1.5b (~1.2 GB)

Total VRAM: ~5 GB (both models loaded)

FULL MIGRATION: Hybrid mode is now MANDATORY for Ollama provider.
No backward compatibility - dual models are always used.

Usage:
    python examples/example_hybrid_llm.py
"""

from janus.ai.llm.unified_client import UnifiedLLMClient
from janus.logging import get_logger

logger = get_logger("example_hybrid_llm")


def main():
    """Demonstrate Ollama hybrid LLM usage (MANDATORY)"""
    
    print("=" * 60)
    print("Hybrid LLM Optimization - FULL MIGRATION")
    print("=" * 60)
    print()
    
    # FULL MIGRATION: Ollama ALWAYS uses hybrid mode
    print("1. Ollama Provider (Hybrid Mode - MANDATORY)")
    print("-" * 60)
    print("⚠️  BREAKING CHANGE: Hybrid mode is now MANDATORY for Ollama")
    print("   No backward compatibility - dual models required")
    print()
    
    try:
        hybrid_client = UnifiedLLMClient(provider="ollama")
        
        print(f"Provider: {hybrid_client.provider}")
        print(f"Reasoner Model: qwen2.5:7b-instruct-q3_k_m")
        print(f"Reflex Model: qwen2.5:1.5b")
        print(f"Status: {'✓ Available' if hybrid_client.available else '✗ Models not installed'}")
    except RuntimeError as e:
        print(f"✗ Error: {e}")
        print()
        print("Install required models with:")
        print("  python scripts/install/install_models.py")
        print()
        print("Or manually:")
        print("  ollama pull qwen2.5:7b-instruct-q3_k_m")
        print("  ollama pull qwen2.5:1.5b")
        hybrid_client = None
    print()
    
    # Example 2: Using smart mode for complex reasoning
    print("2. Smart Mode - Complex Reasoning (Reasoner Model)")
    print("-" * 60)
    
    if hybrid_client and hybrid_client.available:
        complex_prompt = """
        Create a detailed plan to automate the following task:
        1. Open Safari
        2. Navigate to GitHub
        3. Search for "machine learning"
        4. Save the top 3 results to a file
        
        Respond with a JSON plan.
        """
        
        print("Prompt: Complex task planning")
        try:
            response = hybrid_client.generate(
                prompt=complex_prompt,
                mode="smart",  # Uses reasoner model (7B Q3)
                max_tokens=256
            )
            print(f"Response (first 200 chars): {response[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Models not available - see installation instructions above")
    print()
    
    # Example 3: Using fast mode for simple tasks
    print("3. Fast Mode - Simple Task (Reflex Model)")
    print("-" * 60)
    
    if hybrid_client and hybrid_client.available:
        simple_prompt = "Summarize in one sentence: Hello world is the first program."
        
        print("Prompt: Simple summarization")
        try:
            response = hybrid_client.generate(
                prompt=simple_prompt,
                mode="fast",  # Uses reflex model (1.5B)
                max_tokens=50
            )
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Models not available - see installation instructions above")
    print()
    
    # Example 4: Task routing recommendations
    print("4. Task Routing Guidelines")
    print("-" * 60)
    print("Use SMART mode (reasoner) for:")
    print("  • Complex planning and multi-step tasks")
    print("  • Tool selection and code generation")
    print("  • Deep visual analysis")
    print("  • JSON schema generation")
    print()
    print("Use FAST mode (reflex) for:")
    print("  • Simple summarization")
    print("  • Date/time extraction")
    print("  • Small talk and casual chat")
    print("  • Intent classification and routing")
    print("  • Quick yes/no questions")
    print()
    
    # Example 5: Memory benefits
    print("5. Memory Benefits (FULL MIGRATION)")
    print("-" * 60)
    print("❌ OLD Single Model (Q4) - NO LONGER SUPPORTED:")
    print("  • qwen2.5:7b-instruct (Q4): ~6 GB VRAM")
    print()
    print("✅ NEW Hybrid Mode (Q3 + 1.5B) - MANDATORY:")
    print("  • Reasoner (Q3_K_M): ~3.8 GB")
    print("  • Reflex (1.5B): ~1.2 GB")
    print("  • Total: ~5 GB VRAM")
    print("  • Savings: ~1 GB (16% reduction)")
    print("  • Bonus: 60%+ faster simple tasks")
    print()
    print("⚠️  BREAKING CHANGE:")
    print("  Backward compatibility removed - hybrid is now mandatory for Ollama")
    print()


if __name__ == "__main__":
    main()
