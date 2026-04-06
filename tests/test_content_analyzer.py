"""
Tests for Content Analyzer module
"""
import unittest

from janus.ai.llm.content_analyzer import AnalysisTask, ContentAnalyzer, ContentType


class TestContentAnalyzer(unittest.TestCase):
    """Test Content Analyzer functionality"""

    def setUp(self):
        """Set up test content analyzer"""
        self.analyzer = ContentAnalyzer()

    def test_analyze_text(self):
        """Test text analysis"""
        content = "This is a test document with multiple sentences."
        result = self.analyzer.analyze(content, "text", "summarize")
        self.assertEqual(result["status"], "success")
        self.assertIn("stats", result)

    def test_analyze_code(self):
        """Test code analysis"""
        code = "def hello():\n    print('Hello')\n    return True"
        result = self.analyzer.analyze(code, "code", "analyze")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["content_type"], "code")

    def test_summarize_code(self):
        """Test code summarization"""
        code = "function add(a, b) { return a + b; }"
        result = self.analyzer.summarize_code(code, "javascript")
        self.assertEqual(result["status"], "success")

    def test_explain_code(self):
        """Test code explanation"""
        code = "print('Hello, World!')"
        result = self.analyzer.explain_code(code, "python")
        self.assertEqual(result["status"], "success")

    def test_debug_code(self):
        """Test code debugging"""
        code = "result = 10 / 0"
        error = "ZeroDivisionError: division by zero"
        result = self.analyzer.debug_code(code, error, "python")
        self.assertEqual(result["status"], "success")
        self.assertIn("debug", result)

    def test_review_code(self):
        """Test code review"""
        code = "x=1\ny=2\nprint x+y"
        result = self.analyzer.review_code(code, "python")
        self.assertEqual(result["status"], "success")

    def test_summarize_text(self):
        """Test text summarization"""
        text = "A" * 500  # Long text
        result = self.analyzer.summarize_text(text, max_length=100)
        self.assertEqual(result["status"], "success")

    def test_extract_info(self):
        """Test information extraction"""
        content = "Contact us at info@example.com or call 555-1234"
        result = self.analyzer.extract_info(content, "emails")
        self.assertEqual(result["status"], "success")

    def test_detect_content_type_json(self):
        """Test JSON content type detection"""
        content = '{"key": "value"}'
        ctype = self.analyzer.detect_content_type(content)
        self.assertEqual(ctype, "json")

    def test_detect_content_type_code(self):
        """Test code content type detection"""
        content = "def function():\n    pass"
        ctype = self.analyzer.detect_content_type(content)
        self.assertEqual(ctype, "code")

    def test_detect_content_type_by_extension(self):
        """Test content type detection by file extension"""
        ctype = self.analyzer.detect_content_type("", "test.py")
        self.assertEqual(ctype, "code")

        ctype = self.analyzer.detect_content_type("", "test.json")
        self.assertEqual(ctype, "json")

        ctype = self.analyzer.detect_content_type("", "test.md")
        self.assertEqual(ctype, "markdown")

    def test_detect_error_content(self):
        """Test error content detection"""
        content = "Error: Something went wrong\nTraceback (most recent call last):"
        ctype = self.analyzer.detect_content_type(content)
        self.assertEqual(ctype, "error")

    def test_invalid_content_type(self):
        """Test invalid content type"""
        result = self.analyzer.analyze("test", "invalid_type", "summarize")
        self.assertEqual(result["status"], "error")

    def test_invalid_task(self):
        """Test invalid task"""
        result = self.analyzer.analyze("test", "text", "invalid_task")
        self.assertEqual(result["status"], "error")

    def test_basic_analysis_stats(self):
        """Test basic analysis statistics"""
        content = "Line 1\nLine 2\nLine 3"
        result = self.analyzer.analyze(content, "text", "analyze")
        self.assertIn("stats", result)
        self.assertEqual(result["stats"]["lines"], 3)


if __name__ == "__main__":
    unittest.main()
