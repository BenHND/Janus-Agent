"""
Strict Action Validator - TICKET 003

This validator enforces the module action schema strictly.
It sits between the Reasoner (LLM) and the Executor to ensure:
1. Only valid modules are used
2. Only valid actions for each module are executed
3. Required parameters are present
4. Parameter types are correct

If validation fails, it can:
- Auto-correct common mistakes (aliases, case issues)
- Fallback to a safe default action
- Reject the action with a clear error message
"""

from typing import Any, Dict, List, Optional, Tuple

from janus.runtime.core.module_action_schema import (
    RiskLevel,
    auto_correct_action,
    auto_correct_module,
    get_all_actions_for_module,
    get_all_module_names,
    get_module,
    is_valid_action,
    is_valid_module,
    validate_action_plan,
    validate_action_step,
)
from janus.logging import get_logger

logger = get_logger("strict_action_validator")


class StrictActionValidator:
    """
    Strict validator for module actions based on the schema.
    
    This is the GATEKEEPER between Reasoner and Executor.
    No action passes without validation.
    """
    
    def __init__(
        self,
        auto_correct: bool = True,
        allow_fallback: bool = True,
        strict_mode: bool = False
    ):
        """
        Initialize strict validator.
        
        Args:
            auto_correct: Attempt to auto-correct invalid actions using aliases
            allow_fallback: Allow fallback to default safe actions
            strict_mode: Reject everything that's not perfectly valid (no corrections)
        """
        self.auto_correct = auto_correct
        self.allow_fallback = allow_fallback
        self.strict_mode = strict_mode
        
        # Statistics
        self.stats = {
            "total_validations": 0,
            "valid_actions": 0,
            "corrected_actions": 0,
            "rejected_actions": 0,
            "fallback_actions": 0
        }
    
    def validate_step(
        self,
        step: Dict[str, Any],
        auto_correct: Optional[bool] = None,
        normalize: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Optional[RiskLevel]]:
        """
        Validate and optionally correct a single action step.
        
        Args:
            step: Step dictionary with "module", "action", "args"
            auto_correct: Override instance auto_correct setting
            normalize: Normalize action names to canonical form (aliases -> canonical)
        
        Returns:
            Tuple of (is_valid, corrected_step_or_none, error_message_or_none, risk_level)
        """
        self.stats["total_validations"] += 1
        
        # Use instance setting if not overridden
        if auto_correct is None:
            auto_correct = self.auto_correct and not self.strict_mode
        
        # Quick validation first
        is_valid, error = validate_action_step(step)
        
        # Get risk level for the action (TICKET-SEC-001)
        risk_level = self._get_risk_level(step)
        
        if is_valid:
            self.stats["valid_actions"] += 1
            
            # Normalize action names even if already valid (aliases -> canonical)
            if normalize and "module" in step and "action" in step:
                canonical_action = auto_correct_action(step["module"], step["action"])
                if canonical_action and canonical_action != step["action"]:
                    normalized_step = step.copy()
                    normalized_step["action"] = canonical_action
                    logger.debug(f"Normalized action: {step['action']} -> {canonical_action}")
                    return True, normalized_step, None, risk_level
            
            return True, step, None, risk_level
        
        # If strict mode, reject immediately
        if self.strict_mode:
            self.stats["rejected_actions"] += 1
            logger.warning(f"Strict validation failed: {error}")
            return False, None, error, None
        
        # Try auto-correction
        if auto_correct:
            corrected_step = self._try_correct_step(step)
            if corrected_step:
                # Validate corrected step
                is_valid, error = validate_action_step(corrected_step)
                if is_valid:
                    self.stats["corrected_actions"] += 1
                    logger.info(f"Auto-corrected step: {step['module']}.{step.get('action')} -> {corrected_step['module']}.{corrected_step['action']}")
                    corrected_risk_level = self._get_risk_level(corrected_step)
                    return True, corrected_step, None, corrected_risk_level
        
        # Try fallback if allowed
        if self.allow_fallback:
            fallback_step = self._get_fallback_step(step, error)
            if fallback_step:
                self.stats["fallback_actions"] += 1
                logger.warning(f"Using fallback action: {fallback_step}")
                fallback_risk_level = self._get_risk_level(fallback_step)
                return True, fallback_step, None, fallback_risk_level
        
        # All attempts failed
        self.stats["rejected_actions"] += 1
        logger.error(f"Validation failed: {error}")
        return False, None, error, None
    
    def validate_plan(
        self,
        plan: Dict[str, Any],
        auto_correct: Optional[bool] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """
        Validate and optionally correct an entire action plan.
        
        Args:
            plan: Plan dictionary with "steps" array
            auto_correct: Override instance auto_correct setting
        
        Returns:
            Tuple of (is_valid, corrected_plan_or_none, list_of_errors)
        """
        if "steps" not in plan or not isinstance(plan["steps"], list):
            return False, None, ["Invalid plan: missing or invalid 'steps' field"]
        
        corrected_steps = []
        errors = []
        
        for i, step in enumerate(plan["steps"]):
            is_valid, corrected_step, error = self.validate_step(step, auto_correct)
            
            if is_valid:
                # Use corrected step if available, otherwise original
                corrected_steps.append(corrected_step if corrected_step else step)
            else:
                errors.append(f"Step {i}: {error}")
                # In strict mode, stop at first error
                if self.strict_mode:
                    break
        
        # If no errors, return corrected plan
        if not errors:
            corrected_plan = plan.copy()
            corrected_plan["steps"] = corrected_steps
            return True, corrected_plan, []
        
        # Partial success if we have some valid steps
        if corrected_steps and not self.strict_mode:
            logger.warning(f"Plan partially valid: {len(corrected_steps)}/{len(plan['steps'])} steps valid")
            corrected_plan = plan.copy()
            corrected_plan["steps"] = corrected_steps
            return True, corrected_plan, errors
        
        return False, None, errors
    
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
            )
        }
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.stats = {
            "total_validations": 0,
            "valid_actions": 0,
            "corrected_actions": 0,
            "rejected_actions": 0,
            "fallback_actions": 0
        }
    
    def get_schema_summary(self) -> str:
        """
        Get a summary of the available modules and actions.
        
        Useful for debugging and displaying to users.
        """
        from janus.runtime.core.module_action_schema import get_schema_summary
        return get_schema_summary()
    
    def suggest_correction(self, module_name: str, action_name: str) -> Optional[str]:
        """
        Suggest a correction for an invalid action.
        
        Args:
            module_name: Module name
            action_name: Action name (possibly invalid)
        
        Returns:
            Suggested correction or None
        """
        # First check if module is valid
        if not is_valid_module(module_name):
            corrected_module = auto_correct_module(module_name)
            if corrected_module:
                return f"Did you mean module '{corrected_module}'?"
            return f"Invalid module. Valid modules: {', '.join(get_all_module_names())}"
        
        # Check if action exists
        if is_valid_action(module_name, action_name):
            return None  # No correction needed
        
        # Try to find correction
        corrected_action = auto_correct_action(module_name, action_name)
        if corrected_action:
            return f"Did you mean action '{corrected_action}'?"
        
        # Suggest valid actions
        valid_actions = get_all_actions_for_module(module_name)
        return f"Invalid action. Valid actions for {module_name}: {', '.join(valid_actions)}"
    
    def _get_risk_level(self, step: Dict[str, Any]) -> Optional[RiskLevel]:
        """
        Get the risk level for an action step (TICKET-SEC-001).
        
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


# Singleton instance for global use
_global_validator: Optional[StrictActionValidator] = None


def get_global_validator() -> StrictActionValidator:
    """
    Get the global validator instance.
    
    Returns:
        Global StrictActionValidator instance
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = StrictActionValidator(
            auto_correct=True,
            allow_fallback=True,
            strict_mode=False
        )
    return _global_validator


def validate_action(step: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Optional[RiskLevel]]:
    """
    Convenience function for validating a single action step.
    
    Args:
        step: Step dictionary
    
    Returns:
        Tuple of (is_valid, corrected_step, error_message, risk_level)
    """
    validator = get_global_validator()
    return validator.validate_step(step)


def validate_plan(plan: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """
    Convenience function for validating an action plan.
    
    Args:
        plan: Plan dictionary with steps
    
    Returns:
        Tuple of (is_valid, corrected_plan, list_of_errors)
    """
    validator = get_global_validator()
    return validator.validate_plan(plan)
