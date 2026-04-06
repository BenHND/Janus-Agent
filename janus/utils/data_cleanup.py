"""
Data Cleanup Manager - TICKET-DATA-001

Centralized data retention and cleanup management.
Prevents disk saturation by automatically purging old data.

This module provides automated cleanup for all persistent data stores:
- SQLite databases (MemoryEngine, ActionHistory, WorkflowPersistence, SafeQueue, UnifiedStore)
- ChromaDB vector store (semantic memory)
- Audio logs (WAV files and transcripts)
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DataCleanupManager:
    """
    Centralized data cleanup manager.
    
    Handles retention policies for all persistent data:
    - SQLite databases (MemoryEngine, ActionHistory, etc.)
    - ChromaDB vector store
    - Audio logs
    - Temporary files
    """
    
    def __init__(self, settings):
        """
        Initialize cleanup manager.
        
        Args:
            settings: Application settings with data_retention configuration
        """
        self.settings = settings
        self.retention = settings.data_retention
        
    def run_full_cleanup(self) -> Dict[str, Dict[str, int]]:
        """
        Run cleanup on all data stores.
        
        Returns:
            Dict with cleanup statistics per component
        """
        stats = {}
        
        # 1. MemoryEngine cleanup
        stats["memory"] = self._cleanup_memory_engine()
        
        # 2. ChromaDB cleanup
        stats["vectors"] = self._cleanup_chromadb()
        
        # 3. Action history cleanup
        stats["action_history"] = self._cleanup_action_history()
        
        # 4. Workflow states cleanup
        stats["workflows"] = self._cleanup_workflows()
        
        # 5. Audio logs cleanup
        stats["audio_logs"] = self._cleanup_audio_logs()
        
        # 6. Safe queue cleanup
        stats["safe_queue"] = self._cleanup_safe_queue()
        
        # 7. Unified store cleanup
        stats["unified_store"] = self._cleanup_unified_store()
        
        # Log summary
        total_deleted = 0
        for component in stats.values():
            if isinstance(component, dict):
                # Sum only integer values, skip error messages
                for value in component.values():
                    if isinstance(value, int):
                        total_deleted += value
        
        logger.info(f"Data cleanup complete. Total items deleted: {total_deleted}")
        
        return stats
    
    def _cleanup_memory_engine(self) -> Dict[str, int]:
        """Cleanup MemoryEngine (context + history)"""
        try:
            from janus.runtime.core.memory_engine import MemoryEngine
            engine = MemoryEngine()
            # Cleanup context and history separately if configured differently
            stats = {"context_deleted": 0, "history_deleted": 0}
            
            # Clean up context
            context_result = engine.cleanup(days_old=self.retention.memory_context_days)
            stats["context_deleted"] = context_result.get("context_deleted", 0)
            
            # If history has different retention, cleanup again
            if self.retention.memory_history_days != self.retention.memory_context_days:
                history_result = engine.cleanup(days_old=self.retention.memory_history_days)
                stats["history_deleted"] = history_result.get("history_deleted", 0)
            else:
                stats["history_deleted"] = context_result.get("history_deleted", 0)
            
            return stats
        except Exception as e:
            logger.error(f"MemoryEngine cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_chromadb(self) -> Dict[str, int]:
        """
        Cleanup ChromaDB vectors older than retention period.
        
        ChromaDB doesn't have built-in TTL, so we:
        1. Query all documents with timestamp < cutoff
        2. Delete them by ID
        """
        try:
            import chromadb
            
            chroma_path = Path("janus_memory_chroma")
            if not chroma_path.exists():
                return {"skipped": 1, "reason": "directory_not_found"}
            
            client = chromadb.PersistentClient(path=str(chroma_path))
            collection = client.get_or_create_collection("action_memory")
            
            cutoff = datetime.now() - timedelta(days=self.retention.semantic_vectors_days)
            # Use Unix timestamp for more reliable comparison
            cutoff_timestamp = cutoff.timestamp()
            
            # Get all documents
            results = collection.get(include=["metadatas"])
            
            ids_to_delete = []
            ids = results.get("ids", [])
            metadatas = results.get("metadatas", [])
            
            # Validate that we have matching arrays
            if len(ids) != len(metadatas):
                logger.warning(f"ChromaDB data mismatch: {len(ids)} ids vs {len(metadatas)} metadatas")
                # Use the shorter length to avoid IndexError
                min_len = min(len(ids), len(metadatas))
                ids = ids[:min_len]
                metadatas = metadatas[:min_len]
            
            for i, metadata in enumerate(metadatas):
                # Try to parse timestamp, handle both ISO format and Unix timestamp
                if metadata:
                    timestamp_str = metadata.get("timestamp", "")
                    try:
                        # Try parsing as ISO format first
                        doc_datetime = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        doc_timestamp = doc_datetime.timestamp()
                    except (ValueError, AttributeError):
                        # Try as Unix timestamp
                        try:
                            doc_timestamp = float(timestamp_str)
                        except (ValueError, TypeError):
                            # Skip if we can't parse
                            continue
                    
                    if doc_timestamp < cutoff_timestamp:
                        ids_to_delete.append(ids[i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} old vectors from ChromaDB")
            
            return {"vectors_deleted": len(ids_to_delete)}
            
        except ImportError:
            return {"skipped": 1, "reason": "chromadb_not_installed"}
        except Exception as e:
            logger.error(f"ChromaDB cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_action_history(self) -> Dict[str, int]:
        """Cleanup old action history records"""
        try:
            from janus.persistence.action_history import ActionHistory
            
            history = ActionHistory()
            cutoff = datetime.now() - timedelta(days=self.retention.action_history_days)
            
            with history._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM action_history WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                deleted = cursor.rowcount
            
            return {"records_deleted": deleted}
            
        except Exception as e:
            logger.error(f"ActionHistory cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_workflows(self) -> Dict[str, int]:
        """Cleanup old completed/failed workflow states"""
        try:
            from janus.persistence.workflow_persistence import WorkflowPersistence
            
            wp = WorkflowPersistence()
            cutoff = datetime.now() - timedelta(days=self.retention.workflow_states_days)
            
            with wp._get_connection() as conn:
                # Delete old completed/failed workflows
                cursor = conn.execute("""
                    DELETE FROM workflows 
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    AND created_at < ?
                """, (cutoff.isoformat(),))
                workflows_deleted = cursor.rowcount
                
                # Delete orphaned steps
                cursor = conn.execute("""
                    DELETE FROM workflow_steps 
                    WHERE workflow_id NOT IN (SELECT id FROM workflows)
                """)
                steps_deleted = cursor.rowcount
            
            return {
                "workflows_deleted": workflows_deleted,
                "steps_deleted": steps_deleted
            }
            
        except Exception as e:
            logger.error(f"Workflow cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_audio_logs(self) -> Dict[str, int]:
        """Cleanup old audio logs"""
        try:
            from janus.io.stt.audio_logger import AudioLogger
            
            # Find audio logger instance or create temporary one
            audio_logger = AudioLogger(log_dir="audio_logs")
            deleted = audio_logger.cleanup_old_logs_by_age(
                days=self.retention.audio_logs_days
            )
            
            return {"logs_deleted": deleted}
            
        except Exception as e:
            logger.error(f"AudioLogger cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_safe_queue(self) -> Dict[str, int]:
        """Cleanup old completed/expired queue entries"""
        try:
            from janus.safety.safe_queue import SafeQueue, QueueStatus
            
            queue = SafeQueue()
            cutoff = datetime.now() - timedelta(days=self.retention.safe_queue_days)
            
            with queue._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM action_queue 
                    WHERE status IN (?, ?, ?, ?)
                    AND created_at < ?
                """, (
                    QueueStatus.COMPLETED.value,
                    QueueStatus.FAILED.value,
                    QueueStatus.EXPIRED.value,
                    QueueStatus.CANCELLED.value,
                    cutoff.isoformat()
                ))
                deleted = cursor.rowcount
            
            return {"entries_deleted": deleted}
            
        except Exception as e:
            logger.error(f"SafeQueue cleanup failed: {e}")
            return {"error": str(e)}
    
    def _cleanup_unified_store(self) -> Dict[str, int]:
        """Cleanup old entries in UnifiedStore"""
        try:
            from janus.persistence.unified_store import UnifiedStore
            
            store = UnifiedStore()
            cutoff = datetime.now() - timedelta(days=self.retention.unified_store_days)
            
            stats = {}
            with store._get_connection() as conn:
                # Cleanup context snapshots
                cursor = conn.execute(
                    "DELETE FROM context_snapshots WHERE created_at < ?",
                    (cutoff.isoformat(),)
                )
                stats["snapshots_deleted"] = cursor.rowcount
                
                # Cleanup clipboard history
                cursor = conn.execute(
                    "DELETE FROM clipboard_history WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                stats["clipboard_deleted"] = cursor.rowcount
                
                # Cleanup file operations
                cursor = conn.execute(
                    "DELETE FROM file_operations WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                stats["file_ops_deleted"] = cursor.rowcount
            
            return stats
            
        except Exception as e:
            logger.error(f"UnifiedStore cleanup failed: {e}")
            return {"error": str(e)}
    
    def get_storage_stats(self) -> Dict[str, int]:
        """
        Get current storage usage statistics.
        
        Returns:
            Dict with size in bytes per component
        """
        stats = {}
        
        # SQLite databases
        db_files = [
            "janus_memory.db",
            "janus_data.db",
            "janus_unified.db",
            "janus_learning.db",
            "voice_cache.db",
            "context_memory.db",
        ]
        
        for db_file in db_files:
            path = Path(db_file)
            if path.exists():
                stats[db_file] = path.stat().st_size
        
        # ChromaDB directory
        chroma_path = Path("janus_memory_chroma")
        if chroma_path.exists():
            stats["chromadb"] = sum(
                f.stat().st_size 
                for f in chroma_path.rglob("*") 
                if f.is_file()
            )
        
        # Audio logs
        audio_path = Path("audio_logs")
        if audio_path.exists():
            stats["audio_logs"] = sum(
                f.stat().st_size 
                for f in audio_path.rglob("*") 
                if f.is_file()
            )
        
        # Total
        stats["total"] = sum(stats.values())
        
        return stats
    
    def check_disk_space(self) -> bool:
        """
        Check if total storage exceeds max limit.
        
        Returns:
            True if cleanup is needed
        """
        stats = self.get_storage_stats()
        max_bytes = self.retention.max_total_size_mb * 1024 * 1024
        
        if stats["total"] > max_bytes:
            logger.warning(
                f"Storage limit exceeded: {stats['total'] / 1024 / 1024:.1f}MB "
                f"> {self.retention.max_total_size_mb}MB"
            )
            return True
        
        return False
