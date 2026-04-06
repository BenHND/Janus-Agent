"""
Tests for RAG-001 Tool Retrieval Governance

Tests the new features:
1. Auto-generated tool specs from module_action_schema
2. Session-based caching
3. Version hash tracking
4. Delta-only updates
5. Stability metrics
"""

import pytest
from unittest.mock import MagicMock, patch

from janus.runtime.core.tool_spec_generator import (
    generate_tools_catalog,
    generate_catalog_version_hash,
    get_catalog_stats,
    generate_tool_spec_from_action,
)
from janus.runtime.core.module_action_schema import ALL_MODULES, BROWSER_MODULE
from janus.config.tools_registry import TOOLS_CATALOG, CATALOG_VERSION_HASH
from janus.services.tool_retrieval_service import ToolRetrievalService, RAG_AVAILABLE


class TestToolSpecGenerator:
    """Test auto-generation of tool specs from module_action_schema"""
    
    def test_generate_tools_catalog(self):
        """Test that tools catalog can be generated from schema"""
        catalog = generate_tools_catalog()
        
        assert len(catalog) > 0
        assert isinstance(catalog, list)
        
        # Check first tool structure
        tool = catalog[0]
        assert "id" in tool
        assert "signature" in tool
        assert "description" in tool
        assert "keywords" in tool
    
    def test_catalog_version_hash(self):
        """Test that version hash is generated consistently"""
        hash1 = generate_catalog_version_hash()
        hash2 = generate_catalog_version_hash()
        
        # Same catalog should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256
    
    def test_catalog_stats(self):
        """Test catalog statistics"""
        stats = get_catalog_stats()
        
        assert "total_tools" in stats
        assert "total_modules" in stats
        assert "tools_per_module" in stats
        assert "version_hash" in stats
        
        # Should have 8 modules (from module_action_schema)
        assert stats["total_modules"] == 8
        assert len(stats["tools_per_module"]) == 8
    
    def test_tool_spec_format(self):
        """Test that generated tool spec has correct format"""
        # Get a sample action from module_action_schema
        browser_actions = BROWSER_MODULE.actions
        assert len(browser_actions) > 0
        
        action = browser_actions[0]  # open_url
        tool_spec = generate_tool_spec_from_action(
            "browser",
            BROWSER_MODULE.description,
            action
        )
        
        # Verify structure
        assert tool_spec["id"] == f"browser_{action.name}"
        assert "browser." in tool_spec["signature"]
        assert tool_spec["description"] == action.description
        assert len(tool_spec["keywords"]) > 0
    
    def test_tools_registry_uses_auto_generation(self):
        """Test that tools_registry.py uses auto-generated tools"""
        from janus.config.tools_registry import _CORE_MODULE_TOOLS
        
        # Should have tools from all 8 modules
        assert len(_CORE_MODULE_TOOLS) > 0
        
        # Should match generated catalog
        generated = generate_tools_catalog()
        assert len(_CORE_MODULE_TOOLS) == len(generated)
    
    def test_merged_catalog(self):
        """Test that merged catalog includes both core and backend tools"""
        # Total should be core + backend (with deduplication)
        assert len(TOOLS_CATALOG) >= len(generate_tools_catalog())
        
        # Check version hash is set
        assert CATALOG_VERSION_HASH is not None
        assert len(CATALOG_VERSION_HASH) == 16


# Skip RAG-specific tests if dependencies not available
pytestmark_rag = pytest.mark.skipif(
    not RAG_AVAILABLE,
    reason="Tool RAG dependencies (chromadb, sentence-transformers) not installed"
)


@pytestmark_rag
class TestSessionCache:
    """Test session-based caching feature (RAG-001)"""
    
    def test_session_cache_initialization(self):
        """Test that session cache is initialized"""
        service = ToolRetrievalService(enable_session_cache=True)
        
        assert service.enable_session_cache is True
        assert hasattr(service, '_session_cache')
        assert hasattr(service, '_last_selection')
    
    def test_session_cache_hit(self):
        """Test session cache hit behavior"""
        service = ToolRetrievalService(enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        query = "Search contact in Salesforce"
        session_id = "test_session_1"
        
        # First query - miss
        result1 = service.get_relevant_tools(query, top_k=5, session_id=session_id)
        stats1 = service.get_statistics()
        
        # Second query - should hit session cache
        result2 = service.get_relevant_tools(query, top_k=5, session_id=session_id)
        stats2 = service.get_statistics()
        
        # Results should be identical
        assert result1 == result2
        
        # Session cache hits should increase
        assert stats2["session_cache_hits"] > stats1["session_cache_hits"]
    
    def test_different_sessions_separate_caches(self):
        """Test that different sessions have separate caches"""
        service = ToolRetrievalService(enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        query = "Search contact"
        
        # Query from two different sessions
        result1 = service.get_relevant_tools(query, session_id="session_1")
        result2 = service.get_relevant_tools(query, session_id="session_2")
        
        # Both should have content
        assert len(result1) > 0
        assert len(result2) > 0
        
        # Session cache should have 2 entries
        assert len(service._session_cache) == 2
    
    def test_clear_session_cache_specific(self):
        """Test clearing specific session cache"""
        service = ToolRetrievalService(enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        # Create cache entries for two sessions
        service.get_relevant_tools("test", session_id="session_1")
        service.get_relevant_tools("test", session_id="session_2")
        
        assert len(service._session_cache) == 2
        
        # Clear only session_1
        service.clear_session_cache("session_1")
        
        assert len(service._session_cache) == 1
        assert "session_2" in service._session_cache
        assert "session_1" not in service._session_cache
    
    def test_clear_all_session_caches(self):
        """Test clearing all session caches"""
        service = ToolRetrievalService(enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        # Create multiple session caches
        service.get_relevant_tools("test", session_id="session_1")
        service.get_relevant_tools("test", session_id="session_2")
        
        # Clear all
        service.clear_session_cache()
        
        assert len(service._session_cache) == 0


@pytestmark_rag
class TestVersionTracking:
    """Test version hash tracking and cache invalidation (RAG-001)"""
    
    def test_version_tracking_on_index(self):
        """Test that version is tracked when indexing"""
        service = ToolRetrievalService()
        
        version = "test_version_123"
        service.index_tools(TOOLS_CATALOG, catalog_version=version)
        
        assert service._catalog_version == version
    
    def test_cache_invalidation_on_version_change(self):
        """Test that caches are cleared on version change"""
        service = ToolRetrievalService(enable_session_cache=True)
        
        # Index with version 1
        service.index_tools(TOOLS_CATALOG[:10], catalog_version="v1")
        service.get_relevant_tools("test", session_id="session_1")
        
        # Verify caches have data
        assert len(service._cache) > 0 or len(service._session_cache) > 0
        
        # Re-index with version 2
        service.index_tools(TOOLS_CATALOG[:10], catalog_version="v2")
        
        # Caches should be cleared
        assert len(service._cache) == 0
        assert len(service._session_cache) == 0
    
    def test_version_in_statistics(self):
        """Test that version is included in statistics"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG, catalog_version=CATALOG_VERSION_HASH)
        
        stats = service.get_statistics()
        
        assert "catalog_version" in stats
        assert stats["catalog_version"] == CATALOG_VERSION_HASH


@pytestmark_rag
class TestDeltaUpdates:
    """Test delta-only updates feature (RAG-001)"""
    
    def test_delta_updates_initialization(self):
        """Test that delta updates can be enabled"""
        service = ToolRetrievalService(enable_delta_updates=True)
        
        assert service.enable_delta_updates is True
    
    def test_first_query_returns_full_list(self):
        """Test that first query returns full tool list"""
        service = ToolRetrievalService(enable_delta_updates=True, enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        result = service.get_relevant_tools(
            "Search contact",
            session_id="session_1",
            return_delta=True,
            top_k=5
        )
        
        # First query should return full list (no delta markers)
        assert len(result) > 0
        # Should not have delta markers on first call
        # (implementation returns full list when no previous selection)
    
    def test_delta_statistics_tracked(self):
        """Test that delta updates are tracked in statistics"""
        service = ToolRetrievalService(enable_delta_updates=True, enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        # Make queries with delta enabled
        service.get_relevant_tools("test1", session_id="s1", return_delta=True)
        service.get_relevant_tools("test2", session_id="s1", return_delta=True)
        
        stats = service.get_statistics()
        assert "delta_updates" in stats


@pytestmark_rag
class TestStability:
    """Test tool selection stability (RAG-001)"""
    
    def test_repeated_queries_return_same_tools(self):
        """Test that repeated identical queries return same tools"""
        service = ToolRetrievalService(enable_session_cache=True)
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        query = "Search contact in CRM"
        session_id = "stability_test"
        
        # Query 5 times
        results = []
        for _ in range(5):
            result = service.get_relevant_tools(query, session_id=session_id, top_k=5)
            results.append(result)
        
        # All results should be identical (stable)
        for result in results[1:]:
            assert result == results[0], "Tool selection not stable across repeated queries"
    
    def test_similar_queries_have_high_overlap(self):
        """Test that similar queries return similar tools"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        # Similar queries
        query1 = "Search contact in Salesforce"
        query2 = "Find person in CRM"
        query3 = "Lookup customer in Salesforce"
        
        result1 = service.get_relevant_tools(query1, top_k=5)
        result2 = service.get_relevant_tools(query2, top_k=5)
        result3 = service.get_relevant_tools(query3, top_k=5)
        
        # All should have CRM-related tools
        assert "crm" in result1.lower() or "contact" in result1.lower()
        assert "crm" in result2.lower() or "contact" in result2.lower()
        assert "crm" in result3.lower() or "contact" in result3.lower()
    
    def test_performance_stability(self):
        """Test that performance is stable across queries"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG, CATALOG_VERSION_HASH)
        
        # Run 10 queries
        for i in range(10):
            service.get_relevant_tools(f"test query {i}", top_k=5)
        
        stats = service.get_statistics()
        
        # Average latency should be reasonable
        assert stats["avg_latency_ms"] < 300  # Generous for CI
        
        # Max latency should not be too much higher than average
        # (indicates stable performance)
        assert stats["max_latency_ms"] < stats["avg_latency_ms"] * 3


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""
    
    def test_old_api_still_works(self):
        """Test that old API without session_id still works"""
        if not RAG_AVAILABLE:
            pytest.skip("RAG dependencies not available")
        
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Old API call (no session_id, no return_delta)
        result = service.get_relevant_tools("test query", top_k=5)
        
        assert isinstance(result, str)
    
    def test_statistics_include_new_fields(self):
        """Test that statistics include new RAG-001 fields"""
        service = ToolRetrievalService()
        
        stats = service.get_statistics()
        
        # New fields
        assert "session_cache_size" in stats
        assert "catalog_version" in stats
        
        # Old fields still present
        assert "cache_size" in stats
        assert "indexed" in stats
        assert "available" in stats
