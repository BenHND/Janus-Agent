"""
Tests for AsyncVisionMonitor.latest_state property (PERF-M4-001)

Tests the non-blocking vision access via latest_state property.
"""
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from janus.vision.async_vision_monitor import AsyncVisionMonitor, MonitorEvent, MonitorEventType


class TestAsyncVisionMonitorLatestState(unittest.TestCase):
    """Test AsyncVisionMonitor.latest_state property"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock screenshot and OCR engines
        self.mock_screenshot_engine = Mock()
        self.mock_ocr_engine = Mock()
        self.mock_error_detector = Mock()
        
        # Create monitor with fast check interval for testing
        self.monitor = AsyncVisionMonitor(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            error_detector=self.mock_error_detector,
            check_interval_ms=100,  # Fast for testing
        )

    def tearDown(self):
        """Clean up after tests"""
        if self.monitor.is_running():
            self.monitor.stop()

    def test_latest_state_initialized(self):
        """Test that latest_state is initialized with empty data"""
        state = self.monitor.latest_state
        
        self.assertIsInstance(state, dict)
        self.assertIn("timestamp", state)
        self.assertIn("screenshot", state)
        self.assertIn("ocr_text", state)
        self.assertIn("has_popup", state)
        self.assertIn("has_error", state)
        self.assertIn("detected_elements", state)
        
        # Initial state should be empty
        self.assertIsNone(state["timestamp"])
        self.assertIsNone(state["screenshot"])
        self.assertEqual(state["ocr_text"], [])
        self.assertFalse(state["has_popup"])
        self.assertFalse(state["has_error"])
        self.assertEqual(state["detected_elements"], [])

    def test_latest_state_thread_safe(self):
        """Test that latest_state access is thread-safe (returns copy)"""
        state1 = self.monitor.latest_state
        state2 = self.monitor.latest_state
        
        # Should return different dict objects (copies)
        self.assertIsNot(state1, state2)
        
        # But with same content
        self.assertEqual(state1, state2)

    def test_latest_state_updated_by_monitor(self):
        """Test that latest_state is updated by background monitor"""
        # Mock screenshot and OCR results
        mock_screenshot = Mock()
        mock_screenshot.size = (1920, 1080)
        self.mock_screenshot_engine.capture_screen.return_value = mock_screenshot
        
        mock_ocr_result = Mock()
        mock_ocr_result.texts = ["Hello", "World", "Test"]
        self.mock_ocr_engine.extract_text.return_value = mock_ocr_result
        
        # Mock error detector (no error)
        self.mock_error_detector.detect_error.return_value = {"has_error": False}
        
        # Start monitor
        self.monitor.start()
        
        # Wait for at least one check cycle (100ms + margin)
        time.sleep(0.3)
        
        # Get latest state
        state = self.monitor.latest_state
        
        # Verify state was updated
        self.assertIsNotNone(state["timestamp"])
        self.assertIsInstance(state["timestamp"], datetime)
        self.assertEqual(state["screenshot"], mock_screenshot)
        self.assertEqual(state["ocr_text"], ["Hello", "World", "Test"])
        self.assertFalse(state["has_popup"])
        self.assertFalse(state["has_error"])
        
        # Stop monitor
        self.monitor.stop()

    def test_latest_state_popup_detection(self):
        """Test that latest_state reflects popup detection"""
        # Mock screenshot and OCR with popup keywords
        mock_screenshot = Mock()
        self.mock_screenshot_engine.capture_screen.return_value = mock_screenshot
        
        mock_ocr_result = Mock()
        mock_ocr_result.texts = ["OK", "Cancel", "Confirm"]  # Popup keywords
        self.mock_ocr_engine.extract_text.return_value = mock_ocr_result
        
        # Mock locale loader to return popup keywords
        with patch('janus.vision.async_vision_monitor.get_locale_loader') as mock_locale, \
             patch('janus.vision.async_vision_monitor.get_config_loader') as mock_config:
            
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = "en"
            mock_config.return_value = mock_config_instance
            
            mock_locale_instance = Mock()
            mock_locale_instance.get_keywords.return_value = ["ok", "cancel", "confirm"]
            mock_locale.return_value = mock_locale_instance
            
            # Mock error detector
            self.mock_error_detector.detect_error.return_value = {"has_error": False}
            
            # Start monitor
            self.monitor.start()
            time.sleep(0.3)
            
            # Get latest state
            state = self.monitor.latest_state
            
            # Should have detected popup
            self.assertTrue(state["has_popup"])
            
            self.monitor.stop()

    def test_latest_state_error_detection(self):
        """Test that latest_state reflects error detection"""
        # Mock screenshot and OCR
        mock_screenshot = Mock()
        self.mock_screenshot_engine.capture_screen.return_value = mock_screenshot
        
        mock_ocr_result = Mock()
        mock_ocr_result.texts = ["Error", "Failed"]
        self.mock_ocr_engine.extract_text.return_value = mock_ocr_result
        
        # Mock error detector (error detected)
        self.mock_error_detector.detect_error.return_value = {
            "has_error": True,
            "error_type": "dialog",
            "message": "Test error"
        }
        
        # Start monitor
        self.monitor.start()
        time.sleep(0.3)
        
        # Get latest state
        state = self.monitor.latest_state
        
        # Should have detected error
        self.assertTrue(state["has_error"])
        
        self.monitor.stop()

    def test_latest_state_non_blocking(self):
        """Test that accessing latest_state doesn't block"""
        # Start monitor
        self.monitor.start()
        
        # Access latest_state multiple times rapidly
        start_time = time.time()
        for _ in range(100):
            state = self.monitor.latest_state
        elapsed = time.time() - start_time
        
        # Should complete very quickly (< 10ms for 100 accesses)
        self.assertLess(elapsed, 0.01)
        
        self.monitor.stop()


if __name__ == '__main__':
    unittest.main()
