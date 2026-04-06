"""
Unit tests for TICKET-ARCH-005: Dynamic Memory Pipeline (Variable Passing)

Tests the save_to_memory capability that enables scenarios like:
"Take the CEO name from LinkedIn and put it in Salesforce"
"""
import unittest
from janus.memory.session_context import SessionContext
from janus.runtime.core.unified_memory import UnifiedMemoryManager
from janus.runtime.core.settings import DatabaseSettings


class TestSessionContextDynamicMemory(unittest.TestCase):
    """Test SessionContext dynamic memory methods"""

    def setUp(self):
        """Set up test fixtures"""
        self.context = SessionContext()

    def test_save_to_memory(self):
        """Test saving data to memory"""
        self.context.save_to_memory("CEO_name", "John Smith")
        
        # Check it was stored
        self.assertEqual(
            self.context.get_from_memory("CEO_name"),
            "John Smith"
        )

    def test_save_multiple_values(self):
        """Test saving multiple key-value pairs"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("company_revenue", "$10M")
        self.context.save_to_memory("linkedin_url", "https://linkedin.com/in/johnsmith")
        
        # Verify all are stored
        self.assertEqual(self.context.get_from_memory("CEO_name"), "John Smith")
        self.assertEqual(self.context.get_from_memory("company_revenue"), "$10M")
        self.assertEqual(
            self.context.get_from_memory("linkedin_url"),
            "https://linkedin.com/in/johnsmith"
        )

    def test_get_from_memory_nonexistent(self):
        """Test retrieving non-existent key returns None"""
        result = self.context.get_from_memory("nonexistent_key")
        self.assertIsNone(result)

    def test_get_all_memory(self):
        """Test retrieving all memory at once"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("company_revenue", "$10M")
        
        all_memory = self.context.get_all_memory()
        
        self.assertEqual(len(all_memory), 2)
        self.assertEqual(all_memory["CEO_name"], "John Smith")
        self.assertEqual(all_memory["company_revenue"], "$10M")

    def test_get_all_memory_empty(self):
        """Test get_all_memory returns empty dict when no data"""
        all_memory = self.context.get_all_memory()
        self.assertEqual(all_memory, {})

    def test_clear_memory(self):
        """Test clearing dynamic memory"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("company_revenue", "$10M")
        
        # Clear memory
        self.context.clear_memory()
        
        # Verify memory is empty
        self.assertIsNone(self.context.get_from_memory("CEO_name"))
        self.assertEqual(len(self.context.get_all_memory()), 0)

    def test_clear_preserves_other_context(self):
        """Test that clear() clears memory along with other context"""
        # Set up memory and other context
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.last_command = "test command"
        
        # Clear all context
        self.context.clear()
        
        # Verify both are cleared
        self.assertIsNone(self.context.get_from_memory("CEO_name"))
        self.assertIsNone(self.context.last_command)

    def test_memory_in_statistics(self):
        """Test that memory count is included in statistics"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("company_revenue", "$10M")
        
        stats = self.context.get_statistics()
        
        self.assertIn("dynamic_memory_items", stats)
        self.assertEqual(stats["dynamic_memory_items"], 2)

    def test_memory_in_context_for_chaining(self):
        """Test that memory is included in context for chaining"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("company_revenue", "$10M")
        
        context = self.context.get_context_for_chaining()
        
        self.assertIn("memory", context)
        self.assertEqual(context["memory"]["CEO_name"], "John Smith")
        self.assertEqual(context["memory"]["company_revenue"], "$10M")

    def test_overwrite_existing_key(self):
        """Test that saving to an existing key overwrites the value"""
        self.context.save_to_memory("CEO_name", "John Smith")
        self.context.save_to_memory("CEO_name", "Jane Doe")
        
        self.assertEqual(self.context.get_from_memory("CEO_name"), "Jane Doe")

    def test_memory_types(self):
        """Test storing different data types"""
        self.context.save_to_memory("string_value", "John Smith")
        self.context.save_to_memory("int_value", 42)
        self.context.save_to_memory("float_value", 99.99)
        self.context.save_to_memory("bool_value", True)
        self.context.save_to_memory("list_value", [1, 2, 3])
        self.context.save_to_memory("dict_value", {"key": "value"})
        
        self.assertEqual(self.context.get_from_memory("string_value"), "John Smith")
        self.assertEqual(self.context.get_from_memory("int_value"), 42)
        self.assertEqual(self.context.get_from_memory("float_value"), 99.99)
        self.assertEqual(self.context.get_from_memory("bool_value"), True)
        self.assertEqual(self.context.get_from_memory("list_value"), [1, 2, 3])
        self.assertEqual(self.context.get_from_memory("dict_value"), {"key": "value"})


class TestUnifiedMemoryManagerDynamicMemory(unittest.TestCase):
    """Test UnifiedMemoryManager dynamic memory methods"""

    def setUp(self):
        """Set up test fixtures"""
        # Use temporary file for database
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_unified = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.temp_unified.close()
        
        # Create settings and manager
        from janus.runtime.core import Settings
        settings = Settings()
        settings.database.path = self.temp_db.name
        
        self.memory = UnifiedMemoryManager(
            db_settings=settings.database,
            unified_store_path=self.temp_unified.name
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        import os
        try:
            os.unlink(self.temp_db.name)
        except (OSError, FileNotFoundError):
            pass
        try:
            os.unlink(self.temp_unified.name)
        except (OSError, FileNotFoundError):
            pass

    def test_save_to_memory_via_unified_manager(self):
        """Test saving data via UnifiedMemoryManager"""
        self.memory.save_to_memory("CEO_name", "John Smith")
        
        result = self.memory.get_from_memory("CEO_name")
        self.assertEqual(result, "John Smith")

    def test_get_all_memory_via_unified_manager(self):
        """Test retrieving all memory via UnifiedMemoryManager"""
        self.memory.save_to_memory("CEO_name", "John Smith")
        self.memory.save_to_memory("company_revenue", "$10M")
        
        all_memory = self.memory.get_all_memory()
        
        self.assertEqual(len(all_memory), 2)
        self.assertIn("CEO_name", all_memory)
        self.assertIn("company_revenue", all_memory)

    def test_clear_memory_via_unified_manager(self):
        """Test clearing memory via UnifiedMemoryManager"""
        self.memory.save_to_memory("CEO_name", "John Smith")
        self.memory.clear_memory()
        
        result = self.memory.get_from_memory("CEO_name")
        self.assertIsNone(result)

    def test_memory_persists_across_operations(self):
        """Test that memory persists across other memory operations"""
        # Save to dynamic memory
        self.memory.save_to_memory("CEO_name", "John Smith")
        
        # Perform other operations
        self.memory.record_command(
            "test command",
            "test_intent",
            {"param": "value"}
        )
        self.memory.record_click(100, 200)
        
        # Verify dynamic memory still exists
        result = self.memory.get_from_memory("CEO_name")
        self.assertEqual(result, "John Smith")

    def test_multi_application_scenario(self):
        """
        Test a multi-app scenario: LinkedIn → Salesforce
        
        Simulates: "Take the CEO name from LinkedIn and add them to Salesforce"
        """
        # Step 1: Extract from LinkedIn
        self.memory.save_to_memory("CEO_name", "John Smith")
        self.memory.save_to_memory("CEO_title", "Chief Executive Officer")
        self.memory.save_to_memory("company", "Acme Corp")
        
        # Step 2: Verify data is available for Salesforce
        ceo_name = self.memory.get_from_memory("CEO_name")
        ceo_title = self.memory.get_from_memory("CEO_title")
        company = self.memory.get_from_memory("company")
        
        self.assertEqual(ceo_name, "John Smith")
        self.assertEqual(ceo_title, "Chief Executive Officer")
        self.assertEqual(company, "Acme Corp")
        
        # Step 3: Verify all data can be retrieved at once
        all_data = self.memory.get_all_memory()
        self.assertEqual(len(all_data), 3)
        self.assertIn("CEO_name", all_data)
        self.assertIn("CEO_title", all_data)
        self.assertIn("company", all_data)


class TestDynamicMemoryIntegration(unittest.TestCase):
    """Integration tests for dynamic memory in ReAct loop context"""

    def setUp(self):
        """Set up test fixtures"""
        self.context = SessionContext()

    def test_memory_in_react_loop_context(self):
        """Test that memory is available in ReAct loop context"""
        # Simulate extracting data in first loop iteration
        self.context.save_to_memory("CEO_name", "John Smith")
        
        # Get context for next iteration
        loop_context = self.context.get_context_for_chaining()
        
        # Verify memory is included
        self.assertIn("memory", loop_context)
        self.assertEqual(loop_context["memory"]["CEO_name"], "John Smith")

    def test_empty_memory_in_react_loop(self):
        """Test that empty memory doesn't break ReAct loop"""
        loop_context = self.context.get_context_for_chaining()
        
        self.assertIn("memory", loop_context)
        self.assertEqual(loop_context["memory"], {})

    def test_memory_accumulation(self):
        """Test that memory accumulates across multiple extractions"""
        # Simulate multiple data extractions
        self.context.save_to_memory("CEO_name", "John Smith")
        
        # Later extraction
        self.context.save_to_memory("company_revenue", "$10M")
        
        # Even later
        self.context.save_to_memory("employee_count", 150)
        
        # Verify all accumulated
        memory = self.context.get_all_memory()
        self.assertEqual(len(memory), 3)
        self.assertIn("CEO_name", memory)
        self.assertIn("company_revenue", memory)
        self.assertIn("employee_count", memory)


if __name__ == "__main__":
    unittest.main()
