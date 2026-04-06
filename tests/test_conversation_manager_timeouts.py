"""
Tests for ConversationManager timeout and end_conversation features (TICKET A6)

Tests cover:
- Timeout handling with wait_for_response
- End conversation with reason tracking
- Response callbacks
"""
import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from janus.runtime.core.contracts import Intent
from janus.runtime.core.conversation_manager import (
    ClarificationQuestion,
    Conversation,
    ConversationManager,
    ConversationState,
    ConversationTurn,
)
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


class TestConversationManagerTimeouts(unittest.TestCase):
    """Test conversation manager timeout features"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_conversation_timeout.db"

        # Create memory service
        db_settings = DatabaseSettings(path=str(self.db_path))
        self.memory = MemoryEngine(db_settings)

        # Create conversation manager
        self.manager = ConversationManager(self.memory)

        # Create test session
        self.session_id = self.memory.create_session()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_conversation_with_reason(self):
        """Test ending conversation with specific reason"""
        # Start a conversation
        conversation = self.manager.start_conversation(self.session_id)
        conv_id = conversation.conversation_id

        # End with reason
        self.manager.end_conversation(conv_id, reason="timeout")

        # Verify conversation is no longer active
        active = self.manager.get_active_conversation(self.session_id)
        self.assertIsNone(active)

        # Verify reason was saved
        loaded_conv = self.manager._load_conversation(conv_id)
        self.assertIsNotNone(loaded_conv)
        self.assertEqual(loaded_conv.state, ConversationState.COMPLETED)
        self.assertEqual(loaded_conv.end_reason, "timeout")

    def test_complete_conversation_default_reason(self):
        """Test completing conversation with default reason"""
        conversation = self.manager.start_conversation(self.session_id)
        conv_id = conversation.conversation_id

        # Complete without explicit reason
        self.manager.complete_conversation(conv_id)

        # Verify default reason
        loaded_conv = self.manager._load_conversation(conv_id)
        self.assertEqual(loaded_conv.end_reason, "completion")

    def test_wait_for_response_timeout(self):
        """Test wait_for_response timeout behavior"""
        conversation = self.manager.start_conversation(self.session_id)
        conv_id = conversation.conversation_id

        question = ClarificationQuestion(
            question="Test question?", options=["Option 1", "Option 2"]
        )

        # Create a callback that never returns
        async def slow_callback():
            await asyncio.sleep(10)  # Longer than timeout
            return "response"

        # Test timeout (use short timeout for testing)
        async def run_test():
            result = await self.manager.wait_for_response(
                conv_id, question, timeout=0.5, response_callback=slow_callback  # 500ms timeout
            )
            return result

        # Run the test
        result = asyncio.run(run_test())

        # Should return None due to timeout
        self.assertIsNone(result)

        # Conversation should be ended
        active = self.manager.get_active_conversation(self.session_id)
        self.assertIsNone(active)

        # Verify timeout reason
        loaded_conv = self.manager._load_conversation(conv_id)
        self.assertEqual(loaded_conv.end_reason, "timeout")

    def test_wait_for_response_success(self):
        """Test wait_for_response with successful response"""
        conversation = self.manager.start_conversation(self.session_id)
        conv_id = conversation.conversation_id

        question = ClarificationQuestion(
            question="Test question?", options=["Option 1", "Option 2"]
        )

        # Create a callback that returns quickly
        async def quick_callback():
            await asyncio.sleep(0.1)
            return "Option 1"

        # Test successful response
        async def run_test():
            result = await self.manager.wait_for_response(
                conv_id, question, timeout=2, response_callback=quick_callback
            )
            return result

        # Run the test
        result = asyncio.run(run_test())

        # Should return the response
        self.assertEqual(result, "Option 1")

        # Conversation should still be active
        active = self.manager.get_active_conversation(self.session_id)
        self.assertIsNotNone(active)
        self.assertEqual(active.conversation_id, conv_id)

    def test_end_reason_persistence(self):
        """Test that end reason is properly persisted and loaded"""
        conversation = self.manager.start_conversation(self.session_id)
        conv_id = conversation.conversation_id

        # Add some turns
        self.manager.add_turn(
            conv_id,
            "test command",
            intent=Intent(
                action="test_action", confidence=0.9, parameters={}, raw_command="test command"
            ),
        )

        # End with custom reason
        self.manager.end_conversation(conv_id, reason="user_cancel")

        # Create new manager and load conversation
        manager2 = ConversationManager(self.memory)
        loaded_conv = manager2._load_conversation(conv_id)

        # Verify end reason survived reload
        self.assertIsNotNone(loaded_conv)
        self.assertEqual(loaded_conv.end_reason, "user_cancel")
        self.assertEqual(loaded_conv.state, ConversationState.COMPLETED)
        self.assertEqual(len(loaded_conv.turns), 1)

    def test_multiple_end_reasons(self):
        """Test different end reasons are tracked correctly"""
        reasons_to_test = ["timeout", "user_cancel", "error", "completion"]
        conv_ids = []

        for reason in reasons_to_test:
            conv = self.manager.start_conversation(self.session_id)
            conv_ids.append(conv.conversation_id)
            self.manager.end_conversation(conv.conversation_id, reason=reason)

        # Verify all reasons were saved correctly
        for conv_id, expected_reason in zip(conv_ids, reasons_to_test):
            loaded = self.manager._load_conversation(conv_id)
            self.assertEqual(loaded.end_reason, expected_reason)


if __name__ == "__main__":
    unittest.main()
