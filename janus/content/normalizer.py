"""
Content Normalizer - Universal cleaning and deduplication rules.

Applies consistent rules across all content types:
- Table preservation (TSV + Markdown preview)
- Code block boundaries preservation
- Link preservation
- Deduplication (repeated menus, footers, messages)
- Language detection
"""

import logging
import re
from typing import List, Set
from collections import Counter

from .structured_document import (
    StructuredDocument,
    DocumentBlock,
    ParagraphBlock,
    TableBlock,
    MessageBlock,
)

logger = logging.getLogger(__name__)


class ContentNormalizer:
    """
    Normalizer for structured documents.
    
    Applies universal cleaning rules to ensure consistent,
    high-quality content regardless of source.
    """
    
    def __init__(self, dedup_threshold: float = 0.8):
        """
        Initialize normalizer.
        
        Args:
            dedup_threshold: Similarity threshold for deduplication (0.0-1.0)
        """
        self.dedup_threshold = dedup_threshold
    
    def normalize(self, document: StructuredDocument) -> StructuredDocument:
        """
        Normalize a structured document.
        
        Args:
            document: Document to normalize
            
        Returns:
            Normalized document
        """
        # Apply normalization steps
        document = self._deduplicate_blocks(document)
        document = self._normalize_tables(document)
        document = self._detect_language(document)
        
        # Recompute stats
        document.stats = document._compute_stats()
        
        return document
    
    def _deduplicate_blocks(self, document: StructuredDocument) -> StructuredDocument:
        """
        Remove duplicate blocks (e.g., repeated menus, footers).
        
        Args:
            document: Document to deduplicate
            
        Returns:
            Document with duplicates removed
        """
        if not document.blocks:
            return document
        
        # Track seen content
        seen_texts: Set[str] = set()
        unique_blocks: List[DocumentBlock] = []
        
        # Special handling for message blocks (don't deduplicate)
        for block in document.blocks:
            if isinstance(block, MessageBlock):
                unique_blocks.append(block)
                continue
            
            # Get normalized text
            text = block.to_plain_text().strip()
            if not text:
                continue
            
            # Get normalized text (more explicit whitespace handling)
            normalized = re.sub(r'\s+', ' ', text.strip())
            
            # Check if we've seen similar content
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_blocks.append(block)
            else:
                logger.debug(f"Removed duplicate block: {text[:50]}...")
        
        document.blocks = unique_blocks
        return document
    
    def _normalize_tables(self, document: StructuredDocument) -> StructuredDocument:
        """
        Ensure all tables have Markdown previews.
        
        Args:
            document: Document with tables
            
        Returns:
            Document with normalized tables
        """
        for block in document.blocks:
            if isinstance(block, TableBlock) and not block.markdown_preview:
                try:
                    block.generate_markdown_preview()
                except Exception as e:
                    logger.warning(f"Failed to generate table preview: {e}")
        
        return document
    
    def _detect_language(self, document: StructuredDocument) -> StructuredDocument:
        """
        Detect document language for better processing.
        
        Uses simple heuristics based on common words.
        
        Args:
            document: Document to analyze
            
        Returns:
            Document with language metadata
        """
        # Get full text
        text = document.to_plain_text()
        if not text or len(text) < 100:
            return document
        
        # Simple language detection based on common words
        # This is a basic heuristic - could be replaced with langdetect library
        
        # Normalize and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return document
        
        # Common word indicators
        en_indicators = {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'that', 'for', 'it', 'with'}
        fr_indicators = {'le', 'la', 'de', 'et', 'les', 'des', 'un', 'une', 'dans', 'pour', 'que'}
        es_indicators = {'el', 'la', 'de', 'y', 'los', 'las', 'un', 'una', 'en', 'para', 'que'}
        
        # Count indicators
        word_set = set(words[:500])  # Check first 500 words
        en_score = len(word_set & en_indicators)
        fr_score = len(word_set & fr_indicators)
        es_score = len(word_set & es_indicators)
        
        # Determine language
        scores = {'en': en_score, 'fr': fr_score, 'es': es_score}
        if max(scores.values()) >= 3:
            detected_lang = max(scores, key=scores.get)
            document.metadata.language = detected_lang
            logger.debug(f"Detected language: {detected_lang} (scores: {scores})")
        
        return document
    
    def remove_navigation_patterns(self, document: StructuredDocument) -> StructuredDocument:
        """
        Remove common navigation patterns from web content.
        
        Args:
            document: Document to clean
            
        Returns:
            Cleaned document
        """
        # Patterns that indicate navigation/UI elements
        nav_patterns = [
            r'^menu$',
            r'^navigation$',
            r'^skip to',
            r'^search$',
            r'^home\s*\|\s*about',
            r'cookie.*policy',
            r'privacy.*policy',
            r'terms.*service',
        ]
        
        cleaned_blocks = []
        for block in document.blocks:
            text = block.to_plain_text().lower().strip()
            
            # Check if block matches navigation pattern
            is_nav = False
            for pattern in nav_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    is_nav = True
                    break
            
            # Keep block if it's not navigation
            if not is_nav or isinstance(block, MessageBlock):
                cleaned_blocks.append(block)
            else:
                logger.debug(f"Removed navigation block: {text[:50]}...")
        
        document.blocks = cleaned_blocks
        return document
