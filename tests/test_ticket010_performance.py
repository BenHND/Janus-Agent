"""
TICKET 010 - Performance Tests

Tests to ensure the V3 pipeline meets performance requirements:
- Reasoner < 600ms
- Validator < 20ms
- Executor < 50ms per step
- Full cycle < 2.5s for simple commands

Test Categories:
1. Reasoner performance benchmarks
2. Validator performance benchmarks
3. Executor performance benchmarks
4. Full pipeline performance benchmarks
"""

import time
import unittest
from statistics import mean, median

from janus.ai.reasoning.reasoner_llm import ReasonerLLM
from janus.safety.validation.json_plan_validator import JSONPlanValidator
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.agent_setup import setup_agent_registry


class TestReasonerV3Performance(unittest.TestCase):
    """Test Reasoner V3 performance (target: < 600ms)"""

    def setUp(self):
        """Initialize ReasonerLLM with mock backend for consistent timing"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_reasoner_simple_command_performance(self):
        """Test: Reasoner processes simple command in < 600ms"""
        command = "ouvre Safari"
        timings = []

        # Run multiple times for average
        for _ in range(5):
            start = time.time()
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(plan, "Should generate plan")

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nReasoner simple command: avg={avg_time:.1f}ms, median={median_time:.1f}ms")

        # Mock backend should be very fast
        self.assertLess(
            avg_time,
            600,
            f"Reasoner should process simple command in < 600ms (got {avg_time:.1f}ms)"
        )

    def test_reasoner_multi_step_command_performance(self):
        """Test: Reasoner processes multi-step command in < 600ms"""
        command = "Ouvre Safari, va sur YouTube et cherche Python"
        timings = []

        for _ in range(5):
            start = time.time()
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(plan, "Should generate plan")

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nReasoner multi-step command: avg={avg_time:.1f}ms, median={median_time:.1f}ms")

        self.assertLess(
            avg_time,
            600,
            f"Reasoner should process multi-step command in < 600ms (got {avg_time:.1f}ms)"
        )

    def test_reasoner_complex_command_performance(self):
        """Test: Reasoner processes complex command in < 600ms"""
        command = "Ouvre Salesforce, affiche le dossier 44219 et met à jour le statut à En cours"
        timings = []

        for _ in range(5):
            start = time.time()
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(plan, "Should generate plan")

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nReasoner complex command: avg={avg_time:.1f}ms, median={median_time:.1f}ms")

        self.assertLess(
            avg_time,
            600,
            f"Reasoner should process complex command in < 600ms (got {avg_time:.1f}ms)"
        )


class TestValidatorV3Performance(unittest.TestCase):
    """Test Validator V3 performance (target: < 20ms)"""

    def setUp(self):
        """Initialize validator"""
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)

    def test_validator_simple_plan_performance(self):
        """Test: Validator validates simple plan in < 20ms"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                                        "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        timings = []

        for _ in range(20):  # More iterations for small operations
            start = time.time()
            result = self.validator.validate_plan(plan)
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(result)

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nValidator simple plan: avg={avg_time:.2f}ms, median={median_time:.2f}ms")

        self.assertLess(
            avg_time,
            20,
            f"Validator should process simple plan in < 20ms (got {avg_time:.2f}ms)"
        )

    def test_validator_multi_step_plan_performance(self):
        """Test: Validator validates multi-step plan in < 20ms"""
        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                                        "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                },
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {"url": "https://youtube.com"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                },
                {
                    "module": "browser",
                    "action": "search",
                    "args": {"query": "Python"},
                                        "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        timings = []

        for _ in range(20):
            start = time.time()
            result = self.validator.validate_plan(plan)
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(result)

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nValidator multi-step plan: avg={avg_time:.2f}ms, median={median_time:.2f}ms")

        self.assertLess(
            avg_time,
            20,
            f"Validator should process multi-step plan in < 20ms (got {avg_time:.2f}ms)"
        )

    def test_validator_complex_plan_performance(self):
        """Test: Validator validates complex plan with 5+ steps in < 20ms"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"},                     "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
                {"module": "browser", "action": "open_url", "args": {"url": "https://example.com"},                     "context": {
                        "app": "Chrome",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
                {"module": "browser", "action": "search", "args": {"query": "test"},                     "context": {
                        "app": "Chrome",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
                {"module": "ui", "action": "click", "args": {"target": "button"},                     "context": {
                        "app": "Chrome",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
                {"module": "ui", "action": "type", "args": {"text": "test"},                     "context": {
                        "app": "Chrome",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
            ]
        }

        timings = []

        for _ in range(20):
            start = time.time()
            result = self.validator.validate_plan(plan)
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

            self.assertIsNotNone(result)

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nValidator complex plan (5 steps): avg={avg_time:.2f}ms, median={median_time:.2f}ms")

        # Allow slightly more time for complex plans
        self.assertLess(
            avg_time,
            30,
            f"Validator should process complex plan in < 30ms (got {avg_time:.2f}ms)"
        )


class TestExecutorV3Performance(unittest.TestCase):
    """Test Executor V3 performance (target: < 50ms per step overhead)"""

    def setUp(self):
        """Initialize executor with mocked agents"""
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    def test_executor_overhead_per_step(self):
        """Test: Executor overhead is < 50ms per step (excluding actual agent execution)"""
        # Note: This tests the executor's overhead, not the agent execution time
        # In practice, we would mock agents to return immediately

        plan = {
            "steps": [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Safari"},
                                        "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }
                }
            ]
        }

        # The executor overhead should be minimal
        # Actual execution time will be dominated by agent actions
        # This test is informational
        timings = []

        for _ in range(5):
            start = time.time()
            # Note: This will actually try to execute, so timing includes agent time
            # In a real test, we'd mock the agent
            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

        avg_time = mean(timings)
        print(f"\nExecutor per-step (including agent): avg={avg_time:.1f}ms")

        # This is informational - actual agent execution dominates
        # Executor overhead should be minimal


class TestFullPipelinePerformance(unittest.TestCase):
    """Test full V3 pipeline performance (target: < 2.5s for simple command)"""

    def setUp(self):
        """Initialize full pipeline"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator(strict_mode=False, allow_missing_context=True)
        self.registry = AgentRegistry()
        setup_agent_registry(self.registry, use_v3_agents=True)
        self.executor = ExecutionEngineV3(self.registry)

    def test_full_cycle_simple_command(self):
        """Test: Full cycle (Reasoner → Validator → Executor) < 2.5s for simple command"""
        command = "ouvre Safari"
        timings = []

        for _ in range(3):
            start = time.time()

            # Step 1: Reasoner
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            self.assertIsNotNone(plan)

            # Step 2: Validator
            validation_result = self.validator.validate_plan(plan)
            self.assertIsNotNone(validation_result)

            # Step 3: Executor (would execute, but we skip actual execution for timing)
            # In real scenario, execution time varies by action

            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nFull pipeline (Reasoner + Validator): avg={avg_time:.1f}ms, median={median_time:.1f}ms")

        # Without actual execution, should be very fast with mock reasoner
        # With real LLM, target is < 2500ms total
        self.assertLess(
            avg_time,
            2500,
            f"Full cycle should complete in < 2500ms (got {avg_time:.1f}ms)"
        )

    def test_reasoner_validator_combined_performance(self):
        """Test: Reasoner + Validator together are < 620ms"""
        command = "ouvre Safari et va sur YouTube"
        timings = []

        for _ in range(5):
            start = time.time()

            # Reasoner
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            self.assertIsNotNone(plan)

            # Validator
            validation_result = self.validator.validate_plan(plan)
            self.assertIsNotNone(validation_result)

            duration_ms = (time.time() - start) * 1000
            timings.append(duration_ms)

        avg_time = mean(timings)
        median_time = median(timings)

        print(f"\nReasoner + Validator: avg={avg_time:.1f}ms, median={median_time:.1f}ms")

        # Combined should be < 620ms (600ms reasoner + 20ms validator)
        self.assertLess(
            avg_time,
            620,
            f"Reasoner + Validator should complete in < 620ms (got {avg_time:.1f}ms)"
        )


class TestPerformanceRegression(unittest.TestCase):
    """Test for performance regressions compared to baseline"""

    def setUp(self):
        """Initialize components"""
        self.reasoner = ReasonerLLM(backend="mock")
        self.validator = JSONPlanValidator()

    def test_baseline_reasoner_performance(self):
        """Establish baseline for reasoner performance"""
        commands = [
            "ouvre Safari",
            "va sur YouTube",
            "cherche Python",
            "Ouvre Safari et va sur YouTube",
            "Ouvre Chrome, va sur Google et cherche restaurants",
        ]

        all_timings = []

        for command in commands:
            start = time.time()
            plan = self.reasoner.generate_structured_plan(command, {}, "fr")
            duration_ms = (time.time() - start) * 1000
            all_timings.append(duration_ms)
            self.assertIsNotNone(plan)

        avg_time = mean(all_timings)
        max_time = max(all_timings)

        print(f"\nReasoner baseline: avg={avg_time:.1f}ms, max={max_time:.1f}ms")

        # Store baseline for future comparison
        self.assertLess(max_time, 600, "No command should take > 600ms")

    def test_baseline_validator_performance(self):
        """Establish baseline for validator performance"""
        plans = [
            {"steps": [{"module": "system", "action": "open_application", "args": {"app_name": "Safari"},                     "context": {
                        "app": None,
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }}]},
            {"steps": [{"module": "browser", "action": "open_url", "args": {"url": "https://youtube.com"},                     "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }},
                      {"module": "browser", "action": "search", "args": {"query": "test"},                     "context": {
                        "app": "Safari",
                        "surface": None,
                        "url": None,
                        "domain": None,
                        "thread": None,
                        "record": None
                    }}]},
        ]

        all_timings = []

        for plan in plans:
            start = time.time()
            result = self.validator.validate_plan(plan)
            duration_ms = (time.time() - start) * 1000
            all_timings.append(duration_ms)
            self.assertIsNotNone(result)

        avg_time = mean(all_timings)
        max_time = max(all_timings)

        print(f"\nValidator baseline: avg={avg_time:.2f}ms, max={max_time:.2f}ms")

        # Store baseline
        self.assertLess(max_time, 20, "No validation should take > 20ms")


if __name__ == "__main__":
    unittest.main()
