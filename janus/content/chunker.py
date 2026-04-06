"""
Structured Chunker - Structure-aware document segmentation.

Implements token-aware chunking that respects document structure:
1. Split by sections/headings
2. Split by blocks
3. Split by token budget

This ensures chunks are semantically coherent and fit within LLM context windows.
"""

import logging
import re
from typing import List, Optional

from .structured_document import (
    StructuredDocument,
    DocumentBlock,
    DocumentMetadata,
    HeadingBlock,
    BlockType,
)

logger = logging.getLogger(__name__)


class StructuredChunker:
    """
    Structure-aware document chunker.
    
    Splits documents into chunks that respect structure boundaries
    and fit within token budgets for LLM processing.
    """
    
    def __init__(self, max_tokens: int = 4000, overlap_tokens: int = 200):
        """
        Initialize chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = None
        
        # Try to load token counter
        try:
            from janus.utils.token_counter import TokenCounter
            self.token_counter = TokenCounter()
            logger.debug("StructuredChunker using TokenCounter for precise token counting")
        except ImportError:
            logger.warning("TokenCounter not available, using character-based estimation")
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to count
            
        Returns:
            Estimated token count
        """
        if self.token_counter:
            return self.token_counter.count_tokens(text)
        else:
            # Fallback: rough approximation (4 chars per token)
            return len(text) // 4
    
    def chunk(self, document: StructuredDocument) -> List[StructuredDocument]:
        """
        Chunk document into smaller documents.
        
        Respects structure boundaries and token limits.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of document chunks
        """
        # If document is small enough, return as-is
        total_tokens = self._estimate_tokens(document.to_plain_text())
        if total_tokens <= self.max_tokens:
            return [document]
        
        # Split by sections first
        sections = self._split_by_sections(document)
        
        # Now chunk each section if needed
        chunks = []
        for section in sections:
            section_tokens = self._estimate_tokens(section.to_plain_text())
            
            if section_tokens <= self.max_tokens:
                chunks.append(section)
            else:
                # Section too large, split by blocks
                block_chunks = self._chunk_blocks(section)
                chunks.extend(block_chunks)
        
        logger.info(f"Chunked document into {len(chunks)} chunks (max_tokens={self.max_tokens})")
        return chunks
    
    def _split_by_sections(self, document: StructuredDocument) -> List[StructuredDocument]:
        """
        Split document by heading sections.
        
        Args:
            document: Document to split
            
        Returns:
            List of section documents
        """
        sections = []
        current_section_blocks = []
        current_heading = None
        
        for block in document.blocks:
            if isinstance(block, HeadingBlock):
                # Save previous section
                if current_section_blocks:
                    section_doc = StructuredDocument(
                        metadata=document.metadata,
                        blocks=current_section_blocks
                    )
                    sections.append(section_doc)
                
                # Start new section
                current_section_blocks = [block]
                current_heading = block
            else:
                current_section_blocks.append(block)
        
        # Save last section
        if current_section_blocks:
            section_doc = StructuredDocument(
                metadata=document.metadata,
                blocks=current_section_blocks
            )
            sections.append(section_doc)
        
        # If no sections found, return original document
        if not sections:
            return [document]
        
        return sections
    
    def _chunk_blocks(self, document: StructuredDocument) -> List[StructuredDocument]:
        """
        Chunk document by blocks when section is too large.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of chunked documents
        """
        chunks = []
        current_chunk_blocks = []
        current_tokens = 0
        
        for block in document.blocks:
            block_text = block.to_plain_text()
            block_tokens = self._estimate_tokens(block_text)
            
            # If single block exceeds limit, split it
            if block_tokens > self.max_tokens:
                # Save current chunk
                if current_chunk_blocks:
                    chunks.append(StructuredDocument(
                        metadata=document.metadata,
                        blocks=current_chunk_blocks
                    ))
                    current_chunk_blocks = []
                    current_tokens = 0
                
                # Split large block
                split_chunks = self._split_large_block(block, document.metadata)
                chunks.extend(split_chunks)
                continue
            
            # Check if adding block would exceed limit
            if current_tokens + block_tokens > self.max_tokens and current_chunk_blocks:
                # Save current chunk
                chunks.append(StructuredDocument(
                    metadata=document.metadata,
                    blocks=current_chunk_blocks
                ))
                current_chunk_blocks = []
                current_tokens = 0
            
            # Add block to current chunk
            current_chunk_blocks.append(block)
            current_tokens += block_tokens
        
        # Save final chunk
        if current_chunk_blocks:
            chunks.append(StructuredDocument(
                metadata=document.metadata,
                blocks=current_chunk_blocks
            ))
        
        return chunks if chunks else [document]
    
    def _split_large_block(
        self,
        block: DocumentBlock,
        metadata: DocumentMetadata
    ) -> List[StructuredDocument]:
        """
        Split a single large block into multiple chunks.
        
        Args:
            block: Block to split
            metadata: Document metadata
            
        Returns:
            List of single-block documents
        """
        from .structured_document import ParagraphBlock
        
        text = block.to_plain_text()
        chunks = []
        
        # Split by sentences with more robust pattern
        # Handle common cases: ". ", "! ", "? ", but avoid splitting on abbreviations
        # Simple sentence boundary detection (can be improved with nltk)
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        sentences = re.split(sentence_pattern, text)
        
        current_text = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.max_tokens and current_text:
                # Save chunk
                chunk_text = ' '.join(current_text)
                chunks.append(StructuredDocument(
                    metadata=metadata,
                    blocks=[ParagraphBlock(text=chunk_text)]
                ))
                current_text = []
                current_tokens = 0
            
            current_text.append(sentence.strip())
            current_tokens += sentence_tokens
        
        # Save final chunk
        if current_text:
            chunk_text = ' '.join(current_text)
            chunks.append(StructuredDocument(
                metadata=metadata,
                blocks=[ParagraphBlock(text=chunk_text)]
            ))
        
        return chunks if chunks else [StructuredDocument(
            metadata=metadata,
            blocks=[block]
        )]
    
    def chunk_with_overlap(self, document: StructuredDocument) -> List[StructuredDocument]:
        """
        Chunk document with overlapping content between chunks.
        
        Useful for maintaining context across chunks in retrieval scenarios.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of overlapping chunks
        """
        # Get base chunks
        base_chunks = self.chunk(document)
        
        if len(base_chunks) <= 1:
            return base_chunks
        
        # Add overlap between chunks
        overlapped_chunks = []
        
        for i, chunk in enumerate(base_chunks):
            # Add some blocks from previous chunk
            if i > 0 and self.overlap_tokens > 0:
                prev_chunk = base_chunks[i - 1]
                overlap_blocks = self._get_overlap_blocks(
                    prev_chunk.blocks,
                    self.overlap_tokens
                )
                
                # Prepend overlap blocks
                chunk.blocks = overlap_blocks + chunk.blocks
            
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def _get_overlap_blocks(
        self,
        blocks: List[DocumentBlock],
        max_tokens: int
    ) -> List[DocumentBlock]:
        """
        Get blocks from end that fit within token budget.
        
        Args:
            blocks: Blocks to take from
            max_tokens: Maximum tokens for overlap
            
        Returns:
            List of blocks for overlap
        """
        overlap_blocks = []
        current_tokens = 0
        
        # Take blocks from end
        for block in reversed(blocks):
            block_tokens = self._estimate_tokens(block.to_plain_text())
            
            if current_tokens + block_tokens > max_tokens:
                break
            
            overlap_blocks.insert(0, block)
            current_tokens += block_tokens
        
        return overlap_blocks
