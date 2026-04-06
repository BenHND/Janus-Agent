"""
Validator Agent - TICKET 103 (Updated for ONE-TICKET-VERIFICATION-007)

Independent agent that STRICTLY VALIDATES action plans before execution.

ONE-TICKET-VERIFICATION-007: Legacy JSONPlanValidator completely removed.
- Uses UnifiedActionValidator for strict schema validation
- Invalid JSON triggers re-ask to LLM
- No regex repair, no silent corrections
- The Reasoner is responsible for generating valid JSON and self-correcting

This agent acts as a gatekeeper between the Reasoner and the Executor,
ensuring all plans are structurally valid, have correct module/action pairs,
and have complete context information.

Features:
- Structural validation (steps array, required fields)
- Module/action validation against schema (via UnifiedActionValidator)
- Context structure validation
- Clear error reporting for Reasoner to use for self-correction

Does NOT:
- Auto-correct JSON errors (Reasoner must fix)
- Reconstruct plans (Reasoner must replan)
- Apply regex-based repairs
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, NamedTuple

from janus.safety.validation.unified_action_validator import UnifiedActionValidator
from janus.runtime.core.module_action_schema import validate_action_step

logger = logging.getLogger(__name__)


class ValidationIssue(NamedTuple):
    """Validation issue (error or warning)"""
    message: str
    severity: str  # "error" or "warning"


class ValidationResult(NamedTuple):
    """Result of validation"""
    is_valid: bool
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]


class ValidatorAgent:
    """
    JSON V3 Validator Agent - STRICT VALIDATION ONLY (ONE-TICKET-VERIFICATION-007)
    
    ONE-TICKET-VERIFICATION-007: Uses UnifiedActionValidator instead of legacy JSONPlanValidator.
    
    The Reasoner is responsible for:
    - Generating valid JSON
    - Self-correcting when validation fails
    - Providing complete context
    
    Responsibilities:
    1. Verify structural integrity (steps array exists, proper types)
    2. Validate module names against valid modules
    3. Validate action names against module actions
    4. Verify all required fields present (args, context)
    5. Return standardized validation result with clear errors
    
    Does NOT:
    - Auto-correct JSON errors
    - Reconstruct plans
    - Apply regex-based repairs
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        allow_missing_context: bool = False
    ):
        """
        Initialize Validator Agent.
        
        ONE-TICKET-VERIFICATION-007: Uses UnifiedActionValidator.
        
        Args:
            strict_mode: If True, reject plans with any warnings (default: True)
            allow_missing_context: If True, allow missing context fields (default: False)
        """
        self.strict_mode = strict_mode
        self.allow_missing_context = allow_missing_context
        
        # Initialize validator with UnifiedActionValidator
        self.validator = UnifiedActionValidator(
            auto_correct=not strict_mode,
            allow_fallback=False,
            strict_mode=strict_mode
        )
        
        # Stats
        self.stats = {
            "total_validations": 0,
            "valid_plans": 0,
            "rejected_plans": 0,
        }
        
        logger.info(
            f"✓ ValidatorAgent initialized (strict={strict_mode}, "
            f"allow_missing_context={allow_missing_context})"
        )
    
    def validate(
        self,
        plan_or_json: Any,
        previous_steps: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Validate a plan (ONE-TICKET-VERIFICATION-007: strict validation using UnifiedActionValidator).
        
        This is the main entry point for validation.
        
        Args:
            plan_or_json: Either a JSON string or a parsed plan dict
            previous_steps: Optional list of previously executed steps for context inference
        
        Returns:
            Dictionary with structure:
            {
                "valid": bool,          # Whether plan is valid
                "steps": [...],         # Validated steps (if valid)
                "errors": [...],        # List of error messages
                "warnings": [...]       # List of warning messages
            }
        """
        self.stats["total_validations"] += 1
        
        # Step 1: Parse JSON if needed
        if isinstance(plan_or_json, str):
            plan, parse_errors = self._parse_json(plan_or_json)
            if parse_errors:
                self.stats["rejected_plans"] += 1
                return {
                    "valid": False,
                    "steps": [],
                    "errors": parse_errors,
                    "warnings": []
                }
        else:
            plan = plan_or_json
        
        # Step 2: Infer context from previous steps if provided
        if previous_steps:
            plan = self._infer_context_from_previous(plan, previous_steps)
        
        # Step 3: Validate the plan structure
        validation_result = self._validate_plan_structure(plan)
        
        # Step 4: Build response
        if validation_result.is_valid:
            self.stats["valid_plans"] += 1
            
            return {
                "valid": True,
                "steps": plan.get("steps", []),
                "errors": [],
                "warnings": [w.message for w in validation_result.warnings]
            }
        else:
            self.stats["rejected_plans"] += 1
            return {
                "valid": False,
                "steps": plan.get("steps", []),
                "errors": [e.message for e in validation_result.errors],
                "warnings": [w.message for w in validation_result.warnings]
            }
    
    def _validate_plan_structure(self, plan: Dict[str, Any]) -> ValidationResult:
        """
        Validate plan structure using UnifiedActionValidator.
        
        Args:
            plan: Plan dictionary to validate
        
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Check for steps array
        if not isinstance(plan, dict):
            errors.append(ValidationIssue("Plan must be a dictionary", "error"))
            return ValidationResult(False, errors, warnings)
        
        if "steps" not in plan:
            errors.append(ValidationIssue("Plan must have 'steps' array", "error"))
            return ValidationResult(False, errors, warnings)
        
        if not isinstance(plan["steps"], list):
            errors.append(ValidationIssue("Plan 'steps' must be a list", "error"))
            return ValidationResult(False, errors, warnings)
        
        if len(plan["steps"]) == 0:
            errors.append(ValidationIssue("Plan must have at least one step", "error"))
            return ValidationResult(False, errors, warnings)
        
        # Validate each step using UnifiedActionValidator
        for i, step in enumerate(plan["steps"]):
            # Check basic structure
            if not isinstance(step, dict):
                errors.append(ValidationIssue(f"Step {i} must be a dictionary", "error"))
                continue
            
            # Validate using UnifiedActionValidator
            is_valid, error = validate_action_step(step)
            if not is_valid:
                errors.append(ValidationIssue(f"Step {i}: {error}", "error"))
                continue
            
            # Check for required fields
            if "module" not in step:
                errors.append(ValidationIssue(f"Step {i} missing 'module' field", "error"))
            if "action" not in step:
                errors.append(ValidationIssue(f"Step {i} missing 'action' field", "error"))
            if "args" not in step:
                errors.append(ValidationIssue(f"Step {i} missing 'args' field", "error"))
            
            # Optionally check context
            if not self.allow_missing_context and "context" not in step:
                if self.strict_mode:
                    errors.append(ValidationIssue(f"Step {i} missing 'context' field", "error"))
                else:
                    warnings.append(ValidationIssue(f"Step {i} missing 'context' field", "warning"))
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings)
    
    def validate_step(
        self,
        step: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate a single step.
        
        Args:
            step: Step dictionary
            context: Optional context for validation
        
        Returns:
            Validation result dict
        """
        # Validate using module_action_schema
        is_valid, error = validate_action_step(step)
        
        errors = []
        warnings = []
        
        if not is_valid:
            errors.append(error)
        
        # Check for required fields
        if "module" not in step:
            errors.append("Step missing 'module' field")
        if "action" not in step:
            errors.append("Step missing 'action' field")
        if "args" not in step:
            errors.append("Step missing 'args' field")
        
        return {
            "valid": len(errors) == 0,
            "step": step,
            "errors": errors,
            "warnings": warnings
        }
    
    def _parse_json(self, json_str: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Parse JSON string (ARCH-003: strict parsing only, no corrections).
        
        Args:
            json_str: JSON string to parse
        
        Returns:
            Tuple of (parsed_plan, list_of_errors)
        """
        errors = []
        
        # Try direct parsing
        try:
            plan = json.loads(json_str)
            return plan, []
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {str(e)}")
        
        # Could not parse - return empty dict and errors
        return {}, errors
    
    def _infer_context_from_previous(
        self,
        plan: Dict[str, Any],
        previous_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Infer context for steps based on previous steps.
        
        This implements smart context propagation:
        - If previous step opened an app, next step should have that app in context
        - If previous step opened a URL, next step should have that domain
        - If previous step opened a record, next step should have that record ID
        
        Args:
            plan: Plan to update
            previous_steps: List of previously executed steps
        
        Returns:
            Updated plan with inferred context
        """
        if not previous_steps or "steps" not in plan:
            return plan
        
        # Get the last step's result to infer context
        last_step = previous_steps[-1] if previous_steps else None
        
        if not last_step:
            return plan
        
        # Extract context from last step
        last_context = last_step.get("context", {}) or {}  # Handle None context
        last_module = last_step.get("module", "")
        last_action = last_step.get("action", "")
        last_args = last_step.get("args", {})
        
        # Infer app name
        inferred_app = last_context.get("app") if isinstance(last_context, dict) else None
        if last_module == "system" and last_action in ["open_app", "open_application"]:
            inferred_app = last_args.get("app_name")
        
        # Infer domain
        inferred_domain = last_context.get("domain") if isinstance(last_context, dict) else None
        if last_module == "browser" and last_action == "open_url":
            url = last_args.get("url", "")
            if url:
                # Extract domain from URL
                import re
                match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if match:
                    inferred_domain = match.group(1)
        
        # Infer thread
        inferred_thread = last_context.get("thread") if isinstance(last_context, dict) else None
        if last_module == "messaging" and last_action == "open_thread":
            inferred_thread = last_args.get("name") or last_args.get("thread_id")
        
        # Infer record
        inferred_record = last_context.get("record") if isinstance(last_context, dict) else None
        if last_module == "crm" and last_action == "open_record":
            inferred_record = last_args.get("record_id")
        
        # Apply inferred context to steps that don't have it
        for step in plan.get("steps", []):
            if "context" not in step or step["context"] is None:
                step["context"] = {}
            
            context = step["context"]
            
            # Add inferred values if missing
            if "app" not in context or context.get("app") is None:
                context["app"] = inferred_app
            
            if "domain" not in context or context.get("domain") is None:
                context["domain"] = inferred_domain
            
            if "thread" not in context or context.get("thread") is None:
                context["thread"] = inferred_thread
            
            if "record" not in context or context.get("record") is None:
                context["record"] = inferred_record
            
            # Ensure all required V3 context fields exist (excluding already-set fields)
            for field in ["surface", "url"]:
                if field not in context:
                    context[field] = None
        
        return plan
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["valid_plans"] / self.stats["total_validations"] * 100
                if self.stats["total_validations"] > 0
                else 0.0
            )
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_validations": 0,
            "valid_plans": 0,
            "rejected_plans": 0,
        }


# Singleton instance for global use
_global_validator: Optional[ValidatorAgent] = None


def get_global_validator() -> ValidatorAgent:
    """
    Get the global validator agent instance (ARCH-003: strict validation only).
    
    Returns:
        ValidatorAgent instance with strict validation
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = ValidatorAgent(
            strict_mode=False,  # Keep False to allow warnings
            allow_missing_context=True
        )
    return _global_validator


def validate_plan(
    plan_or_json: Any,
    previous_steps: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Convenience function for validating a plan.
    
    Args:
        plan_or_json: JSON string or parsed plan dict
        previous_steps: Optional previous steps for context inference
    
    Returns:
        Validation result dict
    """
    validator = get_global_validator()
    return validator.validate(plan_or_json, previous_steps)
