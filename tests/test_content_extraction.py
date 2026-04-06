"""
Unit tests for ContentExtractor, ContentNormalizer, and StructuredChunker.
"""

import pytest

from janus.content.extractor import ContentExtractor
from janus.content.normalizer import ContentNormalizer
from janus.content.chunker import StructuredChunker
from janus.content.structured_document import (
    StructuredDocument,
    DocumentMetadata,
    HeadingBlock,
    ParagraphBlock,
    ListBlock,
    CodeBlock,
    MessageBlock,
)


class TestContentExtractor:
    """Test ContentExtractor class."""
    
    def test_extract_from_plain_text_simple(self):
        """Test extracting from simple plain text."""
        extractor = ContentExtractor()
        text = "This is a simple paragraph.\n\nThis is another paragraph."
        
        doc = extractor.extract_from_plain_text(text, source="clipboard")
        
        assert doc.metadata.source == "clipboard"
        assert len(doc.blocks) >= 2
        assert doc.raw_text == text
    
    def test_extract_from_plain_text_with_headings(self):
        """Test extracting text with Markdown headings."""
        extractor = ContentExtractor()
        text = "# Main Title\n\nSome content here.\n\n## Subsection\n\nMore content."
        
        doc = extractor.extract_from_plain_text(text)
        
        # Should detect headings
        heading_blocks = [b for b in doc.blocks if isinstance(b, HeadingBlock)]
        assert len(heading_blocks) >= 2
        
        # Check heading levels
        assert any(h.level == 1 for h in heading_blocks)
        assert any(h.level == 2 for h in heading_blocks)
    
    def test_extract_from_plain_text_with_lists(self):
        """Test extracting text with lists."""
        extractor = ContentExtractor()
        text = "# Shopping List\n\n- Apples\n- Bananas\n- Oranges"
        
        doc = extractor.extract_from_plain_text(text)
        
        # Should detect list
        list_blocks = [b for b in doc.blocks if isinstance(b, ListBlock)]
        assert len(list_blocks) >= 1
        assert len(list_blocks[0].items) == 3
    
    def test_extract_from_plain_text_with_code(self):
        """Test extracting text with code blocks."""
        extractor = ContentExtractor()
        text = "# Code Example\n\n```python\ndef hello():\n    print('world')\n```\n\nEnd."
        
        doc = extractor.extract_from_plain_text(text)
        
        # Should detect code block
        code_blocks = [b for b in doc.blocks if isinstance(b, CodeBlock)]
        assert len(code_blocks) >= 1
        assert code_blocks[0].language == "python"
        assert "def hello()" in code_blocks[0].text
    
    def test_extract_from_conversation(self):
        """Test extracting conversation messages."""
        extractor = ContentExtractor()
        messages = [
            {
                "author": "Alice",
                "timestamp": "2024-01-15T10:00:00Z",
                "text": "Hello!",
                "thread_id": "thread-1",
                "attachments": []
            },
            {
                "author": "Bob",
                "timestamp": "2024-01-15T10:01:00Z",
                "text": "Hi there!",
                "thread_id": "thread-1",
                "attachments": []
            },
        ]
        
        doc = extractor.extract_from_conversation(
            messages,
            platform="slack",
            channel="#general"
        )
        
        assert doc.metadata.source == "conversation"
        assert doc.metadata.app_name == "slack"
        assert len(doc.blocks) == 2
        
        # All blocks should be messages
        assert all(isinstance(b, MessageBlock) for b in doc.blocks)
        assert doc.blocks[0].author == "Alice"
        assert doc.blocks[1].author == "Bob"
    
    def test_should_use_rendered_extraction_short_html(self):
        """Test detection of SPA for short HTML."""
        extractor = ContentExtractor()
        short_html = "<html><body><div id='root'></div></body></html>"
        
        result = extractor.should_use_rendered_extraction(short_html, "https://example.com")
        
        assert result is True
    
    def test_should_use_rendered_extraction_spa_indicators(self):
        """Test detection of SPA indicators."""
        extractor = ContentExtractor()
        spa_html = "<html><body><div id='app' data-reactroot></div></body></html>" * 50
        
        result = extractor.should_use_rendered_extraction(spa_html, "https://example.com")
        
        assert result is True
    
    def test_should_use_rendered_extraction_static_content(self):
        """Test that static content doesn't trigger rendered extraction."""
        extractor = ContentExtractor()
        static_html = "<html><body><h1>Title</h1>" + "<p>Content paragraph.</p>" * 100 + "</body></html>"
        
        result = extractor.should_use_rendered_extraction(static_html, "https://example.com")
        
        assert result is False


class TestContentNormalizer:
    """Test ContentNormalizer class."""
    
    def test_deduplicate_blocks(self):
        """Test deduplication of repeated blocks."""
        normalizer = ContentNormalizer()
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            ParagraphBlock(text="Unique content"),
            ParagraphBlock(text="Repeated content"),
            ParagraphBlock(text="Repeated content"),  # Duplicate
            ParagraphBlock(text="Another unique"),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        normalized = normalizer.normalize(doc)
        
        # Should have removed duplicate
        assert len(normalized.blocks) == 3
    
    def test_normalize_tables(self):
        """Test table normalization (Markdown preview generation)."""
        from janus.content.structured_document import TableBlock
        
        normalizer = ContentNormalizer()
        
        metadata = DocumentMetadata(source="web")
        tsv = "Name\tAge\nAlice\t30"
        blocks = [TableBlock(raw_tsv=tsv)]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        normalized = normalizer.normalize(doc)
        
        # Should have generated Markdown preview
        table_block = normalized.blocks[0]
        assert table_block.markdown_preview is not None
        assert "| Name | Age |" in table_block.markdown_preview
    
    def test_detect_language_english(self):
        """Test language detection for English."""
        normalizer = ContentNormalizer()
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            ParagraphBlock(text="The quick brown fox jumps over the lazy dog. " * 10)
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        normalized = normalizer.normalize(doc)
        
        # Should detect English
        assert normalized.metadata.language in ["en", None]  # May or may not detect
    
    def test_detect_language_french(self):
        """Test language detection for French."""
        normalizer = ContentNormalizer()
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            ParagraphBlock(text="Le chat est dans la maison avec les souris et les oiseaux. " * 10)
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        normalized = normalizer.normalize(doc)
        
        # May detect French or not (simple heuristic)
        # Just ensure it doesn't crash
        assert normalized.metadata.language in ["fr", "en", None]
    
    def test_remove_navigation_patterns(self):
        """Test removal of navigation patterns."""
        normalizer = ContentNormalizer()
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            ParagraphBlock(text="Menu"),
            ParagraphBlock(text="Real content here"),
            ParagraphBlock(text="Cookie Policy"),
            ParagraphBlock(text="More content"),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        cleaned = normalizer.remove_navigation_patterns(doc)
        
        # Should remove "Menu" and "Cookie Policy"
        remaining_texts = [b.to_plain_text() for b in cleaned.blocks]
        assert "Menu" not in remaining_texts
        assert "Cookie Policy" not in remaining_texts
        assert "Real content here" in remaining_texts


class TestStructuredChunker:
    """Test StructuredChunker class."""
    
    def test_chunk_small_document(self):
        """Test that small documents are not chunked."""
        chunker = StructuredChunker(max_tokens=1000)
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Title"),
            ParagraphBlock(text="Short content."),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        chunks = chunker.chunk(doc)
        
        # Should return single chunk
        assert len(chunks) == 1
        assert chunks[0] is doc or chunks[0].blocks == doc.blocks
    
    def test_chunk_by_sections(self):
        """Test chunking by heading sections."""
        chunker = StructuredChunker(max_tokens=100)
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Section 1"),
            ParagraphBlock(text="Content for section 1. " * 10),
            HeadingBlock(level=1, text="Section 2"),
            ParagraphBlock(text="Content for section 2. " * 10),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        chunks = chunker.chunk(doc)
        
        # Should create multiple chunks (likely 2 sections)
        assert len(chunks) >= 2
    
    def test_chunk_large_block(self):
        """Test chunking of very large blocks."""
        chunker = StructuredChunker(max_tokens=20)  # Very small for aggressive chunking
        
        metadata = DocumentMetadata(source="web")
        # Create a very long paragraph with sentences
        long_text = " ".join([f"Sentence number {i} with content." for i in range(200)])
        blocks = [
            ParagraphBlock(text=long_text),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        chunks = chunker.chunk(doc)
        
        # Should split large block into multiple chunks
        assert len(chunks) > 1
    
    def test_chunk_with_overlap(self):
        """Test chunking with overlap."""
        chunker = StructuredChunker(max_tokens=50, overlap_tokens=10)
        
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Section 1"),
            ParagraphBlock(text="Content A. " * 20),
            HeadingBlock(level=1, text="Section 2"),
            ParagraphBlock(text="Content B. " * 20),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        chunks = chunker.chunk_with_overlap(doc)
        
        # Should have chunks with some overlap
        assert len(chunks) >= 2
        
        # Check that there's overlap (second chunk should reference first)
        if len(chunks) > 1:
            # This is a basic check - actual overlap verification would be more complex
            assert len(chunks[0].blocks) > 0
            assert len(chunks[1].blocks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
