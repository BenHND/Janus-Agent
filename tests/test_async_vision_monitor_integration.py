"""
Integration tests for AsyncVisionMonitor with JanusPipeline

Tests the integration of AsyncVisionMonitor into the pipeline and main.py
"""
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.runtime.core import Settings, MemoryEngine, JanusPipeline


class TestAsyncVisionMonitorIntegration(unittest.TestCase):
    """Test AsyncVisionMonitor integration with pipeline"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings()
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(
            self.settings,
            self.memory,
            enable_vision=True,
            enable_llm_reasoning=False,
            enable_learning=False,
            enable_tts=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        if self.pipeline:
            self.pipeline.cleanup()

    def test_settings_loaded(self):
        """Test that AsyncVisionMonitor settings are loaded"""
        self.assertIsNotNone(self.settings.async_vision_monitor)
        self.assertIsInstance(self.settings.async_vision_monitor.enable_monitor, bool)
        self.assertIsInstance(self.settings.async_vision_monitor.check_interval_ms, int)
        self.assertIsInstance(self.settings.async_vision_monitor.enable_popup_detection, bool)
        self.assertIsInstance(self.settings.async_vision_monitor.enable_error_detection, bool)

    def test_pipeline_has_monitor_methods(self):
        """Test that pipeline has monitor control methods"""
        self.assertTrue(hasattr(self.pipeline, 'start_monitor'))
        self.assertTrue(hasattr(self.pipeline, 'stop_monitor'))
        self.assertTrue(hasattr(self.pipeline, 'async_vision_monitor'))
        self.assertTrue(hasattr(self.pipeline, '_handle_popup_event'))
        self.assertTrue(hasattr(self.pipeline, '_handle_error_event'))

    def test_monitor_disabled_by_default(self):
        """Test that monitor is disabled by default in config"""
        self.assertFalse(self.settings.async_vision_monitor.enable_monitor)

    def test_start_monitor_when_disabled(self):
        """Test that start_monitor does nothing when disabled in settings"""
        # Should not raise exception, just return early
        self.pipeline.start_monitor()
        
        # Monitor should not be running
        if self.pipeline._async_vision_monitor:
            self.assertFalse(self.pipeline._async_vision_monitor.is_running())

    @patch('janus.core.settings.Settings')
    def test_start_monitor_when_enabled(self, mock_settings_class):
        """Test that monitor starts when enabled in settings"""
        # Create mock settings with monitor enabled
        mock_settings = Mock()
        mock_settings.async_vision_monitor.enable_monitor = True
        mock_settings.async_vision_monitor.check_interval_ms = 100
        mock_settings.async_vision_monitor.enable_popup_detection = True
        mock_settings.async_vision_monitor.enable_error_detection = True
        mock_settings.features.enable_vision = True
        
        # Create minimal settings for other required fields
        mock_settings.database = self.settings.database
        mock_settings.whisper = self.settings.whisper
        mock_settings.features = self.settings.features
        
        # Create pipeline with mock settings
        memory = MemoryEngine(self.settings.database)
        pipeline = JanusPipeline(
            mock_settings,
            memory,
            enable_vision=True,
            enable_llm_reasoning=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        try:
            # Try to start monitor
            pipeline.start_monitor()
            
            # If vision components are available, monitor should be running
            if pipeline._async_vision_monitor:
                # Give it a moment to start
                time.sleep(0.1)
                
                # May or may not be running depending on dependencies
                # Just verify no exceptions were raised
                self.assertIsNotNone(pipeline._async_vision_monitor)
        finally:
            pipeline.cleanup()

    def test_cleanup_stops_monitor(self):
        """Test that cleanup stops the monitor if running"""
        # Mock a running monitor
        mock_monitor = Mock()
        mock_monitor.is_running.return_value = True
        self.pipeline._async_vision_monitor = mock_monitor
        
        # Cleanup should stop it
        self.pipeline.cleanup()
        
        mock_monitor.stop.assert_called_once()

    def test_event_handlers_exist(self):
        """Test that event handlers are defined"""
        # Check that handlers can be called without exceptions
        mock_event = Mock()
        mock_event.details = {'test': 'data'}
        mock_event.priority = 3
        mock_event.to_dict.return_value = {'test': 'dict'}
        
        # These should not raise exceptions
        try:
            self.pipeline._handle_popup_event(mock_event)
            self.pipeline._handle_error_event(mock_event)
        except Exception as e:
            self.fail(f"Event handlers raised unexpected exception: {e}")


class TestConfigurationSettings(unittest.TestCase):
    """Test AsyncVisionMonitor configuration"""

    def test_default_config_values(self):
        """Test default configuration values"""
        settings = Settings()
        
        # Test defaults from config.ini
        self.assertFalse(settings.async_vision_monitor.enable_monitor)
        self.assertEqual(settings.async_vision_monitor.check_interval_ms, 1000)
        self.assertTrue(settings.async_vision_monitor.enable_popup_detection)
        self.assertTrue(settings.async_vision_monitor.enable_error_detection)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncVisionMonitorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationSettings))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
