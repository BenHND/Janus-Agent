"""
Tests for Battery Mode (Eco Mode) - TICKET-PERF-002

Tests battery monitoring, vision polling adjustments, and model unloading.
"""
import time
import unittest
from unittest.mock import Mock, MagicMock, patch

from janus.utils.battery_monitor import BatteryMonitor
from janus.vision.async_vision_monitor import AsyncVisionMonitor
from janus.vision.vision_power_manager import VisionPowerManager


class TestBatteryMonitor(unittest.TestCase):
    """Test BatteryMonitor functionality"""

    @patch('janus.utils.battery_monitor.psutil')
    def test_battery_detection_with_battery(self, mock_psutil):
        """Test battery detection on system with battery"""
        # Mock battery present
        mock_battery = Mock()
        mock_battery.power_plugged = False  # On battery
        mock_psutil.sensors_battery.return_value = mock_battery
        
        monitor = BatteryMonitor()
        
        self.assertTrue(monitor.has_battery())
        self.assertTrue(monitor.is_on_battery())
        self.assertFalse(monitor.is_on_ac_power())

    @patch('janus.utils.battery_monitor.psutil')
    def test_battery_detection_on_ac(self, mock_psutil):
        """Test battery detection when on AC power"""
        # Mock battery present and plugged in
        mock_battery = Mock()
        mock_battery.power_plugged = True  # On AC
        mock_psutil.sensors_battery.return_value = mock_battery
        
        monitor = BatteryMonitor()
        
        self.assertTrue(monitor.has_battery())
        self.assertFalse(monitor.is_on_battery())
        self.assertTrue(monitor.is_on_ac_power())

    @patch('janus.utils.battery_monitor.psutil')
    def test_no_battery_system(self, mock_psutil):
        """Test behavior on desktop system without battery"""
        # Mock no battery
        mock_psutil.sensors_battery.return_value = None
        
        monitor = BatteryMonitor()
        
        self.assertFalse(monitor.has_battery())
        self.assertFalse(monitor.is_on_battery())
        self.assertTrue(monitor.is_on_ac_power())

    @patch('janus.utils.battery_monitor.psutil')
    def test_callbacks_on_battery_change(self, mock_psutil):
        """Test callbacks are called when power state changes"""
        # Start on AC
        mock_battery = Mock()
        mock_battery.power_plugged = True
        mock_psutil.sensors_battery.return_value = mock_battery
        
        monitor = BatteryMonitor(check_interval_seconds=1)
        
        # Add callbacks
        on_battery_called = []
        on_ac_called = []
        
        monitor.add_on_battery_callback(lambda: on_battery_called.append(True))
        monitor.add_on_ac_callback(lambda: on_ac_called.append(True))
        
        # Start monitoring
        monitor.start()
        
        # Simulate switch to battery
        mock_battery.power_plugged = False
        time.sleep(1.5)  # Wait for monitor loop to detect change
        
        # Should have called on_battery callback
        self.assertTrue(len(on_battery_called) > 0)
        self.assertEqual(len(on_ac_called), 0)
        
        monitor.stop()


class TestAsyncVisionMonitorEcoMode(unittest.TestCase):
    """Test AsyncVisionMonitor eco mode functionality"""

    def test_eco_mode_changes_polling_interval(self):
        """Test that eco mode changes polling interval"""
        monitor = AsyncVisionMonitor(check_interval_ms=500)
        
        # Initial interval
        self.assertEqual(monitor.check_interval_ms, 500)
        self.assertFalse(monitor.is_eco_mode_active())
        
        # Enable eco mode
        monitor.enable_eco_mode()
        
        self.assertEqual(monitor.check_interval_ms, 2000)
        self.assertTrue(monitor.is_eco_mode_active())
        
        # Disable eco mode
        monitor.disable_eco_mode()
        
        self.assertEqual(monitor.check_interval_ms, 500)
        self.assertFalse(monitor.is_eco_mode_active())

    def test_eco_mode_in_stats(self):
        """Test that eco mode status appears in stats"""
        monitor = AsyncVisionMonitor(check_interval_ms=500)
        
        stats = monitor.get_stats()
        self.assertIn("eco_mode_active", stats)
        self.assertFalse(stats["eco_mode_active"])
        
        monitor.enable_eco_mode()
        
        stats = monitor.get_stats()
        self.assertTrue(stats["eco_mode_active"])


class TestVisionPowerManager(unittest.TestCase):
    """Test VisionPowerManager functionality"""

    def test_activity_tracking(self):
        """Test that activity is tracked properly"""
        manager = VisionPowerManager(idle_timeout_seconds=2)
        
        # Record activity
        manager.record_activity()
        
        # Should not be idle immediately
        self.assertFalse(manager.is_idle())
        self.assertLess(manager.get_idle_time(), 1.0)
        
        # Wait and check idle
        time.sleep(2.5)
        # Note: is_idle requires the monitor loop to detect it
        # So we just check idle_time instead
        self.assertGreater(manager.get_idle_time(), 2.0)

    def test_eco_mode_enable_disable(self):
        """Test enabling and disabling eco mode"""
        manager = VisionPowerManager()
        
        self.assertFalse(manager.is_eco_mode_active())
        
        manager.enable_eco_mode()
        self.assertTrue(manager.is_eco_mode_active())
        
        manager.disable_eco_mode()
        self.assertFalse(manager.is_eco_mode_active())

    def test_florence_engine_integration(self):
        """Test that Florence engine is properly managed"""
        manager = VisionPowerManager(idle_timeout_seconds=1)
        
        # Mock Florence engine
        mock_florence = Mock()
        mock_florence.unload_models = Mock()
        mock_florence.reload_models = Mock()
        
        manager.set_florence_engine(mock_florence)
        
        # Enable eco mode and start monitoring
        manager.enable_eco_mode()
        
        # Record activity (should reload if models were unloaded)
        manager.record_activity()
        
        # Since models weren't unloaded yet, reload should not be called
        mock_florence.reload_models.assert_not_called()
        
        manager.stop()


class TestFlorenceModelUnloading(unittest.TestCase):
    """Test Florence-2 model unloading functionality"""

    @patch('janus.vision.florence_adapter.torch')
    @patch('janus.vision.florence_adapter.gc')
    def test_unload_models(self, mock_gc, mock_torch):
        """Test that models can be unloaded from VRAM"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        # Create engine with lazy load
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Mock model and processor
        engine.model = Mock()
        engine.model.cpu = Mock()
        engine.processor = Mock()
        engine._models_loaded = True
        
        # Mock torch CUDA
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.empty_cache = Mock()
        
        # Unload models
        engine.unload_models()
        
        # Verify model was moved to CPU
        engine.model.cpu.assert_called_once()
        
        # Verify CUDA cache was cleared
        mock_torch.cuda.empty_cache.assert_called_once()
        
        # Verify garbage collection was triggered
        mock_gc.collect.assert_called_once()
        
        # Verify models_loaded flag was set to False
        self.assertFalse(engine._models_loaded)

    def test_reload_models(self):
        """Test that models can be reloaded to device"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        # Create engine with lazy load
        engine = FlorenceVisionEngine(lazy_load=True, device="cpu")
        
        # Mock model and processor
        engine.model = Mock()
        engine.model.to = Mock()
        engine.processor = Mock()
        engine._models_loaded = False
        
        # Reload models
        engine.reload_models()
        
        # Verify model was moved to device
        engine.model.to.assert_called_once_with("cpu")
        
        # Verify models_loaded flag was set to True
        self.assertTrue(engine._models_loaded)


class TestVisionServiceEcoMode(unittest.TestCase):
    """Test VisionService eco mode integration"""

    def test_eco_mode_methods_exist(self):
        """Test that VisionService has eco mode methods"""
        from janus.services.vision_service import VisionService
        from janus.runtime.core.settings import Settings
        
        settings = Settings()
        service = VisionService(settings, enabled=False)
        
        # Check methods exist
        self.assertTrue(hasattr(service, 'enable_eco_mode'))
        self.assertTrue(hasattr(service, 'disable_eco_mode'))
        self.assertTrue(hasattr(service, 'record_vision_activity'))


class TestLifecycleServiceBatteryIntegration(unittest.TestCase):
    """Test LifecycleService battery monitor integration"""

    def test_battery_monitor_methods_exist(self):
        """Test that LifecycleService has battery monitor methods"""
        from janus.services.lifecycle_service import LifecycleService
        from janus.runtime.core.settings import Settings
        from janus.runtime.core.memory_engine import MemoryEngine
        
        settings = Settings()
        memory = MemoryEngine(settings.database)
        service = LifecycleService(settings, memory, "test_session")
        
        # Check methods exist
        self.assertTrue(hasattr(service, 'start_battery_monitor'))
        self.assertTrue(hasattr(service, 'stop_battery_monitor'))
        self.assertTrue(hasattr(service, '_on_battery_power'))
        self.assertTrue(hasattr(service, '_on_ac_power'))


def run_tests():
    """Run all battery mode tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBatteryMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncVisionMonitorEcoMode))
    suite.addTests(loader.loadTestsFromTestCase(TestVisionPowerManager))
    suite.addTests(loader.loadTestsFromTestCase(TestFlorenceModelUnloading))
    suite.addTests(loader.loadTestsFromTestCase(TestVisionServiceEcoMode))
    suite.addTests(loader.loadTestsFromTestCase(TestLifecycleServiceBatteryIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
