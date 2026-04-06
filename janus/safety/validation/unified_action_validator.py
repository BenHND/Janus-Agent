"""
Unified Action Validator - SAFETY-001

This validator is the SINGLE unified validation and confirmation system for Janus.
It combines:
- Strict schema validation from StrictActionValidator
- Dangerous command detection from ActionValidator
- Risk-based confirmation using RiskLevel from module_action_schema.py (SSOT)

Key principles:
1. Risk level comes ONLY from module_action_schema.py
2. HIGH/CRITICAL actions ALWAYS require confirmation
3. LOW/MEDIUM actions are NOT blocked by arbitrary regex patterns
4. Complete logging of risk_level, requires_confirmation, user_confirmed
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from janus.runtime.core.module_action_schema import (
    RiskLevel,
    auto_correct_action,
    auto_correct_module,
    get_all_actions_for_module,
    get_all_module_names,
    get_module,
    is_valid_action,
    is_valid_module,
    validate_action_step,
)
from janus.logging import get_logger

logger = get_logger("unified_action_validator")


class UnifiedActionValidator:
    """
    Single unified validator for all actions in Janus.
    
    Responsibilities:
    1. Validate actions against module_action_schema.py (strict validation)
    2. Detect dangerous command patterns (security)
    3. Determine if confirmation is required based on RiskLevel (SSOT)
    4. Request user confirmation when needed
    5. Log all validation decisions
    """
    
    def __init__(
        self,
        auto_correct: bool = True,
        allow_fallback: bool = True,
        strict_mode: bool = False,
        confirmation_callback: Optional[Callable] = None
    ):
        """
        Initialize unified validator.
        
        Args:
            auto_correct: Attempt to auto-correct invalid actions using aliases
            allow_fallback: Allow fallback to default safe actions
            strict_mode: Reject everything that's not perfectly valid (no corrections)
            confirmation_callback: Function to call for user confirmation
        """
        self.auto_correct = auto_correct
        self.allow_fallback = allow_fallback
        self.strict_mode = strict_mode
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        
        # Dangerous command patterns for terminal execution (security check)
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Delete root
            r"rm\s+-rf\s+\*",  # Delete all files
            r":\(\)\{ :\|: & \};:",  # Fork bomb - matches :(){ :|:& };:
            r"mkfs\.",  # Format filesystem
            r"dd\s+if=.*of=/dev/",  # Write to disk device
            r"chmod\s+-R\s+777",  # Dangerous permissions
            r"sudo\s+rm",  # Sudo delete
            r"curl.*\|\s*(?:bash|sh)",  # Pipe to shell
            r"wget.*\|\s*(?:bash|sh)",  # Pipe to shell
        ]
        
        # Destructive keywords (word boundary patterns to avoid false positives)
        self.destructive_keywords = [
            (r"\bdelete\b", "delete"),
            (r"\bremove\b", "remove"),
            (r"\brm\b", "rm"),
            (r"\bformat\b", "format"),
            (r"\bwipe\b", "wipe"),
            (r"\bdestroy\b", "destroy"),
        ]
        
        # System-level operation keywords
        self.system_keywords = [
            (r"\bshutdown\b", "shutdown"),
            (r"\breboot\b", "reboot"),
            (r"\bhalt\b", "halt"),
            (r"\bpoweroff\b", "poweroff"),
        ]
        
        # Statistics
        self.stats = {
            "total_validations": 0,
            "valid_actions": 0,
            "corrected_actions": 0,
            "rejected_actions": 0,
            "fallback_actions": 0,
            "confirmations_requested": 0,
            "confirmations_approved": 0,
            "confirmations_denied": 0,
        }
    
    def validate_and_confirm(
        self,
        step: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        auto_correct: Optional[bool] = None,
        normalize: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Optional[RiskLevel], bool]:
        """
        Validate and optionally confirm a single action step.
        
        This is the MAIN entry point for all action validation.
        
        Args:
            step: Step dictionary with "module", "action", "args"
            context: Optional context (session state, etc.)
            auto_correct: Override instance auto_correct setting
            normalize: Normalize action names to canonical form (aliases -> canonical)
        
        Returns:
            Tuple of (is_valid, corrected_step_or_none, error_message_or_none, risk_level, user_confirmed)
        """
        self.stats["total_validations"] += 1
        
        # Use instance setting if not overridden
        if auto_correct is None:
            auto_correct = self.auto_correct and not self.strict_mode
        
        # Step 1: Quick validation first
        is_valid, error = validate_action_step(step)
        
        # Step 2: Get risk level for the action from SSOT (module_action_schema.py)
        risk_level = self._get_risk_level(step)
        
        # Log validation attempt
        logger.info(
            f"Validating action: {step.get('module')}.{step.get('action')} "
            f"(risk_level={risk_level.value if risk_level else 'unknown'})"
        )
        
        if is_valid:
            self.stats["valid_actions"] += 1
            
            # Normalize action names even if already valid (aliases -> canonical)
            corrected_step = step
            if normalize and "module" in step and "action" in step:
                canonical_action = auto_correct_action(step["module"], step["action"])
                if canonical_action and canonical_action != step["action"]:
                    corrected_step = step.copy()
                    corrected_step["action"] = canonical_action
                    logger.debug(f"Normalized action: {step['action']} -> {canonical_action}")
        else:
            # If strict mode, reject immediately
            if self.strict_mode:
                self.stats["rejected_actions"] += 1
                logger.warning(f"Strict validation failed: {error}")
                return False, None, error, None, False
            
            # Try auto-correction
            if auto_correct:
                corrected_step = self._try_correct_step(step)
                if corrected_step:
                    # Validate corrected step
                    is_valid, error = validate_action_step(corrected_step)
                    if is_valid:
                        self.stats["corrected_actions"] += 1
                        logger.info(
                            f"Auto-corrected step: {step['module']}.{step.get('action')} "
                            f"-> {corrected_step['module']}.{corrected_step['action']}"
                        )
                        risk_level = self._get_risk_level(corrected_step)
                    else:
                        corrected_step = None
            else:
                corrected_step = None
            
            # Try fallback if correction didn't work
            if not corrected_step and self.allow_fallback:
                corrected_step = self._get_fallback_step(step, error)
                if corrected_step:
                    self.stats["fallback_actions"] += 1
                    logger.warning(f"Using fallback action: {corrected_step}")
                    risk_level = self._get_risk_level(corrected_step)
                    is_valid = True
            
            # All attempts failed
            if not corrected_step:
                self.stats["rejected_actions"] += 1
                logger.error(f"Validation failed: {error}")
                return False, None, error, None, False
        
        # Step 3: Check for dangerous command patterns (additional security layer)
        if step.get("action") in ["execute_command", "run_script"]:
            command = step.get("args", {}).get("command", "")
            elevated_risk, warning = self._check_command_safety(command)
            if elevated_risk and elevated_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                # Elevate risk level if command is dangerous
                logger.warning(f"Elevated risk for command: {warning}")
                risk_level = elevated_risk
        
        # Step 4: Determine if confirmation is required
        requires_confirmation = self._requires_confirmation(corrected_step, risk_level, context)
        
        logger.info(
            f"Action validated: {corrected_step.get('module')}.{corrected_step.get('action')} "
            f"requires_confirmation={requires_confirmation}"
        )
        
        # Step 5: Request confirmation if needed
        user_confirmed = False
        if requires_confirmation:
            self.stats["confirmations_requested"] += 1
            user_confirmed = self.confirmation_callback(corrected_step, risk_level, context)
            
            if user_confirmed:
                self.stats["confirmations_approved"] += 1
                logger.info(f"User confirmed action: {corrected_step.get('module')}.{corrected_step.get('action')}")
            else:
                self.stats["confirmations_denied"] += 1
                logger.warning(f"User denied action: {corrected_step.get('module')}.{corrected_step.get('action')}")
                return False, None, "Action denied by user", risk_level, False
        else:
            # Auto-approve if no confirmation required
            user_confirmed = True
            logger.debug(f"Action auto-approved (no confirmation required)")
        
        return True, corrected_step, None, risk_level, user_confirmed
    
    def _get_risk_level(self, step: Dict[str, Any]) -> Optional[RiskLevel]:
        """
        Get the risk level for an action step from SSOT (module_action_schema.py).
        
        This is the ONLY place where risk level is determined.
        
        Args:
            step: Step dictionary with "module" and "action"
        
        Returns:
            RiskLevel or None if action not found
        """
        module_name = step.get("module")
        action_name = step.get("action")
        
        if not module_name or not action_name:
            return None
        
        module = get_module(module_name)
        if not module:
            return None
        
        action_def = module.get_action(action_name)
        if not action_def:
            return None
        
        return action_def.risk_level
    
    def _requires_confirmation(
        self,
        step: Dict[str, Any],
        risk_level: Optional[RiskLevel],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Determine if action requires user confirmation based on RiskLevel.
        
        Rules (SAFETY-001):
        - CRITICAL: ALWAYS requires confirmation
        - HIGH: ALWAYS requires confirmation
        - MEDIUM: No confirmation (unless special context)
        - LOW: No confirmation
        
        Args:
            step: Action step
            risk_level: Risk level from SSOT
            context: Optional context
        
        Returns:
            True if confirmation required
        """
        if not risk_level:
            # Unknown risk - be conservative
            logger.warning(f"Unknown risk level for {step.get('module')}.{step.get('action')}, requiring confirmation")
            return True
        
        # CRITICAL and HIGH ALWAYS require confirmation
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return True
        
        # MEDIUM and LOW do NOT require confirmation by default
        # (No arbitrary regex blocking)
        return False
    
    def _check_command_safety(self, command: str) -> Tuple[Optional[RiskLevel], Optional[str]]:
        """
        Check if a terminal command contains dangerous patterns.
        
        This is an ADDITIONAL security layer on top of schema risk levels.
        
        Args:
            command: Command string
        
        Returns:
            Tuple of (elevated_risk_level, warning_message)
        """
        command_lower = command.lower().strip()
        
        # Pattern descriptions for better error messages
        pattern_descriptions = {
            r"rm\s+-rf\s+/": "Attempting to delete root directory",
            r"rm\s+-rf\s+\*": "Attempting to delete all files",
            r":\(\)\{ :\|: & \};:": "Fork bomb detected",
            r"mkfs\.": "Filesystem format command detected",
            r"dd\s+if=.*of=/dev/": "Direct disk write operation detected",
            r"chmod\s+-R\s+777": "Dangerous permissions (777) on directory",
            r"sudo\s+rm": "Privileged delete operation",
            r"curl.*\|\s*(?:bash|sh)": "Piping remote script to shell",
            r"wget.*\|\s*(?:bash|sh)": "Piping remote script to shell",
        }
        
        # Check dangerous patterns with specific warnings
        for pattern, description in pattern_descriptions.items():
            if re.search(pattern, command_lower):
                return (RiskLevel.CRITICAL, f"CRITICAL: {description}")
        
        # Check for destructive keywords (using class-level constants)
        for pattern, keyword in self.destructive_keywords:
            if re.search(pattern, command_lower):
                return (RiskLevel.HIGH, f"Command contains destructive keyword: {keyword}")
        
        # Check for system-level operations (using class-level constants)
        for pattern, keyword in self.system_keywords:
            if re.search(pattern, command_lower):
                return (RiskLevel.CRITICAL, f"System-level operation detected: {keyword}")
        
        # Check for sudo usage
        if command_lower.startswith("sudo "):
            return (RiskLevel.HIGH, "Command uses elevated privileges (sudo)")
        
        return (None, None)
    
    def _try_correct_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Attempt to auto-correct an invalid step.
        
        Args:
            step: Invalid step
        
        Returns:
            Corrected step or None if correction not possible
        """
        corrected = step.copy()
        changed = False
        
        # Try to correct module name
        if "module" in step:
            corrected_module = auto_correct_module(step["module"])
            if corrected_module and corrected_module != step["module"]:
                corrected["module"] = corrected_module
                changed = True
                logger.debug(f"Corrected module: {step['module']} -> {corrected_module}")
        
        # Try to correct action name (normalize to canonical name even if alias)
        if "action" in step and "module" in corrected:
            original_action = step.get("action")
            corrected_action = auto_correct_action(corrected["module"], original_action)
            # Always update if we get a correction (this handles aliases too)
            if corrected_action:
                if corrected_action != original_action:
                    corrected["action"] = corrected_action
                    changed = True
                    logger.debug(f"Corrected action: {original_action} -> {corrected_action}")
        
        return corrected if changed else None
    
    def _get_fallback_step(
        self,
        original_step: Dict[str, Any],
        error: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a safe fallback action when validation fails.
        
        Args:
            original_step: The failed step
            error: Error message from validation
        
        Returns:
            Fallback step or None
        """
        # Extract what we can from the original step
        module_name = original_step.get("module")
        action_name = original_step.get("action")
        args = original_step.get("args", {})
        
        # If module is invalid, try a generic UI action
        if not is_valid_module(module_name):
            logger.warning(f"Invalid module '{module_name}', falling back to UI module")
            return {
                "module": "ui",
                "action": "unknown",
                "args": {"original_module": module_name, "original_action": action_name},
                "context": original_step.get("context", {}),
                "fallback_reason": error
            }
        
        # If action is invalid for the module, try to find a safe action
        if not is_valid_action(module_name, action_name):
            # Get first valid action for the module as fallback
            valid_actions = get_all_actions_for_module(module_name)
            if valid_actions:
                fallback_action = valid_actions[0]  # Use first action as fallback
                logger.warning(
                    f"Invalid action '{action_name}' for module '{module_name}', "
                    f"falling back to '{fallback_action}'"
                )
                return {
                    "module": module_name,
                    "action": fallback_action,
                    "args": {},  # Empty args for safety
                    "context": original_step.get("context", {}),
                    "fallback_reason": error
                }
        
        # No fallback available
        return None
    
    def _default_confirmation(
        self,
        step: Dict[str, Any],
        risk_level: RiskLevel,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Default confirmation callback (auto-deny HIGH/CRITICAL actions).
        
        Args:
            step: Action step
            risk_level: Risk level
            context: Optional context
        
        Returns:
            True if action is confirmed
        """
        # In default mode, deny CRITICAL and HIGH-risk actions
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            logger.warning(f"Action requires manual confirmation: {step.get('action')}")
            logger.warning(f"Risk level: {risk_level.value}")
            logger.info("Use interactive mode for confirmation.")
            return False
        
        # Allow MEDIUM and LOW risk
        return True
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get validation statistics report.
        
        Returns:
            Dictionary with validation stats
        """
        total = self.stats["total_validations"]
        success_rate = (
            (self.stats["valid_actions"] + self.stats["corrected_actions"]) / total * 100
            if total > 0
            else 0.0
        )
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "correction_rate": (
                self.stats["corrected_actions"] / total * 100 if total > 0 else 0.0
            ),
            "rejection_rate": (
                self.stats["rejected_actions"] / total * 100 if total > 0 else 0.0
            ),
            "confirmation_approval_rate": (
                self.stats["confirmations_approved"] / self.stats["confirmations_requested"] * 100
                if self.stats["confirmations_requested"] > 0
                else 0.0
            ),
        }
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.stats = {
            "total_validations": 0,
            "valid_actions": 0,
            "corrected_actions": 0,
            "rejected_actions": 0,
            "fallback_actions": 0,
            "confirmations_requested": 0,
            "confirmations_approved": 0,
            "confirmations_denied": 0,
        }


# Singleton instance for global use
_global_validator: Optional[UnifiedActionValidator] = None


def get_global_validator() -> UnifiedActionValidator:
    """
    Get the global unified validator instance.
    
    Returns:
        Global UnifiedActionValidator instance
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = UnifiedActionValidator(
            auto_correct=True,
            allow_fallback=True,
            strict_mode=False
        )
    return _global_validator


def validate_action(
    step: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Optional[RiskLevel], bool]:
    """
    Convenience function for validating and confirming a single action step.
    
    Args:
        step: Step dictionary
        context: Optional context
    
    Returns:
        Tuple of (is_valid, corrected_step, error_message, risk_level, user_confirmed)
    """
    validator = get_global_validator()
    return validator.validate_and_confirm(step, context)
