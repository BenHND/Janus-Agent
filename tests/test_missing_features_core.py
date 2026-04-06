"""
Simplified tests for missing features implementation
Issue: FONCTIONNALITÉS MANQUANTES

Tests core functionality without full system dependencies
"""
import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUnifiedActionSchemaCore(unittest.TestCase):
    """Test unified action schema core classes"""

    def test_import_action_schema(self):
        """Test that action schema module imports successfully"""
        try:
            from janus.runtime.core import action_schema

            self.assertTrue(hasattr(action_schema, "UnifiedAction"))
            self.assertTrue(hasattr(action_schema, "ActionType"))
            self.assertTrue(hasattr(action_schema, "ActionMethod"))
            self.assertTrue(hasattr(action_schema, "ActionTarget"))
        except ImportError as e:
            self.fail(f"Failed to import action_schema: {e}")

    def test_action_types_enum(self):
        """Test ActionType enum"""
        from janus.runtime.core.action_schema import ActionType

        # Check key action types exist
        self.assertTrue(hasattr(ActionType, "CLICK"))
        self.assertTrue(hasattr(ActionType, "SCROLL_UNTIL"))
        self.assertTrue(hasattr(ActionType, "WAIT_FOR"))
        self.assertTrue(hasattr(ActionType, "VERIFY_STATE"))
        self.assertTrue(hasattr(ActionType, "OPEN_TAB"))

    def test_action_methods_enum(self):
        """Test ActionMethod enum"""
        from janus.runtime.core.action_schema import ActionMethod

        self.assertTrue(hasattr(ActionMethod, "VISION"))
        self.assertTrue(hasattr(ActionMethod, "ADAPTER"))
        self.assertTrue(hasattr(ActionMethod, "POSITION"))
        self.assertTrue(hasattr(ActionMethod, "AUTO"))

    def test_create_action_target(self):
        """Test creating ActionTarget"""
        from janus.runtime.core.action_schema import ActionTarget

        target = ActionTarget(text="Submit Button")
        self.assertEqual(target.text, "Submit Button")
        self.assertTrue(target.fuzzy_match)
        self.assertFalse(target.case_sensitive)

        target_dict = target.to_dict()
        self.assertIn("text", target_dict)
        self.assertEqual(target_dict["text"], "Submit Button")

    def test_create_unified_action(self):
        """Test creating UnifiedAction"""
        from janus.runtime.core.action_schema import ActionMethod, ActionTarget, ActionType, UnifiedAction

        action = UnifiedAction(
            type=ActionType.CLICK, target=ActionTarget(text="Submit"), method=ActionMethod.VISION
        )

        self.assertEqual(action.type, ActionType.CLICK)
        self.assertEqual(action.method, ActionMethod.VISION)
        self.assertEqual(action.target.text, "Submit")
        self.assertIsNotNone(action.action_id)

    def test_action_to_from_dict(self):
        """Test serialization of UnifiedAction"""
        from janus.runtime.core.action_schema import ActionTarget, ActionType, UnifiedAction

        # Create action
        action = UnifiedAction(
            type=ActionType.CLICK, target=ActionTarget(text="Button"), parameters={"test": "value"}
        )

        # Convert to dict
        action_dict = action.to_dict()
        self.assertIn("type", action_dict)
        self.assertIn("target", action_dict)
        self.assertEqual(action_dict["type"], "click")

        # Convert back from dict
        restored = UnifiedAction.from_dict(action_dict)
        self.assertEqual(restored.type, ActionType.CLICK)
        self.assertEqual(restored.target.text, "Button")


class TestActionMemoryCore(unittest.TestCase):
    """Test action memory core functionality"""

    def test_import_action_memory(self):
        """Test that action memory module imports"""
        try:
            from janus.memory import action_memory

            self.assertTrue(hasattr(action_memory, "ActionMemory"))
            self.assertTrue(hasattr(action_memory, "ActionMemoryType"))
        except ImportError as e:
            self.fail(f"Failed to import action_memory: {e}")

    def test_create_action_memory(self):
        """Test creating ActionMemory instance"""
        from janus.memory.action_memory import ActionMemory

        memory = ActionMemory(max_size=100)
        self.assertEqual(memory.max_size, 100)
        self.assertEqual(len(memory.memory), 0)

    def test_record_click(self):
        """Test recording click action"""
        from janus.memory.action_memory import ActionMemory

        memory = ActionMemory()
        memory.record_click(target="Button", coordinates=(100, 200), success=True)

        last_click = memory.get_last_click()
        self.assertIsNotNone(last_click)
        self.assertEqual(last_click.target_description, "Button")
        self.assertEqual(last_click.coordinates, (100, 200))

    def test_record_scroll(self):
        """Test recording scroll action"""
        from janus.memory.action_memory import ActionMemory

        memory = ActionMemory()
        memory.record_scroll(direction="down", amount=3)

        last_scroll = memory.get_last_scroll()
        self.assertIsNotNone(last_scroll)
        self.assertEqual(last_scroll.details["direction"], "down")

    def test_pattern_detection(self):
        """Test pattern detection"""
        from janus.memory.action_memory import ActionMemory

        memory = ActionMemory()

        # Record 5 scrolls
        for _ in range(5):
            memory.record_scroll("down", 3)

        # Should detect pattern
        is_pattern = memory.is_repeating_pattern("scroll", threshold=3)
        self.assertTrue(is_pattern)


class TestModuleStructure(unittest.TestCase):
    """Test that all new modules are properly structured"""

    def test_async_vision_monitor_exists(self):
        """Test async vision monitor module exists"""
        import os

        monitor_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "janus/vision/async_vision_monitor.py"
        )
        self.assertTrue(os.path.exists(monitor_path))

    def test_post_action_validator_exists(self):
        """Test post action validator module exists"""
        import os

        validator_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "janus/vision/post_action_validator.py"
        )
        self.assertTrue(os.path.exists(validator_path))

    def test_enhanced_chaining_exists(self):
        """Test enhanced chaining module exists"""
        import os

        chaining_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "janus/orchestrator/enhanced_chaining.py"
        )
        self.assertTrue(os.path.exists(chaining_path))


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for creating actions"""

    def test_click_action(self):
        """Test click_action convenience function"""
        from janus.runtime.core.action_schema import ActionType, click_action

        action = click_action("Submit", verify=True)
        self.assertEqual(action.type, ActionType.CLICK)
        self.assertEqual(action.target.text, "Submit")
        self.assertIsNotNone(action.verification)

    def test_wait_for_action(self):
        """Test wait_for_action convenience function"""
        from janus.runtime.core.action_schema import ActionType, wait_for_action

        action = wait_for_action("Loading", timeout_ms=5000)
        self.assertEqual(action.type, ActionType.WAIT_FOR)
        self.assertEqual(action.parameters["timeout_ms"], 5000)

    def test_scroll_until_action(self):
        """Test scroll_until_action convenience function"""
        from janus.runtime.core.action_schema import ActionType, scroll_until_action

        action = scroll_until_action("Footer", max_scrolls=10)
        self.assertEqual(action.type, ActionType.SCROLL_UNTIL)
        self.assertEqual(action.parameters["max_scrolls"], 10)


if __name__ == "__main__":
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedActionSchemaCore))
    suite.addTests(loader.loadTestsFromTestCase(TestActionMemoryCore))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 70)

    exit(0 if result.wasSuccessful() else 1)
