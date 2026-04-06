"""
Tests for WhisperRecorder with ring buffer and pre-roll functionality (TICKET-XX)

Tests cover:
- Ring buffer functionality
- Audio reader thread operation
- Pre-roll snapshot retrieval
- Recording with queue consumption
- Silence detection and timeout handling
- Thread lifecycle and cleanup
"""

import queue
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch, call

# Mock heavy dependencies before imports
sys.modules["pyaudio"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["psutil"] = MagicMock()

# Mock logger
mock_logger = MagicMock()
sys.modules["janus.logging"] = MagicMock()
sys.modules["janus.logging"].get_logger = MagicMock(return_value=mock_logger)

from janus.io.stt.whisper_recorder import (
    WhisperRecorder,
    _RingBuffer,
    MIN_FRAMES_REQUIRED,
)


# Test constants
TEST_CHUNK_COUNT_SUFFICIENT = 15  # Enough chunks to pass minimum requirement


class TestRingBuffer(unittest.TestCase):
    """Test the ring buffer implementation"""

    def test_ring_buffer_init(self):
        """Test ring buffer initialization"""
        rb = _RingBuffer(capacity=5)
        self.assertEqual(rb.capacity, 5)
        self.assertEqual(len(rb.buffer), 5)
        self.assertEqual(rb.index, 0)
        self.assertFalse(rb.filled)

    def test_ring_buffer_append_not_full(self):
        """Test appending when buffer not full"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")

        self.assertEqual(rb.index, 2)
        self.assertFalse(rb.filled)

    def test_ring_buffer_append_full(self):
        """Test appending when buffer becomes full"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.append(b"chunk3")

        self.assertEqual(rb.index, 0)
        self.assertTrue(rb.filled)

    def test_ring_buffer_wraps_around(self):
        """Test buffer wraps around correctly"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.append(b"chunk3")
        rb.append(b"chunk4")  # Should overwrite chunk1

        self.assertEqual(rb.index, 1)
        self.assertTrue(rb.filled)

    def test_ring_buffer_snapshot_not_full(self):
        """Test snapshot when buffer not full"""
        rb = _RingBuffer(capacity=5)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.append(b"chunk3")

        snapshot = rb.get_snapshot()
        self.assertEqual(len(snapshot), 3)
        self.assertEqual(snapshot, [b"chunk1", b"chunk2", b"chunk3"])

    def test_ring_buffer_snapshot_full(self):
        """Test snapshot when buffer is full"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.append(b"chunk3")

        snapshot = rb.get_snapshot()
        self.assertEqual(len(snapshot), 3)
        self.assertEqual(snapshot, [b"chunk1", b"chunk2", b"chunk3"])

    def test_ring_buffer_snapshot_after_wrap(self):
        """Test snapshot returns chunks in correct order after wrap"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.append(b"chunk3")
        rb.append(b"chunk4")  # Overwrites chunk1
        rb.append(b"chunk5")  # Overwrites chunk2

        snapshot = rb.get_snapshot()
        # Should return in chronological order: chunk3, chunk4, chunk5
        self.assertEqual(len(snapshot), 3)
        self.assertEqual(snapshot, [b"chunk3", b"chunk4", b"chunk5"])

    def test_ring_buffer_clear(self):
        """Test clearing the ring buffer"""
        rb = _RingBuffer(capacity=3)
        rb.append(b"chunk1")
        rb.append(b"chunk2")
        rb.clear()

        self.assertEqual(rb.index, 0)
        self.assertFalse(rb.filled)
        self.assertEqual(len(rb.get_snapshot()), 0)


class TestWhisperRecorderPreroll(unittest.TestCase):
    """Test WhisperRecorder with pre-roll and threading"""

    def setUp(self):
        """Set up test fixtures with mocked PyAudio"""
        # Create mock PyAudio and stream
        self.mock_pyaudio_class = MagicMock()
        self.mock_audio_instance = MagicMock()
        self.mock_stream = MagicMock()

        # Configure stream behavior
        self.mock_stream.is_active.return_value = True
        self.mock_stream.read.return_value = b"\x00" * 640  # 20ms at 16kHz

        # Configure PyAudio instance
        self.mock_audio_instance.open.return_value = self.mock_stream
        self.mock_audio_instance.get_sample_size.return_value = 2  # 16-bit
        self.mock_pyaudio_class.return_value = self.mock_audio_instance

        # Patch PyAudio
        self.patcher = patch("janus.stt.whisper_recorder.pyaudio.PyAudio", self.mock_pyaudio_class)
        self.patcher.start()

        # Patch numpy for energy calculation
        self.mock_np = MagicMock()
        self.mock_np.frombuffer.return_value = MagicMock()
        self.mock_np.mean.return_value = 100.0
        self.mock_np.sqrt.return_value = 10.0
        self.patcher_np = patch("janus.stt.whisper_recorder.np", self.mock_np)
        self.patcher_np.start()

    def tearDown(self):
        """Clean up patches"""
        self.patcher.stop()
        self.patcher_np.stop()

    def test_recorder_init_creates_thread(self):
        """Test that recorder initializes thread on creation"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Thread should be created and started
        self.assertIsNotNone(recorder._reader_thread)
        self.assertTrue(recorder._reader_thread.is_alive())
        self.assertTrue(recorder._reader_thread.daemon)

        # Cleanup
        recorder._stop_thread.set()
        recorder._reader_thread.join(timeout=1.0)

    def test_recorder_init_creates_ring_buffer(self):
        """Test that recorder creates ring buffer with correct size"""
        # 300ms at 20ms chunks = 15 chunks
        recorder = WhisperRecorder(
            sample_rate=16000, chunk_duration_ms=20, preroll_duration_ms=300
        )

        self.assertIsNotNone(recorder._ring_buffer)
        self.assertEqual(recorder._ring_buffer.capacity, 15)

        # Cleanup
        recorder._stop_thread.set()

    def test_recorder_opens_persistent_stream_once(self):
        """Test that stream is opened once on init"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Stream should be opened exactly once
        self.mock_audio_instance.open.assert_called_once()

        # Verify stream parameters
        call_kwargs = self.mock_audio_instance.open.call_args[1]
        self.assertEqual(call_kwargs["rate"], 16000)
        self.assertEqual(call_kwargs["channels"], 1)
        self.assertTrue(call_kwargs["input"])

        # Cleanup
        recorder._stop_thread.set()

    def test_preroll_snapshot_returns_chunks(self):
        """Test that pre-roll snapshot returns buffered chunks"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Stop reader thread first to avoid interference
        recorder._stop_thread.set()
        recorder._reader_thread.join(timeout=1.0)

        # Clear ring buffer
        recorder._ring_buffer.clear()

        # Simulate some chunks in ring buffer
        recorder._ring_buffer.append(b"chunk1")
        recorder._ring_buffer.append(b"chunk2")
        recorder._ring_buffer.append(b"chunk3")

        snapshot = recorder._get_preroll_snapshot()

        self.assertEqual(len(snapshot), 3)
        self.assertEqual(snapshot, [b"chunk1", b"chunk2", b"chunk3"])

    def test_recording_activates_queue_filling(self):
        """Test that starting recording activates queue filling"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Initially recording should be inactive
        self.assertFalse(recorder._recording_active)

        # Simulate starting a recording (this is done in record_audio)
        with recorder._recording_lock:
            recorder._recording_active = True

        self.assertTrue(recorder._recording_active)

        # Cleanup
        recorder._stop_thread.set()

    @patch("janus.stt.whisper_recorder.Path")
    @patch("janus.stt.whisper_recorder.wave")
    @patch("janus.stt.whisper_recorder.tempfile")
    def test_record_audio_includes_preroll(
        self, mock_tempfile_module, mock_wave_module, mock_path_module
    ):
        """Test that record_audio includes pre-roll data"""
        # Setup mocks
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test.wav"
        mock_tempfile_module.NamedTemporaryFile.return_value.__enter__.return_value = mock_temp

        mock_wave_file = MagicMock()
        mock_wave_module.open.return_value.__enter__.return_value = mock_wave_file

        mock_path = MagicMock()
        mock_path_module.return_value = mock_path

        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Stop the reader thread to control the test
        recorder._stop_thread.set()
        recorder._reader_thread.join(timeout=1.0)

        # Pre-populate ring buffer
        recorder._ring_buffer.clear()
        recorder._ring_buffer.append(b"preroll1")
        recorder._ring_buffer.append(b"preroll2")

        # Mock queue to provide some chunks then stop
        def queue_get_side_effect(timeout=None):
            if not hasattr(queue_get_side_effect, "count"):
                queue_get_side_effect.count = 0
            queue_get_side_effect.count += 1

            if queue_get_side_effect.count <= MIN_FRAMES_REQUIRED:
                return b"chunk" + str(queue_get_side_effect.count).encode()
            else:
                raise queue.Empty()

        # Patch shutil inside the function
        with patch("shutil.copy2"):
            with patch.object(
                recorder._recording_queue, "get", side_effect=queue_get_side_effect
            ):
                audio_path, error = recorder.record_audio(max_duration=1)

        # Should succeed
        self.assertIsNotNone(audio_path)
        self.assertIsNone(error)

        # Verify recording was deactivated
        self.assertFalse(recorder._recording_active)

    def test_stop_listening_interrupts_recording(self):
        """Test that stop_listening flag interrupts recording"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Start recording in a thread
        def do_recording():
            with patch("janus.stt.whisper_recorder.tempfile.NamedTemporaryFile"):
                with patch("janus.stt.whisper_recorder.wave.open"):
                    with patch("janus.stt.whisper_recorder.Path"):
                        recorder.record_audio(max_duration=10)

        record_thread = threading.Thread(target=do_recording)
        record_thread.start()

        # Give it a moment to start
        time.sleep(0.2)

        # Stop listening
        recorder.stop_listening()

        # Recording should complete quickly
        record_thread.join(timeout=2.0)
        self.assertFalse(record_thread.is_alive())

        # Cleanup
        recorder._stop_thread.set()

    def test_thread_stops_on_cleanup(self):
        """Test that reader thread stops when recorder is deleted"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        thread = recorder._reader_thread
        self.assertTrue(thread.is_alive())

        # Trigger cleanup via close()
        recorder.close()

        # Thread should stop
        thread.join(timeout=3.0)
        self.assertFalse(thread.is_alive())

    def test_close_method_is_idempotent(self):
        """Test that close() can be called multiple times safely"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Close multiple times should not raise
        recorder.close()
        recorder.close()
        recorder.close()

        # Thread should be stopped
        self.assertFalse(recorder._reader_thread.is_alive())

    def test_no_indefinite_blocking(self):
        """Test that record_audio doesn't block indefinitely"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Mock queue to always be empty (simulates no audio)
        with patch.object(recorder._recording_queue, "get", side_effect=queue.Empty()):
            with patch("janus.stt.whisper_recorder.tempfile.NamedTemporaryFile"):
                with patch("janus.stt.whisper_recorder.wave.open"):
                    with patch("janus.stt.whisper_recorder.Path"):
                        start_time = time.time()
                        audio_path, error = recorder.record_audio(max_duration=1)
                        elapsed = time.time() - start_time

        # Should timeout and not block indefinitely
        # Allow some margin for processing
        self.assertLess(elapsed, 5.0)

        # Cleanup
        recorder._stop_thread.set()

    def test_stream_not_available_returns_error(self):
        """Test that recording returns error if stream not available"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Simulate stream not available
        recorder.stream = None

        audio_path, error = recorder.record_audio(max_duration=1)

        self.assertIsNone(audio_path)
        self.assertIsNotNone(error)
        self.assertIn("stream not available", error.lower())

    @patch("janus.stt.whisper_recorder.Path")
    @patch("janus.stt.whisper_recorder.wave")
    @patch("janus.stt.whisper_recorder.tempfile")
    def test_multiple_recording_cycles(
        self, mock_tempfile_module, mock_wave_module, mock_path_module
    ):
        """Test multiple start/record cycles"""
        # Setup mocks
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test.wav"
        mock_tempfile_module.NamedTemporaryFile.return_value.__enter__.return_value = mock_temp

        mock_wave_file = MagicMock()
        mock_wave_module.open.return_value.__enter__.return_value = mock_wave_file

        mock_path = MagicMock()
        mock_path_module.return_value = mock_path

        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Mock queue to provide chunks
        def get_chunks(timeout=None, block=True):
            if not hasattr(get_chunks, "count"):
                get_chunks.count = 0
            get_chunks.count += 1
            if get_chunks.count <= TEST_CHUNK_COUNT_SUFFICIENT:
                return b"chunk"
            raise queue.Empty()

        with patch("shutil.copy2"):
            # Cycle 1
            with patch.object(recorder._recording_queue, "get", side_effect=get_chunks):
                recorder.start_listening()
                audio_path, error = recorder.record_audio(max_duration=1)
                self.assertIsNotNone(audio_path)

            # Reset for cycle 2
            get_chunks.count = 0

            # Cycle 2
            with patch.object(recorder._recording_queue, "get", side_effect=get_chunks):
                recorder.start_listening()
                audio_path, error = recorder.record_audio(max_duration=1)
                self.assertIsNotNone(audio_path)

        # Cleanup
        recorder._stop_thread.set()


class TestAudioReaderThread(unittest.TestCase):
    """Test the audio reader thread behavior"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock PyAudio
        self.mock_pyaudio_class = MagicMock()
        self.mock_audio_instance = MagicMock()
        self.mock_stream = MagicMock()

        self.mock_stream.is_active.return_value = True
        self.mock_stream.read.return_value = b"\x00" * 640

        self.mock_audio_instance.open.return_value = self.mock_stream
        self.mock_pyaudio_class.return_value = self.mock_audio_instance

        self.patcher = patch("janus.stt.whisper_recorder.pyaudio.PyAudio", self.mock_pyaudio_class)
        self.patcher.start()

        # Patch numpy
        mock_np = MagicMock()
        mock_np.frombuffer.return_value = MagicMock()
        mock_np.mean.return_value = 100.0
        mock_np.sqrt.return_value = 10.0
        self.patcher_np = patch("janus.stt.whisper_recorder.np", mock_np)
        self.patcher_np.start()

    def tearDown(self):
        """Clean up patches"""
        self.patcher.stop()
        self.patcher_np.stop()

    def test_thread_fills_ring_buffer(self):
        """Test that reader thread fills ring buffer continuously"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Wait for thread to read some chunks
        time.sleep(0.3)

        # Ring buffer should have some data
        snapshot = recorder._get_preroll_snapshot()
        self.assertGreater(len(snapshot), 0)

        # Cleanup
        recorder._stop_thread.set()
        recorder._reader_thread.join(timeout=1.0)

    def test_thread_fills_queue_when_recording_active(self):
        """Test that thread fills recording queue when active"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        # Activate recording
        with recorder._recording_lock:
            recorder._recording_active = True

        # Wait for chunks
        time.sleep(0.2)

        # Queue should have chunks
        self.assertFalse(recorder._recording_queue.empty())

        # Deactivate
        with recorder._recording_lock:
            recorder._recording_active = False

        # Cleanup
        recorder._stop_thread.set()
        recorder._reader_thread.join(timeout=1.0)

    def test_thread_stops_cleanly(self):
        """Test that thread stops when stop event is set"""
        recorder = WhisperRecorder(sample_rate=16000, chunk_duration_ms=20)

        thread = recorder._reader_thread
        self.assertTrue(thread.is_alive())

        # Signal stop
        recorder._stop_thread.set()

        # Thread should stop
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
