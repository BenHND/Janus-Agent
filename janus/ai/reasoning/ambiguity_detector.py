"""
Ambiguity Detector - Detects ambiguities in user commands for clarification.

This module analyzes commands and system state to identify situations that require
user clarification before execution.
"""
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class AmbiguityDetector:
    """
    Detects ambiguities in commands that require clarification.
    
    Detects:
    - Multiple file matches
    - Ambiguous application names
    - Missing required context
    """
    
    def __init__(self):
        """Initialize ambiguity detector"""
        self.common_app_aliases = {
            "chrome": ["Google Chrome", "Chrome Canary", "Chromium"],
            "code": ["Visual Studio Code", "VSCode", "Code - OSS"],
            "terminal": ["Terminal", "iTerm", "Alacritty"],
            "firefox": ["Firefox", "Firefox Developer Edition", "Firefox Nightly"],
        }
    
    def detect_file_ambiguity(
        self, file_pattern: str, search_path: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Detect if a file pattern matches multiple files.
        
        Args:
            file_pattern: File name or pattern to search for
            search_path: Optional directory to search in (defaults to current)
            
        Returns:
            Tuple of (is_ambiguous, list_of_matches)
        """
        if not file_pattern:
            return False, []
        
        try:
            search_dir = Path(search_path) if search_path else Path.cwd()
            
            # Handle exact path
            if file_pattern.startswith("/") or file_pattern.startswith("~"):
                exact_path = Path(file_pattern).expanduser()
                if exact_path.exists():
                    return False, [str(exact_path)]
                return False, []
            
            # Search for matching files
            matches = []
            
            # Try exact match first
            exact = search_dir / file_pattern
            if exact.exists():
                matches.append(str(exact))
            
            # Try glob pattern
            try:
                for match in search_dir.glob(f"**/{file_pattern}"):
                    if match.is_file() and str(match) not in matches:
                        matches.append(str(match))
                        if len(matches) >= 5:  # Limit to 5 matches
                            break
            except Exception as e:
                logger.debug(f"Glob search failed: {e}")
            
            # Check for ambiguity
            is_ambiguous = len(matches) > 1
            
            if is_ambiguous:
                logger.info(f"File ambiguity detected: '{file_pattern}' matches {len(matches)} files")
            
            return is_ambiguous, matches
            
        except Exception as e:
            logger.warning(f"Error detecting file ambiguity: {e}")
            return False, []
    
    def detect_app_ambiguity(self, app_name: str) -> Tuple[bool, List[str]]:
        """
        Detect if an app name is ambiguous.
        
        Args:
            app_name: Application name to check
            
        Returns:
            Tuple of (is_ambiguous, list_of_options)
        """
        if not app_name:
            return False, []
        
        # Check common aliases
        app_lower = app_name.lower()
        
        for alias, variants in self.common_app_aliases.items():
            if alias in app_lower or app_lower in alias:
                logger.info(f"App ambiguity detected: '{app_name}' could be {variants}")
                return True, variants
        
        return False, []
    
    def detect_missing_context(
        self, action: str, parameters: dict
    ) -> Tuple[bool, str]:
        """
        Detect if required context is missing for an action.
        
        Args:
            action: Action to perform
            parameters: Current parameters
            
        Returns:
            Tuple of (is_missing, missing_parameter_description)
        """
        required_params = {
            "open_file": "file_path",
            "save_file": "file_path",
            "delete_file": "file_path",
            "open_app": "app_name",
            "navigate": "url",
            "click": "target",
            "type_text": "text",
        }
        
        if action in required_params:
            required = required_params[action]
            if required not in parameters or not parameters[required]:
                logger.info(f"Missing context for {action}: {required} is required")
                return True, f"Missing required parameter: {required}"
        
        return False, ""
    
    def analyze_command(
        self, command: str, intent_action: str, intent_parameters: dict
    ) -> dict:
        """
        Analyze a command for all types of ambiguity.
        
        Args:
            command: User's command text
            intent_action: Detected intent action
            intent_parameters: Intent parameters
            
        Returns:
            Dict with ambiguity information:
            {
                "needs_clarification": bool,
                "ambiguity_type": str or None,
                "options": list or None,
                "message": str or None
            }
        """
        result = {
            "needs_clarification": False,
            "ambiguity_type": None,
            "options": None,
            "message": None,
        }
        
        # Check for file ambiguity
        if "file_path" in intent_parameters:
            file_path = intent_parameters["file_path"]
            if file_path and "*" in file_path or not file_path.startswith("/"):
                is_ambiguous, matches = self.detect_file_ambiguity(file_path)
                if is_ambiguous:
                    result["needs_clarification"] = True
                    result["ambiguity_type"] = "multiple_files"
                    result["options"] = matches
                    result["message"] = f"Multiple files match '{file_path}'"
                    return result
        
        # Check for app ambiguity
        if "app_name" in intent_parameters:
            app_name = intent_parameters["app_name"]
            is_ambiguous, options = self.detect_app_ambiguity(app_name)
            if is_ambiguous:
                result["needs_clarification"] = True
                result["ambiguity_type"] = "ambiguous_app"
                result["options"] = options
                result["message"] = f"'{app_name}' could refer to multiple applications"
                return result
        
        # Check for missing context
        is_missing, message = self.detect_missing_context(
            intent_action, intent_parameters
        )
        if is_missing:
            result["needs_clarification"] = True
            result["ambiguity_type"] = "missing_context"
            result["options"] = []
            result["message"] = message
            return result
        
        return result
