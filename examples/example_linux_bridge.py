"""
Example: Using LinuxBridge for Linux System Operations

TICKET-PLATFORM-002: Implement Linux Bridge

This example demonstrates how to use the LinuxBridge for Linux-specific
system operations and automation tasks.
"""

import time
from janus.platform.os.linux_bridge import LinuxBridge
from janus.platform.os.system_bridge import SystemBridgeStatus


def check_dependencies():
    """Check which Linux tools are available."""
    print("=" * 60)
    print("Checking Linux Tool Dependencies")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    print(f"\nPlatform: {bridge.get_platform_name()}")
    print(f"Available: {bridge.is_available()}")
    
    if not bridge.is_available():
        print("\n✗ Not running on Linux")
        return None
    
    print("\nInstalled Tools:")
    print(f"  xdotool:    {'✓ Available' if bridge._xdotool_available else '✗ Not installed'}")
    print(f"  wmctrl:     {'✓ Available' if bridge._wmctrl_available else '✗ Not installed'}")
    print(f"  xclip:      {'✓ Available' if bridge._xclip_available else '✗ Not installed'}")
    print(f"  xsel:       {'✓ Available' if bridge._xsel_available else '✗ Not installed'}")
    print(f"  pyautogui:  {'✓ Available' if bridge._pyautogui_available else '✗ Not installed'}")
    
    print("\nInstallation Commands:")
    if not bridge._xdotool_available:
        print("  sudo apt-get install xdotool")
    if not bridge._wmctrl_available:
        print("  sudo apt-get install wmctrl")
    if not bridge._xclip_available and not bridge._xsel_available:
        print("  sudo apt-get install xclip")
    if not bridge._pyautogui_available:
        print("  pip install pyautogui")
    
    return bridge


def example_process_management():
    """Demonstrate process management operations."""
    print("\n" + "=" * 60)
    print("Example 1: Process Management")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Get running processes
    print("\nGetting running processes...")
    result = bridge.get_running_apps()
    
    if result.success:
        apps = result.data["apps"]
        print(f"✓ Found {len(apps)} running processes")
        
        # Show a few common processes
        common = ["systemd", "bash", "python", "firefox", "chrome"]
        found = [app for app in apps if any(c in app.lower() for c in common)]
        if found:
            print("\nSome running processes:")
            for app in found[:10]:
                print(f"  - {app}")
    else:
        print(f"✗ Error: {result.error}")


def example_window_management():
    """Demonstrate window management operations."""
    print("\n" + "=" * 60)
    print("Example 2: Window Management")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Get active window
    print("\nGetting active window...")
    result = bridge.get_active_window()
    
    if result.success:
        window = result.data["window"]
        print(f"✓ Active window:")
        print(f"  Title: {window['title']}")
        print(f"  App: {window['app_name']}")
        print(f"  ID: {window['window_id']}")
    elif result.status == SystemBridgeStatus.NOT_AVAILABLE:
        print(f"ℹ {result.error}")
    else:
        print(f"✗ Error: {result.error}")
    
    # List all windows
    print("\nListing all windows...")
    result = bridge.list_windows()
    
    if result.success:
        windows = result.data["windows"]
        print(f"✓ Found {len(windows)} windows")
        
        # Show first few windows
        for i, window in enumerate(windows[:5]):
            print(f"  {i+1}. {window['app_name']}: {window['title'][:50]}")
        
        if len(windows) > 5:
            print(f"  ... and {len(windows) - 5} more")
    elif result.status == SystemBridgeStatus.NOT_AVAILABLE:
        print(f"ℹ {result.error}")
    else:
        print(f"✗ Error: {result.error}")


def example_clipboard_operations():
    """Demonstrate clipboard operations."""
    print("\n" + "=" * 60)
    print("Example 3: Clipboard Operations")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Get current clipboard
    print("\nReading clipboard...")
    result = bridge.get_clipboard()
    
    if result.success:
        original = result.data["text"]
        print(f"✓ Original clipboard: {original[:50]}...")
        
        # Set new content
        test_content = "Hello from LinuxBridge! 🐧"
        print(f"\nSetting clipboard to: {test_content}")
        result = bridge.set_clipboard(test_content)
        
        if result.success:
            print("✓ Clipboard updated")
            
            # Verify
            result = bridge.get_clipboard()
            if result.success:
                new_content = result.data["text"]
                print(f"✓ Verified: {new_content}")
                
                # Restore original
                bridge.set_clipboard(original)
                print("✓ Restored original clipboard")
        else:
            print(f"✗ Error setting clipboard: {result.error}")
    
    elif result.status == SystemBridgeStatus.NOT_AVAILABLE:
        print(f"ℹ {result.error}")
    else:
        print(f"✗ Error: {result.error}")


def example_notifications():
    """Demonstrate system notifications."""
    print("\n" + "=" * 60)
    print("Example 4: System Notifications")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Show notification
    print("\nShowing notification...")
    result = bridge.show_notification(
        message="This is a test notification from LinuxBridge",
        title="Linux Bridge Example"
    )
    
    if result.success:
        print("✓ Notification displayed")
    else:
        print(f"✗ Error: {result.error}")


def example_bash_scripts():
    """Demonstrate bash script execution."""
    print("\n" + "=" * 60)
    print("Example 5: Bash Script Execution")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Simple command
    print("\nExecuting: echo 'Hello from bash'")
    result = bridge.run_script("echo 'Hello from bash'")
    
    if result.success:
        print(f"✓ Output: {result.data['stdout'].strip()}")
        print(f"  Exit code: {result.data['returncode']}")
    else:
        print(f"✗ Error: {result.error}")
    
    # System info
    print("\nGetting system information...")
    # SECURITY NOTE: This script is safe as it contains no user input.
    # When using run_script() with user-provided content, always validate
    # and sanitize input to prevent command injection attacks.
    script = """
    echo "Hostname: $(hostname)"
    echo "Kernel: $(uname -r)"
    echo "Distro: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
    echo "Desktop: $DESKTOP_SESSION"
    """
    
    result = bridge.run_script(script)
    
    if result.success:
        print("✓ System Info:")
        for line in result.data['stdout'].strip().split('\n'):
            print(f"  {line}")
    else:
        print(f"✗ Error: {result.error}")


def example_app_automation():
    """Demonstrate simple app automation."""
    print("\n" + "=" * 60)
    print("Example 6: Application Automation (Demo)")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    print("\nThis example would automate a text editor:")
    print("1. Open gedit")
    print("2. Type some text")
    print("3. Select all (Ctrl+A)")
    print("4. Copy (Ctrl+C)")
    print("5. Get clipboard content")
    print("6. Close gedit")
    
    print("\nActual implementation (commented for safety):")
    print("""
    # Open gedit
    bridge.open_app("gedit")
    time.sleep(2)
    
    # Type text
    bridge.type_text("Hello from Linux automation!")
    time.sleep(0.5)
    
    # Select all
    bridge.press_key("a", modifiers=["ctrl"])
    time.sleep(0.2)
    
    # Copy
    bridge.press_key("c", modifiers=["ctrl"])
    time.sleep(0.2)
    
    # Get clipboard
    result = bridge.get_clipboard()
    if result.success:
        print(f"Clipboard: {result.data['text']}")
    
    # Close gedit (without saving)
    bridge.close_app("gedit")
    """)


def example_error_handling():
    """Demonstrate proper error handling."""
    print("\n" + "=" * 60)
    print("Example 7: Error Handling")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    # Try to open non-existent app
    print("\nTrying to open non-existent app...")
    result = bridge.open_app("this-app-does-not-exist-12345")
    
    if not result.success:
        print(f"✗ Expected error: {result.error}")
        print(f"  Status: {result.status.value}")
        
        if result.status == SystemBridgeStatus.ERROR:
            print("  → Application error (not found or failed to launch)")
        elif result.status == SystemBridgeStatus.NOT_AVAILABLE:
            print("  → Operation not available on this system")
    
    # Try operation that requires missing tool
    print("\nTrying operation that may require missing tools...")
    
    # NOTE: For demonstration purposes only. In production code, avoid
    # manipulating private attributes. Create a mock bridge instance instead.
    # Temporarily disable tools for demo
    original_xdotool = bridge._xdotool_available
    original_pyautogui = bridge._pyautogui_available
    bridge._xdotool_available = False
    bridge._pyautogui_available = False
    
    result = bridge.click(100, 100)
    
    if result.status == SystemBridgeStatus.NOT_AVAILABLE:
        print(f"ℹ Tool not available: {result.error}")
    
    # Restore flags
    bridge._xdotool_available = original_xdotool
    bridge._pyautogui_available = original_pyautogui


def example_tool_comparison():
    """Compare xdotool vs pyautogui for UI operations."""
    print("\n" + "=" * 60)
    print("Example 8: Tool Comparison")
    print("=" * 60)
    
    bridge = LinuxBridge()
    
    if not bridge.is_available():
        print("✗ Not running on Linux")
        return
    
    print("\nxdotool vs pyautogui:")
    print("\nxdotool:")
    print("  ✓ Linux-native, fast and lightweight")
    print("  ✓ Better integration with X11 windows")
    print("  ✓ More reliable for window management")
    print("  ✗ Requires X11 (doesn't work on Wayland without XWayland)")
    print("  ✗ Must be installed separately")
    
    print("\npyautogui:")
    print("  ✓ Cross-platform (works on Linux, Windows, macOS)")
    print("  ✓ Python library (pip install)")
    print("  ✓ Works on Wayland (with limitations)")
    print("  ✗ Slower than native tools")
    print("  ✗ Less accurate window detection")
    
    print(f"\nCurrent configuration:")
    print(f"  xdotool available: {bridge._xdotool_available}")
    print(f"  pyautogui available: {bridge._pyautogui_available}")
    
    if bridge._xdotool_available:
        print("\n✓ Using xdotool (preferred)")
    elif bridge._pyautogui_available:
        print("\n✓ Using pyautogui (fallback)")
    else:
        print("\n✗ No UI automation tools available")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("LINUX BRIDGE EXAMPLES")
    print("TICKET-PLATFORM-002: Implement Linux Bridge")
    print("=" * 60)
    
    try:
        # Check dependencies first
        bridge = check_dependencies()
        
        if bridge is None:
            print("\nExamples require Linux platform")
            return
        
        # Run examples
        example_process_management()
        example_window_management()
        example_clipboard_operations()
        example_notifications()
        example_bash_scripts()
        example_app_automation()
        example_error_handling()
        example_tool_comparison()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        print("\nNote: Some operations may require additional tools.")
        print("Install missing tools with:")
        print("  sudo apt-get install xdotool wmctrl xclip")
        print("  pip install pyautogui")
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
