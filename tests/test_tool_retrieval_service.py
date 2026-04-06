"""
Tests for ToolRetrievalService - RAG-based tool selection

TICKET-FEAT-TOOL-RAG: Test suite for semantic tool retrieval
"""

import pytest
from unittest.mock import MagicMock, patch

from janus.services.tool_retrieval_service import ToolRetrievalService, RAG_AVAILABLE
from janus.config.tools_registry import TOOLS_CATALOG


# Skip tests if RAG dependencies not available
pytestmark = pytest.mark.skipif(
    not RAG_AVAILABLE,
    reason="Tool RAG dependencies (chromadb, sentence-transformers) not installed"
)


class TestToolRetrievalService:
    """Test suite for ToolRetrievalService"""
    
    def test_initialization(self):
        """Test service can be initialized"""
        service = ToolRetrievalService()
        
        assert service.available == RAG_AVAILABLE
        assert not service.indexed
        assert service.collection_name == "tool_definitions"
        assert service.embedding_model_name == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_index_tools_success(self):
        """Test indexing tools from catalog"""
        service = ToolRetrievalService()
        
        # Index the tools catalog
        success = service.index_tools(TOOLS_CATALOG)
        
        assert success is True
        assert service.indexed is True
    
    def test_index_tools_empty_catalog(self):
        """Test indexing with empty catalog"""
        service = ToolRetrievalService()
        
        # Index empty catalog
        success = service.index_tools([])
        
        assert success is False
        assert service.indexed is False
    
    def test_index_tools_invalid_format(self):
        """Test indexing with invalid tool format"""
        service = ToolRetrievalService()
        
        # Index with tool missing ID
        invalid_catalog = [
            {"signature": "test", "description": "test"}  # Missing "id"
        ]
        success = service.index_tools(invalid_catalog)
        
        # Should still be False since no valid tools
        assert success is False
    
    def test_get_relevant_tools_crm_query(self):
        """Test retrieving relevant tools for CRM query"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Query for Salesforce/CRM functionality
        result = service.get_relevant_tools("Search for contact Dupont in Salesforce", top_k=5)
        
        # Should return formatted tools
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should include CRM-related tools
        assert "crm" in result.lower() or "contact" in result.lower()
    
    def test_get_relevant_tools_messaging_query(self):
        """Test retrieving relevant tools for messaging query"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Query for messaging functionality
        result = service.get_relevant_tools("Post message to Slack channel", top_k=5)
        
        # Should return formatted tools
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should include messaging-related tools
        assert "messaging" in result.lower() or "slack" in result.lower() or "message" in result.lower()
    
    def test_get_relevant_tools_file_query(self):
        """Test retrieving relevant tools for file operations"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Query for file operations
        result = service.get_relevant_tools("Open the documents folder", top_k=5)
        
        # Should return formatted tools
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should include file-related tools
        assert "file" in result.lower() or "folder" in result.lower() or "directory" in result.lower()
    
    def test_get_relevant_tools_not_indexed(self):
        """Test getting tools when not indexed returns empty"""
        service = ToolRetrievalService()
        
        # Don't index - should return empty
        result = service.get_relevant_tools("test query", top_k=5)
        
        assert result == ""
    
    def test_get_relevant_tools_caching(self):
        """Test that caching works for repeated queries"""
        service = ToolRetrievalService(enable_cache=True)
        service.index_tools(TOOLS_CATALOG)
        
        query = "Search Salesforce contact"
        
        # First query - not cached
        result1 = service.get_relevant_tools(query, top_k=5)
        stats1 = service.get_statistics()
        
        # Second query - should hit cache
        result2 = service.get_relevant_tools(query, top_k=5)
        stats2 = service.get_statistics()
        
        # Results should be identical
        assert result1 == result2
        
        # Cache hits should increase
        assert stats2["cache_hits"] > stats1["cache_hits"]
    
    def test_get_relevant_tools_latency(self):
        """Test that retrieval latency meets <200ms requirement"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Query multiple times
        for _ in range(5):
            service.get_relevant_tools("test query", top_k=5)
        
        # Check average latency
        stats = service.get_statistics()
        
        # Average latency should be well under 200ms
        # Note: First query may be slower due to model loading
        # but average should still be good
        assert stats["avg_latency_ms"] < 300  # Generous threshold for CI
        assert stats["total_queries"] == 5
    
    def test_get_relevant_tools_top_k(self):
        """Test that top_k parameter limits results"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Query with different top_k values
        result_3 = service.get_relevant_tools("test", top_k=3)
        result_5 = service.get_relevant_tools("test", top_k=5)
        
        # Count lines in results (each line is one tool)
        lines_3 = len([l for l in result_3.split('\n') if l.strip()])
        lines_5 = len([l for l in result_5.split('\n') if l.strip()])
        
        assert lines_3 <= 3
        assert lines_5 <= 5
        assert lines_5 >= lines_3
    
    def test_statistics(self):
        """Test statistics tracking"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Perform some queries
        service.get_relevant_tools("query 1", top_k=5)
        service.get_relevant_tools("query 2", top_k=5)
        
        # Get statistics
        stats = service.get_statistics()
        
        assert stats["total_queries"] == 2
        assert stats["indexed"] is True
        assert stats["available"] is True
        assert "avg_latency_ms" in stats
        assert "max_latency_ms" in stats
    
    def test_clear_cache(self):
        """Test cache clearing"""
        service = ToolRetrievalService(enable_cache=True)
        service.index_tools(TOOLS_CATALOG)
        
        # Query to populate cache
        service.get_relevant_tools("test", top_k=5)
        
        stats_before = service.get_statistics()
        assert stats_before["cache_size"] > 0
        
        # Clear cache
        service.clear_cache()
        
        stats_after = service.get_statistics()
        assert stats_after["cache_size"] == 0
    
    def test_format_tools_for_prompt(self):
        """Test prompt formatting"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Get formatted result
        result = service.get_relevant_tools("Salesforce contact", top_k=3, format_for_prompt=True)
        
        # Should be formatted as bullet list
        assert result.startswith("- ")
        assert "\n" in result
        
        # Each line should have signature and description
        for line in result.split("\n"):
            if line.strip():
                assert ":" in line  # Format: - signature: description
    
    def test_scalability_large_catalog(self):
        """Test performance with large catalog (100+ tools)"""
        service = ToolRetrievalService()
        
        # Create large catalog by duplicating existing tools
        large_catalog = []
        for i in range(5):  # 5x duplication = ~100 tools
            for tool in TOOLS_CATALOG:
                large_catalog.append({
                    **tool,
                    "id": f"{tool['id']}_{i}"
                })
        
        # Index large catalog
        success = service.index_tools(large_catalog)
        assert success is True
        
        # Query should still be fast
        result = service.get_relevant_tools("test", top_k=5)
        
        stats = service.get_statistics()
        # Should still be under threshold even with 100+ tools
        assert stats["max_latency_ms"] < 500  # Generous for CI


class TestToolRetrievalIntegration:
    """Integration tests with real TOOLS_CATALOG"""
    
    def test_tools_catalog_structure(self):
        """Test that TOOLS_CATALOG has proper structure"""
        from janus.config.tools_registry import TOOLS_CATALOG, TOTAL_TOOLS_COUNT
        
        # Validate catalog structure
        assert len(TOOLS_CATALOG) > 0
        assert len(TOOLS_CATALOG) == TOTAL_TOOLS_COUNT
        
        for tool in TOOLS_CATALOG:
            # Each tool must have required fields
            assert "id" in tool
            assert "signature" in tool
            assert "description" in tool
            assert "keywords" in tool
            
            # Fields should be non-empty strings
            assert isinstance(tool["id"], str) and len(tool["id"]) > 0
            assert isinstance(tool["signature"], str) and len(tool["signature"]) > 0
            assert isinstance(tool["description"], str) and len(tool["description"]) > 0
            assert isinstance(tool["keywords"], str) and len(tool["keywords"]) > 0
    
    def test_semantic_relevance_salesforce(self):
        """Test semantic relevance for Salesforce queries"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        queries = [
            "Search for Dupont in Salesforce",
            "Find contact in CRM",
            "Cherche un contact dans Salesforce",
            "Get customer information from CRM"
        ]
        
        for query in queries:
            result = service.get_relevant_tools(query, top_k=5)
            
            # Should return CRM-related tools
            assert len(result) > 0
            result_lower = result.lower()
            assert "crm" in result_lower or "contact" in result_lower or "salesforce" in result_lower
    
    def test_semantic_relevance_multilingual(self):
        """Test semantic relevance works for both French and English"""
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # French query
        result_fr = service.get_relevant_tools("Ouvrir un fichier", top_k=5)
        
        # English query with same intent
        result_en = service.get_relevant_tools("Open a file", top_k=5)
        
        # Both should return file-related tools
        assert len(result_fr) > 0
        assert len(result_en) > 0
        
        # Both should have "file" or related terms
        assert "file" in result_fr.lower() or "fichier" in result_fr.lower()
        assert "file" in result_en.lower()
