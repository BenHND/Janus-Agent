"""
PERF-001: Context Assembler with Observation Budget

This module implements strict budget control for context injection into LLM prompts.
It limits memory, SOM (Set-of-Marks), and tools to prevent excessive token usage
and improve LLM performance and response quality.

Features:
- Token counting for all context components
- Budget limits for memory, SOM, and tools
- Smart shrinking policy when budget is exceeded
- Size metrics tracking
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Simple estimation: ~4 characters per token for English text.
    This is a rough approximation that works well enough for budgeting.
    
    Args:
        text: Text to estimate tokens for
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Average ~4 chars per token, plus word boundaries
    return len(text) // 4 + text.count(' ') // 2


@dataclass
class BudgetConfig:
    """Configuration for context budget limits."""
    
    # PERF-M4-001: Reduced budgets for M4 performance optimization
    # Maximum tokens for each component (optimized for M4 prefill speed)
    max_som_tokens: int = 600  # Set-of-Marks elements (reduced from 1500 for M4)
    max_memory_tokens: int = 200  # Action history (reduced from 400, keep only 3 most recent)
    max_tools_tokens: int = 300  # Tool/action schema (compact version)
    max_system_state_tokens: int = 200  # System state (app, URL, etc.)
    max_skill_hint_tokens: int = 200  # Skill hints (reduced from 300)
    
    # Maximum number of elements (reduced for M4 performance)
    max_som_elements: int = 10  # Maximum SOM elements (reduced from 30, top 10 most relevant only)
    max_memory_items: int = 3  # Maximum memory items (only 3 most recent actions)
    
    # PERF-M4-001: Total budget set to 1500 tokens for optimal M4 performance
    # On M4, prefill time explodes when prompt > 2000 tokens
    # Component sum: 600 + 200 + 300 + 200 + 200 = 1500 tokens
    max_total_tokens: int = 1500  # Total context budget (optimized for M4)
    
    def __post_init__(self):
        """Validate budget configuration."""
        component_sum = (
            self.max_som_tokens + 
            self.max_memory_tokens + 
            self.max_tools_tokens + 
            self.max_system_state_tokens +
            self.max_skill_hint_tokens  # LEARNING-001
        )
        if component_sum > self.max_total_tokens:
            logger.warning(
                f"Component budgets sum ({component_sum}) exceeds total budget ({self.max_total_tokens}). "
                "Adjusting total budget to accommodate."
            )
            self.max_total_tokens = component_sum


@dataclass
class ContextMetrics:
    """Metrics for context assembly."""
    
    # Token counts by component
    som_tokens: int = 0
    memory_tokens: int = 0
    tools_tokens: int = 0
    system_state_tokens: int = 0
    skill_hint_tokens: int = 0  # LEARNING-001
    total_tokens: int = 0
    
    # Element counts
    som_elements: int = 0
    memory_items: int = 0
    
    # Shrinking applied
    som_shrunk: bool = False
    memory_shrunk: bool = False
    tools_shrunk: bool = False
    skill_hint_shrunk: bool = False  # LEARNING-001
    
    # Over budget flag
    over_budget: bool = False
    budget_exceeded_by: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "tokens": {
                "som": self.som_tokens,
                "memory": self.memory_tokens,
                "tools": self.tools_tokens,
                "system_state": self.system_state_tokens,
                "skill_hint": self.skill_hint_tokens,  # LEARNING-001
                "total": self.total_tokens
            },
            "elements": {
                "som_elements": self.som_elements,
                "memory_items": self.memory_items
            },
            "shrinking": {
                "som_shrunk": self.som_shrunk,
                "memory_shrunk": self.memory_shrunk,
                "tools_shrunk": self.tools_shrunk,
                "skill_hint_shrunk": self.skill_hint_shrunk  # LEARNING-001
            },
            "budget": {
                "over_budget": self.over_budget,
                "exceeded_by": self.budget_exceeded_by
            }
        }


class ContextAssembler:
    """
    Assembles context for LLM prompts with strict budget control.
    
    PERF-001: Prevents excessive context injection that degrades performance.
    
    Features:
    - Token-based budgeting for all context components
    - Automatic shrinking when budget exceeded
    - Prioritization of most relevant context
    - Metrics tracking for monitoring
    """
    
    def __init__(self, config: Optional[BudgetConfig] = None):
        """
        Initialize ContextAssembler with budget configuration.
        
        Args:
            config: Budget configuration (uses defaults if None)
        """
        self.config = config or BudgetConfig()
        self.metrics = ContextMetrics()
        logger.info(
            f"ContextAssembler initialized with budget: "
            f"SOM={self.config.max_som_tokens}t/{self.config.max_som_elements}e, "
            f"Memory={self.config.max_memory_tokens}t/{self.config.max_memory_items}i, "
            f"Tools={self.config.max_tools_tokens}t, "
            f"Total={self.config.max_total_tokens}t"
        )
    
    def assemble_context(
        self,
        visual_context: str,
        action_history: List[Any],
        schema_section: str,
        system_state: Dict[str, Any],
        skill_hint: Optional[str] = None  # LEARNING-001: Skill hint from cache
    ) -> Dict[str, Any]:
        """
        Assemble context components with budget enforcement.
        
        LEARNING-001: Added skill_hint parameter for learned sequences.
        
        Args:
            visual_context: Set-of-Marks visual elements as string
            action_history: List of previous action results
            schema_section: Tool/action schema documentation
            system_state: Current system state (app, URL, etc.)
            skill_hint: Optional skill hint from learned sequences
        
        Returns:
            Dictionary with:
            - visual_context: Budgeted visual context
            - action_history: Budgeted action history
            - schema_section: Budgeted schema
            - system_state: Budgeted system state
            - skill_hint: Budgeted skill hint (if provided)
            - metrics: Context assembly metrics
        """
        # Reset metrics
        self.metrics = ContextMetrics()
        
        # Process each component with budget
        budgeted_visual = self._budget_visual_context(visual_context)
        budgeted_history = self._budget_action_history(action_history)
        budgeted_schema = self._budget_schema(schema_section)
        budgeted_state = self._budget_system_state(system_state)
        budgeted_hint = self._budget_skill_hint(skill_hint)  # LEARNING-001
        
        # Calculate total tokens
        self.metrics.total_tokens = (
            self.metrics.som_tokens +
            self.metrics.memory_tokens +
            self.metrics.tools_tokens +
            self.metrics.system_state_tokens +
            self.metrics.skill_hint_tokens  # LEARNING-001
        )
        
        # TICKET 3 (P0): Structured logging of token budget by section
        logger.info(
            f"📊 Context budget breakdown: "
            f"TOTAL={self.metrics.total_tokens}/{self.config.max_total_tokens} | "
            f"SOM={self.metrics.som_tokens}/{self.config.max_som_tokens} | "
            f"Memory={self.metrics.memory_tokens}/{self.config.max_memory_tokens} | "
            f"Tools={self.metrics.tools_tokens}/{self.config.max_tools_tokens} | "
            f"State={self.metrics.system_state_tokens}/{self.config.max_system_state_tokens} | "
            f"Hint={self.metrics.skill_hint_tokens}/{self.config.max_skill_hint_tokens}"
        )
        
        # Check if over total budget
        if self.metrics.total_tokens > self.config.max_total_tokens:
            self.metrics.over_budget = True
            self.metrics.budget_exceeded_by = self.metrics.total_tokens - self.config.max_total_tokens
            logger.warning(
                f"⚠️ Context over budget: {self.metrics.total_tokens}/{self.config.max_total_tokens} tokens "
                f"(exceeded by {self.metrics.budget_exceeded_by})"
            )
            
            # Apply emergency shrinking if significantly over budget
            if self.metrics.budget_exceeded_by > 500:
                logger.warning("Applying emergency shrinking to bring context under budget")
                budgeted_visual = self._emergency_shrink_visual(budgeted_visual)
                budgeted_history = self._emergency_shrink_history(budgeted_history)
                
                # Recalculate metrics after emergency shrinking
                self.metrics.som_tokens = estimate_tokens(budgeted_visual)
                self.metrics.memory_tokens = estimate_tokens(self._format_history(budgeted_history))
                self.metrics.total_tokens = (
                    self.metrics.som_tokens +
                    self.metrics.memory_tokens +
                    self.metrics.tools_tokens +
                    self.metrics.system_state_tokens +
                    self.metrics.skill_hint_tokens
                )
        
        logger.debug(f"Context assembled: {self.metrics.total_tokens} tokens total")
        
        return {
            "visual_context": budgeted_visual,
            "action_history": budgeted_history,
            "schema_section": budgeted_schema,
            "system_state": budgeted_state,
            "skill_hint": budgeted_hint,  # LEARNING-001
            "metrics": self.metrics
        }
    
    def _budget_visual_context(self, visual_context: str) -> str:
        """
        Budget Set-of-Marks visual context.
        
        Args:
            visual_context: Raw visual context string
        
        Returns:
            Budgeted visual context
        """
        if not visual_context or visual_context.strip() == "":
            self.metrics.som_tokens = 0
            self.metrics.som_elements = 0
            return ""
        
        # Estimate tokens in original context
        original_tokens = estimate_tokens(visual_context)
        self.metrics.som_tokens = original_tokens
        
        # If under budget, return as-is
        if original_tokens <= self.config.max_som_tokens:
            # Count elements (lines that look like SOM elements)
            self.metrics.som_elements = len([
                line for line in visual_context.split('\n') 
                if line.strip() and ('id:' in line.lower() or 'type:' in line.lower())
            ])
            return visual_context
        
        # Over budget - shrink by limiting elements
        logger.debug(
            f"Visual context over budget: {original_tokens}/{self.config.max_som_tokens} tokens. Shrinking..."
        )
        self.metrics.som_shrunk = True
        
        # Split into lines and keep most important ones
        lines = visual_context.split('\n')
        elements = [line for line in lines if line.strip()]
        
        # Keep header lines (non-element lines)
        header = [line for line in lines if line.strip() and not any(
            marker in line.lower() for marker in ['id:', 'type:', 'text:', 'button', 'link', 'input']
        )]
        
        # Keep element lines up to max
        element_lines = [line for line in lines if line.strip() and any(
            marker in line.lower() for marker in ['id:', 'type:', 'text:', 'button', 'link', 'input']
        )]
        
        # Limit to max elements
        if len(element_lines) > self.config.max_som_elements:
            element_lines = element_lines[:self.config.max_som_elements]
            logger.debug(f"Limited SOM elements to {self.config.max_som_elements}")
        
        # Reconstruct context
        shrunk_context = '\n'.join(header + element_lines)
        self.metrics.som_tokens = estimate_tokens(shrunk_context)
        self.metrics.som_elements = len(element_lines)
        
        logger.debug(f"Visual context shrunk to {self.metrics.som_tokens} tokens, {self.metrics.som_elements} elements")
        return shrunk_context
    
    def _budget_action_history(self, action_history: List[Any]) -> List[Any]:
        """
        Budget action history.
        
        Args:
            action_history: List of action results
        
        Returns:
            Budgeted action history
        """
        if not action_history:
            self.metrics.memory_tokens = 0
            self.metrics.memory_items = 0
            return []
        
        # Limit to max items (keep most recent)
        limited_history = action_history[-self.config.max_memory_items:]
        
        # Estimate tokens
        history_text = self._format_history(limited_history)
        history_tokens = estimate_tokens(history_text)
        
        self.metrics.memory_tokens = history_tokens
        self.metrics.memory_items = len(limited_history)
        
        # If over budget, reduce further
        if history_tokens > self.config.max_memory_tokens:
            logger.debug(
                f"History over budget: {history_tokens}/{self.config.max_memory_tokens} tokens. Reducing..."
            )
            self.metrics.memory_shrunk = True
            
            # Keep fewer items
            target_items = max(3, self.config.max_memory_items // 2)
            limited_history = action_history[-target_items:]
            
            history_text = self._format_history(limited_history)
            self.metrics.memory_tokens = estimate_tokens(history_text)
            self.metrics.memory_items = len(limited_history)
            
            logger.debug(f"History reduced to {self.metrics.memory_items} items, {self.metrics.memory_tokens} tokens")
        
        return limited_history
    
    def _budget_schema(self, schema_section: str) -> str:
        """
        Budget tools/action schema.
        
        Args:
            schema_section: Raw schema documentation
        
        Returns:
            Budgeted schema
        """
        if not schema_section:
            self.metrics.tools_tokens = 0
            return ""
        
        schema_tokens = estimate_tokens(schema_section)
        self.metrics.tools_tokens = schema_tokens
        
        # If over budget, truncate (keep beginning which has most important info)
        if schema_tokens > self.config.max_tools_tokens:
            logger.debug(
                f"Schema over budget: {schema_tokens}/{self.config.max_tools_tokens} tokens. Truncating..."
            )
            self.metrics.tools_shrunk = True
            
            # Estimate target length based on token ratio
            ratio = self.config.max_tools_tokens / schema_tokens
            target_chars = int(len(schema_section) * ratio * 0.9)  # 90% to be safe
            
            truncated_schema = schema_section[:target_chars] + "\n... (schema truncated for budget)"
            self.metrics.tools_tokens = estimate_tokens(truncated_schema)
            
            logger.debug(f"Schema truncated to {self.metrics.tools_tokens} tokens")
            return truncated_schema
        
        return schema_section
    
    def _budget_system_state(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Budget system state.
        
        Args:
            system_state: Raw system state dict
        
        Returns:
            Budgeted system state
        """
        if not system_state:
            self.metrics.system_state_tokens = 0
            return {}
        
        # System state should be minimal - just keep essential fields
        essential_fields = ['active_app', 'url', 'window_title', 'domain']
        budgeted_state = {
            k: v for k, v in system_state.items() 
            if k in essential_fields
        }
        
        # Truncate long values
        for key in budgeted_state:
            if isinstance(budgeted_state[key], str) and len(budgeted_state[key]) > 200:
                budgeted_state[key] = budgeted_state[key][:200] + "..."
        
        # Estimate tokens
        state_text = self._format_system_state(budgeted_state)
        self.metrics.system_state_tokens = estimate_tokens(state_text)
        
        return budgeted_state
    
    def _budget_skill_hint(self, skill_hint: Optional[str]) -> str:
        """
        Budget skill hint context.
        
        LEARNING-001: Skill hints are suggestions for the LLM, not automatic execution.
        
        Args:
            skill_hint: Skill hint string (from SkillHint.to_context_string())
        
        Returns:
            Budgeted skill hint string
        """
        if not skill_hint or skill_hint.strip() == "":
            self.metrics.skill_hint_tokens = 0
            return ""
        
        # Estimate tokens in original hint
        original_tokens = estimate_tokens(skill_hint)
        self.metrics.skill_hint_tokens = original_tokens
        
        # If under budget, return as-is
        if original_tokens <= self.config.max_skill_hint_tokens:
            return skill_hint
        
        # If over budget, truncate to fit
        # Keep the header and first few actions
        lines = skill_hint.split('\n')
        
        # Always keep header lines (Intent, Success rate)
        header_lines = []
        action_lines = []
        warning_lines = []
        
        in_actions = False
        in_warning = False
        
        for line in lines:
            if "Intent:" in line or "Success rate:" in line:
                header_lines.append(line)
            elif "Suggested actions:" in line:
                action_lines.append(line)
                in_actions = True
            elif "⚠️ IMPORTANT:" in line or in_warning:
                warning_lines.append(line)
                in_warning = True
            elif in_actions and not in_warning:
                action_lines.append(line)
        
        # Try to fit as many action lines as possible
        truncated = header_lines + action_lines[:5] + ["  ... (more actions omitted)"] + warning_lines
        truncated_str = '\n'.join(truncated)
        truncated_tokens = estimate_tokens(truncated_str)
        
        if truncated_tokens <= self.config.max_skill_hint_tokens:
            self.metrics.skill_hint_shrunk = True
            self.metrics.skill_hint_tokens = truncated_tokens
            logger.debug(f"Skill hint truncated: {original_tokens} -> {truncated_tokens} tokens")
            return truncated_str
        
        # If still over, keep just header and warning
        minimal = header_lines + ["  (actions omitted due to budget)"] + warning_lines
        minimal_str = '\n'.join(minimal)
        minimal_tokens = estimate_tokens(minimal_str)
        
        self.metrics.skill_hint_shrunk = True
        self.metrics.skill_hint_tokens = minimal_tokens
        logger.warning(f"Skill hint heavily truncated: {original_tokens} -> {minimal_tokens} tokens")
        return minimal_str
    
    def _emergency_shrink_visual(self, visual_context: str) -> str:
        """Emergency shrinking of visual context when significantly over budget."""
        if not visual_context:
            return ""
        
        # Reduce to half the max elements
        target_elements = max(10, self.config.max_som_elements // 2)
        
        lines = visual_context.split('\n')
        header = [line for line in lines if line.strip() and not any(
            marker in line.lower() for marker in ['id:', 'type:', 'text:', 'button', 'link', 'input']
        )]
        element_lines = [line for line in lines if line.strip() and any(
            marker in line.lower() for marker in ['id:', 'type:', 'text:', 'button', 'link', 'input']
        )]
        
        element_lines = element_lines[:target_elements]
        shrunk = '\n'.join(header + element_lines)
        
        logger.warning(f"Emergency shrink applied to visual context: {target_elements} elements")
        return shrunk
    
    def _emergency_shrink_history(self, action_history: List[Any]) -> List[Any]:
        """Emergency shrinking of action history when significantly over budget."""
        if not action_history:
            return []
        
        # Keep only last 3 items
        target_items = min(3, len(action_history))
        shrunk = action_history[-target_items:]
        
        logger.warning(f"Emergency shrink applied to action history: {target_items} items")
        return shrunk
    
    def _format_history(self, action_history: List[Any]) -> str:
        """Format action history as text for token estimation."""
        if not action_history:
            return ""
        
        formatted_lines = []
        for res in action_history:
            # Handle both ActionResult objects and dicts
            if hasattr(res, 'action_type'):
                action = res.action_type
                status = 'SUCCÈS' if res.success else 'ÉCHEC'
                message = res.message
            else:
                action = res.get('action_type', 'unknown')
                status = 'SUCCÈS' if res.get('success', False) else 'ÉCHEC'
                message = res.get('message', '')
            
            formatted_lines.append(f"- {action}: {status} ({message})")
        
        return '\n'.join(formatted_lines)
    
    def _format_system_state(self, system_state: Dict[str, Any]) -> str:
        """Format system state as text for token estimation."""
        lines = []
        for key, value in system_state.items():
            if value:
                lines.append(f"{key}: {value}")
        return '\n'.join(lines)
    
    def get_metrics(self) -> ContextMetrics:
        """Get current context metrics."""
        return self.metrics
    
    def reset_metrics(self):
        """Reset metrics."""
        self.metrics = ContextMetrics()
