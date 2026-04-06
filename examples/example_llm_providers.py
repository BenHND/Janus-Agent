"""
Example: Using Alternative LLM Providers - TICKET-009
Demonstrates how to use different LLM providers with Janus
Updated to use UnifiedLLMClient
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.ai.llm.unified_client import UnifiedLLMClient


def example_openai():
    """Example: Using OpenAI GPT-4"""
    print("\n" + "=" * 60)
    print("Example 1: OpenAI GPT-4")
    print("=" * 60 + "\n")

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable to use OpenAI")
        print("Example: export OPENAI_API_KEY='sk-...'")
        return

    # Initialize LLM client with OpenAI
    llm = UnifiedLLMClient(
        provider="openai",
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000,
    )

    # Check provider status
    print(f"Provider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available}")

    if not llm.available:
        print("❌ OpenAI provider not available")
        return

    # Analyze a command
    print("\nAnalyzing command: 'open chrome and navigate to github.com'")
    result = llm.analyze_command("open chrome and navigate to github.com")

    print(f"\nIntent: {result.get('intent', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print(f"Status: {result.get('status', 'N/A')}")


def example_anthropic():
    """Example: Using Anthropic Claude"""
    print("\n" + "=" * 60)
    print("Example 2: Anthropic Claude")
    print("=" * 60 + "\n")

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Set ANTHROPIC_API_KEY environment variable to use Anthropic")
        print("Example: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    # Initialize with Claude Sonnet
    llm = UnifiedLLMClient(
        provider="anthropic",
        model="claude-3-sonnet-20240229",
        temperature=0.7,
    )

    # Provider info accessible via llm.provider, llm.model, llm.available
    print(f"Provider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available}")

    if not llm.available:
        print("❌ Anthropic provider not available")
        return

    # Analyze content
    print("\nAnalyzing code snippet...")
    code = """
def hello_world():
    print("Hello, World!")
    return True
"""
    result = llm.analyze_content(code, "code", "explain")

    print(f"\nTask: {result.get('task', 'N/A')}")
    print(f"Result: {result.get('result', 'N/A')[:200]}...")


def example_local_llm():
    """Example: Using Local LLM via llama-cpp"""
    print("\n" + "=" * 60)
    print("Example 3: Local LLM (llama-cpp)")
    print("=" * 60 + "\n")

    # Example model path (update with your actual path)
    model_path = "/path/to/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

    if not os.path.exists(model_path):
        print(f"⚠️  Model not found: {model_path}")
        print("\nDownload a GGUF model from HuggingFace:")
        print("  https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
        print("\nOr use Ollama instead (see example_ollama)")
        return

    # Initialize local LLM
    llm = UnifiedLLMClient(
        provider="local",
        model_path=model_path,
        temperature=0.1,  # Low temperature for deterministic output
        max_tokens=512,
    )

    # Provider info accessible via llm.provider, llm.model, llm.available
    print(f"Provider: {llm.provider}")
    print(f"Available: {llm.available}")

    if not llm.available:
        print("❌ Local LLM not available")
        return

    # Generate action plan
    print("\nGenerating action plan...")
        print(f"  {i}. {action.get('action', 'N/A')} via {action.get('module', 'N/A')}")


def example_ollama():
    """Example: Using Ollama"""
    print("\n" + "=" * 60)
    print("Example 4: Ollama")
    print("=" * 60 + "\n")

    print("Prerequisites:")
    print("  1. Install Ollama: https://ollama.ai/")
    print("  2. Pull a model: ollama pull mistral:7b-instruct")
    print("  3. Start server: ollama serve")
    print()

    # Initialize Ollama
    llm = UnifiedLLMClient(
    )

    # Provider info accessible via llm.provider, llm.model, llm.available
    print(f"Provider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available}")

    if not llm.available:
        print("❌ Ollama not available")
        print("   Make sure Ollama server is running: ollama serve")
        return

    # Test with multiple commands
    commands = ["open vscode", "copy the selected text", "search for python documentation"]

    print("\nAnalyzing commands:")
    for cmd in commands:
        result = llm.analyze_command(cmd)
        print(f"  '{cmd}' -> {result.get('intent', 'unknown')}")


def example_mistral():
    """Example: Using Mistral AI"""
    print("\n" + "=" * 60)
    print("Example 5: Mistral AI")
    print("=" * 60 + "\n")

    # Check for API key
    if not os.environ.get("MISTRAL_API_KEY"):
        print("⚠️  Set MISTRAL_API_KEY environment variable to use Mistral")
        print("Get your API key from: https://console.mistral.ai/")
        return

    # Initialize Mistral
    llm = UnifiedLLMClient(
    )

    # Provider info accessible via llm.provider, llm.model, llm.available
    print(f"Provider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available}")

    if not llm.available:
        print("❌ Mistral provider not available")
        return

    # Test command analysis
    print("\nAnalyzing command: 'navigate to github.com and search for python projects'")
    result = llm.analyze_command("navigate to github.com and search for python projects")

    print(f"\nIntent: {result.get('intent', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")


def example_fallback_chain():
    """Example: Fallback chain between providers"""
    print("\n" + "=" * 60)
    print("Example 6: Automatic Fallback Chain")
    print("=" * 60 + "\n")

    print("Testing fallback chain: openai -> anthropic -> local -> ollama -> mock")

    # Configure fallback chain
    llm = UnifiedLLMClient(
        provider="openai",  # Primary (will likely fail without API key)
        model="gpt-4",
    )

    # Check which provider is actually being used
    # Provider info accessible via llm.provider, llm.model, llm.available
    print(f"\nActive provider: {info['provider']}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available}")

    # Test it works
    result = llm.analyze_command("open terminal and run ls")
    print(f"\nCommand analyzed successfully with {info['provider']}")
    print(f"Intent: {result.get('intent', 'N/A')}")


def example_mock_provider():
    """Example: Using Mock Provider for Testing"""
    print("\n" + "=" * 60)
    print("Example 7: Mock Provider (Testing)")
    print("=" * 60 + "\n")

    # Mock provider is always available, no API keys needed
    llm = UnifiedLLMClient(provider="mock")

    print("Mock provider is perfect for:")
    print("  • Testing without API costs")
    print("  • Development and debugging")
    print("  • CI/CD pipelines")
    print("  • Unit tests")

    # Test various commands
    test_commands = [
        "open chrome",
        "search for python tutorials",
        "copy this text",
        "delete all files",  # Should require confirmation
    ]

    print("\nTesting commands:")
    for cmd in test_commands:
        result = llm.analyze_command(cmd)
        requires_confirm = "⚠️  " if result.get("requires_confirmation") else "✓ "
        print(f"  {requires_confirm}{cmd}: {result.get('intent', 'unknown')}")

    # Show metrics
    print(f"  Average time: {metrics.get('average_time', 0)*1000:.1f}ms")
    print(f"  Cache hit rate: {metrics.get('cache_hit_rate', 0):.1%}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("LLM Provider Examples - TICKET-009")
    print("=" * 60)

    # Run examples
    example_mock_provider()  # Always works
    example_fallback_chain()  # Demonstrates fallback
    example_openai()  # Requires API key
    example_anthropic()  # Requires API key
    example_mistral()  # Requires API key
    example_ollama()  # Requires Ollama server
    example_local_llm()  # Requires model file

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")

    print("Next steps:")
    print("  • Set up API keys for commercial providers")
    print("  • Install Ollama for local inference")
    print("  • Download GGUF models for llama-cpp")
    print("  • See docs/LLM_PROVIDER_GUIDE.md for detailed setup")


if __name__ == "__main__":
    main()
