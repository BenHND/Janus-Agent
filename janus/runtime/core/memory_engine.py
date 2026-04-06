"""
MemoryEngine: Unified Memory System for Janus

TICKET-AUDIT-005: Consolidates 6 memory systems into a single, coherent API.
TICKET-MEM-001: Adds semantic memory (RAG Local) for contextual reference resolution.

This is the ONLY memory system you should use in Janus.

Unified Architecture:
- Storage: SQLite persistence (that were in MemoryService)
- Session: Current session context (from SessionContext)
- History: Past actions and commands (that were in MemoryService)
- Context: Extracted variables and context (from ContextMemory)
- Conversation: Multi-turn dialogue (that were in ConversationManager)
- Semantic Memory: Vector-based semantic search (TICKET-MEM-001)

Public API (11 core methods):
1. store(key, value) - Store any data
2. retrieve(key) - Retrieve stored data
3. add_context(context) - Add contextual information
4. get_context(limit) - Get recent context
5. record_action(action) - Record an action
6. get_history(limit) - Get action history
7. start_conversation() - Start a conversation
8. end_conversation() - End current conversation
9. resolve_reference(ref) - Resolve "it", "that", etc.
10. search_semantic(query, limit) - Semantic search through action history
11. cleanup() - Clean up old data
"""

import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache Python logger for exception handling in log_structured
_py_logger_cache = logging.getLogger(__name__)

# TICKET-MEM-001: Constants for semantic memory
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ACTION_DESCRIPTION_MAX_LENGTH = 100

# TICKET-MEM-001: Lazy imports for semantic memory (optional dependencies)
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    SEMANTIC_MEMORY_AVAILABLE = True
except ImportError:
    SEMANTIC_MEMORY_AVAILABLE = False
    logger.warning("Semantic memory dependencies (chromadb, sentence-transformers) not available. "
                  "Install them to enable semantic search: pip install chromadb sentence-transformers")


class MemoryEngine:
    """
    Unified Memory Engine for Janus
    
    Consolidates all memory operations into a single, simple API.
    Replaces: MemoryService, UnifiedMemory, ContextMemory, 
              ConversationManager, SessionContext, UnifiedStore
    
    Features:
    - Thread-safe SQLite storage
    - Session management
    - Context tracking with temporal decay
    - Action history
    - Conversation tracking
    - Reference resolution ("it", "that", "here")
    - Automatic cleanup
    """
    
    def __init__(self, db_path: str = "janus_memory.db", session_id: Optional[str] = None,
                 enable_semantic_memory: bool = True):
        """
        Initialize Memory Engine
        
        Args:
            db_path: Path to SQLite database. Can be a string path or an object with a 'path' 
                    attribute (e.g., DatabaseSettings) for backwards compatibility.
            session_id: Session ID (creates new if None)
            enable_semantic_memory: Enable semantic memory (requires chromadb and sentence-transformers)
        """
        # Handle both string path and object with path attribute (backwards compatibility)
        if hasattr(db_path, 'path'):
            db_path = db_path.path
        self.db_path = Path(db_path)
        self._lock = Lock()
        
        # Initialize database
        self._init_database()
        
        # Create or load session
        if session_id is None:
            self.session_id = self._create_session()
        else:
            self.session_id = session_id
            if not self._session_exists(session_id):
                self._create_session(session_id)
        
        # In-memory quick references
        self._quick_refs = {
            "last_command": None,
            "last_copied": None,
            "last_clicked": None,
            "last_app": None,
            "last_file": None,
            "last_url": None,
        }
        
        # Current conversation tracking
        self._current_conversation_id: Optional[str] = None
        
        # TICKET-MEM-001: Initialize semantic memory (vector database)
        self._semantic_memory_enabled = False
        self._embedding_model = None
        self._chroma_client = None
        self._chroma_collection = None
        
        if enable_semantic_memory and SEMANTIC_MEMORY_AVAILABLE:
            try:
                self._init_semantic_memory()
                self._semantic_memory_enabled = True
                logger.info("Semantic memory initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic memory: {e}")
        elif enable_semantic_memory and not SEMANTIC_MEMORY_AVAILABLE:
            logger.info("Semantic memory requested but dependencies not available")
        
        logger.info(f"MemoryEngine initialized with session {self.session_id}")
    
    @contextmanager
    def _get_connection(self):
        """Thread-safe database connection"""
        with self._lock:
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
    
    def _init_database(self):
        """
        Initialize unified database schema using migration system.
        
        TICKET-DB-001: Uses MigrationManager to apply schema changes instead of
        raw CREATE TABLE statements. This allows existing databases to be upgraded
        without data loss.
        """
        from janus.runtime.core.db_migrations import MigrationManager
        
        try:
            # Create migration manager and apply all pending migrations
            migration_manager = MigrationManager(self.db_path)
            
            # Get migration info for logging
            info = migration_manager.get_migration_info()
            if info["migrations_needed"] > 0:
                logger.info(
                    f"Database migration required: v{info['current_version']} -> v{info['latest_version']}"
                )
            
            # Apply migrations
            success = migration_manager.apply_migrations()
            
            if not success:
                raise RuntimeError("Database migration failed")
            
            # Verify schema after migration
            if not migration_manager.verify_schema():
                logger.warning("Database schema verification failed, but continuing anyway")
        
        except Exception as e:
            logger.error(f"Database initialization/migration failed: {e}")
            raise
    
    def _init_semantic_memory(self):
        """
        Initialize semantic memory system (TICKET-MEM-001)
        
        Sets up ChromaDB vector database and embedding model for semantic search.
        """
        if not SEMANTIC_MEMORY_AVAILABLE:
            return
        
        try:
            # Initialize embedding model (lightweight and efficient)
            logger.info(f"Loading embedding model ({DEFAULT_EMBEDDING_MODEL})...")
            from janus.ai.embeddings.shared_sentence_transformer import get_sentence_transformer

            self._embedding_model = get_sentence_transformer(DEFAULT_EMBEDDING_MODEL)
            
            # Initialize ChromaDB client (persistent storage)
            chroma_path = self.db_path.parent / f"{self.db_path.stem}_chroma"
            chroma_path.mkdir(exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_path))
            
            # Create or get collection for action history
            # Sanitize session_id for ChromaDB collection name (alphanumeric and underscores only)
            safe_session_id = "".join(c if c.isalnum() or c == "_" else "_" for c in self.session_id)
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name=f"actions_{safe_session_id}",
                metadata={"description": "Semantic memory for action history"}
            )
            
            logger.info("Semantic memory initialized with ChromaDB")
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory: {e}")
            self._embedding_model = None
            self._chroma_client = None
            self._chroma_collection = None
            raise
    
    # ========== Core API (11 methods) ==========
    
    def store(self, key: str, value: Any, session_id: Optional[str] = None) -> bool:
        """
        Store data in memory (Core API #1)
        
        Args:
            key: Storage key
            value: Value to store (JSON-serializable)
            session_id: Optional session ID (uses current if None)
            
        Returns:
            True if successful
        """
        session = session_id or self.session_id
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO storage (session_id, key, value, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (session, key, json.dumps(value)))
            return True
        except Exception as e:
            logger.error(f"Failed to store {key}: {e}")
            return False
    
    def retrieve(self, key: str, default: Any = None, session_id: Optional[str] = None) -> Any:
        """
        Retrieve data from memory (Core API #2)
        
        Args:
            key: Storage key
            default: Default value if not found
            session_id: Optional session ID (uses current if None)
            
        Returns:
            Stored value or default
        """
        session = session_id or self.session_id
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT value FROM storage
                    WHERE session_id = ? AND key = ?
                """, (session, key))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row["value"])
                return default
        except Exception as e:
            logger.error(f"Failed to retrieve {key}: {e}")
            return default
    
    def add_context(self, context_type: str, data: Dict[str, Any], 
                   relevance: float = 1.0, session_id: Optional[str] = None) -> bool:
        """
        Add contextual information (Core API #3)
        
        Args:
            context_type: Type of context (e.g., "user_action", "app_state", "intent")
            data: Context data
            relevance: Relevance score (0.0-1.0)
            session_id: Optional session ID
            
        Returns:
            True if successful
        """
        session = session_id or self.session_id
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO context (session_id, context_type, data, relevance_score)
                    VALUES (?, ?, ?, ?)
                """, (session, context_type, json.dumps(data), relevance))
            return True
        except Exception as e:
            logger.error(f"Failed to add context: {e}")
            return False
    
    def get_context(self, max_tokens: int = 2000, context_type: Optional[str] = None,
                   min_relevance: float = 0.0, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent context that fits within token budget (Core API #4)
        
        TICKET-LLM-001: Token-aware context retrieval (default behavior).
        Retrieves context items from most recent to oldest, stopping when token budget is reached.
        This prevents LLM context overflow.
        
        Args:
            max_tokens: Maximum tokens to include (default: 2000)
            context_type: Filter by context type
            min_relevance: Minimum relevance score
            session_id: Optional session ID
            
        Returns:
            List of context items that fit within token budget
        """
        # Import token counter
        from janus.utils.token_counter import get_token_counter
        
        session = session_id or self.session_id
        token_counter = get_token_counter()
        
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT context_type, data, timestamp, relevance_score
                    FROM context
                    WHERE session_id = ? AND relevance_score >= ?
                """
                params = [session, min_relevance]
                
                if context_type:
                    query += " AND context_type = ?"
                    params.append(context_type)
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, params)
                
                # Stack items from newest to oldest until budget is reached
                results = []
                total_tokens = 0
                
                for row in cursor.fetchall():
                    item = {
                        "type": row["context_type"],
                        "data": json.loads(row["data"]),
                        "timestamp": row["timestamp"],
                        "relevance": row["relevance_score"]
                    }
                    
                    # Count tokens for this item
                    item_text = json.dumps(item, ensure_ascii=False)
                    item_tokens = token_counter.count_tokens(item_text)
                    
                    # Check if adding this item would exceed budget
                    if total_tokens + item_tokens > max_tokens:
                        logger.debug(
                            f"Token budget reached: {total_tokens} tokens, "
                            f"excluding remaining items"
                        )
                        break
                    
                    results.append(item)
                    total_tokens += item_tokens
                
                logger.debug(f"Retrieved {len(results)} context items ({total_tokens} tokens)")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return []

    def record_action(self, action_type: str, action_data: Dict[str, Any],
                     result: Optional[Dict[str, Any]] = None,
                     session_id: Optional[str] = None) -> bool:
        """
        Record an action in history (Core API #5)
        
        TICKET-MEM-001: Also vectorizes the action description for semantic search.
        
        Args:
            action_type: Type of action (e.g., "command", "click", "copy")
            action_data: Action details
            result: Optional execution result
            session_id: Optional session ID
            
        Returns:
            True if successful
        """
        session = session_id or self.session_id
        
        try:
            # Store in SQLite
            action_id = None
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO history (session_id, action_type, action_data, result)
                    VALUES (?, ?, ?, ?)
                """, (session, action_type, json.dumps(action_data), 
                     json.dumps(result) if result else None))
                action_id = cursor.lastrowid
            
            # Update quick references
            self._update_quick_refs(action_type, action_data)
            
            # Update session last accessed
            self._touch_session(session)
            
            # TICKET-MEM-001: Vectorize and store in semantic memory
            if self._semantic_memory_enabled and action_id:
                self._vectorize_action(action_id, action_type, action_data)
            
            return True
        except Exception as e:
            logger.error(f"Failed to record action: {e}")
            return False
    
    def get_history(self, max_tokens: int = 4000, action_type: Optional[str] = None,
                   session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get action history that fits within token budget (Core API #6)
        
        TICKET-LLM-001: Token-aware history retrieval (default behavior).
        Retrieves history items from most recent to oldest, stopping when token budget is reached.
        This prevents LLM context overflow when users paste large amounts of text.
        
        Args:
            max_tokens: Maximum tokens to include (default: 4000)
            action_type: Filter by action type
            session_id: Optional session ID
            
        Returns:
            List of history items that fit within token budget
        """
        # Import token counter
        from janus.utils.token_counter import get_token_counter
        
        session = session_id or self.session_id
        token_counter = get_token_counter()
        
        try:
            with self._get_connection() as conn:
                # Get all history items in reverse chronological order
                query = """
                    SELECT action_type, action_data, result, timestamp
                    FROM history
                    WHERE session_id = ?
                """
                params = [session]
                
                if action_type:
                    query += " AND action_type = ?"
                    params.append(action_type)
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, params)
                
                # Stack items from newest to oldest until budget is reached
                results = []
                total_tokens = 0
                
                for row in cursor.fetchall():
                    item = {
                        "type": row["action_type"],
                        "data": json.loads(row["action_data"]),
                        "result": json.loads(row["result"]) if row["result"] else None,
                        "timestamp": row["timestamp"]
                    }
                    
                    # Count tokens for this item
                    item_text = json.dumps(item, ensure_ascii=False)
                    item_tokens = token_counter.count_tokens(item_text)
                    
                    # Check if adding this item would exceed budget
                    if total_tokens + item_tokens > max_tokens:
                        logger.debug(
                            f"Token budget reached: {total_tokens} tokens, "
                            f"excluding remaining items"
                        )
                        break
                    
                    results.append(item)
                    total_tokens += item_tokens
                
                logger.debug(f"Retrieved {len(results)} history items ({total_tokens} tokens)")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def start_conversation(self, session_id: Optional[str] = None) -> str:
        """
        Start a new conversation (Core API #7)
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Conversation ID
        """
        session = session_id or self.session_id
        conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO conversations (conversation_id, session_id, state)
                    VALUES (?, ?, 'active')
                """, (conversation_id, session))
            
            self._current_conversation_id = conversation_id
            logger.info(f"Started conversation {conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            return ""
    
    def end_conversation(self, conversation_id: Optional[str] = None,
                        reason: str = "completed") -> bool:
        """
        End a conversation (Core API #8)
        
        Args:
            conversation_id: Conversation ID (uses current if None)
            reason: Reason for ending
            
        Returns:
            True if successful
        """
        conv_id = conversation_id or self._current_conversation_id
        
        if not conv_id:
            return False
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE conversations
                    SET state = 'completed', ended_at = CURRENT_TIMESTAMP, end_reason = ?
                    WHERE conversation_id = ?
                """, (reason, conv_id))
            
            if conv_id == self._current_conversation_id:
                self._current_conversation_id = None
            
            logger.info(f"Ended conversation {conv_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")
            return False
    
    def resolve_reference(self, reference: str) -> Optional[Any]:
        """
        Resolve contextual references like "it", "that", "here" (Core API #9)
        
        TICKET-MEM-001: Now uses semantic search as fallback when exact keywords fail.
        
        Args:
            reference: Reference text (e.g., "it", "the PDF from earlier", "le fichier d'hier")
            
        Returns:
            Resolved value or None
        """
        ref_lower = reference.lower().strip()
        
        # Direct quick reference lookup (exact keywords)
        if ref_lower in ["it", "that", "le", "la", "ça"]:
            result = self._quick_refs.get("last_copied")
            if result:
                return result
        
        if ref_lower in ["here", "ici"]:
            result = self._quick_refs.get("last_clicked")
            if result:
                return result
        
        if "file" in ref_lower or "fichier" in ref_lower:
            result = self._quick_refs.get("last_file")
            if result:
                return result
        
        if "app" in ref_lower or "application" in ref_lower:
            result = self._quick_refs.get("last_app")
            if result:
                return result
        
        if "url" in ref_lower or "site" in ref_lower:
            result = self._quick_refs.get("last_url")
            if result:
                return result
        
        # Try to resolve from recent context
        recent_context = self.get_context(max_tokens=500)  # Small budget for recent context
        for ctx in recent_context:
            if ctx["type"] in ["copy", "file", "app", "url"]:
                result = ctx["data"].get("value")
                if result:
                    return result
        
        # TICKET-MEM-001: Fallback to semantic search
        if self._semantic_memory_enabled:
            semantic_results = self.search_semantic(reference, limit=1)
            if semantic_results:
                # Extract the most relevant value from the action
                action_data = semantic_results[0].get("data", {})
                
                # Try common fields that might contain the referenced value
                for field in ["file_path", "app_name", "url", "content", "value", "path"]:
                    if field in action_data:
                        return action_data[field]
                
                # Return the whole action_data if no specific field found
                return action_data
        
        return None
    
    def search_semantic(self, query: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Search action history using semantic similarity (Core API #10)
        
        TICKET-MEM-001: Semantic search through vectorized action history.
        
        Args:
            query: Natural language query (e.g., "the PDF we saw earlier", "le fichier d'hier")
            limit: Maximum number of results to return
            
        Returns:
            List of matching actions with similarity scores
        """
        if not self._semantic_memory_enabled:
            logger.warning("Semantic search requested but semantic memory is not enabled")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._embedding_model.encode(query).tolist()
            
            # Query ChromaDB
            results = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            if results and results.get("ids") and results["ids"][0]:
                for i, action_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    
                    formatted_results.append({
                        "id": action_id,
                        "type": metadata.get("action_type"),
                        "data": json.loads(metadata.get("action_data", "{}")),
                        "description": metadata.get("description"),
                        "timestamp": metadata.get("timestamp"),
                        "similarity": 1.0 - distance,  # Convert distance to similarity
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def cleanup(self, days_old: int = 7, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Clean up old data (Core API #11)
        
        Args:
            days_old: Delete data older than this many days
            session_id: Optional session ID (cleans all sessions if None)
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff = datetime.now() - timedelta(days=days_old)
        
        stats = {
            "context_deleted": 0,
            "history_deleted": 0,
            "storage_deleted": 0
        }
        
        try:
            with self._get_connection() as conn:
                # Delete old context
                if session_id:
                    cursor = conn.execute("""
                        DELETE FROM context
                        WHERE session_id = ? AND timestamp < ?
                    """, (session_id, cutoff))
                else:
                    cursor = conn.execute("""
                        DELETE FROM context WHERE timestamp < ?
                    """, (cutoff,))
                stats["context_deleted"] = cursor.rowcount
                
                # Delete old history
                if session_id:
                    cursor = conn.execute("""
                        DELETE FROM history
                        WHERE session_id = ? AND timestamp < ?
                    """, (session_id, cutoff))
                else:
                    cursor = conn.execute("""
                        DELETE FROM history WHERE timestamp < ?
                    """, (cutoff,))
                stats["history_deleted"] = cursor.rowcount
                
                logger.info(f"Cleanup complete: {stats}")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return stats
    
    # ========== Helper Methods ==========
    
    def _create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session"""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO sessions (session_id, metadata)
                VALUES (?, ?)
            """, (session_id, json.dumps({})))
        
        return session_id
    
    def _session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM sessions WHERE session_id = ?
            """, (session_id,))
            return cursor.fetchone()["count"] > 0
    
    def _touch_session(self, session_id: str):
        """Update session last accessed time"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions SET last_accessed = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
    
    def _update_quick_refs(self, action_type: str, action_data: Dict[str, Any]):
        """Update in-memory quick references"""
        if action_type == "command":
            self._quick_refs["last_command"] = action_data.get("command")
        elif action_type == "copy":
            self._quick_refs["last_copied"] = action_data.get("content")
        elif action_type == "click":
            x = action_data.get("x")
            y = action_data.get("y")
            if x is not None and y is not None:
                self._quick_refs["last_clicked"] = (x, y)
        elif action_type == "open_app":
            self._quick_refs["last_app"] = action_data.get("app_name")
        elif action_type == "open_file":
            self._quick_refs["last_file"] = action_data.get("file_path")
        elif action_type == "open_url":
            self._quick_refs["last_url"] = action_data.get("url")
    
    def _vectorize_action(self, action_id: int, action_type: str, action_data: Dict[str, Any]):
        """
        Vectorize action and store in semantic memory (TICKET-MEM-001)
        
        Args:
            action_id: Database ID of the action
            action_type: Type of action
            action_data: Action details
        """
        if not self._semantic_memory_enabled:
            return
        
        try:
            # Create a human-readable description of the action
            description = self._create_action_description(action_type, action_data)
            
            # Generate embedding
            embedding = self._embedding_model.encode(description).tolist()
            
            # Store in ChromaDB with metadata
            self._chroma_collection.add(
                ids=[str(action_id)],
                embeddings=[embedding],
                metadatas=[{
                    "action_type": action_type,
                    "action_data": json.dumps(action_data),
                    "description": description,
                    "timestamp": datetime.now().isoformat()
                }]
            )
        except Exception as e:
            logger.error(f"Failed to vectorize action: {e}")
    
    def _create_action_description(self, action_type: str, action_data: Dict[str, Any]) -> str:
        """
        Create a human-readable description for semantic search (TICKET-MEM-001)
        
        Args:
            action_type: Type of action
            action_data: Action details
            
        Returns:
            Human-readable description
        """
        # Build a natural language description based on action type
        if action_type == "open_file":
            file_path = action_data.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown file"
            return f"Opened {file_name} file at {file_path}"
        
        elif action_type == "open_app":
            app_name = action_data.get("app_name", "unknown")
            return f"Opened {app_name} application"
        
        elif action_type == "open_url":
            url = action_data.get("url", "unknown URL")
            return f"Opened website {url}"
        
        elif action_type == "copy":
            content = action_data.get("content", "")
            content_preview = content[:ACTION_DESCRIPTION_MAX_LENGTH] if len(content) > ACTION_DESCRIPTION_MAX_LENGTH else content
            return f"Copied text: {content_preview}"
        
        elif action_type == "click":
            x = action_data.get("x")
            y = action_data.get("y")
            target = action_data.get("target", "")
            if target:
                return f"Clicked on {target} at position ({x}, {y})"
            return f"Clicked at position ({x}, {y})"
        
        elif action_type == "command":
            command = action_data.get("command", "")
            return f"Executed command: {command}"
        
        else:
            # Generic description for unknown action types
            data_str = json.dumps(action_data)
            data_preview = data_str[:ACTION_DESCRIPTION_MAX_LENGTH] if len(data_str) > ACTION_DESCRIPTION_MAX_LENGTH else data_str
            return f"Performed {action_type} action with data: {data_preview}"
    
    # ========== Additional Convenience Methods ==========
    
    def add_conversation_turn(self, conversation_id: str, user_input: str,
                             system_response: Optional[str] = None) -> bool:
        """Add a turn to a conversation"""
        try:
            with self._get_connection() as conn:
                # Get turn number
                cursor = conn.execute("""
                    SELECT COALESCE(MAX(turn_number), 0) + 1 as next_turn
                    FROM conversation_turns
                    WHERE conversation_id = ?
                """, (conversation_id,))
                turn_number = cursor.fetchone()["next_turn"]
                
                # Insert turn
                conn.execute("""
                    INSERT INTO conversation_turns 
                    (conversation_id, turn_number, user_input, system_response)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, turn_number, user_input, system_response))
            
            return True
        except Exception as e:
            logger.error(f"Failed to add conversation turn: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all turns in a conversation"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT turn_number, user_input, system_response, timestamp
                    FROM conversation_turns
                    WHERE conversation_id = ?
                    ORDER BY turn_number
                """, (conversation_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory engine statistics"""
        try:
            with self._get_connection() as conn:
                stats = {}
                
                # Session count
                cursor = conn.execute("SELECT COUNT(*) as count FROM sessions")
                stats["total_sessions"] = cursor.fetchone()["count"]
                
                # Context count
                cursor = conn.execute("SELECT COUNT(*) as count FROM context WHERE session_id = ?", 
                                     (self.session_id,))
                stats["context_items"] = cursor.fetchone()["count"]
                
                # History count
                cursor = conn.execute("SELECT COUNT(*) as count FROM history WHERE session_id = ?",
                                     (self.session_id,))
                stats["history_items"] = cursor.fetchone()["count"]
                
                # Storage count
                cursor = conn.execute("SELECT COUNT(*) as count FROM storage WHERE session_id = ?",
                                     (self.session_id,))
                stats["stored_items"] = cursor.fetchone()["count"]
                
                # Active conversations
                cursor = conn.execute("""
                    SELECT COUNT(*) as count FROM conversations 
                    WHERE session_id = ? AND state = 'active'
                """, (self.session_id,))
                stats["active_conversations"] = cursor.fetchone()["count"]
                
                # Database size
                if self.db_path.exists():
                    stats["db_size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session"""
        if not self._session_exists(session_id):
            return False
        
        self.session_id = session_id
        self._touch_session(session_id)
        logger.info(f"Switched to session {session_id}")
        return True
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session and switch to it"""
        new_session = self._create_session(session_id)
        self.session_id = new_session
        logger.info(f"Created and switched to session {new_session}")
        return new_session
    
    def log_structured(
        self,
        level: str,
        logger: str,
        message: str,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        module: Optional[str] = None,
        function: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Log structured data to the database.
        
        This is a compatibility method for pipeline logging.
        Stores the log entry as context data.
        """
        try:
            log_data = {
                "level": level,
                "logger": logger,
                "message": message,
                "request_id": request_id,
                "module": module,
                "function": function,
            }
            if extra_data:
                log_data["extra_data"] = extra_data
            
            self.add_context(
                context_type="log",
                data=log_data,
                session_id=session_id or self.session_id,
            )
        except Exception as e:
            # Don't let logging errors break the pipeline
            _py_logger_cache.warning(f"Failed to log structured data: {e}")
    
    def store_command(
        self,
        session_id: str,
        raw_command: str,
        intent: Any,
        request_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Store a command in the history.
        
        Compatibility method for pipeline.
        """
        try:
            command_data = {
                "raw_command": raw_command,
                "intent": str(intent) if hasattr(intent, 'action') else str(intent),
                "request_id": request_id,
                "parameters": parameters or {},
            }
            self.record_action(
                action_type="command",
                action_data=command_data,
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Failed to store command: {e}")
    
    def store_context(
        self,
        session_id: str,
        context_type: str,
        data: Dict[str, Any],
    ):
        """
        Store context data.
        
        Compatibility method for pipeline.
        """
        try:
            self.add_context(
                context_type=context_type,
                data=data,
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Failed to store context: {e}")
    
    def log_execution(
        self,
        session_id: str,
        request_id: str,
        success: bool,
        duration_ms: int,
        error: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Log execution result.
        
        Compatibility method for pipeline.
        """
        try:
            execution_data = {
                "request_id": request_id,
                "success": success,
                "duration_ms": duration_ms,
                "error": error,
            }
            if extra_data:
                execution_data.update(extra_data)
            
            self.record_action(
                action_type="execution",
                action_data=execution_data,
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Failed to log execution: {e}")
    
    def get_command_history(
        self,
        session_id: str,
        max_tokens: int = 4000,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get command history for a session.
        
        Compatibility method for pipeline.
        TICKET-LLM-001: Now uses token-aware retrieval.
        """
        try:
            # Backward-compat: older callers used `limit` (#commands). We now use
            # token-aware retrieval, but we can approximate by scaling max_tokens.
            if limit is not None:
                # Heuristic: ~90 tokens per command entry (raw text + metadata)
                max_tokens = min(max_tokens, max(400, int(limit) * 90))

            # Get action history filtered by command type
            actions = self.get_history(
                max_tokens=max_tokens,
                action_type="command",
                session_id=session_id,
            )
            
            # Convert to command format expected by pipeline
            commands = []
            for action in actions:
                action_data = action.get("action_data", {})
                commands.append({
                    "raw_command": action_data.get("raw_command", ""),
                    "intent": action_data.get("intent", ""),
                    "request_id": action_data.get("request_id", ""),
                    "parameters": action_data.get("parameters", {}),
                    "timestamp": action.get("timestamp"),
                })
            
            return commands
        except Exception as e:
            logger.warning(f"Failed to get command history: {e}")
            return []
    
    def list_all_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all sessions.
        
        Compatibility method for pipeline.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, created_at, last_accessed
                    FROM sessions
                    ORDER BY last_accessed DESC
                    LIMIT ?
                """, (limit,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        "session_id": row[0],
                        "created_at": row[1],
                        "last_accessed": row[2],
                    })
                
                return sessions
        except Exception as e:
            logger.warning(f"Failed to list sessions: {e}")
            return []
    
    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """
        Get session details.
        
        Compatibility method for pipeline.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get session info
                cursor.execute("""
                    SELECT created_at, last_accessed
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return {}
                
                # Get action count
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM action_history
                    WHERE session_id = ?
                """, (session_id,))
                
                action_count = cursor.fetchone()[0]
                
                return {
                    "session_id": session_id,
                    "created_at": row[0],
                    "last_accessed": row[1],
                    "action_count": action_count,
                }
        except Exception as e:
            logger.warning(f"Failed to get session details: {e}")
            return {}
