"""
Example: Using OmniParser for UI Element Detection

This example demonstrates how to use the OmniParser unified vision engine.
TICKET-CLEANUP-VISION: Florence-2 is now included inside OmniParser.

OmniParser provides:
- Unified detection (YOLOv8 + Florence-2)
- High precision for UI elements (>95%)
- Specialized for buttons, icons, text fields
- Integrated OCR and captioning

Usage:
    python examples/example_omniparser_ui_detection.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)

from janus.vision.omniparser_adapter import OmniParserVisionEngine
from janus.vision.visual_grounding_engine import VisualGroundingEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_ui(width=1200, height=800):
    """Create a sample UI screenshot for testing"""
    img = Image.new('RGB', (width, height), color='#f0f0f0')
    draw = ImageDraw.Draw(img)
    
    # Draw header
    draw.rectangle([0, 0, width, 60], fill='#2c3e50')
    draw.text((20, 20), "Sample Application", fill='white')
    
    # Draw buttons
    buttons = [
        (50, 100, 150, 40, "Submit", '#3498db'),
        (200, 100, 150, 40, "Cancel", '#95a5a6'),
        (350, 100, 150, 40, "Help", '#e74c3c'),
    ]
    
    for x, y, w, h, text, color in buttons:
        draw.rectangle([x, y, x+w, y+h], fill=color, outline='#2c3e50', width=2)
        # Center text (approximate)
        text_bbox = draw.textbbox((0, 0), text)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = x + (w - text_width) // 2
        draw.text((text_x, y + 12), text, fill='white')
    
    # Draw text fields
    fields = [
        (50, 200, 300, 35, "Email address..."),
        (50, 250, 300, 35, "Password..."),
    ]
    
    for x, y, w, h, placeholder in fields:
        draw.rectangle([x, y, x+w, y+h], fill='white', outline='#bdc3c7', width=1)
        draw.text((x + 10, y + 10), placeholder, fill='#95a5a6')
    
    # Draw icons (simple circles)
    icons = [
        (500, 100, 40, '#e67e22'),  # Settings icon
        (560, 100, 40, '#9b59b6'),  # Profile icon
        (620, 100, 40, '#1abc9c'),  # Search icon
    ]
    
    for x, y, size, color in icons:
        draw.ellipse([x, y, x+size, y+size], fill=color, outline='#2c3e50', width=2)
    
    # Draw some text labels
    draw.text((50, 320), "Dashboard Overview", fill='#2c3e50')
    draw.text((50, 360), "Recent activity and notifications will appear here.", fill='#7f8c8d')
    
    return img


def example_1_basic_detection():
    """Example 1: Basic UI element detection with OmniParser"""
    logger.info("=" * 60)
    logger.info("Example 1: Basic UI Element Detection")
    logger.info("=" * 60)
    
    # Create OmniParser engine
    logger.info("Initializing OmniParser engine...")
    engine = OmniParserVisionEngine(
        device="auto",  # Auto-detect best device (MPS/CUDA/CPU)
        confidence_threshold=0.3,
        lazy_load=False,
    )
    
    if not engine.is_available():
        logger.warning("OmniParser not available (dependencies missing)")
        logger.warning("Install with: pip install ultralytics")
        return
    
    # Create sample UI
    logger.info("Creating sample UI...")
    screenshot = create_sample_ui()
    
    # Detect UI elements
    logger.info("Detecting UI elements...")
    result = engine.detect_objects(screenshot)
    
    # Display results
    logger.info(f"\nDetection Results:")
    logger.info(f"  Method: {result.get('method', 'unknown')}")
    logger.info(f"  Duration: {result.get('duration_ms', 0)}ms")
    logger.info(f"  Elements found: {result.get('count', 0)}")
    
    for i, obj in enumerate(result.get('objects', []), 1):
        logger.info(f"\n  Element {i}:")
        logger.info(f"    Type: {obj.get('label', 'unknown')}")
        logger.info(f"    Confidence: {obj.get('confidence', 0):.2f}")
        logger.info(f"    Position: {obj.get('center', (0, 0))}")
        logger.info(f"    Size: {obj.get('width', 0)}x{obj.get('height', 0)}")


def example_2_visual_grounding():
    """Example 2: Using OmniParser with Visual Grounding Engine"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Visual Grounding with OmniParser")
    logger.info("=" * 60)
    
    # Create Visual Grounding Engine with OmniParser
    logger.info("Initializing Visual Grounding Engine with OmniParser...")
    grounding = VisualGroundingEngine(
        use_omniparser=True,
        min_confidence=0.3,
    )
    
    if not grounding.is_available():
        logger.warning("Visual Grounding not available")
        return
    
    # Create sample UI
    screenshot = create_sample_ui()
    
    # Detect interactive elements
    logger.info("Detecting interactive elements...")
    elements = grounding.detect_interactive_elements(screenshot)
    
    # Display results
    logger.info(f"\nFound {len(elements)} interactive elements:")
    
    for element in elements:
        logger.info(f"\n  [ID {element.id}] {element.type.upper()}")
        logger.info(f"    Text: '{element.text}'")
        logger.info(f"    Position: ({element.center_x}, {element.center_y})")
        logger.info(f"    Confidence: {element.confidence:.2f}")
    
    # Generate LLM-friendly list
    logger.info("\n" + "-" * 60)
    logger.info("LLM Format:")
    logger.info("-" * 60)
    llm_list = grounding.generate_llm_list(elements)
    logger.info(llm_list)


def example_3_omniparser_performance():
    """Example 3: OmniParser Performance Test"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: OmniParser Performance Test")
    logger.info("=" * 60)
    logger.info("(Florence-2 is included inside OmniParser)")
    
    screenshot = create_sample_ui()
    
    # Test OmniParser
    logger.info("\nTesting OmniParser (YOLOv8 + Florence-2)...")
    try:
        omni_engine = OmniParserVisionEngine(lazy_load=False)
        if omni_engine.is_available():
            # Test detection
            omni_result = omni_engine.detect_objects(screenshot)
            logger.info(f"  Detection: {omni_result.get('count', 0)} elements in {omni_result.get('duration_ms', 0)}ms")
            
            # Test captioning
            caption_result = omni_engine.describe(screenshot)
            logger.info(f"  Caption: \"{caption_result.get('description', '')}\" in {caption_result.get('duration_ms', 0)}ms")
            
            # Test OCR
            ocr_result = omni_engine.extract_text(screenshot)
            logger.info(f"  OCR: \"{ocr_result.get('text', '')[:50]}...\" in {ocr_result.get('duration_ms', 0)}ms")
        else:
            logger.info("  OmniParser: Not available")
    except Exception as e:
        logger.warning(f"  OmniParser: Error - {e}")
    
    logger.info("\nFor comprehensive benchmarking, run:")
    logger.info("  python examples/benchmark_vision_models.py")


def main():
    """Run all examples"""
    logger.info("OmniParser UI Detection Examples\n")
    
    try:
        example_1_basic_detection()
        example_2_visual_grounding()
        example_3_omniparser_performance()
        
        logger.info("\n" + "=" * 60)
        logger.info("Examples completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Run benchmark: python examples/benchmark_vision_models.py")
        logger.info("2. Read docs: docs/developer/OMNIPARSER_MIGRATION.md")
        logger.info("3. Integrate into your application")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
