"""
Example: Using Accessibility API for UI Automation

This example demonstrates how to use the unified accessibility API
to interact with UI elements across Windows and macOS platforms.

The accessibility layer provides:
    - Fast, reliable element finding (vs vision-based)
    - Direct element interaction (click, focus, set value)
    - State retrieval (enabled, visible, focused)
    - UI tree inspection
"""

import time
from janus.platform.accessibility import (
    get_accessibility_backend,
    is_accessibility_available,
    AccessibilityRole,
)


def example_basic_usage():
    """Basic accessibility API usage."""
    print("=" * 60)
    print("Example 1: Basic Accessibility Usage")
    print("=" * 60)
    
    # Get the accessibility backend (auto-detects platform)
    backend = get_accessibility_backend()
    
    print(f"\nPlatform: {backend.get_platform_name()}")
    print(f"Available: {backend.is_available()}")
    
    if not backend.is_available():
        print("\n⚠️  Accessibility not available on this platform")
        print("   Falling back to vision-based automation...")
        return
    
    print("\n✓ Accessibility API is available")


def example_find_elements():
    """Finding UI elements."""
    print("\n" + "=" * 60)
    print("Example 2: Finding UI Elements")
    print("=" * 60)
    
    backend = get_accessibility_backend()
    
    if not backend.is_available():
        print("Accessibility not available")
        return
    
    # Find a specific button by name
    print("\nSearching for 'Close' button...")
    button = backend.find_element(
        name="Close",
        role=AccessibilityRole.BUTTON,
        timeout=3.0
    )
    
    if button:
        print(f"✓ Found button: {button.name}")
        print(f"  Role: {button.role.value}")
        print(f"  Enabled: {button.is_enabled()}")
        print(f"  Visible: {button.is_visible()}")
        if button.bounds:
            print(f"  Position: ({button.bounds['x']}, {button.bounds['y']})")
    else:
        print("✗ Button not found")
    
    # Find all buttons in active window
    print("\nFinding all buttons...")
    buttons = backend.find_elements(
        role=AccessibilityRole.BUTTON,
        max_results=10
    )
    
    print(f"Found {len(buttons)} buttons:")
    for btn in buttons[:5]:  # Show first 5
        print(f"  - {btn.name or '(unnamed)'} ({btn.role.value})")


def example_element_interaction():
    """Interacting with UI elements."""
    print("\n" + "=" * 60)
    print("Example 3: Element Interaction")
    print("=" * 60)
    
    backend = get_accessibility_backend()
    
    if not backend.is_available():
        print("Accessibility not available")
        return
    
    # Find a text field
    print("\nSearching for text field...")
    text_field = backend.find_element(
        role=AccessibilityRole.TEXT_FIELD,
        timeout=3.0
    )
    
    if text_field:
        print(f"✓ Found text field: {text_field.name or '(unnamed)'}")
        
        # Focus the field
        result = backend.focus_element(text_field)
        if result.success:
            print("✓ Field focused")
            
            # Set value
            result = backend.set_value(text_field, "Hello from Accessibility API!")
            if result.success:
                print("✓ Value set successfully")
            else:
                print(f"✗ Failed to set value: {result.error}")
        else:
            print(f"✗ Failed to focus: {result.error}")
    else:
        print("✗ Text field not found")


def example_ui_tree():
    """Inspecting UI tree."""
    print("\n" + "=" * 60)
    print("Example 4: UI Tree Inspection")
    print("=" * 60)
    
    backend = get_accessibility_backend()
    
    if not backend.is_available():
        print("Accessibility not available")
        return
    
    # Get active application
    print("\nGetting active application...")
    app = backend.get_active_app()
    
    if app:
        print(f"✓ Active app: {app.name}")
        
        # Get app windows
        windows = backend.get_app_windows()
        print(f"\nApp has {len(windows)} window(s):")
        
        for window in windows[:3]:  # Show first 3
            print(f"\n  Window: {window.name}")
            
            # Get window children (top-level elements)
            children = backend.get_children(window)
            print(f"  Children: {len(children)}")
            
            for child in children[:5]:  # Show first 5
                print(f"    - {child.role.value}: {child.name or '(unnamed)'}")
    else:
        print("✗ Could not get active app")


def example_focused_element():
    """Working with focused element."""
    print("\n" + "=" * 60)
    print("Example 5: Focused Element")
    print("=" * 60)
    
    backend = get_accessibility_backend()
    
    if not backend.is_available():
        print("Accessibility not available")
        return
    
    print("\nGetting currently focused element...")
    focused = backend.get_focused_element()
    
    if focused:
        print(f"✓ Focused element: {focused.name or '(unnamed)'}")
        print(f"  Role: {focused.role.value}")
        print(f"  Value: {focused.value}")
        
        # Get parent
        parent = backend.get_parent(focused)
        if parent:
            print(f"  Parent: {parent.name or '(unnamed)'} ({parent.role.value})")
    else:
        print("✗ No element is currently focused")


def example_performance_comparison():
    """Compare accessibility vs vision performance."""
    print("\n" + "=" * 60)
    print("Example 6: Performance Comparison")
    print("=" * 60)
    
    backend = get_accessibility_backend()
    
    if not backend.is_available():
        print("Accessibility not available - skipping performance test")
        return
    
    # Measure accessibility-based element finding
    print("\nMeasuring accessibility performance...")
    start = time.time()
    
    for _ in range(10):
        button = backend.find_element(
            role=AccessibilityRole.BUTTON,
            timeout=0.5
        )
    
    accessibility_time = (time.time() - start) / 10 * 1000  # ms per operation
    
    print(f"✓ Accessibility: {accessibility_time:.1f}ms per find operation")
    print(f"  (Vision-based typically: 200-500ms)")
    print(f"  Speed improvement: ~{500 / accessibility_time:.1f}x faster")


def example_fallback_strategy():
    """Demonstrate fallback to vision when accessibility unavailable."""
    print("\n" + "=" * 60)
    print("Example 7: Fallback Strategy")
    print("=" * 60)
    
    # Check if accessibility is available
    if is_accessibility_available():
        print("\n✓ Accessibility available - using fast element finding")
        
        backend = get_accessibility_backend()
        element = backend.find_element(name="OK", role=AccessibilityRole.BUTTON)
        
        if element:
            print(f"  Found via accessibility: {element.name}")
            backend.click_element(element)
        else:
            print("  Element not found - falling back to vision...")
            # use_vision_fallback()
    else:
        print("\n⚠️  Accessibility not available - using vision-only mode")
        # use_vision_fallback()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("ACCESSIBILITY API EXAMPLES")
    print("=" * 60)
    
    try:
        example_basic_usage()
        example_find_elements()
        example_element_interaction()
        example_ui_tree()
        example_focused_element()
        example_performance_comparison()
        example_fallback_strategy()
        
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
