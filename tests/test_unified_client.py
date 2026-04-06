"""
Tests for UnifiedLLMClient module
"""
import unittest

from janus.ai.llm.unified_client import UnifiedLLMClient


class TestUnifiedLLMClient(unittest.TestCase):
    """Test UnifiedLLMClient functionality"""

    def setUp(self):
        """Set up test LLM client with mock provider"""
        self.llm = UnifiedLLMClient(provider="mock")

    def test_initialization(self):
        """Test LLM client initialization"""
        self.assertEqual(self.llm.provider, "mock")
        self.assertIsNotNone(self.llm.client)
        self.assertTrue(self.llm.available)

    def test_generate(self):
        """Test basic text generation"""
        result = self.llm.generate("test prompt")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_chat(self):
        """Test chat generation"""
        messages = [
            {"role": "user", "content": "test message"}
        ]
        result = self.llm.generate_chat(messages)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_analyze_command(self):
        """Test command analysis"""
        result = self.llm.analyze_command("open chrome")
        self.assertEqual(result["status"], "success")
        self.assertIn("intent", result)

    def test_analyze_content_summarize(self):
        """Test content summarization"""
        content = "This is a test content with multiple sentences. It contains some information."
        result = self.llm.analyze_content(content, "text", "summarize")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task"], "summarize")
        self.assertIn("result", result)

    def test_analyze_content_code(self):
        """Test code analysis"""
        code = "def hello():\n    print('Hello, world!')"
        result = self.llm.analyze_content(code, "code", "analyze")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["content_type"], "code")

    def test_openai_fallback_without_key(self):
        """Test OpenAI initialization falls back to mock without API key"""
        llm = UnifiedLLMClient(provider="openai", fallback_providers=["mock"])
        # Should fallback to mock
        self.assertEqual(llm.provider, "mock")

    def test_local_fallback(self):
        """Test local LLM falls back to mock"""
        llm = UnifiedLLMClient(provider="local", model_path="/nonexistent/path", fallback_providers=["mock"])
        # Should fallback to mock
        self.assertEqual(llm.provider, "mock")


if __name__ == "__main__":
    unittest.main()
