"""
Database Migration System for Janus Memory Engine

TICKET-DB-001: Lightweight SQLite migration system using PRAGMA user_version.

This module provides a simple yet robust migration system that allows
schema changes without breaking existing user databases. It uses SQLite's
built-in user_version pragma for tracking the current schema version.

Architecture:
- Each migration is a function that takes a database connection
- Migrations are registered with a version number
- On startup, the system checks the current version and applies pending migrations
- Migrations are applied in order and are idempotent

Usage:
    from janus.runtime.core.db_migrations import MigrationManager
    
    manager = MigrationManager(db_path="janus_memory.db")
    manager.apply_migrations()
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when a migration fails"""
    pass


class MigrationManager:
    """
    Manages database schema migrations for Janus Memory Engine.
    
    Uses SQLite's PRAGMA user_version to track the current schema version.
    Migrations are applied sequentially and atomically.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        if hasattr(db_path, 'path'):
            db_path = db_path.path
        self.db_path = Path(db_path)
        self._migrations: Dict[int, Callable] = {}
        
        # Register all migrations
        self._register_migrations()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
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
    
    def get_current_version(self) -> int:
        """
        Get the current database schema version.
        
        Returns:
            Current version number (0 if database is new/unversioned)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("PRAGMA user_version")
                version = cursor.fetchone()[0]
                return version
        except Exception as e:
            logger.error(f"Failed to get database version: {e}")
            return 0
    
    def set_version(self, version: int):
        """
        Set the database schema version.
        
        Args:
            version: Version number to set
        """
        with self._get_connection() as conn:
            conn.execute(f"PRAGMA user_version = {version}")
    
    def get_latest_version(self) -> int:
        """
        Get the latest available migration version.
        
        Returns:
            Latest version number
        """
        if not self._migrations:
            return 0
        return max(self._migrations.keys())
    
    def _register_migrations(self):
        """
        Register all migration functions.
        
        Each migration is a function that takes a connection and applies
        schema changes. Migrations must be idempotent where possible.
        """
        # Migration 1: Baseline schema (initial version)
        self._migrations[1] = self._migration_001_baseline
        
        # Migration 2: Add risk_level column to history table (example for TICKET-DB-001)
        self._migrations[2] = self._migration_002_add_risk_level
        
        # Migration 3: Add scheduled_tasks table (TICKET-FEAT-002)
        self._migrations[3] = self._migration_003_add_scheduled_tasks
    
    def _migration_001_baseline(self, conn: sqlite3.Connection):
        """
        Migration 1: Create baseline schema.
        
        This migration creates the initial database schema. It's designed to be
        idempotent and safe to run on both new and existing databases.
        """
        logger.info("Applying migration 001: Baseline schema")
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Storage table (key-value store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, key)
            )
        """)
        
        # Context table (temporal context with decay)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 1.0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # History table (actions and commands)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT NOT NULL,
                result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                state TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                end_reason TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Conversation turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                user_input TEXT NOT NULL,
                system_response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Create indexes for performance (only if columns exist)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_session ON storage(session_id)")
        
        # Check if timestamp column exists in context table before creating index
        cursor.execute("PRAGMA table_info(context)")
        context_cols = [row[1] for row in cursor.fetchall()]
        if "timestamp" in context_cols:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_session_time ON context(session_id, timestamp DESC)")
        
        # Check if timestamp column exists in history table before creating index
        cursor.execute("PRAGMA table_info(history)")
        history_cols = [row[1] for row in cursor.fetchall()]
        if "timestamp" in history_cols:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_session_time ON history(session_id, timestamp DESC)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_turns_conversation ON conversation_turns(conversation_id, turn_number)")
        
        logger.info("✓ Migration 001 completed: Baseline schema created")
    
    def _migration_002_add_risk_level(self, conn: sqlite3.Connection):
        """
        Migration 2: Add risk_level column to history table.
        
        This is an example migration that demonstrates how to add a new column
        to an existing table. This addresses the scenario mentioned in TICKET-DB-001
        where adding a column would break existing installations.
        """
        logger.info("Applying migration 002: Add risk_level to history")
        cursor = conn.cursor()
        
        # Check if column already exists (idempotency check)
        cursor.execute("PRAGMA table_info(history)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "risk_level" not in columns:
            # Add the new column with a default value
            cursor.execute("""
                ALTER TABLE history 
                ADD COLUMN risk_level TEXT DEFAULT 'low'
            """)
            logger.info("✓ Added risk_level column to history table")
        else:
            logger.info("✓ risk_level column already exists, skipping")
        
        logger.info("✓ Migration 002 completed")
    
    def _migration_003_add_scheduled_tasks(self, conn: sqlite3.Connection):
        """
        Migration 3: Add scheduled_tasks table for task scheduler.
        TICKET-FEAT-002: Scheduler & Actions Différées (Cron)
        
        This migration creates the scheduled_tasks table to support
        delayed and recurring task execution.
        """
        logger.info("Applying migration 003: Add scheduled_tasks table")
        cursor = conn.cursor()
        
        # Create scheduled_tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                command TEXT NOT NULL,
                action TEXT NOT NULL,
                schedule_time TEXT,
                schedule_expression TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT,
                run_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status 
            ON scheduled_tasks(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run 
            ON scheduled_tasks(next_run)
        """)
        
        logger.info("✓ Migration 003 completed: scheduled_tasks table created")
    
    def apply_migrations(self, target_version: Optional[int] = None) -> bool:
        """
        Apply all pending migrations up to target_version.
        
        Args:
            target_version: Target version to migrate to (latest if None)
            
        Returns:
            True if migrations were successful, False otherwise
        """
        current_version = self.get_current_version()
        target = target_version if target_version is not None else self.get_latest_version()
        
        if current_version == target:
            logger.info(f"Database is already at version {current_version}, no migrations needed")
            return True
        
        if current_version > target:
            logger.warning(
                f"Database version {current_version} is newer than target {target}. "
                "Downgrade migrations are not supported."
            )
            return False
        
        logger.info(f"Migrating database from version {current_version} to {target}")
        
        try:
            # Apply migrations in order
            for version in range(current_version + 1, target + 1):
                if version not in self._migrations:
                    raise MigrationError(f"Migration {version} not found")
                
                logger.info(f"Applying migration {version}...")
                
                # Apply migration in a transaction
                with self._get_connection() as conn:
                    self._migrations[version](conn)
                    # Update version after successful migration
                    conn.execute(f"PRAGMA user_version = {version}")
                
                logger.info(f"✓ Migration {version} applied successfully")
            
            logger.info(f"✓ All migrations completed. Database is now at version {target}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            logger.error("Database may be in an inconsistent state. Manual intervention may be required.")
            raise MigrationError(f"Migration failed: {e}") from e
    
    def verify_schema(self) -> bool:
        """
        Verify that the database schema matches the expected version.
        
        Returns:
            True if schema is valid, False otherwise
        """
        try:
            current_version = self.get_current_version()
            latest_version = self.get_latest_version()
            
            if current_version < latest_version:
                logger.warning(
                    f"Database schema is outdated (v{current_version}), "
                    f"latest is v{latest_version}"
                )
                return False
            
            if current_version > latest_version:
                logger.warning(
                    f"Database schema is from a newer version (v{current_version}), "
                    f"latest known is v{latest_version}"
                )
                return False
            
            logger.info(f"✓ Database schema verified (v{current_version})")
            return True
            
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False
    
    def get_migration_info(self) -> Dict[str, any]:
        """
        Get information about the migration system state.
        
        Returns:
            Dictionary with migration information
        """
        current = self.get_current_version()
        latest = self.get_latest_version()
        
        return {
            "current_version": current,
            "latest_version": latest,
            "migrations_needed": latest - current if current < latest else 0,
            "up_to_date": current == latest,
            "pending_migrations": list(range(current + 1, latest + 1)) if current < latest else []
        }
