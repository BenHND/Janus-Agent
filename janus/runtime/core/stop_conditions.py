"""
StopConditionEvaluator - Stop Condition Evaluation

Extracted from ActionCoordinator to separate stop condition concerns.
CORE-FOUNDATION-002: Stop condition evaluation logic.
ARCH-004: Uses canonical SystemState for consistent key access.
"""

import logging
from typing import List, Optional

from janus.runtime.core.contracts import (
    StopCondition,
    StopConditionType,
    SystemState,
)

logger = logging.getLogger(__name__)


class StopConditionEvaluator:
    """
    Evaluates stop conditions against current system state.
    
    ARCH-004: Uses canonical SystemState for consistent key access.
    """
    
    def __init__(self, vision_engine=None):
        """
        Initialize StopConditionEvaluator.
        
        Args:
            vision_engine: Optional vision engine for UI element checks
        """
        self.vision_engine = vision_engine
    
    def evaluate_stop_conditions(
        self,
        stop_conditions: List[StopCondition],
        system_state: SystemState
    ) -> bool:
        """
        Evaluate stop conditions against current system state.
        
        ARCH-004: Uses canonical SystemState for consistent key access.
        
        Args:
            stop_conditions: List of stop conditions to evaluate
            system_state: Current SystemState snapshot
        
        Returns:
            True if any stop condition is met.
        """
        if not stop_conditions:
            return False
        
        for condition in stop_conditions:
            if self.evaluate_single_stop_condition(condition, system_state):
                logger.info(f"✓ Stop condition met: {condition.type.value if hasattr(condition, 'type') else condition.get('type')} = {condition.value if hasattr(condition, 'value') else condition.get('value')}")
                return True
        
        return False
    
    def evaluate_single_stop_condition(
        self,
        condition: StopCondition,
        system_state: SystemState
    ) -> bool:
        """
        Evaluate a single stop condition.
        
        ARCH-004: Uses SystemState attributes directly for stable access.
        
        Args:
            condition: Stop condition to evaluate
            system_state: Current SystemState snapshot
        
        Returns:
            True if condition is met
        """
        # Handle both StopCondition objects and dicts
        if isinstance(condition, dict):
            cond_type = condition.get("type")
            cond_value = condition.get("value", "")
        else:
            cond_type = condition.type.value if isinstance(condition.type, StopConditionType) else condition.type
            cond_value = condition.value
        
        if cond_type == "url_contains":
            return cond_value.lower() in system_state.url.lower()
        
        elif cond_type == "url_equals":
            return system_state.url.lower() == cond_value.lower()
        
        elif cond_type == "app_active":
            return system_state.active_app.lower() == cond_value.lower()
        
        elif cond_type == "window_title_contains":
            return cond_value.lower() in system_state.window_title.lower()
        
        elif cond_type == "clipboard_contains":
            return cond_value.lower() in system_state.clipboard.lower()
        
        elif cond_type == "ui_element_visible":
            # TICKET-5: Implement vision-based element check via SOM
            # Check if element is visible by searching in SOM cache
            if not self.vision_engine or not self.vision_engine.is_available():
                logger.debug("ui_element_visible: vision engine not available")
                return False
            
            try:
                # cond_value can be either element_id or text to search for
                # Try element_id first
                element = self.vision_engine.get_element_by_id(cond_value)
                if element:
                    logger.info(f"✓ ui_element_visible: element '{cond_value}' found by ID")
                    return True
                
                # Fall back to text search
                element = self.vision_engine.find_element_by_text(cond_value)
                if element:
                    logger.info(f"✓ ui_element_visible: element with text '{cond_value}' found")
                    return True
                
                logger.debug(f"ui_element_visible: element '{cond_value}' not found")
                return False
                
            except Exception as e:
                logger.warning(f"ui_element_visible error: {e}")
                return False
        
        elif cond_type == "ui_element_contains_text":
            # TICKET-5: Implement vision-based text check via SOM
            # Format: "element_id:text" where we check if element_id contains text
            if not self.vision_engine or not self.vision_engine.is_available():
                logger.debug("ui_element_contains_text: vision engine not available")
                return False
            
            try:
                # Parse condition value - expected format: "element_id:text" or just "text"
                if ":" in cond_value:
                    element_id, text = cond_value.split(":", 1)
                    result = self.vision_engine.element_contains_text(element_id.strip(), text.strip())
                    if result:
                        logger.info(f"✓ ui_element_contains_text: element '{element_id}' contains '{text}'")
                    return result
                else:
                    # Just text - search for any element containing it
                    element = self.vision_engine.find_element_by_text(cond_value)
                    if element:
                        logger.info(f"✓ ui_element_contains_text: found element with text '{cond_value}'")
                        return True
                    return False
                    
            except Exception as e:
                logger.warning(f"ui_element_contains_text error: {e}")
                return False
        
        return False
