"""
Unit tests for AudioLogger
"""
import os
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from janus.io.stt.audio_logger import AudioLogger


class TestAudioLogger(unittest.TestCase):
    """Test cases for AudioLogger"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = AudioLogger(log_dir=self.temp_dir, max_logs=10)

        # Create a dummy audio file for testing
        self.test_audio = os.path.join(self.temp_dir, "test_audio.wav")
        self._create_dummy_audio(self.test_audio)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_dummy_audio(self, path):
        """Create a dummy WAV file for testing"""
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)  # 1 second of silence

    def test_log_directory_creation(self):
        """Test that log directories are created"""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertTrue((Path(self.temp_dir) / "audio").exists())
        self.assertTrue((Path(self.temp_dir) / "transcripts").exists())

    def test_log_transcription_success(self):
        """Test logging a successful transcription"""
        log_id = self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="test raw text",
            corrected_transcription="test corrected text",
            normalized_transcription="test normalized text",
            language="fr",
            model="base",
        )

        self.assertIsNotNone(log_id)

        # Verify log can be retrieved
        log = self.logger.get_log(log_id)
        self.assertIsNotNone(log)
        self.assertEqual(log["raw_transcription"], "test raw text")
        self.assertEqual(log["corrected_transcription"], "test corrected text")
        self.assertTrue(log["success"])

    def test_log_transcription_failure(self):
        """Test logging a failed transcription"""
        log_id = self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="",
            language="fr",
            model="base",
            error="Test error message",
        )

        log = self.logger.get_log(log_id)
        self.assertIsNotNone(log)
        self.assertFalse(log["success"])
        self.assertEqual(log["error"], "Test error message")

    def test_audio_file_saved(self):
        """Test that audio files are saved"""
        log_id = self.logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="test", language="fr", model="base"
        )

        # Check that audio file was copied
        log = self.logger.get_log(log_id)
        audio_path = log["audio_path"]
        self.assertTrue(Path(audio_path).exists())

    def test_audio_save_disabled(self):
        """Test logging with audio save disabled"""
        logger = AudioLogger(log_dir=self.temp_dir + "_no_audio", enable_audio_save=False)

        log_id = logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="test", language="fr", model="base"
        )

        log = logger.get_log(log_id)
        # Audio path should be original path, not saved
        self.assertEqual(log["audio_path"], self.test_audio)

    def test_get_recent_logs(self):
        """Test retrieving recent logs"""
        # Create multiple logs
        for i in range(5):
            self.logger.log_transcription(
                audio_path=self.test_audio,
                raw_transcription=f"test {i}",
                language="fr",
                model="base",
            )

        recent = self.logger.get_recent_logs(count=3)
        self.assertEqual(len(recent), 3)

        # Should be in reverse chronological order
        self.assertIn("test 4", recent[0]["raw_transcription"])

    def test_search_logs_by_query(self):
        """Test searching logs by text query"""
        # Create logs with different text
        self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="open chrome browser",
            language="en",
            model="base",
        )

        self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="close firefox window",
            language="en",
            model="base",
        )

        # Search for "chrome"
        results = self.logger.search_logs(query="chrome")
        self.assertEqual(len(results), 1)
        self.assertIn("chrome", results[0]["raw_transcription"])

    def test_search_logs_by_language(self):
        """Test searching logs by language"""
        self.logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="test french", language="fr", model="base"
        )

        self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="test english",
            language="en",
            model="base",
        )

        results = self.logger.search_logs(language="fr")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["language"], "fr")

    def test_search_logs_success_only(self):
        """Test searching only successful logs"""
        self.logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="success", language="fr", model="base"
        )

        self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="",
            language="fr",
            model="base",
            error="Test error",
        )

        results = self.logger.search_logs(success_only=True)
        self.assertTrue(all(log["success"] for log in results))

    def test_max_logs_cleanup(self):
        """Test that old logs are cleaned up when max is reached"""
        logger = AudioLogger(log_dir=self.temp_dir + "_cleanup", max_logs=5)

        # Create 10 logs
        for i in range(10):
            logger.log_transcription(
                audio_path=self.test_audio,
                raw_transcription=f"test {i}",
                language="fr",
                model="base",
            )

        # Should only have 5 logs
        stats = logger.get_statistics()
        self.assertEqual(stats["current_logs"], 5)

        # Total should be 10 (all created)
        self.assertEqual(stats["total_logs"], 10)

    def test_get_statistics(self):
        """Test getting logger statistics"""
        # Create some logs
        self.logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="success 1", language="fr", model="base"
        )

        self.logger.log_transcription(
            audio_path=self.test_audio,
            raw_transcription="",
            language="fr",
            model="base",
            error="Test error",
        )

        stats = self.logger.get_statistics()

        self.assertEqual(stats["total_logs"], 2)
        self.assertEqual(stats["successful"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["success_rate"], 0.5)

    def test_export_logs_json(self):
        """Test exporting logs to JSON"""
        self.logger.log_transcription(
            audio_path=self.test_audio, raw_transcription="test export", language="fr", model="base"
        )

        export_path = os.path.join(self.temp_dir, "export.json")
        self.logger.export_logs(export_path, format="json")

        self.assertTrue(Path(export_path).exists())

        # Verify it's valid JSON
        import json

        with open(export_path, "r") as f:
            data = json.load(f)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)


if __name__ == "__main__":
    unittest.main()
