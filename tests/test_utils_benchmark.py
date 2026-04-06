"""
Unit tests for janus.utils.benchmark module
Tests benchmarking utilities, statistics, and result comparison
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from janus.utils.benchmark import (
    Benchmark,
    BenchmarkSuite,
    quick_benchmark,
)


class TestBenchmark:
    """Test Benchmark class"""

    def test_initialization(self):
        """Test Benchmark initialization"""
        bench = Benchmark("test_bench", iterations=5)
        assert bench.name == "test_bench"
        assert bench.iterations == 5
        assert bench.results == []
        assert isinstance(bench.metadata, dict)

    def test_run_single_iteration(self):
        """Test running benchmark with single iteration"""
        mock_func = Mock(return_value="result")
        bench = Benchmark("single_iter", iterations=1)
        
        stats = bench.run(mock_func)
        
        assert mock_func.call_count == 1  # No warmup for single iteration
        assert stats["iterations"] == 1
        assert len(bench.results) == 1

    def test_run_multiple_iterations(self):
        """Test running benchmark with multiple iterations"""
        counter = {"calls": 0}
        
        def counting_func():
            counter["calls"] += 1
            return "result"
        
        bench = Benchmark("multi_iter", iterations=5)
        stats = bench.run(counting_func)
        
        # 1 warmup + 5 iterations = 6 total calls
        assert counter["calls"] == 6
        assert stats["iterations"] == 5
        assert len(bench.results) == 5

    def test_run_with_arguments(self):
        """Test running benchmark with function arguments"""
        mock_func = Mock(return_value="result")
        bench = Benchmark("with_args", iterations=1)
        
        bench.run(mock_func, "arg1", "arg2", kwarg1="value1")
        
        mock_func.assert_called_with("arg1", "arg2", kwarg1="value1")

    def test_get_stats(self):
        """Test getting benchmark statistics"""
        bench = Benchmark("test_stats", iterations=3)
        bench.results = [1.0, 2.0, 3.0]
        
        stats = bench.get_stats()
        
        assert stats["name"] == "test_stats"
        assert stats["iterations"] == 3
        assert stats["total"] == 6.0
        assert stats["mean"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["results"] == [1.0, 2.0, 3.0]

    def test_get_stats_empty(self):
        """Test getting stats when no results"""
        bench = Benchmark("empty", iterations=1)
        stats = bench.get_stats()
        assert stats == {}

    def test_metadata(self):
        """Test benchmark metadata"""
        bench = Benchmark("with_metadata", iterations=1)
        bench.metadata["test_key"] = "test_value"
        
        stats = bench.get_stats()
        bench.results = [1.0]
        stats = bench.get_stats()
        
        assert stats["metadata"]["test_key"] == "test_value"

    def test_print_results_with_data(self):
        """Test printing results with data"""
        bench = Benchmark("print_test", iterations=1)
        bench.results = [1.5]
        
        # Should not raise exception
        bench.print_results()

    def test_print_results_without_data(self):
        """Test printing results without data"""
        bench = Benchmark("no_data", iterations=1)
        
        # Should not raise exception
        bench.print_results()

    def test_actual_timing(self):
        """Test that benchmark actually measures time"""
        def sleep_func():
            time.sleep(0.01)
        
        bench = Benchmark("timing_test", iterations=2)
        stats = bench.run(sleep_func)
        
        # Each iteration should take at least 0.01s
        assert stats["mean"] >= 0.01
        assert stats["total"] >= 0.02


class TestBenchmarkSuite:
    """Test BenchmarkSuite class"""

    def test_initialization(self):
        """Test BenchmarkSuite initialization"""
        suite = BenchmarkSuite("test_suite")
        assert suite.name == "test_suite"
        assert isinstance(suite.benchmarks, list)
        assert len(suite.benchmarks) == 0
        assert suite.timestamp is not None

    def test_add_benchmark(self):
        """Test adding benchmarks to suite"""
        suite = BenchmarkSuite("test_suite")
        bench1 = Benchmark("bench1", iterations=1)
        bench2 = Benchmark("bench2", iterations=1)
        
        suite.add(bench1)
        suite.add(bench2)
        
        assert len(suite.benchmarks) == 2
        assert suite.benchmarks[0] is bench1
        assert suite.benchmarks[1] is bench2

    def test_print_report(self):
        """Test printing suite report"""
        suite = BenchmarkSuite("test_suite")
        bench = Benchmark("test_bench", iterations=1)
        bench.results = [1.0]
        suite.add(bench)
        
        # Should not raise exception
        suite.print_report()

    def test_save_results(self, tmp_path):
        """Test saving benchmark results to file"""
        suite = BenchmarkSuite("test_suite")
        
        bench1 = Benchmark("bench1", iterations=1)
        bench1.results = [1.0]
        
        bench2 = Benchmark("bench2", iterations=1)
        bench2.results = [2.0]
        
        suite.add(bench1)
        suite.add(bench2)
        
        output_path = tmp_path / "results.json"
        suite.save_results(str(output_path))
        
        # Verify file was created
        assert output_path.exists()
        
        # Verify content
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["name"] == "test_suite"
        assert "timestamp" in data
        assert len(data["benchmarks"]) == 2
        assert data["benchmarks"][0]["name"] == "bench1"
        assert data["benchmarks"][1]["name"] == "bench2"

    def test_save_results_creates_directory(self, tmp_path):
        """Test that save_results creates parent directories"""
        suite = BenchmarkSuite("test_suite")
        bench = Benchmark("test", iterations=1)
        bench.results = [1.0]
        suite.add(bench)
        
        output_path = tmp_path / "subdir" / "nested" / "results.json"
        suite.save_results(str(output_path))
        
        assert output_path.exists()

    def test_compare_results(self, tmp_path):
        """Test comparing two benchmark result files"""
        # Create baseline results
        baseline_data = {
            "name": "baseline",
            "timestamp": "2024-01-01T00:00:00",
            "benchmarks": [
                {"name": "bench1", "mean": 1.0, "total": 1.0, "min": 1.0, "max": 1.0, "count": 1},
                {"name": "bench2", "mean": 2.0, "total": 2.0, "min": 2.0, "max": 2.0, "count": 1},
            ],
        }
        
        baseline_path = tmp_path / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)
        
        # Create current results
        current_data = {
            "name": "current",
            "timestamp": "2024-01-02T00:00:00",
            "benchmarks": [
                {"name": "bench1", "mean": 0.8, "total": 0.8, "min": 0.8, "max": 0.8, "count": 1},
                {"name": "bench2", "mean": 2.5, "total": 2.5, "min": 2.5, "max": 2.5, "count": 1},
            ],
        }
        
        current_path = tmp_path / "current.json"
        with open(current_path, "w") as f:
            json.dump(current_data, f)
        
        # Should not raise exception
        BenchmarkSuite.compare_results(str(baseline_path), str(current_path))

    def test_compare_results_with_missing_benchmark(self, tmp_path):
        """Test comparing results when benchmark is missing in current"""
        baseline_data = {
            "name": "baseline",
            "timestamp": "2024-01-01T00:00:00",
            "benchmarks": [
                {"name": "bench1", "mean": 1.0, "total": 1.0, "min": 1.0, "max": 1.0, "count": 1},
                {"name": "bench2", "mean": 2.0, "total": 2.0, "min": 2.0, "max": 2.0, "count": 1},
            ],
        }
        
        baseline_path = tmp_path / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)
        
        # Current only has bench1
        current_data = {
            "name": "current",
            "timestamp": "2024-01-02T00:00:00",
            "benchmarks": [
                {"name": "bench1", "mean": 0.8, "total": 0.8, "min": 0.8, "max": 0.8, "count": 1},
            ],
        }
        
        current_path = tmp_path / "current.json"
        with open(current_path, "w") as f:
            json.dump(current_data, f)
        
        # Should handle missing benchmark gracefully
        BenchmarkSuite.compare_results(str(baseline_path), str(current_path))


class TestQuickBenchmark:
    """Test quick_benchmark utility function"""

    def test_quick_benchmark_basic(self):
        """Test quick_benchmark with basic function"""
        def simple_func():
            time.sleep(0.01)
            return "result"
        
        results = quick_benchmark("quick_test", simple_func, iterations=2)
        
        assert results["name"] == "quick_test"
        assert results["iterations"] == 2
        assert results["mean"] >= 0.01

    def test_quick_benchmark_with_arguments(self):
        """Test quick_benchmark with function arguments"""
        mock_func = Mock(return_value="result")
        
        results = quick_benchmark(
            "with_args", mock_func, 1, "arg1", kwarg1="value1"
        )
        
        mock_func.assert_called_with("arg1", kwarg1="value1")
        assert results["iterations"] == 1

    def test_quick_benchmark_returns_stats(self):
        """Test that quick_benchmark returns complete stats"""
        def test_func():
            return "result"
        
        results = quick_benchmark("stats_test", test_func, iterations=3)
        
        assert "name" in results
        assert "iterations" in results
        assert "total" in results
        assert "mean" in results
        assert "min" in results
        assert "max" in results
        assert "results" in results


class TestBenchmarkIntegration:
    """Integration tests for benchmark module"""

    def test_full_benchmark_workflow(self, tmp_path):
        """Test complete benchmark workflow"""
        # Create suite
        suite = BenchmarkSuite("integration_test")
        
        # Add benchmarks
        def fast_func():
            time.sleep(0.001)
        
        def slow_func():
            time.sleep(0.002)
        
        bench1 = Benchmark("fast_op", iterations=3)
        bench1.run(fast_func)
        suite.add(bench1)
        
        bench2 = Benchmark("slow_op", iterations=3)
        bench2.run(slow_func)
        suite.add(bench2)
        
        # Save results
        output_path = tmp_path / "integration_results.json"
        suite.save_results(str(output_path))
        
        # Verify saved data
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data["benchmarks"]) == 2
        assert data["benchmarks"][0]["mean"] < data["benchmarks"][1]["mean"]

    def test_benchmark_accuracy(self):
        """Test that benchmarks accurately measure time"""
        def precise_sleep():
            time.sleep(0.05)
        
        bench = Benchmark("accuracy_test", iterations=3)
        stats = bench.run(precise_sleep)
        
        # Should be close to 0.05s per iteration
        # Use 30% margin for CI environment variability
        assert 0.035 <= stats["mean"] <= 0.065  # Allow 30% margin
        assert 0.105 <= stats["total"] <= 0.195  # 3 iterations
