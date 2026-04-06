"""
LLM Utilities - Shared helper functions for LLM operations

ARCH-002: Centralized utilities to avoid code duplication.
"""


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (ROUGH approximation: 1 token ≈ 4 chars).
    
    Note: This is a simplified heuristic that may be inaccurate for:
    - Non-English text (especially Asian languages)
    - Code (varies by language)
    - Special characters and formatting
    
    For accurate token counts, use tiktoken or model-specific tokenizers.
    This method is used for instrumentation metrics only.
    
    Args:
        text: Text to estimate tokens for (None or empty returns 1)
        
    Returns:
        Estimated number of tokens (minimum 1)
    """
    if not text:
        return 1
    return max(1, len(text) // 4)
