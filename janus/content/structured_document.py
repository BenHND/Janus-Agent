"""
StructuredDocument - Unified document representation for content extraction.

Provides a pivot format for the Extract→Process→Output pipeline that preserves
structure (headings, lists, tables, code) while being LLM-friendly.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Types of content blocks in a structured document."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE = "code"
    TABLE = "table"
    MESSAGE = "message"


@dataclass
class DocumentBlock:
    """Base class for document content blocks."""
    type: BlockType = field(init=False)
    
    def to_markdown(self) -> str:
        """Convert block to Markdown format."""
        raise NotImplementedError("Subclasses must implement to_markdown")
    
    def to_plain_text(self) -> str:
        """Convert block to plain text."""
        raise NotImplementedError("Subclasses must implement to_plain_text")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        data = asdict(self)
        # Convert BlockType enum to string for JSON serialization
        if 'type' in data and isinstance(data['type'], BlockType):
            data['type'] = data['type'].value
        return data


@dataclass
class HeadingBlock(DocumentBlock):
    """Heading block with level (1-6) and text."""
    level: int  # 1-6
    text: str
    
    def __post_init__(self):
        self.type = BlockType.HEADING
        if not 1 <= self.level <= 6:
            raise ValueError(f"Heading level must be 1-6, got {self.level}")
    
    def to_markdown(self) -> str:
        return f"{'#' * self.level} {self.text}"
    
    def to_plain_text(self) -> str:
        return self.text


@dataclass
class ParagraphBlock(DocumentBlock):
    """Paragraph block with plain text."""
    text: str
    
    def __post_init__(self):
        self.type = BlockType.PARAGRAPH
    
    def to_markdown(self) -> str:
        return self.text
    
    def to_plain_text(self) -> str:
        return self.text


@dataclass
class ListBlock(DocumentBlock):
    """List block with items."""
    items: List[str]
    ordered: bool = False
    
    def __post_init__(self):
        self.type = BlockType.LIST
    
    def to_markdown(self) -> str:
        lines = []
        for i, item in enumerate(self.items, 1):
            prefix = f"{i}. " if self.ordered else "- "
            lines.append(f"{prefix}{item}")
        return "\n".join(lines)
    
    def to_plain_text(self) -> str:
        return "\n".join(self.items)


@dataclass
class CodeBlock(DocumentBlock):
    """Code block with optional language and text."""
    text: str
    language: Optional[str] = None
    
    def __post_init__(self):
        self.type = BlockType.CODE
    
    def to_markdown(self) -> str:
        lang = self.language or ""
        return f"```{lang}\n{self.text}\n```"
    
    def to_plain_text(self) -> str:
        return self.text


@dataclass
class TableBlock(DocumentBlock):
    """
    Table block with lossless TSV representation and optional preview.
    
    Tables are stored in TSV format (tab-separated values) to preserve
    structure without loss. A Markdown preview can be generated for display.
    """
    raw_tsv: str
    caption: Optional[str] = None
    markdown_preview: Optional[str] = None
    
    def __post_init__(self):
        self.type = BlockType.TABLE
    
    def to_markdown(self) -> str:
        """Return Markdown table if available, otherwise TSV in code block."""
        if self.markdown_preview:
            result = self.markdown_preview
            if self.caption:
                result = f"*{self.caption}*\n\n{result}"
            return result
        
        # Fallback: TSV in code block
        result = f"```tsv\n{self.raw_tsv}\n```"
        if self.caption:
            result = f"*{self.caption}*\n\n{result}"
        return result
    
    def to_plain_text(self) -> str:
        """Return TSV representation."""
        if self.caption:
            return f"{self.caption}\n{self.raw_tsv}"
        return self.raw_tsv
    
    def generate_markdown_preview(self) -> str:
        """
        Generate a Markdown table from TSV data.
        
        Returns:
            Markdown table string
        """
        lines = self.raw_tsv.strip().split('\n')
        if not lines:
            return ""
        
        # Parse TSV
        rows = [line.split('\t') for line in lines]
        if not rows:
            return ""
        
        # Build Markdown table
        md_lines = []
        
        # Header
        md_lines.append('| ' + ' | '.join(rows[0]) + ' |')
        md_lines.append('| ' + ' | '.join(['---'] * len(rows[0])) + ' |')
        
        # Data rows
        for row in rows[1:]:
            # Pad row if needed
            padded_row = row + [''] * (len(rows[0]) - len(row))
            md_lines.append('| ' + ' | '.join(padded_row[:len(rows[0])]) + ' |')
        
        self.markdown_preview = '\n'.join(md_lines)
        return self.markdown_preview


@dataclass
class MessageBlock(DocumentBlock):
    """
    Message block for conversation threads.
    
    Preserves message metadata (author, timestamp, thread) for proper
    conversation reconstruction.
    """
    author: str
    timestamp: str  # ISO format
    text: str
    thread_id: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.type = BlockType.MESSAGE
    
    def to_markdown(self) -> str:
        """Format as Markdown with metadata."""
        lines = [f"**{self.author}** ({self.timestamp})"]
        if self.thread_id:
            lines.append(f"*Thread: {self.thread_id}*")
        lines.append("")
        lines.append(self.text)
        if self.attachments:
            lines.append("")
            lines.append("Attachments:")
            for att in self.attachments:
                lines.append(f"- {att}")
        return "\n".join(lines)
    
    def to_plain_text(self) -> str:
        """Format as plain text."""
        parts = [f"{self.author} ({self.timestamp}): {self.text}"]
        if self.attachments:
            parts.append(f"Attachments: {', '.join(self.attachments)}")
        return "\n".join(parts)


@dataclass
class DocumentMetadata:
    """Metadata for a structured document."""
    source: str  # "web", "app", "pdf", "conversation", "clipboard"
    url: Optional[str] = None
    app_name: Optional[str] = None
    window_title: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    extracted_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    language: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DocumentStats:
    """Statistics about a structured document."""
    char_count: int = 0
    token_estimate: int = 0
    block_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class StructuredDocument:
    """
    Unified structured document representation.
    
    Provides a pivot format for the Extract→Process→Output pipeline.
    Supports conversion to Markdown, plain text, and JSON.
    
    Attributes:
        metadata: Document metadata (source, URL, timestamps, etc.)
        blocks: List of typed content blocks
        raw_text: Optional raw text (for debug/fallback)
        stats: Document statistics (char count, token estimate, block count)
    """
    
    def __init__(
        self,
        metadata: DocumentMetadata,
        blocks: Optional[List[DocumentBlock]] = None,
        raw_text: Optional[str] = None
    ):
        """
        Initialize a structured document.
        
        Args:
            metadata: Document metadata
            blocks: List of content blocks
            raw_text: Optional raw text (for debug/fallback)
        """
        self.metadata = metadata
        self.blocks = blocks or []
        self.raw_text = raw_text
        self.stats = self._compute_stats()
    
    def _compute_stats(self) -> DocumentStats:
        """Compute document statistics."""
        # Count characters across all blocks
        text_parts = [block.to_plain_text() for block in self.blocks]
        all_text = "\n\n".join(text_parts)
        char_count = len(all_text)
        
        # Estimate tokens (rough approximation: chars / 4)
        # This is overridden if using token counter
        token_estimate = char_count // 4
        
        return DocumentStats(
            char_count=char_count,
            token_estimate=token_estimate,
            block_count=len(self.blocks)
        )
    
    def update_token_estimate(self, token_counter=None):
        """
        Update token estimate using a token counter.
        
        Args:
            token_counter: TokenCounter instance (from janus.utils.token_counter)
        """
        if token_counter is None:
            # Try to import and create default counter
            try:
                from janus.utils.token_counter import TokenCounter
                token_counter = TokenCounter()
            except ImportError:
                logger.warning("TokenCounter not available, using fallback estimation")
                return
        
        text = self.to_plain_text()
        self.stats.token_estimate = token_counter.count_tokens(text)
    
    def add_block(self, block: DocumentBlock):
        """Add a content block and update stats."""
        self.blocks.append(block)
        self.stats = self._compute_stats()
    
    def to_markdown(self) -> str:
        """
        Convert document to Markdown format.
        
        Returns:
            Markdown string suitable for LLM input
        """
        parts = []
        
        # Add metadata header (commented out, but available if needed)
        # parts.append(f"<!-- Source: {self.metadata.source} -->")
        # if self.metadata.url:
        #     parts.append(f"<!-- URL: {self.metadata.url} -->")
        # parts.append("")
        
        # Convert blocks to Markdown
        for block in self.blocks:
            parts.append(block.to_markdown())
            parts.append("")  # Blank line between blocks
        
        return "\n".join(parts).strip()
    
    def to_plain_text(self) -> str:
        """
        Convert document to plain text format.
        
        Returns:
            Plain text string
        """
        parts = [block.to_plain_text() for block in self.blocks]
        return "\n\n".join(parts)
    
    def to_json(self) -> str:
        """
        Convert document to JSON format (for logging/debugging).
        
        Returns:
            JSON string
        """
        data = {
            "metadata": self.metadata.to_dict(),
            "blocks": [block.to_dict() for block in self.blocks],
            "stats": self.stats.to_dict(),
        }
        if self.raw_text:
            data["raw_text"] = self.raw_text
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert document to dictionary.
        
        Returns:
            Dictionary representation
        """
        data = {
            "metadata": self.metadata.to_dict(),
            "blocks": [block.to_dict() for block in self.blocks],
            "stats": self.stats.to_dict(),
        }
        if self.raw_text:
            data["raw_text"] = self.raw_text
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredDocument":
        """
        Create StructuredDocument from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            StructuredDocument instance
        """
        metadata = DocumentMetadata(**data["metadata"])
        
        # Reconstruct blocks
        blocks = []
        for block_data in data.get("blocks", []):
            block_type = BlockType(block_data["type"])
            block_data_copy = block_data.copy()
            del block_data_copy["type"]
            
            if block_type == BlockType.HEADING:
                blocks.append(HeadingBlock(**block_data_copy))
            elif block_type == BlockType.PARAGRAPH:
                blocks.append(ParagraphBlock(**block_data_copy))
            elif block_type == BlockType.LIST:
                blocks.append(ListBlock(**block_data_copy))
            elif block_type == BlockType.CODE:
                blocks.append(CodeBlock(**block_data_copy))
            elif block_type == BlockType.TABLE:
                blocks.append(TableBlock(**block_data_copy))
            elif block_type == BlockType.MESSAGE:
                blocks.append(MessageBlock(**block_data_copy))
        
        raw_text = data.get("raw_text")
        
        return cls(metadata=metadata, blocks=blocks, raw_text=raw_text)
    
    @classmethod
    def from_json(cls, json_str: str) -> "StructuredDocument":
        """
        Create StructuredDocument from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            StructuredDocument instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
