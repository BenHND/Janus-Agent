"""
Tests for ambiguity detector and conversation analytics.
"""
import tempfile
import unittest
from pathlib import Path

from janus.ai.reasoning.ambiguity_detector import AmbiguityDetector
from janus.runtime.core.conversation_analytics import ConversationAnalytics
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


class TestAmbiguityDetector(unittest.TestCase):
    """Test ambiguity detection"""
    
    def setUp(self):
        self.detector = AmbiguityDetector()
    
    def test_app_ambiguity_detection(self):
        """Test detecting ambiguous app names"""
        is_ambiguous, options = self.detector.detect_app_ambiguity("chrome")
        self.assertTrue(is_ambiguous)
        self.assertIn("Google Chrome", options)
        self.assertIn("Chromium", options)
    
    def test_no_app_ambiguity(self):
        """Test no ambiguity for specific app"""
        is_ambiguous, options = self.detector.detect_app_ambiguity("Safari")
        self.assertFalse(is_ambiguous)
    
    def test_missing_context_detection(self):
        """Test detecting missing required context"""
        is_missing, msg = self.detector.detect_missing_context(
            "open_file", {}
        )
        self.assertTrue(is_missing)
        self.assertIn("file_path", msg)
    
    def test_analyze_command_with_app_ambiguity(self):
        """Test full command analysis with app ambiguity"""
        result = self.detector.analyze_command(
            "open chrome",
            "open_app",
            {"app_name": "chrome"}
        )
        self.assertTrue(result["needs_clarification"])
        self.assertEqual(result["ambiguity_type"], "ambiguous_app")
        self.assertIsNotNone(result["options"])
    
    def test_analyze_command_no_ambiguity(self):
        """Test command with no ambiguity"""
        result = self.detector.analyze_command(
            "open safari",
            "open_app",
            {"app_name": "Safari"}
        )
        self.assertFalse(result["needs_clarification"])


class TestConversationAnalytics(unittest.TestCase):
    """Test conversation analytics"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_analytics.db"
        db_settings = DatabaseSettings(path=str(self.db_path))
        self.memory = MemoryEngine(db_settings)
        self.analytics = ConversationAnalytics(self.memory)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_start_tracking(self):
        """Test starting analytics tracking"""
        self.analytics.start_tracking("conv_1", "session_1")
        metrics = self.analytics.get_conversation_metrics("conv_1")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.conversation_id, "conv_1")
    
    def test_record_turn(self):
        """Test recording turns"""
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_turn("conv_1", True)
        self.analytics.record_turn("conv_1", False)
        
        metrics = self.analytics.get_conversation_metrics("conv_1")
        self.assertEqual(metrics.turn_count, 2)
        self.assertEqual(metrics.successful_turns, 1)
        self.assertEqual(metrics.failed_turns, 1)
    
    def test_record_clarification(self):
        """Test recording clarifications"""
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_turn("conv_1", True, had_clarification=True)
        self.analytics.record_clarification_resolved("conv_1", True)
        
        metrics = self.analytics.get_conversation_metrics("conv_1")
        self.assertEqual(metrics.clarification_count, 1)
        self.assertEqual(metrics.clarifications_resolved, 1)
    
    def test_record_implicit_reference(self):
        """Test recording implicit references"""
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_implicit_reference("conv_1")
        self.analytics.record_implicit_reference("conv_1")
        
        metrics = self.analytics.get_conversation_metrics("conv_1")
        self.assertEqual(metrics.implicit_references_resolved, 2)
    
    def test_end_tracking(self):
        """Test ending tracking"""
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_turn("conv_1", True)
        
        final_metrics = self.analytics.end_tracking("conv_1")
        self.assertIsNotNone(final_metrics)
        self.assertIsNotNone(final_metrics.end_time)
        self.assertIsNotNone(final_metrics.total_duration_seconds)
        
        # Should no longer be tracked
        metrics = self.analytics.get_conversation_metrics("conv_1")
        self.assertIsNone(metrics)
    
    def test_aggregate_metrics(self):
        """Test aggregate metrics calculation"""
        # Track multiple conversations
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_turn("conv_1", True)
        self.analytics.record_turn("conv_1", True, had_clarification=True)
        self.analytics.record_clarification_resolved("conv_1", True)
        
        self.analytics.start_tracking("conv_2", "session_1")
        self.analytics.record_turn("conv_2", False)
        
        agg = self.analytics.get_aggregate_metrics()
        self.assertEqual(agg.total_conversations, 2)
        self.assertEqual(agg.total_turns, 3)
        self.assertEqual(agg.total_clarifications, 1)
        self.assertEqual(agg.clarification_success_rate, 100.0)
    
    def test_summary_report(self):
        """Test summary report generation"""
        self.analytics.start_tracking("conv_1", "session_1")
        self.analytics.record_turn("conv_1", True)
        
        report = self.analytics.get_summary_report()
        self.assertIn("Total Conversations", report)
        self.assertIn("Total Turns", report)


if __name__ == "__main__":
    unittest.main()
