"""
Integration test for conversation mode end-to-end flow.

Tests the complete conversation flow:
1. Start conversation
2. Process command
3. Handle clarification
4. Resolve implicit references
5. Complete conversation
"""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from janus.runtime.core import MemoryEngine, Settings, JanusPipeline
from janus.runtime.core.conversation_manager import ConversationManager, ConversationState
from janus.runtime.core.contracts import Intent
from janus.runtime.core.settings import DatabaseSettings


class TestConversationIntegration(unittest.TestCase):
    """Integration tests for conversation mode"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_integration.db"

        # Create memory engine
        db_settings = DatabaseSettings(path=str(self.db_path))
        self.memory = MemoryEngine(db_settings)

        # Create conversation manager
        self.manager = ConversationManager(self.memory)

        # Create test session
        self.session_id = self.memory.create_session()

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_conversation_flow(self):
        """Test complete conversation flow from start to finish"""
        # Step 1: Start conversation
        conversation = self.manager.start_conversation(self.session_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.state, ConversationState.ACTIVE)

        # Step 2: Add first turn
        intent1 = Intent(
            action="open_file",
            confidence=0.9,
            parameters={"file_path": "/home/user/document.txt"},
            raw_command="open document.txt",
        )
        turn1 = self.manager.add_turn(
            conversation.conversation_id, "open document.txt", intent=intent1
        )
        self.assertEqual(turn1.command, "open document.txt")

        # Step 3: Resolve implicit reference in second command
        resolved = self.manager.resolve_implicit_references(
            "save it", conversation.conversation_id
        )
        self.assertIn("document.txt", resolved.lower())

        # Step 4: Add second turn with resolved reference
        intent2 = Intent(
            action="save_file",
            confidence=0.9,
            parameters={"file_path": "/home/user/document.txt"},
            raw_command=resolved,
        )
        turn2 = self.manager.add_turn(
            conversation.conversation_id, resolved, intent=intent2
        )
        self.assertEqual(len(conversation.turns), 2)

        # Step 5: Test clarification flow
        clarification = self.manager.generate_clarification(
            "open chrome", "ambiguous_app", ["Google Chrome", "Chrome Canary"]
        )
        self.assertIsNotNone(clarification)

        # Add turn that needs clarification
        intent3 = Intent(
            action="open_app",
            confidence=0.8,
            parameters={"app_name": "chrome", "needs_clarification": True},
            raw_command="open chrome",
        )
        turn3 = self.manager.add_turn(
            conversation.conversation_id,
            "open chrome",
            intent=intent3,
            clarification=clarification,
            state=ConversationState.NEEDS_CLARIFICATION,
        )
        self.assertEqual(conversation.state, ConversationState.NEEDS_CLARIFICATION)

        # Step 6: Resolve clarification
        success, context = self.manager.resolve_clarification(
            conversation.conversation_id, "1"
        )
        self.assertTrue(success)
        self.assertEqual(context["selected_option"], "Google Chrome")

        # Step 7: Complete conversation
        success = self.manager.complete_conversation(conversation.conversation_id)
        self.assertTrue(success)

        # Step 8: Verify conversation is no longer active
        active_conv = self.manager.get_active_conversation(self.session_id)
        self.assertIsNone(active_conv)

    def test_context_carryover(self):
        """Test that context carries over between turns"""
        conversation = self.manager.start_conversation(self.session_id)

        # Add multiple turns with different entity types
        turns_data = [
            ("open VSCode", Intent(
                action="open_app",
                confidence=0.9,
                parameters={"app_name": "VSCode"},
                raw_command="open VSCode"
            )),
            ("open main.py", Intent(
                action="open_file",
                confidence=0.9,
                parameters={"file_path": "/project/main.py"},
                raw_command="open main.py"
            )),
            ("go to google.com", Intent(
                action="navigate",
                confidence=0.9,
                parameters={"url": "google.com"},
                raw_command="go to google.com"
            )),
        ]

        for command, intent in turns_data:
            self.manager.add_turn(conversation.conversation_id, command, intent=intent)

        # Get context summary
        context = self.manager.get_context_for_command(conversation.conversation_id)

        # Verify all recent entities are tracked
        self.assertEqual(context["turn_count"], 3)
        self.assertIn("VSCode", context["recent_entities"].values())
        self.assertIn("/project/main.py", context["recent_entities"].values())
        self.assertIn("google.com", context["recent_entities"].values())

        # Verify last commands are recorded
        self.assertEqual(len(context["last_commands"]), 3)

    def test_multiple_clarifications(self):
        """Test handling multiple clarifications in sequence"""
        conversation = self.manager.start_conversation(self.session_id)

        # First clarification
        clarif1 = self.manager.generate_clarification(
            "open file", "multiple_files", ["file1.txt", "file2.txt"]
        )
        intent1 = Intent(
            action="open_file",
            confidence=0.8,
            parameters={"needs_clarification": True},
            raw_command="open file"
        )
        self.manager.add_turn(
            conversation.conversation_id,
            "open file",
            intent=intent1,
            clarification=clarif1,
            state=ConversationState.NEEDS_CLARIFICATION,
        )

        # Resolve first clarification
        success1, context1 = self.manager.resolve_clarification(
            conversation.conversation_id, "1"
        )
        self.assertTrue(success1)
        self.assertEqual(context1["selected_option"], "file1.txt")

        # Conversation should be back to active
        self.assertEqual(conversation.state, ConversationState.ACTIVE)

        # Second clarification
        clarif2 = self.manager.generate_clarification(
            "open app", "ambiguous_app", ["App A", "App B"]
        )
        intent2 = Intent(
            action="open_app",
            confidence=0.8,
            parameters={"needs_clarification": True},
            raw_command="open app"
        )
        self.manager.add_turn(
            conversation.conversation_id,
            "open app",
            intent=intent2,
            clarification=clarif2,
            state=ConversationState.NEEDS_CLARIFICATION,
        )

        # Resolve second clarification
        success2, context2 = self.manager.resolve_clarification(
            conversation.conversation_id, "App B"
        )
        self.assertTrue(success2)
        self.assertEqual(context2["selected_option"], "App B")


if __name__ == "__main__":
    unittest.main()
