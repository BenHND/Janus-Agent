"""
Test JanusAgent API (TICKET-AUDIT-003)

This test verifies that the new JanusAgent API works correctly
and provides a single entry point for Janus functionality.
"""

import asyncio
import logging
import pytest

from janus.runtime.core import JanusAgent, execute_command
from janus.runtime.core.contracts import ExecutionResult

logger = logging.getLogger(__name__)


class TestJanusAgentAPI:
    """Test suite for JanusAgent API"""
    
    def test_agent_initialization(self):
        """Test that JanusAgent initializes correctly"""
        agent = JanusAgent()
        
        assert agent is not None
        assert agent.session_id is not None
        assert agent.settings is not None
        assert agent.memory is not None
        
        # Check repr
        repr_str = repr(agent)
        assert "JanusAgent" in repr_str
        assert agent.session_id in repr_str
    
    def test_agent_with_custom_config(self):
        """Test JanusAgent with custom configuration"""
        agent = JanusAgent(
            enable_voice=False,
            enable_llm=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        assert agent is not None
        assert agent._enable_voice is False
        assert agent._enable_llm is True
        assert agent._enable_vision is False
    
    def test_agent_with_language(self):
        """Test JanusAgent with language setting"""
        agent = JanusAgent(language="en")
        
        assert agent.settings.language.default == "en"
    
    def test_agent_availability(self):
        """Test agent availability check"""
        agent = JanusAgent(
            enable_voice=False,
            enable_vision=False,
            enable_llm=True,
        )
        
        # Agent should be available with basic config
        assert agent.available is True
    
    @pytest.mark.asyncio
    async def test_execute_with_mock(self):
        """Test execute method with mock backend"""
        agent = JanusAgent(
            enable_voice=False,
            enable_vision=False,
            enable_llm=True,  # Will use mock backend if real LLM unavailable
        )
        
        try:
            result = await agent.execute("open Calculator")
            
            # Check result structure
            assert isinstance(result, ExecutionResult)
            assert result.session_id == agent.session_id
            assert result.intent is not None
            
            logger.info(f"Test result: success={result.success}, message={result.message}")
        
        finally:
            await agent.cleanup()
    
    @pytest.mark.asyncio
    async def test_execute_with_context_manager(self):
        """Test execute with async context manager"""
        async with JanusAgent(
            enable_voice=False,
            enable_vision=False,
            enable_llm=True,
        ) as agent:
            result = await agent.execute("open Calculator")
            
            assert isinstance(result, ExecutionResult)
            assert result.session_id == agent.session_id
    
    @pytest.mark.asyncio
    async def test_execute_with_request_id(self):
        """Test execute with custom request ID"""
        async with JanusAgent(
            enable_voice=False,
            enable_vision=False,
        ) as agent:
            request_id = "test-request-123"
            result = await agent.execute("open Calculator", request_id=request_id)
            
            assert result.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_execute_with_extra_context(self):
        """Test execute with extra context"""
        async with JanusAgent(
            enable_voice=False,
            enable_vision=False,
        ) as agent:
            result = await agent.execute(
                "send email",
                extra_context={"recipient": "test@example.com"}
            )
            
            assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_execute_invalid_command(self):
        """Test execute with invalid command"""
        async with JanusAgent(
            enable_voice=False,
            enable_vision=False,
        ) as agent:
            # Empty command should raise ValueError
            with pytest.raises(ValueError, match="Command cannot be empty"):
                await agent.execute("")
            
            # Whitespace-only command should raise ValueError
            with pytest.raises(ValueError, match="Command cannot be empty"):
                await agent.execute("   ")
    
    @pytest.mark.asyncio
    async def test_execute_command_convenience(self):
        """Test execute_command convenience function"""
        result = await execute_command(
            "open Calculator",
            enable_voice=False,
            enable_vision=False,
            enable_llm=True,
        )
        
        assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_multiple_commands_same_session(self):
        """Test executing multiple commands in same session"""
        async with JanusAgent(
            enable_voice=False,
            enable_vision=False,
        ) as agent:
            session_id = agent.session_id
            
            # Execute first command
            result1 = await agent.execute("open Calculator")
            assert result1.session_id == session_id
            
            # Execute second command (should use same session)
            result2 = await agent.execute("open Safari")
            assert result2.session_id == session_id
    
    @pytest.mark.asyncio
    async def test_agent_cleanup(self):
        """Test agent cleanup"""
        agent = JanusAgent(
            enable_voice=False,
            enable_vision=False,
        )
        
        # Execute a command
        result = await agent.execute("open Calculator")
        assert isinstance(result, ExecutionResult)
        
        # Cleanup should not raise errors
        await agent.cleanup()
        
        # Should be able to cleanup multiple times
        await agent.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
