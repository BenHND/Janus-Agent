"""
Flight Recorder - Complete Session Trace Recording
TICKET-DEV-001: Captures screenshots, vision data, and LLM interactions for debugging

This module records a complete trace of agent execution including:
- Screenshots at each pipeline step (JPG 50% quality)
- Set-of-Marks (detected elements) as JSON
- LLM prompts and responses
- Pipeline metadata and timing

The trace is saved as a .janus_trace file (ZIP format) containing:
- trace.json: Main trace data with metadata and timeline
- screenshots/: Compressed screenshots for each step
- elements/: Set-of-Marks JSON for each step
- llm/: LLM interactions (prompts and responses)

PII Integration (TICKET-PRIV-001):
- Screenshots are automatically masked if PII masking is enabled
- Uses existing PIIMasker to blur sensitive information
"""

import json
import logging
import os
import time
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from janus.utils.paths import get_log_dir

logger = logging.getLogger(__name__)


class TraceRecorder:
    """
    Records complete session traces for debugging and analysis.
    
    Captures all agent actions, vision data, and LLM interactions
    in a single .janus_trace file for post-mortem debugging.
    """

    def __init__(
        self,
        session_id: str,
        trace_dir: Optional[str] = None,
        enable_pii_masking: bool = False,
        jpeg_quality: int = 50,
    ):
        """
        Initialize trace recorder
        
        Args:
            session_id: Session identifier
            trace_dir: Directory to save traces (default: logs/traces)
            enable_pii_masking: Enable PII masking on screenshots
            jpeg_quality: JPEG compression quality (1-100, default 50)
        """
        self.session_id = session_id
        self.enable_pii_masking = enable_pii_masking
        self.jpeg_quality = max(1, min(100, jpeg_quality))
        
        # Set up trace directory
        if trace_dir is None:
            trace_dir = get_log_dir() / "traces"
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        
        # Trace data
        self.trace_data: Dict[str, Any] = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "metadata": {},
        }
        
        # Store actual data for writing to ZIP
        self._screenshots: Dict[int, bytes] = {}  # step_index -> JPEG bytes
        self._elements: Dict[int, List[Dict[str, Any]]] = {}  # step_index -> elements
        self._llm_interactions: Dict[int, Dict[str, str]] = {}  # step_index -> {prompt, response}
        
        # Lazy-loaded components
        self._pii_masker = None
        self._ocr_engine = None
        self._step_counter = 0
        
        logger.info(
            f"TraceRecorder initialized for session {session_id} "
            f"(PII masking: {enable_pii_masking}, quality: {jpeg_quality}%)"
        )

    @property
    def pii_masker(self):
        """Lazy-load PII masker if needed"""
        if self.enable_pii_masking and self._pii_masker is None:
            from janus.vision.pii_masker import PIIMasker
            self._pii_masker = PIIMasker(blur_radius=15)
        return self._pii_masker

    @property
    def ocr_engine(self):
        """Lazy-load OCR engine for PII detection"""
        if self.enable_pii_masking and self._ocr_engine is None:
            try:
                from janus.vision.native_ocr_adapter import NativeOCRAdapter
                self._ocr_engine = NativeOCRAdapter(backend="auto")
            except Exception as e:
                logger.warning(f"Failed to load OCR engine for PII masking: {e}")
                self._ocr_engine = None
        return self._ocr_engine

    def record_step(
        self,
        step_name: str,
        screenshot: Optional[Image.Image] = None,
        elements: Optional[List[Dict[str, Any]]] = None,
        llm_prompt: Optional[str] = None,
        llm_response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record a pipeline step with all associated data
        
        Args:
            step_name: Name of the pipeline step (e.g., "vision", "reasoning", "execution")
            screenshot: PIL Image to save (will be compressed and optionally masked)
            elements: List of detected elements (Set-of-Marks)
            llm_prompt: LLM prompt if applicable
            llm_response: LLM response if applicable
            metadata: Additional metadata for this step
            
        Returns:
            Step index (for reference)
        """
        step_index = self._step_counter
        self._step_counter += 1
        
        timestamp = datetime.now().isoformat()
        
        step_data = {
            "step_index": step_index,
            "step_name": step_name,
            "timestamp": timestamp,
            "has_screenshot": screenshot is not None,
            "has_elements": elements is not None and len(elements) > 0,
            "has_llm_interaction": llm_prompt is not None or llm_response is not None,
            "metadata": metadata or {},
        }
        
        # Store references to files that will be added to ZIP and store actual data
        if screenshot is not None:
            step_data["screenshot_path"] = f"screenshots/step_{step_index:03d}.jpg"
            # Process and store screenshot
            try:
                screenshot_bytes = self._process_screenshot(screenshot)
                self._screenshots[step_index] = screenshot_bytes
            except Exception as e:
                logger.warning(f"Failed to process screenshot for step {step_index}: {e}")
            
        if elements is not None and len(elements) > 0:
            step_data["elements_path"] = f"elements/step_{step_index:03d}.json"
            # Store elements
            self._elements[step_index] = elements
            
        if llm_prompt is not None or llm_response is not None:
            step_data["llm_path"] = f"llm/step_{step_index:03d}.json"
            # Store LLM interaction
            self._llm_interactions[step_index] = {
                "prompt": llm_prompt,
                "response": llm_response,
            }
        
        self.trace_data["steps"].append(step_data)
        
        logger.debug(
            f"Recorded step {step_index}: {step_name} "
            f"(screenshot: {screenshot is not None}, "
            f"elements: {elements is not None}, "
            f"llm: {llm_prompt is not None or llm_response is not None})"
        )
        
        return step_index

    def _process_screenshot(self, screenshot: Image.Image) -> bytes:
        """
        Process screenshot: apply PII masking if enabled, then compress as JPEG
        
        Args:
            screenshot: PIL Image to process
            
        Returns:
            Compressed JPEG image bytes
        """
        processed_image = screenshot
        
        # Apply PII masking if enabled
        if self.enable_pii_masking and self.pii_masker is not None:
            try:
                # Run OCR to detect text regions
                if self.ocr_engine is not None:
                    ocr_results = self.ocr_engine.extract_text(screenshot)
                    # Mask PII regions
                    processed_image = self.pii_masker.mask_pii_in_image(
                        screenshot, ocr_results
                    )
                    logger.debug("Applied PII masking to screenshot")
                else:
                    logger.warning("OCR engine not available, skipping PII masking")
            except Exception as e:
                logger.warning(f"Failed to apply PII masking: {e}")
                processed_image = screenshot
        
        # Compress as JPEG
        buffer = BytesIO()
        # Convert RGBA to RGB if needed
        if processed_image.mode == "RGBA":
            rgb_image = Image.new("RGB", processed_image.size, (255, 255, 255))
            rgb_image.paste(processed_image, mask=processed_image.split()[3])
            processed_image = rgb_image
        
        processed_image.save(buffer, format="JPEG", quality=self.jpeg_quality, optimize=True)
        return buffer.getvalue()

    def save_trace(self, filename: Optional[str] = None) -> Path:
        """
        Save the complete trace to a .janus_trace file
        
        Args:
            filename: Optional filename (default: session_{id}_{timestamp}.janus_trace)
            
        Returns:
            Path to saved trace file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{self.session_id}_{timestamp}.janus_trace"
        
        if not filename.endswith(".janus_trace"):
            filename += ".janus_trace"
        
        trace_path = self.trace_dir / filename
        
        # Finalize trace metadata
        self.trace_data["end_time"] = datetime.now().isoformat()
        self.trace_data["total_steps"] = len(self.trace_data["steps"])
        
        logger.info(f"Saving trace to {trace_path}")
        
        # Create ZIP file with all trace data
        with zipfile.ZipFile(trace_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write main trace JSON
            zf.writestr("trace.json", json.dumps(self.trace_data, indent=2))
            
            # Write screenshots
            for step_index, screenshot_bytes in self._screenshots.items():
                path = f"screenshots/step_{step_index:03d}.jpg"
                zf.writestr(path, screenshot_bytes)
            
            # Write elements
            for step_index, elements in self._elements.items():
                path = f"elements/step_{step_index:03d}.json"
                zf.writestr(path, json.dumps(elements, indent=2))
            
            # Write LLM interactions
            for step_index, llm_data in self._llm_interactions.items():
                path = f"llm/step_{step_index:03d}.json"
                zf.writestr(path, json.dumps(llm_data, indent=2))
            
        logger.info(
            f"Trace saved successfully: {trace_path} "
            f"({trace_path.stat().st_size / 1024:.1f} KB)"
        )
        
        return trace_path

    def add_metadata(self, key: str, value: Any):
        """
        Add metadata to the trace
        
        Args:
            key: Metadata key
            value: Metadata value (must be JSON serializable)
        """
        self.trace_data["metadata"][key] = value

    def get_trace_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current trace
        
        Returns:
            Dictionary with trace statistics
        """
        return {
            "session_id": self.session_id,
            "total_steps": len(self.trace_data["steps"]),
            "start_time": self.trace_data.get("start_time"),
            "pii_masking_enabled": self.enable_pii_masking,
            "jpeg_quality": self.jpeg_quality,
            "steps": [
                {
                    "index": step["step_index"],
                    "name": step["step_name"],
                    "timestamp": step["timestamp"],
                }
                for step in self.trace_data["steps"]
            ],
        }


class TraceRecorderManager:
    """
    Manager for trace recorders across multiple sessions.
    
    Provides a singleton-like interface for managing trace recording
    across the application.
    """

    _instance = None
    _recorders: Dict[str, TraceRecorder] = {}
    _enabled: bool = False

    @classmethod
    def enable(cls, enable_pii_masking: bool = False):
        """Enable trace recording globally"""
        cls._enabled = True
        cls._pii_masking_enabled = enable_pii_masking
        logger.info(f"Trace recording enabled (PII masking: {enable_pii_masking})")

    @classmethod
    def disable(cls):
        """Disable trace recording globally"""
        cls._enabled = False
        logger.info("Trace recording disabled")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if trace recording is enabled"""
        return cls._enabled

    @classmethod
    def get_recorder(cls, session_id: str) -> Optional[TraceRecorder]:
        """
        Get or create a trace recorder for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            TraceRecorder instance if enabled, None otherwise
        """
        if not cls._enabled:
            return None
        
        if session_id not in cls._recorders:
            cls._recorders[session_id] = TraceRecorder(
                session_id=session_id,
                enable_pii_masking=getattr(cls, "_pii_masking_enabled", False),
            )
        
        return cls._recorders[session_id]

    @classmethod
    def finalize_session(cls, session_id: str) -> Optional[Path]:
        """
        Finalize and save trace for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Path to saved trace file, or None if recording wasn't enabled
        """
        if session_id in cls._recorders:
            recorder = cls._recorders[session_id]
            trace_path = recorder.save_trace()
            del cls._recorders[session_id]
            return trace_path
        return None

    @classmethod
    def finalize_all(cls):
        """Finalize and save all active traces"""
        session_ids = list(cls._recorders.keys())
        for session_id in session_ids:
            cls.finalize_session(session_id)
