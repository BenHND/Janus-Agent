"""
LearningManager - Central coordinator for all learning components
Integrates with CommandParser for auto-improvement and feedback collection
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.learning.feedback_manager import FeedbackManager
from janus.learning.heuristic_updater import HeuristicUpdater
from janus.learning.learning_cache import LearningCache
from janus.learning.performance_reporter import PerformanceReporter
from janus.learning.user_correction_listener import UserCorrectionListener
from janus.logging import get_logger


class LearningManager:
    """
    Central manager for learning system
    Coordinates feedback collection, heuristic updates, and corrections
    """

    def __init__(
        self,
        db_path: str = "janus_learning.db",
        cache_path: str = "learning_cache.json",
        heuristics_config_path: str = "heuristics_config.json",
        correction_history_path: str = "correction_history.json",
        reports_dir: str = "performance_reports",
        profile_name: str = "default",
        auto_update: bool = True,
        update_interval_hours: int = 24,
    ):
        """
        Initialize learning manager

        Args:
            db_path: Path to feedback database
            cache_path: Path to learning cache
            heuristics_config_path: Path to heuristics config
            correction_history_path: Path to correction history
            reports_dir: Directory for performance reports
            profile_name: User profile name
            auto_update: Whether to automatically update heuristics
            update_interval_hours: Hours between automatic updates
        """
        # Initialize logger
        self.logger = get_logger("learning_manager")

        # Initialize components
        self.feedback_manager = FeedbackManager(db_path=db_path)
        self.learning_cache = LearningCache(cache_path=cache_path, profile_name=profile_name)
        self.heuristic_updater = HeuristicUpdater(
            feedback_manager=self.feedback_manager, config_path=heuristics_config_path
        )
        self.performance_reporter = PerformanceReporter(
            feedback_manager=self.feedback_manager,
            learning_cache=self.learning_cache,
            reports_dir=reports_dir,
        )
        self.correction_listener = UserCorrectionListener(
            correction_history_path=correction_history_path
        )

        # Configuration
        self.auto_update = auto_update
        self.update_interval_hours = update_interval_hours
        self.last_update = datetime.now()

        # Session tracking
        self.current_session_id: Optional[str] = None
        self.session_actions: List[Dict[str, Any]] = []

    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new learning session

        Args:
            session_id: Optional session ID (generated if not provided)

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.current_session_id = session_id
        self.session_actions = []

        return session_id

    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        End current learning session and generate report

        Returns:
            Session report or None if no active session
        """
        if self.current_session_id is None:
            return None

        report = self.performance_reporter.generate_session_report(
            self.current_session_id, save_to_file=True
        )

        # Trigger auto-update if needed
        if self.auto_update:
            self._check_and_update_heuristics()

        self.current_session_id = None
        self.session_actions = []

        return report

    def record_feedback(self, text: str, intent: Any, feedback_type: str) -> int:
        """
        Simple feedback recording for pipeline integration

        Args:
            text: Command text
            intent: Intent object
            feedback_type: 'POSITIVE' or 'NEGATIVE'

        Returns:
            Feedback entry ID
        """
        success = feedback_type == "POSITIVE"
        intent_str = intent.action if hasattr(intent, "action") else str(intent)
        confidence = intent.confidence if hasattr(intent, "confidence") else 0.5

        return self.record_command_parse(
            raw_command=text, parsed_intent=intent_str, confidence=confidence, success=success
        )

    def record_command_parse(
        self,
        raw_command: str,
        parsed_intent: str,
        confidence: float,
        success: bool,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Record feedback for a command parsing attempt

        Args:
            raw_command: Original command text
            parsed_intent: Detected intent
            confidence: Parse confidence
            success: Whether parsing succeeded
            execution_time_ms: Time taken to parse
            error_message: Error if parsing failed

        Returns:
            Feedback entry ID
        """
        action_context = {
            "raw_command": raw_command,
            "parsed_intent": parsed_intent,
            "confidence": confidence,
        }

        feedback_id = self.feedback_manager.record_feedback(
            action_type="command_parse",
            success=success,
            action_context=action_context,
            error_type="parse_error" if not success else None,
            error_message=error_message,
            duration_ms=execution_time_ms,
            session_id=self.current_session_id,
        )

        # Track in cache
        self.learning_cache.increment_action_count()

        return feedback_id

    def record_action_execution(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        success: bool,
        duration_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Record feedback for an action execution

        Args:
            action_type: Type of action executed
            action_parameters: Action parameters
            success: Whether action succeeded
            duration_ms: Execution duration
            error_type: Type of error if failed
            error_message: Error message if failed

        Returns:
            Feedback entry ID
        """
        feedback_id = self.feedback_manager.record_feedback(
            action_type=action_type,
            success=success,
            action_context=action_parameters,
            error_type=error_type,
            error_message=error_message,
            duration_ms=duration_ms,
            session_id=self.current_session_id,
            metadata={"source": "execution"},
        )

        # Record action for correction tracking
        action_record = {
            "action_type": action_type,
            "parameters": action_parameters,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        self.correction_listener.record_action(action_record)
        self.session_actions.append(action_record)

        # Track in cache
        self.learning_cache.increment_action_count()

        return feedback_id

    def record_user_correction(
        self,
        correction_text: str,
        language: str = "fr",
        alternative_action: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record a user correction

        Args:
            correction_text: User's correction input
            language: Language of correction
            alternative_action: User's preferred alternative

        Returns:
            Correction record or None
        """
        correction = self.correction_listener.process_correction(
            correction_text, language, alternative_action
        )

        if correction:
            self.learning_cache.increment_correction_count()

        return correction

    def get_recommended_parameters(self, action_type: str) -> Dict[str, Any]:
        """
        Get recommended parameters for an action type

        Args:
            action_type: Type of action

        Returns:
            Dictionary of recommended parameters
        """
        return {
            "wait_time_ms": self.heuristic_updater.get_wait_time(action_type),
            "retry_count": self.heuristic_updater.get_retry_count(action_type),
            "timeout_seconds": self.heuristic_updater.get_timeout(action_type),
            "success_probability": self.heuristic_updater.heuristics.get(
                "success_probabilities", {}
            ).get(action_type),
        }

    def should_avoid_action(
        self, action_type: str, context: Dict[str, Any], threshold: int = 2
    ) -> bool:
        """
        Check if action should be avoided based on corrections

        Args:
            action_type: Type of action
            context: Action context
            threshold: Minimum corrections to avoid

        Returns:
            True if action should be avoided
        """
        return self.correction_listener.should_avoid_action(action_type, context, threshold)

    def get_preferred_alternative(
        self, action_type: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get preferred alternative for an action

        Args:
            action_type: Type of action
            context: Action context

        Returns:
            Preferred alternative or None
        """
        return self.correction_listener.get_preferred_alternative(action_type, context)

    def update_all_heuristics(self, days: int = 7) -> Dict[str, Any]:
        """
        Manually trigger heuristics update

        Args:
            days: Days of data to analyze

        Returns:
            Update summary
        """
        updates = self.heuristic_updater.update_all_heuristics(days)
        self.last_update = datetime.now()
        return updates

    def _check_and_update_heuristics(self):
        """Check if heuristics need updating and update if necessary"""
        hours_since_update = (datetime.now() - self.last_update).total_seconds() / 3600

        if hours_since_update >= self.update_interval_hours:
            self.update_all_heuristics()

    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive performance summary

        Args:
            days: Days to analyze

        Returns:
            Performance summary
        """
        return self.performance_reporter.generate_comprehensive_report(
            days=days, save_to_file=False
        )

    def get_correction_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary of user corrections

        Args:
            days: Days to analyze

        Returns:
            Corrections summary
        """
        return self.correction_listener.get_corrections_summary(days)

    def get_success_rate(self, action_type: Optional[str] = None, days: int = 30) -> float:
        """
        Get success rate for actions

        Args:
            action_type: Specific action type (None for all)
            days: Days to analyze

        Returns:
            Success rate as percentage
        """
        return self.feedback_manager.get_success_rate(action_type=action_type, days=days)

    def get_recurring_errors(self, min_occurrences: int = 3, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recurring errors

        Args:
            min_occurrences: Minimum occurrences
            days: Days to analyze

        Returns:
            List of recurring errors
        """
        return self.feedback_manager.get_recurring_errors(
            min_occurrences=min_occurrences, days=days
        )

    def export_heuristics(self, output_path: str) -> bool:
        """
        Export learned heuristics to file

        Args:
            output_path: Path to export file

        Returns:
            True if successful
        """
        import json

        try:
            export_data = {
                "heuristics": self.heuristic_updater.get_heuristics_summary(),
                "cache": self.learning_cache.get_cache_summary(),
                "corrections": self.correction_listener.get_corrections_summary(),
                "exported_at": datetime.now().isoformat(),
                "profile": self.learning_cache.profile_name,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"Error exporting heuristics: {e}", exc_info=True)
            return False

    def import_heuristics(self, input_path: str) -> bool:
        """
        Import learned heuristics from file

        Args:
            input_path: Path to import file

        Returns:
            True if successful
        """
        import json

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            # Validate structure
            if "heuristics" not in import_data:
                self.logger.error("Invalid import file: missing heuristics data")
                return False

            # Import heuristics
            heuristics = import_data.get("heuristics", {})
            self.heuristic_updater.heuristics.update(heuristics)
            self.heuristic_updater._save_heuristics()

            self.logger.info(f"Successfully imported heuristics from {input_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error importing heuristics: {e}", exc_info=True)
            return False

    def get_learning_status(self) -> Dict[str, Any]:
        """
        Get overall learning system status

        Returns:
            Status dictionary
        """
        cache_summary = self.learning_cache.get_cache_summary()
        heuristics_summary = self.heuristic_updater.get_heuristics_summary()

        return {
            "profile": cache_summary["profile_name"],
            "total_actions": cache_summary["statistics"].get("total_actions", 0),
            "total_corrections": cache_summary["statistics"].get("total_corrections", 0),
            "learning_updates": cache_summary["statistics"].get("learning_updates", 0),
            "heuristics_count": len(heuristics_summary.get("wait_times", {})),
            "last_heuristic_update": heuristics_summary.get("last_updated"),
            "session_active": self.current_session_id is not None,
            "current_session_id": self.current_session_id,
            "auto_update_enabled": self.auto_update,
            "hours_since_last_update": (datetime.now() - self.last_update).total_seconds() / 3600,
        }

    # LEARNING-001: Skill Caching Methods
    def store_corrective_sequence(
        self,
        intent_text: str,
        intent_vector: Optional[bytes] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Store successful action sequence after user correction as a learned skill

        Args:
            intent_text: The user's intent/command
            intent_vector: Optional embedding vector for the intent
            context_data: Optional visual/contextual state data

        Returns:
            Skill ID if stored, None otherwise
        """
        # Extract successful actions from the session
        successful_actions = [
            action for action in self.session_actions if action.get("success", False)
        ]

        if not successful_actions:
            self.logger.debug("No successful actions to store as skill")
            return None

        # Clean and simplify action sequence
        cleaned_sequence = self._clean_action_sequence(successful_actions)

        if not cleaned_sequence:
            self.logger.debug("Cleaned sequence is empty, not storing")
            return None

        # Generate context hash
        context_hash = self._compute_context_hash(intent_text, context_data)

        # Generate or use provided intent vector
        if intent_vector is None:
            intent_vector = self._generate_intent_vector(intent_text)

        # Store in skill cache
        try:
            skill_id = self.feedback_manager.store_skill(
                intent_vector=intent_vector,
                context_hash=context_hash,
                action_sequence=cleaned_sequence,
                intent_text=intent_text,
            )

            self.logger.info(
                f"Stored skill {skill_id} for intent '{intent_text}' "
                f"with {len(cleaned_sequence)} actions"
            )

            return skill_id
        except Exception as e:
            self.logger.error(f"Error storing skill: {e}", exc_info=True)
            return None

    def retrieve_cached_skill(
        self,
        intent_text: str,
        intent_vector: Optional[bytes] = None,
        context_data: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.8,
        return_metadata: bool = False,
    ) -> Optional[Any]:
        """
        Retrieve a cached skill for the given intent and context
        
        LEARNING-001: Updated to support returning full metadata for SkillHint creation.

        Args:
            intent_text: The user's intent/command
            intent_vector: Optional embedding vector for the intent
            context_data: Optional visual/contextual state data
            similarity_threshold: Minimum similarity for vector matching
            return_metadata: If True, return full skill metadata dict; if False, return just actions

        Returns:
            - If return_metadata=True: Dict with skill_id, intent_text, action_sequence, etc.
            - If return_metadata=False: List[Dict[str, Any]] action sequence (legacy behavior)
            - None if no skill found
        """
        # Generate context hash
        context_hash = self._compute_context_hash(intent_text, context_data)

        # Generate or use provided intent vector
        if intent_vector is None:
            intent_vector = self._generate_intent_vector(intent_text)

        # Retrieve from skill cache
        try:
            result = self.feedback_manager.retrieve_skill(
                intent_vector=intent_vector,
                context_hash=context_hash,
                similarity_threshold=similarity_threshold,
                return_metadata=return_metadata,
            )

            if result:
                if return_metadata:
                    self.logger.info(
                        f"Retrieved cached skill metadata for '{intent_text}' "
                        f"(skill_id: {result.get('skill_id', 'unknown')})"
                    )
                else:
                    self.logger.info(
                        f"Retrieved cached skill for '{intent_text}' "
                        f"with {len(result)} actions"
                    )

            return result
        except Exception as e:
            self.logger.error(f"Error retrieving skill: {e}", exc_info=True)
            return None

    def _clean_action_sequence(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and simplify action sequence for storage
        
        Filters out:
        - Actions without action_type
        - Consecutive duplicate actions (likely retry attempts)
        - Redundant actions with same type and parameters
        
        This prevents storing failed attempts or retry sequences
        that were part of the learning process.

        Args:
            actions: Raw action sequence (should be pre-filtered for success=True)

        Returns:
            Cleaned action sequence without duplicates or retries
        """
        if not actions:
            return []
            
        cleaned = []
        last_action = None
        
        for action in actions:
            # Extract essential fields only
            cleaned_action = {
                "action_type": action.get("action_type"),
                "parameters": action.get("parameters", {}),
            }

            # Filter out None values, empty strings, and empty parameters
            if not cleaned_action["action_type"]:
                continue
                
            if not cleaned_action["parameters"]:
                del cleaned_action["parameters"]
            
            # Check for consecutive duplicates (likely retry attempts)
            # This prevents storing sequences like: click, click, click from failed retries
            if last_action is not None:
                if self._actions_are_equivalent(cleaned_action, last_action):
                    # Skip this duplicate action
                    self.logger.debug(
                        f"Filtered duplicate action: {cleaned_action['action_type']}"
                    )
                    continue
            
            cleaned.append(cleaned_action)
            last_action = cleaned_action

        return cleaned
    
    def _actions_are_equivalent(
        self, action1: Dict[str, Any], action2: Dict[str, Any]
    ) -> bool:
        """
        Check if two actions are equivalent (same type and parameters)
        
        Args:
            action1: First action
            action2: Second action
            
        Returns:
            True if actions are equivalent
        """
        if action1.get("action_type") != action2.get("action_type"):
            return False
            
        # Both have same action_type, now check parameters
        params1 = action1.get("parameters", {})
        params2 = action2.get("parameters", {})
        
        # Deep comparison of parameters
        return self._deep_dict_equal(params1, params2)
    
    def _deep_dict_equal(self, dict1: Any, dict2: Any) -> bool:
        """
        Recursively compare two dictionaries for deep equality
        
        Args:
            dict1: First dictionary or value
            dict2: Second dictionary or value
            
        Returns:
            True if equal
        """
        # Handle non-dict types
        if type(dict1) is not type(dict2):
            return False
            
        if not isinstance(dict1, dict):
            return dict1 == dict2
        
        # Compare dict keys
        if set(dict1.keys()) != set(dict2.keys()):
            return False
        
        # Recursively compare values
        for key in dict1:
            if not self._deep_dict_equal(dict1[key], dict2[key]):
                return False
                
        return True

    def _compute_context_hash(
        self, intent_text: str, context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute hash for intent and context

        Args:
            intent_text: The user's intent/command
            context_data: Optional contextual state data

        Returns:
            Hash string
        """
        # Normalize intent text
        normalized_intent = intent_text.lower().strip()

        # Create hash input
        hash_input = normalized_intent

        if context_data:
            # Include relevant context fields
            context_str = json.dumps(context_data, sort_keys=True)
            hash_input += context_str

        # Generate hash
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _generate_intent_vector(self, intent_text: str) -> bytes:
        """
        Generate embedding vector for intent text

        Args:
            intent_text: The user's intent/command

        Returns:
            Vector as bytes
        """
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            import numpy as np

            # Use same model as SemanticRouter for consistency
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            embedding = model.encode([intent_text])[0]

            # Convert to bytes
            return embedding.astype(np.float32).tobytes()
        except (ImportError, Exception) as e:
            # Fallback: use simple hash as pseudo-vector
            # This handles both missing dependencies and corrupted installations
            self.logger.debug(f"Could not generate embedding vector, using hash fallback: {e}")
            hash_bytes = hashlib.sha256(intent_text.encode()).digest()
            # Repeat to create a 384-dimensional pseudo-vector (same as all-MiniLM-L6-v2)
            pseudo_vector = hash_bytes * 12  # 32 bytes * 12 = 384 bytes
            return pseudo_vector[:384]

    def get_cached_skills_summary(self) -> Dict[str, Any]:
        """
        Get summary of cached skills

        Returns:
            Summary dictionary
        """
        try:
            skills = self.feedback_manager.get_all_skills(limit=100)
            return {
                "total_skills": len(skills),
                "skills": [
                    {
                        "intent": skill["intent_text"],
                        "actions_count": len(skill["action_sequence"]),
                        "success_count": skill["success_count"],
                        "last_used": skill["last_used"],
                    }
                    for skill in skills[:10]  # Show top 10
                ],
            }
        except Exception as e:
            self.logger.error(f"Error getting skills summary: {e}", exc_info=True)
            return {"total_skills": 0, "skills": []}
