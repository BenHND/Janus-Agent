"""
Provider Performance Comparison Tool - TICKET-009
Compare latency, quality, and cost across different LLM providers
"""
import json
import os
import sys
import time
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.ai.llm.unified_client import UnifiedLLMClient


class ProviderComparison:
    """
    Compare performance across multiple LLM providers

    Metrics tracked:
    - Average latency
    - Cache hit rate
    - Error rate
    - Response quality (manual evaluation)
    """

    def __init__(self, providers_config: List[Dict[str, Any]]):
        """
        Initialize comparison tool

        Args:
            providers_config: List of provider configurations
                Example: [
                    {"provider": "openai", "model": "gpt-4"},
                    {"provider": "anthropic", "model": "claude-3-sonnet-20240229"},
                    {"provider": "local", "model_path": "/path/to/model.gguf"}
                ]
        """
        self.providers_config = providers_config
        self.results = {}

    def run_comparison(self, test_commands: List[str], iterations: int = 3) -> Dict[str, Any]:
        """
        Run performance comparison across providers

        Args:
            test_commands: List of commands to test
            iterations: Number of iterations per command

        Returns:
            Comparison results with metrics per provider
        """
        print(f"\n{'='*60}")
        print("LLM Provider Performance Comparison")
        print(f"{'='*60}\n")
        print(f"Test commands: {len(test_commands)}")
        print(f"Iterations per command: {iterations}")
        print(f"Total tests per provider: {len(test_commands) * iterations}\n")

        for config in self.providers_config:
            provider_name = f"{config['provider']}:{config.get('model', 'default')}"
            print(f"Testing {provider_name}...")

            try:
                # Initialize provider
                llm = UnifiedLLMClient(**config)

                if not llm.available:
                    print(f"  ⚠️  Provider unavailable, skipping...")
                    self.results[provider_name] = {
                        "available": False,
                        "error": "Provider not available",
                    }
                    continue

                # Reset metrics
                llm.reset_metrics()

                # Run tests
                latencies = []
                errors = 0
                responses = []

                for iteration in range(iterations):
                    for cmd in test_commands:
                        start_time = time.time()
                        try:
                            result = llm.analyze_command(cmd)
                            latency = (time.time() - start_time) * 1000  # ms
                            latencies.append(latency)
                            responses.append(result)
                        except Exception as e:
                            errors += 1
                            print(f"  ❌ Error: {e}")

                # Get metrics
                metrics = llm.get_performance_metrics()

                # Store results
                self.results[provider_name] = {
                    "available": True,
                    "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                    "min_latency_ms": min(latencies) if latencies else 0,
                    "max_latency_ms": max(latencies) if latencies else 0,
                    "total_calls": len(latencies),
                    "errors": errors,
                    "error_rate": errors / (len(test_commands) * iterations)
                    if test_commands
                    else 0,
                    "cache_hit_rate": metrics.get("cache_hit_rate", 0),
                    "provider_info": llm.get_provider_info(),
                }

                print(f"  ✅ Completed: avg={self.results[provider_name]['avg_latency_ms']:.1f}ms")

            except Exception as e:
                print(f"  ❌ Failed to initialize: {e}")
                self.results[provider_name] = {"available": False, "error": str(e)}

        return self.results

    def print_results(self):
        """Print comparison results in formatted table"""
        print(f"\n{'='*80}")
        print("Results Summary")
        print(f"{'='*80}\n")

        # Header
        print(
            f"{'Provider':<30} {'Latency (ms)':<15} {'Error Rate':<12} {'Cache Rate':<12} {'Status':<10}"
        )
        print(f"{'-'*80}")

        # Sort by latency
        sorted_results = sorted(
            self.results.items(), key=lambda x: x[1].get("avg_latency_ms", float("inf"))
        )

        for provider, data in sorted_results:
            if not data.get("available", False):
                status = "❌ Unavailable"
                latency = "N/A"
                error_rate = "N/A"
                cache_rate = "N/A"
            else:
                status = "✅ Available"
                latency = f"{data['avg_latency_ms']:.1f}"
                error_rate = f"{data['error_rate']:.1%}"
                cache_rate = f"{data['cache_hit_rate']:.1%}"

            print(f"{provider:<30} {latency:<15} {error_rate:<12} {cache_rate:<12} {status:<10}")

        print(f"\n{'='*80}\n")

    def save_results(self, filepath: str):
        """Save results to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {filepath}")

    def get_recommendations(self) -> Dict[str, str]:
        """
        Get recommendations based on results

        Returns:
            Dictionary with recommendations for different use cases
        """
        available_providers = {
            name: data for name, data in self.results.items() if data.get("available", False)
        }

        if not available_providers:
            return {"error": "No available providers to recommend"}

        recommendations = {}

        # Fastest provider
        fastest = min(
            available_providers.items(), key=lambda x: x[1].get("avg_latency_ms", float("inf"))
        )
        recommendations["fastest"] = {
            "provider": fastest[0],
            "latency_ms": fastest[1]["avg_latency_ms"],
            "use_case": "Development, quick iterations, latency-critical tasks",
        }

        # Most reliable (lowest error rate)
        most_reliable = min(available_providers.items(), key=lambda x: x[1].get("error_rate", 1.0))
        recommendations["most_reliable"] = {
            "provider": most_reliable[0],
            "error_rate": most_reliable[1]["error_rate"],
            "use_case": "Production, critical tasks requiring reliability",
        }

        # Best cache performance
        best_cache = max(available_providers.items(), key=lambda x: x[1].get("cache_hit_rate", 0.0))
        recommendations["best_cache"] = {
            "provider": best_cache[0],
            "cache_hit_rate": best_cache[1]["cache_hit_rate"],
            "use_case": "Repetitive tasks, testing, cost optimization",
        }

        return recommendations

    def print_recommendations(self):
        """Print usage recommendations"""
        recommendations = self.get_recommendations()

        if "error" in recommendations:
            print(f"\n❌ {recommendations['error']}\n")
            return

        print(f"\n{'='*80}")
        print("Recommendations")
        print(f"{'='*80}\n")

        for category, rec in recommendations.items():
            print(f"{category.upper().replace('_', ' ')}:")
            print(f"  Provider: {rec['provider']}")

            if "latency_ms" in rec:
                print(f"  Latency: {rec['latency_ms']:.1f}ms")
            if "error_rate" in rec:
                print(f"  Error Rate: {rec['error_rate']:.1%}")
            if "cache_hit_rate" in rec:
                print(f"  Cache Hit Rate: {rec['cache_hit_rate']:.1%}")

            print(f"  Use Case: {rec['use_case']}\n")


def main():
    """Run example comparison"""

    # Test commands (varied complexity)
    test_commands = [
        "open chrome",
        "search for python tutorials",
        "copy this text and paste it in notepad",
        "navigate to github.com",
        "open vscode and create a new file",
    ]

    # Provider configurations to test
    providers_config = [
        # OpenAI
        {"provider": "openai", "model": "gpt-4", "enable_cache": True},
        {"provider": "openai", "model": "gpt-3.5-turbo", "enable_cache": True},
        # Anthropic
        {"provider": "anthropic", "model": "claude-3-sonnet-20240229", "enable_cache": True},
        {"provider": "anthropic", "model": "claude-3-haiku-20240307", "enable_cache": True},
        # Mistral
        {"provider": "mistral", "model": "mistral-small", "enable_cache": True},
        # Ollama (if running locally)
        {"provider": "ollama", "model": "mistral:7b-instruct", "enable_cache": True},
        # Mock (always available for testing)
        {"provider": "mock", "enable_cache": True},
    ]

    # Run comparison
    comparison = ProviderComparison(providers_config)
    comparison.run_comparison(test_commands, iterations=3)

    # Print results
    comparison.print_results()
    comparison.print_recommendations()

    # Save results
    comparison.save_results("provider_comparison_results.json")


if __name__ == "__main__":
    main()
