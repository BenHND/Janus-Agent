"""
Unit tests for SessionContext
Part of PHASE-19: Context & Memory Engine
"""
import time
import unittest

from janus.memory.session_context import ActionRecord, SessionContext


class TestSessionContext(unittest.TestCase):
    """Test cases for SessionContext"""

    def setUp(self):
        """Set up test fixtures"""
        self.context = SessionContext(max_actions=10)

    def test_initialization(self):
        """Test session context initialization"""
        self.assertIsNotNone(self.context)
        self.assertEqual(len(self.context.actions), 0)
        self.assertIsNone(self.context.last_command)
        self.assertIsNone(self.context.last_click_position)
        self.assertIsNone(self.context.last_copied_content)

    def test_record_command(self):
        """Test recording a command"""
        self.context.record_command(
            command_text="open Chrome",
            intent="open_app",
            parameters={"app_name": "Chrome"},
            result={"status": "success"},
        )

        self.assertEqual(len(self.context.actions), 1)
        self.assertEqual(self.context.last_command, "open Chrome")
        self.assertEqual(self.context.last_opened_app, "Chrome")

        action = self.context.actions[0]
        self.assertEqual(action.action_type, "command")
        self.assertEqual(action.details["intent"], "open_app")

    def test_record_click(self):
        """Test recording a click action"""
        self.context.record_click(x=100, y=200, target="Submit Button")

        self.assertEqual(len(self.context.actions), 1)
        self.assertEqual(self.context.last_click_position, (100, 200))

        action = self.context.actions[0]
        self.assertEqual(action.action_type, "click")
        self.assertEqual(action.details["x"], 100)
        self.assertEqual(action.details["y"], 200)
        self.assertEqual(action.details["target"], "Submit Button")

    def test_record_copy(self):
        """Test recording a copy action"""
        self.context.record_copy(content="Hello World", source="text field")

        self.assertEqual(len(self.context.actions), 1)
        self.assertEqual(self.context.last_copied_content, "Hello World")

        action = self.context.actions[0]
        self.assertEqual(action.action_type, "copy")
        self.assertEqual(action.details["content"], "Hello World")

    def test_record_paste(self):
        """Test recording a paste action"""
        self.context.record_paste(content="Hello World", destination="editor")

        self.assertEqual(len(self.context.actions), 1)

        action = self.context.actions[0]
        self.assertEqual(action.action_type, "paste")
        self.assertEqual(action.details["destination"], "editor")

    def test_max_actions_limit(self):
        """Test that max actions limit is enforced"""
        # Add more than max_actions
        for i in range(15):
            self.context.record_click(x=i, y=i)

        # Should only keep last 10
        self.assertEqual(len(self.context.actions), 10)

        # First action should be from iteration 5
        self.assertEqual(self.context.actions[0].details["x"], 5)

    def test_resolve_reference_it(self):
        """Test resolving 'it' reference"""
        self.context.record_copy(content="Test Content")

        resolved = self.context.resolve_reference("it")
        self.assertEqual(resolved, "Test Content")

    def test_resolve_reference_here(self):
        """Test resolving 'here' reference"""
        self.context.record_click(x=50, y=75)

        resolved = self.context.resolve_reference("here")
        self.assertEqual(resolved, (50, 75))

    def test_resolve_reference_file(self):
        """Test resolving file reference"""
        self.context.record_command(
            command_text="open test.py",
            intent="open_file",
            parameters={"file_path": "/path/to/test.py"},
        )

        resolved = self.context.resolve_reference("this file")
        self.assertEqual(resolved, "/path/to/test.py")

    def test_resolve_reference_app(self):
        """Test resolving app reference"""
        self.context.record_command(
            command_text="open Chrome",
            intent="open_app",
            parameters={"app_name": "Chrome"},
        )

        resolved = self.context.resolve_reference("this app")
        self.assertEqual(resolved, "Chrome")

    def test_resolve_reference_unknown(self):
        """Test resolving unknown reference"""
        resolved = self.context.resolve_reference("unknown")
        self.assertIsNone(resolved)

    def test_get_last_action(self):
        """Test getting last action"""
        self.context.record_click(x=10, y=20)
        self.context.record_copy(content="Test")

        last_action = self.context.get_last_action()
        self.assertIsNotNone(last_action)
        self.assertEqual(last_action.action_type, "copy")

    def test_get_last_action_by_type(self):
        """Test getting last action by type"""
        self.context.record_click(x=10, y=20)
        self.context.record_copy(content="Test")
        self.context.record_paste(content="Test")

        last_click = self.context.get_last_action("click")
        self.assertIsNotNone(last_click)
        self.assertEqual(last_click.action_type, "click")
        self.assertEqual(last_click.details["x"], 10)

    def test_get_last_n_actions(self):
        """Test getting last N actions"""
        for i in range(5):
            self.context.record_click(x=i, y=i)

        last_3 = self.context.get_last_n_actions(3)
        self.assertEqual(len(last_3), 3)
        self.assertEqual(last_3[0].details["x"], 2)
        self.assertEqual(last_3[2].details["x"], 4)

    def test_get_context_for_chaining(self):
        """Test getting context for command chaining"""
        self.context.record_command(
            command_text="open Chrome",
            intent="open_app",
            parameters={"app_name": "Chrome"},
        )
        self.context.record_copy(content="Hello")
        self.context.record_click(x=100, y=200)

        chaining_context = self.context.get_context_for_chaining()

        self.assertEqual(chaining_context["last_command"], "open Chrome")
        self.assertEqual(chaining_context["last_copied_content"], "Hello")
        self.assertEqual(chaining_context["last_click_position"], (100, 200))
        self.assertEqual(chaining_context["last_opened_app"], "Chrome")
        self.assertEqual(chaining_context["total_actions"], 3)
        self.assertIn("session_duration_seconds", chaining_context)

    def test_clear(self):
        """Test clearing session context"""
        self.context.record_command("test", "test", {})
        self.context.record_copy(content="Test")

        self.context.clear()

        self.assertEqual(len(self.context.actions), 0)
        self.assertIsNone(self.context.last_command)
        self.assertIsNone(self.context.last_copied_content)

    def test_get_statistics(self):
        """Test getting session statistics"""
        self.context.record_click(x=10, y=20)
        self.context.record_copy(content="Test")
        self.context.record_command("test", "test", {})

        stats = self.context.get_statistics()

        self.assertIn("session_start", stats)
        self.assertIn("session_duration_seconds", stats)
        self.assertIn("total_actions", stats)
        self.assertIn("action_counts", stats)

        self.assertEqual(stats["total_actions"], 3)
        self.assertEqual(stats["action_counts"]["click"], 1)
        self.assertEqual(stats["action_counts"]["copy"], 1)
        self.assertEqual(stats["action_counts"]["command"], 1)
        self.assertTrue(stats["has_copied_content"])
        self.assertTrue(stats["has_click_position"])

    def test_update_references_with_file(self):
        """Test that references are updated with file operations"""
        self.context.record_command(
            command_text="open test.py",
            intent="open_file",
            parameters={"file_path": "/path/to/test.py"},
        )

        self.assertEqual(self.context.last_opened_file, "/path/to/test.py")

    def test_update_references_with_url(self):
        """Test that references are updated with URL navigation"""
        self.context.record_command(
            command_text="go to github.com",
            intent="navigate_url",
            parameters={"url": "https://github.com"},
        )

        self.assertEqual(self.context.last_url, "https://github.com")

    def test_action_timestamps(self):
        """Test that actions have proper timestamps"""
        before = time.time()
        self.context.record_click(x=10, y=20)
        after = time.time()

        action = self.context.actions[0]
        self.assertGreaterEqual(action.timestamp, before)
        self.assertLessEqual(action.timestamp, after)


if __name__ == "__main__":
    unittest.main()
