"""
Benchmark script for OmniParser UI element detection
TICKET-CLEANUP-VISION: Updated to use only OmniParser (Florence-2 is inside OmniParser)

NOTE: This benchmark file is being simplified to only test OmniParser since
      Florence-2 standalone has been removed. OmniParser includes Florence-2
      internally, so there's no longer a need to compare them separately.

Usage:
    python examples/benchmark_vision_models.py

Tests:
- Detection accuracy (precision for buttons/fields/icons)
- Latency (inference time)  
- Model size
- Memory usage

Outputs a performance report for OmniParser unified vision engine.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image
    import torch
except ImportError as e:
    print(f"Error: Missing dependencies. Install with: pip install -r requirements-vision.txt")
    print(f"       Or compile from source: pip-compile requirements-vision.in")
    print(f"Details: {e}")
    sys.exit(1)

from janus.vision.omniparser_adapter import OmniParserVisionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VisionModelBenchmark:
    """Benchmark OmniParser vision model for UI element detection"""
    
    def __init__(self, test_images_dir: str = None):
        """
        Initialize benchmark
        
        Args:
            test_images_dir: Directory containing test UI screenshots
        """
        self.test_images_dir = test_images_dir or "artifacts/test_screenshots"
        self.results: Dict[str, List[Dict[str, Any]]] = {
            "omniparser": [],
        }
        
        # Initialize OmniParser (includes Florence-2)
        logger.info("Initializing OmniParser...")
        self.omniparser = None
        
        try:
            self.omniparser = OmniParserVisionEngine(lazy_load=False)
            logger.info("✓ OmniParser initialized (includes Florence-2 + YOLOv8)")
        except Exception as e:
            logger.warning(f"OmniParser initialization failed: {e}")
    
    def create_test_image(self, width: int = 1920, height: int = 1080) -> Image.Image:
        """Create a synthetic test image with UI elements"""
        from PIL import ImageDraw, ImageFont
        
        # Create blank image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw some UI elements (buttons, text, etc.)
        # Button 1
        draw.rectangle([100, 100, 200, 140], fill='blue', outline='darkblue')
        draw.text((120, 115), "Submit", fill='white')
        
        # Button 2
        draw.rectangle([100, 160, 200, 200], fill='green', outline='darkgreen')
        draw.text((120, 175), "Cancel", fill='white')
        
        # Text field
        draw.rectangle([100, 220, 300, 250], fill='white', outline='gray')
        draw.text((110, 228), "Enter text here...", fill='gray')
        
        # Icon/Image placeholder
        draw.ellipse([350, 100, 400, 150], fill='orange', outline='darkorange')
        
        return img
    
    def benchmark_detection(self, image: Image.Image) -> Dict[str, Any]:
        """
        Benchmark object detection on an image using OmniParser
        
        Args:
            image: PIL Image to test
            
        Returns:
            Dictionary with benchmark results
        """
        engine = self.omniparser
        
        if engine is None:
            return {
                "error": "OmniParser not available",
                "duration_ms": 0,
                "count": 0,
            }
        
        # Warm-up run
        try:
            engine.detect_objects(image)
        except Exception as e:
            logger.warning(f"Warm-up failed for {model_name}: {e}")
        
        # Benchmark run
        start_time = time.time()
        try:
            result = engine.detect_objects(image)
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "model": model_name,
                "duration_ms": duration_ms,
                "count": result.get("count", 0),
                "objects": result.get("objects", []),
                "method": result.get("method", "unknown"),
            }
        except Exception as e:
            return {
                "error": str(e),
                "model": model_name,
                "duration_ms": int((time.time() - start_time) * 1000),
                "count": 0,
            }
    
    def benchmark_ocr(self, image: Image.Image, model_name: str) -> Dict[str, Any]:
        """
        Benchmark OCR/text extraction
        
        Args:
            image: PIL Image to test
            model_name: "florence2" or "omniparser"
            
        Returns:
            Dictionary with OCR benchmark results
        """
        engine = self.florence if model_name == "florence2" else self.omniparser
        
        if engine is None:
            return {"error": f"{model_name} not available", "duration_ms": 0}
        
        start_time = time.time()
        try:
            result = engine.extract_text(image, with_regions=True)
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "model": model_name,
                "duration_ms": duration_ms,
                "text_length": len(result.get("text", "")),
                "regions_count": len(result.get("regions", [])),
                "method": result.get("method", "unknown"),
            }
        except Exception as e:
            return {
                "error": str(e),
                "model": model_name,
                "duration_ms": int((time.time() - start_time) * 1000),
            }
    
    def run_benchmark(self, num_iterations: int = 5):
        """
        Run full benchmark suite
        
        Args:
            num_iterations: Number of iterations for each test
        """
        logger.info(f"Running benchmark with {num_iterations} iterations...")
        
        # Create test image
        test_image = self.create_test_image()
        logger.info(f"Created test image: {test_image.size}")
        
        # Benchmark detection
        logger.info("\n" + "="*60)
        logger.info("OBJECT DETECTION BENCHMARK")
        logger.info("="*60)
        
        for model_name in ["florence2", "omniparser"]:
            logger.info(f"\nBenchmarking {model_name}...")
            for i in range(num_iterations):
                result = self.benchmark_detection(test_image, model_name)
                self.results[model_name].append(result)
                logger.info(f"  Iteration {i+1}: {result.get('duration_ms', 0)}ms, {result.get('count', 0)} objects")
        
        # Benchmark OCR
        logger.info("\n" + "="*60)
        logger.info("OCR BENCHMARK")
        logger.info("="*60)
        
        for model_name in ["florence2", "omniparser"]:
            logger.info(f"\nBenchmarking {model_name} OCR...")
            for i in range(num_iterations):
                result = self.benchmark_ocr(test_image, model_name)
                logger.info(f"  Iteration {i+1}: {result.get('duration_ms', 0)}ms")
    
    def print_summary(self):
        """Print benchmark summary"""
        logger.info("\n" + "="*60)
        logger.info("BENCHMARK SUMMARY")
        logger.info("="*60)
        
        for model_name in ["florence2", "omniparser"]:
            results = self.results[model_name]
            if not results:
                logger.info(f"\n{model_name.upper()}: No results")
                continue
            
            # Filter out errors
            valid_results = [r for r in results if "error" not in r]
            if not valid_results:
                logger.info(f"\n{model_name.upper()}: All runs failed")
                continue
            
            # Calculate statistics
            durations = [r["duration_ms"] for r in valid_results]
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            logger.info(f"\n{model_name.upper()}:")
            logger.info(f"  Average latency: {avg_duration:.1f}ms")
            logger.info(f"  Min latency: {min_duration}ms")
            logger.info(f"  Max latency: {max_duration}ms")
            logger.info(f"  Successful runs: {len(valid_results)}/{len(results)}")
        
        # Model size comparison
        logger.info("\n" + "="*60)
        logger.info("MODEL SIZE COMPARISON")
        logger.info("="*60)
        
        if self.florence:
            info = self.florence.get_info()
            logger.info(f"\nFlorence-2:")
            logger.info(f"  Model: {info.get('model_id', 'unknown')}")
            logger.info(f"  Device: {info.get('device', 'unknown')}")
            logger.info(f"  Available: {info.get('available', False)}")
        
        if self.omniparser:
            info = self.omniparser.get_info()
            logger.info(f"\nOmniParser:")
            logger.info(f"  Detection: {info.get('detection_model', 'unknown')}")
            logger.info(f"  Caption: {info.get('caption_model', 'unknown')}")
            logger.info(f"  Device: {info.get('device', 'unknown')}")
            logger.info(f"  Available: {info.get('available', False)}")
        
        logger.info("\n" + "="*60)
        logger.info("RECOMMENDATION")
        logger.info("="*60)
        
        # Calculate performance improvement
        florence_results = [r for r in self.results["florence2"] if "error" not in r]
        omni_results = [r for r in self.results["omniparser"] if "error" not in r]
        
        if florence_results and omni_results:
            florence_avg = sum(r["duration_ms"] for r in florence_results) / len(florence_results)
            omni_avg = sum(r["duration_ms"] for r in omni_results) / len(omni_results)
            
            if omni_avg < florence_avg:
                improvement = ((florence_avg - omni_avg) / florence_avg) * 100
                logger.info(f"\n✓ OmniParser is {improvement:.1f}% faster than Florence-2")
                logger.info("  Recommended: Use OmniParser for UI element detection")
            else:
                degradation = ((omni_avg - florence_avg) / florence_avg) * 100
                logger.info(f"\n⚠ OmniParser is {degradation:.1f}% slower than Florence-2")
                logger.info("  Recommended: Keep Florence-2 for now, or optimize OmniParser")


def main():
    """Main benchmark entry point"""
    parser = argparse.ArgumentParser(description="Benchmark vision models for UI detection")
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations per test (default: 5)"
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        default=None,
        help="Directory containing test screenshots (optional)"
    )
    
    args = parser.parse_args()
    
    # Run benchmark
    benchmark = VisionModelBenchmark(test_images_dir=args.test_dir)
    benchmark.run_benchmark(num_iterations=args.iterations)
    benchmark.print_summary()


if __name__ == "__main__":
    main()
