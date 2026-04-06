"""
Set-of-Marks Vision System - TICKET-AUDIT-006, TICKET-VIS-001

Proactive element detection and ID generation for visual grounding.
Optimized for performance and prompt size efficiency.
"""

import concurrent.futures
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class InteractiveElement:
    element_id: str
    element_type: str
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.element_id,
            "type": self.element_type,
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "attributes": self.attributes,
        }
    
    def to_reasoner_format(self) -> Dict[str, Any]:
        # TICKET-4: Include bbox for spatial reasoning
        return {
            "id": self.element_id,
            "t": self.element_type,
            "txt": self.text[:80] if self.text else "",
            "bb": self.bbox,  # (x, y, width, height)
        }


@dataclass
class ScreenCapture:
    timestamp: float
    elements: List[InteractiveElement]
    screenshot_hash: str
    capture_duration_ms: int
    
    def is_expired(self, ttl_seconds: float = 2.0) -> bool:
        return (time.time() - self.timestamp) > ttl_seconds


class SetOfMarksEngine:
    
    # TICKET-ARCHI: Configurable element limit (reduced from 50 to 30)
    # BUG-FIX: Fewer elements but keep more tokens per element for better quality
    DEFAULT_ELEMENT_LIMIT = 30
    
    # TICKET-ARCHI: Spatial scoring constants for element prioritization
    # These control how elements are sorted based on screen position
    HEADER_AREA_THRESHOLD = 0.2     # Top 20% of screen is header/navigation
    FOOTER_AREA_THRESHOLD = 0.8     # Bottom 20% of screen is footer
    HEADER_PENALTY = 100            # Penalty for elements in header area
    FOOTER_PENALTY = 75             # Penalty for elements in footer area
    CENTER_PENALTY_MAX = 50         # Max penalty for distance from center in content area
    
    def __init__(
        self,
        screenshot_engine=None,
        ocr_engine=None,
        element_locator=None,
        florence_engine=None,
        omniparser_engine=None,
        cache_ttl: float = 2.0,
        enable_cache: bool = True,
        use_omniparser: Optional[bool] = None,  # Changed: None = auto-detect
        element_limit: int = DEFAULT_ELEMENT_LIMIT,
    ):
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.use_omniparser = use_omniparser  # Will be updated in _init_vision_components
        self.element_limit = element_limit  # TICKET-ARCHI: Configurable element limit
        self._last_capture: Optional[ScreenCapture] = None
        self._id_counters: Dict[str, int] = {}
        
        self.screenshot_engine = screenshot_engine
        self.ocr_engine = ocr_engine
        self.element_locator = element_locator
        self.florence_engine = florence_engine
        self.omniparser_engine = omniparser_engine
        self._vision_available = False
        
        self._init_vision_components()
    
    def _init_vision_components(self):
        try:
            if self.screenshot_engine is None:
                from janus.vision.screenshot_engine import ScreenshotEngine
                self.screenshot_engine = ScreenshotEngine()
            
            if self.ocr_engine is None:
                from janus.vision.native_ocr_adapter import NativeOCRAdapter
                self.ocr_engine = NativeOCRAdapter(backend="auto")
            
            if self.element_locator is None:
                from janus.vision.element_locator import ElementLocator
                self.element_locator = ElementLocator(
                    screenshot_engine=self.screenshot_engine,
                    ocr_engine=self.ocr_engine,
                )
            
            # TICKET-PERF: Auto-enable OmniParser when available (unless explicitly disabled)
            should_try_omniparser = self.use_omniparser is not False
            
            if should_try_omniparser and self.omniparser_engine is None:
                try:
                    from janus.vision.omniparser_adapter import OmniParserVisionEngine
                    self.omniparser_engine = OmniParserVisionEngine(lazy_load=True)
                    self.use_omniparser = self.omniparser_engine.is_available()
                    if self.use_omniparser:
                        logger.info("✓ OmniParser auto-detected and enabled for UI detection")
                    elif self.use_omniparser is True:
                        logger.warning("⚠️ OmniParser requested but models not available")
                        self.use_omniparser = False
                except Exception as e:
                    logger.debug(f"OmniParser not available: {e}")
                    self.use_omniparser = False
            elif self.omniparser_engine is not None:
                # Engine was provided externally
                self.use_omniparser = self.use_omniparser is not False and self.omniparser_engine.is_available()
            else:
                # Explicitly disabled (use_omniparser is False)
                self.use_omniparser = False
            
            # TICKET-CLEANUP-VISION: Florence-2 fallback removed
            # OmniParser is now the unified vision engine
            
            self._vision_available = True
            logger.info("Set-of-Marks vision components initialized")
            
        except ImportError as e:
            logger.warning(f"Vision components not available: {e}")
            self._vision_available = False
        except Exception as e:
            logger.warning(f"Failed to initialize vision components: {e}")
            self._vision_available = False
    
    def is_available(self) -> bool:
        return self._vision_available
    
    def capture_elements(
        self,
        force_refresh: bool = False,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[InteractiveElement]:
        start_time = time.time()
        
        if (
            self.enable_cache
            and not force_refresh
            and self._last_capture is not None
            and not self._last_capture.is_expired(self.cache_ttl)
        ):
            return self._last_capture.elements
        
        if not self._vision_available:
            return []
        
        try:
            if region:
                screenshot = self.screenshot_engine.capture_region(*region)
            else:
                screenshot = self.screenshot_engine.capture_screen()
            
            if screenshot is None:
                return []
            
            screenshot_hash = self._compute_screenshot_hash(screenshot)
            elements = self._detect_elements(screenshot)
            
            capture_duration_ms = int((time.time() - start_time) * 1000)
            self._last_capture = ScreenCapture(
                timestamp=time.time(),
                elements=elements,
                screenshot_hash=screenshot_hash,
                capture_duration_ms=capture_duration_ms,
            )
            
            logger.info(f"Captured {len(elements)} interactive elements in {capture_duration_ms}ms")
            return elements
            
        except Exception as e:
            logger.error(f"Error capturing elements: {e}", exc_info=True)
            return []
    
    def _detect_elements(self, screenshot: Image.Image) -> List[InteractiveElement]:
        elements = []
        self._id_counters = {}
        
        try:
            ocr_result = None
            florence_result = None
            omniparser_result = None
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                ocr_future = executor.submit(self._run_ocr_detection, screenshot)
                
                vision_future = None
                # Prefer OmniParser over Florence-2
                if self.use_omniparser and self.omniparser_engine and self.omniparser_engine.is_available():
                    vision_future = executor.submit(self._run_omniparser_detection, screenshot)
                elif self.florence_engine and self.florence_engine.is_available():
                    vision_future = executor.submit(self._run_florence_detection, screenshot)
                
                try:
                    ocr_result = ocr_future.result(timeout=15.0)
                except Exception as e:
                    logger.error(f"OCR detection failed: {e}")
                
                if vision_future:
                    try:
                        vision_result = vision_future.result(timeout=15.0)
                        # Check if it's OmniParser or Florence result
                        if self.use_omniparser and vision_result:
                            omniparser_result = vision_result
                        else:
                            florence_result = vision_result
                    except Exception as e:
                        logger.warning(f"Vision detection failed: {e}")
            
            if ocr_result:
                elements.extend(self._create_elements_from_ocr(ocr_result))
            
            if omniparser_result:
                elements.extend(self._create_elements_from_omniparser(omniparser_result))
            elif florence_result:
                elements.extend(self._create_elements_from_florence(florence_result))
            
        except Exception as e:
            logger.error(f"Error detecting elements: {e}", exc_info=True)
        
        return elements
    
    def _run_ocr_detection(self, screenshot: Image.Image) -> Dict[str, Any]:
        return self.ocr_engine.extract_text(screenshot)
    
    def _run_omniparser_detection(self, screenshot: Image.Image) -> Dict[str, Any]:
        return self.omniparser_engine.detect_objects(screenshot)
    
    def _run_florence_detection(self, screenshot: Image.Image) -> Dict[str, Any]:
        return self.florence_engine.detect_objects(screenshot)
    
    def _create_elements_from_ocr(self, ocr_result: Dict[str, Any]) -> List[InteractiveElement]:
        elements = []
        texts = ocr_result.get("texts", [])
        boxes = ocr_result.get("boxes", [])
        confidences = ocr_result.get("confidence", [])
        
        for i, (text, box) in enumerate(zip(texts, boxes)):
            if not text or not text.strip():
                continue
            
            confidence = confidences[i] if i < len(confidences) else 0.5
            element_type = self._classify_element_type(text)
            bbox_tuple = tuple(box) if isinstance(box, list) else box
            # TICKET-4: Pass text and bbox for stable element_id generation
            element_id = self._generate_element_id(element_type, text.strip(), bbox_tuple)
            
            element = InteractiveElement(
                element_id=element_id,
                element_type=element_type,
                text=text.strip(),
                bbox=bbox_tuple,
                confidence=float(confidence) / 100.0 if confidence > 1.0 else float(confidence),
                attributes={"source": "ocr"},
            )
            elements.append(element)
        return elements
    
    def _create_elements_from_omniparser(self, omniparser_result: Dict[str, Any]) -> List[InteractiveElement]:
        elements = []
        objects = omniparser_result.get("objects", [])
        
        for obj in objects:
            label = obj.get("label", "")
            bbox = obj.get("bbox", None)
            confidence = obj.get("confidence", 0.85)
            
            if not bbox:
                continue
            
            element_type = self._classify_object_type(label)
            # TICKET-4: Pass text and bbox for stable element_id generation
            element_id = self._generate_element_id(element_type, label, bbox)
            
            element = InteractiveElement(
                element_id=element_id,
                element_type=element_type,
                text=label,
                bbox=bbox,
                confidence=confidence,
                attributes={"source": "omniparser", "object_label": label},
            )
            elements.append(element)
        return elements
    
    def _create_elements_from_florence(self, florence_result: Dict[str, Any]) -> List[InteractiveElement]:
        elements = []
        objects = florence_result.get("objects", [])
        
        for obj in objects:
            label = obj.get("label", "")
            bbox = obj.get("bbox", None)
            
            if not bbox:
                continue
            
            element_type = self._classify_object_type(label)
            # TICKET-4: Pass text and bbox for stable element_id generation
            element_id = self._generate_element_id(element_type, label, bbox)
            
            element = InteractiveElement(
                element_id=element_id,
                element_type=element_type,
                text=label,
                bbox=bbox,
                confidence=0.85,
                attributes={"source": "florence2", "object_label": label},
            )
            elements.append(element)
        return elements
    
    def _classify_object_type(self, label: str) -> str:
        label_lower = label.lower()
        if any(keyword in label_lower for keyword in ["button", "btn"]): return "button"
        elif any(keyword in label_lower for keyword in ["icon", "menu", "burger", "magnifying", "glass", "loupe"]): return "icon"
        elif any(keyword in label_lower for keyword in ["input", "textbox"]): return "input"
        elif any(keyword in label_lower for keyword in ["image", "picture"]): return "image"
        return "icon"
    
    def _classify_element_type(self, text: str) -> str:
        text_lower = text.lower().strip()
        if text_lower.startswith("http") or "www." in text_lower: return "link"
        
        input_keywords = ["enter ", "type ", "search", "chercher", "rechercher", "email", "password", "username", "input"]
        if any(keyword in text_lower for keyword in input_keywords): return "input"
        
        button_keywords = ["button", "btn", "submit", "ok", "cancel", "save", "login", "sign", "click"]
        if any(keyword in text_lower for keyword in button_keywords): return "button"
        
        return "text"
    
    def _generate_element_id(
        self, 
        element_type: str, 
        text: str = "", 
        bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    ) -> str:
        """
        Generate stable element ID based on content hash.
        
        TICKET-4: Stable element_id = hash(type + normalized_text + bbox_quantized + capture_id)
        This ensures the same element gets the same ID across captures.
        
        Args:
            element_type: Type of element (button, text, icon, etc.)
            text: Element text content
            bbox: Bounding box (x, y, width, height)
            
        Returns:
            Stable element ID like "button_a3f2", "text_9b4e"
        """
        # Normalize text (lowercase, strip whitespace, limit length)
        normalized_text = text.lower().strip()[:50] if text else ""
        
        # Quantize bbox to reduce noise (round to nearest 10 pixels)
        x, y, w, h = bbox
        quantized_bbox = (
            (x // 10) * 10,
            (y // 10) * 10,
            (w // 10) * 10,
            (h // 10) * 10,
        )
        
        # Get capture_id (screenshot hash) for context
        capture_id = self._last_capture.screenshot_hash if self._last_capture else "default"
        
        # Create stable hash from all components
        hash_input = f"{element_type}|{normalized_text}|{quantized_bbox}|{capture_id}"
        hash_digest = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:4]
        
        # Return stable ID: type_hash
        return f"{element_type}_{hash_digest}"
    
    def _compute_screenshot_hash(self, screenshot: Image.Image) -> str:
        try:
            return hashlib.sha256(screenshot.tobytes()).hexdigest()[:16]
        except: return "unknown"
    
    def invalidate_cache(self):
        self._last_capture = None
    
    def get_elements_for_reasoner(self, force_refresh: bool = False) -> str:
        """
        Get elements for Reasoner with SMART SORTING.
        
        TICKET-ARCHI: Increased limit from 20 to 50 to avoid missing important content.
        Hybrid sorting: Combines element type priority with spatial positioning to
        prioritize main content area over navigation elements.
        
        Args:
            force_refresh: If True, bypass cache and capture fresh elements
            
        Returns:
            JSON string containing sorted and filtered elements for reasoning
        """
        elements = self.capture_elements(force_refresh=force_refresh)
        
        # Early return if no elements
        if not elements:
            logger.info("ℹ️  No interactive elements captured")
            return "[]"
        
        # Calculate screen dimensions for spatial scoring
        # bbox format is (x, y, width, height) per InteractiveElement.to_reasoner_format
        screen_height = max((el.bbox[1] + el.bbox[3] for el in elements), default=1000)  # y + height
        screen_width = max((el.bbox[0] + el.bbox[2] for el in elements), default=1000)   # x + width
        center_y = screen_height / 2
        center_x = screen_width / 2
        
        # --- SMART SORTING LOGIC ---
        def priority_score(el: InteractiveElement) -> tuple:
            role = el.element_type.lower()
            text = (el.text or "").lower()
            
            # Type priority (lower = higher priority)
            # 1. INPUTS & SEARCH (CRITICAL)
            if role in ['search', 'input', 'text_field', 'textbox']: 
                type_priority = 0
            elif 'search' in text or 'chercher' in text or 'rechercher' in text: 
                type_priority = 0
            # 2. SEARCH ICONS
            elif role == 'icon' and ('search' in text or 'magnifying' in text): 
                type_priority = 0
            # 3. BUTTONS
            elif role == 'button': 
                type_priority = 1
            # 4. LINKS (YouTube videos are links!)
            elif role == 'link': 
                type_priority = 2
            else:
                type_priority = 3
            
            # Spatial priority: Favor elements in main content area (center of screen)
            # Calculate distance from center, normalized
            el_center_x = el.bbox[0] + el.bbox[2] / 2
            el_center_y = el.bbox[1] + el.bbox[3] / 2
            
            # Elements in the top area are likely navigation (deprioritize)
            if el_center_y < screen_height * self.HEADER_AREA_THRESHOLD:
                spatial_penalty = self.HEADER_PENALTY
            # Elements in center vertical area are main content (prioritize)
            elif screen_height * self.HEADER_AREA_THRESHOLD <= el_center_y <= screen_height * self.FOOTER_AREA_THRESHOLD:
                # Distance from center (normalized 0-1)
                dist_from_center = abs(el_center_y - center_y) / (screen_height / 2)
                spatial_penalty = int(dist_from_center * self.CENTER_PENALTY_MAX)
            else:
                spatial_penalty = self.FOOTER_PENALTY
            
            # Return tuple for sorting: (type_priority, spatial_penalty)
            # This ensures type is primary sort, spatial is secondary
            return (type_priority, spatial_penalty)

        elements.sort(key=priority_score)
        
        # TICKET-ARCHI: Use configurable element limit (default 30, optimized for quality)
        # BUG-FIX: Fewer elements (30 instead of 50) keeps more detail per element within token budget
        if len(elements) > self.element_limit:
            logger.warning(f"⚠️  Truncating visual elements from {len(elements)} to {self.element_limit}")
            elements = elements[:self.element_limit]
        else:
            logger.info(f"ℹ️  Captured {len(elements)} interactive elements")
        
        reasoner_elements = [elem.to_reasoner_format() for elem in elements]
        return json.dumps(reasoner_elements, ensure_ascii=False)
    
    def get_element_by_id(self, element_id: str) -> Optional[InteractiveElement]:
        if self._last_capture is None: return None
        for element in self._last_capture.elements:
            if element.element_id == element_id: return element
        return None
    
    def find_element_by_text(self, text: str, case_sensitive: bool = False) -> Optional[InteractiveElement]:
        """
        Find element by text content.
        
        TICKET-5: Helper for ui_element_visible and ui_element_contains_text stop conditions.
        
        Args:
            text: Text to search for
            case_sensitive: Whether to match case
        
        Returns:
            First matching element or None
        """
        if self._last_capture is None:
            return None
        
        search_text = text if case_sensitive else text.lower()
        
        for element in self._last_capture.elements:
            element_text = element.text if case_sensitive else element.text.lower()
            if search_text in element_text:
                return element
        
        return None
    
    def element_contains_text(self, element_id: str, text: str, case_sensitive: bool = False) -> bool:
        """
        Check if element contains specific text.
        
        TICKET-5: Helper for ui_element_contains_text stop condition.
        
        Args:
            element_id: Element ID to check
            text: Text to search for
            case_sensitive: Whether to match case
        
        Returns:
            True if element contains text
        """
        element = self.get_element_by_id(element_id)
        if element is None:
            return False
        
        search_text = text if case_sensitive else text.lower()
        element_text = element.text if case_sensitive else element.text.lower()
        
        return search_text in element_text
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns stats in the CORRECT format to avoid AttributeError in Coordinator.
        """
        stats = {
            "vision_available": self._vision_available,
            "cache_enabled": self.enable_cache,
            "last_capture": None
        }
        
        if self._last_capture:
            stats["last_capture"] = {
                "timestamp": self._last_capture.timestamp,
                "age_seconds": time.time() - self._last_capture.timestamp,
                "element_count": len(self._last_capture.elements),
                "capture_duration_ms": self._last_capture.capture_duration_ms,
                "screenshot_hash": self._last_capture.screenshot_hash,
                "is_expired": self._last_capture.is_expired(self.cache_ttl),
            }
        
        return stats