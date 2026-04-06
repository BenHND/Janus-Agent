"""
Integration test for PHASE-19 Context & Memory Engine
Tests complete workflow with all components
"""
import os
import tempfile
import unittest
from datetime import datetime

from janus.runtime.api.context_api import (
    ContextEngine,
    clear_context,
    get_context,
    get_context_statistics,
    resolve_reference,
    update_context,
)


class TestPhase19Integration(unittest.TestCase):
    """Integration tests for Context & Memory Engine"""

    def setUp(self):
        """Set up test environment"""
        # Create temp database
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()

        # Clear any global context
        clear_context(clear_memory=True, clear_session=True)

    def tearDown(self):
        """Clean up"""
        clear_context(clear_memory=True, clear_session=True)
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_complete_workflow(self):
        """Test complete workflow: open app -> navigate -> copy -> paste"""
        # Step 1: Open browser
        update_context(
            command_text="open Chrome",
            intent="open_app",
            parameters={"app_name": "Chrome"},
            result={"status": "success"},
        )

        # Verify context updated
        context = get_context()
        self.assertEqual(context["memory"]["last_app"], "Chrome")
        self.assertEqual(context["session"]["last_opened_app"], "Chrome")

        # Step 2: Navigate to URL
        update_context(
            command_text="go to github.com",
            intent="navigate_url",
            parameters={"url": "https://github.com"},
            result={"status": "success"},
        )

        # Verify URL remembered
        context = get_context()
        self.assertEqual(context["memory"]["last_url"], "https://github.com")
        self.assertEqual(context["memory"]["last_app"], "Chrome")  # Still Chrome

        # Step 3: Copy text
        update_context(
            action_type="copy",
            action_details={
                "content": "function hello() { return 'world'; }",
                "source": "code block",
            },
        )

        # Verify copy recorded
        context = get_context()
        self.assertIn("hello", context["session"]["last_copied_content"])

        # Step 4: Open editor
        update_context(
            command_text="open VSCode",
            intent="open_app",
            parameters={"app_name": "VSCode"},
        )

        # Step 5: Open file
        update_context(
            command_text="open test.js",
            intent="open_file",
            parameters={"file_path": "/project/test.js"},
        )

        # Verify file remembered
        context = get_context()
        self.assertEqual(context["memory"]["last_file"], "/project/test.js")
        self.assertEqual(context["memory"]["last_app"], "VSCode")

        # Step 6: Paste with implicit references
        content = resolve_reference("it")
        file = resolve_reference("file")

        self.assertIn("hello", content)
        self.assertEqual(file, "/project/test.js")

        # Record paste
        update_context(
            action_type="paste",
            action_details={
                "content": content,
                "destination": file,
            },
        )

        # Verify complete workflow
        stats = get_context_statistics()
        self.assertEqual(stats["session"]["total_actions"], 6)
        self.assertGreater(stats["memory"]["total_commands"], 0)

    def test_reference_resolution_chain(self):
        """Test chained reference resolution"""
        # Copy something
        update_context(
            action_type="copy",
            action_details={"content": "test content"},
        )

        # Click somewhere
        update_context(
            action_type="click",
            action_details={"x": 100, "y": 200},
        )

        # Resolve multiple references
        it = resolve_reference("it")
        that = resolve_reference("that")
        here = resolve_reference("here")

        self.assertEqual(it, "test content")
        self.assertEqual(that, "test content")
        self.assertEqual(here, (100, 200))

    def test_performance_under_load(self):
        """Test performance with multiple operations"""
        import time

        # Simulate 20 operations
        start = time.time()
        for i in range(20):
            update_context(
                command_text=f"command {i}",
                intent="test",
                parameters={"index": i},
            )

        # Get context (should still be fast)
        context_start = time.time()
        context = get_context()
        context_time = (time.time() - context_start) * 1000

        total_time = time.time() - start

        # Verify performance
        self.assertLess(context_time, 100)  # Context should be <100ms
        self.assertLess(total_time, 5)  # Total should be <5 seconds

        # Verify data integrity
        self.assertEqual(context["session"]["total_actions"], 20)

    def test_persistence_integration(self):
        """Test that data persists across engine instances"""
        # Create engine with specific DB
        engine1 = ContextEngine(
            enable_ocr=False,
            enable_persistence=True,
            db_path=self.temp_db.name,
        )

        # Add data
        engine1.update_context(
            command_text="test command",
            intent="test",
            parameters={"key": "value"},
        )

        # Get context (should save to DB)
        context1 = engine1.get_context()

        # Create new engine with same DB
        engine2 = ContextEngine(
            enable_ocr=False,
            enable_persistence=True,
            db_path=self.temp_db.name,
        )

        # Should be able to query saved data
        if engine2.persistence:
            latest = engine2.persistence.get_latest_snapshot()
            self.assertIsNotNone(latest)

    def test_context_analyzer_integration(self):
        """Test system state observation via canonical SystemState (ARCH-004)"""
        context = get_context(include_ocr=False, include_apps=False)

        # Verify structure
        self.assertIn("system_state", context)
        self.assertIn("timestamp", context["system_state"])
        self.assertIn("performance_ms", context["system_state"])

        # Verify performance
        self.assertLess(context["performance_ms"], 100)

    def test_multi_reference_workflow(self):
        """Test complex workflow with multiple references"""
        # Open app
        update_context(
            command_text="open Chrome",
            intent="open_app",
            parameters={"app_name": "Chrome"},
        )

        # Open file
        update_context(
            command_text="open config.json",
            intent="open_file",
            parameters={"file_path": "/config.json"},
        )

        # Navigate URL
        update_context(
            command_text="go to docs.com",
            intent="navigate_url",
            parameters={"url": "https://docs.com"},
        )

        # Verify all references are maintained
        app = resolve_reference("app")
        file = resolve_reference("file")
        url = resolve_reference("url")

        self.assertEqual(app, "Chrome")
        self.assertEqual(file, "/config.json")
        self.assertEqual(url, "https://docs.com")

    def test_context_statistics(self):
        """Test statistics collection"""
        # Add various actions
        update_context(command_text="cmd1", intent="test", parameters={})
        update_context(action_type="click", action_details={"x": 10, "y": 20})
        update_context(action_type="copy", action_details={"content": "test"})
        update_context(action_type="paste", action_details={"content": "test"})

        # Get statistics
        stats = get_context_statistics()

        # Verify structure
        self.assertIn("session", stats)
        self.assertIn("memory", stats)

        # Verify counts
        self.assertEqual(stats["session"]["total_actions"], 4)
        self.assertIn("action_counts", stats["session"])
        self.assertEqual(stats["session"]["action_counts"]["command"], 1)
        self.assertEqual(stats["session"]["action_counts"]["click"], 1)
        self.assertEqual(stats["session"]["action_counts"]["copy"], 1)
        self.assertEqual(stats["session"]["action_counts"]["paste"], 1)

    def test_clear_context_selective(self):
        """Test selective context clearing"""
        # Add data to both session and memory
        update_context(
            command_text="test",
            intent="test",
            parameters={},
        )
        update_context(
            action_type="copy",
            action_details={"content": "test"},
        )

        # Verify data exists
        stats_before = get_context_statistics()
        session_actions_before = stats_before["session"]["total_actions"]
        memory_commands_before = stats_before["memory"]["total_commands"]

        self.assertGreater(session_actions_before, 0)
        self.assertGreater(memory_commands_before, 0)

        # Clear session only
        clear_context(clear_memory=False, clear_session=True)

        # Get new statistics
        stats_after = get_context_statistics()

        # Session should be empty
        self.assertEqual(stats_after["session"]["total_actions"], 0)

        # Memory should still have data
        self.assertEqual(stats_after["memory"]["total_commands"], memory_commands_before)

    def test_command_history_tracking(self):
        """Test command history is properly tracked"""
        # Add multiple commands
        commands = [
            ("open Chrome", "open_app", {"app_name": "Chrome"}),
            ("go to github.com", "navigate_url", {"url": "https://github.com"}),
            ("open test.py", "open_file", {"file_path": "test.py"}),
        ]

        for cmd_text, intent, params in commands:
            update_context(
                command_text=cmd_text,
                intent=intent,
                parameters=params,
            )

        # Get context
        context = get_context()

        # Verify history
        last_commands = context["memory"]["last_commands"]
        self.assertGreaterEqual(len(last_commands), 3)

        # Verify order (most recent last)
        self.assertEqual(last_commands[-1]["command"], "open test.py")
        self.assertEqual(last_commands[-1]["intent"], "open_file")


if __name__ == "__main__":
    unittest.main()
