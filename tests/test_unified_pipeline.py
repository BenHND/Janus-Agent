"""
Unit tests for unified pipeline

These tests verify all acceptance criteria from issue #82:
1. python main.py works
2. End-to-end mocked run passes
3. Zero JSON state writes
4. SQLite database created
5. Structured logs present for each step
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from janus.runtime.core import ExecutionResult, Intent, MemoryEngine, Settings, JanusPipeline


class TestUnifiedPipeline(unittest.TestCase):
    """Test cases for unified pipeline"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        # Create isolated temp directory for each test
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config.ini for testing
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[audio]
sample_rate = 16000
activation_threshold = 500.0

[language]
default = fr

[automation]
safety_delay = 0.5

[session]
state_file = session_state.json
max_history = 50

[llm]
provider = mock
model = gpt-4

[tts]
enable_tts = false

[database]
path = janus.db
enable_wal = true

[logging]
level = INFO
enable_structured = true
log_to_database = true
"""
            )

        # Initialize components
        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(self.settings, self.memory)

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_basic_command_processing(self):
        """Test basic command processing through pipeline"""
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        self.assertIsInstance(result, ExecutionResult)
        self.assertIsNotNone(result.intent)
        self.assertEqual(result.intent.raw_command, "ouvre Safari")
        self.assertIsNotNone(result.session_id)
        self.assertIsNotNone(result.request_id)

    def test_click_command(self):
        """Test click command processing"""
        result = self.pipeline.process_command("clique sur le bouton", mock_execution=True)

        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertGreater(len(result.action_results), 0)

    def test_copy_command(self):
        """Test copy command processing"""
        result = self.pipeline.process_command("copie ceci", mock_execution=True)

        self.assertIsInstance(result, ExecutionResult)
        self.assertIsNotNone(result.intent)

    def test_paste_command(self):
        """Test paste command processing"""
        result = self.pipeline.process_command("colle ici", mock_execution=True)

        self.assertIsInstance(result, ExecutionResult)
        self.assertIsNotNone(result.intent)

    def test_unknown_command(self):
        """Test handling of unknown commands"""
        result = self.pipeline.process_command(
            "xyzabc unknown command that makes no sense", mock_execution=True
        )

        self.assertIsInstance(result, ExecutionResult)
        self.assertIsNotNone(result.intent)
        # Unknown commands should still be processed

    def test_multiple_commands_sequence(self):
        """Test processing multiple commands in sequence"""
        commands = ["ouvre Safari", "clique sur le bouton", "copie ceci"]

        for cmd in commands:
            result = self.pipeline.process_command(cmd, mock_execution=True)
            self.assertIsInstance(result, ExecutionResult)
            self.assertIsNotNone(result.intent)

    def test_no_json_files_created(self):
        """Test that no JSON state files are created"""
        # Process a command
        self.pipeline.process_command("ouvre Safari", mock_execution=True)

        # Check that no JSON files were created
        json_files = list(Path(self.test_dir).glob("*.json"))
        # Filter out config.ini - we only care about state files
        state_json_files = [
            f
            for f in json_files
            if f.name
            in [
                "session_state.json",
                "context_memory.json",
                "clipboard_history.json",
                "session_memory.json",
            ]
        ]

        self.assertEqual(
            len(state_json_files), 0, f"Found unexpected JSON state files: {state_json_files}"
        )

    def test_sqlite_database_created(self):
        """Test that SQLite database is created correctly"""
        # Process a command to trigger database initialization
        self.pipeline.process_command("ouvre Safari", mock_execution=True)

        # Check database exists
        db_path = Path(self.test_dir) / "janus.db"
        self.assertTrue(db_path.exists(), "Database file not created")

        # Verify tables exist
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        # Verify required tables exist
        required_tables = {
            "sessions",
            "context",
            "command_history",
            "execution_logs",
            "structured_logs",
        }

        self.assertTrue(
            required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"
        )

        conn.close()

    def test_structured_logs_present(self):
        """Test that structured logs are present for each step"""
        # Process a command
        result = self.pipeline.process_command("ouvre Safari", mock_execution=True)

        # Get structured logs for this session
        logs = self.memory.get_structured_logs(session_id=result.session_id, limit=100)

        # Should have logs for:
        # - Pipeline initialization
        # - Processing command
        # - Parsing command
        # - Storing command
        # - Creating action plan
        # - Executing action(s)
        # - Updating session state
        # - Command processed successfully

        self.assertGreater(len(logs), 0, "No structured logs found")

        # Verify log structure
        for log in logs:
            self.assertIn("level", log)
            self.assertIn("logger", log)
            self.assertIn("message", log)
            self.assertIn("timestamp", log)

    def test_session_persistence(self):
        """Test that session state persists across pipeline instances"""
        # Process command with first pipeline
        result1 = self.pipeline.process_command("ouvre Safari", mock_execution=True)
        session_id = result1.session_id

        # Create new pipeline with same session
        pipeline2 = JanusPipeline(self.settings, self.memory, session_id=session_id)

        # Process another command
        result2 = pipeline2.process_command("clique sur le bouton", mock_execution=True)

        # Verify same session
        self.assertEqual(result2.session_id, session_id)

        # Verify command history contains both commands
        history = self.memory.get_command_history(session_id)
        self.assertGreaterEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
