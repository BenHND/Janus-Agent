"""
FeedbackManager - Records and analyzes action success/failure rates
Tracks patterns to identify recurring errors and learning opportunities
"""

import json
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FeedbackManager:
    """
    Manages feedback tracking for actions
    Records success/failure rates and identifies patterns
    """

    def __init__(self, db_path: str = "janus_learning.db"):
        """
        Initialize feedback manager

        Args:
            db_path: Path to SQLite database for feedback storage
        """
        self.db_path = Path(db_path)
        self._initialize_tables()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_tables(self):
        """Create feedback tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Action feedback table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    action_context TEXT,
                    success INTEGER NOT NULL,
                    error_type TEXT,
                    error_message TEXT,
                    duration_ms INTEGER,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    metadata TEXT
                )
            """
            )

            # Skill cache table (LEARNING-001)
            # Stores learned action sequences that succeeded after corrections
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_vector BLOB NOT NULL,
                    context_hash TEXT NOT NULL,
                    action_sequence TEXT NOT NULL,
                    intent_text TEXT,
                    success_count INTEGER DEFAULT 1,
                    last_used TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(context_hash)
                )
            """
            )

            # Create indexes for efficient querying
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_action_type
                ON action_feedback(action_type)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_timestamp
                ON action_feedback(timestamp DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_success
                ON action_feedback(success)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skill_cache_context
                ON skill_cache(context_hash)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skill_cache_last_used
                ON skill_cache(last_used DESC)
            """
            )

    def record_feedback(
        self,
        action_type: str,
        success: bool,
        action_context: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record feedback for an action

        Args:
            action_type: Type of action (click, copy, open_app, etc.)
            success: Whether action succeeded
            action_context: Context information (target, parameters, etc.)
            error_type: Type of error if failed
            error_message: Error message if failed
            duration_ms: Execution duration in milliseconds
            session_id: Session identifier
            metadata: Additional metadata

        Returns:
            ID of recorded feedback entry
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action_feedback (
                    action_type, action_context, success, error_type,
                    error_message, duration_ms, timestamp, session_id, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    action_type,
                    json.dumps(action_context) if action_context else None,
                    1 if success else 0,
                    error_type,
                    error_message,
                    duration_ms,
                    datetime.now().isoformat(),
                    session_id,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            return cursor.lastrowid

    def get_success_rate(
        self,
        action_type: Optional[str] = None,
        days: int = 30,
        context_filter: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate success rate for actions

        Args:
            action_type: Specific action type (None for all actions)
            days: Number of days to look back
            context_filter: Filter by context attributes

        Returns:
            Success rate as percentage (0-100)
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            query = "SELECT AVG(success) * 100 FROM action_feedback WHERE timestamp >= ?"
            params = [cutoff_date]

            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)

            cursor.execute(query, params)
            result = cursor.fetchone()[0]
            return float(result) if result is not None else 0.0

    def get_action_statistics(
        self, action_type: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed statistics for actions

        Args:
            action_type: Specific action type (None for all)
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            query_base = "FROM action_feedback WHERE timestamp >= ?"
            params = [cutoff_date]

            if action_type:
                query_base += " AND action_type = ?"
                params.append(action_type)

            # Total count
            cursor.execute(f"SELECT COUNT(*) {query_base}", params)
            total_count = cursor.fetchone()[0]

            # Success count
            cursor.execute(f"SELECT COUNT(*) {query_base} AND success = 1", params)
            success_count = cursor.fetchone()[0]

            # Average duration
            cursor.execute(
                f"SELECT AVG(duration_ms) {query_base} AND duration_ms IS NOT NULL", params
            )
            avg_duration = cursor.fetchone()[0]

            # Most common errors
            cursor.execute(
                f"""
                SELECT error_type, COUNT(*) as count
                {query_base} AND success = 0 AND error_type IS NOT NULL
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 5
            """,
                params,
            )
            common_errors = [{"error_type": row[0], "count": row[1]} for row in cursor.fetchall()]

            return {
                "total_count": total_count,
                "success_count": success_count,
                "failure_count": total_count - success_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0.0,
                "avg_duration_ms": float(avg_duration) if avg_duration else 0.0,
                "common_errors": common_errors,
            }

    def get_recurring_errors(self, min_occurrences: int = 3, days: int = 7) -> List[Dict[str, Any]]:
        """
        Identify recurring errors

        Args:
            min_occurrences: Minimum times error must occur
            days: Days to analyze

        Returns:
            List of recurring error patterns
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    action_type,
                    error_type,
                    error_message,
                    COUNT(*) as occurrence_count,
                    MAX(timestamp) as last_occurrence
                FROM action_feedback
                WHERE timestamp >= ? AND success = 0 AND error_type IS NOT NULL
                GROUP BY action_type, error_type, error_message
                HAVING COUNT(*) >= ?
                ORDER BY occurrence_count DESC
            """,
                (cutoff_date, min_occurrences),
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "action_type": row[0],
                        "error_type": row[1],
                        "error_message": row[2],
                        "occurrence_count": row[3],
                        "last_occurrence": row[4],
                    }
                )

            return results

    def get_performance_trend(
        self, action_type: str, days: int = 30, bucket_size_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get performance trend over time

        Args:
            action_type: Action type to analyze
            days: Number of days
            bucket_size_hours: Time bucket size in hours

        Returns:
            List of time-bucketed performance metrics
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    datetime(timestamp, 'start of day') as date_bucket,
                    COUNT(*) as total,
                    SUM(success) as successes,
                    AVG(duration_ms) as avg_duration
                FROM action_feedback
                WHERE action_type = ? AND timestamp >= ?
                GROUP BY date_bucket
                ORDER BY date_bucket ASC
            """,
                (action_type, cutoff_date),
            )

            results = []
            for row in cursor.fetchall():
                total = row[1]
                successes = row[2]
                results.append(
                    {
                        "date": row[0],
                        "total_count": total,
                        "success_count": successes,
                        "success_rate": (successes / total * 100) if total > 0 else 0.0,
                        "avg_duration_ms": float(row[3]) if row[3] else 0.0,
                    }
                )

            return results

    def clear_old_feedback(self, days: int = 90):
        """
        Clear feedback older than specified days

        Args:
            days: Keep feedback from last N days
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM action_feedback WHERE timestamp < ?", (cutoff_date,))

    def get_feedback_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific session

        Args:
            session_id: Session identifier

        Returns:
            List of feedback entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM action_feedback
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """,
                (session_id,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        result = dict(row)

        # Parse JSON fields
        if "action_context" in result and result["action_context"]:
            result["action_context"] = json.loads(result["action_context"])
        if "metadata" in result and result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])

        # Convert success to boolean
        if "success" in result:
            result["success"] = bool(result["success"])

        return result

    # LEARNING-001: Skill Cache Methods
    def store_skill(
        self,
        intent_vector: bytes,
        context_hash: str,
        action_sequence: List[Dict[str, Any]],
        intent_text: Optional[str] = None,
    ) -> int:
        """
        Store a learned skill (action sequence) in cache

        Args:
            intent_vector: Embedding vector for the intent (as bytes)
            context_hash: Hash of the visual/contextual state
            action_sequence: List of actions that succeeded
            intent_text: Human-readable intent text

        Returns:
            ID of stored skill
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()

            # Check if skill already exists for this context
            cursor.execute(
                "SELECT id, success_count FROM skill_cache WHERE context_hash = ?",
                (context_hash,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing skill
                skill_id = existing[0]
                success_count = existing[1] + 1
                cursor.execute(
                    """
                    UPDATE skill_cache
                    SET intent_vector = ?, action_sequence = ?, intent_text = ?,
                        success_count = ?, last_used = ?
                    WHERE id = ?
                """,
                    (
                        intent_vector,
                        json.dumps(action_sequence),
                        intent_text,
                        success_count,
                        timestamp,
                        skill_id,
                    ),
                )
            else:
                # Insert new skill
                cursor.execute(
                    """
                    INSERT INTO skill_cache (
                        intent_vector, context_hash, action_sequence,
                        intent_text, success_count, last_used, created_at
                    )
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                    (
                        intent_vector,
                        context_hash,
                        json.dumps(action_sequence),
                        intent_text,
                        timestamp,
                        timestamp,
                    ),
                )
                skill_id = cursor.lastrowid

            return skill_id

    def retrieve_skill(
        self, 
        intent_vector: bytes, 
        context_hash: str, 
        similarity_threshold: float = 0.8,
        return_metadata: bool = False,
    ) -> Optional[Any]:
        """
        Retrieve a cached skill by intent and context
        
        LEARNING-001: Updated to support returning full metadata for SkillHint creation.

        Args:
            intent_vector: Embedding vector for the intent
            context_hash: Hash of the visual/contextual state
            similarity_threshold: Minimum similarity for vector matching (0-1)
            return_metadata: If True, return full metadata dict; if False, return just actions

        Returns:
            - If return_metadata=True: Dict with skill_id, intent_text, action_sequence, etc.
            - If return_metadata=False: List[Dict[str, Any]] action sequence (legacy)
            - None if not found or similarity too low
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Query with all fields if metadata requested
            if return_metadata:
                cursor.execute(
                    """
                    SELECT id, action_sequence, intent_vector, intent_text, 
                           success_count, last_used, context_hash
                    FROM skill_cache
                    WHERE context_hash = ?
                """,
                    (context_hash,),
                )
            else:
                # Legacy query: just action_sequence and intent_vector
                cursor.execute(
                    """
                    SELECT action_sequence, intent_vector, last_used
                    FROM skill_cache
                    WHERE context_hash = ?
                """,
                    (context_hash,),
                )

            result = cursor.fetchone()
            if result:
                if return_metadata:
                    skill_id, action_seq_json, stored_vector, intent_text, success_count, last_used, ctx_hash = result
                    action_sequence = json.loads(action_seq_json)
                else:
                    action_seq_json, stored_vector, last_used = result
                    action_sequence = json.loads(action_seq_json)

                # Calculate similarity if vectors are available
                similarity = 1.0  # Default if no vector comparison
                if stored_vector and intent_vector:
                    try:
                        import numpy as np

                        stored_vec = np.frombuffer(stored_vector, dtype=np.float32)
                        query_vec = np.frombuffer(intent_vector, dtype=np.float32)

                        # Cosine similarity
                        similarity = np.dot(stored_vec, query_vec) / (
                            np.linalg.norm(stored_vec) * np.linalg.norm(query_vec)
                        )

                        if similarity < similarity_threshold:
                            return None  # Not similar enough
                            
                    except (ImportError, Exception) as e:
                        # If similarity calculation fails, continue with default similarity
                        # (fail-open approach) - handles both missing numpy and calculation errors
                        pass

                # Update last_used timestamp
                cursor.execute(
                    "UPDATE skill_cache SET last_used = ?, success_count = success_count + 1 WHERE context_hash = ?",
                    (datetime.now().isoformat(), context_hash),
                )
                
                # Return appropriate format
                if return_metadata:
                    return {
                        "skill_id": skill_id,
                        "intent_text": intent_text,
                        "action_sequence": action_sequence,
                        "context_hash": ctx_hash,
                        "success_count": success_count + 1,  # +1 because we just incremented
                        "last_used": datetime.now().isoformat(),
                        "similarity": similarity,
                    }
                else:
                    return action_sequence

            return None

    def get_all_skills(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all cached skills

        Args:
            limit: Maximum number of skills to return

        Returns:
            List of skill records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, context_hash, action_sequence, intent_text,
                       success_count, last_used, created_at
                FROM skill_cache
                ORDER BY last_used DESC
                LIMIT ?
            """,
                (limit,),
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "id": row[0],
                        "context_hash": row[1],
                        "action_sequence": json.loads(row[2]),
                        "intent_text": row[3],
                        "success_count": row[4],
                        "last_used": row[5],
                        "created_at": row[6],
                    }
                )

            return results

    def clear_old_skills(self, days: int = 90):
        """
        Clear skills not used in specified days

        Args:
            days: Keep skills used in last N days
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skill_cache WHERE last_used < ?", (cutoff_date,))
