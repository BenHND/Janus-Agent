"""
Ollama Integration Example
Demonstrates the enhanced Ollama support features including:
- Model management (list, pull, delete)
- Streaming inference
- GPU detection
- Chat interactions
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from janus.ai.llm.ollama_client import OllamaClient
from janus.ai.llm.unified_client import UnifiedLLMClient


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def example_check_availability():
    """Example: Check if Ollama server is available"""
    print_section("Checking Ollama Availability")
    
    client = OllamaClient()
    available = client.is_available()
    
    if available:
        version = client.get_version()
        print(f"✓ Ollama server is available")
        print(f"  Version: {version}")
    else:
        print("✗ Ollama server is not available")
        print("  Make sure Ollama is installed and running:")
        print("    - Install: https://ollama.ai/download")
        print("    - Start: ollama serve")
    
    return available


def example_list_models():
    """Example: List installed models"""
    print_section("Listing Installed Models")
    
    client = OllamaClient()
    models = client.list_models()
    
    if models:
        print(f"Found {len(models)} model(s):\n")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0) / (1024**3)  # Convert to GB
            print(f"  • {name}")
            print(f"    Size: {size:.2f} GB")
            
            # Get detailed info
            info = client.get_model_info(name)
            if info and "details" in info:
                details = info["details"]
                if "parameter_size" in details:
                    print(f"    Parameters: {details['parameter_size']}")
            print()
    else:
        print("No models installed yet.")
        print("\nInstall a model with:")
        print("  ollama pull mistral:7b")


def example_gpu_detection():
    """Example: Detect GPU hardware"""
    print_section("GPU Detection")
    
    client = OllamaClient()
    gpu_info = client.detect_gpu()
    
    if gpu_info.get("available"):
        print(f"✓ GPU detected: {gpu_info.get('type', 'unknown').upper()}")
        devices = gpu_info.get("devices", [])
        if devices:
            print(f"\nDevices ({len(devices)}):")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device.get('name', 'Unknown')}")
                memory = device.get("memory")
                if memory:
                    print(f"     Memory: {memory}")
        
        # Show recommended options
        print("\nRecommended options:")
        options = client.get_recommended_options(gpu_info)
        for key, value in options.items():
            print(f"  {key}: {value}")
    else:
        print("✗ No GPU detected (will use CPU)")
        print("\nRecommended CPU options:")
        options = client.get_recommended_options(gpu_info)
        for key, value in options.items():
            print(f"  {key}: {value}")


def example_non_streaming_generation():
    """Example: Non-streaming text generation"""
    print_section("Non-Streaming Generation")
    
    client = OllamaClient()
    models = client.list_models()
    
    if not models:
        print("No models available. Please install a model first.")
        return
    
    model_name = models[0].get("name")
    print(f"Using model: {model_name}\n")
    
    prompt = "Explain what Ollama is in one sentence."
    print(f"Prompt: {prompt}\n")
    
    print("Response:")
    for response in client.generate(
        model=model_name,
        prompt=prompt,
        stream=False,
    ):
        if "error" in response:
            print(f"Error: {response['error']}")
        elif "response" in response:
            print(response["response"])


def example_streaming_generation():
    """Example: Streaming text generation"""
    print_section("Streaming Generation")
    
    client = OllamaClient()
    models = client.list_models()
    
    if not models:
        print("No models available. Please install a model first.")
        return
    
    model_name = models[0].get("name")
    print(f"Using model: {model_name}\n")
    
    prompt = "Write a haiku about artificial intelligence."
    print(f"Prompt: {prompt}\n")
    
    print("Response (streaming):")
    for chunk in client.generate(
        model=model_name,
        prompt=prompt,
        stream=True,
    ):
        if "error" in chunk:
            print(f"\nError: {chunk['error']}")
            break
        elif "response" in chunk:
            print(chunk["response"], end="", flush=True)
            if chunk.get("done"):
                print()  # New line at end


def example_chat_interaction():
    """Example: Multi-turn chat conversation"""
    print_section("Chat Interaction")
    
    client = OllamaClient()
    models = client.list_models()
    
    if not models:
        print("No models available. Please install a model first.")
        return
    
    model_name = models[0].get("name")
    print(f"Using model: {model_name}\n")
    
    messages = [
        {"role": "user", "content": "What is 2+2?"},
    ]
    
    print("User: What is 2+2?\n")
    print("Assistant: ", end="", flush=True)
    
    for chunk in client.chat(
        model=model_name,
        messages=messages,
        stream=True,
    ):
        if "error" in chunk:
            print(f"\nError: {chunk['error']}")
            break
        elif "message" in chunk:
            content = chunk["message"].get("content", "")
            print(content, end="", flush=True)
            if chunk.get("done"):
                print()


def example_llm_service_integration():
    """Example: Using Ollama through LLMService"""
    print_section("LLMService Integration")
    
    client = OllamaClient()
    models = client.list_models()
    
    if not models:
        print("No models available. Please install a model first.")
        return
    
    model_name = models[0].get("name")
    print(f"Using model: {model_name}\n")
    
    # Initialize LLMService with Ollama
    llm = UnifiedLLMClient(
        provider="ollama",
        model=model_name,
    )
    
    if llm.available:
        print("✓ LLMService initialized with Ollama\n")
        
        # Analyze a command
        command = "open Chrome and search for Python tutorials"
        print(f"Command: {command}\n")
        
        result = llm.analyze_command(command)
        
        if result.get("status") == "success":
            print("Analysis Results:")
            print(f"  Intent: {result.get('intent', 'unknown')}")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
            
            if "actions" in result:
                print(f"  Actions: {len(result.get('actions', []))}")
        else:
            print(f"Analysis failed: {result.get('error', 'Unknown error')}")
    else:
        print("✗ Failed to initialize LLMService with Ollama")


def example_embeddings():
    """Example: Generate embeddings"""
    print_section("Embeddings Generation")
    
    client = OllamaClient()
    models = client.list_models()
    
    if not models:
        print("No models available. Please install a model first.")
        return
    
    model_name = models[0].get("name")
    print(f"Using model: {model_name}\n")
    
    text = "Ollama is a tool for running large language models locally."
    print(f"Text: {text}\n")
    
    embeddings = client.embeddings(
        model=model_name,
        prompt=text,
    )
    
    if embeddings:
        print(f"✓ Generated embeddings vector")
        print(f"  Dimensions: {len(embeddings)}")
        print(f"  First 5 values: {embeddings[:5]}")
    else:
        print("✗ Failed to generate embeddings")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("  Ollama Integration Examples")
    print("  Demonstrating Enhanced Ollama Support")
    print("=" * 60)
    
    # Check if Ollama is available
    available = example_check_availability()
    
    if not available:
        print("\n⚠️  Ollama is not available. Please install and start it first.")
        print("   Visit https://ollama.ai/download for installation instructions.")
        return
    
    # Run all examples
    try:
        example_gpu_detection()
        example_list_models()
        
        # Only run generation examples if models are installed
        client = OllamaClient()
        if client.list_models():
            example_non_streaming_generation()
            example_streaming_generation()
            example_chat_interaction()
            example_embeddings()
            example_llm_service_integration()
        else:
            print("\n⚠️  No models installed. Install one to try generation examples:")
            print("   ollama pull mistral:7b")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("  Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
