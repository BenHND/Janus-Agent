"""
Content extraction and processing module.

This module provides structured content extraction from various sources
(web, apps, PDFs, conversations) with a unified pipeline:
Extract → Normalize → Chunk → Output

Key components:
- StructuredDocument: Unified document representation
- Extraction router: Select best strategy by source type
- Normalizer: Apply universal cleaning rules
- Chunker: Structure-aware segmentation
"""

from .structured_document import (
    StructuredDocument,
    BlockType,
    DocumentBlock,
    HeadingBlock,
    ParagraphBlock,
    ListBlock,
    CodeBlock,
    TableBlock,
    MessageBlock,
    DocumentMetadata,
)
from .extractor import ContentExtractor
from .normalizer import ContentNormalizer
from .chunker import StructuredChunker

__all__ = [
    "StructuredDocument",
    "BlockType",
    "DocumentBlock",
    "HeadingBlock",
    "ParagraphBlock",
    "ListBlock",
    "CodeBlock",
    "TableBlock",
    "MessageBlock",
    "DocumentMetadata",
    "ContentExtractor",
    "ContentNormalizer",
    "StructuredChunker",
]
