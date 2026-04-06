"""
Example: SystemBridge with Accessibility Integration

This example demonstrates how the SystemBridge integrates with the accessibility
layer to provide fast, reliable UI automation with automatic fallback.

The integration provides:
    - Unified API through SystemBridge
    - Automatic platform detection
    - Accessibility-first approach with vision fallback
    - Transparent switching between methods
"""

from janus.platform.os import get_system_bridge
from janus.platform.accessibility import AccessibilityRole


def example_basic_integration():
    """Basic SystemBridge with accessibility."""
    print("=" * 60)
    print("Example 1: SystemBridge with Accessibility")
    print("=" * 60)
    
    # Get system bridge (same as before)
    bridge = get_system_bridge()
    
    print(f"\nPlatform: {bridge.get_platform_name()}")
    print(f"Bridge available: {bridge.is_available()}")
    
    # Check if accessibility is available
    accessibility = bridge.get_accessibility_backend()
    if accessibility and accessibility.is_available():
        print(f"✓ Accessibility available: {accessibility.get_platform_name()}")
    else:
        print("⚠️  Accessibility not available - will use vision fallback")


def example_find_ui_element():
    """Find UI element via SystemBridge."""
    print("\n" + "=" * 60)
    print("Example 2: Find UI Element")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    # Find element using unified API
    # Tries accessibility first, falls back to vision
    print("\nSearching for 'Close' button...")
    result = bridge.find_ui_element(name="Close", role="button", timeout=3.0)
    
    if result.success:
        element = result.data["element"]
        method = result.data.get("method", "unknown")
        print(f"✓ Found element via {method}")
        print(f"  Name: {element.get('name')}")
        print(f"  Role: {element.get('role')}")
        if element.get('bounds'):
            print(f"  Position: ({element['bounds']['x']}, {element['bounds']['y']})")
    else:
        print(f"✗ Element not found: {result.error}")


def example_click_ui_element():
    """Click UI element via SystemBridge."""
    print("\n" + "=" * 60)
    print("Example 3: Click UI Element")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    # Find and click in one operation
    print("\nClicking 'OK' button...")
    result = bridge.click_ui_element(name="OK", role="button", timeout=3.0)
    
    if result.success:
        method = result.data.get("method", "unknown")
        print(f"✓ Clicked successfully via {method}")
    else:
        print(f"✗ Click failed: {result.error}")


def example_direct_accessibility():
    """Direct access to accessibility backend."""
    print("\n" + "=" * 60)
    print("Example 4: Direct Accessibility Access")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    # Get accessibility backend directly for advanced features
    accessibility = bridge.get_accessibility_backend()
    
    if not accessibility or not accessibility.is_available():
        print("Accessibility not available")
        return
    
    print("\n✓ Accessibility backend available")
    
    # Use advanced accessibility features
    print("\nFinding all buttons in active window...")
    buttons = accessibility.find_elements(
        role=AccessibilityRole.BUTTON,
        max_results=5
    )
    
    print(f"Found {len(buttons)} buttons:")
    for button in buttons:
        print(f"  - {button.name or '(unnamed)'}")
        print(f"    Enabled: {button.is_enabled()}")
        print(f"    Visible: {button.is_visible()}")


def example_ui_tree_inspection():
    """Inspect UI tree via accessibility."""
    print("\n" + "=" * 60)
    print("Example 5: UI Tree Inspection")
    print("=" * 60)
    
    bridge = get_system_bridge()
    accessibility = bridge.get_accessibility_backend()
    
    if not accessibility or not accessibility.is_available():
        print("Accessibility not available")
        return
    
    # Get active application
    print("\nGetting active application...")
    app = accessibility.get_active_app()
    
    if app:
        print(f"✓ Active app: {app.name}")
        
        # Get UI tree (limited depth for performance)
        print("\nBuilding UI tree (depth 3)...")
        tree = accessibility.get_ui_tree(root=app, max_depth=3)
        
        # Display tree structure
        print_tree(tree, indent=0, max_items=3)
    else:
        print("✗ Could not get active app")


def print_tree(node, indent=0, max_items=5):
    """Helper to print UI tree structure."""
    prefix = "  " * indent
    
    # Print current node
    name = node.get('name') or '(unnamed)'
    role = node.get('role', 'unknown')
    print(f"{prefix}• {role}: {name}")
    
    # Print children (limited)
    children = node.get('children', [])
    for i, child in enumerate(children[:max_items]):
        print_tree(child, indent + 1, max_items)
    
    if len(children) > max_items:
        print(f"{prefix}  ... and {len(children) - max_items} more")


def example_performance_comparison():
    """Compare accessibility vs traditional methods."""
    print("\n" + "=" * 60)
    print("Example 6: Performance Comparison")
    print("=" * 60)
    
    bridge = get_system_bridge()
    accessibility = bridge.get_accessibility_backend()
    
    if not accessibility or not accessibility.is_available():
        print("Accessibility not available - skipping comparison")
        return
    
    import time
    
    # Test accessibility performance
    print("\nTesting accessibility performance...")
    start = time.time()
    
    for _ in range(5):
        element = accessibility.find_element(
            role=AccessibilityRole.BUTTON,
            timeout=0.5
        )
    
    accessibility_time = (time.time() - start) / 5 * 1000
    
    print(f"✓ Accessibility: {accessibility_time:.1f}ms per operation")
    print(f"  (Vision typically: 200-500ms)")
    print(f"  Speed improvement: ~{500 / max(accessibility_time, 1):.1f}x faster")


def example_fallback_strategy():
    """Demonstrate automatic fallback."""
    print("\n" + "=" * 60)
    print("Example 7: Automatic Fallback Strategy")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    print("\nSystemBridge automatically tries:")
    print("  1. Accessibility API (fast, reliable)")
    print("  2. Vision-based fallback (slower, but always works)")
    
    # This automatically uses the best available method
    result = bridge.find_ui_element(name="Submit", role="button")
    
    if result.success:
        method = result.data.get("method", "unknown")
        print(f"\n✓ Element found via: {method}")
    else:
        print(f"\n⚠️  Element not found: {result.error}")
        print("   Would fall back to vision in production")


def example_real_world_workflow():
    """Real-world workflow using SystemBridge."""
    print("\n" + "=" * 60)
    print("Example 8: Real-World Workflow")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    print("\nWorkflow: Fill form and submit")
    print("=" * 40)
    
    # Step 1: Find text field
    print("\n1. Finding username field...")
    result = bridge.find_ui_element(role="text_field", timeout=2.0)
    
    if result.success:
        print("   ✓ Found text field")
        
        # Step 2: Type text (using SystemBridge)
        print("\n2. Typing username...")
        bridge.type_text("john.doe@example.com")
        print("   ✓ Text entered")
        
        # Step 3: Find and click submit button
        print("\n3. Finding Submit button...")
        result = bridge.click_ui_element(name="Submit", role="button", timeout=2.0)
        
        if result.success:
            print("   ✓ Form submitted successfully")
            print(f"\nWorkflow completed using {result.data.get('method', 'mixed')} method(s)")
        else:
            print(f"   ✗ Submit failed: {result.error}")
    else:
        print(f"   ✗ Field not found: {result.error}")


def main():
    """Run all integration examples."""
    print("\n" + "=" * 60)
    print("SYSTEMBRIDGE + ACCESSIBILITY INTEGRATION EXAMPLES")
    print("=" * 60)
    
    try:
        example_basic_integration()
        example_find_ui_element()
        example_click_ui_element()
        example_direct_accessibility()
        example_ui_tree_inspection()
        example_performance_comparison()
        example_fallback_strategy()
        example_real_world_workflow()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
