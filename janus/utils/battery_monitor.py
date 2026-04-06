"""
Battery Monitor for Janus Energy Saving Mode
TICKET-PERF-002: Mode Économie d'Énergie (Laptop Mode)

Monitors battery status using psutil to enable power-saving features:
- Detects AC/battery power state
- Triggers reduced polling intervals for AsyncVisionMonitor
- Enables model unloading when on battery power
"""

import logging
import threading
import time
from typing import Callable, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class BatteryMonitor:
    """
    Monitor battery status and power state.
    
    Uses psutil.sensors_battery() to detect whether the system is on
    AC power or battery power, enabling power-saving features when unplugged.
    """

    def __init__(self, check_interval_seconds: int = 10):
        """
        Initialize battery monitor.
        
        Args:
            check_interval_seconds: How often to check battery status (default: 10s)
        """
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Callbacks for battery state changes
        self._on_battery_callbacks: list[Callable[[], None]] = []
        self._on_ac_callbacks: list[Callable[[], None]] = []
        
        # Current state
        self._is_on_battery = False
        self._battery_available = self._check_battery_available()
        
        if not self._battery_available:
            logger.info("No battery detected - running on desktop/server system")
        else:
            # Get initial state
            self._is_on_battery = self._check_battery_status()
            power_state = "battery" if self._is_on_battery else "AC power"
            logger.info(f"Battery monitor initialized - running on {power_state}")

    def _check_battery_available(self) -> bool:
        """Check if a battery is available on this system"""
        if not PSUTIL_AVAILABLE:
            logger.debug("psutil not available - battery detection disabled")
            return False
        try:
            battery = psutil.sensors_battery()
            return battery is not None
        except Exception as e:
            logger.debug(f"Battery detection failed: {e}")
            return False

    def _check_battery_status(self) -> bool:
        """
        Check if system is running on battery power.
        
        Returns:
            True if on battery, False if on AC power or battery unavailable
        """
        if not self._battery_available or not PSUTIL_AVAILABLE:
            return False
            
        try:
            battery = psutil.sensors_battery()
            
            if battery is None:
                return False
            
            # psutil.sensors_battery().power_plugged:
            # - False = running on battery
            # - True = plugged in to AC power
            return not battery.power_plugged
            
        except Exception as e:
            logger.debug(f"Failed to check battery status: {e}")
            return False

    def is_on_battery(self) -> bool:
        """
        Check if system is currently on battery power.
        
        Returns:
            True if on battery, False if on AC power or no battery
        """
        with self._lock:
            return self._is_on_battery

    def is_on_ac_power(self) -> bool:
        """
        Check if system is currently on AC power.
        
        Returns:
            True if on AC power or no battery, False if on battery
        """
        return not self.is_on_battery()

    def has_battery(self) -> bool:
        """
        Check if system has a battery.
        
        Returns:
            True if battery detected, False otherwise
        """
        return self._battery_available

    def add_on_battery_callback(self, callback: Callable[[], None]):
        """
        Add callback to be called when system switches to battery power.
        
        Args:
            callback: Function to call when on battery
        """
        with self._lock:
            self._on_battery_callbacks.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Added on_battery callback: {callback_name}")

    def add_on_ac_callback(self, callback: Callable[[], None]):
        """
        Add callback to be called when system switches to AC power.
        
        Args:
            callback: Function to call when on AC
        """
        with self._lock:
            self._on_ac_callbacks.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Added on_ac callback: {callback_name}")

    def start(self):
        """Start battery monitoring in background thread"""
        if not self._battery_available:
            logger.debug("Battery monitoring not started - no battery detected")
            return
            
        if self._running:
            logger.warning("Battery monitor already running")
            return

        logger.info("Starting battery monitor")
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop battery monitoring"""
        if not self._running:
            return

        logger.info("Stopping battery monitor")
        self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def is_running(self) -> bool:
        """Check if monitor is running"""
        return self._running

    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        logger.info("Battery monitor loop started")

        while self._running:
            try:
                # Check current battery status
                current_on_battery = self._check_battery_status()
                
                # Check if state changed
                with self._lock:
                    previous_on_battery = self._is_on_battery
                    
                    if current_on_battery != previous_on_battery:
                        self._is_on_battery = current_on_battery
                        
                        # State changed - trigger callbacks
                        if current_on_battery:
                            logger.info("⚡ Power state changed: Switched to BATTERY power")
                            callbacks = self._on_battery_callbacks.copy()
                            for callback in callbacks:
                                try:
                                    callback()
                                except Exception as e:
                                    logger.error(f"Error in on_battery callback: {e}")
                        else:
                            logger.info("🔌 Power state changed: Switched to AC power")
                            callbacks = self._on_ac_callbacks.copy()
                            for callback in callbacks:
                                try:
                                    callback()
                                except Exception as e:
                                    logger.error(f"Error in on_ac callback: {e}")

                # Sleep for check interval
                time.sleep(self.check_interval_seconds)

            except Exception as e:
                logger.error(f"Error in battery monitor loop: {e}")
                time.sleep(self.check_interval_seconds)

        logger.info("Battery monitor loop stopped")


# Global battery monitor instance
_global_battery_monitor: Optional[BatteryMonitor] = None


def get_battery_monitor() -> BatteryMonitor:
    """Get or create global battery monitor instance"""
    global _global_battery_monitor
    if _global_battery_monitor is None:
        _global_battery_monitor = BatteryMonitor()
    return _global_battery_monitor


def start_battery_monitor():
    """Start global battery monitor"""
    monitor = get_battery_monitor()
    monitor.start()


def stop_battery_monitor():
    """Stop global battery monitor"""
    if _global_battery_monitor:
        _global_battery_monitor.stop()
