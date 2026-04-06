"""
Async Vision Monitor for Janus

Feature 4: Vision Async
Issue: FONCTIONNALITÉS MANQUANTES - #4

Vision must run in parallel to:
- Detect popups automatically
- Detect errors in real-time
- React to unexpected UI changes
- Monitor for specific patterns

This provides continuous visual monitoring while actions are executing.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..logging import get_logger
from .native_ocr_adapter import NativeOCRAdapter as OCREngine
from .screenshot_engine import ScreenshotEngine
from .visual_error_detector import VisualErrorDetector


class MonitorEventType(Enum):
    """Types of monitor events"""

    POPUP_DETECTED = "popup_detected"
    ERROR_DETECTED = "error_detected"
    EXPECTED_ELEMENT_APPEARED = "expected_element_appeared"
    UNEXPECTED_CHANGE = "unexpected_change"
    PATTERN_MATCHED = "pattern_matched"


@dataclass
class MonitorEvent:
    """Event detected by async monitor"""

    event_type: MonitorEventType
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    priority: int = 1  # 1=low, 5=critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "screenshot_path": self.screenshot_path,
            "priority": self.priority,
        }


class AsyncVisionMonitor:
    """
    Async vision monitoring system

    Runs in background thread to continuously monitor screen for:
    - Error dialogs and popups
    - Expected elements appearing
    - Unexpected UI changes
    - Custom patterns

    Provides real-time event callbacks for immediate reaction.
    """

    def __init__(
        self,
        screenshot_engine: Optional[ScreenshotEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        error_detector: Optional[VisualErrorDetector] = None,
        check_interval_ms: int = 1000,
        enable_popup_detection: bool = True,
        enable_error_detection: bool = True,
    ):
        """
        Initialize async vision monitor

        Args:
            screenshot_engine: Screenshot engine for capturing screen
            ocr_engine: OCR engine for text recognition
            error_detector: Visual error detector
            check_interval_ms: Interval between checks (milliseconds)
            enable_popup_detection: Enable popup detection
            enable_error_detection: Enable error detection
        """
        self.logger = get_logger("async_vision_monitor")

        # Initialize vision components
        self.screenshot_engine = screenshot_engine or ScreenshotEngine()
        self.ocr_engine = ocr_engine or OCREngine(backend="auto")
        self.error_detector = error_detector or VisualErrorDetector(ocr_engine=self.ocr_engine)

        self.check_interval_ms = check_interval_ms
        self._default_check_interval_ms = check_interval_ms  # Store default for restoration
        self.enable_popup_detection = enable_popup_detection
        self.enable_error_detection = enable_error_detection

        # Monitoring state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Battery/eco mode state (TICKET-PERF-002)
        self._eco_mode_active = False

        # Event callbacks
        self._callbacks: Dict[MonitorEventType, List[Callable[[MonitorEvent], None]]] = {
            event_type: [] for event_type in MonitorEventType
        }

        # Event history
        self._events: List[MonitorEvent] = []
        self._max_events = 100

        # Monitoring targets
        self._watch_for_elements: List[str] = []
        self._watch_for_patterns: List[Dict[str, Any]] = []

        # Performance metrics
        self._checks_performed = 0
        self._events_detected = 0
        
        # Latest visual state for non-blocking access (PERF-M4-001)
        self._latest_state: Dict[str, Any] = self._create_empty_state()

    @staticmethod
    def _create_empty_state() -> Dict[str, Any]:
        """
        Create an empty state structure.
        
        PERF-M4-001: Centralized state structure definition for consistency.
        
        Returns:
            Empty state dictionary with default values
        """
        return {
            "timestamp": None,
            "screenshot": None,
            "ocr_text": [],
            "has_popup": False,
            "has_error": False,
            "detected_elements": [],
        }

    def start(self):
        """Start async monitoring"""
        if self._running:
            self.logger.warning("Monitor already running")
            return

        self.logger.info("Starting async vision monitor")
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop async monitoring"""
        if not self._running:
            return

        self.logger.info("Stopping async vision monitor")
        self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def is_running(self) -> bool:
        """Check if monitor is running"""
        return self._running
    
    @property
    def latest_state(self) -> Dict[str, Any]:
        """
        Get the latest visual state captured by the monitor (thread-safe, non-blocking).
        
        PERF-M4-001: This property provides non-blocking access to the most recent
        visual state captured by the background monitor. The pipeline can read this
        instead of waiting for a new vision analysis, drastically reducing latency.
        
        Returns:
            Dictionary containing:
                - timestamp: datetime of last capture
                - screenshot: Latest screenshot (PIL Image or None)
                - ocr_text: List of detected text strings
                - has_popup: Boolean indicating popup detection
                - has_error: Boolean indicating error detection
                - detected_elements: List of watched elements that were found
        """
        with self._lock:
            return self._latest_state.copy()

    def add_callback(self, event_type: MonitorEventType, callback: Callable[[MonitorEvent], None]):
        """
        Add callback for event type

        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        with self._lock:
            self._callbacks[event_type].append(callback)
            self.logger.debug(f"Added callback for {event_type.value}")

    def remove_callback(
        self, event_type: MonitorEventType, callback: Callable[[MonitorEvent], None]
    ):
        """Remove callback for event type"""
        with self._lock:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)

    def watch_for_element(self, element_text: str):
        """
        Watch for specific element to appear

        Args:
            element_text: Text of element to watch for
        """
        with self._lock:
            if element_text not in self._watch_for_elements:
                self._watch_for_elements.append(element_text)
                self.logger.debug(f"Watching for element: {element_text}")

    def stop_watching_element(self, element_text: str):
        """Stop watching for element"""
        with self._lock:
            if element_text in self._watch_for_elements:
                self._watch_for_elements.remove(element_text)

    def watch_for_pattern(self, pattern_name: str, keywords: List[str], priority: int = 3):
        """
        Watch for custom pattern

        Args:
            pattern_name: Name of pattern
            keywords: Keywords to look for
            priority: Event priority if detected
        """
        with self._lock:
            pattern = {"name": pattern_name, "keywords": keywords, "priority": priority}
            self._watch_for_patterns.append(pattern)
            self.logger.debug(f"Watching for pattern: {pattern_name}")

    def get_recent_events(self, count: int = 10) -> List[MonitorEvent]:
        """Get recent events"""
        with self._lock:
            return self._events[-count:][::-1]

    def get_events_by_type(
        self, event_type: MonitorEventType, count: int = 10
    ) -> List[MonitorEvent]:
        """Get recent events of specific type"""
        with self._lock:
            matching = [e for e in self._events if e.event_type == event_type]
            return matching[-count:][::-1]

    def clear_events(self):
        """Clear event history"""
        with self._lock:
            self._events.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            "running": self._running,
            "checks_performed": self._checks_performed,
            "events_detected": self._events_detected,
            "check_interval_ms": self.check_interval_ms,
            "watching_elements": len(self._watch_for_elements),
            "watching_patterns": len(self._watch_for_patterns),
            "callbacks_registered": sum(len(cbs) for cbs in self._callbacks.values()),
            "eco_mode_active": self._eco_mode_active,
        }
    
    def enable_eco_mode(self):
        """
        Enable eco mode - reduces polling interval to save battery.
        TICKET-PERF-002: Mode Économie d'Énergie
        
        Reduces check_interval from default (0.5s/500ms) to 2.0s (2000ms) when on battery.
        """
        with self._lock:
            if not self._eco_mode_active:
                self._eco_mode_active = True
                # Change polling from default to 2000ms (2 seconds)
                self.check_interval_ms = 2000
                self.logger.info(
                    f"🔋 Eco mode enabled - polling interval increased to {self.check_interval_ms}ms"
                )
    
    def disable_eco_mode(self):
        """
        Disable eco mode - restores normal polling interval.
        TICKET-PERF-002: Mode Économie d'Énergie
        
        Restores check_interval to default value when back on AC power.
        """
        with self._lock:
            if self._eco_mode_active:
                self._eco_mode_active = False
                # Restore to default
                self.check_interval_ms = self._default_check_interval_ms
                self.logger.info(
                    f"🔌 Eco mode disabled - polling interval restored to {self.check_interval_ms}ms"
                )
    
    def is_eco_mode_active(self) -> bool:
        """
        Check if eco mode is currently active.
        
        Returns:
            True if eco mode is active, False otherwise
        """
        with self._lock:
            return self._eco_mode_active

    def check_alert_state(self) -> bool:
        """
        Check if there are any active alerts that should pause execution.
        
        Returns:
            True if there are critical alerts (popups or errors) that should pause execution,
            False otherwise.
        """
        with self._lock:
            # Check for recent high-priority events (popup or error detected)
            critical_event_types = [
                MonitorEventType.POPUP_DETECTED,
                MonitorEventType.ERROR_DETECTED,
            ]
            
            for event in self._events[-5:]:  # Check last 5 events
                if event.event_type in critical_event_types and event.priority >= 4:
                    self.logger.warning(
                        f"Alert state detected: {event.event_type.value} - {event.details}"
                    )
                    return True
            
            return False

    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.logger.info("Monitor loop started")

        while self._running:
            try:
                self._perform_check()
                self._checks_performed += 1

                # Sleep for check interval
                time.sleep(self.check_interval_ms / 1000.0)

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                # Continue monitoring despite errors
                time.sleep(1.0)

        self.logger.info("Monitor loop stopped")

    def _perform_check(self):
        """Perform single monitoring check"""
        
        # Capture screenshot
        screenshot = self.screenshot_engine.capture_screen()
        if not screenshot:
            return
        
        # Extract OCR text for latest_state
        ocr_result = self.ocr_engine.extract_text(screenshot)
        ocr_texts = ocr_result.texts if ocr_result and hasattr(ocr_result, 'texts') else []
        
        # Initialize state tracking for this check
        has_popup = False
        has_error = False
        detected_elements = []

        # Check for popups (if enabled)
        if self.enable_popup_detection:
            popup_detected = self._check_for_popups(screenshot)
            has_popup = popup_detected

        # Check for errors (if enabled)
        if self.enable_error_detection:
            error_detected = self._check_for_errors(screenshot)
            has_error = error_detected

        # Check for watched elements
        if self._watch_for_elements:
            found_elements = self._check_for_watched_elements(screenshot)
            detected_elements = found_elements if found_elements else []

        # Check for patterns
        if self._watch_for_patterns:
            self._check_for_patterns(screenshot)
        
        # Update latest_state with this check's data (PERF-M4-001)
        with self._lock:
            self._latest_state = {
                "timestamp": datetime.now(),
                "screenshot": screenshot,
                "ocr_text": ocr_texts,
                "has_popup": has_popup,
                "has_error": has_error,
                "detected_elements": detected_elements,
            }

    def _check_for_popups(self, screenshot):
        """Check for popup dialogs. Returns True if popup detected, False otherwise."""
        try:
            # Simple popup detection: look for common popup keywords
            ocr_results = self.ocr_engine.extract_text(screenshot)

            if not ocr_results or not ocr_results.texts:
                return False

            # TICKET-ARCH-FINAL: Load popup indicators from locale configuration
            from janus.resources.locale_loader import get_locale_loader
            from janus.utils.config_loader import get_config_loader
            
            config_loader = get_config_loader()
            language = config_loader.get("language", "default", "en")  # Default to English for popups
            locale_loader = get_locale_loader()
            
            popup_keywords = locale_loader.get_keywords("popup_indicators", language=language)
            
            # Fallback if locale not available
            if not popup_keywords:
                popup_keywords = ["ok", "cancel", "close", "yes", "no", "confirm", "alert", "warning"]

            # Check if multiple popup keywords are present (likely a popup)
            found_keywords = []
            for text in ocr_results.texts:
                text_lower = text.lower()
                for keyword in popup_keywords:
                    if keyword in text_lower:
                        found_keywords.append(keyword)

            # If we found 2+ popup keywords, likely a popup
            if len(set(found_keywords)) >= 2:
                event = MonitorEvent(
                    event_type=MonitorEventType.POPUP_DETECTED,
                    details={
                        "keywords_found": list(set(found_keywords)),
                        "all_text": ocr_results.texts[:5],  # First 5 text elements
                    },
                    priority=4,
                )
                self._emit_event(event)
                return True
            
            return False

        except Exception as e:
            self.logger.debug(f"Popup check error: {e}")
            return False

    def _check_for_errors(self, screenshot):
        """Check for error dialogs. Returns True if error detected, False otherwise."""
        try:
            # Use error detector
            result = self.error_detector.detect_error(screenshot)

            if result.get("has_error", False):
                event = MonitorEvent(
                    event_type=MonitorEventType.ERROR_DETECTED,
                    details={
                        "error_type": result.get("error_type"),
                        "message": result.get("message"),
                        "confidence": result.get("confidence", 0.0),
                    },
                    priority=5,  # Errors are critical
                )
                self._emit_event(event)
                return True
            
            return False

        except Exception as e:
            self.logger.debug(f"Error check error: {e}")
            return False

    def _check_for_watched_elements(self, screenshot):
        """Check for elements we're watching for. Returns list of found elements."""
        found_elements = []
        try:
            ocr_results = self.ocr_engine.extract_text(screenshot)

            if not ocr_results or not ocr_results.texts:
                return

            # Check each watched element
            with self._lock:
                watched = self._watch_for_elements.copy()

            for element_text in watched:
                # Check if element text appears in OCR results
                for ocr_text in ocr_results.texts:
                    if element_text.lower() in ocr_text.lower():
                        event = MonitorEvent(
                            event_type=MonitorEventType.EXPECTED_ELEMENT_APPEARED,
                            details={"element_text": element_text, "found_text": ocr_text},
                            priority=3,
                        )
                        self._emit_event(event)
                        found_elements.append(element_text)

                        # Remove from watch list (found)
                        self.stop_watching_element(element_text)
                        break
        
        except Exception as e:
            self.logger.debug(f"Element watch error: {e}")
        
        return found_elements

    def _check_for_patterns(self, screenshot):
        """Check for custom patterns"""
        try:
            ocr_results = self.ocr_engine.extract_text(screenshot)

            if not ocr_results or not ocr_results.texts:
                return

            # Combine all text
            all_text = " ".join(ocr_results.texts).lower()

            # Check each pattern
            with self._lock:
                patterns = self._watch_for_patterns.copy()

            for pattern in patterns:
                # Check if all keywords are present
                keywords_found = []
                for keyword in pattern["keywords"]:
                    if keyword.lower() in all_text:
                        keywords_found.append(keyword)

                # If all keywords found, emit event
                if len(keywords_found) == len(pattern["keywords"]):
                    event = MonitorEvent(
                        event_type=MonitorEventType.PATTERN_MATCHED,
                        details={"pattern_name": pattern["name"], "keywords": keywords_found},
                        priority=pattern["priority"],
                    )
                    self._emit_event(event)

        except Exception as e:
            self.logger.debug(f"Pattern check error: {e}")

    def _emit_event(self, event: MonitorEvent):
        """Emit event to callbacks"""
        self.logger.info(f"Event detected: {event.event_type.value} - {event.details}")

        # Add to history
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events :]

            self._events_detected += 1

            # Get callbacks for this event type
            callbacks = self._callbacks[event.event_type].copy()

        # Call callbacks
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")


# Global monitor instance
_global_monitor: Optional[AsyncVisionMonitor] = None


def get_global_monitor() -> AsyncVisionMonitor:
    """Get or create global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AsyncVisionMonitor()
    return _global_monitor


def start_global_monitor():
    """Start global monitor"""
    monitor = get_global_monitor()
    monitor.start()


def stop_global_monitor():
    """Stop global monitor"""
    monitor = get_global_monitor()
    monitor.stop()
