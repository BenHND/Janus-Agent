"""
TICKET 3 (P0): Test compact schema generation for burst mode.

This test validates that the compact schema:
1. Is significantly smaller than the full schema
2. Is deterministic (always produces the same output)
3. Contains the most important actions
4. Has valid syntax
"""

import pytest
from janus.runtime.core.module_action_schema import (
    get_compact_schema_section,
    get_prompt_schema_section
)
from janus.ai.llm.llm_utils import estimate_tokens


class TestCompactSchema:
    """Test compact schema generation."""
    
    def test_compact_schema_is_smaller(self):
        """Test that compact schema is significantly smaller than full schema."""
        compact_fr = get_compact_schema_section(language="fr", top_k=4)
        full_fr = get_prompt_schema_section(language="fr")
        
        compact_tokens = estimate_tokens(compact_fr)
        full_tokens = estimate_tokens(full_fr)
        
        # Compact should be at least 50% smaller
        assert compact_tokens < full_tokens * 0.5, \
            f"Compact schema ({compact_tokens} tokens) should be <50% of full schema ({full_tokens} tokens)"
        
        # Should be under 300 tokens (our new budget)
        assert compact_tokens < 300, \
            f"Compact schema ({compact_tokens} tokens) should be under 300 tokens"
    
    def test_compact_schema_is_deterministic(self):
        """Test that compact schema always produces the same output."""
        schema1 = get_compact_schema_section(language="fr", top_k=4)
        schema2 = get_compact_schema_section(language="fr", top_k=4)
        
        assert schema1 == schema2, "Compact schema should be deterministic"
    
    def test_compact_schema_contains_essential_actions(self):
        """Test that compact schema contains the most essential actions."""
        compact = get_compact_schema_section(language="fr", top_k=4)
        
        # Should contain all 8 modules
        assert "system:" in compact
        assert "browser:" in compact
        assert "messaging:" in compact
        assert "crm:" in compact
        assert "files:" in compact
        assert "ui:" in compact
        assert "code:" in compact
        assert "llm:" in compact
        
        # Should contain essential actions
        assert "open_application" in compact
        assert "open_url" in compact
        assert "click" in compact
        assert "type" in compact
    
    def test_compact_schema_has_valid_syntax(self):
        """Test that compact schema has valid syntax hints."""
        compact_fr = get_compact_schema_section(language="fr", top_k=4)
        compact_en = get_compact_schema_section(language="en", top_k=4)
        
        # Should have syntax reminder
        assert '{"module"' in compact_fr
        assert '{"module"' in compact_en
        
        # Should have warning symbol
        assert "⚠️" in compact_fr
        assert "⚠️" in compact_en
    
    def test_compact_schema_different_top_k(self):
        """Test that different top_k values produce different sizes."""
        compact_2 = get_compact_schema_section(language="fr", top_k=2)
        compact_3 = get_compact_schema_section(language="fr", top_k=3)
        compact_4 = get_compact_schema_section(language="fr", top_k=4)
        
        tokens_2 = estimate_tokens(compact_2)
        tokens_3 = estimate_tokens(compact_3)
        tokens_4 = estimate_tokens(compact_4)
        
        # More actions = more tokens
        assert tokens_2 < tokens_3 < tokens_4, \
            f"Expected tokens_2 ({tokens_2}) < tokens_3 ({tokens_3}) < tokens_4 ({tokens_4})"
    
    def test_compact_schema_english_and_french(self):
        """Test that both English and French schemas work."""
        compact_fr = get_compact_schema_section(language="fr", top_k=4)
        compact_en = get_compact_schema_section(language="en", top_k=4)
        
        # Both should be valid
        assert len(compact_fr) > 0
        assert len(compact_en) > 0
        
        # Both should have language-specific content
        assert "ACTIONS PRINCIPALES" in compact_fr
        assert "MAIN ACTIONS" in compact_en
    
    def test_compact_schema_format(self):
        """Test that compact schema has the expected format."""
        compact = get_compact_schema_section(language="fr", top_k=4)
        
        # Should show parameters for actions
        assert "(" in compact  # Function-like syntax
        assert ")" in compact
        
        # Should use commas to separate parameters
        assert "," in compact
        
        # Should have one line per module
        lines = [line for line in compact.split('\n') if line.strip() and ':' in line and not '===' in line and not '⚠️' in line]
        # Should have 8 modules
        assert len(lines) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
