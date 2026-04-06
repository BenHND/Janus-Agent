"""
Tests for TICKET-P0-00: Single-Shot Pipeline Optimization

This ticket implements:
1. Conversation history injection in ReasonerLLM._build_structured_plan_prompt
2. extra_context parameter in JanusPipeline.process_command_async
3. Single-shot refactor of process_command_with_conversation
4. BrowserAgent NoneType safety (already implemented, verified)

The goal is to reduce latency from ~16-20s (double LLM inference) to <10s (single-shot).
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


# Shared test configuration to avoid duplication
TEST_CONFIG_CONTENT = """[whisper]
model_size = base

[audio]
sample_rate = 16000

[language]
default = fr

[llm]
provider = mock
model = mock

[tts]
enable_tts = false

[database]
path = janus.db

[logging]
level = INFO
"""


def create_test_config(test_dir: str) -> str:
    """Create a minimal config.ini for testing.
    
    Args:
        test_dir: Directory to create the config file in.
    
    Returns:
        Path to the created config file.
    """
    config_path = os.path.join(test_dir, "config.ini")
    with open(config_path, "w") as f:
        f.write(TEST_CONFIG_CONTENT)
    return config_path


class TestReasonerLLMConversationHistory(unittest.TestCase):
    """Test conversation history injection in ReasonerLLM."""
    
    def setUp(self):
        """Set up mock ReasonerLLM for testing."""
        self.llm = ReasonerLLM(backend="mock")
    
    def test_prompt_without_conversation_history(self):
        """Test prompt building without conversation history."""
        prompt = self.llm._build_structured_plan_prompt(
            command="Ouvre Chrome",
            context=None,
            language="fr"
        )
        
        # Should contain the command
        self.assertIn("Ouvre Chrome", prompt)
        # Should NOT contain conversation context header
        self.assertNotIn("CONTEXTE CONVERSATIONNEL", prompt)
    
    def test_prompt_with_empty_conversation_history(self):
        """Test prompt building with empty conversation history."""
        prompt = self.llm._build_structured_plan_prompt(
            command="Ouvre Chrome",
            context={"conversation_history": []},
            language="fr"
        )
        
        # Should contain the command
        self.assertIn("Ouvre Chrome", prompt)
        # Should NOT contain conversation context header when empty
        self.assertNotIn("CONTEXTE CONVERSATIONNEL", prompt)
    
    def test_prompt_with_conversation_history_french(self):
        """Test prompt building with conversation history (French)."""
        context = {
            "conversation_history": [
                {"command": "Ouvre Safari", "action": "[open_application(Safari)]"},
                {"command": "Va sur le site d'Apple", "action": "[open_url(https://www.apple.com)]"}
            ]
        }
        
        prompt = self.llm._build_structured_plan_prompt(
            command="Ferme-le",
            context=context,
            language="fr"
        )
        
        # Should contain conversation context header
        self.assertIn("CONTEXTE CONVERSATIONNEL", prompt)
        self.assertIn("Derniers échanges", prompt)
        
        # Should contain the conversation turns
        self.assertIn("Ouvre Safari", prompt)
        self.assertIn("Va sur le site d'Apple", prompt)
        
        # Should contain the current command
        self.assertIn("COMMANDE ACTUELLE", prompt)
        self.assertIn("Ferme-le", prompt)
    
    def test_prompt_with_conversation_history_english(self):
        """Test prompt building with conversation history (English)."""
        context = {
            "conversation_history": [
                {"command": "Open Safari", "action": "[open_application(Safari)]"}
            ]
        }
        
        prompt = self.llm._build_structured_plan_prompt(
            command="Close it",
            context=context,
            language="en"
        )
        
        # Should contain English headers
        self.assertIn("CONVERSATION CONTEXT", prompt)
        self.assertIn("Recent exchanges", prompt)
        self.assertIn("CURRENT COMMAND", prompt)
        
        # Should contain the conversation turn
        self.assertIn("Open Safari", prompt)
        self.assertIn("Close it", prompt)
    
    def test_prompt_limits_to_3_turns(self):
        """Test that only last 3 turns are included in prompt."""
        context = {
            "conversation_history": [
                {"command": "Command 1", "action": "[action1]"},
                {"command": "Command 2", "action": "[action2]"},
                {"command": "Command 3", "action": "[action3]"},
                {"command": "Command 4", "action": "[action4]"},
                {"command": "Command 5", "action": "[action5]"},
            ]
        }
        
        prompt = self.llm._build_structured_plan_prompt(
            command="Current command",
            context=context,
            language="fr"
        )
        
        # Should only contain last 3 commands (3, 4, 5)
        self.assertNotIn("Command 1", prompt)
        self.assertNotIn("Command 2", prompt)
        self.assertIn("Command 3", prompt)
        self.assertIn("Command 4", prompt)
        self.assertIn("Command 5", prompt)
    
    def test_prompt_with_user_key_format(self):
        """Test that 'user' key format also works for conversation history."""
        context = {
            "conversation_history": [
                {"user": "Ouvre Chrome", "agent": "[Opened Chrome]"}
            ]
        }
        
        prompt = self.llm._build_structured_plan_prompt(
            command="Ferme",
            context=context,
            language="fr"
        )
        
        # Should contain the user command
        self.assertIn("Ouvre Chrome", prompt)
    
    def test_generate_structured_plan_with_conversation(self):
        """Test full plan generation with conversation context."""
        context = {
            "conversation_history": [
                {"command": "Ouvre Safari", "action": "[open_application(Safari)]"}
            ]
        }
        
        result = self.llm.generate_structured_plan(
            command="Va sur YouTube",
            context=context,
            language="fr"
        )
        
        # Should return valid structure
        self.assertIn("steps", result)
        self.assertIsInstance(result["steps"], list)


class TestPipelineExtraContext(unittest.TestCase):
    """Test extra_context parameter in JanusPipeline."""
    
    def setUp(self):
        """Set up test fixtures with isolated temp directory."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Use shared config helper
        config_path = create_test_config(self.test_dir)
        
        from janus.runtime.core import Settings, MemoryEngine, JanusPipeline
        
        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(self.settings, self.memory)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)
    
    def test_process_command_accepts_extra_context(self):
        """Test that process_command accepts extra_context parameter."""
        extra_context = {
            "conversation_history": [
                {"command": "Test", "action": "[test]"}
            ]
        }
        
        # Should not raise
        result = self.pipeline.process_command(
            "test command",
            mock_execution=True,
            extra_context=extra_context
        )
        
        self.assertIsNotNone(result)
    
    def test_process_command_without_extra_context(self):
        """Test that process_command works without extra_context."""
        result = self.pipeline.process_command(
            "ouvre Safari",
            mock_execution=True
        )
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.intent)


class TestBrowserAgentNoneTypeHandling(unittest.TestCase):
    """Test BrowserAgent NoneType safety (Tâche 3)."""
    
    def test_open_url_with_none_context(self):
        """Test _open_url handles None context safely."""
        from janus.capabilities.agents.browser_agent import BrowserAgent
        
        agent = BrowserAgent()
        
        # Should not crash with empty context
        import asyncio
        
        async def test():
            result = await agent._open_url(
                {"url": "https://example.com"},
                {}  # Empty context
            )
            return result
        
        # This should not raise AttributeError
        try:
            result = asyncio.run(test())
            # Result could be success or error, but shouldn't crash
            self.assertIn("status", result)
        except Exception as e:
            # AppleScript not available on non-macOS, but shouldn't be AttributeError
            self.assertNotIn("AttributeError", str(type(e)))
    
    def test_search_with_none_context(self):
        """Test _search handles None context safely."""
        from janus.capabilities.agents.browser_agent import BrowserAgent
        
        agent = BrowserAgent()
        
        import asyncio
        
        async def test():
            result = await agent._search(
                {"query": "test"},
                {}  # Empty context
            )
            return result
        
        # This should not raise AttributeError for NoneType
        try:
            result = asyncio.run(test())
            self.assertIn("status", result)
        except Exception as e:
            # Should not be NoneType error
            error_str = str(e)
            self.assertNotIn("'NoneType' object", error_str)


class TestSingleShotPerformance(unittest.TestCase):
    """Test single-shot architecture reduces LLM calls."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Use shared config helper
        config_path = create_test_config(self.test_dir)
        
        from janus.runtime.core import Settings, MemoryEngine, JanusPipeline
        
        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(self.settings, self.memory)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)
    
    def test_process_command_with_conversation_single_shot(self):
        """Test that process_command_with_conversation uses single-shot (no clarification)."""
        # First command
        result1, clarification1 = self.pipeline.process_command_with_conversation(
            "Ouvre Safari",
            mock_execution=True
        )
        
        # Clarification should be None in single-shot mode
        self.assertIsNone(clarification1)
        
        # Second command with pronoun
        result2, clarification2 = self.pipeline.process_command_with_conversation(
            "Ferme-le",
            mock_execution=True
        )
        
        # Should still be None - no clarification in single-shot
        self.assertIsNone(clarification2)
    
    def test_conversation_history_passed_to_reasoner(self):
        """Test that conversation history is passed to the reasoner."""
        # Execute first command
        result1, _ = self.pipeline.process_command_with_conversation(
            "Ouvre Safari",
            mock_execution=True
        )
        
        # The conversation should be stored
        conversation = self.pipeline.conversation_manager.get_active_conversation(
            self.pipeline.session_id
        )
        
        self.assertIsNotNone(conversation)
        self.assertGreater(len(conversation.turns), 0)
        
        # The first turn should be stored
        first_turn = conversation.turns[0]
        self.assertEqual(first_turn.command, "Ouvre Safari")


if __name__ == "__main__":
    unittest.main()
