"""
Integration tests for multi-session memory features

Tests:
- Session listing and details
- Session search
- Session export/import
- Session analytics
- Cross-session context loading
- Related session finding
"""
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from janus.runtime.core.contracts import Intent
from janus.runtime.core import MemoryEngine
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core.settings import DatabaseSettings, Settings


class TestMultiSessionMemory(unittest.TestCase):
    """Test multi-session memory features"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_memory.db"

        # Create test settings
        db_settings = DatabaseSettings(path=str(self.db_path), enable_wal=True)

        # Create memory service
        self.memory = MemoryEngine(db_settings)

        # Create test sessions with data
        self.session1_id = self.memory.create_session()
        self.session2_id = self.memory.create_session()
        self.session3_id = self.memory.create_session()

        # Add commands to sessions
        self._populate_test_data()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _populate_test_data(self):
        """Populate test sessions with sample data"""
        # Session 1: Chrome-focused session
        for i in range(5):
            self.memory.store_command(
                session_id=self.session1_id,
                request_id=f"req1_{i}",
                raw_command=f"open chrome tab {i}",
                intent=Intent(
                    action="navigate_url",
                    confidence=0.95,
                    parameters={"url": f"http://example{i}.com"},
                    raw_command=f"open chrome tab {i}",
                ),
            )

            self.memory.log_execution(
                session_id=self.session1_id,
                request_id=f"req1_{i}",
                action="navigate_url",
                status="success",
                message="Navigated successfully",
                duration_ms=100 + i * 10,
            )

        # Session 2: App opening session
        for i in range(3):
            self.memory.store_command(
                session_id=self.session2_id,
                request_id=f"req2_{i}",
                raw_command=f"open application {i}",
                intent=Intent(
                    action="open_app",
                    confidence=0.9,
                    parameters={"app_name": f"App{i}"},
                    raw_command=f"open application {i}",
                ),
            )

            self.memory.log_execution(
                session_id=self.session2_id,
                request_id=f"req2_{i}",
                action="open_app",
                status="success",
                message="App opened",
                duration_ms=150,
            )

        # Session 3: Mixed commands
        commands = [
            ("open chrome", "navigate_url", {"url": "http://example.com"}),
            ("send message", "send_message", {"recipient": "John"}),
            ("open vscode", "open_app", {"app_name": "VSCode"}),
        ]

        for i, (cmd, intent_action, params) in enumerate(commands):
            self.memory.store_command(
                session_id=self.session3_id,
                request_id=f"req3_{i}",
                raw_command=cmd,
                intent=Intent(
                    action=intent_action, confidence=0.92, parameters=params, raw_command=cmd
                ),
            )

            self.memory.log_execution(
                session_id=self.session3_id,
                request_id=f"req3_{i}",
                action=intent_action,
                status="success",
                message="Executed",
                duration_ms=120,
            )

    def test_list_all_sessions(self):
        """Test listing all sessions"""
        sessions = self.memory.list_all_sessions(limit=100)

        self.assertGreaterEqual(len(sessions), 3)

        # Check that our test sessions are in the list
        session_ids = [s["session_id"] for s in sessions]
        self.assertIn(self.session1_id, session_ids)
        self.assertIn(self.session2_id, session_ids)
        self.assertIn(self.session3_id, session_ids)

        # Check that sessions have expected fields
        for session in sessions:
            self.assertIn("session_id", session)
            self.assertIn("created_at", session)
            self.assertIn("last_accessed", session)
            self.assertIn("command_count", session)
            self.assertIn("execution_count", session)

    def test_get_session_details(self):
        """Test getting detailed session information"""
        details = self.memory.get_session_details(self.session1_id)

        self.assertIsNotNone(details)
        self.assertEqual(details["session_id"], self.session1_id)

        # Check command stats
        self.assertEqual(details["command_stats"]["total_commands"], 5)

        # Check execution stats
        self.assertEqual(details["execution_stats"]["total_executions"], 5)
        self.assertEqual(details["execution_stats"]["successful"], 5)
        self.assertEqual(details["execution_stats"]["failed"], 0)

        # Check top intents
        self.assertGreater(len(details["top_intents"]), 0)
        self.assertEqual(details["top_intents"][0]["intent"], "navigate_url")

    def test_search_sessions(self):
        """Test searching sessions by command text"""
        # Search for chrome-related sessions
        results = self.memory.search_sessions("chrome", limit=50)

        self.assertGreater(len(results), 0)

        # Session 1 and 3 should be in results (both have chrome commands)
        session_ids = [r["session_id"] for r in results]
        self.assertIn(self.session1_id, session_ids)
        self.assertIn(self.session3_id, session_ids)

        # Each result should have matching_commands count
        for result in results:
            self.assertIn("matching_commands", result)
            self.assertGreater(result["matching_commands"], 0)

    def test_delete_session(self):
        """Test deleting a session"""
        # Create a temporary session to delete
        temp_session = self.memory.create_session()
        self.memory.store_command(
            session_id=temp_session,
            request_id="temp_req",
            raw_command="test command",
            intent=Intent(action="test", confidence=0.9, raw_command="test command"),
        )

        # Verify it exists
        details = self.memory.get_session_details(temp_session)
        self.assertIsNotNone(details)

        # Delete it
        result = self.memory.delete_session(temp_session)
        self.assertTrue(result)

        # Verify it's gone
        details = self.memory.get_session_details(temp_session)
        self.assertIsNone(details)

        # Try deleting non-existent session
        result = self.memory.delete_session("non_existent_session")
        self.assertFalse(result)

    def test_get_session_analytics(self):
        """Test getting analytics across all sessions"""
        analytics = self.memory.get_session_analytics()

        self.assertIn("total_sessions", analytics)
        self.assertIn("total_commands", analytics)
        self.assertIn("success_rate", analytics)
        self.assertIn("top_intents", analytics)
        self.assertIn("most_productive_sessions", analytics)

        # Check that we have data
        self.assertGreaterEqual(analytics["total_sessions"], 3)
        self.assertGreaterEqual(analytics["total_commands"], 11)  # 5 + 3 + 3

        # Success rate should be 100% (all our test commands succeeded)
        self.assertEqual(analytics["success_rate"], 100.0)

        # Check top intents
        self.assertGreater(len(analytics["top_intents"]), 0)

    def test_export_session(self):
        """Test exporting a session"""
        exported = self.memory.export_session(self.session1_id)

        self.assertIsNotNone(exported)
        self.assertIn("session", exported)
        self.assertIn("commands", exported)
        self.assertIn("execution_logs", exported)
        self.assertIn("context", exported)
        self.assertIn("exported_at", exported)

        # Check that we have the expected number of commands
        self.assertEqual(len(exported["commands"]), 5)
        self.assertEqual(len(exported["execution_logs"]), 5)

        # Check session details
        self.assertEqual(exported["session"]["session_id"], self.session1_id)

    def test_import_session(self):
        """Test importing a session"""
        # Export a session first
        exported = self.memory.export_session(self.session1_id)

        # Delete the original
        self.memory.delete_session(self.session1_id)

        # Import it back
        imported_id = self.memory.import_session(exported)

        self.assertEqual(imported_id, self.session1_id)

        # Verify the data was restored
        details = self.memory.get_session_details(imported_id)
        self.assertIsNotNone(details)
        self.assertEqual(details["command_stats"]["total_commands"], 5)

    def test_export_import_workflow(self):
        """Test complete export/import workflow with file"""
        # Export to file
        exported = self.memory.export_session(self.session2_id)

        export_file = self.test_dir / "session_export.json"
        with export_file.open("w") as f:
            json.dump(exported, f, indent=2)

        # Verify file was created
        self.assertTrue(export_file.exists())

        # Delete the session
        self.memory.delete_session(self.session2_id)

        # Import from file
        with export_file.open("r") as f:
            data = json.load(f)

        imported_id = self.memory.import_session(data)

        # Verify restoration
        details = self.memory.get_session_details(imported_id)
        self.assertIsNotNone(details)
        self.assertEqual(details["session_id"], self.session2_id)
        self.assertEqual(details["command_stats"]["total_commands"], 3)


class TestPipelineMultiSession(unittest.TestCase):
    """Test pipeline multi-session integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_memory.db"

        # Create test settings
        db_settings = DatabaseSettings(path=str(self.db_path), enable_wal=True)

        # Create mock settings
        self.settings = Settings()
        self.settings.database = db_settings

        # Create memory service
        self.memory = MemoryEngine(db_settings)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_context_from_recent(self):
        """Test loading context from recent sessions"""
        # Create a session with some commands
        old_session = self.memory.create_session()
        for i in range(3):
            self.memory.store_command(
                session_id=old_session,
                request_id=f"old_req_{i}",
                raw_command=f"command {i}",
                intent=Intent(action=f"intent_{i}", confidence=0.9, raw_command=f"command {i}"),
            )

        # Create new pipeline with context loading enabled
        pipeline = JanusPipeline(
            settings=self.settings, memory=self.memory, load_context_from_recent=True
        )

        # Check that context was loaded
        context = self.memory.get_context(pipeline.session_id, limit=100)

        # Should have loaded_recent_context entry
        context_types = [c["type"] for c in context]
        self.assertIn("loaded_recent_context", context_types)

        # Find the loaded context
        loaded_context = next(c for c in context if c["type"] == "loaded_recent_context")
        self.assertIn("source_sessions", loaded_context["data"])
        self.assertIn("loaded_commands", loaded_context["data"])

    def test_get_related_sessions(self):
        """Test finding related sessions"""
        # Create sessions with overlapping intents
        session1 = self.memory.create_session()
        session2 = self.memory.create_session()
        session3 = self.memory.create_session()

        # Session 1: Chrome and VSCode
        for intent in ["navigate_url", "open_app"]:
            self.memory.store_command(
                session_id=session1,
                request_id=f"s1_{intent}",
                raw_command=f"test {intent}",
                intent=Intent(action=intent, confidence=0.9, raw_command=f"test {intent}"),
            )

        # Session 2: Chrome and messaging (50% overlap with session1)
        for intent in ["navigate_url", "send_message"]:
            self.memory.store_command(
                session_id=session2,
                request_id=f"s2_{intent}",
                raw_command=f"test {intent}",
                intent=Intent(action=intent, confidence=0.9, raw_command=f"test {intent}"),
            )

        # Session 3: Only messaging (no overlap with session1)
        self.memory.store_command(
            session_id=session3,
            request_id="s3_msg",
            raw_command="test message",
            intent=Intent(action="send_message", confidence=0.9, raw_command="test message"),
        )

        # Create pipeline with session1
        pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            session_id=session1,
            load_context_from_recent=False,
        )

        # Find related sessions
        related = pipeline.get_related_sessions(min_similarity=0.3)

        # Session 2 should be related (has navigate_url in common)
        # Session 3 should not be related (no common intents)
        self.assertGreater(len(related), 0)

        # Session 2 should be in results
        related_ids = [r["session_id"] for r in related]
        self.assertIn(session2, related_ids)

    def test_get_session_summary(self):
        """Test getting session summary"""
        # Create pipeline
        pipeline = JanusPipeline(
            settings=self.settings, memory=self.memory, load_context_from_recent=False
        )

        # Add some commands
        for i in range(3):
            self.memory.store_command(
                session_id=pipeline.session_id,
                request_id=f"req_{i}",
                raw_command=f"command {i}",
                intent=Intent(action="test_action", confidence=0.9, raw_command=f"command {i}"),
            )

        # Get summary
        summary = pipeline.get_session_summary()

        self.assertIn("session_id", summary)
        self.assertIn("command_stats", summary)
        self.assertEqual(summary["command_stats"]["total_commands"], 3)


if __name__ == "__main__":
    unittest.main()
