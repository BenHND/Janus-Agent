"""
Unit tests for StructuredDocument and content extraction components.

Tests the core data structures and conversion methods.
"""

import json
import pytest
from datetime import datetime

from janus.content.structured_document import (
    StructuredDocument,
    DocumentMetadata,
    DocumentStats,
    BlockType,
    HeadingBlock,
    ParagraphBlock,
    ListBlock,
    CodeBlock,
    TableBlock,
    MessageBlock,
)


class TestDocumentBlocks:
    """Test individual block types."""
    
    def test_heading_block(self):
        """Test heading block creation and rendering."""
        block = HeadingBlock(level=2, text="Test Heading")
        
        assert block.type == BlockType.HEADING
        assert block.to_markdown() == "## Test Heading"
        assert block.to_plain_text() == "Test Heading"
    
    def test_heading_block_invalid_level(self):
        """Test that invalid heading levels raise error."""
        with pytest.raises(ValueError):
            HeadingBlock(level=7, text="Invalid")
        
        with pytest.raises(ValueError):
            HeadingBlock(level=0, text="Invalid")
    
    def test_paragraph_block(self):
        """Test paragraph block."""
        block = ParagraphBlock(text="This is a test paragraph.")
        
        assert block.type == BlockType.PARAGRAPH
        assert block.to_markdown() == "This is a test paragraph."
        assert block.to_plain_text() == "This is a test paragraph."
    
    def test_list_block_unordered(self):
        """Test unordered list block."""
        items = ["Item 1", "Item 2", "Item 3"]
        block = ListBlock(items=items, ordered=False)
        
        assert block.type == BlockType.LIST
        assert block.to_markdown() == "- Item 1\n- Item 2\n- Item 3"
        assert block.to_plain_text() == "Item 1\nItem 2\nItem 3"
    
    def test_list_block_ordered(self):
        """Test ordered list block."""
        items = ["First", "Second", "Third"]
        block = ListBlock(items=items, ordered=True)
        
        assert block.type == BlockType.LIST
        assert block.to_markdown() == "1. First\n2. Second\n3. Third"
    
    def test_code_block(self):
        """Test code block."""
        code = "def hello():\n    print('Hello')"
        block = CodeBlock(text=code, language="python")
        
        assert block.type == BlockType.CODE
        assert block.to_markdown() == f"```python\n{code}\n```"
        assert block.to_plain_text() == code
    
    def test_code_block_no_language(self):
        """Test code block without language."""
        code = "some code"
        block = CodeBlock(text=code)
        
        assert block.to_markdown() == f"```\n{code}\n```"
    
    def test_table_block(self):
        """Test table block with TSV."""
        tsv = "Name\tAge\tCity\nAlice\t30\tParis\nBob\t25\tLondon"
        block = TableBlock(raw_tsv=tsv, caption="User Data")
        
        assert block.type == BlockType.TABLE
        assert "User Data" in block.to_plain_text()
        assert tsv in block.to_plain_text()
    
    def test_table_block_markdown_preview(self):
        """Test table Markdown preview generation."""
        tsv = "Name\tAge\nAlice\t30\nBob\t25"
        block = TableBlock(raw_tsv=tsv)
        
        preview = block.generate_markdown_preview()
        
        assert "| Name | Age |" in preview
        assert "| --- | --- |" in preview
        assert "| Alice | 30 |" in preview
        assert "| Bob | 25 |" in preview
    
    def test_message_block(self):
        """Test message block."""
        block = MessageBlock(
            author="Alice",
            timestamp="2024-01-15T10:30:00Z",
            text="Hello, world!",
            thread_id="thread-123",
            attachments=["file.pdf"]
        )
        
        assert block.type == BlockType.MESSAGE
        assert "Alice" in block.to_markdown()
        assert "2024-01-15T10:30:00Z" in block.to_markdown()
        assert "Hello, world!" in block.to_markdown()
        assert "file.pdf" in block.to_markdown()


class TestStructuredDocument:
    """Test StructuredDocument class."""
    
    def test_create_empty_document(self):
        """Test creating an empty document."""
        metadata = DocumentMetadata(source="web", url="https://example.com")
        doc = StructuredDocument(metadata=metadata)
        
        assert doc.metadata.source == "web"
        assert doc.metadata.url == "https://example.com"
        assert len(doc.blocks) == 0
        assert doc.stats.block_count == 0
    
    def test_create_document_with_blocks(self):
        """Test creating a document with blocks."""
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Title"),
            ParagraphBlock(text="This is a paragraph."),
            ListBlock(items=["Item 1", "Item 2"], ordered=False),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        assert len(doc.blocks) == 3
        assert doc.stats.block_count == 3
        assert doc.stats.char_count > 0
    
    def test_add_block(self):
        """Test adding blocks to document."""
        metadata = DocumentMetadata(source="web")
        doc = StructuredDocument(metadata=metadata)
        
        doc.add_block(HeadingBlock(level=1, text="Title"))
        assert len(doc.blocks) == 1
        
        doc.add_block(ParagraphBlock(text="Content"))
        assert len(doc.blocks) == 2
        assert doc.stats.block_count == 2
    
    def test_to_markdown(self):
        """Test Markdown conversion."""
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Title"),
            ParagraphBlock(text="Introduction text."),
            ListBlock(items=["Point 1", "Point 2"], ordered=False),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        markdown = doc.to_markdown()
        
        assert "# Title" in markdown
        assert "Introduction text." in markdown
        assert "- Point 1" in markdown
        assert "- Point 2" in markdown
    
    def test_to_plain_text(self):
        """Test plain text conversion."""
        metadata = DocumentMetadata(source="web")
        blocks = [
            HeadingBlock(level=1, text="Title"),
            ParagraphBlock(text="Content here."),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        text = doc.to_plain_text()
        
        assert "Title" in text
        assert "Content here." in text
    
    def test_to_json(self):
        """Test JSON serialization."""
        metadata = DocumentMetadata(source="web", url="https://example.com")
        blocks = [
            HeadingBlock(level=1, text="Title"),
            ParagraphBlock(text="Content"),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        json_str = doc.to_json()
        data = json.loads(json_str)
        
        assert data["metadata"]["source"] == "web"
        assert data["metadata"]["url"] == "https://example.com"
        assert len(data["blocks"]) == 2
        assert data["stats"]["block_count"] == 2
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "metadata": {
                "source": "web",
                "url": "https://example.com",
                "app_name": None,
                "window_title": None,
                "file_path": None,
                "mime_type": None,
                "extracted_at": "2024-01-15T10:00:00",
                "language": "en",
            },
            "blocks": [
                {"type": "heading", "level": 1, "text": "Title"},
                {"type": "paragraph", "text": "Content"},
            ],
            "stats": {"char_count": 100, "token_estimate": 25, "block_count": 2}
        }
        
        doc = StructuredDocument.from_dict(data)
        
        assert doc.metadata.source == "web"
        assert doc.metadata.url == "https://example.com"
        assert len(doc.blocks) == 2
        assert isinstance(doc.blocks[0], HeadingBlock)
        assert isinstance(doc.blocks[1], ParagraphBlock)
    
    def test_from_json(self):
        """Test deserialization from JSON."""
        json_str = """
        {
            "metadata": {
                "source": "web",
                "url": "https://example.com",
                "app_name": null,
                "window_title": null,
                "file_path": null,
                "mime_type": null,
                "extracted_at": "2024-01-15T10:00:00",
                "language": null
            },
            "blocks": [
                {"type": "heading", "level": 1, "text": "Title"}
            ],
            "stats": {"char_count": 5, "token_estimate": 1, "block_count": 1}
        }
        """
        
        doc = StructuredDocument.from_json(json_str)
        
        assert doc.metadata.source == "web"
        assert len(doc.blocks) == 1
    
    def test_stats_computation(self):
        """Test statistics computation."""
        metadata = DocumentMetadata(source="web")
        blocks = [
            ParagraphBlock(text="A" * 100),
            ParagraphBlock(text="B" * 200),
        ]
        doc = StructuredDocument(metadata=metadata, blocks=blocks)
        
        # Should have counted characters
        assert doc.stats.char_count >= 300
        # Should have estimated tokens (rough: chars / 4)
        assert doc.stats.token_estimate > 0
        assert doc.stats.block_count == 2


class TestDocumentMetadata:
    """Test DocumentMetadata class."""
    
    def test_create_metadata(self):
        """Test metadata creation."""
        metadata = DocumentMetadata(
            source="web",
            url="https://example.com",
            language="en"
        )
        
        assert metadata.source == "web"
        assert metadata.url == "https://example.com"
        assert metadata.language == "en"
        assert metadata.extracted_at is not None
    
    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = DocumentMetadata(
            source="pdf",
            file_path="/path/to/file.pdf",
            mime_type="application/pdf"
        )
        
        data = metadata.to_dict()
        
        assert data["source"] == "pdf"
        assert data["file_path"] == "/path/to/file.pdf"
        assert data["mime_type"] == "application/pdf"
