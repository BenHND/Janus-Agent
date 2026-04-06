"""
Tests for LLM Module - Native AI actions
TICKET 3: Reasoning Structuré
"""
import unittest

from janus.modules.llm_module import LLMModule


class TestLLMModule(unittest.TestCase):
    """Test LLM Module functionality"""

    def setUp(self):
        """Set up LLM module for testing"""
        self.module = LLMModule()
        self.module.initialize()

    def test_initialization(self):
        """Test LLM module initialization"""
        self.assertEqual(self.module.name, "llm")
        self.assertTrue(self.module.status.value in ["ready", "uninitialized"])

    def test_get_supported_actions(self):
        """Test getting supported actions list"""
        actions = self.module.get_supported_actions()

        self.assertIsInstance(actions, list)
        self.assertIn("summarize", actions)
        self.assertIn("rewrite", actions)
        self.assertIn("extract_keywords", actions)
        self.assertIn("analyze_error", actions)
        self.assertIn("answer_question", actions)

    def test_summarize_with_text(self):
        """Test summarize action with direct text"""
        action = {
            "action": "summarize",
            "args": {
                "text": "This is a long piece of text that needs to be summarized. It contains multiple sentences and paragraphs. The main idea is that we want to extract the key points."
            },
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "summarize")
        self.assertIn("summary", result)
        self.assertIsInstance(result["summary"], str)

    def test_summarize_without_text(self):
        """Test summarize action without text (should use last_result)"""
        # First set some text as last result
        self.module.last_result = "Some previous text to summarize"

        action = {"action": "summarize", "args": {}}
        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertIn("summary", result)

    def test_rewrite_with_style(self):
        """Test rewrite action with style"""
        action = {"action": "rewrite", "args": {"text": "Hey, what's up?", "style": "formal"}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "rewrite")
        self.assertIn("rewritten_text", result)
        self.assertEqual(result["style"], "formal")

    def test_extract_keywords(self):
        """Test extract keywords action"""
        action = {
            "action": "extract_keywords",
            "args": {
                "text": "Python programming is a powerful language. Python is used for web development, data science, automation, and machine learning. Learning Python opens many opportunities.",
                "max_keywords": 5,
            },
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "extract_keywords")
        self.assertIn("keywords", result)
        self.assertIsInstance(result["keywords"], list)
        self.assertLessEqual(len(result["keywords"]), 5)

    def test_analyze_error(self):
        """Test analyze error action"""
        action = {
            "action": "analyze_error",
            "args": {
                "error": "PermissionError: [Errno 13] Permission denied: '/etc/hosts'",
                "context": "Trying to modify system file",
            },
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "analyze_error")
        self.assertIn("analysis", result)
        self.assertIsInstance(result["analysis"], str)

    def test_analyze_error_without_context(self):
        """Test analyze error without context"""
        action = {
            "action": "analyze_error",
            "args": {"error": "FileNotFoundError: file.txt not found"},
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertIn("analysis", result)

    def test_answer_question(self):
        """Test answer question action"""
        action = {
            "action": "answer_question",
            "args": {
                "question": "What is Python?",
                "context": "Python is a high-level programming language known for its simplicity and readability.",
            },
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "answer_question")
        self.assertIn("answer", result)
        self.assertIn("question", result)

    def test_unknown_action(self):
        """Test handling of unknown action"""
        action = {"action": "unknown_action", "args": {}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertIn("supported_actions", result)

    def test_get_metadata(self):
        """Test getting module metadata"""
        metadata = self.module.get_metadata()

        self.assertIsInstance(metadata, dict)
        self.assertIn("name", metadata)
        self.assertEqual(metadata["name"], "llm")
        self.assertIn("supported_actions", metadata)

    # REMOVED: test_shared_context_integration (TICKET-AUDIT-001)
    # SharedContext was deleted with legacy orchestrators.
    # LLMModule no longer uses SharedContext.
        # Should have used the context value
        self.assertIn("summary", result)


class TestLLMModuleEdgeCases(unittest.TestCase):
    """Test edge cases for LLM module"""

    def setUp(self):
        """Set up LLM module"""
        self.module = LLMModule()
        self.module.initialize()

    def test_summarize_empty_text(self):
        """Test summarize with no text provided"""
        action = {"action": "summarize", "args": {}}

        result = self.module.execute(action)

        # Should return error when no text is available
        self.assertEqual(result["status"], "error")

    def test_rewrite_empty_text(self):
        """Test rewrite with no text"""
        action = {"action": "rewrite", "args": {"style": "formal"}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "error")

    def test_extract_keywords_empty_text(self):
        """Test extract keywords with no text"""
        action = {"action": "extract_keywords", "args": {}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "error")

    def test_analyze_error_no_error(self):
        """Test analyze error with no error message"""
        action = {"action": "analyze_error", "args": {}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "error")

    def test_answer_question_no_question(self):
        """Test answer question with no question"""
        action = {"action": "answer_question", "args": {}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "error")

    def test_last_result_persistence(self):
        """Test that last_result is updated correctly"""
        # Execute summarize
        action = {"action": "summarize", "args": {"text": "Test text for summarization"}}
        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        # Check that last_result was set
        self.assertIsNotNone(self.module.last_result)

        # Now execute another action without text - should use last_result
        action2 = {"action": "extract_keywords", "args": {"max_keywords": 3}}
        result2 = self.module.execute(action2)

        # Should work using the last_result
        self.assertEqual(result2["status"], "success")


class TestLLMModuleFallbacks(unittest.TestCase):
    """Test fallback behavior when LLM service unavailable"""

    def setUp(self):
        """Set up module without LLM service"""
        self.module = LLMModule()
        self.module.initialize()
        # Force service to be unavailable for testing fallbacks
        if self.module.llm_service:
            self.module.llm_service.available = False

    def test_summarize_fallback(self):
        """Test summarize falls back to truncation"""
        action = {
            "action": "summarize",
            "args": {"text": " ".join(["word"] * 200), "max_length": 50},  # Long text
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertIn("summary", result)
        self.assertTrue(result.get("fallback", False))

    def test_extract_keywords_fallback(self):
        """Test keyword extraction falls back to frequency analysis"""
        action = {
            "action": "extract_keywords",
            "args": {
                "text": "Python programming language Python code Python development",
                "max_keywords": 3,
            },
        }

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertIn("keywords", result)
        # Should extract "python" as top keyword
        keywords = result["keywords"]
        self.assertIsInstance(keywords, list)

    def test_analyze_error_fallback(self):
        """Test error analysis falls back to pattern matching"""
        action = {"action": "analyze_error", "args": {"error": "Permission denied"}}

        result = self.module.execute(action)

        self.assertEqual(result["status"], "success")
        self.assertIn("analysis", result)
        self.assertIn("suggestions", result)
        self.assertTrue(result.get("fallback", False))


if __name__ == "__main__":
    unittest.main()
