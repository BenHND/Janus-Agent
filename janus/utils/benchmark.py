"""
Benchmarking utilities for Janus performance testing
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from janus.logging import get_logger

logger = get_logger("benchmark")


class Benchmark:
    """
    Simple benchmarking utility for performance testing
    """

    def __init__(self, name: str, iterations: int = 1):
        """
        Initialize benchmark

        Args:
            name: Name of the benchmark
            iterations: Number of iterations to run
        """
        self.name = name
        self.iterations = iterations
        self.results: List[float] = []
        self.metadata: Dict[str, Any] = {}

    def run(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Run benchmark

        Args:
            func: Function to benchmark
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Dictionary with benchmark results
        """
        self.results = []

        # Warmup run
        if self.iterations > 1:
            func(*args, **kwargs)

        # Timed runs
        for _ in range(self.iterations):
            start = time.time()
            func(*args, **kwargs)
            duration = time.time() - start
            self.results.append(duration)

        return self.get_stats()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get benchmark statistics

        Returns:
            Dictionary with timing statistics
        """
        if not self.results:
            return {}

        return {
            "name": self.name,
            "iterations": len(self.results),
            "total": sum(self.results),
            "mean": sum(self.results) / len(self.results),
            "min": min(self.results),
            "max": max(self.results),
            "results": self.results,
            "metadata": self.metadata,
        }

    def print_results(self):
        """Print formatted benchmark results"""
        stats = self.get_stats()
        if not stats:
            logger.info(f"Benchmark '{self.name}': No results")
            return

        logger.info(f"\nBenchmark: {self.name}")
        logger.info(f"  Iterations: {stats['iterations']}")
        logger.info(f"  Mean: {stats['mean']:.4f}s")
        logger.info(f"  Min: {stats['min']:.4f}s")
        logger.info(f"  Max: {stats['max']:.4f}s")
        logger.info(f"  Total: {stats['total']:.4f}s")


class BenchmarkSuite:
    """
    Collection of benchmarks with comparison and reporting
    """

    def __init__(self, name: str):
        """
        Initialize benchmark suite

        Args:
            name: Name of the benchmark suite
        """
        self.name = name
        self.benchmarks: List[Benchmark] = []
        self.timestamp = datetime.now().isoformat()

    def add(self, benchmark: Benchmark):
        """
        Add a benchmark to the suite

        Args:
            benchmark: Benchmark to add
        """
        self.benchmarks.append(benchmark)

    def print_report(self):
        """Print formatted report of all benchmarks"""
        logger.info("=" * 70)
        logger.info(f"BENCHMARK SUITE: {self.name}")
        logger.info(f"Timestamp: {self.timestamp}")
        logger.info("=" * 70)

        for benchmark in self.benchmarks:
            benchmark.print_results()

        logger.info("=" * 70)

    def save_results(self, output_path: str):
        """
        Save benchmark results to JSON file

        Args:
            output_path: Path to output file
        """
        results = {
            "name": self.name,
            "timestamp": self.timestamp,
            "benchmarks": [b.get_stats() for b in self.benchmarks],
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_path}")

    @staticmethod
    def compare_results(baseline_path: str, current_path: str):
        """
        Compare two benchmark result files

        Args:
            baseline_path: Path to baseline results
            current_path: Path to current results
        """
        with open(baseline_path) as f:
            baseline = json.load(f)

        with open(current_path) as f:
            current = json.load(f)

        logger.info("=" * 70)
        logger.info("BENCHMARK COMPARISON")
        logger.info(f"Baseline: {baseline_path}")
        logger.info(f"Current: {current_path}")
        logger.info("=" * 70)
        logger.info(f"{'Benchmark':<30} {'Baseline':>12} {'Current':>12} {'Change':>12} {'%':>8}")
        logger.info("-" * 70)

        # Create lookup for current benchmarks
        current_lookup = {b["name"]: b for b in current["benchmarks"]}

        for baseline_bench in baseline["benchmarks"]:
            name = baseline_bench["name"]
            baseline_mean = baseline_bench["mean"]

            if name in current_lookup:
                current_mean = current_lookup[name]["mean"]
                change = current_mean - baseline_mean
                percent = (change / baseline_mean) * 100 if baseline_mean > 0 else 0

                # Color code based on performance
                symbol = "✓" if change < 0 else "✗" if change > 0 else "="

                logger.info(
                    f"{name:<30} "
                    f"{baseline_mean:>12.4f}s "
                    f"{current_mean:>12.4f}s "
                    f"{change:>+12.4f}s "
                    f"{percent:>+7.1f}% {symbol}"
                )
            else:
                logger.info(f"{name:<30} {'N/A':>12} {'MISSING':>12}")

        logger.info("=" * 70)


def quick_benchmark(
    name: str, func: Callable, iterations: int = 10, *args, **kwargs
) -> Dict[str, Any]:
    """
    Quick utility to benchmark a function

    Args:
        name: Name of the benchmark
        func: Function to benchmark
        iterations: Number of iterations
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function

    Returns:
        Dictionary with benchmark results
    """
    bench = Benchmark(name, iterations)
    results = bench.run(func, *args, **kwargs)
    bench.print_results()
    return results
