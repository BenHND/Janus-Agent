"""
TICKET-011 Demo: Simplified Cognitive Planner Configuration
Demonstrates the new setup wizard and enhanced features
"""
import json

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_01_backend_detection():
    """Demo 1: Automatic backend detection"""
    print_section("Demo 1: Backend Detection and Status")

    from janus.ai.reasoning.llm_setup_wizard import LLMSetupWizard

    wizard = LLMSetupWizard()

    # Detect backends
    ollama_available, ollama_info = wizard.detect_ollama()
    llama_cpp_available, llama_cpp_info = wizard.detect_llama_cpp()

    print("Backend Detection Results:")
    print(f"  Ollama: {'✅ Available' if ollama_available else '❌ Not available'}")
    if ollama_info:
        print(f"    {ollama_info}")

    print(f"  llama-cpp-python: {'✅ Available' if llama_cpp_available else '❌ Not available'}")
    if llama_cpp_info:
        print(f"    {llama_cpp_info}")

    print()


def demo_02_performance_metrics():
    """Demo 2: Enhanced performance metrics"""
    print_section("Demo 2: Performance Metrics Comparison")

    # Initialize with mock backend for demo
    llm = ReasonerLLM(backend="mock")

    # Reset metrics for clean demo
    llm.reset_metrics()

    print("Running 10 command parses...")

    # Make several calls
    commands = [
        "ouvre Chrome",
        "copie ce texte",
        "colle ici",
        "open Safari",
        "navigate to GitHub",
        "clique sur le bouton",
        "save file",
        "cherche Python",
        "close window",
        "paste content",
    ]

    for cmd in commands:
        lang = "fr" if any(word in cmd for word in ["ouvre", "copie", "colle", "cherche"]) else "en"
        llm.parse_command(cmd, language=lang)

    # Get standard metrics
    print("\nStandard Metrics:")
    metrics = llm.get_metrics()
    print(f"  Total calls: {metrics['total_calls']}")
    print(f"  LLM calls: {metrics['llm_calls']}")
    print(f"  Fallback calls: {metrics['fallback_count']}")
    print(f"  Average latency: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  LLM avg latency: {metrics['llm_avg_latency_ms']:.2f}ms")
    print(f"  Fallback avg latency: {metrics['fallback_avg_latency_ms']:.2f}ms")
    print(f"  LLM usage: {metrics['llm_usage_percent']:.1f}%")

    # Get performance comparison
    print("\nPerformance Comparison:")
    comparison = llm.get_performance_comparison()
    print(f"  Backend: {comparison['backend']}")
    print(f"  Model: {comparison['model']}")
    print(f"  Performance rating: {comparison['performance_rating']}")
    print(f"  Overall avg latency: {comparison['overall_avg_latency_ms']:.2f}ms")

    if "speed_comparison" in comparison:
        print(f"  Speed comparison: {comparison['speed_comparison']}")


def demo_03_fallback_with_logging():
    """Demo 3: Graceful fallback with detailed logging"""
    print_section("Demo 3: Fallback Mechanism with Logging")

    import logging

    # Enable logging to see fallback messages
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("Initializing with unavailable backend (will trigger fallback)...\n")

    # Create LLM with unavailable backend
    llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")

    print(f"\nBackend available: {llm.available}")
    print("Parsing commands (will use fallback)...\n")

    # Try parsing - should fallback gracefully
    result = llm.parse_command("ouvre Chrome", language="fr")

    print(f"\nResult:")
    print(f"  Source: {result['source']}")
    print(f"  Intent: {result['intents'][0]['intent'] if result['intents'] else 'none'}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")

    # Check metrics
    metrics = llm.get_metrics()
    print(f"\nFallback statistics:")
    print(f"  Fallback calls: {metrics['fallback_count']}/{metrics['total_calls']}")
    print(f"  Fallback avg latency: {metrics['fallback_avg_latency_ms']:.2f}ms")


def demo_04_model_recommendations():
    """Demo 4: Model recommendations"""
    print_section("Demo 4: Model Recommendations")

    from janus.ai.reasoning.llm_setup_wizard import LLMSetupWizard

    wizard = LLMSetupWizard()

    print("Recommended Ollama Models:\n")
    models = wizard.get_recommended_models("ollama")

    for i, model in enumerate(models, 1):
        print(f"{i}. {model['display_name']}")
        print(f"   Size: {model['size']}")
        print(f"   Performance: {model['performance']}")
        print(f"   Install: {model['command']}")
        print()


def demo_05_latency_optimization():
    """Demo 5: Latency optimization (<500ms target)"""
    print_section("Demo 5: Latency Optimization (<500ms target)")

    from janus.ai.reasoning.reasoner_llm import LLMBackend, LLMConfig

    # Create config optimized for speed
    config = LLMConfig(
        backend=LLMBackend.MOCK,
        n_ctx=1024,  # Reduced context window
        temperature=0.1,  # Low temperature for faster, deterministic output
        max_tokens=256,  # Fewer tokens to generate
        timeout_ms=500,  # 500ms timeout (optimized from 800ms)
    )

    llm = ReasonerLLM(backend="mock", config=config)

    print("Configuration optimized for speed:")
    print(f"  Context window: {config.n_ctx} tokens")
    print(f"  Max tokens: {config.max_tokens}")
    print(f"  Timeout: {config.timeout_ms}ms")
    print(f"  Temperature: {config.temperature}")

    print("\nTesting latency with optimized config...")

    # Test latency
    result = llm.parse_command("ouvre Chrome", language="fr")
    latency = result.get("latency_ms", 0)

    print(f"\nResult:")
    print(f"  Latency: {latency:.2f}ms")
    print(f"  Target: <500ms")
    print(f"  Status: {'✅ Within target' if latency < 500 else '⚠️  Above target'}")


def demo_06_performance_comparison():
    """Demo 6: LLM vs Classic Parser comparison"""
    print_section("Demo 6: LLM vs Classic Parser Performance")

    llm = ReasonerLLM(backend="mock")
    llm.reset_metrics()

    print("Simulating mixed usage (LLM + fallback)...")
    print("Note: In real usage, fallback is only used when LLM is unavailable")

    # Simulate some LLM calls (mock backend)
    for cmd in ["ouvre Chrome", "copie", "colle"]:
        llm.parse_command(cmd, language="fr")

    # Get comparison
    comparison = llm.get_performance_comparison()

    print("\nPerformance Summary:")
    print(f"  Backend: {comparison['backend']}")
    print(f"  LLM available: {comparison['llm_available']}")
    print(f"  Total calls: {comparison['total_calls']}")
    print(f"  LLM usage: {comparison['llm_usage_percent']:.1f}%")
    print(f"  Performance rating: {comparison['performance_rating']}")
    print(f"  Overall avg latency: {comparison['overall_avg_latency_ms']:.2f}ms")

    print("\nDetailed Metrics:")
    print(f"  LLM calls: {comparison['llm_calls']}")
    print(f"  LLM avg latency: {comparison['llm_avg_latency_ms']:.2f}ms")
    print(f"  Fallback calls: {comparison['fallback_calls']}")
    print(f"  Fallback avg latency: {comparison['fallback_avg_latency_ms']:.2f}ms")


def demo_07_ui_features():
    """Demo 7: UI Configuration Features"""
    print_section("Demo 7: UI Configuration Features")

    print("New UI Features:")
    print()
    print("1. Status Indicator")
    print("   - Real-time backend status (green/orange)")
    print("   - Shows available backends and versions")
    print()
    print("2. Setup Wizard Button")
    print("   - Click 'Run Setup Wizard' for guided installation")
    print("   - Detects backends, helps select models")
    print("   - Tests configuration automatically")
    print()
    print("3. Test Backend Button")
    print("   - Click 'Test Backend' to verify configuration")
    print("   - Shows latency and status")
    print("   - Helpful for troubleshooting")
    print()
    print("4. Browse Button")
    print("   - Easy file browser for llama-cpp models")
    print("   - Filters for .gguf files")
    print()
    print("5. Enhanced Model Selection")
    print("   - Updated model recommendations")
    print("   - Mistral 7B, Phi-3, Gemma, Qwen supported")
    print()
    print("6. Timeout Configuration")
    print("   - Adjustable timeout (200-5000ms)")
    print("   - Default optimized to 500ms (from 800ms)")
    print("   - Visual indicator shows target")
    print()
    print("To open the UI:")
    print('  python -c "from janus.ui.config_ui import ConfigUI; ConfigUI().show()"')


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  TICKET-011: Cognitive Planner Simplified Configuration")
    print("  Feature Demonstrations")
    print("=" * 70)

    demos = [
        demo_01_backend_detection,
        demo_02_performance_metrics,
        demo_03_fallback_with_logging,
        demo_04_model_recommendations,
        demo_05_latency_optimization,
        demo_06_performance_comparison,
        demo_07_ui_features,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"❌ Error in {demo.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("  All demos completed!")
    print("  See docs/COGNITIVE_PLANNER_SETUP.md for full documentation")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
