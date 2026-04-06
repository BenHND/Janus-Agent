"""
Token Counter Utility for LLM Context Management

TICKET-LLM-001: Provides token counting functionality for managing LLM context windows.
Supports both tiktoken (for OpenAI models) and fallback approximation (for Llama/other models).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import tiktoken (optional dependency)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.info("tiktoken not available, using fallback token approximation")


class TokenCounter:
    """
    Token counter with support for multiple encoding methods.
    
    Features:
    - Precise counting with tiktoken (when available)
    - Fallback approximation for non-OpenAI models (len/3 heuristic)
    - Caching for performance
    """
    
    # Default encoding for OpenAI models
    DEFAULT_ENCODING = "cl100k_base"  # Used by GPT-4, GPT-3.5-turbo
    
    # Fallback ratio: approximately 3 characters per token for most languages
    FALLBACK_CHARS_PER_TOKEN = 3
    
    def __init__(self, encoding_name: Optional[str] = None, use_tiktoken: bool = True):
        """
        Initialize token counter.
        
        Args:
            encoding_name: Name of tiktoken encoding (e.g., "cl100k_base", "p50k_base")
                          If None, uses DEFAULT_ENCODING
            use_tiktoken: Whether to use tiktoken if available (default: True)
        """
        self.encoding_name = encoding_name or self.DEFAULT_ENCODING
        self.use_tiktoken = use_tiktoken and TIKTOKEN_AVAILABLE
        self.encoding = None
        
        if self.use_tiktoken:
            try:
                self.encoding = tiktoken.get_encoding(self.encoding_name)
                logger.debug(f"TokenCounter initialized with tiktoken encoding: {self.encoding_name}")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding {self.encoding_name}: {e}")
                self.use_tiktoken = False
        
        if not self.use_tiktoken:
            logger.info("TokenCounter using fallback approximation (chars/3)")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens (approximate for fallback mode)
        """
        if not text:
            return 0
        
        if self.use_tiktoken and self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed, using fallback: {e}")
                # Fall through to fallback
        
        # Fallback: approximate token count
        return max(1, len(text) // self.FALLBACK_CHARS_PER_TOKEN)
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token budget.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            
        Returns:
            Truncated text that fits within token budget
        """
        if not text:
            return ""
        
        # Quick check: if text is already short enough
        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text
        
        if self.use_tiktoken and self.encoding:
            try:
                # Encode and truncate at token boundary
                tokens = self.encoding.encode(text)
                truncated_tokens = tokens[:max_tokens]
                return self.encoding.decode(truncated_tokens)
            except Exception as e:
                logger.warning(f"Token truncation failed, using fallback: {e}")
                # Fall through to fallback
        
        # Fallback: truncate by character count (approximate)
        max_chars = max_tokens * self.FALLBACK_CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars]
    
    def count_tokens_for_messages(self, messages: list) -> int:
        """
        Count tokens for a list of message objects.
        
        Supports both dict format ({"role": "user", "content": "text"})
        and plain string format.
        
        Args:
            messages: List of message dicts or strings
            
        Returns:
            Total token count for all messages
        """
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                # Count role + content
                role = msg.get("role", "")
                content = msg.get("content", "")
                total += self.count_tokens(role)
                total += self.count_tokens(content)
                # Add overhead for message formatting (typically 4 tokens per message)
                total += 4
            elif isinstance(msg, str):
                total += self.count_tokens(msg)
            else:
                # Try to convert to string
                total += self.count_tokens(str(msg))
        
        return total


# Global singleton instance for efficient reuse
_global_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """
    Get the global TokenCounter instance.
    
    Returns:
        Singleton TokenCounter instance
    """
    global _global_counter
    if _global_counter is None:
        _global_counter = TokenCounter()
    return _global_counter


def count_tokens(text: str) -> int:
    """
    Convenience function to count tokens using the global counter.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Number of tokens
    """
    return get_token_counter().count_tokens(text)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    Convenience function to truncate text using the global counter.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens
        
    Returns:
        Truncated text
    """
    return get_token_counter().truncate_to_tokens(text, max_tokens)
