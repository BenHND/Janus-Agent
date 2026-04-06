"""
Unit tests for TraceRecorder
TICKET-DEV-001: Flight Recorder
"""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from janus.logging.trace_recorder import TraceRecorder, TraceRecorderManager


class TestTraceRecorder(unittest.TestCase):
    """Test cases for TraceRecorder"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.session_id = "test_session_123"
        self.recorder = TraceRecorder(
            session_id=self.session_id,
            trace_dir=self.temp_dir,
            enable_pii_masking=False,
            jpeg_quality=50,
        )

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test TraceRecorder initialization"""
        self.assertEqual(self.recorder.session_id, self.session_id)
        self.assertEqual(self.recorder.jpeg_quality, 50)
        self.assertFalse(self.recorder.enable_pii_masking)
        self.assertEqual(len(self.recorder.trace_data["steps"]), 0)

    def test_record_step_basic(self):
        """Test recording a basic step"""
        step_index = self.recorder.record_step(
            step_name="test_step",
            metadata={"action": "test"}
        )
        
        self.assertEqual(step_index, 0)
        self.assertEqual(len(self.recorder.trace_data["steps"]), 1)
        
        step = self.recorder.trace_data["steps"][0]
        self.assertEqual(step["step_name"], "test_step")
        self.assertEqual(step["step_index"], 0)
        self.assertFalse(step["has_screenshot"])
        self.assertFalse(step["has_elements"])
        self.assertFalse(step["has_llm_interaction"])

    def test_record_step_with_screenshot(self):
        """Test recording a step with screenshot"""
        # Create a test image
        image = Image.new("RGB", (100, 100), color="red")
        
        step_index = self.recorder.record_step(
            step_name="vision_step",
            screenshot=image
        )
        
        step = self.recorder.trace_data["steps"][0]
        self.assertTrue(step["has_screenshot"])
        self.assertIn("screenshot_path", step)
        self.assertEqual(step["screenshot_path"], "screenshots/step_000.jpg")

    def test_record_step_with_elements(self):
        """Test recording a step with elements"""
        elements = [
            {"type": "button", "text": "Click me", "bbox": [10, 10, 100, 50]},
            {"type": "text", "text": "Hello", "bbox": [20, 60, 80, 90]}
        ]
        
        step_index = self.recorder.record_step(
            step_name="detection_step",
            elements=elements
        )
        
        step = self.recorder.trace_data["steps"][0]
        self.assertTrue(step["has_elements"])
        self.assertIn("elements_path", step)
        self.assertEqual(step["elements_path"], "elements/step_000.json")

    def test_record_step_with_llm(self):
        """Test recording a step with LLM interaction"""
        step_index = self.recorder.record_step(
            step_name="reasoning_step",
            llm_prompt="What should I do?",
            llm_response="Click the button"
        )
        
        step = self.recorder.trace_data["steps"][0]
        self.assertTrue(step["has_llm_interaction"])
        self.assertIn("llm_path", step)
        self.assertEqual(step["llm_path"], "llm/step_000.json")

    def test_record_multiple_steps(self):
        """Test recording multiple steps"""
        self.recorder.record_step("step1")
        self.recorder.record_step("step2")
        self.recorder.record_step("step3")
        
        self.assertEqual(len(self.recorder.trace_data["steps"]), 3)
        self.assertEqual(self.recorder.trace_data["steps"][0]["step_index"], 0)
        self.assertEqual(self.recorder.trace_data["steps"][1]["step_index"], 1)
        self.assertEqual(self.recorder.trace_data["steps"][2]["step_index"], 2)

    def test_process_screenshot(self):
        """Test screenshot processing (compression)"""
        image = Image.new("RGB", (200, 200), color="blue")
        
        jpeg_bytes = self.recorder._process_screenshot(image)
        
        # Check that we got JPEG bytes
        self.assertIsInstance(jpeg_bytes, bytes)
        self.assertGreater(len(jpeg_bytes), 0)
        # JPEG files start with FF D8
        self.assertEqual(jpeg_bytes[0:2], b'\xff\xd8')

    def test_process_screenshot_rgba(self):
        """Test processing RGBA images (should convert to RGB)"""
        image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        
        jpeg_bytes = self.recorder._process_screenshot(image)
        
        # Should successfully convert and compress
        self.assertIsInstance(jpeg_bytes, bytes)
        self.assertGreater(len(jpeg_bytes), 0)

    def test_save_trace(self):
        """Test saving trace to file"""
        # Record some steps
        self.recorder.record_step("step1", metadata={"test": "data"})
        self.recorder.record_step("step2")
        
        # Save trace
        trace_path = self.recorder.save_trace()
        
        # Check that file was created
        self.assertTrue(trace_path.exists())
        self.assertTrue(trace_path.name.endswith(".janus_trace"))
        
        # Check that it's a valid ZIP file
        self.assertTrue(zipfile.is_zipfile(trace_path))
        
        # Check contents
        with zipfile.ZipFile(trace_path, "r") as zf:
            # Should contain trace.json
            self.assertIn("trace.json", zf.namelist())
            
            # Load and verify trace.json
            with zf.open("trace.json") as f:
                trace_data = json.load(f)
            
            self.assertEqual(trace_data["session_id"], self.session_id)
            self.assertEqual(trace_data["total_steps"], 2)
            self.assertIn("start_time", trace_data)
            self.assertIn("end_time", trace_data)

    def test_save_trace_custom_filename(self):
        """Test saving trace with custom filename"""
        self.recorder.record_step("test")
        
        trace_path = self.recorder.save_trace(filename="custom_trace.janus_trace")
        
        self.assertTrue(trace_path.exists())
        self.assertEqual(trace_path.name, "custom_trace.janus_trace")

    def test_save_trace_auto_extension(self):
        """Test that .janus_trace extension is added if missing"""
        self.recorder.record_step("test")
        
        trace_path = self.recorder.save_trace(filename="my_trace")
        
        self.assertTrue(trace_path.name.endswith(".janus_trace"))

    def test_add_metadata(self):
        """Test adding metadata to trace"""
        self.recorder.add_metadata("test_key", "test_value")
        self.recorder.add_metadata("number", 42)
        
        self.assertEqual(self.recorder.trace_data["metadata"]["test_key"], "test_value")
        self.assertEqual(self.recorder.trace_data["metadata"]["number"], 42)

    def test_get_trace_summary(self):
        """Test getting trace summary"""
        self.recorder.record_step("step1")
        self.recorder.record_step("step2")
        
        summary = self.recorder.get_trace_summary()
        
        self.assertEqual(summary["session_id"], self.session_id)
        self.assertEqual(summary["total_steps"], 2)
        self.assertFalse(summary["pii_masking_enabled"])
        self.assertEqual(summary["jpeg_quality"], 50)
        self.assertEqual(len(summary["steps"]), 2)

    def test_jpeg_quality_bounds(self):
        """Test that JPEG quality is bounded to 1-100"""
        # Test below minimum
        recorder_low = TraceRecorder(
            session_id="test",
            trace_dir=self.temp_dir,
            jpeg_quality=0
        )
        self.assertEqual(recorder_low.jpeg_quality, 1)
        
        # Test above maximum
        recorder_high = TraceRecorder(
            session_id="test",
            trace_dir=self.temp_dir,
            jpeg_quality=150
        )
        self.assertEqual(recorder_high.jpeg_quality, 100)


class TestTraceRecorderManager(unittest.TestCase):
    """Test cases for TraceRecorderManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset manager state
        TraceRecorderManager._recorders = {}
        TraceRecorderManager._enabled = False

    def test_enable_disable(self):
        """Test enabling and disabling trace recording"""
        self.assertFalse(TraceRecorderManager.is_enabled())
        
        TraceRecorderManager.enable()
        self.assertTrue(TraceRecorderManager.is_enabled())
        
        TraceRecorderManager.disable()
        self.assertFalse(TraceRecorderManager.is_enabled())

    def test_get_recorder_disabled(self):
        """Test that get_recorder returns None when disabled"""
        recorder = TraceRecorderManager.get_recorder("session_123")
        self.assertIsNone(recorder)

    def test_get_recorder_enabled(self):
        """Test getting a recorder when enabled"""
        TraceRecorderManager.enable()
        
        recorder = TraceRecorderManager.get_recorder("session_123")
        self.assertIsNotNone(recorder)
        self.assertIsInstance(recorder, TraceRecorder)
        self.assertEqual(recorder.session_id, "session_123")

    def test_get_recorder_reuse(self):
        """Test that same recorder is returned for same session"""
        TraceRecorderManager.enable()
        
        recorder1 = TraceRecorderManager.get_recorder("session_123")
        recorder2 = TraceRecorderManager.get_recorder("session_123")
        
        self.assertIs(recorder1, recorder2)

    def test_get_recorder_different_sessions(self):
        """Test that different recorders are created for different sessions"""
        TraceRecorderManager.enable()
        
        recorder1 = TraceRecorderManager.get_recorder("session_1")
        recorder2 = TraceRecorderManager.get_recorder("session_2")
        
        self.assertIsNot(recorder1, recorder2)
        self.assertEqual(recorder1.session_id, "session_1")
        self.assertEqual(recorder2.session_id, "session_2")

    def test_finalize_session(self):
        """Test finalizing a session"""
        TraceRecorderManager.enable()
        
        recorder = TraceRecorderManager.get_recorder("session_123")
        recorder.record_step("test_step")
        
        trace_path = TraceRecorderManager.finalize_session("session_123")
        
        # Should return a path
        self.assertIsNotNone(trace_path)
        self.assertTrue(trace_path.exists())
        
        # Recorder should be removed
        self.assertNotIn("session_123", TraceRecorderManager._recorders)

    def test_finalize_session_not_found(self):
        """Test finalizing a non-existent session"""
        trace_path = TraceRecorderManager.finalize_session("nonexistent")
        self.assertIsNone(trace_path)

    def test_finalize_all(self):
        """Test finalizing all sessions"""
        TraceRecorderManager.enable()
        
        # Create multiple sessions
        recorder1 = TraceRecorderManager.get_recorder("session_1")
        recorder2 = TraceRecorderManager.get_recorder("session_2")
        recorder1.record_step("test1")
        recorder2.record_step("test2")
        
        # Finalize all
        TraceRecorderManager.finalize_all()
        
        # All recorders should be removed
        self.assertEqual(len(TraceRecorderManager._recorders), 0)

    def test_enable_with_pii_masking(self):
        """Test enabling trace recording with PII masking"""
        TraceRecorderManager.enable(enable_pii_masking=True)
        
        recorder = TraceRecorderManager.get_recorder("session_123")
        self.assertTrue(recorder.enable_pii_masking)


class TestTraceRecorderPIIMasking(unittest.TestCase):
    """Test cases for PII masking integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = TraceRecorder(
            session_id="test_pii",
            trace_dir=self.temp_dir,
            enable_pii_masking=True,
        )

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("janus.logging.trace_recorder.PIIMasker")
    def test_pii_masker_lazy_loading(self, mock_pii_masker_class):
        """Test that PII masker is lazy-loaded"""
        # PIIMasker should not be instantiated yet
        mock_pii_masker_class.assert_not_called()
        
        # Access the property
        masker = self.recorder.pii_masker
        
        # Now it should be instantiated
        mock_pii_masker_class.assert_called_once_with(blur_radius=15)

    @patch("janus.logging.trace_recorder.OCREngine")
    def test_ocr_engine_lazy_loading(self, mock_ocr_class):
        """Test that OCR engine is lazy-loaded"""
        # OCREngine should not be instantiated yet
        mock_ocr_class.assert_not_called()
        
        # Access the property
        engine = self.recorder.ocr_engine
        
        # Now it should be instantiated
        mock_ocr_class.assert_called_once()

    def test_pii_masking_disabled_by_default(self):
        """Test that PII masking is disabled by default"""
        recorder = TraceRecorder(
            session_id="test",
            trace_dir=self.temp_dir,
            enable_pii_masking=False,
        )
        
        # Accessing pii_masker should return None when disabled
        self.assertIsNone(recorder.pii_masker)


if __name__ == "__main__":
    unittest.main()
