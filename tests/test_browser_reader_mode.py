"""
Tests for BrowserAgent Reader Mode (TICKET-APP-002)

This test suite validates the get_page_content functionality that allows
the LLM to read entire web pages instantly without visual scrolling.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class MockOSInterface:
    """Mock OS interface for testing."""
    
    def is_available(self):
        return True
    
    def run_script(self, script):
        # Simulate HTML extraction
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Article</title></head>
        <body>
            <nav>Navigation menu</nav>
            <article>
                <h1>Main Article Title</h1>
                <p>This is the main content of the article.</p>
                <p>It contains important information.</p>
            </article>
            <aside>Advertisement</aside>
            <footer>Footer content</footer>
        </body>
        </html>
        """
        return MagicMock(success=True, data={"stdout": html_content}, error=None)


class TestBrowserReaderMode(unittest.TestCase):
    """Test get_page_content action (Reader Mode)."""
    
    @staticmethod
    def _get_method_content(file_content: str, method_name: str) -> str:
        """Helper to extract a method's content from file."""
        method_start = file_content.find(f"async def {method_name}")
        if method_start == -1:
            return ""
        
        # Find next method or end of file
        next_method = file_content.find("\n    async def ", method_start + 1)
        if next_method == -1:
            next_method = len(file_content)
        
        return file_content[method_start:next_method]
    
    def test_get_page_content_action_exists(self):
        """Test that get_page_content action is registered in execute method."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify get_page_content action is handled
        self.assertIn('action == "get_page_content"', content,
                      "get_page_content action should be handled in execute method")
        self.assertIn('_get_page_content', content,
                      "_get_page_content method should exist")
    
    def test_get_page_content_method_exists(self):
        """Test that _get_page_content method exists with proper signature."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify method signature
        self.assertIn("async def _get_page_content(", content,
                      "_get_page_content method should exist")
    
    def test_get_page_content_uses_trafilatura(self):
        """Test that _get_page_content uses trafilatura for content extraction."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        self.assertTrue(method_content, "_get_page_content should exist")
        
        # Verify trafilatura is imported and used
        self.assertIn("import trafilatura", method_content,
                      "Should import trafilatura")
        self.assertIn("trafilatura.extract", method_content,
                      "Should use trafilatura.extract")
    
    def test_get_page_content_returns_markdown(self):
        """Test that _get_page_content extracts content in Markdown format."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        
        # Verify Markdown output format
        self.assertIn("output_format='markdown'", method_content,
                      "Should request Markdown output format")
    
    def test_get_page_content_extracts_full_html(self):
        """Test that _get_page_content extracts full HTML from browser."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        
        # Verify it extracts outerHTML
        self.assertIn("document.documentElement.outerHTML", method_content,
                      "Should extract full HTML document")
    
    def test_get_page_content_includes_links_and_tables(self):
        """Test that _get_page_content preserves links and tables."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        
        # Verify configuration for links and tables
        self.assertIn("include_links=True", method_content,
                      "Should include links in output")
        self.assertIn("include_tables=True", method_content,
                      "Should include tables in output")
    
    def test_get_page_content_has_fallback(self):
        """Test that _get_page_content has fallback to text format."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        
        # Verify fallback to text format
        self.assertIn("output_format='txt'", method_content,
                      "Should have fallback to text format")
    
    def test_get_page_content_returns_content_in_data(self):
        """Test that _get_page_content returns content in data field."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        method_content = self._get_method_content(content, "_get_page_content")
        
        # Verify return structure
        self.assertIn('"content":', method_content,
                      "Should return content in data")
        self.assertIn('"format":', method_content,
                      "Should return format in data")
    
    def test_documentation_updated(self):
        """Test that BrowserAgent documentation mentions 6 operations."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Check docstring is updated
        self.assertIn("6 atomic operations", content,
                      "Documentation should mention 6 operations")
        self.assertIn("get_page_content", content,
                      "Documentation should mention get_page_content")
        self.assertIn("TICKET-APP-002", content,
                      "Documentation should reference TICKET-APP-002")


class TestTrafilaturaIntegration(unittest.TestCase):
    """Test trafilatura integration."""
    
    def test_trafilatura_is_installed(self):
        """Test that trafilatura is available."""
        try:
            import trafilatura
            self.assertTrue(True, "trafilatura is installed")
        except ImportError:
            self.fail("trafilatura should be installed")
    
    def test_trafilatura_extract_works(self):
        """Test basic trafilatura extraction."""
        import trafilatura
        
        html = """
        <html>
        <body>
            <article>
                <h1>Test Title</h1>
                <p>Test content paragraph.</p>
            </article>
        </body>
        </html>
        """
        
        result = trafilatura.extract(html, output_format='markdown')
        
        # Basic validation - should extract some content
        self.assertIsNotNone(result, "Should extract content")
        if result:
            self.assertIn("Test", result, "Should contain test content")


class TestReaderModeRequirements(unittest.TestCase):
    """Test that Reader Mode meets acceptance criteria."""
    
    def test_requirements_in_file(self):
        """Test that trafilatura is in requirements.txt."""
        with open("requirements.txt", "r") as f:
            content = f.read()
        
        self.assertIn("trafilatura", content,
                      "trafilatura should be in requirements.txt")
    
    def test_requirements_in_source(self):
        """Test that trafilatura is in requirements.in."""
        with open("requirements.in", "r") as f:
            content = f.read()
        
        self.assertIn("trafilatura", content,
                      "trafilatura should be in requirements.in")
        self.assertIn("TICKET-APP-002", content,
                      "Should reference TICKET-APP-002 in requirements")


if __name__ == "__main__":
    unittest.main(verbosity=2)
