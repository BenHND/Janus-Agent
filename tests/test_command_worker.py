"""
Tests for command_worker module.

TICKET-P3-01: UI Asynchronous Non-Blocking

These tests verify that:
1. CommandWorker emits correct signals during processing
2. RecordingWorker handles audio recording/transcription
3. Workers can be stopped gracefully
4. Signals are thread-safe for UI updates
"""

import asyncio
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest


# Check if PySide6 is available and can be used
PYSIDE6_AVAILABLE = False
PYSIDE6_IMPORT_ERROR = None

try:
    from PySide6.QtCore import QCoreApplication, QTimer
    from PySide6.QtWidgets import QApplication
    # Try creating an application to verify PySide6 works
    if QApplication.instance() is None:
        app = QApplication([])
    PYSIDE6_AVAILABLE = True
except Exception as e:
    PYSIDE6_IMPORT_ERROR = str(e)


# Create a marker decorator
skip_no_pyside6 = pytest.mark.skipif(
    not PYSIDE6_AVAILABLE,
    reason=f"PySide6 not available or cannot initialize: {PYSIDE6_IMPORT_ERROR}"
)


@skip_no_pyside6
class TestCommandWorkerSignals(unittest.TestCase):
    """Test CommandWorker signal emissions."""
    
    def test_command_worker_imports(self):
        """Test that CommandWorker can be imported."""
        from janus.ui.command_worker import CommandWorker, CommandWorkerSignals
        
        self.assertIsNotNone(CommandWorker)
        self.assertIsNotNone(CommandWorkerSignals)
    
    def test_command_worker_signals_defined(self):
        """Test that CommandWorkerSignals has all required signals."""
        from janus.ui.command_worker import CommandWorkerSignals
        
        signals = CommandWorkerSignals()
        
        # Check all signals exist
        self.assertTrue(hasattr(signals, 'started'))
        self.assertTrue(hasattr(signals, 'thinking'))
        self.assertTrue(hasattr(signals, 'acting'))
        self.assertTrue(hasattr(signals, 'finished'))
        self.assertTrue(hasattr(signals, 'error'))
        self.assertTrue(hasattr(signals, 'transcript'))
    
    def test_command_worker_initialization(self):
        """Test CommandWorker initialization."""
        from janus.ui.command_worker import CommandWorker
        
        mock_pipeline = Mock()
        worker = CommandWorker(
            pipeline=mock_pipeline,
            command="test command",
            mock_execution=True
        )
        
        self.assertEqual(worker.pipeline, mock_pipeline)
        self.assertEqual(worker.command, "test command")
        self.assertTrue(worker.mock_execution)
        self.assertFalse(worker._stopped)
    
    def test_command_worker_stop(self):
        """Test CommandWorker stop method."""
        from janus.ui.command_worker import CommandWorker
        
        mock_pipeline = Mock()
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        
        self.assertFalse(worker.is_stopped())
        worker.stop()
        self.assertTrue(worker.is_stopped())


@skip_no_pyside6
class TestRecordingWorker(unittest.TestCase):
    """Test RecordingWorker."""
    
    def test_recording_worker_imports(self):
        """Test that RecordingWorker can be imported."""
        from janus.ui.command_worker import RecordingWorker
        
        self.assertIsNotNone(RecordingWorker)
    
    def test_recording_worker_initialization(self):
        """Test RecordingWorker initialization."""
        from janus.ui.command_worker import RecordingWorker
        
        mock_stt = Mock()
        worker = RecordingWorker(
            stt=mock_stt,
            language="fr",
            max_duration=10.0
        )
        
        self.assertEqual(worker.stt, mock_stt)
        self.assertEqual(worker.language, "fr")
        self.assertEqual(worker.max_duration, 10.0)
        self.assertFalse(worker._stopped)
    
    def test_recording_worker_stop(self):
        """Test RecordingWorker stop method."""
        from janus.ui.command_worker import RecordingWorker
        
        mock_stt = Mock()
        worker = RecordingWorker(stt=mock_stt, language="en")
        
        worker.stop()
        
        self.assertTrue(worker._stopped)
        mock_stt.stop_listening.assert_called_once()


@skip_no_pyside6
class TestCommandWorkerExecution(unittest.TestCase):
    """Test CommandWorker execution with mocked pipeline."""
    
    def test_command_worker_emits_thinking_signal(self):
        """Test that CommandWorker emits thinking signal."""
        from janus.ui.command_worker import CommandWorker
        
        # Create mock result
        mock_result = Mock()
        mock_result.success = True
        mock_result.action_results = []
        mock_result.error = None
        
        mock_pipeline = Mock()
        mock_pipeline.process_command_with_conversation.return_value = (mock_result, None)
        
        worker = CommandWorker(
            pipeline=mock_pipeline,
            command="test command"
        )
        
        # Track signal emissions
        thinking_emitted = []
        worker.signals.thinking.connect(lambda: thinking_emitted.append(True))
        
        # Run the worker
        worker.run()
        
        # Verify thinking signal was emitted
        self.assertEqual(len(thinking_emitted), 1)
        mock_pipeline.process_command_with_conversation.assert_called_once_with(
            "test command",
            mock_execution=False
        )
    
    def test_command_worker_emits_finished_signal(self):
        """Test that CommandWorker emits finished signal with result."""
        from janus.ui.command_worker import CommandWorker
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.action_results = []
        
        mock_pipeline = Mock()
        mock_pipeline.process_command_with_conversation.return_value = (mock_result, None)
        
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        
        # Track signal emissions
        finished_args = []
        worker.signals.finished.connect(lambda r, c: finished_args.append((r, c)))
        
        worker.run()
        
        self.assertEqual(len(finished_args), 1)
        self.assertEqual(finished_args[0][0], mock_result)
        self.assertIsNone(finished_args[0][1])
    
    def test_command_worker_emits_error_on_exception(self):
        """Test that CommandWorker emits error signal on exception."""
        from janus.ui.command_worker import CommandWorker
        
        mock_pipeline = Mock()
        mock_pipeline.process_command_with_conversation.side_effect = Exception("Test error")
        
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        
        # Track signal emissions
        error_msgs = []
        worker.signals.error.connect(lambda msg: error_msgs.append(msg))
        
        worker.run()
        
        self.assertEqual(len(error_msgs), 1)
        self.assertIn("Test error", error_msgs[0])
    
    def test_command_worker_stops_early_if_stopped(self):
        """Test that CommandWorker respects stop flag."""
        from janus.ui.command_worker import CommandWorker
        
        mock_pipeline = Mock()
        
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        worker.stop()  # Stop before running
        
        worker.run()
        
        # Pipeline should not be called
        mock_pipeline.process_command_with_conversation.assert_not_called()


@skip_no_pyside6
class TestUIResponsiveness(unittest.TestCase):
    """
    Test that UI remains responsive during command processing.
    
    TICKET-P3-01: Definition of Done:
    - Window can be moved while agent waits for LLM response
    - Stop button can be clicked during LLM processing
    """
    
    def test_worker_runs_in_separate_thread(self):
        """Test that CommandWorker runs in a separate thread."""
        from janus.ui.command_worker import CommandWorker
        import threading
        
        main_thread_id = threading.current_thread().ident
        worker_thread_id = [None]
        
        # Create a slow pipeline mock
        def slow_process(*args, **kwargs):
            worker_thread_id[0] = threading.current_thread().ident
            time.sleep(0.1)
            mock_result = Mock()
            mock_result.success = True
            mock_result.action_results = []
            return (mock_result, None)
        
        mock_pipeline = Mock()
        mock_pipeline.process_command_with_conversation.side_effect = slow_process
        
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        
        # Start worker thread
        worker.start()
        worker.wait()  # Wait for completion
        
        # Verify worker ran in a different thread
        self.assertIsNotNone(worker_thread_id[0])
        self.assertNotEqual(worker_thread_id[0], main_thread_id)
    
    def test_worker_can_be_stopped(self):
        """Test that worker can be stopped from main thread."""
        from janus.ui.command_worker import CommandWorker
        
        # Create a very slow pipeline mock
        def very_slow_process(*args, **kwargs):
            time.sleep(10)  # Very long operation
            mock_result = Mock()
            mock_result.success = True
            mock_result.action_results = []
            return (mock_result, None)
        
        mock_pipeline = Mock()
        mock_pipeline.process_command_with_conversation.side_effect = very_slow_process
        
        worker = CommandWorker(pipeline=mock_pipeline, command="test")
        
        # Start worker
        worker.start()
        
        # Immediately stop from main thread
        worker.stop()
        
        # Wait a bit for stop to take effect
        worker.wait(100)  # 100ms timeout
        
        # Worker should have stopped flag set
        self.assertTrue(worker.is_stopped())


class TestCommandWorkerWithoutPySide6(unittest.TestCase):
    """
    Basic tests that don't require PySide6.
    These tests verify the module structure and error handling.
    """
    
    def test_module_can_be_imported_on_systems_with_pyside6(self):
        """Test that the module exists and has expected structure."""
        # This test runs regardless of PySide6 availability
        # It just checks the file exists
        import os
        worker_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "janus",
            "ui",
            "command_worker.py"
        )
        self.assertTrue(os.path.exists(worker_path))
    
    def test_overlay_types_importable(self):
        """Test that overlay types can be imported without PySide6."""
        # MicState and StatusState should be importable without PySide6
        from janus.ui.overlay_types import MicState, StatusState
        
        self.assertEqual(MicState.THINKING.value, "thinking")
        self.assertEqual(StatusState.ACTING.value, "acting")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
