"""
Tests for global shutdown mechanism - TICKET 1 (P0)

Verifies that:
1. Shutdown flag can be set and checked
2. AgentRegistry aborts actions after shutdown
3. SystemBridge aborts AppleScript after shutdown
4. Cleanup pipeline stops all threads
"""

import asyncio
import pytest
import threading
import time

from janus.runtime.shutdown import (
    request_shutdown,
    is_shutdown_requested,
    get_shutdown_reason,
    reset_shutdown_state,
)


class TestShutdownModule:
    """Test the global shutdown module."""
    
    def setup_method(self):
        """Reset shutdown state before each test."""
        reset_shutdown_state()
    
    def teardown_method(self):
        """Reset shutdown state after each test."""
        reset_shutdown_state()
    
    def test_initial_state(self):
        """Test that shutdown is not requested initially."""
        assert not is_shutdown_requested()
        assert get_shutdown_reason() is None
    
    def test_request_shutdown(self):
        """Test that shutdown can be requested."""
        request_shutdown("Test shutdown")
        
        assert is_shutdown_requested()
        assert get_shutdown_reason() == "Test shutdown"
    
    def test_request_shutdown_multiple_times(self):
        """Test that multiple shutdown requests keep the first reason."""
        request_shutdown("First reason")
        request_shutdown("Second reason")
        
        assert is_shutdown_requested()
        assert get_shutdown_reason() == "First reason"
    
    def test_thread_safety(self):
        """Test that shutdown flag is thread-safe."""
        results = []
        
        def check_and_set():
            time.sleep(0.01)  # Small delay to encourage race conditions
            if not is_shutdown_requested():
                request_shutdown(f"Thread {threading.current_thread().name}")
            results.append(is_shutdown_requested())
        
        threads = [
            threading.Thread(target=check_and_set, name=f"Thread-{i}")
            for i in range(10)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All threads should see shutdown requested
        assert all(results)
        assert is_shutdown_requested()
        assert get_shutdown_reason() is not None
    
    def test_reset_shutdown_state(self):
        """Test that shutdown state can be reset (for testing)."""
        request_shutdown("Test")
        assert is_shutdown_requested()
        
        reset_shutdown_state()
        assert not is_shutdown_requested()
        assert get_shutdown_reason() is None


class TestAgentRegistryShutdown:
    """Test that AgentRegistry aborts actions after shutdown."""
    
    def setup_method(self):
        """Reset shutdown state before each test."""
        reset_shutdown_state()
    
    def teardown_method(self):
        """Reset shutdown state after each test."""
        reset_shutdown_state()
    
    @pytest.mark.asyncio
    async def test_execute_async_aborts_after_shutdown(self):
        """Test that execute_async aborts when shutdown is requested."""
        from janus.runtime.core.agent_registry import AgentRegistry
        
        # Create a mock agent
        class MockAgent:
            async def execute(self, action, args, context):
                return {"status": "success", "data": "executed"}
        
        registry = AgentRegistry()
        registry.register("test", MockAgent())
        
        # Request shutdown
        request_shutdown("Test shutdown")
        
        # Try to execute an action
        result = await registry.execute_async("test", "action", {})
        
        # Should abort with error
        assert result["status"] == "error"
        assert "shutdown requested" in result["error"].lower()
        assert result["error_type"] == "shutdown_requested"
    
    @pytest.mark.asyncio
    async def test_execute_async_succeeds_before_shutdown(self):
        """Test that execute_async works normally before shutdown."""
        from janus.runtime.core.agent_registry import AgentRegistry
        
        # Create a mock agent
        class MockAgent:
            async def execute(self, action, args, context):
                return {"status": "success", "data": "executed"}
        
        registry = AgentRegistry()
        registry.register("test", MockAgent())
        
        # Execute action before shutdown
        result = await registry.execute_async("test", "action", {})
        
        # Should succeed
        assert result["status"] == "success"
        assert result["data"] == "executed"


class TestSystemBridgeShutdown:
    """Test that SystemBridge aborts AppleScript after shutdown."""
    
    def setup_method(self):
        """Reset shutdown state before each test."""
        reset_shutdown_state()
    
    def teardown_method(self):
        """Reset shutdown state after each test."""
        reset_shutdown_state()
    
    def test_run_script_aborts_after_shutdown(self):
        """Test that run_script aborts when shutdown is requested."""
        from janus.platform.os.macos_bridge import MacOSBridge
        
        bridge = MacOSBridge()
        
        # Request shutdown
        request_shutdown("Test shutdown")
        
        # Try to run a script
        result = bridge.run_script('tell application "Finder" to activate')
        
        # Should abort with error
        assert result.status.value == "error"
        assert "shutdown requested" in result.error.lower()
    
    def test_run_script_checks_shutdown_before_execution(self):
        """Test that shutdown check happens before executing AppleScript."""
        from janus.platform.os.macos_bridge import MacOSBridge
        
        bridge = MacOSBridge()
        
        # Request shutdown
        request_shutdown("Test shutdown")
        
        # Try to run a potentially harmful script
        # (it should never execute because shutdown is requested)
        result = bridge.run_script('tell application "System Events" to shut down')
        
        # Should abort immediately
        assert result.status.value == "error"
        assert "shutdown requested" in result.error.lower()


class TestCleanupPipeline:
    """Test cleanup_pipeline function."""
    
    def test_cleanup_stops_services(self):
        """Test that cleanup_pipeline stops all services."""
        # This is an integration test that would need a real pipeline
        # For now, just test that cleanup doesn't crash
        from janus.app.initialization import cleanup_pipeline
        
        # Create a mock pipeline with minimal services
        class MockPipeline:
            def __init__(self):
                self.monitor_stopped = False
                self.cleanup_called = False
                
            def stop_monitor(self):
                self.monitor_stopped = True
            
            def cleanup(self):
                self.cleanup_called = True
        
        pipeline = MockPipeline()
        cleanup_pipeline(pipeline)
        
        # Verify services were stopped
        assert pipeline.monitor_stopped
        assert pipeline.cleanup_called
    
    def test_cleanup_handles_missing_services_gracefully(self):
        """Test that cleanup doesn't crash if services are missing."""
        from janus.app.initialization import cleanup_pipeline
        
        # Create a minimal pipeline
        class MinimalPipeline:
            pass
        
        pipeline = MinimalPipeline()
        
        # Should not crash
        cleanup_pipeline(pipeline)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
