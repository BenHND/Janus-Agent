#!/usr/bin/env python3
"""
Migration Script: Old Memory Systems → MemoryEngine

TICKET-AUDIT-005: Migrate data from 6 memory systems to unified MemoryEngine

This script:
1. Reads data from old memory systems (if they exist)
2. Migrates data to MemoryEngine
3. Validates no data loss
4. Creates backup of old databases

Usage:
    python migrate_to_memory_engine.py [--old-db PATH] [--new-db PATH] [--validate]
"""

import argparse
import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MemoryMigrator:
    """Migrates data from old memory systems to MemoryEngine"""
    
    def __init__(self, old_db_path: str, new_db_path: str):
        self.old_db_path = Path(old_db_path)
        self.new_db_path = Path(new_db_path)
        
        self.stats = {
            "sessions_migrated": 0,
            "commands_migrated": 0,
            "context_migrated": 0,
            "conversations_migrated": 0,
            "errors": []
        }
    
    def backup_old_database(self) -> Optional[str]:
        """Create backup of old database"""
        if not self.old_db_path.exists():
            logger.warning(f"Old database not found: {self.old_db_path}")
            return None
        
        backup_path = self.old_db_path.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        try:
            shutil.copy2(self.old_db_path, backup_path)
            logger.info(f"✓ Created backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"✗ Failed to create backup: {e}")
            return None
    
    def migrate_sessions(self, old_conn: sqlite3.Connection, new_conn: sqlite3.Connection):
        """Migrate sessions from MemoryService"""
        try:
            # Check if old sessions table exists
            cursor = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            if not cursor.fetchone():
                logger.info("No sessions table found in old database")
                return
            
            # Get sessions from old DB
            cursor = old_conn.execute("SELECT session_id, created_at, last_accessed, data FROM sessions")
            sessions = cursor.fetchall()
            
            for session in sessions:
                session_id, created_at, last_accessed, data = session
                
                try:
                    # Insert into new MemoryEngine
                    new_conn.execute("""
                        INSERT OR IGNORE INTO sessions (session_id, created_at, last_accessed, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, created_at, last_accessed, data))
                    
                    self.stats["sessions_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Session {session_id}: {e}")
            
            logger.info(f"✓ Migrated {self.stats['sessions_migrated']} sessions")
            
        except Exception as e:
            logger.error(f"✗ Failed to migrate sessions: {e}")
    
    def migrate_commands(self, old_conn: sqlite3.Connection, new_conn: sqlite3.Connection):
        """Migrate command history from MemoryService"""
        try:
            # Check if old command_history table exists
            cursor = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='command_history'"
            )
            if not cursor.fetchone():
                logger.info("No command_history table found in old database")
                return
            
            # Get commands from old DB
            cursor = old_conn.execute("""
                SELECT session_id, raw_command, intent, parameters, timestamp
                FROM command_history
                ORDER BY timestamp
            """)
            commands = cursor.fetchall()
            
            for cmd in commands:
                session_id, raw_command, intent, parameters, timestamp = cmd
                
                try:
                    # Parse parameters if JSON string
                    params_dict = {}
                    if parameters:
                        try:
                            params_dict = json.loads(parameters)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse parameters JSON: {e}")
                            params_dict = {}
                    
                    # Insert as action in MemoryEngine
                    action_data = {
                        "command": raw_command,
                        "intent": intent,
                        "parameters": params_dict
                    }
                    
                    new_conn.execute("""
                        INSERT INTO history (session_id, action_type, action_data, timestamp)
                        VALUES (?, 'command', ?, ?)
                    """, (session_id, json.dumps(action_data), timestamp))
                    
                    self.stats["commands_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Command '{raw_command}': {e}")
            
            logger.info(f"✓ Migrated {self.stats['commands_migrated']} commands")
            
        except Exception as e:
            logger.error(f"✗ Failed to migrate commands: {e}")
    
    def migrate_context(self, old_conn: sqlite3.Connection, new_conn: sqlite3.Connection):
        """Migrate context from MemoryService/ContextMemory"""
        try:
            # Check if old context table exists
            cursor = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='context'"
            )
            if not cursor.fetchone():
                logger.info("No context table found in old database")
                return
            
            # Get context from old DB
            cursor = old_conn.execute("""
                SELECT session_id, context_type, data, timestamp
                FROM context
                ORDER BY timestamp
            """)
            contexts = cursor.fetchall()
            
            for ctx in contexts:
                session_id, context_type, data, timestamp = ctx
                
                try:
                    # Insert into MemoryEngine context
                    new_conn.execute("""
                        INSERT INTO context (session_id, context_type, data, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, context_type, data, timestamp))
                    
                    self.stats["context_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Context {context_type}: {e}")
            
            logger.info(f"✓ Migrated {self.stats['context_migrated']} context items")
            
        except Exception as e:
            logger.error(f"✗ Failed to migrate context: {e}")
    
    def migrate_conversations(self, old_conn: sqlite3.Connection, new_conn: sqlite3.Connection):
        """Migrate conversations from ConversationManager"""
        try:
            # Check if old conversations table exists
            cursor = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
            )
            if not cursor.fetchone():
                logger.info("No conversations table found in old database")
                return
            
            # Get conversations from old DB
            cursor = old_conn.execute("""
                SELECT conversation_id, session_id, state, created_at, updated_at
                FROM conversations
            """)
            conversations = cursor.fetchall()
            
            for conv in conversations:
                conv_id, session_id, state, created_at, updated_at = conv
                
                try:
                    # Map old state to new
                    new_state = "active" if state in ["active", "needs_clarification"] else "completed"
                    ended_at = updated_at if state == "completed" else None
                    
                    # Insert conversation
                    new_conn.execute("""
                        INSERT OR IGNORE INTO conversations 
                        (conversation_id, session_id, state, started_at, ended_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (conv_id, session_id, new_state, created_at, ended_at))
                    
                    # Migrate turns
                    turn_cursor = old_conn.execute("""
                        SELECT turn_number, command, timestamp
                        FROM conversation_turns
                        WHERE conversation_id = ?
                        ORDER BY turn_number
                    """, (conv_id,))
                    
                    for turn in turn_cursor.fetchall():
                        turn_number, command, timestamp = turn
                        
                        new_conn.execute("""
                            INSERT INTO conversation_turns
                            (conversation_id, turn_number, user_input, timestamp)
                            VALUES (?, ?, ?, ?)
                        """, (conv_id, turn_number, command, timestamp))
                    
                    self.stats["conversations_migrated"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Conversation {conv_id}: {e}")
            
            logger.info(f"✓ Migrated {self.stats['conversations_migrated']} conversations")
            
        except Exception as e:
            logger.error(f"✗ Failed to migrate conversations: {e}")
    
    def migrate(self) -> bool:
        """Run complete migration"""
        logger.info("Starting migration to MemoryEngine...")
        
        # Backup old database
        backup = self.backup_old_database()
        if not backup and self.old_db_path.exists():
            logger.error("Failed to create backup. Aborting migration.")
            return False
        
        # Connect to databases
        old_conn = None
        new_conn = None
        try:
            old_conn = sqlite3.connect(self.old_db_path) if self.old_db_path.exists() else None
            
            # Create new MemoryEngine database
            from janus.runtime.core.memory_engine import MemoryEngine
            new_engine = MemoryEngine(str(self.new_db_path))
            new_conn = sqlite3.connect(self.new_db_path)
            
            if old_conn:
                # Migrate data
                self.migrate_sessions(old_conn, new_conn)
                self.migrate_commands(old_conn, new_conn)
                self.migrate_context(old_conn, new_conn)
                self.migrate_conversations(old_conn, new_conn)
                
                new_conn.commit()
            else:
                logger.info("No old database found. Creating new MemoryEngine database.")
            
            # Print summary
            logger.info("\n" + "="*50)
            logger.info("Migration Complete!")
            logger.info("="*50)
            logger.info(f"Sessions migrated:      {self.stats['sessions_migrated']}")
            logger.info(f"Commands migrated:      {self.stats['commands_migrated']}")
            logger.info(f"Context items migrated: {self.stats['context_migrated']}")
            logger.info(f"Conversations migrated: {self.stats['conversations_migrated']}")
            
            if self.stats["errors"]:
                logger.warning(f"\nErrors encountered: {len(self.stats['errors'])}")
                for error in self.stats["errors"][:10]:  # Show first 10
                    logger.warning(f"  - {error}")
                if len(self.stats["errors"]) > 10:
                    logger.warning(f"  ... and {len(self.stats['errors']) - 10} more")
            
            logger.info(f"\nNew database: {self.new_db_path}")
            if backup:
                logger.info(f"Backup saved: {backup}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Migration failed: {e}")
            return False
        finally:
            # Ensure connections are closed
            if old_conn:
                old_conn.close()
            if new_conn:
                new_conn.close()
    
    def validate(self) -> bool:
        """Validate migration was successful"""
        logger.info("\nValidating migration...")
        
        old_conn = None
        new_conn = None
        try:
            old_conn = sqlite3.connect(self.old_db_path)
            new_conn = sqlite3.connect(self.new_db_path)
            
            # Count records in old DB
            old_sessions = old_conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            
            old_commands = 0
            try:
                old_commands = old_conn.execute("SELECT COUNT(*) FROM command_history").fetchone()[0]
            except sqlite3.OperationalError:
                # Table doesn't exist
                pass
            
            # Count records in new DB
            new_sessions = new_conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            new_commands = new_conn.execute(
                "SELECT COUNT(*) FROM history WHERE action_type = 'command'"
            ).fetchone()[0]
            
            # Validate
            valid = True
            if new_sessions < old_sessions:
                logger.warning(f"⚠ Session count mismatch: {old_sessions} → {new_sessions}")
                valid = False
            
            if new_commands < old_commands:
                logger.warning(f"⚠ Command count mismatch: {old_commands} → {new_commands}")
                valid = False
            
            if valid:
                logger.info("✓ Validation passed!")
            else:
                logger.warning("⚠ Validation found discrepancies")
            
            return valid
            
        except Exception as e:
            logger.error(f"✗ Validation failed: {e}")
            return False
        finally:
            # Ensure connections are closed
            if old_conn:
                old_conn.close()
            if new_conn:
                new_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate from old memory systems to MemoryEngine (TICKET-AUDIT-005)"
    )
    parser.add_argument(
        "--old-db",
        default="janus.db",
        help="Path to old database (default: janus.db)"
    )
    parser.add_argument(
        "--new-db",
        default="janus_memory.db",
        help="Path to new MemoryEngine database (default: janus_memory.db)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate migration after completion"
    )
    
    args = parser.parse_args()
    
    migrator = MemoryMigrator(args.old_db, args.new_db)
    
    # Run migration
    success = migrator.migrate()
    
    # Validate if requested
    if success and args.validate:
        migrator.validate()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
