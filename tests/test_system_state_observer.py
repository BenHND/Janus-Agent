"""
Unit tests for SystemStateObserver

Tests system state observation logic.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

from janus.runtime.core.system_state_observer import SystemStateObserver
from janus.platform.os.system_bridge import SystemBridgeStatus


class MockWindow:
    """Mock window object"""
    def __init__(self, app_name, title):
        self.app_name = app_name
        self.title = title


class MockBridgeResult:
    """Mock bridge result"""
    def __init__(self, status, data=None):
        self.status = status
        self.data = data or {}


class TestSystemStateObserver(unittest.TestCase):
    """Test SystemStateObserver"""
    
    def setUp(self):
        """Set up test environment"""
        self.system_bridge = MagicMock()
        self.clipboard_manager = AsyncMock()
        self.observer = SystemStateObserver(
            system_bridge=self.system_bridge,
            clipboard_manager=self.clipboard_manager
        )
    
    def test_initialization(self):
        """Test SystemStateObserver initialization"""
        self.assertIsNotNone(self.observer.system_bridge)
        self.assertIsNotNone(self.observer.clipboard_manager)
    
    def test_observe_system_state_success(self):
        """Test successful system state observation"""
        # Mock window
        window = MockWindow("Safari", "Test Page")
        self.system_bridge.get_active_window.return_value = MockBridgeResult(
            SystemBridgeStatus.SUCCESS,
            {"window": window}
        )
        
        # Mock URL
        self.system_bridge.run_script.return_value = MockBridgeResult(
            SystemBridgeStatus.SUCCESS,
            {"stdout": "https://example.com"}
        )
        
        # Mock clipboard
        self.clipboard_manager.get_text.return_value = "test clipboard"
        
        async def run_test():
            state = await self.observer.observe_system_state()
            
            self.assertEqual(state.active_app, "Safari")
            self.assertEqual(state.window_title, "Test Page")
            self.assertEqual(state.url, "https://example.com")
            self.assertEqual(state.domain, "example.com")
            self.assertEqual(state.clipboard, "test clipboard")
        
        asyncio.run(run_test())
    
    def test_extract_domain(self):
        """Test domain extraction"""
        # Standard URL
        self.assertEqual(self.observer.extract_domain("https://www.example.com/page"), "example.com")
        
        # Without www
        self.assertEqual(self.observer.extract_domain("https://example.com/page"), "example.com")
        
        # With port
        self.assertEqual(self.observer.extract_domain("https://example.com:8080/page"), "example.com")
        
        # Empty URL
        self.assertIsNone(self.observer.extract_domain(""))
        
        # None URL
        self.assertIsNone(self.observer.extract_domain(None))


if __name__ == "__main__":
    unittest.main()
