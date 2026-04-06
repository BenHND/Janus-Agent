"""
Tests for Token Counter Utility (TICKET-LLM-001)

Validates token counting functionality for LLM context management.
"""

import unittest

from janus.utils.token_counter import TokenCounter, count_tokens, truncate_to_tokens


class TestTokenCounter(unittest.TestCase):
    """Test token counting functionality"""
    
    def test_initialization(self):
        """Test TokenCounter initialization"""
        counter = TokenCounter()
        assert counter is not None
        assert counter.encoding_name == "cl100k_base"
    
    def test_count_empty_string(self):
        """Test counting tokens in empty string"""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
        assert counter.count_tokens(None) == 0
    
    def test_count_simple_text(self):
        """Test counting tokens in simple text"""
        counter = TokenCounter()
        
        # Short text
        text = "Hello, world!"
        tokens = counter.count_tokens(text)
        assert tokens > 0
        assert tokens < 10  # Should be around 3-4 tokens
    
    def test_count_long_text(self):
        """Test counting tokens in longer text"""
        counter = TokenCounter()
        
        # Longer text
        text = "This is a longer piece of text that contains multiple sentences. " * 10
        tokens = counter.count_tokens(text)
        assert tokens > 50  # Should be significantly more tokens
    
    def test_fallback_mode(self):
        """Test fallback approximation mode"""
        # Force fallback mode
        counter = TokenCounter(use_tiktoken=False)
        assert not counter.use_tiktoken
        
        text = "Hello, world!" * 10  # 130 chars
        tokens = counter.count_tokens(text)
        # With fallback (chars/3), should be around 43 tokens
        assert 40 <= tokens <= 50
    
    def test_truncate_short_text(self):
        """Test truncating text that's already within budget"""
        counter = TokenCounter()
        
        text = "Short text"
        result = counter.truncate_to_tokens(text, max_tokens=100)
        assert result == text  # Should not be truncated
    
    def test_truncate_long_text(self):
        """Test truncating text that exceeds budget"""
        counter = TokenCounter()
        
        # Create long text
        text = "This is a test sentence. " * 100  # ~2500 chars
        
        # Truncate to 50 tokens
        result = counter.truncate_to_tokens(text, max_tokens=50)
        
        # Result should be shorter
        assert len(result) < len(text)
        
        # Result should fit within token budget (with small margin for encoding differences)
        result_tokens = counter.count_tokens(result)
        assert result_tokens <= 55  # Allow small margin
    
    def test_truncate_empty_text(self):
        """Test truncating empty text"""
        counter = TokenCounter()
        self.assertEqual(counter.truncate_to_tokens("", max_tokens=10), "")
        self.assertEqual(counter.truncate_to_tokens(None, max_tokens=10), "")
    
    def test_count_messages_dict_format(self):
        """Test counting tokens in message dict format"""
        counter = TokenCounter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
        
        tokens = counter.count_tokens_for_messages(messages)
        assert tokens > 0
        # Should include overhead for formatting
        assert tokens > sum(counter.count_tokens(m["content"]) for m in messages)
    
    def test_count_messages_string_format(self):
        """Test counting tokens in plain string format"""
        counter = TokenCounter()
        
        messages = [
            "First message",
            "Second message",
            "Third message"
        ]
        
        tokens = counter.count_tokens_for_messages(messages)
        assert tokens > 0
        assert tokens == sum(counter.count_tokens(m) for m in messages)
    
    def test_count_messages_mixed_format(self):
        """Test counting tokens with mixed message formats"""
        counter = TokenCounter()
        
        messages = [
            {"role": "user", "content": "Hello"},
            "Plain string message",
            {"role": "assistant", "content": "Response"},
        ]
        
        tokens = counter.count_tokens_for_messages(messages)
        assert tokens > 0
    
    def test_large_text_handling(self):
        """Test handling of very large text (book-sized)"""
        counter = TokenCounter()
        
        # Simulate pasting a book (~100k words, ~500k chars)
        large_text = "Lorem ipsum dolor sit amet. " * 20000  # ~560k chars
        
        tokens = counter.count_tokens(large_text)
        assert tokens > 10000  # Should be many thousands of tokens
        
        # Test truncation
        truncated = counter.truncate_to_tokens(large_text, max_tokens=1000)
        assert len(truncated) < len(large_text)
        assert counter.count_tokens(truncated) <= 1100  # With small margin


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_count_tokens_function(self):
        """Test global count_tokens function"""
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10
    
    def test_truncate_to_tokens_function(self):
        """Test global truncate_to_tokens function"""
        text = "This is a test. " * 100
        truncated = truncate_to_tokens(text, max_tokens=50)
        assert len(truncated) < len(text)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_unicode_text(self):
        """Test handling of Unicode text"""
        counter = TokenCounter()
        
        # Text with emojis and special characters
        text = "Hello 👋 世界 🌍 Здравствуй мир"
        tokens = counter.count_tokens(text)
        assert tokens > 0
    
    def test_code_text(self):
        """Test handling of code"""
        counter = TokenCounter()
        
        code = """
def hello_world():
    print("Hello, world!")
    return True
"""
        tokens = counter.count_tokens(code)
        assert tokens > 0
    
    def test_json_text(self):
        """Test handling of JSON"""
        counter = TokenCounter()
        
        json_text = '{"key": "value", "nested": {"foo": "bar"}}'
        tokens = counter.count_tokens(json_text)
        assert tokens > 0
    
    def test_extremely_long_single_word(self):
        """Test handling of extremely long single word"""
        counter = TokenCounter()
        
        # Very long "word" without spaces
        text = "a" * 10000
        tokens = counter.count_tokens(text)
        assert tokens > 0


class TestTokenBudgetScenarios(unittest.TestCase):
    """Test realistic token budget scenarios"""
    
    def test_4k_context_window(self):
        """Test fitting content in 4k context window"""
        counter = TokenCounter()
        
        # Simulate conversation history
        messages = []
        for i in range(100):
            messages.append(f"User message {i}: This is a test message with some content.")
            messages.append(f"Assistant response {i}: Here is my response to your message.")
        
        # Convert to text
        history_text = "\n".join(messages)
        tokens = counter.count_tokens(history_text)
        
        # If exceeds budget, truncate
        if tokens > 4000:
            truncated = counter.truncate_to_tokens(history_text, max_tokens=4000)
            truncated_tokens = counter.count_tokens(truncated)
            assert truncated_tokens <= 4100  # With small margin
    
    def test_8k_context_window(self):
        """Test fitting content in 8k context window (Llama 3)"""
        counter = TokenCounter()
        
        # Simulate larger context
        text = "This is sample text. " * 1000
        tokens = counter.count_tokens(text)
        
        if tokens > 8000:
            truncated = counter.truncate_to_tokens(text, max_tokens=8000)
            truncated_tokens = counter.count_tokens(truncated)
            assert truncated_tokens <= 8200  # With small margin
