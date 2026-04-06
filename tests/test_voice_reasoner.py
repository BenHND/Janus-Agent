"""
Unit tests for Voice Reasoner (Voice Reasoning Engine)
"""
import os
import tempfile
import unittest

from janus.ai.reasoning.voice_reasoner import ReasonedIntent, VoiceReasoner


class TestVoiceReasoner(unittest.TestCase):
    """Test cases for VoiceReasoner"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary context storage
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        self.temp_file.close()

        self.reasoner = VoiceReasoner(
            classifier_model_path=None,  # No ML model for tests
            context_storage_path=self.temp_file.name,
            use_ml_classifier=False,  # Use parser only for testing
        )

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_file.name)
        except:
            pass

    def test_simple_command_french(self):
        """Test simple French command reasoning"""
        intents = self.reasoner.reason("ouvre Chrome")

        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].intent, "open_app")
        self.assertIn("app_name", intents[0].parameters)
        self.assertGreater(intents[0].confidence, 0.5)

    def test_simple_command_english(self):
        """Test simple English command reasoning"""
        intents = self.reasoner.reason("open Safari")

        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].intent, "open_app")
        self.assertIn("app_name", intents[0].parameters)

    def test_multi_action_command(self):
        """Test multi-action command reasoning"""
        intents = self.reasoner.reason("ouvre Chrome et va sur github.com")

        self.assertGreaterEqual(len(intents), 2)
        self.assertEqual(intents[0].intent, "open_app")
        self.assertEqual(intents[1].intent, "open_url")

    def test_context_tracking(self):
        """Test context tracking across commands"""
        # First command
        self.reasoner.reason("ouvre Chrome")

        # Context should remember last app
        self.assertEqual(self.reasoner.context.get_context("last_app"), "Chrome")

    def test_implicit_reference_resolution(self):
        """Test implicit reference resolution"""
        # Open Chrome first
        self.reasoner.reason("ouvre Chrome")

        # Navigate without specifying browser
        intents = self.reasoner.reason("va sur github.com")

        # Should have implicit browser in parameters
        self.assertIn("implicit_browser", intents[0].parameters)
        self.assertEqual(intents[0].parameters["implicit_browser"], "Chrome")

    def test_file_context(self):
        """Test file context tracking"""
        # Open a file
        self.reasoner.reason("ouvre le fichier test.py")

        # Check context
        self.assertIn("test.py", self.reasoner.context.get_context("last_file"))

    def test_reason_with_feedback(self):
        """Test reasoning with detailed feedback"""
        result = self.reasoner.reason_with_feedback("ouvre Chrome")

        self.assertEqual(result["status"], "success")
        self.assertIn("intents", result)
        self.assertIn("context", result)
        self.assertIn("statistics", result)
        self.assertGreater(result["count"], 0)

    def test_clear_context(self):
        """Test clearing context"""
        self.reasoner.reason("ouvre Chrome")
        self.reasoner.clear_context()

        self.assertIsNone(self.reasoner.context.get_context("last_app"))
        self.assertEqual(len(self.reasoner.context.history), 0)

    def test_cleanup_sensitive_data(self):
        """Test sensitive data cleanup"""
        self.reasoner.reason("va sur https://secret-site.com")
        self.reasoner.cleanup_sensitive_data()

        self.assertIsNone(self.reasoner.context.get_context("last_url"))

    def test_get_statistics(self):
        """Test getting reasoner statistics"""
        stats = self.reasoner.get_statistics()

        self.assertIn("parser", stats)
        self.assertIn("context", stats)
        self.assertIn("synonyms_fr", stats["parser"])
        self.assertIn("total_commands", stats["context"])

    def test_empty_command(self):
        """Test empty command handling"""
        intents = self.reasoner.reason("")

        self.assertEqual(len(intents), 0)

    def test_unknown_command(self):
        """Test unknown command handling"""
        intents = self.reasoner.reason("fais quelque chose d'impossible")

        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].intent, "unknown")

    def test_confidence_levels(self):
        """Test confidence levels in results"""
        intents = self.reasoner.reason("ouvre Chrome")

        self.assertGreater(intents[0].confidence, 0.0)
        self.assertLessEqual(intents[0].confidence, 1.0)

    def test_source_tracking(self):
        """Test source tracking (parser vs classifier)"""
        intents = self.reasoner.reason("ouvre Chrome")

        self.assertIn(intents[0].source, ["parser", "classifier", "hybrid"])

    def test_context_persistence(self):
        """Test context persistence across reasoner instances"""
        self.reasoner.reason("ouvre Chrome")

        # Create new reasoner with same storage
        reasoner2 = VoiceReasoner(
            context_storage_path=self.temp_file.name,
            use_ml_classifier=False,
        )

        # Context should be loaded
        self.assertEqual(reasoner2.context.get_context("last_app"), "Chrome")

    def test_add_to_context_flag(self):
        """Test add_to_context flag"""
        # Don't add to context
        self.reasoner.reason("ouvre Chrome", add_to_context=False)

        # Context should be empty
        self.assertEqual(len(self.reasoner.context.history), 0)

        # Add to context
        self.reasoner.reason("ouvre Safari", add_to_context=True)

        # Context should have one entry
        self.assertEqual(len(self.reasoner.context.history), 1)

    def test_complex_workflow(self):
        """Test complex multi-step workflow"""
        # Step 1: Open editor
        intents1 = self.reasoner.reason("ouvre VSCode")
        self.assertEqual(intents1[0].intent, "open_app")

        # Step 2: Open file (implicit editor context)
        intents2 = self.reasoner.reason("ouvre le fichier main.py")
        self.assertEqual(intents2[0].intent, "open_file")

        # Step 3: Go to line (implicit file context)
        intents3 = self.reasoner.reason("va à la ligne 42")
        self.assertEqual(intents3[0].intent, "goto_line")
        self.assertIn("implicit_file", intents3[0].parameters)


if __name__ == "__main__":
    unittest.main()
