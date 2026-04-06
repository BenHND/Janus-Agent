"""
Vision Power Manager for Janus Energy Saving Mode
TICKET-PERF-002: Mode Économie d'Énergie (Laptop Mode)

Manages power-saving features for vision models:
- Tracks activity and idle time
- Unloads heavy models (OmniParser) from VRAM after 30s inactivity
- Reloads models when needed
"""

import logging
import threading
import time
import warnings
from typing import Optional

logger = logging.getLogger(__name__)


class VisionPowerManager:
    """
    Manages power-saving features for vision models.
    
    Tracks vision activity and automatically unloads heavy models from VRAM
    when system is on battery power and idle for more than 30 seconds.
    """

    def __init__(self, idle_timeout_seconds: int = 30):
        """
        Initialize vision power manager.
        
        Args:
            idle_timeout_seconds: Seconds of inactivity before unloading models (default: 30)
        """
        self.idle_timeout_seconds = idle_timeout_seconds
        self._lock = threading.Lock()
        
        # Activity tracking
        self._last_activity_time = time.time()
        self._is_idle = False
        
        # Power state
        self._eco_mode_enabled = False
        self._models_unloaded = False
        
        # References to vision components (set via setters)
        self._omniparser_engine = None
        
        # Monitoring thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        logger.info(f"VisionPowerManager initialized (idle_timeout={idle_timeout_seconds}s)")

    def set_omniparser_engine(self, engine):
        """
        Set OmniParser engine reference for model management.
        
        Args:
            engine: OmniParserVisionEngine instance
        """
        with self._lock:
            self._omniparser_engine = engine
            logger.debug("OmniParser engine reference set in power manager")
    
    # Backward compatibility alias
    def set_florence_engine(self, engine):
        """
        DEPRECATED: Use set_omniparser_engine instead.
        Provided for backward compatibility.
        """
        warnings.warn(
            "set_florence_engine is deprecated, use set_omniparser_engine instead",
            DeprecationWarning,
            stacklevel=2
        )
        self.set_omniparser_engine(engine)

    def record_activity(self):
        """
        Record vision activity (model usage).
        
        Resets idle timer and reloads models if they were unloaded.
        """
        with self._lock:
            self._last_activity_time = time.time()
            
            # If models were unloaded and eco mode is active, reload them
            if self._models_unloaded and self._eco_mode_enabled:
                self._reload_models()
            
            self._is_idle = False

    def enable_eco_mode(self):
        """
        Enable eco mode - starts monitoring for idle time.
        TICKET-PERF-002: Mode Économie d'Énergie
        """
        with self._lock:
            if not self._eco_mode_enabled:
                self._eco_mode_enabled = True
                logger.info("🔋 Vision power manager eco mode enabled")
                
                # Start monitoring thread if not running
                if not self._running:
                    self._start_monitoring()

    def disable_eco_mode(self):
        """
        Disable eco mode - stops monitoring and reloads models if needed.
        TICKET-PERF-002: Mode Économie d'Énergie
        """
        with self._lock:
            if self._eco_mode_enabled:
                self._eco_mode_enabled = False
                logger.info("🔌 Vision power manager eco mode disabled")
                
                # Reload models if they were unloaded
                if self._models_unloaded:
                    self._reload_models()

    def is_eco_mode_active(self) -> bool:
        """Check if eco mode is currently active"""
        with self._lock:
            return self._eco_mode_enabled

    def is_idle(self) -> bool:
        """Check if vision system is currently idle"""
        with self._lock:
            return self._is_idle

    def get_idle_time(self) -> float:
        """Get current idle time in seconds"""
        with self._lock:
            return time.time() - self._last_activity_time

    def _start_monitoring(self):
        """Start idle monitoring thread"""
        if self._running:
            return
        
        logger.debug("Starting vision power monitoring")
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop monitoring thread"""
        if not self._running:
            return
        
        logger.debug("Stopping vision power monitoring")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _monitor_loop(self):
        """Main monitoring loop - checks for idle time and unloads models"""
        logger.info("Vision power monitor loop started")
        
        while self._running:
            try:
                with self._lock:
                    if not self._eco_mode_enabled:
                        # Eco mode disabled, skip monitoring
                        time.sleep(5.0)
                        continue
                    
                    idle_time = time.time() - self._last_activity_time
                    
                    # Check if we've been idle for long enough
                    if idle_time >= self.idle_timeout_seconds:
                        if not self._is_idle:
                            self._is_idle = True
                            logger.debug(f"Vision system idle for {idle_time:.1f}s")
                        
                        # Unload models if not already unloaded
                        if not self._models_unloaded:
                            logger.info(
                                f"Vision idle for {idle_time:.1f}s (>={self.idle_timeout_seconds}s), "
                                f"unloading models"
                            )
                            self._unload_models()
                
                # Check every 5 seconds
                time.sleep(5.0)
                
            except Exception as e:
                logger.error(f"Error in vision power monitor loop: {e}")
                time.sleep(5.0)
        
        logger.info("Vision power monitor loop stopped")

    def _unload_models(self):
        """
        Unload heavy models from VRAM (called from monitor loop).
        
        IMPORTANT: This method must be called with self._lock already held.
        It is designed to be called only from _monitor_loop which acquires the lock.
        """
        # Verify lock is held (defensive programming)
        if not self._lock.locked():
            logger.error("_unload_models called without lock - this is a bug!")
            return
            
        if self._models_unloaded:
            return
        
        try:
            # Unload OmniParser model
            if self._omniparser_engine:
                self._omniparser_engine.unload_models()
                self._models_unloaded = True
                logger.info("✓ Vision models unloaded to save power")
            else:
                logger.debug("No OmniParser engine available to unload")
                
        except Exception as e:
            logger.error(f"Failed to unload vision models: {e}")

    def _reload_models(self):
        """
        Reload models to VRAM (called when activity resumes).
        
        IMPORTANT: This method must be called with self._lock already held.
        It is designed to be called only from record_activity and disable_eco_mode
        which acquire the lock.
        """
        # Verify lock is held (defensive programming)
        if not self._lock.locked():
            logger.error("_reload_models called without lock - this is a bug!")
            return
            
        if not self._models_unloaded:
            return
        
        try:
            # Reload OmniParser model
            if self._omniparser_engine:
                self._omniparser_engine.reload_models()
                self._models_unloaded = False
                logger.info("✓ Vision models reloaded")
            else:
                logger.debug("No OmniParser engine available to reload")
                
        except Exception as e:
            logger.error(f"Failed to reload vision models: {e}")


# Global vision power manager instance
_global_vision_power_manager: Optional[VisionPowerManager] = None


def get_vision_power_manager() -> VisionPowerManager:
    """Get or create global vision power manager instance"""
    global _global_vision_power_manager
    if _global_vision_power_manager is None:
        _global_vision_power_manager = VisionPowerManager()
    return _global_vision_power_manager
