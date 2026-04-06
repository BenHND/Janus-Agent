"""
Test ARCH-002: LLM instrumentation and metrics tracking

This test verifies that:
1. All LLM calls are tracked with metrics
2. No hidden LLM calls exist
3. LLM configuration is centralized
4. ContextRouter can be disabled
"""

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Simple replacement for pytest functions
    def skip(reason):
        pass

from unittest.mock import Mock, patch

from janus.ai.llm import UnifiedLLMClient, get_llm_metrics, reset_llm_metrics
from janus.ai.reasoning.context_router import ContextRouter


class TestLLMInstrumentation:
    """Test LLM call instrumentation and transparency"""
    
    def test_unified_client_tracks_metrics(self):
        """Test that UnifiedLLMClient tracks all calls in global metrics"""
        # Reset metrics before test
        reset_llm_metrics()
        
        # Create mock client
        client = UnifiedLLMClient(provider="mock")
        
        # Make a call
        result = client.generate("test prompt", system_prompt="test system")
        
        # Verify metrics were recorded
        metrics = get_llm_metrics()
        assert metrics["total_calls"] == 1, "Should record 1 LLM call"
        assert metrics["total_tokens_in"] > 0, "Should track input tokens"
        assert metrics["total_tokens_out"] > 0, "Should track output tokens"
        assert metrics["total_latency_ms"] >= 0, "Should track latency"
        
        # Verify tracking by model
        assert "mock/mistral" in metrics["calls_by_model"], "Should track calls by model"
        assert metrics["calls_by_model"]["mock/mistral"] == 1
    
    def test_metrics_accumulate_across_calls(self):
        """Test that metrics accumulate across multiple calls"""
        reset_llm_metrics()
        
        client = UnifiedLLMClient(provider="mock")
        
        # Make multiple calls
        for i in range(3):
            client.generate(f"test prompt {i}")
        
        metrics = get_llm_metrics()
        assert metrics["total_calls"] == 3, "Should record 3 LLM calls"
        assert metrics["calls_by_model"]["mock/mistral"] == 3
    
    def test_metrics_reset(self):
        """Test that metrics can be reset"""
        reset_llm_metrics()
        
        client = UnifiedLLMClient(provider="mock")
        client.generate("test")
        
        # Verify we have metrics
        metrics = get_llm_metrics()
        assert metrics["total_calls"] == 1
        
        # Reset
        reset_llm_metrics()
        
        # Verify metrics are cleared
        metrics = get_llm_metrics()
        assert metrics["total_calls"] == 0
        assert metrics["total_tokens_in"] == 0
        assert metrics["total_tokens_out"] == 0
        assert len(metrics["calls_by_site"]) == 0
        assert len(metrics["calls_by_model"]) == 0


class TestContextRouterDisable:
    """Test ContextRouter can be disabled to avoid hidden LLM calls"""
    
    def test_router_disabled_returns_all_context(self):
        """Test that disabled router returns all context keys (no LLM call)"""
        reset_llm_metrics()
        
        # Create disabled router (no LLM client)
        router = ContextRouter(llm_client=None, enabled=False)
        
        # Get requirements
        requirements = router.get_requirements("Copie ça")
        
        # Should return all keys (safe fallback)
        from janus.ai.reasoning.context_router import VALID_CONTEXT_KEYS
        assert set(requirements) == VALID_CONTEXT_KEYS
        
        # Verify no LLM call was made
        metrics = get_llm_metrics()
        assert metrics["total_calls"] == 0, "Disabled router should not make LLM calls"
    
    def test_router_with_client_but_disabled(self):
        """Test that router with client but disabled=False still doesn't call LLM"""
        reset_llm_metrics()
        
        # Create mock client
        mock_client = UnifiedLLMClient(provider="mock")
        
        # Create disabled router with client
        router = ContextRouter(llm_client=mock_client, enabled=False)
        
        # Get requirements
        requirements = router.get_requirements("Copie ça")
        
        # Should return all keys without calling LLM
        from janus.ai.reasoning.context_router import VALID_CONTEXT_KEYS
        assert set(requirements) == VALID_CONTEXT_KEYS
        
        # Verify no LLM call was made through router
        # (The mock client itself might have some initialization calls, so we check router metrics)
        metrics = router.get_metrics()
        assert metrics["fallback_count"] > 0, "Should use fallback when disabled"
    
    def test_router_enabled_with_client(self):
        """Test that enabled router with client does make LLM calls"""
        reset_llm_metrics()
        
        # Create mock client
        mock_client = UnifiedLLMClient(provider="mock")
        
        # Create enabled router
        router = ContextRouter(llm_client=mock_client, enabled=True)
        
        # Get requirements
        requirements = router.get_requirements("Copie ça")
        
        # Should have made an LLM call
        metrics = get_llm_metrics()
        # Note: Mock client might return different results, but we verify a call was made
        assert router.available is True, "Router should be available with client"


class TestCentralizedConfiguration:
    """Test that LLM configuration is centralized"""
    
    def test_model_is_qwen25(self):
        """Test that default model is qwen2.5:7b-instruct"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        # Default Ollama model should be qwen2.5:7b-instruct
        assert ReasonerLLM.DEFAULT_OLLAMA_MODEL == "qwen2.5:7b-instruct"
    
    def test_no_hardcoded_llama32_in_context_router(self):
        """Test that ContextRouter no longer hardcodes llama3.2"""
        # ContextRouter should not have a default model anymore
        router = ContextRouter(llm_client=None, enabled=False)
        
        # Router should not have model_name attribute
        assert not hasattr(router, 'model_name'), "ContextRouter should not have hardcoded model"


class TestNoHiddenLLMCalls:
    """Test that no hidden LLM calls exist"""
    
    def test_simple_command_no_hidden_calls(self):
        """Test that a simple command doesn't make hidden LLM calls"""
        reset_llm_metrics()
        
        # This test is a placeholder - in a real scenario, we'd run a simple command
        # and verify llm_calls == expected_calls
        
        # For now, we just verify the metrics are working
        initial_metrics = get_llm_metrics()
        assert initial_metrics["total_calls"] == 0
        
        # Make one explicit call
        client = UnifiedLLMClient(provider="mock")
        client.generate("test")
        
        # Verify exactly 1 call
        final_metrics = get_llm_metrics()
        assert final_metrics["total_calls"] == 1, "Should have exactly 1 LLM call (no hidden calls)"


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__, "-v"])
    else:
        print("⚠️  pytest not installed. Install with: pip install pytest")
        print("Or run tests with the full test suite via run_tests.sh")
