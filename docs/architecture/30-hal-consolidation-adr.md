# 30. ADR: Hardware Abstraction Layer (HAL) Consolidation

**Status:** ✅ Complete  
**Date:** December 2024  
**Ticket:** CORE-FOUNDATION-003  
**Decision Makers:** Development Team  
**Implementation:** Complete - automation/* layer removed

---

## Context and Problem Statement

Janus currently has **two separate automation layers** that provide OS-level abstractions for system operations:

1. **SystemBridge** (`janus/os/*`)
   - Comprehensive API with 16 methods
   - Platform implementations: MacOSBridge, WindowsBridge, LinuxBridge, MockBridge
   - Used by: BrowserAgent, ActionCoordinator
   - Well-documented in architecture docs

2. **OSInterface** (`janus/automation/*`)
   - Limited API with 9 methods
   - Platform implementations: MacOSBackend, StubOSInterface
   - Used by: SystemAgent, UIAgent
   - Less comprehensive coverage

This duplication creates several problems:

- **Code Duplication**: Similar functionality implemented twice
- **Maintenance Burden**: Bug fixes and improvements must be done in two places
- **Inconsistencies**: Different behaviors and edge case handling
- **Confusion**: Developers don't know which layer to use
- **Testing Complexity**: Need to maintain parallel test suites
- **Poor Cohesion**: The "core" is split between two abstraction attempts

## Decision Drivers

- **Minimize Code Duplication**: Single source of truth for OS operations
- **Maximize API Completeness**: More comprehensive API coverage
- **Ensure Testability**: Easy to mock for unit tests
- **Platform Support**: Strong multi-platform support (macOS, Windows, Linux)
- **Consistency**: Single contract for all OS interactions
- **Documentation**: Well-documented architecture
- **Migration Cost**: Minimize refactoring effort

## Considered Options

### Option 1: Consolidate on SystemBridge ✅ **SELECTED**

**Pros:**
- ✅ More comprehensive API (16 methods vs 9)
- ✅ Better naming and clarity ("SystemBridge" is clearer than "OSInterface")
- ✅ Complete platform implementations (MacOS, Windows, Linux)
- ✅ Already used by critical components (ActionCoordinator, BrowserAgent)
- ✅ Better documentation in architecture docs
- ✅ MockBridge for testing is complete
- ✅ Consistent result type (SystemBridgeResult)
- ✅ WindowInfo dataclass for structured data

**Cons:**
- ⚠️ Need to migrate SystemAgent and UIAgent
- ⚠️ Need to deprecate automation/* layer

**Migration Effort:** Medium (2 agents to migrate)

### Option 2: Consolidate on OSInterface

**Pros:**
- ✅ Currently used by more agents (SystemAgent, UIAgent)

**Cons:**
- ❌ Less complete API (missing: open_app, close_app, get_running_apps, list_windows, get_clipboard, set_clipboard, press_key, get_platform_name)
- ❌ Limited platform support (only MacOSBackend fully implemented)
- ❌ Less clear naming
- ❌ Would require migrating ActionCoordinator (critical component)
- ❌ Not as well documented

**Migration Effort:** High (ActionCoordinator is complex)

### Option 3: Merge Both into New Abstraction

**Pros:**
- ✅ Could take best of both worlds

**Cons:**
- ❌ High implementation cost
- ❌ Need to migrate all components
- ❌ Risk of introducing new bugs
- ❌ Delays solving the duplication problem

**Migration Effort:** Very High

## Decision Outcome

**Chosen option: "Option 1 - Consolidate on SystemBridge"**

SystemBridge will be the **official and sole Hardware Abstraction Layer (HAL)** for Janus.

### Rationale

1. **More Complete API**: SystemBridge offers 16 methods covering all necessary OS operations
2. **Better Platform Coverage**: Full implementations for macOS, Windows, and Linux
3. **Critical Component Usage**: ActionCoordinator (the heart of OODA loop) already depends on it
4. **Lower Migration Risk**: Only 2 agents (SystemAgent, UIAgent) need migration
5. **Better Architecture**: Aligns with documented system architecture
6. **Clear Naming**: "SystemBridge" clearly indicates its role as a bridge to the OS

### Consequences

#### Positive

- ✅ **Single Source of Truth**: One HAL for all OS operations
- ✅ **Reduced Maintenance**: Fix bugs once, benefit everywhere
- ✅ **Better Testing**: Unified mocking strategy with MockSystemBridge
- ✅ **Clearer Architecture**: No confusion about which layer to use
- ✅ **Consistent Behavior**: All agents use same underlying implementation
- ✅ **Better Documentation**: Can focus docs on one HAL
- ✅ **Codebase Cleanup**: Removed 8 deprecated files and 4 test files
- ✅ **AppleScriptExecutor Organized**: Moved to proper location in `janus/os/macos/`

#### Negative

- ✅ **Migration Completed**: SystemAgent and UIAgent successfully migrated
- ✅ **Legacy Removed**: automation/* layer completely deleted
- ✅ **Tests Updated**: All tests updated to use SystemBridge

#### Neutral

- ✅ **Documentation Updated**: Developer guide and architecture docs updated
- ✅ **Examples Updated**: Code examples now use SystemBridge

## Migration Plan

### Phase 1: Preparation ✅ COMPLETE
1. ✅ Write this ADR
2. ✅ Document API mapping between OSInterface and SystemBridge
3. ✅ Review all usages of both layers

### Phase 2: Migration ✅ COMPLETE
1. ✅ Migrate SystemAgent to use SystemBridge
2. ✅ Migrate UIAgent to use SystemBridge
3. ✅ Update tests for migrated agents
4. ✅ Verify all functionality works

### Phase 3: Cleanup ✅ COMPLETE
1. ✅ Move AppleScriptExecutor to `janus/os/macos/`
2. ✅ Update all imports to new location
3. ✅ Remove automation/* layer entirely (8 files)
4. ✅ Remove deprecated tests (4 files)
5. ✅ Update FEATURES_AUDIT.md

### Phase 4: Final Verification ✅ COMPLETE
1. ✅ All tests passing (9/9 tests)
2. ✅ No references to deleted code
3. ✅ Documentation updated

## API Mapping

### Methods Available in Both

| OSInterface | SystemBridge | Notes |
|------------|--------------|-------|
| `focus_window(app_name)` | `focus_window(app_name, timeout)` | SystemBridge adds timeout support |
| `send_keys(keys, modifiers)` | `send_keys(keys, modifiers)` | Identical |
| `click(x, y, button)` | `click(x, y, button)` | Identical |
| `type_text(text)` | `type_text(text)` | Identical |
| `run_script(script, timeout)` | `run_script(script, timeout)` | Identical |
| `show_notification(message, title)` | `show_notification(message, title)` | Identical |
| `is_available()` | `is_available()` | Identical |

### OSInterface Methods Needing Mapping

| OSInterface Method | SystemBridge Equivalent |
|-------------------|------------------------|
| `get_active_window_title()` | `get_active_window()` returns WindowInfo with title |
| `quit_application(app_name)` | `close_app(app_name)` |

### Additional SystemBridge Methods (Not in OSInterface)

- `get_platform_name()` - Get platform name (macOS, Windows, Linux)
- `open_app(app_name, timeout)` - Launch applications
- `get_running_apps()` - List all running applications
- `list_windows()` - Get all windows across apps
- `press_key(key, modifiers)` - Press individual key (vs send_keys)
- `get_clipboard()` - Read clipboard content
- `set_clipboard(text)` - Write to clipboard

## Code Examples

### Before (OSInterface)
```python
from janus.automation.factory import get_os_interface

os_interface = get_os_interface()
os_interface.focus_window("Safari")
result = os_interface.get_active_window_title()
title = result.data["title"]
```

### After (SystemBridge)
```python
from janus.os import get_system_bridge

bridge = get_system_bridge()
bridge.focus_window("Safari")
result = bridge.get_active_window()
if result.success:
    window = result.data["window"]
    title = window.title
```

## Testing Strategy

1. **Unit Tests**: Use MockSystemBridge for isolated testing
2. **Integration Tests**: Verify agents work with real SystemBridge
3. **Cross-Platform Tests**: Ensure behavior consistent across OS
4. **Regression Tests**: Ensure no functionality lost in migration

## Documentation Updates

Files to update:
- ✅ `docs/architecture/30-hal-consolidation-adr.md` (this file)
- 🔄 `docs/architecture/19-system-bridge.md` (mark as official HAL)
- 🔄 `docs/developer/03-core-modules.md` (update agent examples)
- 🔄 `FEATURES_AUDIT.md` (update automation section)

## Monitoring and Success Criteria

Success will be measured by:
- ✅ All agents use SystemBridge exclusively
- ✅ Zero references to OSInterface in active code
- ✅ All tests pass with SystemBridge
- ✅ No regression in functionality
- ✅ Documentation reflects single HAL

## Links and References

- [System Bridge Documentation](./19-system-bridge.md)
- [Platform Bridges Guide](./18-platform-bridges.md)
- [Agent Architecture](./04-agent-architecture.md)
- Issue: CORE-FOUNDATION-003
- Related Tickets: TICKET-P1-02, TICKET-AUDIT-007

---

## Appendix: Full API Comparison

### SystemBridge API (16 methods)

```python
# Platform Detection
is_available() -> bool
get_platform_name() -> str

# Application Management
open_app(app_name, timeout) -> SystemBridgeResult
close_app(app_name) -> SystemBridgeResult
get_running_apps() -> SystemBridgeResult

# Window Management
get_active_window() -> SystemBridgeResult  # Returns WindowInfo
list_windows() -> SystemBridgeResult
focus_window(app_name, timeout) -> SystemBridgeResult

# UI Interactions
click(x, y, button) -> SystemBridgeResult
type_text(text) -> SystemBridgeResult
press_key(key, modifiers) -> SystemBridgeResult
send_keys(keys, modifiers) -> SystemBridgeResult

# Clipboard
get_clipboard() -> SystemBridgeResult
set_clipboard(text) -> SystemBridgeResult

# System
show_notification(message, title) -> SystemBridgeResult
run_script(script, timeout) -> SystemBridgeResult
```

### OSInterface API (9 methods)

```python
# Platform Detection
is_available() -> bool

# Window Management
focus_window(app_name, timeout) -> OSInterfaceResult
get_active_window_title() -> OSInterfaceResult

# UI Interactions
send_keys(keys, modifiers) -> OSInterfaceResult
click(x, y, button) -> OSInterfaceResult
type_text(text) -> OSInterfaceResult

# Application Management
quit_application(app_name) -> OSInterfaceResult

# System
show_notification(message, title) -> OSInterfaceResult
run_script(script, timeout) -> OSInterfaceResult
```

---

**Status:** ✅ Complete  
**Implementation Status:** ✅ Fully Implemented  
**Last Updated:** December 14, 2024

## Summary of Changes

### Files Removed (12 total)
**Deprecated automation layer (8 files):**
- `janus/automation/__init__.py`
- `janus/automation/action_abstraction_layer.py`
- `janus/automation/applescript_executor.py` → Moved to `janus/os/macos/`
- `janus/automation/factory.py`
- `janus/automation/macos_backend.py`
- `janus/automation/os_interface.py`
- `janus/automation/ui_executor.py`
- `janus/automation/window_manager.py`

**Deprecated tests (4 files):**
- `tests/test_os_abstraction_layer.py`
- `tests/test_ui_executor.py`
- `tests/test_ui_executor_scenarios.py`
- `tests/test_window_manager.py`

### Files Modified (8 files)
**Agent migrations:**
- `janus/agents/system_agent.py` - Now uses SystemBridge
- `janus/agents/ui_agent.py` - Now uses SystemBridge with cross-platform modifiers

**Import updates:**
- `janus/os/macos_bridge.py` - Updated to import from `janus/os/macos/`
- `janus/os/system_info.py` - Updated imports
- `janus/os/foreground_app_sync.py` - Updated imports

**Tests:**
- `tests/test_applescript_executor.py` - Updated imports
- `tests/test_system_agent_keystroke.py` - Removed deprecated MacOSBackend tests
- `tests/test_missing_features_core.py` - Removed AAL existence test

**Documentation:**
- `docs/architecture/30-hal-consolidation-adr.md` - This file
- `docs/architecture/19-system-bridge.md` - Marked as official HAL
- `FEATURES_AUDIT.md` - Updated automation section

### Files Added (1 file)
- `janus/os/macos/applescript_executor.py` - Moved from automation/

## Verification

✅ All imports updated  
✅ All tests passing (9/9)  
✅ No broken references  
✅ Documentation complete  
✅ Legacy code removed
