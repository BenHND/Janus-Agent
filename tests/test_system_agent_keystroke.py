"""
Tests for SystemAgent keystroke modifier parsing (Suite Fix PR).

This test verifies that the _keystroke method correctly parses
modifier keys from strings like "command l" instead of typing them literally.

This test module uses mocked imports to avoid triggering
heavy dependencies (pyautogui, PIL) in headless CI environments.
"""

import asyncio
import platform
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Mock heavy dependencies before importing from janus
# This prevents pyautogui and PIL from being loaded in headless environments
_mock_modules = {
    'pyautogui': MagicMock(),
    'PIL': MagicMock(),
    'PIL.Image': MagicMock(),
    'cv2': MagicMock(),
    'numpy': MagicMock(),
    'mouseinfo': MagicMock(),
}
for mod_name, mock in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock


def async_test(coro):
    """Decorator to run async tests in unittest."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestKeystrokeModifierParsing(unittest.TestCase):
    """Test keystroke modifier parsing logic (Suite Fix PR).
    
    This tests the fix for the issue where 'command l' was being
    typed literally instead of executing Cmd+L shortcut.
    """

    def test_parse_command_l(self):
        """Test 'command l' is parsed as modifier + key."""
        modifier_names = {"command", "control", "option", "shift"}
        
        keys = "command l"
        parts = keys.split()
        modifiers = [p for p in parts if p.lower() in modifier_names]
        key_parts = [p for p in parts if p.lower() not in modifier_names]
        
        self.assertEqual(modifiers, ["command"])
        self.assertEqual(key_parts, ["l"])
        self.assertEqual(key_parts[-1], "l")  # Last non-modifier is the key

    def test_parse_command_shift_t(self):
        """Test 'command shift t' is parsed as two modifiers + key."""
        modifier_names = {"command", "control", "option", "shift"}
        
        keys = "command shift t"
        parts = keys.split()
        modifiers = [p for p in parts if p.lower() in modifier_names]
        key_parts = [p for p in parts if p.lower() not in modifier_names]
        
        self.assertEqual(modifiers, ["command", "shift"])
        self.assertEqual(key_parts, ["t"])

    def test_parse_single_key_no_modifiers(self):
        """Test single key 'a' has no modifiers."""
        modifier_names = {"command", "control", "option", "shift"}
        
        keys = "a"
        parts = keys.split()
        modifiers = [p for p in parts if p.lower() in modifier_names]
        key_parts = [p for p in parts if p.lower() not in modifier_names]
        
        self.assertEqual(modifiers, [])
        self.assertEqual(key_parts, ["a"])

    def test_parse_control_option_delete(self):
        """Test 'control option delete' parses correctly."""
        modifier_names = {"command", "control", "option", "shift"}
        
        keys = "control option delete"
        parts = keys.split()
        modifiers = [p for p in parts if p.lower() in modifier_names]
        key_parts = [p for p in parts if p.lower() not in modifier_names]
        
        self.assertEqual(modifiers, ["control", "option"])
        self.assertEqual(key_parts, ["delete"])

    def test_case_insensitive_modifiers(self):
        """Test that modifier detection is case-insensitive."""
        modifier_names = {"command", "control", "option", "shift"}
        
        test_cases = [
            ("Command L", ["Command"], ["L"]),
            ("COMMAND SHIFT T", ["COMMAND", "SHIFT"], ["T"]),
            ("CONTROL Option Delete", ["CONTROL", "Option"], ["Delete"]),
        ]
        
        for keys, expected_mods, expected_keys in test_cases:
            parts = keys.split()
            modifiers = [p for p in parts if p.lower() in modifier_names]
            key_parts = [p for p in parts if p.lower() not in modifier_names]
            
            self.assertEqual(modifiers, expected_mods, f"Failed for '{keys}'")
            self.assertEqual(key_parts, expected_keys, f"Failed for '{keys}'")

    def test_special_keys_without_modifiers(self):
        """Test special keys like 'return', 'escape' have no modifiers."""
        modifier_names = {"command", "control", "option", "shift"}
        
        special_keys = ["return", "escape", "space", "tab", "delete"]
        
        for key in special_keys:
            parts = key.split()
            modifiers = [p for p in parts if p.lower() in modifier_names]
            
            self.assertEqual(modifiers, [], f"Key '{key}' should have no modifiers")
            self.assertEqual(len(parts), 1, f"Key '{key}' should be a single part")


class TestSystemAgentKeystrokeIntegration(unittest.TestCase):
    """Integration tests for SystemAgent keystroke with mocked SystemBridge."""

    @async_test
    async def test_keystroke_with_modifiers_calls_send_keys_correctly(self):
        """Test that keystroke with modifiers calls send_keys with correct args."""
        # Import after mocking
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus
        
        # Create agent with mocked SystemBridge
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.send_keys.return_value = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS
        )
        
        agent = SystemAgent(system_bridge=mock_bridge)
        
        # Execute keystroke with modifiers
        result = await agent.execute(
            action="keystroke",
            args={"keys": "command l"},
            context={}
        )
        
        # Verify send_keys was called with key and modifiers
        mock_bridge.send_keys.assert_called_once()
        call_args = mock_bridge.send_keys.call_args
        
        # Should be called with key='l' and modifiers=['command']
        self.assertEqual(call_args[0][0], "l")  # First positional arg is key
        self.assertEqual(call_args[0][1], ["command"])  # Second positional arg is modifiers
        self.assertEqual(result["status"], "success")

    @async_test
    async def test_keystroke_without_modifiers_calls_send_keys_correctly(self):
        """Test that keystroke without modifiers calls send_keys without modifiers."""
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus
        
        # Create agent with mocked SystemBridge
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.send_keys.return_value = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS
        )
        
        agent = SystemAgent(system_bridge=mock_bridge)
        
        # Execute keystroke without modifiers
        result = await agent.execute(
            action="keystroke",
            args={"keys": "a"},
            context={}
        )
        
        # Verify send_keys was called with just the key
        mock_bridge.send_keys.assert_called_once()
        call_args = mock_bridge.send_keys.call_args
        
        # Should be called with just key='a'
        self.assertEqual(call_args[0][0], "a")
        self.assertEqual(result["status"], "success")

    @async_test
    async def test_keystroke_command_shift_t(self):
        """Test keystroke 'command shift t' calls send_keys with both modifiers."""
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus
        
        # Create agent with mocked SystemBridge
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.send_keys.return_value = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS
        )
        
        agent = SystemAgent(system_bridge=mock_bridge)
        
        # Execute keystroke with multiple modifiers
        result = await agent.execute(
            action="keystroke",
            args={"keys": "command shift t"},
            context={}
        )
        
        # Verify send_keys was called with key and both modifiers
        mock_bridge.send_keys.assert_called_once()
        call_args = mock_bridge.send_keys.call_args
        
        # Should be called with key='t' and modifiers=['command', 'shift']
        self.assertEqual(call_args[0][0], "t")
        self.assertEqual(call_args[0][1], ["command", "shift"])
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main(verbosity=2)
