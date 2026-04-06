# Platform Bridges: Cross-Platform System Automation

> **Architecture**: See [Complete System Architecture](./01-complete-system-architecture.md) for V3 Multi-Layer OODA Loop overview.

---


- System Abstraction Layer Implementation

## Overview

The Platform Bridges provide a unified, cross-platform API for system-level operations, abstracting away differences between macOS, Windows, and Linux. This allows Janus to work seamlessly across different operating systems.

## Supported Platforms

### ✅ macOS (Full Support)
- **Status**: Fully implemented and tested
- **Technology**: AppleScript + System Events
- **Features**:
  - Application management (open, close, list)
  - Window management (focus, list, get active)
  - UI interactions (click, type, press keys)
  - Clipboard operations (get, set)
  - System notifications
  - Script execution (AppleScript)

### ✅ Windows (Full Support) - TICKET-PLATFORM-001
- **Status**: Fully implemented with optional dependencies (December 2024)
- **Technology**: subprocess + PowerShell + optional libraries
- **Features**:
  - ✅ Application management (subprocess + taskkill)
  - ✅ Clipboard operations (tkinter - built-in)
  - ✅ Notifications (PowerShell)
  - ✅ Script execution (PowerShell)
  - **Optional**: Window management (requires pywinauto)
  - **Optional**: UI interactions (requires pyautogui)

**Installation for full Windows support:**
```bash
pip install pyautogui pywinauto
```

### ✅ Linux (Basic Support)
- **Status**: Basic implementation with optional dependencies
- **Technology**: subprocess + standard Linux tools
- **Features**:
  - Application management (subprocess + pkill)
  - Notifications (notify-send)
  - Script execution (bash)
  - **Optional**: Clipboard operations (requires xclip or xsel)
  - **Optional**: Window management (requires wmctrl or xdotool)
  - **Optional**: UI interactions (requires xdotool or pyautogui)

**Installation for full Linux support:**
```bash
# Debian/Ubuntu
sudo apt-get install xdotool wmctrl xclip notify-send

# Optional: Python automation library
pip install pyautogui
```

## Architecture

```
SystemBridge (Abstract Base Class)
├── MacOSBridge (macOS)
├── WindowsBridge (Windows)
└── LinuxBridge (Linux)

get_system_bridge()  # Auto-detects platform
```

## Usage

### Basic Example

```python
from janus.os import get_system_bridge

# Automatically selects the correct platform bridge
bridge = get_system_bridge()

# Check availability
if bridge.is_available():
    print(f"Running on: {bridge.get_platform_name()}")
    
    # Open an application
    result = bridge.open_app("notepad" if bridge.get_platform_name() == "Windows" else "gedit")
    if result.success:
        print("App opened successfully")
    
    # Type some text
    result = bridge.type_text("Hello from Janus!")
    
    # Get clipboard content
    result = bridge.get_clipboard()
    if result.success:
        print(f"Clipboard: {result.data['text']}")
```

### Application Management

```python
# Open application
result = bridge.open_app("firefox")

# Close application
result = bridge.close_app("firefox")

# List running apps
result = bridge.get_running_apps()
if result.success:
    print(f"Running apps: {result.data['apps']}")
```

### Window Management

```python
# Get active window
result = bridge.get_active_window()
if result.success:
    window = result.data["window"]
    print(f"Active: {window['app_name']} - {window['title']}")

# List all windows
result = bridge.list_windows()
if result.success:
    for window in result.data["windows"]:
        print(f"{window['app_name']}: {window['title']}")

# Focus a window
result = bridge.focus_window("Safari")
```

### UI Interactions

```python
# Click at coordinates
result = bridge.click(x=100, y=200, button="left")

# Type text
result = bridge.type_text("Hello, World!")

# Press keys with modifiers
result = bridge.press_key("c", modifiers=["ctrl"])  # Ctrl+C on Windows/Linux
result = bridge.press_key("c", modifiers=["command"])  # Cmd+C on macOS
```

### Clipboard Operations

```python
# Set clipboard
result = bridge.set_clipboard("Text to copy")

# Get clipboard
result = bridge.get_clipboard()
if result.success:
    text = result.data["text"]
```

### System Operations

```python
# Show notification
result = bridge.show_notification(
    message="Task completed!",
    title="Janus"
)

# Run platform-specific script
if bridge.get_platform_name() == "Windows":
    result = bridge.run_script("Get-Process | Select-Object -First 5")
elif bridge.get_platform_name() == "Linux":
    result = bridge.run_script("ls -la /home")
else:  # macOS
    result = bridge.run_script('tell application "Finder" to activate')
```

## Result Handling

All operations return a `SystemBridgeResult` object:

```python
result = bridge.open_app("notepad")

# Check if operation succeeded
if result.success:
    print("Operation succeeded")
    print(f"Data: {result.data}")
else:
    print(f"Operation failed: {result.error}")
    print(f"Status: {result.status}")  # SUCCESS, ERROR, NOT_AVAILABLE, TIMEOUT
```

### Status Codes

- `SUCCESS`: Operation completed successfully
- `ERROR`: Operation failed due to an error
- `NOT_AVAILABLE`: Feature not available (missing dependencies)
- `TIMEOUT`: Operation timed out

## Graceful Degradation

The bridges are designed to work with missing dependencies:

1. **Core features** work without any dependencies:
   - Application launch/close (subprocess)
   - Script execution
   - Notifications (platform-specific tools)

2. **Optional features** require additional dependencies:
   - **Windows**: pywinauto, pyautogui
   - **Linux**: xdotool, wmctrl, xclip, xsel, pyautogui

3. When dependencies are missing:
   - Operations return `NOT_AVAILABLE` status
   - Clear error messages indicate what's needed
   - Core functionality remains operational

## Testing

The platform bridges are thoroughly tested with 48+ unit tests covering:

- Platform detection
- Feature availability checks
- Operation execution (with mocks)
- Dependency checks
- Error handling
- Result formatting

Run tests:
```bash
pytest tests/test_system_bridge.py -v
```

## Implementation Details

### Windows Bridge
- Uses `subprocess` for app launching
- Uses `taskkill` for app closing
- Uses `tasklist` for listing apps
- Uses `tkinter` for clipboard (built-in)
- Uses `PowerShell` for notifications and scripts
- **Optional**: Uses `pywinauto` for window management
- **Optional**: Uses `pyautogui` for UI interactions

### Linux Bridge
- Uses `subprocess` for app launching
- Uses `pkill`/`wmctrl` for app closing
- Uses `ps` for listing apps
- Uses `notify-send` for notifications
- Uses `bash` for script execution
- **Optional**: Uses `xclip`/`xsel` for clipboard
- **Optional**: Uses `wmctrl`/`xdotool` for window management
- **Optional**: Uses `xdotool`/`pyautogui` for UI interactions

## Future Enhancements

1. **Windows**:
   - Full UIAutomation support
   - win32clipboard for improved clipboard handling
   - win10toast for better notifications

2. **Linux**:
   - Wayland support (currently X11-focused)
   - python-xlib for native window management
   - Better desktop environment integration

3. **Cross-platform**:
   - Enhanced error recovery
   - Better timeout handling
   - Improved window matching algorithms
   - Screenshot and visual feedback integration

## Related Documentation

- [Architecture Overview](./README.md)
- [OODA Loop](./02-unified-pipeline.md)
- [Agent Architecture](./04-agent-architecture.md)
- [Testing Guide](../project/TESTING_GUIDE.md)

## See Also

- Implementation: `janus/os/system_bridge.py`
- Platform bridges: `janus/os/{macos,windows,linux}_bridge.py`
- Tests: `tests/test_system_bridge.py`
- Factory: `janus/os/__init__.py`
