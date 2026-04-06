"""
Compensation Manager for P2 Rollback Feature

Handles undo/rollback of reversible actions through compensation actions.
Each action type can register a compensation handler that knows how to undo it.
"""

import logging
import os
import shutil
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CompensationRecord:
    """Record of a reversible action that can be compensated/undone"""
    
    action_id: str  # Unique ID for this action
    action_type: str  # e.g., "files.create_file"
    timestamp: datetime
    compensation_data: Dict[str, Any]  # Data needed to undo
    status: str  # pending, compensated, failed
    error: Optional[str] = None


class CompensationManager:
    """
    Manages compensation (undo/rollback) for reversible actions.
    
    P2 Feature: Provides rollback capability for destructive actions.
    """
    
    def __init__(self):
        """Initialize compensation manager"""
        self._compensation_handlers: Dict[str, Callable] = {}
        self._compensation_history: List[CompensationRecord] = []
        self.logger = logging.getLogger(__name__)
    
    def register_handler(self, action_type: str, handler: Callable[[Dict[str, Any]], bool]):
        """
        Register a compensation handler for an action type.
        
        Args:
            action_type: Action type (e.g., "files.create_file")
            handler: Function that takes compensation_data and returns success bool
        """
        self._compensation_handlers[action_type] = handler
        self.logger.debug(f"Registered compensation handler for {action_type}")
    
    def record_action(
        self,
        action_id: str,
        action_type: str,
        compensation_data: Dict[str, Any]
    ) -> CompensationRecord:
        """
        Record a reversible action for potential compensation.
        
        Args:
            action_id: Unique identifier for this action
            action_type: Type of action (e.g., "files.delete_file")
            compensation_data: Data needed to undo the action
        
        Returns:
            CompensationRecord for tracking
        """
        record = CompensationRecord(
            action_id=action_id,
            action_type=action_type,
            timestamp=datetime.now(),
            compensation_data=compensation_data,
            status="pending"
        )
        self._compensation_history.append(record)
        self.logger.info(f"Recorded reversible action: {action_type} (id={action_id})")
        return record
    
    def compensate(self, action_id: str) -> bool:
        """
        Compensate (undo) a previously executed action.
        
        Args:
            action_id: ID of the action to undo
        
        Returns:
            True if compensation succeeded, False otherwise
        """
        # Find the action record
        record = None
        for r in self._compensation_history:
            if r.action_id == action_id:
                record = r
                break
        
        if not record:
            self.logger.error(f"No compensation record found for action {action_id}")
            return False
        
        if record.status == "compensated":
            self.logger.warning(f"Action {action_id} already compensated")
            return True
        
        # Check if we have a handler for this action type
        handler = self._compensation_handlers.get(record.action_type)
        if not handler:
            self.logger.error(f"No compensation handler registered for {record.action_type}")
            record.status = "failed"
            record.error = "No compensation handler available"
            return False
        
        # Execute compensation
        try:
            self.logger.info(f"Compensating action {action_id} ({record.action_type})...")
            success = handler(record.compensation_data)
            
            if success:
                record.status = "compensated"
                self.logger.info(f"✓ Successfully compensated action {action_id}")
                return True
            else:
                record.status = "failed"
                record.error = "Handler returned False"
                self.logger.error(f"✗ Compensation failed for action {action_id}")
                return False
        
        except Exception as e:
            record.status = "failed"
            record.error = str(e)
            self.logger.exception(f"✗ Exception during compensation of {action_id}: {e}")
            return False
    
    def get_reversible_actions(self, limit: int = 10) -> List[CompensationRecord]:
        """
        Get recent reversible actions that can be compensated.
        
        Args:
            limit: Maximum number of actions to return
        
        Returns:
            List of compensation records (most recent first)
        """
        pending = [r for r in self._compensation_history if r.status == "pending"]
        return sorted(pending, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_compensation_stats(self) -> Dict[str, int]:
        """
        Get statistics about compensation history.
        
        Returns:
            Dictionary with counts by status
        """
        stats = {"pending": 0, "compensated": 0, "failed": 0}
        for record in self._compensation_history:
            stats[record.status] = stats.get(record.status, 0) + 1
        return stats


# Global compensation manager instance
_global_compensation_manager: Optional[CompensationManager] = None


def get_global_compensation_manager() -> CompensationManager:
    """Get or create global compensation manager instance"""
    global _global_compensation_manager
    if _global_compensation_manager is None:
        _global_compensation_manager = CompensationManager()
    return _global_compensation_manager


# Built-in compensation handlers for common actions

def compensate_file_creation(data: Dict[str, Any]) -> bool:
    """
    Compensate file creation by deleting the file.
    
    Args:
        data: {"path": "/path/to/file"}
    
    Returns:
        True if file was deleted successfully
    """
    path = data.get("path")
    if not path:
        logger.error("No path in compensation data")
        return False
    
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted file: {path}")
            return True
        else:
            logger.warning(f"File already deleted: {path}")
            return True  # Already gone, consider it success
    except Exception as e:
        logger.error(f"Failed to delete file {path}: {e}")
        return False


def compensate_file_deletion(data: Dict[str, Any]) -> bool:
    """
    Compensate file deletion by restoring from backup.
    
    Args:
        data: {"path": "/path/to/file", "backup_content": "..."}
    
    Returns:
        True if file was restored
    """
    path = data.get("path")
    backup_content = data.get("backup_content")
    
    if not path or backup_content is None:
        logger.error("Missing path or backup_content in compensation data")
        return False
    
    try:
        with open(path, 'w') as f:
            f.write(backup_content)
        logger.info(f"Restored deleted file: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore file {path}: {e}")
        return False


def compensate_file_move(data: Dict[str, Any]) -> bool:
    """
    Compensate file move by moving it back.
    
    Args:
        data: {"from": "/old/path", "to": "/new/path"}
    
    Returns:
        True if file was moved back
    """
    from_path = data.get("from")
    to_path = data.get("to")
    
    if not from_path or not to_path:
        logger.error("Missing from/to paths in compensation data")
        return False
    
    try:
        if os.path.exists(to_path):
            shutil.move(to_path, from_path)
            logger.info(f"Moved file back: {to_path} → {from_path}")
            return True
        else:
            logger.warning(f"File not found at destination: {to_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to move file back: {e}")
        return False


# Register built-in handlers
def register_builtin_handlers():
    """Register built-in compensation handlers"""
    manager = get_global_compensation_manager()
    manager.register_handler("files.create_file", compensate_file_creation)
    manager.register_handler("files.delete_file", compensate_file_deletion)
    manager.register_handler("files.move_file", compensate_file_move)
    logger.info("Registered built-in compensation handlers")
