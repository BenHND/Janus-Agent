"""
Tests for VisionRecoveryService

TICKET-REFACTOR-003: Tests for extracted vision recovery functionality
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock

from janus.services.vision_recovery_service import VisionRecoveryService


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestVisionRecoveryService(unittest.TestCase):
    """Test VisionRecoveryService functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = VisionRecoveryService()
    
    def test_initialization_no_vision_engine(self):
        """Test: Service initializes without pre-configured vision engine"""
        service = VisionRecoveryService()
        self.assertIsNone(service._vision_engine)
    
    def test_initialization_with_vision_engine(self):
        """Test: Service accepts pre-configured vision engine"""
        mock_engine = MagicMock()
        service = VisionRecoveryService(vision_engine=mock_engine)
        self.assertEqual(service._vision_engine, mock_engine)
    
    @async_test
    async def test_recovery_without_vision_engine(self):
        """Test: Recovery fails gracefully when vision engine unavailable"""
        service = VisionRecoveryService()
        # Prevent lazy loading by mocking the property
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        
        with patch.object(VisionRecoveryService, 'vision_engine', property(lambda self: None)):
            result = await service.attempt_recovery(failed_step, error, context)
        
        self.assertFalse(result)
    
    # NOTE: These tests are skipped because they require vision dependencies (pyautogui)
    # Integration tests with actual vision components should be added separately
    # For now, we test the service interface and basic error handling
    
    def test_recovery_interface(self):
        """Test: Recovery method has correct interface"""
        service = VisionRecoveryService()
        # Just verify the method exists and is callable
        self.assertTrue(callable(service.attempt_recovery))


if __name__ == '__main__':
    unittest.main()
