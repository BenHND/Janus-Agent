"""
Example: Using SystemBridge for Cross-Platform System Operations

TICKET-AUDIT-007: System Abstraction Layer

This example demonstrates how to use the SystemBridge abstraction layer
for platform-agnostic system operations.
"""

import asyncio
import time
from janus.platform.os import get_system_bridge, SystemBridgeStatus


def example_basic_usage():
    """Basic SystemBridge usage."""
    print("=" * 60)
    print("Example 1: Basic SystemBridge Usage")
    print("=" * 60)
    
    # Get the system bridge (singleton)
    bridge = get_system_bridge()
    
    # Check if available
    print(f"\nPlatform: {bridge.get_platform_name()}")
    print(f"Available: {bridge.is_available()}")
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    # Get running applications
    result = bridge.get_running_apps()
    if result.success:
        apps = result.data["apps"]
        print(f"\nRunning applications ({len(apps)}):")
        for app in apps[:10]:  # Show first 10
            print(f"  - {app}")
    else:
        print(f"Error getting apps: {result.error}")


def example_window_management():
    """Window management operations."""
    print("\n" + "=" * 60)
    print("Example 2: Window Management")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    # Get active window
    result = bridge.get_active_window()
    if result.success:
        window = result.data["window"]
        print(f"\nActive window:")
        print(f"  App: {window.app_name}")
        print(f"  Title: {window.title}")
        print(f"  Active: {window.is_active}")
    
    # List all windows
    result = bridge.list_windows()
    if result.success:
        windows = result.data["windows"]
        print(f"\nAll windows ({len(windows)}):")
        for window in windows[:5]:  # Show first 5
            print(f"  - {window.app_name}: {window.title}")


def example_application_control():
    """Application launch and control."""
    print("\n" + "=" * 60)
    print("Example 3: Application Control")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    # Open an application (non-destructive example)
    print("\nOpening Terminal...")
    result = bridge.open_app("Terminal")
    
    if result.success:
        print(f"✓ Opened {result.data['app_name']}")
        
        # Wait a moment
        time.sleep(1)
        
        # Close it
        print("\nClosing Terminal...")
        result = bridge.close_app("Terminal")
        if result.success:
            print(f"✓ Closed {result.data['app_name']}")
    else:
        print(f"✗ Error: {result.error}")


def example_keyboard_input():
    """Keyboard input operations."""
    print("\n" + "=" * 60)
    print("Example 4: Keyboard Input (Simulated)")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    print("\nNote: These operations would interact with the active window")
    print("We're just showing the API without actually executing:")
    
    # Type text
    print("\n1. Type text:")
    print("   bridge.type_text('Hello, World!')")
    
    # Press key with modifiers
    print("\n2. Press Cmd+C (copy):")
    print("   bridge.press_key('c', modifiers=['command'])")
    
    # Press special keys
    print("\n3. Press Enter:")
    print("   bridge.press_key('return')")
    
    print("\n4. Press Escape:")
    print("   bridge.press_key('escape')")


def example_clipboard_operations():
    """Clipboard read/write operations."""
    print("\n" + "=" * 60)
    print("Example 5: Clipboard Operations")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    # Get current clipboard
    result = bridge.get_clipboard()
    if result.success:
        original = result.data["text"]
        print(f"\nOriginal clipboard: {original[:50]}...")
        
        # Set new content
        test_content = "Hello from SystemBridge!"
        result = bridge.set_clipboard(test_content)
        if result.success:
            print(f"✓ Set clipboard to: {test_content}")
            
            # Verify
            result = bridge.get_clipboard()
            if result.success:
                new_content = result.data["text"]
                print(f"✓ Verified clipboard: {new_content}")
                
                # Restore original
                bridge.set_clipboard(original)
                print(f"✓ Restored original clipboard")
    else:
        print(f"✗ Error: {result.error}")


def example_system_notifications():
    """System notification operations."""
    print("\n" + "=" * 60)
    print("Example 6: System Notifications")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    # Show notification
    print("\nShowing notification...")
    result = bridge.show_notification(
        message="This is a test notification from SystemBridge",
        title="SystemBridge Example"
    )
    
    if result.success:
        print("✓ Notification shown")
    else:
        print(f"✗ Error: {result.error}")


def example_error_handling():
    """Proper error handling."""
    print("\n" + "=" * 60)
    print("Example 7: Error Handling")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    # Check availability first
    if not bridge.is_available():
        print(f"✗ Bridge not available on {bridge.get_platform_name()}")
        return
    
    # Try to open non-existent app
    print("\nTrying to open non-existent app...")
    result = bridge.open_app("NonExistentApp12345")
    
    if result.success:
        print("✓ Success (unexpected)")
    else:
        print(f"✗ Expected failure: {result.error}")
        print(f"   Status: {result.status.value}")
        
        # Handle different error types
        if result.status == SystemBridgeStatus.ERROR:
            print("   → Application error (not found or failed to launch)")
        elif result.status == SystemBridgeStatus.NOT_AVAILABLE:
            print("   → Operation not available on this platform")
        elif result.status == SystemBridgeStatus.TIMEOUT:
            print("   → Operation timed out")


def example_mock_bridge():
    """Using MockSystemBridge for testing."""
    print("\n" + "=" * 60)
    print("Example 8: Mock Bridge for Testing")
    print("=" * 60)
    
    from janus.platform.os.mock_bridge import MockSystemBridge
    
    # Create mock bridge
    mock = MockSystemBridge()
    
    print(f"\nMock bridge available: {mock.is_available()}")
    print(f"Platform: {mock.get_platform_name()}")
    
    # Perform operations
    print("\nPerforming mock operations:")
    mock.open_app("TestApp")
    mock.type_text("Hello")
    mock.click(100, 200)
    
    # Check call log
    print(f"\nCalls made: {len(mock.call_log)}")
    for call in mock.call_log:
        print(f"  - {call['method']}: {call['args']}")
    
    # Test failure mode
    print("\nTesting failure mode:")
    mock_fail = MockSystemBridge(should_fail=True)
    result = mock_fail.open_app("App")
    print(f"  Result: {result.success} (expected: False)")
    print(f"  Error: {result.error}")


async def example_automation_workflow():
    """Complete automation workflow."""
    print("\n" + "=" * 60)
    print("Example 9: Complete Automation Workflow")
    print("=" * 60)
    
    bridge = get_system_bridge()
    
    if not bridge.is_available():
        print("SystemBridge not available on this platform")
        return
    
    print("\nAutomation workflow (simulated):")
    print("1. Open TextEdit")
    print("2. Type some text")
    print("3. Select all (Cmd+A)")
    print("4. Copy (Cmd+C)")
    print("5. Get clipboard content")
    print("6. Close TextEdit")
    
    # Note: This is just demonstrating the API
    # In a real scenario, you would:
    # 1. bridge.open_app("TextEdit")
    # 2. await asyncio.sleep(1)
    # 3. bridge.type_text("Hello, World!")
    # 4. bridge.press_key("a", modifiers=["command"])
    # 5. bridge.press_key("c", modifiers=["command"])
    # 6. result = bridge.get_clipboard()
    # 7. bridge.close_app("TextEdit")
    
    print("\n✓ Workflow completed (simulated)")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SYSTEMBRIDGE EXAMPLES")
    print("TICKET-AUDIT-007: System Abstraction Layer")
    print("=" * 60)
    
    try:
        # Basic usage
        example_basic_usage()
        
        # Window management
        example_window_management()
        
        # Application control (be careful with this one)
        # Uncomment to test:
        # example_application_control()
        
        # Keyboard input (informational only)
        example_keyboard_input()
        
        # Clipboard operations
        example_clipboard_operations()
        
        # System notifications
        # Uncomment to test:
        # example_system_notifications()
        
        # Error handling
        example_error_handling()
        
        # Mock bridge
        example_mock_bridge()
        
        # Automation workflow
        asyncio.run(example_automation_workflow())
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
