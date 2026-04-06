#!/usr/bin/env python3
"""
Example demonstrating TICKET-013 performance optimizations
Shows GPU support, lazy loading, profiling, and smart caching
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.utils.benchmark import quick_benchmark
from janus.utils.gpu_utils import get_best_device, print_device_info
from janus.utils.profiler import get_memory_tracker, get_profiler, profile


def demo_gpu_detection():
    """Demonstrate GPU device detection"""
    print("\n" + "=" * 70)
    print("DEMO: GPU Device Detection")
    print("=" * 70)

    # Print detailed device info
    print_device_info()

    # Get best device
    device = get_best_device()
    print(f"\nBest available device: {device.name}")
    print(f"Device type: {device.device_type}")


def demo_lazy_loading():
    """Demonstrate lazy loading of Whisper model"""
    print("\n" + "=" * 70)
    print("DEMO: Lazy Loading")
    print("=" * 70)

    from janus.io.stt.whisper_stt import WhisperSTT

    # Create STT with lazy loading (model not loaded yet)
    print("\n1. Creating WhisperSTT with lazy_load=True...")
    with profile("stt_init_lazy"):
        stt_lazy = WhisperSTT(
            model_size="tiny",
            lazy_load=True,  # Don't load model yet
            enable_corrections=False,
            enable_normalization=False,
            enable_logging=False,
        )

    print("   ✓ WhisperSTT created (model not loaded)")

    # Compare with eager loading
    print("\n2. Creating WhisperSTT with lazy_load=False...")
    with profile("stt_init_eager"):
        stt_eager = WhisperSTT(
            model_size="tiny",
            lazy_load=False,  # Load model immediately
            enable_corrections=False,
            enable_normalization=False,
            enable_logging=False,
        )

    print("   ✓ WhisperSTT created (model loaded)")

    # Print timing comparison
    profiler = get_profiler()
    profiler.print_report()


def demo_profiling():
    """Demonstrate profiling capabilities"""
    print("\n" + "=" * 70)
    print("DEMO: Performance Profiling")
    print("=" * 70)

    import time

    from janus.utils.profiler import timed

    # Use context manager
    print("\n1. Using context manager:")
    with profile("example_operation"):
        time.sleep(0.1)  # Simulate work
        print("   Doing some work...")

    # Use decorator
    @timed("decorated_function")
    def slow_function():
        time.sleep(0.05)
        return "result"

    print("\n2. Using decorator:")
    result = slow_function()
    print(f"   Function returned: {result}")

    # Multiple calls to show statistics
    print("\n3. Multiple calls to track statistics:")
    for i in range(5):
        with profile("repeated_operation"):
            time.sleep(0.02)

    # Print profiling report
    profiler = get_profiler()
    profiler.print_report()


def demo_memory_tracking():
    """Demonstrate memory tracking"""
    print("\n" + "=" * 70)
    print("DEMO: Memory Tracking")
    print("=" * 70)

    memory_tracker = get_memory_tracker()

    if not memory_tracker.available:
        print("\npsutil not installed, skipping memory tracking demo")
        return

    print("\n1. Current memory usage:")
    mem_info = memory_tracker.get_memory_info()
    print(f"   RSS: {mem_info['rss_mb']:.2f} MB")
    print(f"   VMS: {mem_info['vms_mb']:.2f} MB")
    print(f"   Percent: {mem_info['percent']:.2f}%")

    print("\n2. Tracking memory delta:")
    with memory_tracker.track("allocate_memory"):
        # Allocate some memory
        data = [0] * (1024 * 1024)  # ~8 MB
        import time

        time.sleep(0.1)


def demo_smart_cache():
    """Demonstrate smart OCR caching with perceptual hashing"""
    print("\n" + "=" * 70)
    print("DEMO: Smart OCR Cache")
    print("=" * 70)

    try:
        from PIL import Image, ImageDraw

        from janus.vision.cache import OCRCache

        # Create cache
        cache = OCRCache(use_perceptual_hash=True)

        # Create a test image
        print("\n1. Creating test image...")
        img1 = Image.new("RGB", (200, 100), color="white")
        draw = ImageDraw.Draw(img1)
        draw.text((10, 40), "Hello World", fill="black")

        # Cache OCR result
        print("2. Caching OCR result...")
        cache.set(img1, {"text": "Hello World", "confidence": 0.95})

        # Exact match
        print("3. Testing exact match...")
        result = cache.get(img1)
        print(f"   Result: {result}")

        # Create similar image (slightly different)
        print("4. Creating similar image (slightly shifted)...")
        img2 = Image.new("RGB", (200, 100), color="white")
        draw2 = ImageDraw.Draw(img2)
        draw2.text((12, 42), "Hello World", fill="black")  # Slightly shifted

        # Try to get similar image (should match with perceptual hash)
        print("5. Testing similarity matching...")
        result = cache.get(img2, use_similarity=True)
        if result:
            print(f"   ✓ Found similar cached result: {result}")
        else:
            print(f"   ✗ No similar match found")

        # Show cache stats
        print("\n6. Cache statistics:")
        stats = cache.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

    except ImportError as e:
        print(f"\nSkipping smart cache demo: {e}")


def demo_benchmarking():
    """Demonstrate benchmarking utilities"""
    print("\n" + "=" * 70)
    print("DEMO: Benchmarking")
    print("=" * 70)

    import time

    print("\n1. Quick benchmark:")

    def test_function():
        time.sleep(0.01)

    quick_benchmark("test_function", test_function, iterations=10)

    print("\n2. Comparing implementations:")

    # Implementation 1: List comprehension
    def impl1():
        result = [x**2 for x in range(1000)]

    # Implementation 2: Map
    def impl2():
        result = list(map(lambda x: x**2, range(1000)))

    quick_benchmark("list_comprehension", impl1, iterations=100)
    quick_benchmark("map_function", impl2, iterations=100)


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("TICKET-013: PERFORMANCE OPTIMIZATION DEMOS")
    print("=" * 70)

    # Run demos
    demo_gpu_detection()
    demo_profiling()
    demo_memory_tracking()
    demo_smart_cache()
    demo_benchmarking()

    # Lazy loading demo (optional, requires whisper)
    if "--full" in sys.argv:
        demo_lazy_loading()
    else:
        print("\n" + "=" * 70)
        print("Skipping lazy loading demo (use --full to include)")
        print("=" * 70)

    print("\n" + "=" * 70)
    print("ALL DEMOS COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
