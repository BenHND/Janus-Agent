"""
Tests for TICKET-336: Pipeline Optimization & Pre-loading

This module tests the three optimizations:
1. Agent warmup for eager initialization
2. Fast-path parsing to avoid double LLM inference
3. UI click argument validation (indirectly via prompt updates)
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAgentRegistryWarmup(unittest.TestCase):
    """Test AgentRegistry.warmup() for eager agent loading."""

    def test_warmup_method_exists(self):
        """Verify AgentRegistry has warmup method."""
        from janus.runtime.core.agent_registry import AgentRegistry

        registry = AgentRegistry()
        self.assertTrue(hasattr(registry, "warmup"))
        self.assertTrue(asyncio.iscoroutinefunction(registry.warmup))

    def test_warmup_empty_registry(self):
        """Test warmup on empty registry."""
        from janus.runtime.core.agent_registry import AgentRegistry

        async def run_test():
            registry = AgentRegistry()
            results = await registry.warmup()
            self.assertEqual(results, {})

        asyncio.run(run_test())

    def test_warmup_with_agents(self):
        """Test warmup with registered agents."""
        from janus.runtime.core.agent_registry import AgentRegistry

        async def run_test():
            registry = AgentRegistry()

            # Create mock agents with different capabilities
            agent_with_warmup = MagicMock()
            agent_with_warmup.warmup = MagicMock(return_value=None)

            # Agent with only is_available (no warmup attribute)
            class MockAgentWithAvailability:
                def is_available(self):
                    return True
            agent_with_availability = MockAgentWithAvailability()
            # Track calls for assertion
            original_is_available = agent_with_availability.is_available
            agent_with_availability.is_available = MagicMock(return_value=True)

            agent_plain = MagicMock(spec=[])  # No special methods

            registry.register("system", agent_with_warmup)
            registry.register("browser", agent_with_availability)
            registry.register("files", agent_plain)

            results = await registry.warmup()

            self.assertEqual(len(results), 3)
            self.assertTrue(results["system"])
            self.assertTrue(results["browser"])
            self.assertTrue(results["files"])
            
            # Verify warmup was called
            agent_with_warmup.warmup.assert_called_once()
            # Verify is_available was called as fallback
            agent_with_availability.is_available.assert_called_once()

        asyncio.run(run_test())

    def test_warmup_handles_errors(self):
        """Test warmup handles agent errors gracefully."""
        from janus.runtime.core.agent_registry import AgentRegistry

        async def run_test():
            registry = AgentRegistry()

            # Agent that raises error
            failing_agent = MagicMock()
            failing_agent.warmup = MagicMock(side_effect=Exception("Init failed"))

            # Normal agent with only is_available (no warmup attribute)
            class MockNormalAgent:
                def is_available(self):
                    return True
            normal_agent = MockNormalAgent()
            normal_agent.is_available = MagicMock(return_value=True)

            registry.register("failing", failing_agent)
            registry.register("normal", normal_agent)

            results = await registry.warmup()

            # Failing agent marked as failed, normal continues
            self.assertFalse(results["failing"])
            self.assertTrue(results["normal"])

        asyncio.run(run_test())


class TestFastPathParsing(unittest.TestCase):
    """Test skip_llm_parsing fast-path for avoiding double LLM inference."""

    def test_skip_llm_parsing_parameter(self):
        """Test skip_llm_parsing parameter exists."""
        from janus.legacy.parser.unified_command_parser import UnifiedCommandParser

        parser = UnifiedCommandParser(skip_llm_parsing=True)
        self.assertTrue(parser.skip_llm_parsing)

        parser = UnifiedCommandParser(skip_llm_parsing=False)
        self.assertFalse(parser.skip_llm_parsing)

    def test_simple_command_fast_path(self):
        """Test simple commands still work with fast-path enabled."""
        from janus.legacy.parser.unified_command_parser import (
            Intent,
            ParserProvider,
            UnifiedCommandParser,
        )

        parser = UnifiedCommandParser(
            provider=ParserProvider.DETERMINISTIC, skip_llm_parsing=True
        )

        # Simple command should parse successfully
        result = parser.parse("ouvre Safari")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intent, Intent.OPEN_APP)
        self.assertGreater(result[0].confidence, 0.5)

    def test_complex_command_fast_path(self):
        """Test complex commands return pass-to-Reasoner result with fast-path."""
        from janus.legacy.parser.unified_command_parser import (
            Intent,
            ParserProvider,
            UnifiedCommandParser,
        )

        parser = UnifiedCommandParser(
            provider=ParserProvider.DETERMINISTIC, skip_llm_parsing=True
        )

        # Complex command should signal "pass to Reasoner"
        result = parser.parse("ouvre Safari et va sur YouTube puis cherche Python")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intent, Intent.UNKNOWN)
        self.assertTrue(result[0].metadata.get("fast_path", False))
        self.assertEqual(result[0].metadata.get("reason"), "Pass to ReasonerV3")

    def test_low_confidence_fast_path(self):
        """Test low confidence commands pass to Reasoner."""
        from janus.legacy.parser.unified_command_parser import (
            Intent,
            ParserProvider,
            UnifiedCommandParser,
        )

        parser = UnifiedCommandParser(
            provider=ParserProvider.DETERMINISTIC,
            skip_llm_parsing=True,
            confidence_threshold=0.9,  # High threshold
        )

        # Ambiguous command should pass to Reasoner
        result = parser.parse("fais quelque chose d'intéressant")
        self.assertEqual(len(result), 1)
        self.assertTrue(
            result[0].intent == Intent.UNKNOWN
            or result[0].confidence < 0.9
        )

    def test_fast_path_preserves_raw_text(self):
        """Test fast-path preserves raw text for Reasoner."""
        from janus.legacy.parser.unified_command_parser import (
            ParserProvider,
            UnifiedCommandParser,
        )

        parser = UnifiedCommandParser(
            provider=ParserProvider.DETERMINISTIC, skip_llm_parsing=True
        )

        text = "ouvre Safari et va sur YouTube"
        result = parser.parse(text)

        # Raw text should be preserved
        self.assertEqual(result[0].raw_text, text)


class TestWarmupAgentsFunction(unittest.TestCase):
    """Test warmup_agents initialization function."""

    def test_warmup_agents_exists(self):
        """Verify warmup_agents function exists."""
        from janus.app.initialization import warmup_agents

        self.assertTrue(asyncio.iscoroutinefunction(warmup_agents))

    def test_warmup_agents_returns_dict(self):
        """Test warmup_agents returns a dictionary."""
        from janus.app.initialization import warmup_agents
        from janus.runtime.core.agent_registry import reset_global_agent_registry

        async def run_test():
            # Reset to get clean slate
            reset_global_agent_registry()
            results = await warmup_agents()
            self.assertIsInstance(results, dict)
            # Should have registered some agents
            self.assertGreater(len(results), 0)

        asyncio.run(run_test())


class TestUIClickPromptRules(unittest.TestCase):
    """Test that UI click rules are present in prompts."""

    def test_french_prompt_has_ui_click_rules(self):
        """Verify French prompt contains ui.click selector/text rules."""
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "janus",
            "resources",
            "prompts",
            "reasoner_v3_system_fr.jinja2",
        )
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key phrases
        self.assertIn("ui.click", content)
        self.assertIn("selector", content)
        self.assertIn("text", content)
        self.assertIn('JAMAIS "target"', content)

    def test_english_prompt_has_ui_click_rules(self):
        """Verify English prompt contains ui.click selector/text rules."""
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "janus",
            "resources",
            "prompts",
            "reasoner_v3_system_en.jinja2",
        )
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key phrases
        self.assertIn("ui.click", content)
        self.assertIn("selector", content)
        self.assertIn("text", content)
        self.assertIn('NEVER "target"', content)


if __name__ == "__main__":
    unittest.main()
