"""
TICKET-404: Test for Missing Info Feedback Loop

Tests that the pipeline correctly handles cases where the Reasoner
detects missing information and provides appropriate TTS feedback.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import Settings
from janus.runtime.core import MemoryEngine


@pytest.fixture
def mock_settings():
    """Create mock settings for testing"""
    # Create nested mock objects
    settings = MagicMock(spec=Settings)
    settings.llm = MagicMock()
    settings.llm.provider = "mock"
    settings.llm.model = "mock"
    settings.language = MagicMock()
    settings.language.default = "fr"
    settings.execution = MagicMock()
    settings.execution.enable_vision_recovery = False
    settings.execution.enable_replanning = False
    settings.execution.max_retries = 1
    settings.async_vision_monitor = MagicMock()
    settings.async_vision_monitor.enable_monitor = False
    return settings


@pytest.fixture
def mock_memory():
    """Create mock memory service"""
    memory = MagicMock(spec=MemoryEngine)
    memory.create_session.return_value = "test-session-123"
    memory.log_structured = MagicMock()
    memory.store_command = MagicMock()
    memory.store_context = MagicMock()
    memory.get_command_history.return_value = []
    return memory


@pytest.fixture
def pipeline(mock_settings, mock_memory):
    """Create pipeline with mocked dependencies"""
    pipeline = JanusPipeline(
        settings=mock_settings,
        memory=mock_memory,
        enable_voice=False,
        enable_llm_reasoning=True,
        enable_vision=False,
        enable_learning=False,
        enable_tts=False,  # Will be mocked separately in tests
    )
    return pipeline


@pytest.mark.asyncio
async def test_missing_info_detection_no_tts():
    """
    Test that missing info is detected and appropriate result is returned
    without TTS (TTS disabled)
    """
    # Arrange
    mock_settings = MagicMock(spec=Settings)
    mock_settings.llm = MagicMock()
    mock_settings.llm.provider = "mock"
    mock_settings.llm.model = "mock"
    mock_settings.language = MagicMock()
    mock_settings.language.default = "fr"
    mock_settings.execution = MagicMock()
    mock_settings.execution.enable_vision_recovery = False
    mock_settings.execution.enable_replanning = False
    mock_settings.execution.max_retries = 1
    mock_settings.async_vision_monitor = MagicMock()
    mock_settings.async_vision_monitor.enable_monitor = False
    
    mock_memory = MagicMock(spec=MemoryEngine)
    mock_memory.create_session.return_value = "test-session-123"
    mock_memory.log_structured = MagicMock()
    mock_memory.store_command = MagicMock()
    mock_memory.store_context = MagicMock()
    mock_memory.get_command_history.return_value = []
    
    # Mock get_active_context to return empty dict (avoid platform-specific issues)
    with patch('janus.os.system_info.get_active_context', return_value={}):
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock the reasoner to return missing info
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {
            "steps": [],
            "missing_info": ["recipient", "message"]
        }
        pipeline._reasoner_llm = mock_reasoner
        
        # Mock semantic router
        mock_semantic_router = MagicMock()
        mock_semantic_router.classify_intent.return_value = "ACTION"
        pipeline._semantic_router = mock_semantic_router
        
        # Mock context router
        mock_context_router = MagicMock()
        mock_context_router.get_requirements.return_value = []
        pipeline._context_router = mock_context_router
        
        # Act
        result = await pipeline.process_command_async("Envoie un message sur Slack")
        
        # Assert
        assert result.success is False
        assert result.intent.action == "clarification_needed"
        assert "missing_info" in result.intent.parameters
        assert result.intent.parameters["missing_info"] == ["recipient", "message"]
        # Check for i18n message format
        assert "Je ne peux pas exécuter la demande" in result.message
        assert "recipient, message" in result.message
        print(f"✓ Missing info detected correctly: {result.message}")


@pytest.mark.asyncio
async def test_missing_info_with_tts_async():
    """
    Test that missing info triggers TTS feedback (async TTS)
    """
    # Arrange
    mock_settings = MagicMock(spec=Settings)
    mock_settings.llm = MagicMock()
    mock_settings.llm.provider = "mock"
    mock_settings.llm.model = "mock"
    mock_settings.language = MagicMock()
    mock_settings.language.default = "fr"
    mock_settings.execution = MagicMock()
    mock_settings.execution.enable_vision_recovery = False
    mock_settings.execution.enable_replanning = False
    mock_settings.execution.max_retries = 1
    mock_settings.async_vision_monitor = MagicMock()
    mock_settings.async_vision_monitor.enable_monitor = False
    mock_settings.tts = MagicMock()
    mock_settings.tts.voice = None
    mock_settings.tts.rate = 200
    mock_settings.tts.volume = 1.0
    mock_settings.tts.lang = "fr"
    
    mock_memory = MagicMock(spec=MemoryEngine)
    mock_memory.create_session.return_value = "test-session-123"
    mock_memory.log_structured = MagicMock()
    mock_memory.store_command = MagicMock()
    mock_memory.store_context = MagicMock()
    mock_memory.get_command_history.return_value = []
    
    # Mock get_active_context to avoid platform-specific issues
    with patch('janus.os.system_info.get_active_context', return_value={}):
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=True,
        )
        
        # Mock TTS with async speak
        mock_tts = MagicMock()
        mock_tts.speak = AsyncMock()  # Async TTS
        pipeline._tts = mock_tts
        
        # Mock the reasoner to return missing info
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {
            "steps": [],
            "missing_info": ["destinataire", "message"]
        }
        pipeline._reasoner_llm = mock_reasoner
        
        # Mock semantic router
        mock_semantic_router = MagicMock()
        mock_semantic_router.classify_intent.return_value = "ACTION"
        pipeline._semantic_router = mock_semantic_router
        
        # Mock context router
        mock_context_router = MagicMock()
        mock_context_router.get_requirements.return_value = []
        pipeline._context_router = mock_context_router
        
        # Act
        result = await pipeline.process_command_async("Envoie un message sur Slack")
        
        # Assert
        assert result.success is False
        assert result.intent.action == "clarification_needed"
        
        # Verify TTS was called with the correct message (i18n format)
        mock_tts.speak.assert_called_once()
        args, kwargs = mock_tts.speak.call_args
        assert "Je ne peux pas exécuter la demande" in args[0]
        assert "destinataire, message" in args[0]
        print(f"✓ TTS feedback provided: {args[0]}")


@pytest.mark.asyncio
async def test_missing_info_with_tts_sync():
    """
    Test that missing info triggers TTS feedback (sync TTS)
    """
    # Arrange
    mock_settings = MagicMock(spec=Settings)
    mock_settings.llm = MagicMock()
    mock_settings.llm.provider = "mock"
    mock_settings.llm.model = "mock"
    mock_settings.language = MagicMock()
    mock_settings.language.default = "fr"
    mock_settings.execution = MagicMock()
    mock_settings.execution.enable_vision_recovery = False
    mock_settings.execution.enable_replanning = False
    mock_settings.execution.max_retries = 1
    mock_settings.async_vision_monitor = MagicMock()
    mock_settings.async_vision_monitor.enable_monitor = False
    mock_settings.tts = MagicMock()
    mock_settings.tts.voice = None
    mock_settings.tts.rate = 200
    mock_settings.tts.volume = 1.0
    mock_settings.tts.lang = "fr"
    
    mock_memory = MagicMock(spec=MemoryEngine)
    mock_memory.create_session.return_value = "test-session-123"
    mock_memory.log_structured = MagicMock()
    mock_memory.store_command = MagicMock()
    mock_memory.store_context = MagicMock()
    mock_memory.get_command_history.return_value = []
    
    # Mock get_active_context to avoid platform-specific issues
    with patch('janus.os.system_info.get_active_context', return_value={}):
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=True,
        )
        
        # Mock TTS with sync speak
        mock_tts = MagicMock()
        mock_tts.speak = MagicMock()  # Sync TTS
        pipeline._tts = mock_tts
        
        # Mock the reasoner to return missing info
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {
            "steps": [],
            "missing_info": ["destinataire"]
        }
        pipeline._reasoner_llm = mock_reasoner
        
        # Mock semantic router
        mock_semantic_router = MagicMock()
        mock_semantic_router.classify_intent.return_value = "ACTION"
        pipeline._semantic_router = mock_semantic_router
        
        # Mock context router
        mock_context_router = MagicMock()
        mock_context_router.get_requirements.return_value = []
        pipeline._context_router = mock_context_router
        
        # Act
        result = await pipeline.process_command_async("Envoie un message")
        
        # Assert
        assert result.success is False
        assert result.intent.action == "clarification_needed"
        
        # Verify TTS was called with the correct message (i18n format)
        mock_tts.speak.assert_called_once()
        args, kwargs = mock_tts.speak.call_args
        assert "Je ne peux pas exécuter la demande" in args[0]
        assert "destinataire" in args[0]
        print(f"✓ TTS feedback provided (sync): {args[0]}")


@pytest.mark.asyncio
async def test_no_missing_info_executes_normally():
    """
    Test that commands with all required info execute normally
    """
    # Arrange
    mock_settings = MagicMock(spec=Settings)
    mock_settings.llm = MagicMock()
    mock_settings.llm.provider = "mock"
    mock_settings.llm.model = "mock"
    mock_settings.language = MagicMock()
    mock_settings.language.default = "fr"
    mock_settings.execution = MagicMock()
    mock_settings.execution.enable_vision_recovery = False
    mock_settings.execution.enable_replanning = False
    mock_settings.execution.max_retries = 1
    mock_settings.async_vision_monitor = MagicMock()
    mock_settings.async_vision_monitor.enable_monitor = False
    
    mock_memory = MagicMock(spec=MemoryEngine)
    mock_memory.create_session.return_value = "test-session-123"
    mock_memory.log_structured = MagicMock()
    mock_memory.store_command = MagicMock()
    mock_memory.store_context = MagicMock()
    mock_memory.log_execution = MagicMock()
    mock_memory.get_command_history.return_value = []
    
    # Mock get_active_context to avoid platform-specific issues
    with patch('janus.os.system_info.get_active_context', return_value={}):
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=True,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock the reasoner to return a valid plan (no missing info)
        mock_reasoner = MagicMock()
        mock_reasoner.generate_structured_plan.return_value = {
            "steps": [
                {
                    "module": "slack",
                    "action": "send_message",
                    "args": {
                        "recipient": "john",
                        "message": "Hello"
                    }
                }
            ],
            "missing_info": []  # No missing info
        }
        pipeline._reasoner_llm = mock_reasoner
        
        # Mock semantic router
        mock_semantic_router = MagicMock()
        mock_semantic_router.classify_intent.return_value = "ACTION"
        pipeline._semantic_router = mock_semantic_router
        
        # Mock context router
        mock_context_router = MagicMock()
        mock_context_router.get_requirements.return_value = []
        pipeline._context_router = mock_context_router
        
        # Mock validator
        from janus.safety.validation.json_plan_validator import ValidationResult
        mock_validator = MagicMock()
        valid_plan = {
            "steps": [
                {
                    "module": "slack",
                    "action": "send_message",
                    "args": {
                        "recipient": "john",
                        "message": "Hello"
                    }
                }
            ]
        }
        mock_validator.validate_plan.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            plan=valid_plan
        )
        pipeline._validator_v3 = mock_validator
        
        # Mock agent executor
        from janus.runtime.core.contracts import ExecutionResult, Intent
        mock_executor = MagicMock()
        exec_intent = Intent(action="slack.send_message", confidence=1.0, raw_command="")
        mock_executor.execute_plan = AsyncMock(return_value=ExecutionResult(
            success=True,
            intent=exec_intent,
            session_id="test-session-123",
            request_id="test-req-123",
            message="Message sent successfully"
        ))
        pipeline._agent_executor_v3 = mock_executor
        
        # Act
        result = await pipeline.process_command_async("Envoie un message à John avec le texte Hello")
        
        # Assert
        # Should proceed to execution, not return clarification
        assert result.intent.action != "clarification_needed"
        # Note: In this mocked scenario, execution will happen
        print(f"✓ Command with complete info executes normally")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_missing_info_detection_no_tts())
    asyncio.run(test_missing_info_with_tts_async())
    asyncio.run(test_missing_info_with_tts_sync())
    asyncio.run(test_no_missing_info_executes_normally())
    print("\n✓ All TICKET-404 tests passed!")
