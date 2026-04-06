"""
Tests for TICKET-330: FIX BLOQUANT - Latence & Robustesse Reasoner

This ticket addresses two CRITICAL production issues:

1. LATENCE (30s+): JanusPipeline was initializing a ContextRouter based on LLM,
   causing model loading and network delay blocking each command.
   
   FIX: Force MockContextRouter (keyword-based, 0ms latency) in pipeline.context_router

2. CRASH (Missing Args): ReasonerLLM had no "Self-Healing" logic. If the model
   forgot an argument, execution failed without correction attempt.
   
   FIX: Add auto-repair loop in generate_structured_plan when plan is empty/invalid

Expected Results:
- At command launch: "⚡️ PERFORMANCE: ContextRouter forcé en mode SIGNAL (0ms)" appears
- If Qwen forgets app_name: "✅ Auto-réparation réussie !" appears
"""
import time
import unittest
from unittest.mock import MagicMock, patch

from janus.ai.reasoning.context_router import MockContextRouter
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


def create_mock_pipeline_dependencies():
    """
    Create mock dependencies for JanusPipeline tests.
    
    Returns:
        tuple: (mock_settings, mock_memory) configured for minimal testing.
    """
    from janus.runtime.core.settings import Settings
    from janus.runtime.core import MemoryEngine
    
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
    mock_memory.create_session.return_value = "test_session_330"
    
    return mock_settings, mock_memory


class TestTicket330PerformanceFix(unittest.TestCase):
    """Test TICKET-330 FIX 1: Kill LLM Router - Force SIGNAL mode (0ms)"""

    def test_pipeline_context_router_uses_mock(self):
        """
        Verify JanusPipeline.context_router always returns MockContextRouter.
        
        TICKET-330 FIX 1: Replace LLM-based ContextRouter with MockContextRouter
        to eliminate 30s+ latency on cold starts.
        """
        from janus.runtime.core.pipeline import JanusPipeline
        
        mock_settings, mock_memory = create_mock_pipeline_dependencies()
        
        # Create pipeline
        pipeline = JanusPipeline(
            settings=mock_settings,
            memory=mock_memory,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
            load_context_from_recent=False,
        )
        
        # Access context_router property - should return MockContextRouter
        router = pipeline.context_router
        
        # Verify it's MockContextRouter (fast mode)
        self.assertIsInstance(router, MockContextRouter)
        self.assertTrue(router.available)
        self.assertEqual(router.model_name, "mock")

    def test_mock_context_router_latency_under_5ms(self):
        """
        Verify MockContextRouter provides near-instant routing (< 5ms).
        
        TICKET-330: Latency fix ensures routing is instant (0ms target).
        """
        router = MockContextRouter()
        
        # Measure multiple calls
        total_time_ms = 0
        iterations = 50
        
        for _ in range(iterations):
            start = time.time()
            router.get_requirements("Ouvre Safari et va sur YouTube")
            total_time_ms += (time.time() - start) * 1000
        
        avg_time_ms = total_time_ms / iterations
        
        # Average should be < 1ms (effectively 0ms)
        self.assertLess(avg_time_ms, 5, f"Avg routing: {avg_time_ms:.3f}ms (target: < 5ms)")

    def test_mock_context_router_no_network_dependency(self):
        """
        Verify MockContextRouter has no network/LLM dependencies.
        
        TICKET-330: MockContextRouter must work offline without Ollama.
        """
        router = MockContextRouter()
        
        # Should be available without any network setup
        self.assertTrue(router.available)
        self.assertIsNone(router.llm_client)  # No LLM client needed
        
        # Should work with any command
        result = router.get_requirements("Commande test")
        self.assertIsInstance(result, list)


class TestTicket330RobustnessFix(unittest.TestCase):
    """Test TICKET-330 FIX 2: Activate Auto-Repair for missing arguments"""

    def setUp(self):
        """Set up ReasonerLLM with mock backend"""
        self.llm = ReasonerLLM(backend="mock")

    def test_auto_repair_method_exists(self):
        """
        Verify _attempt_auto_repair method exists in ReasonerLLM.
        
        TICKET-330: Auto-repair is the self-healing mechanism.
        """
        self.assertTrue(hasattr(self.llm, '_attempt_auto_repair'))
        self.assertTrue(callable(self.llm._attempt_auto_repair))

    def test_auto_repair_prompt_contains_mandatory_args(self):
        """
        Verify auto-repair prompt contains instructions for mandatory arguments.
        
        TICKET-330: Prompt must specify that app_name is MANDATORY for open_application.
        """
        prompt = self.llm._build_auto_repair_prompt("ouvre Safari")
        
        # Should contain the CRITICAL INSTRUCTIONS
        self.assertIn("INSTRUCTIONS CRITIQUES", prompt)
        self.assertIn("open_application", prompt)
        self.assertIn("app_name", prompt)
        self.assertIn("OBLIGATOIRE", prompt.upper())  # "MANDATORY" or "OBLIGATOIRE"

    def test_auto_repair_triggered_on_empty_steps(self):
        """
        Verify auto-repair is triggered when plan has no steps.
        
        TICKET-330: If the model forgets app_name, the plan is empty and 
        auto-repair should be triggered.
        """
        # First call returns empty, then auto-repair is called
        call_count = [0]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            call_count[0] += 1
            if call_count[0] == 1:
                return '{"steps": []}'  # Empty plan triggers repair
            return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        with patch.object(self.llm, '_run_inference', side_effect=mock_inference):
            with patch.object(self.llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.side_effect = [
                    {"steps": []},
                    {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}
                ]
                
                result = self.llm.generate_structured_plan("ouvre Safari")
        
        # Should have called inference at least twice (initial + repair)
        self.assertGreaterEqual(call_count[0], 2)
        
        # Result should have steps after repair
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0)

    def test_auto_repair_uses_json_mode(self):
        """
        Verify auto-repair forces JSON mode to prevent invalid output.
        
        TICKET-330: Auto-repair should use json_mode=True to force valid JSON.
        """
        json_mode_used = [False]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            if json_mode:
                json_mode_used[0] = True
            return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        with patch.object(self.llm, '_run_inference', side_effect=mock_inference):
            with patch.object(self.llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.return_value = {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}
                
                self.llm._attempt_auto_repair("ouvre Safari")
        
        self.assertTrue(json_mode_used[0], "Auto-repair must use json_mode=True")

    def test_first_attempt_uses_json_mode(self):
        """
        Verify FIRST ATTEMPT in generate_structured_plan uses json_mode=True.
        
        CRITICAL FIX: Without json_mode on the first attempt, Qwen 2.5 generates
        verbose text responses filling 1024 tokens (~94 seconds). With json_mode,
        output is constrained to valid JSON, stopping at the closing brace (~2 seconds).
        
        This is the key fix for the inference latency issue.
        """
        first_attempt_json_mode = [False]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            # Track json_mode on first call (not auto-repair)
            if not first_attempt_json_mode[0]:  # Only record first call
                first_attempt_json_mode[0] = json_mode
            return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        with patch.object(self.llm, '_run_inference', side_effect=mock_inference):
            with patch.object(self.llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.return_value = {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}
                
                self.llm.generate_structured_plan("ouvre Safari")
        
        self.assertTrue(first_attempt_json_mode[0], 
            "FIRST ATTEMPT must use json_mode=True to prevent 94s inference latency. "
            "Without json_mode, Qwen fills 1024 tokens with verbose text.")

    def test_generate_structured_plan_returns_valid_plan(self):
        """
        Verify generate_structured_plan returns valid plan with mock backend.
        
        TICKET-330: After fixes, plan generation should succeed.
        """
        result = self.llm.generate_structured_plan("ouvre Chrome et va sur YouTube", language="fr")
        
        # Should have steps
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0)
        
        # First step should be open_application
        first_step = result["steps"][0]
        self.assertEqual(first_step.get("module"), "system")
        self.assertEqual(first_step.get("action"), "open_application")
        self.assertIn("app_name", first_step.get("args", {}))

    def test_all_inference_methods_use_json_mode(self):
        """
        CRITICAL: Verify ALL LLM inference methods use json_mode=True.
        
        Without json_mode=True, Qwen 2.5 generates verbose text filling 1024 tokens,
        taking ~90-94 seconds on M4. With json_mode, it stops at the closing brace (~2s).
        
        This test ensures we don't regress on this critical performance fix.
        """
        json_mode_calls = []
        
        def track_json_mode(prompt, max_tokens=512, timeout_override=None, json_mode=False):
            json_mode_calls.append({
                'method': 'inference',
                'json_mode': json_mode,
                'max_tokens': max_tokens,
            })
            # Return valid JSON for all expected response formats
            return '{"intents": [{"intent": "open_app"}], "steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}], "task": "test", "children": [], "explanation": "test"}'
        
        with patch.object(self.llm, '_run_inference', side_effect=track_json_mode):
            # Test parse_command
            try:
                self.llm.parse_command("ouvre Safari", language="fr")
            except Exception:
                pass  # May fail on parse, but we only care about json_mode
            
            # Test generate_plan
            try:
                self.llm.generate_plan("open_app", {"app_name": "Safari"})
            except Exception:
                pass
            
            # Test generate_structured_plan
            try:
                with patch.object(self.llm, '_parse_structured_plan_response', return_value={"steps": [{"module": "system", "action": "test", "args": {}}]}):
                    self.llm.generate_structured_plan("ouvre Safari")
            except Exception:
                pass
            
            # Test replan
            try:
                with patch.object(self.llm, '_parse_structured_plan_response', return_value={"steps": [{"module": "system", "action": "test", "args": {}}]}):
                    self.llm.replan({"module": "test", "action": "test"}, "test error")
            except Exception:
                pass
            
            # Test decompose_task
            try:
                self.llm.decompose_task("test task")
            except Exception:
                pass
        
        # Verify ALL calls used json_mode=True
        self.assertGreater(len(json_mode_calls), 0, "No inference calls were tracked")
        
        for i, call in enumerate(json_mode_calls):
            self.assertTrue(
                call['json_mode'],
                f"Call {i+1} did NOT use json_mode=True. "
                f"This will cause 90s+ inference latency on M4 Mac! "
                f"Call details: {call}"
            )


class TestTicket330ExpectedResults(unittest.TestCase):
    """Test TICKET-330 Expected Results from the issue description"""

    def test_expected_log_message_context_router(self):
        """
        Verify the expected log message appears: 
        "⚡️ PERFORMANCE: ContextRouter forcé en mode SIGNAL (0ms)"
        """
        import logging
        from janus.runtime.core.pipeline import JanusPipeline
        
        # Capture log messages
        log_messages = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())
        
        # Set up log capture
        logger = logging.getLogger("janus.core.pipeline")
        handler = LogCapture()
        logger.addHandler(handler)
        original_level = logger.level
        logger.setLevel(logging.INFO)
        
        try:
            mock_settings, mock_memory = create_mock_pipeline_dependencies()
            
            pipeline = JanusPipeline(
                settings=mock_settings,
                memory=mock_memory,
                enable_voice=False,
                enable_llm_reasoning=False,
                enable_vision=False,
                enable_learning=False,
                enable_tts=False,
                load_context_from_recent=False,
            )
            
            # Trigger context_router lazy loading
            _ = pipeline.context_router
            
            # Check for expected log message
            expected_msg = "⚡️ PERFORMANCE: ContextRouter forcé en mode SIGNAL (0ms)"
            found = any(expected_msg in msg for msg in log_messages)
            
            self.assertTrue(found, f"Expected log message not found. Messages: {log_messages}")
            
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_expected_log_message_auto_repair_success(self):
        """
        Verify auto-repair is called and returns valid plan after initial empty plan.
        
        The log message "✅ Auto-réparation réussie !" is emitted when auto-repair
        succeeds. We verify this behavior by checking that:
        1. Auto-repair is triggered on empty plan
        2. Result has valid steps after repair
        """
        llm = ReasonerLLM(backend="mock")
        
        # Mock to return empty first, triggering auto-repair
        call_count = [0]
        
        def mock_inference(prompt, max_tokens=1024, timeout_override=None, json_mode=False):
            call_count[0] += 1
            # First call returns empty to trigger repair
            if call_count[0] == 1:
                return '{"steps": []}'
            return '{"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}'
        
        with patch.object(llm, '_run_inference', side_effect=mock_inference):
            with patch.object(llm, '_parse_structured_plan_response') as mock_parse:
                mock_parse.side_effect = [
                    {"steps": []},  # Initial parse returns empty
                    {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}]}  # Repair parse returns valid
                ]
                
                result = llm.generate_structured_plan("ouvre Safari")
        
        # Verify auto-repair was needed and executed (inference called twice)
        self.assertGreaterEqual(call_count[0], 2, "Auto-repair should have triggered a second inference call")
        
        # Verify result has valid steps after repair
        self.assertIn("steps", result)
        self.assertGreater(len(result["steps"]), 0, "Result should have steps after auto-repair")


if __name__ == "__main__":
    unittest.main()
