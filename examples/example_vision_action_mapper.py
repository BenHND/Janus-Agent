"""
Example demonstrating Vision-to-Action Mapping (VAM)

This shows how the vision action mapper creates a universal layer
between vision (OCR + bounding boxes) and physical actions.

The agent can now:
1. Click on any button detected by vision
2. Execute generic actions without application-specific adapters
3. Automatically retry with scroll on failures
4. Verify actions completed successfully

Note: This example requires vision dependencies to be installed.
Run: pip install -r requirements-vision.txt
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if vision dependencies are available
try:
    from janus.vision import ElementType, VisionActionMapper, VisualAttributes

    VISION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Vision dependencies not available: {e}")
    print("This is expected in CI/test environments without full dependencies.")
    print("Install vision dependencies with: pip install -r requirements-vision.txt")
    VISION_AVAILABLE = False


def example_basic_vision_actions():
    """Example: Basic vision-based actions"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("=" * 60)
    print("Example 1: Basic Vision-Based Actions")
    print("=" * 60)

    # Initialize the mapper
    mapper = VisionActionMapper(
        enable_auto_scroll=True,
        enable_auto_retry=True,
        max_retries=3,
        enable_post_action_verification=True,
    )

    print("\n1. Click on a button using vision")
    print("   mapper.click_viz('Submit')")
    # result = mapper.click_viz("Submit")
    # print(f"   Result: {result.success}, {result.message}")

    print("\n2. Select text using vision")
    print("   mapper.select_viz('Important Text')")
    # result = mapper.select_viz("Important Text")
    # print(f"   Result: {result.success}, {result.message}")

    print("\n3. Extract text using vision")
    print("   mapper.extract_viz('Error Message')")
    # result = mapper.extract_viz("Error Message")
    # print(f"   Result: {result.success}, Extracted: {result.element.text if result.element else 'None'}")

    print("\n✅ These actions work on ANY application - no adapter needed!")


def example_find_by_text():
    """Example: Finding elements by text"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 2: Finding Elements by Text")
    print("=" * 60)

    mapper = VisionActionMapper()

    print("\n1. Find with exact match")
    print("   element = mapper.find_element_by_text('Login')")
    # element = mapper.find_element_by_text("Login")
    # if element:
    #     print(f"   Found: {element.text} at ({element.center_x}, {element.center_y})")

    print("\n2. Find with fuzzy match")
    print("   element = mapper.find_element_by_text('Log', fuzzy_match=True)")
    # element = mapper.find_element_by_text("Log", fuzzy_match=True)
    # if element:
    #     print(f"   Found: {element.text} (fuzzy matched)")

    print("\n3. Find with automatic scroll")
    print("   element = mapper.find_element_by_text('Footer', scroll_if_not_found=True)")
    # element = mapper.find_element_by_text("Footer", scroll_if_not_found=True)
    # if element:
    #     print(f"   Found: {element.text} (after scrolling)")

    print("\n✅ Fuzzy matching + auto-scroll = robust element finding!")


def example_find_by_attributes():
    """Example: Finding elements by visual attributes"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 3: Finding Elements by Attributes")
    print("=" * 60)

    mapper = VisionActionMapper()

    print("\n1. Find button by size")
    attrs = VisualAttributes(
        element_type=ElementType.BUTTON,
        size=(100, 40),  # Approximate button size
        confidence_threshold=80.0,
    )
    print(f"   attrs = VisualAttributes(type=BUTTON, size=(100, 40))")
    print(f"   element = mapper.find_element_by_attributes(attrs)")
    # element = mapper.find_element_by_attributes(attrs)

    print("\n2. Find element by color")
    attrs = VisualAttributes(color=(255, 0, 0), confidence_threshold=75.0)  # Red color
    print(f"   attrs = VisualAttributes(color=(255, 0, 0))")
    print(f"   element = mapper.find_element_by_attributes(attrs)")
    # element = mapper.find_element_by_attributes(attrs)

    print("\n3. Find element in specific region")
    attrs = VisualAttributes(
        position=(0, 0, 800, 200),  # Top region of screen
        element_type=ElementType.MENU,
        confidence_threshold=70.0,
    )
    print(f"   attrs = VisualAttributes(position=(0, 0, 800, 200), type=MENU)")
    print(f"   element = mapper.find_element_by_attributes(attrs)")
    # element = mapper.find_element_by_attributes(attrs)

    print("\n✅ Visual attributes enable finding elements without text!")


def example_coordinate_conversion():
    """Example: Bounding box to screen coordinate conversion"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 4: Coordinate Conversion")
    print("=" * 60)

    mapper = VisionActionMapper()

    print("\n1. Convert bbox to screen coordinates")
    bbox = (100, 200, 80, 40)  # x, y, width, height
    screen_coords = mapper.bbox_to_screen_coords(bbox)
    print(f"   bbox = {bbox}")
    print(f"   screen_coords = {screen_coords}")

    print("\n2. Convert with region offset")
    region_offset = (50, 100)  # Region starts at (50, 100)
    screen_coords = mapper.bbox_to_screen_coords(bbox, region_offset)
    print(f"   bbox = {bbox}, offset = {region_offset}")
    print(f"   screen_coords = {screen_coords}")

    print("\n3. Get center point for clicking")
    center = mapper.get_element_center(bbox)
    print(f"   bbox = {bbox}")
    print(f"   center = {center}")

    print("\n✅ Easy conversion from OCR bounding boxes to clickable coordinates!")


def example_retry_and_verification():
    """Example: Automatic retry and post-action verification"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 5: Retry and Verification")
    print("=" * 60)

    print("\n1. Action with automatic retry")
    mapper = VisionActionMapper(enable_auto_retry=True, max_retries=3)
    print("   mapper = VisionActionMapper(enable_auto_retry=True, max_retries=3)")
    print("   result = mapper.click_viz('Submit')")
    # result = mapper.click_viz("Submit")
    # print(f"   Success: {result.success}, Retries: {result.retry_count}")

    print("\n2. Action with post-action verification")
    mapper = VisionActionMapper(enable_post_action_verification=True)
    print("   mapper = VisionActionMapper(enable_post_action_verification=True)")
    print("   result = mapper.click_viz('OK', verify=True)")
    # result = mapper.click_viz("OK", verify=True)
    # if result.verification:
    #     print(f"   Verified: {result.verification['verified']}")
    #     print(f"   Confidence: {result.verification['confidence']}")

    print("\n✅ Automatic retry + verification = reliable actions!")


def example_statistics():
    """Example: Tracking statistics"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 6: Statistics Tracking")
    print("=" * 60)

    mapper = VisionActionMapper()

    print("\nPerforming several actions...")
    print("   mapper.extract_viz('Text1')")
    print("   mapper.click_viz('Button1', verify=False)")
    print("   mapper.extract_viz('Text2')")

    # Simulate some actions
    # mapper.extract_viz("Text1")
    # mapper.click_viz("Button1", verify=False)
    # mapper.extract_viz("Text2")

    print("\nGetting statistics...")
    stats = mapper.get_stats()
    print(f"   Total actions: {stats['total_actions']}")
    print(f"   Successful: {stats['successful_actions']}")
    print(f"   Failed: {stats['failed_actions']}")
    print(f"   Success rate: {stats['success_rate']:.2%}")
    print(f"   Avg retries: {stats['avg_retries']:.2f}")
    print(f"   Scrolls performed: {stats['scrolls_performed']}")

    print("\n✅ Track performance and optimize your vision-based workflows!")


def example_universal_agent():
    """Example: Universal agent without application-specific adapters"""
    if not VISION_AVAILABLE:
        print("\n⚠️  Skipping: Vision dependencies not available")
        return

    print("\n" + "=" * 60)
    print("Example 7: Universal Agent Capability")
    print("=" * 60)

    mapper = VisionActionMapper(
        enable_auto_scroll=True, enable_auto_retry=True, enable_post_action_verification=True
    )

    print("\n🎯 The agent can now work on ANY application:")
    print()
    print("   # Web browser")
    print("   mapper.click_viz('Sign In')")
    print("   mapper.select_viz('Email field')")
    print()
    print("   # Native app")
    print("   mapper.click_viz('New Document')")
    print("   mapper.extract_viz('Status: Ready')")
    print()
    print("   # System dialog")
    print("   mapper.click_viz('Allow')")
    print("   mapper.click_viz('OK')")
    print()
    print("   # Any UI element visible on screen")
    print("   mapper.click_viz('Close popup')")
    print("   mapper.select_viz('Important message')")

    print("\n✅ No adapter needed - vision makes the agent truly universal!")
    print("✅ Works with ANY application that displays text or UI elements!")
    print("✅ Automatic retry with scroll for reliability!")
    print("✅ Post-action verification ensures success!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("VISION-TO-ACTION MAPPING (VAM) EXAMPLES")
    print("Bridging the gap: Vision → Action")
    print("=" * 60)

    if not VISION_AVAILABLE:
        print("\n⚠️  Vision dependencies not available")
        print("This example demonstrates the API but requires full dependencies.")
        print("Install with: pip install -r requirements-vision.txt")
        print("\n" + "=" * 60)
        sys.exit(0)

    example_basic_vision_actions()
    example_find_by_text()
    example_find_by_attributes()
    example_coordinate_conversion()
    example_retry_and_verification()
    example_statistics()
    example_universal_agent()

    print("\n" + "=" * 60)
    print("🎉 Vision-to-Action Mapping makes Janus UNIVERSAL!")
    print("=" * 60)
    print("\nKey capabilities:")
    print("  ✅ Find elements by text (exact, fuzzy, with scroll)")
    print("  ✅ Find elements by attributes (color, size, position)")
    print("  ✅ Vision-based actions (click_viz, select_viz, extract_viz)")
    print("  ✅ Automatic retry on failures")
    print("  ✅ Automatic scroll to find elements")
    print("  ✅ Post-action verification")
    print("  ✅ Works on ANY application")
    print("  ✅ No application-specific adapters needed")
    print("\n" + "=" * 60)
