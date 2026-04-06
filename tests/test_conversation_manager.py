"""
Tests for ConversationManager - Multi-turn dialogue management.

Tests cover:
- Conversation lifecycle (create, update, complete)
- Turn management
- Clarification questions
- Context carryover
- Implicit reference resolution
"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from janus.runtime.core.contracts import ActionResult, ExecutionResult, Intent
from janus.runtime.core.conversation_manager import (
    ClarificationQuestion,
    Conversation,
    ConversationManager,
    ConversationState,
    ConversationTurn,
)
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


class TestConversationManager(unittest.TestCase):
    """Test conversation manager functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_conversation.db"

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

    def test_start_conversation(self):
        """Test starting a new conversation"""
        conversation = self.manager.start_conversation(self.session_id)

        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.session_id, self.session_id)
        self.assertEqual(conversation.state, ConversationState.ACTIVE)
        self.assertEqual(len(conversation.turns), 0)

    def test_get_active_conversation(self):
        """Test retrieving active conversation"""
        # Start a conversation
        conv1 = self.manager.start_conversation(self.session_id)

        # Retrieve it
        conv2 = self.manager.get_active_conversation(self.session_id)

        self.assertIsNotNone(conv2)
        self.assertEqual(conv1.conversation_id, conv2.conversation_id)
        self.assertEqual(conv2.state, ConversationState.ACTIVE)

    def test_add_turn(self):
        """Test adding a turn to a conversation"""
        conversation = self.manager.start_conversation(self.session_id)

        intent = Intent(
            action="open_app",
            confidence=0.95,
            parameters={"app_name": "Chrome"},
            raw_command="ouvre chrome",
        )

        turn = self.manager.add_turn(conversation.conversation_id, "ouvre chrome", intent=intent)

        self.assertIsNotNone(turn)
        self.assertEqual(turn.command, "ouvre chrome")
        self.assertEqual(turn.intent.action, "open_app")
        self.assertEqual(turn.state, ConversationState.ACTIVE)

        # Verify turn was added to conversation
        conv = self.manager.get_active_conversation(self.session_id)
        self.assertEqual(len(conv.turns), 1)
        self.assertEqual(conv.turns[0].command, "ouvre chrome")

    def test_generate_clarification(self):
        """Test generating clarification questions"""
        question = self.manager.generate_clarification(
            "open file",
            "multiple_files",
            ["file1.txt", "file2.txt", "file3.txt"],
            {"directory": "/home/user"},
        )

        self.assertIsNotNone(question)
        self.assertIn("plusieurs fichiers", question.question.lower())
        self.assertEqual(len(question.options), 3)
        self.assertIn("file1.txt", question.options)
        self.assertEqual(question.context["directory"], "/home/user")

    def test_resolve_clarification_numeric(self):
        """Test resolving clarification with numeric selection"""
        # Start conversation with clarification
        conversation = self.manager.start_conversation(self.session_id)

        clarification = ClarificationQuestion(
            question="Which file?", options=["file1.txt", "file2.txt", "file3.txt"], context={}
        )

        intent = Intent(
            action="open_file",
            confidence=0.8,
            parameters={"file_path": "*.txt"},
            raw_command="open file",
        )

        self.manager.add_turn(
            conversation.conversation_id,
            "open file",
            intent=intent,
            clarification=clarification,
            state=ConversationState.NEEDS_CLARIFICATION,
        )

        # Resolve with numeric selection
        success, context = self.manager.resolve_clarification(conversation.conversation_id, "2")

        self.assertTrue(success)
        self.assertEqual(context["selected_option"], "file2.txt")
        self.assertEqual(context["original_command"], "open file")

        # Verify conversation state updated
        conv = self.manager.get_active_conversation(self.session_id)
        self.assertEqual(conv.state, ConversationState.ACTIVE)

    def test_resolve_clarification_text(self):
        """Test resolving clarification with text match"""
        # Start conversation with clarification
        conversation = self.manager.start_conversation(self.session_id)

        clarification = ClarificationQuestion(
            question="Which app?",
            options=["Google Chrome", "Chrome Canary", "Chromium"],
            context={},
        )

        intent = Intent(
            action="open_app",
            confidence=0.8,
            parameters={"app_name": "chrome"},
            raw_command="open chrome",
        )

        self.manager.add_turn(
            conversation.conversation_id,
            "open chrome",
            intent=intent,
            clarification=clarification,
            state=ConversationState.NEEDS_CLARIFICATION,
        )

        # Resolve with text match
        success, context = self.manager.resolve_clarification(
            conversation.conversation_id, "Google Chrome"
        )

        self.assertTrue(success)
        self.assertEqual(context["selected_option"], "Google Chrome")

    def test_get_context_summary(self):
        """Test getting conversation context summary"""
        conversation = self.manager.start_conversation(self.session_id)

        # Add several turns
        intents = [
            Intent(
                action="open_app",
                confidence=0.9,
                parameters={"app_name": "Chrome"},
                raw_command="ouvre chrome",
            ),
            Intent(
                action="open_file",
                confidence=0.9,
                parameters={"file_path": "/test.txt"},
                raw_command="ouvre test.txt",
            ),
            Intent(
                action="copy",
                confidence=0.9,
                parameters={"target": "button"},
                raw_command="copie button",
            ),
        ]

        for intent in intents:
            self.manager.add_turn(conversation.conversation_id, intent.raw_command, intent=intent)

        # Get context summary
        summary = self.manager.get_context_for_command(conversation.conversation_id)

        self.assertEqual(summary["turn_count"], 3)
        self.assertEqual(summary["state"], "active")
        self.assertEqual(len(summary["last_commands"]), 3)

        # Check recent entities
        entities = summary["recent_entities"]
        self.assertEqual(entities["app_name"], "Chrome")
        self.assertEqual(entities["file_path"], "/test.txt")
        self.assertEqual(entities["target"], "button")

    def test_resolve_implicit_references(self):
        """Test resolving implicit references using context"""
        conversation = self.manager.start_conversation(self.session_id)

        # Add turn with file reference
        intent = Intent(
            action="open_file",
            confidence=0.9,
            parameters={"file_path": "/home/user/document.txt"},
            raw_command="ouvre document.txt",
        )

        self.manager.add_turn(conversation.conversation_id, "ouvre document.txt", intent=intent)

        # Try to resolve "close it"
        resolved = self.manager.resolve_implicit_references(
            "close it", conversation.conversation_id
        )

        self.assertIn("document.txt", resolved.lower())

    def test_complete_conversation(self):
        """Test completing a conversation"""
        conversation = self.manager.start_conversation(self.session_id)

        # Add a turn
        self.manager.add_turn(
            conversation.conversation_id,
            "test command",
            intent=Intent(action="test", confidence=1.0, raw_command="test"),
        )

        # Complete conversation
        self.manager.complete_conversation(conversation.conversation_id)

        # Verify it's no longer active
        active_conv = self.manager.get_active_conversation(self.session_id)
        self.assertIsNone(active_conv)

    def test_multi_turn_conversation(self):
        """Test a complete multi-turn conversation scenario"""
        # Turn 1: Open app
        conv = self.manager.start_conversation(self.session_id)

        intent1 = Intent(
            action="open_app",
            confidence=0.9,
            parameters={"app_name": "VSCode"},
            raw_command="open vscode",
        )

        self.manager.add_turn(conv.conversation_id, "open vscode", intent=intent1)

        # Turn 2: Open file (with implicit reference later)
        intent2 = Intent(
            action="open_file",
            confidence=0.9,
            parameters={"file_path": "/project/main.py"},
            raw_command="open main.py",
        )

        self.manager.add_turn(conv.conversation_id, "open main.py", intent=intent2)

        # Turn 3: Save it (implicit reference)
        resolved = self.manager.resolve_implicit_references("save it", conv.conversation_id)

        # Should resolve "it" to the file
        self.assertIn("main.py", resolved)

        # Get context summary
        summary = self.manager.get_context_for_command(conv.conversation_id)
        self.assertEqual(summary["turn_count"], 2)
        self.assertIn("main.py", summary["last_commands"][-1])

    def test_persistence(self):
        """Test that conversations are persisted to database"""
        # Create conversation and add turns
        conv = self.manager.start_conversation(self.session_id)

        intent = Intent(
            action="test", confidence=1.0, parameters={"test": "value"}, raw_command="test command"
        )

        self.manager.add_turn(conv.conversation_id, "test command", intent=intent)

        # Create new manager with same database
        new_manager = ConversationManager(self.memory)

        # Retrieve conversation
        loaded_conv = new_manager.get_active_conversation(self.session_id)

        self.assertIsNotNone(loaded_conv)
        self.assertEqual(loaded_conv.conversation_id, conv.conversation_id)
        self.assertEqual(len(loaded_conv.turns), 1)
        self.assertEqual(loaded_conv.turns[0].command, "test command")

    def test_clarification_with_ambiguous_app(self):
        """Test clarification for ambiguous app names"""
        conv = self.manager.start_conversation(self.session_id)

        clarification = self.manager.generate_clarification(
            "open chrome", "ambiguous_app", ["Google Chrome", "Chrome Canary", "Chromium"]
        )

        self.assertIn("plusieurs applications", clarification.question.lower())
        self.assertEqual(len(clarification.options), 3)

    def test_empty_clarification_resolution(self):
        """Test that resolving without clarification fails gracefully"""
        conv = self.manager.start_conversation(self.session_id)

        # Add normal turn (no clarification)
        intent = Intent(action="test", confidence=1.0, raw_command="test")
        self.manager.add_turn(conv.conversation_id, "test", intent=intent)

        # Try to resolve clarification
        success, context = self.manager.resolve_clarification(conv.conversation_id, "some response")

        self.assertFalse(success)
        self.assertIsNone(context)


if __name__ == "__main__":
    unittest.main()
