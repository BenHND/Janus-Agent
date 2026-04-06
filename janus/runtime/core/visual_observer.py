"""
VisualObserver - Visual Context Observation with Async Background Updates

Extracted from ActionCoordinator to separate visual observation concerns.
PERF: Skips vision if accessibility API can provide sufficient UI element data.
PERF-M4-001: Supports background vision updates to avoid blocking OODA loop.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

from janus.platform.accessibility import AccessibilityRole

logger = logging.getLogger(__name__)


class VisualObserver:
    """
    Observes visual context with smart fallback to accessibility.
    
    PERF: Reduces latency by avoiding expensive vision operations when
    accessibility API can provide sufficient data.
    
    PERF-M4-001: Supports async background vision updates to avoid blocking
    the OODA loop. Vision runs in its own asyncio Task and updates a shared
    state that the OODA loop can read without waiting.
    """
    
    # Constants for accessibility element extraction
    MAX_ELEMENTS_PER_ROLE = 5      # Limit elements per role to avoid overload
    MAX_TOTAL_ELEMENTS = 20        # Total element limit (matches SOM limit)
    MAX_ELEMENT_TEXT_LENGTH = 80   # Maximum text length for element names
    
    # PERF-M4-001: Constants for AsyncVisionMonitor state freshness
    ASYNC_MONITOR_STATE_MAX_AGE_SECONDS = 1.0  # Maximum age for cached state (1 second)
    
    def __init__(self, vision_engine=None, system_bridge=None, async_vision_monitor=None):
        """
        Initialize VisualObserver.
        
        Args:
            vision_engine: Optional vision engine for visual context
            system_bridge: Optional system bridge for accessibility backend
            async_vision_monitor: Optional AsyncVisionMonitor for non-blocking vision (PERF-M4-001)
        """
        self.vision_engine = vision_engine
        self.system_bridge = system_bridge
        self.async_vision_monitor = async_vision_monitor  # PERF-M4-001
        
        # PERF-M4-001: Background vision state
        self._background_vision_enabled = False
        self._vision_task: Optional[asyncio.Task] = None
        self._latest_visual_state: Optional[Tuple[str, str, float]] = None  # (elements, source, timestamp)
        self._vision_update_interval = 0.1  # 10 FPS max (as per problem statement)
        self._running = False
    
    def start_background_vision(self, update_interval: float = 0.1):
        """
        Start background vision updates in a separate asyncio Task.
        
        PERF-M4-001: Vision runs continuously in the background and updates
        _latest_visual_state. The OODA loop can read this state without waiting.
        
        Args:
            update_interval: Time between vision updates in seconds (default: 0.1 = 10 FPS)
        """
        if self._background_vision_enabled:
            logger.warning("Background vision already enabled")
            return
        
        self._vision_update_interval = update_interval
        self._background_vision_enabled = True
        self._running = True
        
        # Create background task
        self._vision_task = asyncio.create_task(self._vision_loop())
        logger.info(f"Background vision started (update interval: {update_interval}s, {1/update_interval:.0f} FPS max)")
    
    def stop_background_vision(self):
        """Stop background vision updates."""
        if not self._background_vision_enabled:
            return
        
        self._running = False
        self._background_vision_enabled = False
        
        if self._vision_task and not self._vision_task.done():
            self._vision_task.cancel()
        
        logger.info("Background vision stopped")
    
    async def _vision_loop(self):
        """
        Background vision loop - continuously updates visual state.
        
        PERF-M4-001: This runs in its own asyncio Task and updates
        _latest_visual_state without blocking the OODA loop.
        """
        logger.debug("Vision loop started")
        
        while self._running:
            try:
                # Capture visual state
                start_time = time.time()
                elements, source = await self._capture_visual_state(force_vision=False)
                capture_time = (time.time() - start_time) * 1000
                
                # Update latest state atomically
                self._latest_visual_state = (elements, source, time.time())
                
                logger.debug(f"Vision update: {source} in {capture_time:.0f}ms")
                
            except asyncio.CancelledError:
                logger.debug("Vision loop cancelled")
                break
            except Exception as e:
                logger.warning(f"Vision frame dropped: {e}")
            
            # Sleep until next update (10 FPS max)
            await asyncio.sleep(self._vision_update_interval)
        
        logger.debug("Vision loop stopped")
    
    def get_latest_visual_state(self) -> Optional[Tuple[str, str]]:
        """
        Get the latest visual state from background vision.
        
        PERF-M4-001: This returns immediately with the latest available state,
        without waiting for vision capture. Returns None if no state available yet.
        
        Returns:
            Tuple of (elements_json, source) or None if no state available
        """
        if not self._background_vision_enabled or not self._latest_visual_state:
            return None
        
        elements, source, timestamp = self._latest_visual_state
        age_ms = (time.time() - timestamp) * 1000
        
        logger.debug(f"Using cached visual state (age: {age_ms:.0f}ms, source: {source})")
        return elements, source
    
    async def observe_visual_context(self, force_vision: bool = False, use_background: bool = False) -> Tuple[str, str]:
        """
        Observe visual context with smart fallback to accessibility.
        
        PERF: Skips vision if accessibility API can provide sufficient UI element data.
        This reduces latency by avoiding expensive vision operations when not needed.
        
        PERF-M4-001: If use_background=True and background vision is running,
        returns the latest cached state immediately without blocking.
        
        TICKET-ARCHI: Respects force_vision parameter to bypass accessibility and
        use vision directly when requested (e.g., during recovery or stagnation).
        Also automatically falls back to vision if accessibility returns no elements.
        
        Args:
            force_vision: If True, bypass accessibility and use vision directly
            use_background: If True and background vision is running, use latest cached state
        
        Returns:
            Tuple of (elements_json, source) where source is "accessibility", "vision", or "cached"
        """
        # PERF-M4-001: Use background vision if available and requested
        if use_background and self._background_vision_enabled:
            cached_state = self.get_latest_visual_state()
            if cached_state:
                elements, source = cached_state
                return elements, f"cached_{source}"
            # Fall through to regular observation if no cached state yet
        
        # Regular observation (blocks until complete)
        return await self._capture_visual_state(force_vision=force_vision)
    
    async def _capture_visual_state(self, force_vision: bool = False) -> Tuple[str, str]:
        """
        Capture visual state (internal method).
        
        This is the actual vision capture logic, extracted to support both
        synchronous and background modes.
        
        PERF-M4-001: Checks AsyncVisionMonitor first for non-blocking vision access.
        
        Args:
            force_vision: If True, bypass accessibility and use vision directly
        
        Returns:
            Tuple of (elements_json, source)
        """
        try:
            # PERF-M4-001: Check AsyncVisionMonitor first if available and running
            if self.async_vision_monitor and self.async_vision_monitor.is_running() and not force_vision:
                latest_state = self.async_vision_monitor.latest_state
                if latest_state and latest_state.get("timestamp"):
                    # Check if state is recent (< 1 second old)
                    timestamp = latest_state["timestamp"]
                    age = datetime.now() - timestamp
                    
                    if age < timedelta(seconds=self.ASYNC_MONITOR_STATE_MAX_AGE_SECONDS):
                        # Use the latest state from the monitor
                        ocr_text = latest_state.get("ocr_text", [])
                        if ocr_text and len(ocr_text) > 0:
                            # Convert OCR text to simple JSON format
                            # This is a simplified format - in a real implementation,
                            # you'd want to include bounding boxes if available
                            elements = []
                            for idx, text in enumerate(ocr_text[:20]):  # Limit to 20 elements
                                elements.append({
                                    "id": str(idx + 1),
                                    "type": "text",
                                    "text": text[:80],  # Truncate long text
                                })
                            
                            elements_json = json.dumps(elements, ensure_ascii=False)
                            logger.info(f"✅ Using AsyncVisionMonitor latest_state ({len(elements)} elements, age={age.total_seconds():.2f}s)")
                            return elements_json, "async_monitor"
            
            # TICKET-ARCHI: Respect force_vision - bypass accessibility when True
            if not force_vision and self.can_use_accessibility_instead_of_vision():
                logger.debug("Skipping vision - using accessibility data instead")
                elements = await self.get_accessibility_elements_json()
                
                # TICKET-ARCHI: Fallback to vision if accessibility returns empty or invalid
                # Check for empty JSON array or empty/whitespace string
                has_elements = False
                if elements and elements.strip():
                    try:
                        parsed_elements = json.loads(elements)
                        has_elements = len(parsed_elements) > 0
                    except (json.JSONDecodeError, TypeError):
                        has_elements = False
                
                if not has_elements:
                    logger.warning("⚠️  Accessibility returned 0 elements - falling back to vision")
                    if self.vision_engine and self.vision_engine.is_available():
                        elements = self.vision_engine.get_elements_for_reasoner(force_refresh=True)
                        return elements, "vision"
                    # If vision not available, return empty
                    return "[]", "none"
                
                logger.info(f"✓ Using accessibility data ({len(parsed_elements)} elements)")
                return elements, "accessibility"
            
            # Use vision when forced or accessibility is not available
            if force_vision:
                logger.debug("Using vision (forced)")
            
            # Fall back to vision if accessibility is not available or insufficient
            if self.vision_engine and self.vision_engine.is_available():
                elements = self.vision_engine.get_elements_for_reasoner(force_refresh=False)
                return elements, "vision"
        except Exception as e:
            logger.debug(f"Visual context observation failed: {e}")
            # TICKET-ARCHI: Try vision as last resort on exception
            if self.vision_engine and self.vision_engine.is_available():
                try:
                    elements = self.vision_engine.get_elements_for_reasoner(force_refresh=False)
                    return elements, "vision"
                except Exception as ve:
                    logger.debug(f"Vision fallback also failed: {ve}")
        return "[]", "none"
    
    def can_use_accessibility_instead_of_vision(self) -> bool:
        """
        Check if accessibility API can provide sufficient data instead of vision.
        
        Returns True if accessibility is available and can provide interactive elements.
        This allows skipping expensive vision operations when accessibility suffices.
        """
        try:
            if self.system_bridge is None:
                return False
            
            # Check if accessibility backend is available
            backend = self.system_bridge.get_accessibility_backend()
            if backend is None or not backend.is_available():
                return False
            
            # Accessibility is available - return True to use it
            # Note: We don't check for focused element because accessibility
            # can still provide useful UI tree information even without focus
            return True
            
        except Exception as e:
            logger.debug(f"Accessibility check failed: {e}")
            return False
    
    async def get_accessibility_elements_json(self) -> str:
        """
        Get UI elements from accessibility API in JSON format similar to vision.
        
        Returns JSON array of elements with id, type, text, and bbox fields.
        Falls back to empty array if accessibility data is unavailable.
        """
        try:
            if self.system_bridge is None:
                return "[]"
            
            backend = self.system_bridge.get_accessibility_backend()
            if backend is None:
                return "[]"
            
            # Get interactive elements from accessibility (buttons, text fields, etc.)
            elements = []
            interactive_roles = [
                "button", "text_field", "link", "checkbox", "radio_button",
                "combo_box", "menu_item", "tab"
            ]
            
            for role_str in interactive_roles:
                try:
                    role_enum = self.map_role_str_to_enum(role_str)
                    if role_enum:
                        found = backend.find_elements(role=role_enum)
                        if found:
                            # Limit to MAX_ELEMENTS_PER_ROLE per role to avoid overload
                            for elem in found[:self.MAX_ELEMENTS_PER_ROLE]:
                                # Use deterministic ID based on role and position
                                # Using SHA256 with 12 characters for better collision resistance
                                text_for_hash = elem.name or ""
                                elem_hash = hashlib.sha256(f"{role_str}:{text_for_hash}".encode()).hexdigest()[:12]
                                
                                # Truncate text at word boundary when possible
                                elem_text = elem.name or ""
                                if len(elem_text) > self.MAX_ELEMENT_TEXT_LENGTH:
                                    truncated = elem_text[:self.MAX_ELEMENT_TEXT_LENGTH]
                                    # Try to truncate at last space to avoid cutting mid-word
                                    last_space = truncated.rfind(' ')
                                    if last_space > self.MAX_ELEMENT_TEXT_LENGTH * 0.8:  # Only if space is near end
                                        truncated = truncated[:last_space] + "..."
                                    else:
                                        truncated = truncated + "..."
                                    elem_text = truncated
                                
                                elements.append({
                                    "id": f"{role_str}_{elem_hash}",
                                    "t": role_str,
                                    "txt": elem_text,
                                    "bb": elem.bounds if elem.bounds else [0, 0, 0, 0]
                                })
                except Exception:
                    continue
            
            # Limit total elements to MAX_TOTAL_ELEMENTS (same as SOM limit)
            if len(elements) > self.MAX_TOTAL_ELEMENTS:
                elements = elements[:self.MAX_TOTAL_ELEMENTS]
            
            return json.dumps(elements, ensure_ascii=False)
            
        except Exception as e:
            logger.debug(f"Failed to get accessibility elements: {e}")
            return "[]"
    
    def map_role_str_to_enum(self, role_str: str) -> Optional[AccessibilityRole]:
        """
        Map role string to AccessibilityRole enum.
        
        Args:
            role_str: Role string (e.g., "button", "text_field")
        
        Returns:
            AccessibilityRole enum or None
        """
        try:
            role_map = {
                "button": AccessibilityRole.BUTTON,
                "text_field": AccessibilityRole.TEXT_FIELD,
                "link": AccessibilityRole.LINK,
                "checkbox": AccessibilityRole.CHECKBOX,
                "radio_button": AccessibilityRole.RADIO_BUTTON,
                "combo_box": AccessibilityRole.COMBO_BOX,
                "menu_item": AccessibilityRole.MENU_ITEM,
                "tab": AccessibilityRole.TAB,
            }
            return role_map.get(role_str)
        except Exception:
            return None
