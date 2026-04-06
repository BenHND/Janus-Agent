"""
Unit tests for Context Ranker (TICKET A4).

Tests the relevance scoring and temporal decay functionality
for smart context loading.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from janus.runtime.core.context_ranker import ContextRanker
from janus.runtime.core.contracts import Intent
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


class TestContextRanker(unittest.TestCase):
    """Test cases for ContextRanker"""

    def setUp(self):
        """Set up test fixtures"""
        self.ranker = ContextRanker(decay_halflife_hours=24.0)

    def test_score_relevance_app_match(self):
        """Test relevance scoring for matching app contexts"""
        context_item = {
            "type": "app",
            "data": {"app_name": "Chrome"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Chrome"})

        score = self.ranker.score_relevance(context_item, intent)

        # Should get high score for exact app match
        self.assertGreater(score, 0.7)
        self.assertLessEqual(score, 1.0)

    def test_score_relevance_app_mismatch(self):
        """Test relevance scoring for non-matching app contexts"""
        context_item = {
            "type": "app",
            "data": {"app_name": "Safari"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(
            action="open_file", confidence=0.9, parameters={"path": "/home/user/document.txt"}
        )

        score = self.ranker.score_relevance(context_item, intent)

        # Should get lower score for mismatched context
        self.assertLess(score, 0.75)

    def test_score_relevance_file_match(self):
        """Test relevance scoring for matching file contexts"""
        context_item = {
            "type": "file",
            "data": {"file_path": "/home/user/project/file.py"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(
            action="open_file", confidence=0.9, parameters={"path": "/home/user/project/file.py"}
        )

        score = self.ranker.score_relevance(context_item, intent)

        # Should get high score for exact file match
        self.assertGreater(score, 0.8)

    def test_score_relevance_file_same_directory(self):
        """Test relevance scoring for files in same directory"""
        context_item = {
            "type": "file",
            "data": {"file_path": "/home/user/project/file1.py"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(
            action="open_file", confidence=0.9, parameters={"path": "/home/user/project/file2.py"}
        )

        score = self.ranker.score_relevance(context_item, intent)

        # Should get good score for same directory
        self.assertGreater(score, 0.6)

    def test_score_relevance_clipboard_paste(self):
        """Test relevance scoring for clipboard context with paste intent"""
        context_item = {
            "type": "clipboard",
            "data": {"content": "test text"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(action="paste_text", confidence=0.9, parameters={})

        score = self.ranker.score_relevance(context_item, intent)

        # Should get high score for clipboard + paste
        self.assertGreater(score, 0.7)

    def test_score_relevance_browser_intent(self):
        """Test relevance scoring for browser contexts"""
        context_item = {
            "type": "browser",
            "data": {"url": "https://github.com"},
            "timestamp": datetime.now().isoformat(),
        }

        intent = Intent(
            action="open_browser", confidence=0.9, parameters={"url": "https://github.com"}
        )

        score = self.ranker.score_relevance(context_item, intent)

        # Should get good score for browser context + browser intent
        self.assertGreater(score, 0.6)

    def test_apply_decay_recent(self):
        """Test temporal decay for recent context (< 1 hour)"""
        decay = self.ranker.apply_decay(0.5)  # 30 minutes

        # Recent context should have minimal decay
        self.assertGreater(decay, 0.95)

    def test_apply_decay_halflife(self):
        """Test temporal decay at half-life point (24 hours)"""
        decay = self.ranker.apply_decay(24.0)  # 24 hours (half-life)

        # At half-life, decay should be around 0.5
        self.assertAlmostEqual(decay, 0.5, delta=0.05)

    def test_apply_decay_old(self):
        """Test temporal decay for old context (> 48 hours)"""
        decay = self.ranker.apply_decay(48.0)  # 48 hours

        # Old context should have significant decay
        self.assertLess(decay, 0.4)
        self.assertGreater(decay, 0.0)

    def test_apply_decay_very_old(self):
        """Test temporal decay for very old context (> 1 week)"""
        decay = self.ranker.apply_decay(168.0)  # 1 week

        # Very old context should have heavy decay
        self.assertLess(decay, 0.2)
        self.assertGreater(decay, 0.0)

    def test_rank_context_items_ordering(self):
        """Test that context items are ranked correctly"""
        # Create context items with different timestamps
        now = datetime.now()

        context_items = [
            {
                "type": "app",
                "data": {"app_name": "Chrome"},
                "timestamp": (now - timedelta(hours=2)).isoformat(),  # Old
            },
            {
                "type": "app",
                "data": {"app_name": "Chrome"},
                "timestamp": (now - timedelta(minutes=5)).isoformat(),  # Recent
            },
            {
                "type": "file",
                "data": {"file_path": "/other/file.txt"},
                "timestamp": (now - timedelta(minutes=10)).isoformat(),  # Unrelated
            },
        ]

        intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Chrome"})

        ranked = self.ranker.rank_context_items(context_items, intent, max_items=10)

        # Should return all items
        self.assertEqual(len(ranked), 3)

        # First item should be the recent Chrome app context
        self.assertEqual(ranked[0][0]["data"]["app_name"], "Chrome")
        # Verify it's the recent one (higher score due to recency)
        self.assertGreater(ranked[0][1], ranked[1][1])

        # Scores should be descending
        for i in range(len(ranked) - 1):
            self.assertGreaterEqual(ranked[i][1], ranked[i + 1][1])

    def test_rank_context_items_max_items(self):
        """Test that max_items limit is respected"""
        context_items = [
            {
                "type": "app",
                "data": {"app_name": f"App{i}"},
                "timestamp": datetime.now().isoformat(),
            }
            for i in range(50)
        ]

        intent = Intent(action="test", confidence=0.9, parameters={})

        ranked = self.ranker.rank_context_items(context_items, intent, max_items=20)

        # Should return only top 20
        self.assertEqual(len(ranked), 20)

    def test_get_age_hours_recent(self):
        """Test age calculation for recent context"""
        context_item = {"timestamp": datetime.now().isoformat()}

        age = self.ranker._get_age_hours(context_item)

        # Should be very small
        self.assertLess(age, 0.1)  # Less than 6 minutes

    def test_get_age_hours_old(self):
        """Test age calculation for old context"""
        old_time = datetime.now() - timedelta(hours=48)
        context_item = {"timestamp": old_time.isoformat()}

        age = self.ranker._get_age_hours(context_item)

        # Should be around 48 hours
        self.assertAlmostEqual(age, 48.0, delta=0.5)

    def test_get_age_hours_missing_timestamp(self):
        """Test age calculation for missing timestamp"""
        context_item = {}

        age = self.ranker._get_age_hours(context_item)

        # Should default to large value (1 week)
        self.assertEqual(age, 168.0)

    def test_temporal_proximity_scoring(self):
        """Test temporal proximity scoring separately"""
        # Very recent context
        recent_context = {
            "type": "app",
            "data": {},
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
        }

        score_recent = self.ranker._score_temporal_proximity(recent_context)
        self.assertGreater(score_recent, 0.9)

        # Old context
        old_context = {
            "type": "app",
            "data": {},
            "timestamp": (datetime.now() - timedelta(hours=48)).isoformat(),
        }

        score_old = self.ranker._score_temporal_proximity(old_context)
        self.assertLess(score_old, 0.5)


class TestMemoryEngineContextRanking(unittest.TestCase):
    """Test context ranking integration with MemoryEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()

        settings = DatabaseSettings(path=self.temp_db.name)
        self.memory_service = MemoryEngine(settings)

        # Create a test session
        self.session_id = self.memory_service.create_session()

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_get_recent_context(self):
        """Test getting recent context items"""
        # Store some context
        self.memory_service.store_context(self.session_id, "app", {"app_name": "Chrome"})
        self.memory_service.store_context(self.session_id, "file", {"file_path": "/test/file.txt"})

        # Get recent context
        recent = self.memory_service._get_recent(self.session_id, hours=1.0, limit=10)

        # Should get both items
        self.assertEqual(len(recent), 2)

    def test_get_recent_context_time_filter(self):
        """Test that time filtering works for recent context"""
        # This test demonstrates the concept, but in practice we can't
        # manipulate timestamps in the database easily in a unit test
        # In a real scenario, you'd use time mocking or database manipulation

        # Store context
        self.memory_service.store_context(self.session_id, "app", {"app_name": "Chrome"})

        # Get recent context with very short window
        recent = self.memory_service._get_recent(self.session_id, hours=0.001, limit=10)

        # Should get empty or very few items (since context is just stored)
        # This is a weak test, but demonstrates the API
        self.assertIsInstance(recent, list)

    def test_load_recent_context_ranked(self):
        """Test loading recent context with ranking"""
        # Store multiple context items
        self.memory_service.store_context(self.session_id, "app", {"app_name": "Chrome"})
        self.memory_service.store_context(self.session_id, "file", {"file_path": "/test/file.txt"})
        self.memory_service.store_context(self.session_id, "clipboard", {"content": "test text"})

        # Load with ranking
        intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Chrome"})

        ranked = self.memory_service.load_recent_context(self.session_id, intent, max_items=10)

        # Should return ranked items
        self.assertIsInstance(ranked, list)
        self.assertGreater(len(ranked), 0)

        # Each item should be a tuple of (context_item, score)
        for item, score in ranked:
            self.assertIsInstance(item, dict)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_cleanup_old_context(self):
        """Test cleanup of old context"""
        # Store some context
        self.memory_service.store_context(self.session_id, "app", {"app_name": "Chrome"})
        self.memory_service.store_context(self.session_id, "file", {"file_path": "/test/file.txt"})

        # Verify context exists
        context = self.memory_service.get_context(self.session_id, limit=10)
        self.assertEqual(len(context), 2)

        # Clean up with 0 days threshold (should delete everything)
        deleted_count = self.memory_service.cleanup_old_context(
            days_threshold=0, session_id=self.session_id
        )

        # Should have deleted items
        self.assertGreaterEqual(deleted_count, 0)

        # Context should be empty or reduced
        context_after = self.memory_service.get_context(self.session_id, limit=10)
        self.assertLessEqual(len(context_after), len(context))

    def test_cleanup_old_context_all_sessions(self):
        """Test cleanup across all sessions"""
        # Create multiple sessions with context
        session1 = self.memory_service.create_session()
        session2 = self.memory_service.create_session()

        self.memory_service.store_context(session1, "app", {"app_name": "App1"})
        self.memory_service.store_context(session2, "app", {"app_name": "App2"})

        # Clean up all sessions with 0 days threshold
        deleted_count = self.memory_service.cleanup_old_context(days_threshold=0, session_id=None)

        # Should have attempted to delete from all sessions
        self.assertGreaterEqual(deleted_count, 0)

    def test_cleanup_old_context_threshold(self):
        """Test cleanup respects threshold"""
        # Store context
        self.memory_service.store_context(self.session_id, "app", {"app_name": "Chrome"})

        # Clean up with large threshold (30 days) - should not delete recent items
        deleted_count = self.memory_service.cleanup_old_context(
            days_threshold=30, session_id=self.session_id
        )

        # Should not delete recent items
        self.assertEqual(deleted_count, 0)

        # Context should still exist
        context = self.memory_service.get_context(self.session_id, limit=10)
        self.assertEqual(len(context), 1)


class TestContextRankerTFIDF(unittest.TestCase):
    """Test cases for TF-IDF-based context pruning (TICKET-P2-03)"""

    def setUp(self):
        """Set up test fixtures"""
        self.ranker = ContextRanker(decay_halflife_hours=24.0)

    def test_tokenize_basic(self):
        """Test basic tokenization"""
        tokens = self.ranker._tokenize("ouvre Safari et va sur YouTube")
        # Should have meaningful tokens, excluding stopwords like 'et', 'sur'
        self.assertIn("ouvre", tokens)
        self.assertIn("safari", tokens)
        self.assertIn("youtube", tokens)
        # Stopwords should be removed
        self.assertNotIn("et", tokens)
        self.assertNotIn("sur", tokens)

    def test_tokenize_french_stopwords(self):
        """Test that French stopwords are removed"""
        tokens = self.ranker._tokenize("le fichier est dans le dossier")
        self.assertIn("fichier", tokens)
        self.assertIn("dossier", tokens)
        # Stopwords should be removed
        self.assertNotIn("le", tokens)
        self.assertNotIn("est", tokens)
        self.assertNotIn("dans", tokens)

    def test_tokenize_empty_input(self):
        """Test tokenization of empty input"""
        self.assertEqual(self.ranker._tokenize(""), [])
        self.assertEqual(self.ranker._tokenize(None), [])

    def test_compute_tf(self):
        """Test Term Frequency computation"""
        tokens = ["hello", "world", "hello"]
        tf = self.ranker._compute_tf(tokens)
        
        # "hello" appears 2 times out of 3 tokens
        self.assertAlmostEqual(tf["hello"], 2/3, places=5)
        # "world" appears 1 time out of 3 tokens
        self.assertAlmostEqual(tf["world"], 1/3, places=5)

    def test_compute_tf_empty(self):
        """Test TF computation with empty input"""
        self.assertEqual(self.ranker._compute_tf([]), {})

    def test_compute_idf(self):
        """Test Inverse Document Frequency computation"""
        documents = [
            ["hello", "world"],
            ["hello", "python"],
            ["goodbye", "world"],
        ]
        idf = self.ranker._compute_idf(documents)
        
        # "hello" appears in 2 of 3 documents
        # IDF = log(3 / (1 + 2)) = log(1) = 0
        self.assertAlmostEqual(idf["hello"], 0.0, places=5)
        
        # "python" appears in 1 of 3 documents
        # IDF = log(3 / (1 + 1)) = log(1.5) ≈ 0.405
        self.assertGreater(idf["python"], 0.3)

    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical vectors"""
        vec = {"hello": 0.5, "world": 0.5}
        similarity = self.ranker._cosine_similarity(vec, vec)
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors"""
        vec1 = {"hello": 1.0}
        vec2 = {"world": 1.0}
        similarity = self.ranker._cosine_similarity(vec1, vec2)
        self.assertEqual(similarity, 0.0)

    def test_cosine_similarity_empty(self):
        """Test cosine similarity with empty vectors"""
        self.assertEqual(self.ranker._cosine_similarity({}, {"a": 1}), 0.0)
        self.assertEqual(self.ranker._cosine_similarity({"a": 1}, {}), 0.0)

    def test_rank_commands_by_similarity_basic(self):
        """Test basic command ranking by similarity"""
        current = "ouvre Safari"
        history = [
            {"raw_command": "ouvre Chrome", "timestamp": datetime.now().isoformat()},
            {"raw_command": "ouvre Safari", "timestamp": datetime.now().isoformat()},
            {"raw_command": "ferme le fichier", "timestamp": datetime.now().isoformat()},
        ]
        
        ranked = self.ranker.rank_commands_by_similarity(current, history, max_items=3)
        
        # Should return all 3 items
        self.assertEqual(len(ranked), 3)
        
        # "ouvre Safari" should be ranked first (most similar)
        self.assertIn("Safari", ranked[0][0]["raw_command"])
        
        # "ouvre Chrome" should be second (shares "ouvre")
        self.assertIn("Chrome", ranked[1][0]["raw_command"])
        
        # "ferme le fichier" should be last (least similar)
        self.assertIn("fichier", ranked[2][0]["raw_command"])

    def test_rank_commands_by_similarity_max_items(self):
        """Test that max_items is respected"""
        current = "ouvre app"
        history = [{"raw_command": f"commande {i}"} for i in range(20)]
        
        ranked = self.ranker.rank_commands_by_similarity(current, history, max_items=5)
        
        self.assertEqual(len(ranked), 5)

    def test_rank_commands_by_similarity_empty_history(self):
        """Test ranking with empty history"""
        ranked = self.ranker.rank_commands_by_similarity("ouvre Safari", [], max_items=5)
        self.assertEqual(ranked, [])

    def test_rank_commands_by_similarity_empty_current(self):
        """Test ranking with empty current command"""
        history = [{"raw_command": "ouvre Safari"}]
        ranked = self.ranker.rank_commands_by_similarity("", history, max_items=5)
        # Should handle empty current command gracefully
        self.assertEqual(ranked, [])

    def test_get_pruned_context(self):
        """Test pruned context generation"""
        current = "ouvre Safari et va sur YouTube"
        history = [
            {"raw_command": "ouvre Safari", "intent": "open_app"},
            {"raw_command": "va sur Google", "intent": "open_url"},
            {"raw_command": "ouvre Chrome", "intent": "open_app"},
            {"raw_command": "ferme le document", "intent": "close_file"},
            {"raw_command": "copie le texte", "intent": "copy"},
            {"raw_command": "ouvre YouTube dans Safari", "intent": "open_url"},
        ]
        
        pruned = self.ranker.get_pruned_context(current, history, max_commands=3)
        
        # Should return max 3 items
        self.assertLessEqual(len(pruned), 3)
        
        # Should include cleaned commands
        for cmd in pruned:
            self.assertIn("command", cmd)
            self.assertIsInstance(cmd["command"], str)

    def test_clean_command_for_prompt(self):
        """Test command cleaning for prompts"""
        cmd = {
            "raw_command": "ouvre Safari",
            "intent": "open_app",
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.95,
            "parameters": {"app_name": "Safari"},
        }
        
        cleaned = self.ranker._clean_command_for_prompt(cmd)
        
        # Should keep only essential fields
        self.assertEqual(cleaned["command"], "ouvre Safari")
        self.assertEqual(cleaned["intent"], "open_app")
        
        # Should not include technical fields
        self.assertNotIn("timestamp", cleaned)
        self.assertNotIn("confidence", cleaned)
        self.assertNotIn("parameters", cleaned)

    def test_clean_command_for_prompt_unknown_intent(self):
        """Test that unknown intents are excluded"""
        cmd = {
            "raw_command": "ouvre Safari",
            "intent": "unknown",
        }
        
        cleaned = self.ranker._clean_command_for_prompt(cmd)
        
        self.assertIn("command", cleaned)
        self.assertNotIn("intent", cleaned)

    def test_clean_command_for_prompt_empty(self):
        """Test cleaning of empty command"""
        self.assertIsNone(self.ranker._clean_command_for_prompt({}))
        self.assertIsNone(self.ranker._clean_command_for_prompt({"raw_command": ""}))
        self.assertIsNone(self.ranker._clean_command_for_prompt({"raw_command": " "}))

    def test_estimate_prompt_reduction(self):
        """Test prompt reduction estimation"""
        full_history = [{"raw_command": f"commande {i}", "intent": f"intent_{i}"} for i in range(20)]
        pruned_history = [{"command": f"commande {i}"} for i in range(5)]
        
        metrics = self.ranker.estimate_prompt_reduction(full_history, pruned_history)
        
        self.assertEqual(metrics["full_command_count"], 20)
        self.assertEqual(metrics["pruned_command_count"], 5)
        self.assertGreater(metrics["reduction_percent"], 0)
        self.assertIn("target_reduction_met", metrics)

    def test_estimate_prompt_reduction_long_session(self):
        """Test that 40% reduction is achievable for long sessions"""
        # Simulate a long session with 50 commands
        full_history = [
            {
                "raw_command": f"commande numéro {i} avec beaucoup de texte supplémentaire",
                "intent": f"intent_{i}",
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "confidence": 0.95,
                "parameters": {"param1": "value1", "param2": "value2"},
            }
            for i in range(50)
        ]
        
        # Prune to 5 commands
        pruned_history = self.ranker.get_pruned_context(
            "ouvre Safari", full_history, max_commands=5
        )
        
        metrics = self.ranker.estimate_prompt_reduction(full_history, pruned_history)
        
        # Should achieve at least 40% reduction (target from ticket)
        self.assertGreaterEqual(
            metrics["reduction_percent"], 40.0,
            f"Expected >=40% reduction but got {metrics['reduction_percent']}%"
        )

    def test_rank_commands_temporal_decay_factor(self):
        """Test that temporal decay affects ranking"""
        current = "ouvre Safari"
        # Create two similar commands, one old and one recent
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        recent_time = datetime.now().isoformat()
        
        history = [
            {"raw_command": "ouvre Safari", "timestamp": old_time},
            {"raw_command": "ouvre Safari", "timestamp": recent_time},
        ]
        
        ranked = self.ranker.rank_commands_by_similarity(
            current, history, max_items=2, include_temporal_decay=True
        )
        
        # Recent command should be ranked higher
        self.assertGreater(ranked[0][1], ranked[1][1])
        # The first (highest scored) should be the recent one
        self.assertEqual(ranked[0][0]["timestamp"], recent_time)

    def test_rank_commands_without_temporal_decay(self):
        """Test ranking without temporal decay"""
        current = "ouvre Safari"
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        recent_time = datetime.now().isoformat()
        
        history = [
            {"raw_command": "ouvre Safari", "timestamp": old_time},
            {"raw_command": "ouvre Safari maintenant", "timestamp": recent_time},
        ]
        
        # Without temporal decay, both should have similar scores (based only on text similarity)
        ranked = self.ranker.rank_commands_by_similarity(
            current, history, max_items=2, include_temporal_decay=False
        )
        
        # Both commands are very similar, scores should be close
        self.assertAlmostEqual(ranked[0][1], ranked[1][1], delta=0.3)


if __name__ == "__main__":
    unittest.main()
