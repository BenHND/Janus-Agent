"""
Unit tests for BatteryMonitor - TICKET-PERF-002

Lightweight tests that don't require vision dependencies.
"""
import sys
import time
import unittest
from unittest.mock import Mock, MagicMock, patch


class TestBatteryMonitorUnit(unittest.TestCase):
    """Test BatteryMonitor functionality without heavy dependencies"""

    def setUp(self):
        """Mock psutil module before importing BatteryMonitor"""
        self.mock_psutil = MagicMock()
        sys.modules['psutil'] = self.mock_psutil

    def tearDown(self):
        """Clean up psutil mock"""
        if 'psutil' in sys.modules:
            del sys.modules['psutil']
        # Clear any imported BatteryMonitor
        if 'janus.utils.battery_monitor' in sys.modules:
            del sys.modules['janus.utils.battery_monitor']

    def test_battery_detection_with_battery(self):
        """Test battery detection on system with battery"""
        # Mock battery present
        mock_battery = Mock()
        mock_battery.power_plugged = False  # On battery
        self.mock_psutil.sensors_battery.return_value = mock_battery
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor()
        
        self.assertTrue(monitor.has_battery())
        self.assertTrue(monitor.is_on_battery())
        self.assertFalse(monitor.is_on_ac_power())

    def test_battery_detection_on_ac(self):
        """Test battery detection when on AC power"""
        # Mock battery present and plugged in
        mock_battery = Mock()
        mock_battery.power_plugged = True  # On AC
        self.mock_psutil.sensors_battery.return_value = mock_battery
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor()
        
        self.assertTrue(monitor.has_battery())
        self.assertFalse(monitor.is_on_battery())
        self.assertTrue(monitor.is_on_ac_power())

    def test_no_battery_system(self):
        """Test behavior on desktop system without battery"""
        # Mock no battery
        self.mock_psutil.sensors_battery.return_value = None
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor()
        
        self.assertFalse(monitor.has_battery())
        self.assertFalse(monitor.is_on_battery())
        self.assertTrue(monitor.is_on_ac_power())

    def test_callbacks_registered(self):
        """Test that callbacks can be registered"""
        # Mock battery
        mock_battery = Mock()
        mock_battery.power_plugged = True
        self.mock_psutil.sensors_battery.return_value = mock_battery
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor(check_interval_seconds=1)
        
        # Add callbacks
        on_battery_callback = Mock()
        on_ac_callback = Mock()
        
        monitor.add_on_battery_callback(on_battery_callback)
        monitor.add_on_ac_callback(on_ac_callback)
        
        # Callbacks should be registered
        self.assertEqual(len(monitor._on_battery_callbacks), 1)
        self.assertEqual(len(monitor._on_ac_callbacks), 1)

    def test_monitor_start_stop(self):
        """Test starting and stopping the monitor"""
        # Mock battery
        mock_battery = Mock()
        mock_battery.power_plugged = True
        self.mock_psutil.sensors_battery.return_value = mock_battery
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor()
        
        # Should not be running initially
        self.assertFalse(monitor.is_running())
        
        # Start monitor
        monitor.start()
        time.sleep(0.1)  # Give thread time to start
        
        self.assertTrue(monitor.is_running())
        
        # Stop monitor
        monitor.stop()
        
        self.assertFalse(monitor.is_running())

    def test_no_start_without_battery(self):
        """Test that monitor doesn't start on systems without battery"""
        # Mock no battery
        self.mock_psutil.sensors_battery.return_value = None
        
        from janus.utils.battery_monitor import BatteryMonitor
        
        monitor = BatteryMonitor()
        
        # Try to start
        monitor.start()
        
        # Should not start
        self.assertFalse(monitor.is_running())


if __name__ == "__main__":
    unittest.main(verbosity=2)
