"""
Unit tests for Phase 16 modules
Tests: RealtimeSTTEngine, NaturalReformatter, VoiceAdaptationCache
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from janus.io.stt.natural_reformatter import ReformattedResult, RuleBasedReformatter
from janus.io.stt.voice_adaptation_cache import CacheEntry, VoiceAdaptationCache


class TestNaturalReformatter(unittest.TestCase):
    """Test cases for NaturalReformatter"""

    def setUp(self):
        """Set up test fixtures"""
        self.reformatter = RuleBasedReformatter()

    def test_french_filler_removal(self):
        """Test French filler word removal"""
        test_cases = [
            ("euh ouvre le navigateur", "Ouvre le navigateur"),
            ("euh euh je veux ouvrir vscode", "Je veux ouvrir vscode"),
            ("alors euh lance le terminal", "Lance le terminal"),
            ("ben ferme la fenêtre", "Ferme la fenêtre"),
        ]

        for input_text, expected in test_cases:
            result = self.reformatter.reformat(input_text, language="fr")
            self.assertEqual(result.reformatted, expected)
            self.assertEqual(result.method, "rule-based")

    def test_english_filler_removal(self):
        """Test English filler word removal"""
        test_cases = [
            ("uh open the browser", "Open the browser"),
            ("um um I want to open vscode", "I want to open vscode"),
            ("well like launch the terminal", "Launch the terminal"),
            ("you know close the window", "Close the window"),
        ]

        for input_text, expected in test_cases:
            result = self.reformatter.reformat(input_text, language="en")
            self.assertEqual(result.reformatted, expected)
            self.assertEqual(result.method, "rule-based")

    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        input_text = "ouvre   le    navigateur"
        result = self.reformatter.reformat(input_text, language="fr")
        self.assertEqual(result.reformatted, "Ouvre le navigateur")

    def test_capitalization(self):
        """Test first letter capitalization"""
        input_text = "ouvre le navigateur"
        result = self.reformatter.reformat(input_text, language="fr")
        self.assertTrue(result.reformatted[0].isupper())

    def test_repeated_word_removal(self):
        """Test removal of repeated words"""
        input_text = "ouvre le le navigateur"
        result = self.reformatter.reformat(input_text, language="fr")
        self.assertNotIn("le le", result.reformatted.lower())

    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.reformatter.reformat("", language="fr")
        self.assertEqual(result.reformatted, "")

    def test_performance(self):
        """Test reformatter performance"""
        input_text = "euh ouvre le navigateur"
        result = self.reformatter.reformat(input_text, language="fr")

        # Should be very fast (< 10ms)
        self.assertLess(result.duration_ms, 10.0)

    def test_statistics(self):
        """Test statistics tracking"""
        self.reformatter.reformat("test 1", language="fr")
        self.reformatter.reformat("test 2", language="fr")

        stats = self.reformatter.get_statistics()
        self.assertEqual(stats["total_reformats"], 2)
        self.assertGreater(stats["avg_latency_ms"], 0)

    def test_technical_terms_preserved(self):
        """Test that technical terms are not modified"""
        technical_terms = ["vscode", "github", "firefox", "terminal"]

        for term in technical_terms:
            input_text = f"euh ouvre {term}"
            result = self.reformatter.reformat(input_text, language="fr")
            self.assertIn(term, result.reformatted.lower())


class TestVoiceAdaptationCache(unittest.TestCase):
    """Test cases for VoiceAdaptationCache"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.cache = VoiceAdaptationCache(
            db_path=self.temp_db.name,
            user_id="test_user",
            enable_encryption=False,  # Disable for testing simplicity
        )

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            Path(self.temp_db.name).unlink()
        except:
            pass

    def test_add_correction(self):
        """Test adding corrections to cache"""
        audio_data = b"test_audio_data"
        raw_text = "euh ouvre vs code"
        corrected_text = "Ouvre VSCode"

        success = self.cache.add_correction(audio_data, raw_text, corrected_text, language="fr")

        self.assertTrue(success)

        # Verify it was added
        stats = self.cache.get_statistics()
        self.assertEqual(stats["total_entries"], 1)

    def test_get_correction_exact_match(self):
        """Test retrieving correction with exact audio match"""
        audio_data = b"test_audio_data"
        raw_text = "euh ouvre vs code"
        corrected_text = "Ouvre VSCode"

        self.cache.add_correction(audio_data, raw_text, corrected_text, language="fr")

        # Get correction
        result = self.cache.get_correction(audio_data)
        self.assertEqual(result, corrected_text)

        # Check stats
        stats = self.cache.get_statistics()
        self.assertEqual(stats["cache_hits"], 1)

    def test_get_correction_miss(self):
        """Test cache miss"""
        audio_data = b"nonexistent_audio"
        result = self.cache.get_correction(audio_data)

        self.assertIsNone(result)

        stats = self.cache.get_statistics()
        self.assertEqual(stats["cache_misses"], 1)

    def test_fuzzy_matching(self):
        """Test fuzzy text matching with Levenshtein distance"""
        audio_data = b"test_audio_1"
        self.cache.add_correction(audio_data, "ouvre vs code", "Ouvre VSCode", language="fr")

        # Search for similar
        similar = self.cache.find_similar_corrections("ouvre vscode")

        self.assertGreater(len(similar), 0)
        self.assertLess(similar[0]["distance"], 0.2)
        self.assertEqual(similar[0]["corrected_text"], "Ouvre VSCode")

    def test_multiple_corrections(self):
        """Test adding multiple corrections"""
        corrections = [
            (b"audio_1", "text 1", "corrected 1", "fr"),
            (b"audio_2", "text 2", "corrected 2", "fr"),
            (b"audio_3", "text 3", "corrected 3", "en"),
        ]

        for audio, raw, corrected, lang in corrections:
            self.cache.add_correction(audio, raw, corrected, lang)

        # Check all were added
        entries = self.cache.get_all_corrections()
        self.assertEqual(len(entries), 3)

    def test_use_count_increment(self):
        """Test that use count increments on retrieval"""
        audio_data = b"test_audio"
        self.cache.add_correction(audio_data, "text", "corrected", "fr")

        # Retrieve multiple times
        for _ in range(3):
            self.cache.get_correction(audio_data)

        # Check use count
        entries = self.cache.get_all_corrections()
        self.assertEqual(entries[0].use_count, 3)

    def test_delete_correction(self):
        """Test deleting a correction"""
        audio_data = b"test_audio"
        self.cache.add_correction(audio_data, "text", "corrected", "fr")

        entries = self.cache.get_all_corrections()
        entry_id = entries[0].id

        # Delete
        success = self.cache.delete_correction(entry_id)
        self.assertTrue(success)

        # Verify deleted
        entries = self.cache.get_all_corrections()
        self.assertEqual(len(entries), 0)

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries"""
        # Add entry with old timestamp
        self.cache.add_correction(b"old_audio", "old", "old_corrected", "fr")

        # Cleanup entries older than 0 days (should delete)
        deleted = self.cache.cleanup_old_entries(days=0)

        self.assertGreater(deleted, 0)

        entries = self.cache.get_all_corrections()
        self.assertEqual(len(entries), 0)

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation"""
        # Test exact match
        distance = self.cache._levenshtein_distance("hello", "hello")
        self.assertEqual(distance, 0)

        # Test single character change
        distance = self.cache._levenshtein_distance("hello", "hallo")
        self.assertEqual(distance, 1)

        # Test insertion
        distance = self.cache._levenshtein_distance("hello", "helllo")
        self.assertEqual(distance, 1)

        # Test deletion
        distance = self.cache._levenshtein_distance("hello", "helo")
        self.assertEqual(distance, 1)

    def test_statistics(self):
        """Test statistics tracking"""
        audio_data = b"test_audio"
        self.cache.add_correction(audio_data, "text", "corrected", "fr")
        self.cache.get_correction(audio_data)  # Hit
        self.cache.get_correction(b"nonexistent")  # Miss

        stats = self.cache.get_statistics()

        self.assertEqual(stats["total_entries"], 1)
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(stats["cache_misses"], 1)
        self.assertEqual(stats["entries_added"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)

    def test_export_corrections(self):
        """Test exporting corrections to JSON"""
        self.cache.add_correction(b"audio_1", "text 1", "corrected 1", "fr")
        self.cache.add_correction(b"audio_2", "text 2", "corrected 2", "en")

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_path.close()

        try:
            success = self.cache.export_corrections(output_path.name)
            self.assertTrue(success)

            # Verify file exists and has content
            import json

            data = json.loads(Path(output_path.name).read_text())

            self.assertEqual(data["user_id"], "test_user")
            self.assertEqual(data["total_entries"], 2)
            self.assertEqual(len(data["corrections"]), 2)
        finally:
            Path(output_path.name).unlink()

    def test_performance_add(self):
        """Test add performance"""
        audio_data = b"test_audio_perf"

        start = time.time()
        self.cache.add_correction(audio_data, "text", "corrected", "fr")
        duration_ms = (time.time() - start) * 1000

        # Should be fast (< 10ms)
        self.assertLess(duration_ms, 10.0)

    def test_performance_retrieve(self):
        """Test retrieve performance"""
        audio_data = b"test_audio_perf"
        self.cache.add_correction(audio_data, "text", "corrected", "fr")

        start = time.time()
        self.cache.get_correction(audio_data)
        duration_ms = (time.time() - start) * 1000

        # Should be fast (< 10ms)
        self.assertLess(duration_ms, 10.0)


class TestRealtimeSTTEngineStub(unittest.TestCase):
    """Stub tests for RealtimeSTTEngine (requires whisper installation)"""

    def test_import(self):
        """Test that module can be imported"""
        try:
            from janus.io.stt.realtime_stt_engine import RealtimeSTTEngine, TranscriptionResult

            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"RealtimeSTTEngine not available: {e}")

    def test_buffer_operations(self):
        """Test rolling buffer operations"""
        try:
            from janus.io.stt.realtime_stt_engine import RealtimeSTTEngine
        except ImportError:
            self.skipTest("RealtimeSTTEngine not available")

        # This would require whisper to be installed
        # For now, just test that the class exists
        self.assertTrue(hasattr(RealtimeSTTEngine, "add_to_buffer"))
        self.assertTrue(hasattr(RealtimeSTTEngine, "get_buffer_audio"))
        self.assertTrue(hasattr(RealtimeSTTEngine, "clear_buffer"))


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestNaturalReformatter))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceAdaptationCache))
    suite.addTests(loader.loadTestsFromTestCase(TestRealtimeSTTEngineStub))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
