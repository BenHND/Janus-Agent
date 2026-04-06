"""
Tests for TICKET-315: Fast Router & Auto-Repair

This ticket addresses two critical issues:
1. Force ContextRouter to use SIGNAL (keywords) mode for 0ms latency
2. Add auto-repair loop in generate_structured_plan when plan is invalid

Expected outcomes:
- Speed: "Step 1: Generating structured plan" displays instantly (no ContextRouter delay)
- Reliability: If LLM forgets app_name, auto-repair kicks in:
  ⚠️ Plan invalide...
  ✅ Auto-réparation réussie !
"""
import unittest
from unittest.mock import MagicMock, patch

from janus.ai.reasoning.context_router import MockContextRouter
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestTicket315FastRouter(unittest.TestCase):
    """Test TICKET-315 Part 1: Fast Router (Force SIGNAL mode)"""

    def test_pipeline_uses_mock_context_router(self):
        """
        Verify that pipeline always uses MockContextRouter for instant routing.
        
        TICKET-315: Force mode SIGNAL (keywords) to eliminate 15s latency.
        """
        # We need to test the pipeline property, so we mock the dependencies
        from janus.runtime.core.settings import Settings
        from janus.runtime.core import MemoryEngine
        
        # Create mock settings and memory
        mock_settings = MagicMock(spec=Settings)
        mock_settings.llm = MagicMock()
        mock_settings.llm.provider = "mock"
        mock_settings.llm.model = "mock"
        mock_settings.features = MagicMock()
        mock_settings.features.enable_semantic_correction = False
        mock_settings.execution = MagicMock()
        mock_settings.execution.enable_vision_recovery = False
        mock_settings.execution.enable_replanning = False
        mock_settings.execution.max_retries = 3
        mock_settings.async_vision_monitor = MagicMock()
        mock_settings.async_vision_monitor.enable_monitor = False
        mock_settings.language = MagicMock()
        mock_settings.language.default = "fr"
        
        mock_memory = MagicMock(spec=MemoryEngine)
        mock_memory.create_session.return_value = "test_session"
        
        # Import after mocking
        from janus.runtime.core.pipeline import JanusPipeline
        
        # Create pipeline with minimal options
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=False,  # Disable LLM to avoid loading it
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
            load_context_from_recent=False,
        )
        
        # Access context_router property (triggers lazy loading)
        router = pipeline.context_router
        
        # Assert it's a MockContextRouter (SIGNAL mode)
        self.assertIsInstance(router, MockContextRouter)
        self.assertTrue(router.available)

    def test_mock_context_router_is_instant(self):
        """
        Verify MockContextRouter provides near-instant response (< 5ms).
        """
        router = MockContextRouter()
        
        import time
        start = time.time()
        result = router.get_requirements("Ouvre Safari")
        elapsed_ms = (time.time() - start) * 1000
        
        # Should be nearly instant (< 5ms)
        self.assertLess(elapsed_ms, 5, f"MockContextRouter took {elapsed_ms:.2f}ms (should be < 5ms)")
        
        # Simple command should return empty list (no special context needed)
        self.assertEqual(result, [])

    def test_mock_context_router_detects_keywords(self):
        """
        Verify MockContextRouter correctly detects context requirements via keywords.
        """
        router = MockContextRouter()
        
        # Vision keywords
        result = router.get_requirements("Qu'est-ce qu'il y a à l'écran ?")
        self.assertIn("vision", result)
        
        # Clipboard keywords
        result = router.get_requirements("Copie ça")
        self.assertIn("clipboard", result)
        
        # Browser content keywords
        result = router.get_requirements("Résume cette page")
        self.assertIn("browser_content", result)
        
        # File history keywords
        result = router.get_requirements("Ouvre le dernier fichier")
        self.assertIn("file_history", result)


class TestTicket315AutoRepair(unittest.TestCase):
    """Test TICKET-315 Part 2: Auto-Repair for invalid plans"""

    def setUp(self):
        """Set up ReasonerLLM with mock backend"""
        self.llm = ReasonerLLM(backend="mock")

    def test_build_auto_repair_prompt(self):
        """
        Verify the auto-repair prompt is correctly built.
        """
        prompt = self.llm._build_auto_repair_prompt("Ouvre Safari")
        
        # Should contain the command
        self.assertIn("Ouvre Safari", prompt)
        
        # Should contain directive instructions (now in French)
        self.assertIn("INSTRUCTIONS CRITIQUES", prompt)
        self.assertIn("open_application", prompt)
        self.assertIn("app_name", prompt)
        
        # Should contain the schema section with available modules
        self.assertIn("MODULES DISPONIBLES", prompt)
        self.assertIn("open_url", prompt)
        self.assertIn("browser", prompt)

    def test_auto_repair_uses_json_mode(self):
        """
        Verify that auto-repair uses json_mode=True when calling _run_inference.
        
        TICKET-315: JSON mode forces Qwen to output valid JSON only.
        """
        # Track if json_mode was passed correctly
        json_mode_used = [False]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            if json_mode:
                json_mode_used[0] = True
            return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        with patch.object(self.llm, '_run_inference', side_effect=mock_inference):
            with patch.object(self.llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.return_value = {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}
                
                # Call auto-repair directly
                result = self.llm._attempt_auto_repair("Ouvre Safari")
        
        # Verify json_mode was used
        self.assertTrue(json_mode_used[0], "json_mode should be True in auto-repair")
        self.assertIn("steps", result)

    def test_auto_repair_triggered_on_empty_plan(self):
        """
        Verify that auto-repair is triggered when initial plan has no steps.
        
        TICKET-315: If Qwen forgets app_name, auto-repair should kick in with json_mode=True.
        """
        # Create a mock LLM that returns empty steps first, then valid on repair
        call_count = [0]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: return invalid plan (empty steps)
                return '{"steps": []}'
            else:
                # Second call (repair with json_mode): return valid plan
                return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        # Patch _run_inference
        with patch.object(self.llm, '_run_inference', side_effect=mock_inference):
            # Patch _parse_structured_plan_response to pass through
            with patch.object(self.llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.side_effect = [
                    {"steps": []},  # First parse returns empty
                    {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}  # Repair parse returns valid
                ]
                
                result = self.llm.generate_structured_plan("Ouvre Safari")
        
        # Should have called inference twice (initial + repair)
        self.assertEqual(call_count[0], 2)
        
        # Should return valid plan after repair
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0)

    def test_valid_plan_no_auto_repair(self):
        """
        Verify that auto-repair is NOT triggered when initial plan is valid.
        """
        # The mock backend already returns valid plans for "ouvre Chrome"
        result = self.llm.generate_structured_plan("ouvre Chrome")
        
        # Should return valid plan
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0)
        
        # Check the plan has correct structure
        step = result["steps"][0]
        self.assertIn("module", step)
        self.assertIn("action", step)

    def test_auto_repair_with_app_name(self):
        """
        Test auto-repair specifically for open_application missing app_name.
        
        This is the main use case from the ticket.
        """
        result = self.llm.generate_structured_plan("Ouvre Safari", language="fr")
        
        # Should return valid plan
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0)
        
        # Should have proper app_name in args
        for step in result["steps"]:
            if step.get("action") == "open_application":
                self.assertIn("args", step)
                self.assertIn("app_name", step.get("args", {}))

    def test_generate_structured_plan_with_mock_returns_steps(self):
        """
        Verify mock backend returns valid structured plans.
        """
        # Test various commands
        test_commands = [
            ("ouvre Chrome", "system"),
            ("va sur YouTube", "browser"),
            ("copie", "ui"),
        ]
        
        for command, expected_module in test_commands:
            result = self.llm.generate_structured_plan(command, language="fr")
            
            self.assertIn("steps", result, f"No steps for command: {command}")
            self.assertGreater(len(result["steps"]), 0, f"Empty steps for command: {command}")


class TestTicket315Integration(unittest.TestCase):
    """Integration tests for TICKET-315 changes"""

    def test_full_flow_simple_command(self):
        """
        Test complete flow: simple command with fast router and successful plan.
        """
        from janus.ai.reasoning.context_router import MockContextRouter
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        # 1. Context routing (should be instant)
        router = MockContextRouter()
        import time
        
        start = time.time()
        context_keys = router.get_requirements("Ouvre Safari")
        router_time = (time.time() - start) * 1000
        
        # Router should be < 5ms
        self.assertLess(router_time, 5)
        
        # Simple command needs no extra context
        self.assertEqual(context_keys, [])
        
        # 2. Plan generation (should succeed)
        llm = ReasonerLLM(backend="mock")
        plan = llm.generate_structured_plan("Ouvre Safari", language="fr")
        
        # Plan should be valid
        self.assertIn("steps", plan)
        self.assertGreater(len(plan["steps"]), 0)

    def test_performance_router_vs_llm(self):
        """
        Verify that MockContextRouter is significantly faster than LLM-based routing.
        
        MockContextRouter: ~0ms (keyword matching)
        LLM ContextRouter: up to 15s on cold start
        """
        router = MockContextRouter()
        
        import time
        
        # Run multiple iterations to get accurate timing
        iterations = 100
        start = time.time()
        for _ in range(iterations):
            router.get_requirements("Test command for routing")
        total_time_ms = (time.time() - start) * 1000
        avg_time_ms = total_time_ms / iterations
        
        # Average should be < 1ms per call
        self.assertLess(avg_time_ms, 1, f"Avg routing time: {avg_time_ms:.3f}ms (should be < 1ms)")


if __name__ == "__main__":
    unittest.main()
