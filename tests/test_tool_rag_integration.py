"""
Integration tests for Tool RAG in ActionCoordinator

TICKET-FEAT-TOOL-RAG: Test dynamic tool injection in prompt building
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.services.tool_retrieval_service import RAG_AVAILABLE


class TestActionCoordinatorToolRAG:
    """Test Tool RAG integration in ActionCoordinator"""
    
    def test_tool_retriever_lazy_loading(self):
        """Test that tool retriever is lazy-loaded"""
        coordinator = ActionCoordinator()
        
        # Should not be initialized yet
        assert coordinator._tool_retriever is None
        
        # Access should trigger lazy loading
        retriever = coordinator.tool_retriever
        
        # Should now be initialized (even if dependencies not available, it should be non-None)
        assert retriever is not None
    
    def test_tool_retriever_available(self):
        """Test tool retriever availability check"""
        coordinator = ActionCoordinator()
        retriever = coordinator.tool_retriever
        
        # Availability should match RAG_AVAILABLE
        assert retriever.available == RAG_AVAILABLE
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_tool_retriever_indexing(self):
        """Test that tools are indexed on first access"""
        coordinator = ActionCoordinator()
        retriever = coordinator.tool_retriever
        
        # Should be indexed if RAG is available
        if retriever.available:
            assert retriever.indexed is True
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_build_react_prompt_with_dynamic_tools(self):
        """Test prompt building includes dynamic tools"""
        coordinator = ActionCoordinator()
        
        # Build prompt with Salesforce-related query
        prompt = coordinator._build_react_prompt(
            user_goal="Search for contact Dupont in Salesforce",
            system_state={"active_app": "Chrome", "clipboard": "test"},
            visual_context="[]",
            memory={},
            language="fr"
        )
        
        # Prompt should be generated
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # If RAG is available, should include contextual tools section
        if coordinator.tool_retriever.available and coordinator.tool_retriever.indexed:
            # Should mention contextual tools
            assert "CONTEXTUELS" in prompt or "CONTEXTUAL" in prompt
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_build_react_prompt_crm_query(self):
        """Test that CRM query gets CRM tools in prompt"""
        coordinator = ActionCoordinator()
        
        # Build prompt with CRM query
        prompt = coordinator._build_react_prompt(
            user_goal="Find customer John Doe in Salesforce CRM",
            system_state={"active_app": "Chrome"},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        # If RAG available and indexed, should include CRM-related tools
        if coordinator.tool_retriever.available and coordinator.tool_retriever.indexed:
            prompt_lower = prompt.lower()
            # Should have CRM tools dynamically injected
            assert "crm" in prompt_lower or "contact" in prompt_lower or "salesforce" in prompt_lower
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_build_react_prompt_file_query(self):
        """Test that file query gets file tools in prompt"""
        coordinator = ActionCoordinator()
        
        # Build prompt with file query
        prompt = coordinator._build_react_prompt(
            user_goal="Open the documents folder",
            system_state={"active_app": "Finder"},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        # If RAG available, should include file-related tools
        if coordinator.tool_retriever.available and coordinator.tool_retriever.indexed:
            prompt_lower = prompt.lower()
            assert "file" in prompt_lower or "folder" in prompt_lower or "directory" in prompt_lower
    
    def test_build_react_prompt_fallback_without_rag(self):
        """Test prompt building works even without RAG"""
        coordinator = ActionCoordinator()
        
        # Mock tool retriever to simulate unavailable RAG
        coordinator._tool_retriever = MagicMock()
        coordinator._tool_retriever.available = False
        coordinator._tool_retriever.indexed = False
        
        # Build prompt
        prompt = coordinator._build_react_prompt(
            user_goal="Test goal",
            system_state={"active_app": "Test"},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        # Should still generate a prompt (using static tools or fallback)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Test goal" in prompt
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_build_react_prompt_performance(self):
        """Test that prompt building with RAG meets performance requirements"""
        import time
        
        coordinator = ActionCoordinator()
        
        # Warm up (first call may be slower due to lazy loading)
        coordinator._build_react_prompt(
            user_goal="warmup",
            system_state={},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        # Measure performance
        iterations = 5
        start = time.time()
        
        for _ in range(iterations):
            coordinator._build_react_prompt(
                user_goal="Search contact in Salesforce",
                system_state={"active_app": "Chrome"},
                visual_context="[]",
                memory={},
                language="en"
            )
        
        duration = time.time() - start
        avg_ms = (duration / iterations) * 1000
        
        # Average prompt building (including RAG) should be fast
        # Target: <200ms for RAG retrieval, so total prompt building should be <300ms
        assert avg_ms < 500  # Generous for CI environments
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_dynamic_tools_different_queries(self):
        """Test that different queries get different relevant tools"""
        coordinator = ActionCoordinator()
        
        if not (coordinator.tool_retriever.available and coordinator.tool_retriever.indexed):
            pytest.skip("RAG not available or not indexed")
        
        # Build prompts for different domains
        prompt_crm = coordinator._build_react_prompt(
            user_goal="Search Salesforce contact",
            system_state={},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        prompt_file = coordinator._build_react_prompt(
            user_goal="Open documents folder",
            system_state={},
            visual_context="[]",
            memory={},
            language="en"
        )
        
        # Extract contextual tools sections
        # They should be different for different query types
        # CRM query should have CRM tools, file query should have file tools
        assert "crm" in prompt_crm.lower() or "salesforce" in prompt_crm.lower()
        assert "file" in prompt_file.lower() or "folder" in prompt_file.lower()
    
    def test_tool_retriever_statistics(self):
        """Test that tool retriever statistics are tracked"""
        coordinator = ActionCoordinator()
        retriever = coordinator.tool_retriever
        
        if not (retriever.available and retriever.indexed):
            pytest.skip("RAG not available")
        
        # Build some prompts
        for i in range(3):
            coordinator._build_react_prompt(
                user_goal=f"test query {i}",
                system_state={},
                visual_context="[]",
                memory={},
                language="en"
            )
        
        # Check statistics
        stats = retriever.get_statistics()
        
        assert stats["total_queries"] >= 3
        assert "avg_latency_ms" in stats
        assert stats["indexed"] is True


class TestToolRAGEndToEnd:
    """End-to-end tests for Tool RAG feature"""
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_acceptance_criteria_1_salesforce_query(self):
        """
        Acceptance Criteria 1:
        When I ask "Search Dupont in Salesforce", the prompt should contain
        only relevant tool definitions (CRM contact search), not unrelated tools
        like send_email or file operations.
        """
        coordinator = ActionCoordinator()
        
        if not (coordinator.tool_retriever.available and coordinator.tool_retriever.indexed):
            pytest.skip("RAG not available")
        
        # Build prompt for Salesforce query
        prompt = coordinator._build_react_prompt(
            user_goal="Cherche Dupont sur Salesforce",
            system_state={"active_app": "Chrome"},
            visual_context="[]",
            memory={},
            language="fr"
        )
        
        # Get the dynamic tools section
        retriever = coordinator.tool_retriever
        dynamic_tools = retriever.get_relevant_tools(
            "Cherche Dupont sur Salesforce",
            top_k=5
        )
        
        # Should contain CRM/contact tools
        dynamic_lower = dynamic_tools.lower()
        assert "crm" in dynamic_lower or "contact" in dynamic_lower or "salesforce" in dynamic_lower
        
        # Dynamic tools should be focused - check it's not too long
        # (less than 10 tools, each ~100 chars = ~1000 chars max)
        assert len(dynamic_tools) < 2000
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_acceptance_criteria_3_latency(self):
        """
        Acceptance Criteria 3:
        Tool retrieval latency should be <200ms
        """
        from janus.services.tool_retrieval_service import ToolRetrievalService
        from janus.config.tools_registry import TOOLS_CATALOG
        
        service = ToolRetrievalService()
        service.index_tools(TOOLS_CATALOG)
        
        # Run multiple queries and check latency
        for _ in range(10):
            service.get_relevant_tools("test query", top_k=5)
        
        stats = service.get_statistics()
        
        # Average latency should be under 200ms
        # (First query might be slower, but average should meet target)
        assert stats["avg_latency_ms"] < 250  # Slightly generous for CI
    
    @pytest.mark.skipif(not RAG_AVAILABLE, reason="RAG dependencies not available")
    def test_acceptance_criteria_4_scalability(self):
        """
        Acceptance Criteria 4:
        System should work with 100+ tools without modifying the prompt template
        """
        from janus.services.tool_retrieval_service import ToolRetrievalService
        from janus.config.tools_registry import TOOLS_CATALOG
        
        # Create catalog with 100+ tools
        large_catalog = []
        for i in range(5):
            for tool in TOOLS_CATALOG:
                large_catalog.append({
                    **tool,
                    "id": f"{tool['id']}_{i}"
                })
        
        assert len(large_catalog) >= 100
        
        # Service should handle it
        service = ToolRetrievalService()
        success = service.index_tools(large_catalog)
        
        assert success is True
        
        # Queries should still work
        result = service.get_relevant_tools("Search contact", top_k=5)
        assert len(result) > 0
        
        # And still be fast
        stats = service.get_statistics()
        assert stats["max_latency_ms"] < 500
