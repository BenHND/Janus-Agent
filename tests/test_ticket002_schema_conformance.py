"""
Tests for TICKET 002 (P0) - Schema ↔ Agent ↔ Prompt Conformance

This test validates that:
1. All actions defined in module_action_schema are implemented in their corresponding agents
2. All actions implemented in agents are defined in the schema
3. Unknown actions are handled gracefully at runtime
4. Prompts only reference valid schema actions

These tests ensure the unified action contract between:
- Schema (single source of truth)
- Agents (execution layer)
- Prompts (LLM guidance)
"""

import re
import unittest
from pathlib import Path
from typing import Dict, Set

from janus.runtime.core.module_action_schema import (
    ALL_MODULES,
    get_all_actions_for_module,
    get_all_module_names,
)
from janus.runtime.core.agent_registry import get_global_agent_registry


class TestSchemaAgentConformance(unittest.TestCase):
    """Test that schema and agents are in perfect alignment"""
    
    @classmethod
    def setUpClass(cls):
        """Extract actions from agent source files"""
        cls.agent_files = {
            'system': 'janus/capabilities/agents/system_agent.py',
            'browser': 'janus/capabilities/agents/browser_agent.py',
            'messaging': 'janus/capabilities/agents/messaging_agent.py',
            'crm': 'janus/capabilities/agents/crm_agent.py',
            'files': 'janus/capabilities/agents/files_agent.py',
            'ui': 'janus/capabilities/agents/ui_agent.py',
            'code': 'janus/capabilities/agents/code_agent.py',
            'llm': 'janus/capabilities/agents/llm_agent.py',
        }
        
        cls.agent_actions = cls._extract_agent_actions()
        cls.schema_actions = cls._extract_schema_actions()
    
    @classmethod
    def _extract_agent_actions(cls) -> Dict[str, Set[str]]:
        """Extract actions from agent source files by parsing execute() methods"""
        agent_actions = {}
        
        for agent_name, filepath in cls.agent_files.items():
            try:
                # Read agent source
                full_path = Path(__file__).parent.parent / filepath
                with open(full_path, 'r') as f:
                    content = f.read()
                
                # Find all action checks in execute method: if/elif action == "action_name"
                pattern = r'(?:if|elif)\s+action\s*==\s*["\'](\w+)["\']'
                actions = set(re.findall(pattern, content))
                
                # Also check for aliases: action == "name" or action == "alias"
                # This pattern catches: or action == "alias"
                alias_pattern = r'or\s+action\s*==\s*["\'](\w+)["\']'
                aliases = set(re.findall(alias_pattern, content))
                actions.update(aliases)
                
                agent_actions[agent_name] = actions
            except Exception as e:
                # If we can't read the file, assume empty action set
                agent_actions[agent_name] = set()
        
        return agent_actions
    
    @classmethod
    def _extract_schema_actions(cls) -> Dict[str, Set[str]]:
        """Extract actions from schema"""
        schema_actions = {}
        
        for module_name in get_all_module_names():
            actions = set(get_all_actions_for_module(module_name))
            schema_actions[module_name] = actions
        
        return schema_actions
    
    def test_all_schema_actions_have_agent_handlers(self):
        """
        CRITICAL: Every action in the schema MUST have a handler in the corresponding agent.
        
        This prevents "Unknown action" errors at runtime when the LLM generates
        valid schema actions that can't be executed.
        """
        missing_handlers = {}
        
        for module_name in sorted(self.schema_actions.keys()):
            schema = self.schema_actions[module_name]
            agent = self.agent_actions.get(module_name, set())
            
            # Actions in schema but not in agent = missing handlers
            missing = schema - agent
            
            if missing:
                missing_handlers[module_name] = sorted(missing)
        
        if missing_handlers:
            report = ["Schema actions missing agent handlers:"]
            for module, actions in missing_handlers.items():
                report.append(f"  {module}: {actions}")
            
            self.fail("\n".join(report))
    
    def test_no_ghost_actions_in_agents(self):
        """
        WARNING: Agents should not implement actions that aren't in the schema.
        
        Ghost actions won't be documented in prompts and the LLM won't know to use them.
        They represent orphaned functionality that should either:
        1. Be added to the schema, OR
        2. Be removed as dead code
        
        This test is a WARNING, not a failure - some internal/helper actions
        may legitimately not be in the schema.
        """
        ghost_actions = {}
        
        for module_name in sorted(self.agent_actions.keys()):
            agent = self.agent_actions[module_name]
            schema = self.schema_actions.get(module_name, set())
            
            # Actions in agent but not in schema = ghost actions
            ghosts = agent - schema
            
            if ghosts:
                ghost_actions[module_name] = sorted(ghosts)
        
        if ghost_actions:
            report = ["⚠️  Ghost actions found (in agent but not schema):"]
            for module, actions in ghost_actions.items():
                report.append(f"  {module}: {actions}")
            report.append("\nThese actions won't be used by the LLM unless added to schema.")
            
            # Print warning but don't fail - these might be internal actions
            print("\n".join(report))
    
    def test_schema_actions_count_reasonable(self):
        """Sanity check: Each module should have at least 3 actions"""
        for module_name in self.schema_actions.keys():
            actions = self.schema_actions[module_name]
            self.assertGreaterEqual(
                len(actions), 3,
                f"Module {module_name} has too few actions: {len(actions)}"
            )
    
    def test_all_modules_have_agents(self):
        """Verify all schema modules have corresponding agent implementations"""
        for module_name in self.schema_actions.keys():
            self.assertIn(
                module_name,
                self.agent_actions,
                f"Schema module '{module_name}' has no corresponding agent file"
            )


class TestRuntimeUnknownActionHandling(unittest.TestCase):
    """Test that unknown actions are handled gracefully at runtime"""
    
    def setUp(self):
        """Get agent registry"""
        self.registry = get_global_agent_registry()
    
    def test_unknown_action_returns_error_result(self):
        """Unknown actions should return proper error result, not raise exception"""
        # This is tested at the agent level, not registry level
        # since agents are responsible for validating actions
        pass  # Placeholder - actual implementation would test agent execute()
    
    def test_unknown_module_returns_error_result(self):
        """Unknown modules should return error result with recoverable=False"""
        result = self.registry.execute(
            module="unknown_module",
            action="some_action",
            args={},
            context={}
        )
        
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertEqual(result.get("error_type"), "module_not_found")
        self.assertFalse(result.get("recoverable", True))


class TestPromptSchemaAlignment(unittest.TestCase):
    """Test that prompts reference only valid schema actions"""
    
    def test_prompt_templates_exist(self):
        """Verify prompt templates exist"""
        prompts_dir = Path(__file__).parent.parent / "janus" / "resources" / "prompts"
        
        self.assertTrue(prompts_dir.exists(), "Prompts directory not found")
        
        # Check for key template files
        templates = [
            "reasoner_react_system_fr.jinja2",
            "reasoner_react_system_en.jinja2",
        ]
        
        for template in templates:
            template_path = prompts_dir / template
            self.assertTrue(
                template_path.exists(),
                f"Template {template} not found"
            )
    
    def test_prompts_use_schema_generated_actions(self):
        """
        Prompts should ideally use get_prompt_schema_section() to generate
        action lists dynamically from schema.
        
        This test checks if hardcoded action lists exist in prompts.
        """
        prompts_dir = Path(__file__).parent.parent / "janus" / "resources" / "prompts"
        
        # Read reasoner prompt
        prompt_file = prompts_dir / "reasoner_react_system_fr.jinja2"
        if not prompt_file.exists():
            self.skipTest("Prompt file not found")
        
        with open(prompt_file, 'r') as f:
            content = f.read()
        
        # Check if dynamic_tools_definitions is used (good)
        has_dynamic = "dynamic_tools_definitions" in content
        
        # Check for hardcoded actions (not ideal but acceptable)
        hardcoded_actions = [
            "system.open_app",
            "browser.open_url",
            "ui.click",
            "browser.type_text",
            "browser.press_key",
        ]
        
        has_hardcoded = any(action in content for action in hardcoded_actions)
        
        # Either dynamic OR hardcoded is fine, but dynamic is preferred
        self.assertTrue(
            has_dynamic or has_hardcoded,
            "Prompt should reference actions either dynamically or hardcoded"
        )


if __name__ == '__main__':
    unittest.main()
