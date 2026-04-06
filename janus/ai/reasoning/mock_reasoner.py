"""
MockReasoner - Isolated mock logic for testing ReasonerLLM

This module contains all hardcoded mock inference logic, separated from
the production ReasonerLLM code for better maintainability.

Fixtures are loaded from JSON files for easy configuration and updates.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class MockReasoner:
    """
    Mock reasoner for testing purposes.
    
    Uses JSON fixtures to provide deterministic responses for different
    prompt types without requiring a real LLM.
    """
    
    def __init__(self, fixtures_dir: Optional[Path] = None):
        """
        Initialize MockReasoner with fixtures.
        
        Args:
            fixtures_dir: Path to fixtures directory (defaults to ./fixtures/)
        """
        if fixtures_dir is None:
            fixtures_dir = Path(__file__).parent / "fixtures"
        
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures: Dict[str, Any] = {}
        self._load_fixtures()
    
    def _load_fixtures(self):
        """Load all fixture files from the fixtures directory."""
        fixture_files = [
            "parse_command.json",
            "react_decision.json",
            "burst_decision.json",
            "reflex_action.json",
            "structured_plan.json",
            "v4_analysis.json",
        ]
        
        for filename in fixture_files:
            fixture_path = self.fixtures_dir / filename
            if fixture_path.exists():
                with open(fixture_path, 'r', encoding='utf-8') as f:
                    fixture_name = filename.replace('.json', '')
                    self.fixtures[fixture_name] = json.load(f)
    
    def generate_response(self, prompt: str) -> str:
        """
        Generate mock response based on prompt content.
        
        Args:
            prompt: Input prompt to analyze
            
        Returns:
            JSON string response appropriate for the prompt type
        """
        prompt_lower = prompt.lower()
        
        # Try each fixture type in priority order
        
        # 1. ReAct prompts (highest priority - most specific)
        response = self._check_react_prompt(prompt_lower)
        if response:
            return response
        
        # 2. Reflex prompts
        response = self._check_reflex_prompt(prompt_lower)
        if response:
            return response
        
        # 3. V4 format
        response = self._check_v4_prompt(prompt_lower)
        if response:
            return response
        
        # 4. Structured plan (V3)
        response = self._check_structured_plan_prompt(prompt, prompt_lower)
        if response:
            return response
        
        # 5. Command parsing (most common)
        response = self._check_parse_command_prompt(prompt, prompt_lower)
        if response:
            return response
        
        # Default fallback
        return self._get_default_response()
    
    def _check_react_prompt(self, prompt_lower: str) -> Optional[str]:
        """Check if prompt matches ReAct pattern."""
        fixture = self.fixtures.get("react_decision", {})
        patterns = fixture.get("patterns", {}).get("react_prompt", {})
        keywords = patterns.get("keywords", [])
        
        if any(kw in prompt_lower for kw in keywords):
            return json.dumps(patterns["response"])
        return None
    
    def _check_reflex_prompt(self, prompt_lower: str) -> Optional[str]:
        """Check if prompt matches reflex pattern."""
        fixture = self.fixtures.get("reflex_action", {})
        patterns = fixture.get("patterns", {}).get("reflex_prompt", {})
        keywords = patterns.get("keywords", [])
        
        if any(kw in prompt_lower for kw in keywords):
            return json.dumps(patterns["response"])
        return None
    
    def _check_v4_prompt(self, prompt_lower: str) -> Optional[str]:
        """Check if prompt matches V4 format pattern."""
        fixture = self.fixtures.get("v4_analysis", {})
        patterns = fixture.get("patterns", {}).get("v4_prompt", {})
        keywords = patterns.get("keywords", [])
        
        if any(kw in prompt_lower for kw in keywords):
            return json.dumps(patterns["response"])
        return None
    
    def _check_structured_plan_prompt(self, prompt: str, prompt_lower: str) -> Optional[str]:
        """Check if prompt matches structured plan (V3) pattern."""
        fixture = self.fixtures.get("structured_plan", {})
        patterns = fixture.get("patterns", {}).get("plan_prompt", {})
        keywords = patterns.get("keywords", [])
        
        # Check if keywords match (must have at least 2 keywords or specific phrase)
        if "génère le plan json" in prompt_lower or \
           ("steps" in prompt_lower and "module" in prompt_lower):
            
            # Try to extract app name using word boundaries
            apps = patterns.get("apps", [])
            for app in apps:
                if self._match_word_boundary(app, prompt_lower):
                    # Use template replacement helper
                    return self._apply_template(
                        patterns["response_template"],
                        {"app_name": app.capitalize()}
                    )
            
            # No app found, return fallback
            return json.dumps(patterns["fallback_response"])
        
        return None
    
    def _check_parse_command_prompt(self, prompt: str, prompt_lower: str) -> Optional[str]:
        """Check if prompt matches command parsing pattern."""
        fixture = self.fixtures.get("parse_command", {})
        patterns = fixture.get("patterns", {})
        
        # Extract command text from prompt
        command_text = self._extract_command_text(prompt, prompt_lower)
        
        if not command_text:
            # Not a parse_command prompt
            return None
        
        # Check open_app pattern
        open_app = patterns.get("open_app", {})
        if any(kw in command_text for kw in open_app.get("keywords", [])):
            # Try to find app name using word boundaries
            apps = open_app.get("apps", [])
            for app in apps:
                if self._match_word_boundary(app, command_text):
                    # Use template replacement helper
                    return self._apply_template(
                        open_app["response_template"],
                        {"app_name": app.capitalize()}
                    )
            
            # No specific app found, return fallback
            return json.dumps(open_app["fallback_response"])
        
        # Check paste pattern
        paste = patterns.get("paste", {})
        if any(kw in command_text for kw in paste.get("keywords", [])):
            return json.dumps(paste["response"])
        
        # Check copy pattern
        copy = patterns.get("copy", {})
        if any(kw in command_text for kw in copy.get("keywords", [])):
            return json.dumps(copy["response"])
        
        # Default for parse_command
        return json.dumps(patterns.get("default", {}).get("response", {}))
    
    def _extract_command_text(self, prompt: str, prompt_lower: str) -> str:
        """
        Extract command text from parse_command prompt.
        
        Args:
            prompt: Original prompt
            prompt_lower: Lowercase version of prompt
            
        Returns:
            Extracted command text (lowercase) or empty string if not found
        """
        command_text = ""
        
        if "commande:" in prompt_lower:
            # French format
            start_idx = prompt_lower.find("commande:") + 9
            command_text = prompt[start_idx:].split("\n")[0].strip().lower()
        elif "command:" in prompt_lower:
            # English format
            start_idx = prompt_lower.find("command:") + 8
            command_text = prompt[start_idx:].split("\n")[0].strip().lower()
        
        return command_text
    
    def _match_word_boundary(self, word: str, text: str) -> bool:
        """
        Match word with word boundaries to avoid false positives.
        
        Args:
            word: Word to search for
            text: Text to search in (should be lowercase)
            
        Returns:
            True if word is found with word boundaries, False otherwise
        """
        import re
        # Use word boundary regex to avoid matching partial words
        # \b ensures we match whole words only
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        return bool(re.search(pattern, text))
    
    def _apply_template(self, template: Dict[str, Any], replacements: Dict[str, str]) -> str:
        """
        Apply template replacements to a JSON template.
        
        Args:
            template: Template dict with {placeholder} values
            replacements: Dict mapping placeholder names to replacement values
            
        Returns:
            JSON string with placeholders replaced
        """
        # Convert to JSON string
        template_str = json.dumps(template)
        
        # Replace each placeholder
        for key, value in replacements.items():
            placeholder = "{" + key + "}"
            template_str = template_str.replace(placeholder, value)
        
        return template_str
    
    def _get_default_response(self) -> str:
        """Get default response when no pattern matches."""
        fixture = self.fixtures.get("parse_command", {})
        default = fixture.get("patterns", {}).get("default", {})
        return json.dumps(default.get("response", {
            "intents": [{"intent": "unknown", "parameters": {}, "confidence": 0.3}]
        }))
