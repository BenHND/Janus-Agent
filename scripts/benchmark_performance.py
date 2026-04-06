#!/usr/bin/env python3
"""
Performance benchmarking script for Janus
Tests STT → Action chain performance
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time

from janus.utils.benchmark import Benchmark, BenchmarkSuite
from janus.utils.gpu_utils import print_device_info
from janus.utils.profiler import get_memory_tracker, get_profiler


def benchmark_imports():
    """Benchmark import times"""
    print("\n" + "=" * 70)
    print("BENCHMARKING MODULE IMPORTS")
    print("=" * 70)

    imports_to_test = [
        ("whisper", "import whisper"),
        ("pyautogui", "import pyautogui"),
        ("PIL", "from PIL import Image"),
        ("numpy", "import numpy as np"),
        ("torch", "import torch"),
    ]

    for name, import_stmt in imports_to_test:
        bench = Benchmark(f"import_{name}", iterations=1)

        def do_import():
            exec(import_stmt, {})

        try:
            bench.run(do_import)
            bench.print_results()
        except ImportError:
            print(f"\nBenchmark: import_{name}")
            print(f"  Status: Not installed")


def benchmark_whisper_loading():
    """Benchmark Whisper model loading"""
    print("\n" + "=" * 70)
    print("BENCHMARKING WHISPER MODEL LOADING")
    print("=" * 70)

    try:
        import whisper

        from janus.utils.gpu_utils import get_whisper_device

        device = get_whisper_device()
        print(f"\nDevice: {device}")

        models_to_test = ["tiny", "base"]

        for model_size in models_to_test:
            bench = Benchmark(f"load_whisper_{model_size}", iterations=1)

            def load_model():
                model = whisper.load_model(model_size, device=device)
                del model  # Clean up

            bench.run(load_model)
            bench.print_results()
    except ImportError:
        print("\nWhisper not installed, skipping")


def benchmark_ocr_cache():
    """Benchmark OCR cache performance"""
    print("\n" + "=" * 70)
    print("BENCHMARKING OCR CACHE")
    print("=" * 70)

    try:
        import io

        from PIL import Image

        from janus.vision.cache import OCRCache

        # Create test image
        test_img = Image.new("RGB", (100, 100), color="white")

        # Test without perceptual hashing
        cache_no_phash = OCRCache(use_perceptual_hash=False)
        bench1 = Benchmark("cache_set_no_phash", iterations=100)
        bench1.run(lambda: cache_no_phash.set(test_img, "test_result"))
        bench1.print_results()

        bench2 = Benchmark("cache_get_no_phash", iterations=100)
        bench2.run(lambda: cache_no_phash.get(test_img))
        bench2.print_results()

        # Test with perceptual hashing
        cache_with_phash = OCRCache(use_perceptual_hash=True)
        bench3 = Benchmark("cache_set_with_phash", iterations=100)
        bench3.run(lambda: cache_with_phash.set(test_img, "test_result"))
        bench3.print_results()

        bench4 = Benchmark("cache_get_with_phash", iterations=100)
        bench4.run(lambda: cache_with_phash.get(test_img))
        bench4.print_results()

    except ImportError as e:
        print(f"\nSkipping OCR cache benchmark: {e}")


def benchmark_profiler_overhead():
    """Benchmark profiler overhead"""
    print("\n" + "=" * 70)
    print("BENCHMARKING PROFILER OVERHEAD")
    print("=" * 70)

    from janus.utils.profiler import get_profiler, profile

    profiler = get_profiler()

    # Test overhead of profiling
    def dummy_work():
        time.sleep(0.001)

    # Without profiling
    bench1 = Benchmark("no_profiling", iterations=100)
    bench1.run(dummy_work)
    bench1.print_results()

    # With profiling
    profiler.enable()
    bench2 = Benchmark("with_profiling", iterations=100)

    def profiled_work():
        with profile("dummy_work"):
            dummy_work()

    bench2.run(profiled_work)
    bench2.print_results()

    overhead = (
        (bench2.get_stats()["mean"] - bench1.get_stats()["mean"]) / bench1.get_stats()["mean"] * 100
    )
    print(f"\nProfiler overhead: {overhead:.2f}%")


def main():
    """Run all benchmarks"""
    print("\n" + "=" * 70)
    print("SPECTRA PERFORMANCE BENCHMARKS")
    print("=" * 70)

    # Print device info
    print_device_info()

    # Run benchmarks
    benchmark_imports()
    benchmark_profiler_overhead()
    benchmark_ocr_cache()

    # Whisper benchmarks (may take longer)
    if "--full" in sys.argv:
        benchmark_whisper_loading()
    else:
        print("\n" + "=" * 70)
        print("Skipping Whisper model loading benchmarks (use --full to include)")
        print("=" * 70)

    print("\n" + "=" * 70)
    print("BENCHMARKS COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
