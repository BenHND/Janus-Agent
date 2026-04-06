"""
Content Extractor - Router for selecting extraction strategies.

Routes extraction to the best strategy based on source type and capabilities:
- Web: static (trafilatura) or rendered (Playwright fallback)
- PDF: text-first or OCR fallback
- Apps: accessibility snapshot or clipboard fallback
- Conversations: preserve thread/message structure
"""

import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .structured_document import (
    StructuredDocument,
    DocumentMetadata,
    HeadingBlock,
    ParagraphBlock,
    ListBlock,
    CodeBlock,
    TableBlock,
    MessageBlock,
)

logger = logging.getLogger(__name__)

# Try to import trafilatura
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("trafilatura not available - web extraction will use basic fallback")


class ContentExtractor:
    """
    Router for content extraction strategies.
    
    Selects the best extraction method based on source type and capabilities,
    then produces a StructuredDocument with typed blocks.
    """
    
    def __init__(self, system_bridge=None):
        """
        Initialize content extractor.
        
        Args:
            system_bridge: Optional SystemBridge for platform operations
        """
        self.system_bridge = system_bridge
    
    def extract_from_web(
        self,
        html: Optional[str] = None,
        url: Optional[str] = None,
        use_trafilatura: bool = True
    ) -> StructuredDocument:
        """
        Extract structured content from web page.
        
        Args:
            html: HTML content (if available)
            url: Page URL
            use_trafilatura: Whether to use trafilatura for parsing
            
        Returns:
            StructuredDocument with extracted content
        """
        metadata = DocumentMetadata(
            source="web",
            url=url
        )
        
        blocks = []
        raw_text = None
        
        # Try trafilatura first if available and enabled
        if TRAFILATURA_AVAILABLE and use_trafilatura and html:
            try:
                extracted = trafilatura.extract(
                    html,
                    url=url,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                    output_format='json',
                    with_metadata=True
                )
                
                if extracted:
                    import json
                    data = json.loads(extracted) if isinstance(extracted, str) else extracted
                    
                    # Extract title as heading
                    if data.get('title'):
                        blocks.append(HeadingBlock(level=1, text=data['title']))
                    
                    # Extract main text as paragraphs
                    if data.get('text'):
                        # Split into paragraphs
                        paragraphs = data['text'].split('\n\n')
                        for para in paragraphs:
                            para = para.strip()
                            if para:
                                blocks.append(ParagraphBlock(text=para))
                    
                    raw_text = data.get('raw_text') or data.get('text')
                    
                    logger.info(f"Extracted {len(blocks)} blocks using trafilatura")
                    
            except Exception as e:
                logger.warning(f"Trafilatura extraction failed: {e}, using fallback")
        
        # Fallback: basic HTML parsing if no blocks extracted
        if not blocks and html:
            # Simple fallback: extract text from HTML
            try:
                from html.parser import HTMLParser
                
                class SimpleHTMLParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                    
                    def handle_data(self, data):
                        text = data.strip()
                        if text:
                            self.text_parts.append(text)
                
                parser = SimpleHTMLParser()
                parser.feed(html)
                
                # Combine text parts into paragraphs
                if parser.text_parts:
                    # Group consecutive short parts into paragraphs
                    current_para = []
                    for part in parser.text_parts:
                        if len(part) > 100:  # Long part = new paragraph
                            if current_para:
                                blocks.append(ParagraphBlock(text=' '.join(current_para)))
                                current_para = []
                            blocks.append(ParagraphBlock(text=part))
                        else:
                            current_para.append(part)
                    
                    if current_para:
                        blocks.append(ParagraphBlock(text=' '.join(current_para)))
                    
                    raw_text = '\n\n'.join(parser.text_parts)
                    logger.info(f"Extracted {len(blocks)} blocks using fallback HTML parser")
                    
            except Exception as e:
                logger.warning(f"Fallback HTML parsing failed: {e}")
        
        # Last resort: raw text as single paragraph
        if not blocks and raw_text:
            blocks.append(ParagraphBlock(text=raw_text))
        
        return StructuredDocument(metadata=metadata, blocks=blocks, raw_text=raw_text)
    
    def extract_from_plain_text(
        self,
        text: str,
        source: str = "clipboard",
        **metadata_kwargs
    ) -> StructuredDocument:
        """
        Extract structured content from plain text.
        
        Attempts to detect structure (headings, lists, code blocks) in plain text.
        
        Args:
            text: Plain text content
            source: Source type ("clipboard", "app", etc.)
            **metadata_kwargs: Additional metadata fields
            
        Returns:
            StructuredDocument with extracted content
        """
        metadata = DocumentMetadata(source=source, **metadata_kwargs)
        blocks = []
        
        # Split into lines for analysis
        lines = text.split('\n')
        current_para = []
        in_code_block = False
        code_lines = []
        code_language = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Detect code fence
            if stripped.startswith('```'):
                if in_code_block:
                    # End code block
                    if code_lines:
                        blocks.append(CodeBlock(
                            text='\n'.join(code_lines),
                            language=code_language
                        ))
                    code_lines = []
                    code_language = None
                    in_code_block = False
                else:
                    # Start code block
                    if current_para:
                        blocks.append(ParagraphBlock(text='\n'.join(current_para)))
                        current_para = []
                    in_code_block = True
                    code_language = stripped[3:].strip() or None
                i += 1
                continue
            
            # If in code block, accumulate code lines
            if in_code_block:
                code_lines.append(line)
                i += 1
                continue
            
            # Detect headings (markdown-style)
            if stripped.startswith('#'):
                # Save current paragraph
                if current_para:
                    blocks.append(ParagraphBlock(text='\n'.join(current_para)))
                    current_para = []
                
                # Parse heading
                level = 0
                for char in stripped:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                heading_text = stripped[level:].strip()
                if heading_text:
                    blocks.append(HeadingBlock(level=min(level, 6), text=heading_text))
                i += 1
                continue
            
            # Detect list items
            if stripped.startswith(('-', '*', '+')) or (stripped and stripped[0].isdigit() and '. ' in stripped[:4]):
                # Save current paragraph
                if current_para:
                    blocks.append(ParagraphBlock(text='\n'.join(current_para)))
                    current_para = []
                
                # Collect consecutive list items
                list_items = []
                ordered = stripped[0].isdigit()
                
                while i < len(lines):
                    item_line = lines[i].strip()
                    if not item_line:
                        i += 1
                        break
                    
                    # Check if it's a list item
                    is_item = False
                    item_text = ""
                    
                    if item_line.startswith(('-', '*', '+')):
                        is_item = True
                        item_text = item_line[1:].strip()
                    elif item_line and item_line[0].isdigit() and '. ' in item_line[:4]:
                        is_item = True
                        item_text = item_line.split('. ', 1)[1] if '. ' in item_line else item_line
                    
                    if is_item:
                        list_items.append(item_text)
                        i += 1
                    else:
                        break
                
                if list_items:
                    blocks.append(ListBlock(items=list_items, ordered=ordered))
                continue
            
            # Regular line - accumulate into paragraph
            if stripped:
                current_para.append(line)
            elif current_para:
                # Empty line - end paragraph
                blocks.append(ParagraphBlock(text='\n'.join(current_para)))
                current_para = []
            
            i += 1
        
        # Save any remaining paragraph
        if current_para:
            blocks.append(ParagraphBlock(text='\n'.join(current_para)))
        
        # Save any remaining code block
        if in_code_block and code_lines:
            blocks.append(CodeBlock(text='\n'.join(code_lines), language=code_language))
        
        return StructuredDocument(metadata=metadata, blocks=blocks, raw_text=text)
    
    def extract_from_conversation(
        self,
        messages: list,
        platform: str = "slack",
        channel: Optional[str] = None
    ) -> StructuredDocument:
        """
        Extract structured content from conversation messages.
        
        Preserves thread structure and message metadata.
        
        Args:
            messages: List of message dicts with keys: author, timestamp, text, thread_id, attachments
            platform: Platform name (slack, teams, discord, etc.)
            channel: Optional channel/thread identifier
            
        Returns:
            StructuredDocument with message blocks
        """
        metadata = DocumentMetadata(
            source="conversation",
            app_name=platform,
            window_title=channel
        )
        
        blocks = []
        
        for msg in messages:
            blocks.append(MessageBlock(
                author=msg.get('author', 'Unknown'),
                timestamp=msg.get('timestamp', ''),
                text=msg.get('text', ''),
                thread_id=msg.get('thread_id'),
                attachments=msg.get('attachments', [])
            ))
        
        return StructuredDocument(metadata=metadata, blocks=blocks)
    
    def should_use_rendered_extraction(self, html: str, url: str) -> bool:
        """
        Determine if rendered extraction (Playwright) should be used.
        
        Triggers rendered extraction if:
        - Content is too short (likely SPA with minimal static HTML)
        - Text density is too low (lots of scripts, little content)
        - Known SPA patterns detected
        
        Args:
            html: HTML content
            url: Page URL
            
        Returns:
            True if rendered extraction should be used
        """
        if not html:
            return True
        
        # Check content length
        if len(html) < 500:
            logger.info("HTML too short, suggesting rendered extraction")
            return True
        
        # Check for SPA indicators
        spa_indicators = [
            '<div id="root"',
            '<div id="app"',
            'data-reactroot',
            'ng-app',
            'v-app',
        ]
        
        if any(indicator in html.lower() for indicator in spa_indicators):
            logger.info("SPA indicators detected, suggesting rendered extraction")
            return True
        
        # Check script-to-text ratio (more robust detection)
        # Use regex to count actual script tags, not just string occurrences
        script_tags = len(re.findall(r'<script\b', html.lower()))
        if script_tags > 10:
            # Rough text extraction
            try:
                from html.parser import HTMLParser
                
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_length = 0
                    
                    def handle_data(self, data):
                        self.text_length += len(data.strip())
                
                extractor = TextExtractor()
                extractor.feed(html)
                
                if extractor.text_length < 1000:
                    logger.info("Low text density with many scripts, suggesting rendered extraction")
                    return True
                    
            except Exception:
                pass
        
        return False
