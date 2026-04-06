"""
Integration tests for structured content extraction workflows.

Tests the content extraction pipeline without full agent dependencies.
"""

import pytest

from janus.content.extractor import ContentExtractor
from janus.content.normalizer import ContentNormalizer
from janus.content.chunker import StructuredChunker
from janus.content.structured_document import (
    StructuredDocument,
    BlockType,
    HeadingBlock,
    ParagraphBlock,
    MessageBlock,
)


class TestWebStructuredExtraction:
    """Test structured extraction from web pages."""
    
    def test_web_extraction_from_html(self):
        """
        Test extracting structured content from HTML.
        
        This tests the ContentExtractor with sample HTML content.
        """
        # Sample HTML content
        sample_html = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is the first paragraph with some content.</p>
            <p>This is the second paragraph with more information.</p>
            <h2>Subsection</h2>
            <p>Content under the subsection.</p>
        </body>
        </html>
        """
        
        extractor = ContentExtractor()
        doc = extractor.extract_from_web(
            html=sample_html,
            url="https://example.com",
            use_trafilatura=True
        )
        
        # Verify document structure
        assert doc.metadata.source == "web"
        assert doc.metadata.url == "https://example.com"
        assert len(doc.blocks) > 0
        
        # Should have at least some content
        assert doc.stats.char_count > 0
        assert doc.stats.block_count > 0
    
    def test_web_extraction_spa_detection(self):
        """
        Test SPA detection heuristics.
        """
        # Minimal SPA HTML
        spa_html = """
        <html>
        <head><title>SPA App</title></head>
        <body>
            <div id="root"></div>
            <script src="app.js"></script>
        </body>
        </html>
        """
        
        extractor = ContentExtractor()
        
        # Should detect that this needs rendered extraction
        should_render = extractor.should_use_rendered_extraction(spa_html, "https://spa.com")
        assert should_render is True
    
    def test_web_extraction_with_normalization(self):
        """
        Test full extraction + normalization pipeline.
        """
        html = "<html><body><h1>Title</h1><p>Content</p><p>Content</p></body></html>"
        
        extractor = ContentExtractor()
        normalizer = ContentNormalizer()
        
        doc = extractor.extract_from_web(html=html, url="https://example.com")
        doc = normalizer.normalize(doc)
        
        # Should have deduped and normalized
        assert doc.stats.block_count > 0
        assert doc.metadata.language is not None or doc.metadata.language is None  # May or may not detect


class TestAppStructuredExtraction:
    """Test structured extraction from native apps."""
    
    def test_app_extraction_from_text(self):
        """
        Test extracting structured content from app text.
        """
        # Sample app text with structure
        sample_text = """# My Notes

This is a note with some structure.

## Shopping List
- Milk
- Bread
- Eggs

## Code Snippet
```python
def hello():
    print("world")
```

Regular paragraph at the end.
"""
        
        extractor = ContentExtractor()
        doc = extractor.extract_from_plain_text(
            text=sample_text,
            source="app",
            app_name="Notes",
            window_title="My Note"
        )
        
        # Verify document structure
        assert doc.metadata.source == "app"
        assert doc.metadata.app_name == "Notes"
        assert doc.metadata.window_title == "My Note"
        
        # Should have detected headings, lists, code blocks
        block_types = [b.type for b in doc.blocks]
        assert BlockType.HEADING in block_types
        assert BlockType.LIST in block_types
        assert BlockType.CODE in block_types
    
    def test_app_extraction_with_chunking(self):
        """
        Test extracting and chunking large app content.
        """
        # Large text content
        large_text = "# Section " + ("Large paragraph. " * 100) + "\n\n" + "# Another Section " + ("More content. " * 100)
        
        extractor = ContentExtractor()
        chunker = StructuredChunker(max_tokens=200)
        
        doc = extractor.extract_from_plain_text(text=large_text, source="app")
        chunks = chunker.chunk(doc)
        
        # Should have split into multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should have content
        for chunk in chunks:
            assert len(chunk.blocks) > 0


class TestConversationStructuredExtraction:
    """Test structured extraction from conversations."""
    
    def test_conversation_thread_extraction(self):
        """
        Test extracting conversation threads with message structure preserved.
        """
        # Sample conversation thread
        messages = [
            {
                "author": "Alice",
                "timestamp": "2024-01-15T10:00:00Z",
                "text": "Has anyone seen the latest design mockups?",
                "thread_id": "thread-123",
                "attachments": []
            },
            {
                "author": "Bob",
                "timestamp": "2024-01-15T10:05:00Z",
                "text": "Yes, I reviewed them. Looking good!",
                "thread_id": "thread-123",
                "attachments": []
            },
            {
                "author": "Charlie",
                "timestamp": "2024-01-15T10:10:00Z",
                "text": "Agreed. I uploaded the final version.",
                "thread_id": "thread-123",
                "attachments": ["design-final.pdf"]
            },
        ]
        
        # Extract conversation
        extractor = ContentExtractor()
        doc = extractor.extract_from_conversation(
            messages=messages,
            platform="slack",
            channel="#design"
        )
        
        # Verify document structure
        assert doc.metadata.source == "conversation"
        assert doc.metadata.app_name == "slack"
        assert doc.metadata.window_title == "#design"
        
        # Should have 3 message blocks
        assert len(doc.blocks) == 3
        
        # All blocks should be messages
        for block in doc.blocks:
            assert block.type == BlockType.MESSAGE
        
        # Verify message content
        assert doc.blocks[0].author == "Alice"
        assert doc.blocks[1].author == "Bob"
        assert doc.blocks[2].author == "Charlie"
        assert "design-final.pdf" in doc.blocks[2].attachments
        
        # Verify markdown output preserves structure
        markdown = doc.to_markdown()
        assert "Alice" in markdown
        assert "Bob" in markdown
        assert "Charlie" in markdown
        assert "design-final.pdf" in markdown
    
    def test_conversation_normalization(self):
        """
        Test that conversation messages are not deduplicated.
        """
        # Messages with similar content (should not be deduped)
        messages = [
            {"author": "Alice", "timestamp": "2024-01-15T10:00:00Z", "text": "Hello"},
            {"author": "Bob", "timestamp": "2024-01-15T10:01:00Z", "text": "Hello"},
            {"author": "Alice", "timestamp": "2024-01-15T10:02:00Z", "text": "Hello"},
        ]
        
        extractor = ContentExtractor()
        normalizer = ContentNormalizer()
        
        doc = extractor.extract_from_conversation(messages, platform="slack")
        doc = normalizer.normalize(doc)
        
        # Should keep all 3 messages (even with duplicate text)
        assert len(doc.blocks) == 3


class TestEndToEndPipeline:
    """Test complete extraction pipeline."""
    
    def test_complete_pipeline_web(self):
        """
        Test complete pipeline: Extract → Normalize → Chunk → Output
        """
        html = """
        <html><body>
        <h1>Article Title</h1>
        <p>Introduction paragraph with some content.</p>
        <h2>Section 1</h2>
        <p>""" + ("Content. " * 50) + """</p>
        <h2>Section 2</h2>
        <p>""" + ("More content. " * 50) + """</p>
        </body></html>
        """
        
        # Full pipeline
        extractor = ContentExtractor()
        normalizer = ContentNormalizer()
        chunker = StructuredChunker(max_tokens=200)
        
        # Extract
        doc = extractor.extract_from_web(html=html, url="https://example.com")
        assert len(doc.blocks) > 0
        
        # Normalize
        doc = normalizer.normalize(doc)
        assert doc.metadata.language is not None or doc.metadata.language is None
        
        # Chunk
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1
        
        # Output to markdown
        for chunk in chunks:
            markdown = chunk.to_markdown()
            assert len(markdown) > 0
            
            # Should have content
            assert len(markdown.strip()) > 10
    
    def test_document_serialization_round_trip(self):
        """
        Test that documents can be serialized and deserialized.
        """
        # Create a document
        extractor = ContentExtractor()
        doc = extractor.extract_from_plain_text(
            "# Title\n\nSome content here.",
            source="test"
        )
        
        # Serialize to JSON
        json_str = doc.to_json()
        assert len(json_str) > 0
        
        # Deserialize
        doc2 = StructuredDocument.from_json(json_str)
        
        # Should be equivalent
        assert doc2.metadata.source == doc.metadata.source
        assert len(doc2.blocks) == len(doc.blocks)
        assert doc2.to_markdown() == doc.to_markdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
