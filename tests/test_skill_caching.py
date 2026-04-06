"""
Tests for TICKET-LEARN-001: Skill Caching & Corrective Sequences

Tests the skill cache functionality that allows the agent to learn and reuse
successful action sequences after user corrections.
"""

import os
import tempfile
import unittest
from typing import Dict, Any, List
import json

from janus.learning.feedback_manager import FeedbackManager
from janus.learning.learning_manager import LearningManager
from janus.ai.reasoning.semantic_router import SemanticRouter


class TestSkillCache(unittest.TestCase):
    """Test skill caching in FeedbackManager"""

    def setUp(self):
        """Set up test environment with temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.feedback_manager = FeedbackManager(db_path=self.db_path)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_skill_cache_table_created(self):
        """Test that skill_cache table is created"""
        # Try to query the table
        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skill_cache'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)

    def test_store_and_retrieve_skill(self):
        """Test storing and retrieving a skill"""
        # Create a test skill
        intent_vector = b"test_vector_bytes_12345678"
        context_hash = "test_context_hash_123"
        action_sequence = [
            {"action_type": "click", "parameters": {"target": "button"}},
            {"action_type": "type", "parameters": {"text": "Hello"}},
        ]
        intent_text = "Click button and type hello"

        # Store the skill
        skill_id = self.feedback_manager.store_skill(
            intent_vector=intent_vector,
            context_hash=context_hash,
            action_sequence=action_sequence,
            intent_text=intent_text,
        )

        self.assertIsNotNone(skill_id)
        self.assertGreater(skill_id, 0)

        # Retrieve the skill
        retrieved = self.feedback_manager.retrieve_skill(
            intent_vector=intent_vector,
            context_hash=context_hash,
            similarity_threshold=0.5,
        )

        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]["action_type"], "click")
        self.assertEqual(retrieved[1]["action_type"], "type")

    def test_skill_update_on_duplicate(self):
        """Test that storing same context updates the skill"""
        intent_vector = b"test_vector"
        context_hash = "same_context"
        action_sequence_v1 = [{"action_type": "click"}]
        action_sequence_v2 = [{"action_type": "click"}, {"action_type": "type"}]

        # Store first version
        skill_id_1 = self.feedback_manager.store_skill(
            intent_vector=intent_vector,
            context_hash=context_hash,
            action_sequence=action_sequence_v1,
            intent_text="Version 1",
        )

        # Store second version with same context
        skill_id_2 = self.feedback_manager.store_skill(
            intent_vector=intent_vector,
            context_hash=context_hash,
            action_sequence=action_sequence_v2,
            intent_text="Version 2",
        )

        # Should be the same skill ID (updated)
        self.assertEqual(skill_id_1, skill_id_2)

        # Retrieve should get the updated version
        retrieved = self.feedback_manager.retrieve_skill(
            intent_vector=intent_vector,
            context_hash=context_hash,
        )

        self.assertEqual(len(retrieved), 2)  # Should have 2 actions (v2)

    def test_skill_success_count_increments(self):
        """Test that success_count increments on updates"""
        intent_vector = b"test_vector"
        context_hash = "test_hash"
        action_sequence = [{"action_type": "click"}]

        # Store skill 3 times
        for i in range(3):
            self.feedback_manager.store_skill(
                intent_vector=intent_vector,
                context_hash=context_hash,
                action_sequence=action_sequence,
                intent_text=f"Attempt {i+1}",
            )

        # Check success count
        skills = self.feedback_manager.get_all_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["success_count"], 3)

    def test_get_all_skills(self):
        """Test retrieving all cached skills"""
        # Store multiple skills
        for i in range(5):
            self.feedback_manager.store_skill(
                intent_vector=f"vector_{i}".encode(),
                context_hash=f"hash_{i}",
                action_sequence=[{"action_type": f"action_{i}"}],
                intent_text=f"Intent {i}",
            )

        # Retrieve all
        skills = self.feedback_manager.get_all_skills(limit=10)
        self.assertEqual(len(skills), 5)

        # Check structure
        skill = skills[0]
        self.assertIn("id", skill)
        self.assertIn("context_hash", skill)
        self.assertIn("action_sequence", skill)
        self.assertIn("intent_text", skill)
        self.assertIn("success_count", skill)

    def test_clear_old_skills(self):
        """Test clearing old skills"""
        # Store a skill
        self.feedback_manager.store_skill(
            intent_vector=b"vector",
            context_hash="hash",
            action_sequence=[{"action_type": "click"}],
            intent_text="Test",
        )

        # Verify it exists
        skills_before = self.feedback_manager.get_all_skills()
        self.assertEqual(len(skills_before), 1)

        # Clear skills older than 0 days (should clear all)
        self.feedback_manager.clear_old_skills(days=0)

        # Verify it's cleared
        skills_after = self.feedback_manager.get_all_skills()
        self.assertEqual(len(skills_after), 0)


class TestLearningManagerSkillCache(unittest.TestCase):
    """Test skill caching in LearningManager"""

    def setUp(self):
        """Set up test environment"""
        self.temp_files = []

        self.db_file = self._create_temp_file(suffix=".db")
        self.cache_file = self._create_temp_file(suffix=".json")
        self.heuristics_file = self._create_temp_file(suffix=".json")
        self.corrections_file = self._create_temp_file(suffix=".json")
        self.reports_dir = tempfile.mkdtemp()

        self.manager = LearningManager(
            db_path=self.db_file,
            cache_path=self.cache_file,
            heuristics_config_path=self.heuristics_file,
            correction_history_path=self.corrections_file,
            reports_dir=self.reports_dir,
            auto_update=False,
        )

    def _create_temp_file(self, suffix=""):
        """Create a temporary file and track it"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Clean up"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                os.unlink(os.path.join(self.reports_dir, file))
            os.rmdir(self.reports_dir)

    def test_store_corrective_sequence(self):
        """Test storing a corrective sequence"""
        # Start a session
        self.manager.start_session()

        # Record some successful actions
        self.manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "button"},
            success=True,
            duration_ms=100,
        )
        self.manager.record_action_execution(
            action_type="type",
            action_parameters={"text": "Hello"},
            success=True,
            duration_ms=50,
        )

        # Store the sequence
        skill_id = self.manager.store_corrective_sequence(
            intent_text="Click button and type hello",
            context_data={"screen": "login_page"},
        )

        self.assertIsNotNone(skill_id)
        self.assertGreater(skill_id, 0)

    def test_retrieve_cached_skill(self):
        """Test retrieving a cached skill"""
        # Store a skill
        self.manager.start_session()
        self.manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "submit"},
            success=True,
        )

        intent_text = "Submit form"
        context_data = {"screen": "form_page"}

        skill_id = self.manager.store_corrective_sequence(
            intent_text=intent_text,
            context_data=context_data,
        )

        self.assertIsNotNone(skill_id)

        # Retrieve the skill
        retrieved = self.manager.retrieve_cached_skill(
            intent_text=intent_text,
            context_data=context_data,
        )

        self.assertIsNotNone(retrieved)
        self.assertGreater(len(retrieved), 0)
        self.assertEqual(retrieved[0]["action_type"], "click")

    def test_context_hash_consistency(self):
        """Test that same intent/context produces same hash"""
        intent = "Open Chrome"
        context = {"screen": "desktop"}

        hash1 = self.manager._compute_context_hash(intent, context)
        hash2 = self.manager._compute_context_hash(intent, context)

        self.assertEqual(hash1, hash2)

    def test_context_hash_differs_for_different_context(self):
        """Test that different context produces different hash"""
        intent = "Open Chrome"
        context1 = {"screen": "desktop"}
        context2 = {"screen": "browser"}

        hash1 = self.manager._compute_context_hash(intent, context1)
        hash2 = self.manager._compute_context_hash(intent, context2)

        self.assertNotEqual(hash1, hash2)

    def test_clean_action_sequence(self):
        """Test cleaning action sequence"""
        raw_actions = [
            {
                "action_type": "click",
                "parameters": {"target": "button"},
                "success": True,
                "timestamp": "2024-01-01T00:00:00",
            },
            {
                "action_type": "type",
                "parameters": {"text": "Hello"},
                "success": True,
                "timestamp": "2024-01-01T00:00:01",
            },
            {
                "action_type": None,  # Should be filtered out
                "parameters": {},
                "success": False,
            },
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)

        # Should have 2 actions (third filtered out)
        self.assertEqual(len(cleaned), 2)

        # Should only have action_type and parameters
        self.assertIn("action_type", cleaned[0])
        self.assertIn("parameters", cleaned[0])
        self.assertNotIn("success", cleaned[0])
        self.assertNotIn("timestamp", cleaned[0])
    
    def test_clean_action_sequence_removes_consecutive_duplicates(self):
        """Test that consecutive duplicate actions are removed (retry attempts)"""
        raw_actions = [
            {
                "action_type": "click",
                "parameters": {"target": "button"},
                "success": True,
            },
            {
                "action_type": "click",  # Duplicate - should be removed
                "parameters": {"target": "button"},
                "success": True,
            },
            {
                "action_type": "click",  # Another duplicate - should be removed
                "parameters": {"target": "button"},
                "success": True,
            },
            {
                "action_type": "type",
                "parameters": {"text": "Hello"},
                "success": True,
            },
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)

        # Should have 2 actions (duplicates removed)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["action_type"], "click")
        self.assertEqual(cleaned[1]["action_type"], "type")
    
    def test_clean_action_sequence_preserves_non_consecutive_duplicates(self):
        """Test that non-consecutive duplicate actions are preserved"""
        raw_actions = [
            {
                "action_type": "click",
                "parameters": {"target": "button1"},
                "success": True,
            },
            {
                "action_type": "type",
                "parameters": {"text": "Hello"},
                "success": True,
            },
            {
                "action_type": "click",  # Same as first - keep it (non-consecutive)
                "parameters": {"target": "button1"},
                "success": True,
            },
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)

        # Should have all 3 actions (not consecutive duplicates)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned[0]["action_type"], "click")
        self.assertEqual(cleaned[1]["action_type"], "type")
        self.assertEqual(cleaned[2]["action_type"], "click")
    
    def test_clean_action_sequence_different_parameters(self):
        """Test that actions with same type but different parameters are kept"""
        raw_actions = [
            {
                "action_type": "click",
                "parameters": {"target": "button1"},
                "success": True,
            },
            {
                "action_type": "click",  # Same type, different params - keep it
                "parameters": {"target": "button2"},
                "success": True,
            },
            {
                "action_type": "type",
                "parameters": {"text": "Hello"},
                "success": True,
            },
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)

        # Should have all 3 actions (different parameters)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned[0]["parameters"]["target"], "button1")
        self.assertEqual(cleaned[1]["parameters"]["target"], "button2")
    
    def test_clean_action_sequence_empty_input(self):
        """Test cleaning empty action sequence"""
        cleaned = self.manager._clean_action_sequence([])
        self.assertEqual(len(cleaned), 0)
    
    def test_clean_action_sequence_all_invalid(self):
        """Test cleaning sequence with all invalid actions"""
        raw_actions = [
            {"action_type": None, "parameters": {}},
            {"action_type": "", "parameters": {}},
            {"action_type": None, "parameters": {"x": 1}},
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)
        self.assertEqual(len(cleaned), 0)
    
    def test_actions_are_equivalent(self):
        """Test action equivalence checking"""
        action1 = {"action_type": "click", "parameters": {"target": "button"}}
        action2 = {"action_type": "click", "parameters": {"target": "button"}}
        action3 = {"action_type": "click", "parameters": {"target": "other"}}
        action4 = {"action_type": "type", "parameters": {"target": "button"}}
        
        # Same action
        self.assertTrue(self.manager._actions_are_equivalent(action1, action2))
        
        # Different parameters
        self.assertFalse(self.manager._actions_are_equivalent(action1, action3))
        
        # Different action type
        self.assertFalse(self.manager._actions_are_equivalent(action1, action4))
    
    def test_actions_are_equivalent_nested_params(self):
        """Test action equivalence with nested parameters"""
        action1 = {
            "action_type": "complex",
            "parameters": {
                "target": "button",
                "options": {"delay": 100, "retry": True}
            }
        }
        action2 = {
            "action_type": "complex",
            "parameters": {
                "target": "button",
                "options": {"delay": 100, "retry": True}
            }
        }
        action3 = {
            "action_type": "complex",
            "parameters": {
                "target": "button",
                "options": {"delay": 200, "retry": True}  # Different nested value
            }
        }
        
        # Same nested parameters
        self.assertTrue(self.manager._actions_are_equivalent(action1, action2))
        
        # Different nested parameters
        self.assertFalse(self.manager._actions_are_equivalent(action1, action3))
    
    def test_clean_action_sequence_complex_retry_pattern(self):
        """Test filtering complex retry patterns from failed attempts"""
        # Simulates: user tries 3 times, fails, then succeeds
        raw_actions = [
            # First failed attempt (already filtered by store_corrective_sequence)
            # These would have success=False and not be in the list
            
            # Successful attempt after correction
            {
                "action_type": "close_popup",
                "parameters": {"target": "modal"},
                "success": True,
            },
            {
                "action_type": "click",
                "parameters": {"target": "status_button"},
                "success": True,
            },
            {
                "action_type": "click",  # Retry due to UI delay - should be filtered
                "parameters": {"target": "status_button"},
                "success": True,
            },
            {
                "action_type": "select",
                "parameters": {"option": "away"},
                "success": True,
            },
        ]

        cleaned = self.manager._clean_action_sequence(raw_actions)

        # Should have 3 actions (duplicate click removed)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned[0]["action_type"], "close_popup")
        self.assertEqual(cleaned[1]["action_type"], "click")
        self.assertEqual(cleaned[2]["action_type"], "select")

    def test_get_cached_skills_summary(self):
        """Test getting summary of cached skills"""
        # Store some skills
        self.manager.start_session()
        self.manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "button"},
            success=True,
        )

        self.manager.store_corrective_sequence(
            intent_text="Click button",
            context_data={"screen": "test"},
        )

        # Get summary
        summary = self.manager.get_cached_skills_summary()

        self.assertIn("total_skills", summary)
        self.assertIn("skills", summary)
        self.assertGreater(summary["total_skills"], 0)


class TestSemanticRouterSkillCache(unittest.TestCase):
    """Test skill cache integration with SemanticRouter"""

    def setUp(self):
        """Set up test environment"""
        self.temp_files = []

        # Create learning manager
        self.db_file = self._create_temp_file(suffix=".db")
        self.cache_file = self._create_temp_file(suffix=".json")
        self.heuristics_file = self._create_temp_file(suffix=".json")
        self.corrections_file = self._create_temp_file(suffix=".json")
        self.reports_dir = tempfile.mkdtemp()

        self.learning_manager = LearningManager(
            db_path=self.db_file,
            cache_path=self.cache_file,
            heuristics_config_path=self.heuristics_file,
            correction_history_path=self.corrections_file,
            reports_dir=self.reports_dir,
            auto_update=False,
        )

        # Create semantic router with learning manager
        self.router = SemanticRouter(
            reasoner=None,
            enable_embeddings=False,  # Disable embeddings for simpler tests
            learning_manager=self.learning_manager,
        )

    def _create_temp_file(self, suffix=""):
        """Create a temporary file and track it"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Clean up"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                os.unlink(os.path.join(self.reports_dir, file))
            os.rmdir(self.reports_dir)

    def test_router_has_learning_manager(self):
        """Test that router is initialized with learning manager"""
        self.assertIsNotNone(self.router.learning_manager)

    def test_check_skill_cache_returns_none_when_empty(self):
        """Test that checking empty cache returns None"""
        result = self.router.check_skill_cache("Open Chrome")
        self.assertIsNone(result)

    def test_store_and_retrieve_skill_via_router(self):
        """Test full cycle: store skill and retrieve via router"""
        intent = "Set Slack status to away"
        
        # Start a session and record actions
        self.learning_manager.start_session()
        self.learning_manager.record_action_execution(
            action_type="open_app",
            action_parameters={"app_name": "Slack"},
            success=True,
        )
        self.learning_manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "status_button"},
            success=True,
        )

        # Store via router
        skill_id = self.router.store_successful_sequence(
            text=intent,
            context_data={"app": "Slack"},
        )

        self.assertIsNotNone(skill_id)

        # Retrieve via router
        cached_skill = self.router.check_skill_cache(
            text=intent,
            context_data={"app": "Slack"},
        )

        self.assertIsNotNone(cached_skill)
        self.assertEqual(len(cached_skill), 2)
        self.assertEqual(cached_skill[0]["action_type"], "open_app")

    def test_reflex_mode_performance(self):
        """Test that reflex mode is faster than reasoning"""
        import time

        intent = "Quick test action"
        
        # Store a skill
        self.learning_manager.start_session()
        self.learning_manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "button"},
            success=True,
        )
        self.router.store_successful_sequence(text=intent)

        # Measure cache retrieval time
        start = time.time()
        cached_skill = self.router.check_skill_cache(text=intent)
        cache_time = time.time() - start

        self.assertIsNotNone(cached_skill)
        
        # Cache retrieval should be very fast (< 10ms)
        self.assertLess(cache_time, 0.01, "Cache retrieval should be < 10ms")

    def test_skill_not_retrieved_for_different_intent(self):
        """Test that skill is not retrieved for different intent"""
        # Store a skill
        self.learning_manager.start_session()
        self.learning_manager.record_action_execution(
            action_type="open_app",
            action_parameters={"app_name": "Chrome"},
            success=True,
        )
        self.router.store_successful_sequence(text="Open Chrome")

        # Try to retrieve with different intent
        cached_skill = self.router.check_skill_cache(text="Open Firefox")

        # Should not find a match (different context hash)
        self.assertIsNone(cached_skill)


class TestSkillCachingIntegration(unittest.TestCase):
    """Integration tests for skill caching workflow"""

    def setUp(self):
        """Set up test environment"""
        self.temp_files = []

        # Create learning manager
        self.db_file = self._create_temp_file(suffix=".db")
        self.cache_file = self._create_temp_file(suffix=".json")
        self.heuristics_file = self._create_temp_file(suffix=".json")
        self.corrections_file = self._create_temp_file(suffix=".json")
        self.reports_dir = tempfile.mkdtemp()

        self.learning_manager = LearningManager(
            db_path=self.db_file,
            cache_path=self.cache_file,
            heuristics_config_path=self.heuristics_file,
            correction_history_path=self.corrections_file,
            reports_dir=self.reports_dir,
            auto_update=False,
        )

        self.router = SemanticRouter(
            reasoner=None,
            enable_embeddings=False,
            learning_manager=self.learning_manager,
        )

    def _create_temp_file(self, suffix=""):
        """Create a temporary file and track it"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Clean up"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        if os.path.exists(self.reports_dir):
            for file in os.listdir(self.reports_dir):
                os.unlink(os.path.join(self.reports_dir, file))
            os.rmdir(self.reports_dir)

    def test_learning_from_correction_workflow(self):
        """
        Test complete workflow: fail -> correction -> success -> cache -> fast retrieval
        
        This simulates the acceptance criteria:
        1. First execution: agent fails or user corrects
        2. Record the corrected actions
        3. Store as skill
        4. Second execution: retrieve from cache (2x faster)
        """
        intent = "Mets mon statut Slack à absent"
        
        # === First execution: Learning phase ===
        self.learning_manager.start_session("session_1")
        
        # Simulate failed action
        self.learning_manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "wrong_button"},
            success=False,
            error_message="Element not found",
        )
        
        # User correction
        self.learning_manager.record_user_correction(
            correction_text="Non, il faut d'abord fermer la popup",
            language="fr",
        )
        
        # Corrected actions that work
        self.learning_manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "close_popup"},
            success=True,
        )
        self.learning_manager.record_action_execution(
            action_type="open_app",
            action_parameters={"app_name": "Slack"},
            success=True,
        )
        self.learning_manager.record_action_execution(
            action_type="click",
            action_parameters={"target": "status_dropdown"},
            success=True,
        )
        self.learning_manager.record_action_execution(
            action_type="select",
            action_parameters={"option": "away"},
            success=True,
        )
        
        # Store the corrected sequence as a skill
        skill_id = self.router.store_successful_sequence(
            text=intent,
            context_data={"app": "Slack", "state": "popup_present"},
        )
        
        self.assertIsNotNone(skill_id, "Skill should be stored")
        self.learning_manager.end_session()
        
        # === Second execution: Reflex mode ===
        self.learning_manager.start_session("session_2")
        
        # Check cache BEFORE reasoning (reflex mode)
        import time
        start = time.time()
        cached_skill = self.router.check_skill_cache(
            text=intent,
            context_data={"app": "Slack", "state": "popup_present"},
        )
        cache_time = time.time() - start
        
        # Should find the cached skill
        self.assertIsNotNone(cached_skill, "Cached skill should be found")
        self.assertEqual(len(cached_skill), 4, "Should have 4 actions")
        
        # Verify the sequence is correct
        self.assertEqual(cached_skill[0]["action_type"], "click")
        self.assertEqual(cached_skill[0]["parameters"]["target"], "close_popup")
        self.assertEqual(cached_skill[1]["action_type"], "open_app")
        self.assertEqual(cached_skill[3]["action_type"], "select")
        
        # Cache retrieval should be very fast
        self.assertLess(cache_time, 0.05, "Cache retrieval should be < 50ms")
        
        # Verify we can skip the expensive LLM reasoning
        # (In real usage, the pipeline would execute cached_skill directly)
        self.learning_manager.end_session()


if __name__ == "__main__":
    unittest.main()
