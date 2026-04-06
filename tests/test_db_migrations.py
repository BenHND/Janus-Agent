"""
Tests for Database Migration System (TICKET-DB-001)

Tests the database migration system to ensure:
1. Migrations can be applied successfully
2. Migrations are idempotent (can be run multiple times)
3. Data is preserved during migrations
4. Version tracking works correctly
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy pytest decorator for when pytest is not available
    class DummyPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = DummyPytest()

# Import directly to avoid loading all janus dependencies
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core.db_migrations import MigrationManager, MigrationError

# We'll test MemoryEngine separately since it has heavy dependencies


class TestMigrationSystem:
    """Test the database migration system"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_migration_manager_initialization(self, temp_db):
        """Test MigrationManager initialization"""
        manager = MigrationManager(temp_db)
        assert manager.db_path == Path(temp_db)
        assert isinstance(manager._migrations, dict)
        assert len(manager._migrations) > 0
    
    def test_get_current_version_new_database(self, temp_db):
        """Test getting version from a new database"""
        manager = MigrationManager(temp_db)
        version = manager.get_current_version()
        assert version == 0
    
    def test_apply_migrations_from_scratch(self, temp_db):
        """Test applying migrations to a new database"""
        manager = MigrationManager(temp_db)
        
        # Apply all migrations
        success = manager.apply_migrations()
        assert success
        
        # Verify version was updated
        current_version = manager.get_current_version()
        latest_version = manager.get_latest_version()
        assert current_version == latest_version
    
    def test_migration_001_creates_tables(self, temp_db):
        """Test that migration 001 creates all required tables"""
        manager = MigrationManager(temp_db)
        manager.apply_migrations(target_version=1)
        
        # Check that all tables exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'sessions', 'storage', 'context', 'history',
            'conversations', 'conversation_turns'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
        
        conn.close()
    
    def test_migration_002_adds_risk_level_column(self, temp_db):
        """Test that migration 002 adds risk_level column to history table"""
        manager = MigrationManager(temp_db)
        
        # Apply migration 1 first
        manager.apply_migrations(target_version=1)
        
        # Verify risk_level doesn't exist yet
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(history)")
        columns_v1 = [row[1] for row in cursor.fetchall()]
        assert "risk_level" not in columns_v1
        conn.close()
        
        # Apply migration 2
        manager.apply_migrations(target_version=2)
        
        # Verify risk_level now exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(history)")
        columns_v2 = [row[1] for row in cursor.fetchall()]
        assert "risk_level" in columns_v2
        conn.close()
    
    def test_migration_idempotency(self, temp_db):
        """Test that migrations can be run multiple times safely"""
        manager = MigrationManager(temp_db)
        
        # Apply migrations twice
        manager.apply_migrations()
        current_version_1 = manager.get_current_version()
        
        # Apply again - should be a no-op
        manager.apply_migrations()
        current_version_2 = manager.get_current_version()
        
        assert current_version_1 == current_version_2
    
    def test_data_preservation_during_migration(self, temp_db):
        """Test that existing data is preserved during migration"""
        # Create database with v1 schema
        manager = MigrationManager(temp_db)
        manager.apply_migrations(target_version=1)
        
        # Insert test data
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Add a session
        cursor.execute("""
            INSERT INTO sessions (session_id, metadata)
            VALUES ('test_session', '{"test": true}')
        """)
        
        # Add history entry (without risk_level, as it doesn't exist yet in v1)
        cursor.execute("""
            INSERT INTO history (session_id, action_type, action_data, result)
            VALUES ('test_session', 'test_action', '{"key": "value"}', '{"status": "ok"}')
        """)
        
        conn.commit()
        
        # Get the history entry ID
        cursor.execute("SELECT id, action_type, action_data FROM history WHERE session_id = 'test_session'")
        row = cursor.fetchone()
        history_id = row[0]
        original_action_type = row[1]
        original_action_data = row[2]
        
        conn.close()
        
        # Apply migration 2
        manager.apply_migrations(target_version=2)
        
        # Verify data is still there and intact
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sessions WHERE session_id = 'test_session'")
        session_row = cursor.fetchone()
        assert session_row is not None
        
        cursor.execute("SELECT id, action_type, action_data, risk_level FROM history WHERE id = ?", (history_id,))
        history_row = cursor.fetchone()
        assert history_row is not None
        assert history_row[1] == original_action_type
        assert history_row[2] == original_action_data
        assert history_row[3] == 'low'  # Default value for risk_level
        
        conn.close()
    
    def test_migration_info(self, temp_db):
        """Test get_migration_info returns correct information"""
        manager = MigrationManager(temp_db)
        
        # Check info for new database
        info = manager.get_migration_info()
        assert info["current_version"] == 0
        assert info["latest_version"] >= 2
        assert info["migrations_needed"] >= 2
        assert not info["up_to_date"]
        assert len(info["pending_migrations"]) >= 2
        
        # Apply all migrations
        manager.apply_migrations()
        
        # Check info after migration
        info = manager.get_migration_info()
        assert info["current_version"] == info["latest_version"]
        assert info["migrations_needed"] == 0
        assert info["up_to_date"]
        assert len(info["pending_migrations"]) == 0
    
    def test_verify_schema(self, temp_db):
        """Test schema verification"""
        manager = MigrationManager(temp_db)
        
        # New database should not pass verification
        assert not manager.verify_schema()
        
        # After migration, should pass
        manager.apply_migrations()
        assert manager.verify_schema()
    
    # NOTE: MemoryEngine tests are commented out due to heavy dependencies
    # They should be tested as integration tests
    
    # def test_memory_engine_with_new_database(self, temp_db):
    #     """Test MemoryEngine initialization with new database"""
    #     from janus.runtime.core.memory_engine import MemoryEngine
    #     # Create a new MemoryEngine - should apply migrations automatically
    #     engine = MemoryEngine(db_path=temp_db)
    #     
    #     # Verify migrations were applied
    #     manager = MigrationManager(temp_db)
    #     info = manager.get_migration_info()
    #     
    #     assert info["up_to_date"]
    #     assert info["current_version"] == info["latest_version"]
    
    # def test_memory_engine_with_old_database(self, temp_db):
    #     """Test MemoryEngine initialization with old database (v1)"""
    #     from janus.runtime.core.memory_engine import MemoryEngine
    #     # Create database at v1
    #     manager = MigrationManager(temp_db)
    #     manager.apply_migrations(target_version=1)
    #     
    #     # Add some test data
    #     conn = sqlite3.connect(temp_db)
    #     cursor = conn.cursor()
    #     cursor.execute("""
    #         INSERT INTO sessions (session_id, metadata)
    #         VALUES ('old_session', '{"version": 1}')
    #     """)
    #     cursor.execute("""
    #         INSERT INTO history (session_id, action_type, action_data)
    #         VALUES ('old_session', 'old_action', '{"old": "data"}')
    #     """)
    #     conn.commit()
    #     conn.close()
    #     
    #     # Create MemoryEngine - should upgrade to latest version
    #     engine = MemoryEngine(db_path=temp_db)
    #     
    #     # Verify upgrade happened
    #     manager = MigrationManager(temp_db)
    #     assert manager.get_current_version() == manager.get_latest_version()
    #     
    #     # Verify old data is still accessible
    #     history = engine.get_history(max_tokens=1000, session_id='old_session')
    #     assert len(history) == 1
    #     assert history[0]['type'] == 'old_action'
    
    def test_migration_with_existing_risk_level_column(self, temp_db):
        """Test that migration 002 is idempotent if risk_level already exists"""
        manager = MigrationManager(temp_db)
        
        # Apply both migrations
        manager.apply_migrations(target_version=2)
        
        # Try to apply migration 2 again (should be a no-op)
        # First reset the version
        manager.set_version(1)
        
        # Now apply migration 2 again
        manager.apply_migrations(target_version=2)
        
        # Should not raise an error and version should be 2
        assert manager.get_current_version() == 2


class TestBackwardsCompatibility:
    """Test backwards compatibility with old database format"""
    
    @pytest.fixture
    def old_format_db(self):
        """Create a database in the old format (without migrations)"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        # Create database with old CREATE TABLE IF NOT EXISTS pattern
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables as the old code did
        cursor.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT NOT NULL,
                result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add some old data
        cursor.execute("""
            INSERT INTO sessions (session_id, metadata)
            VALUES ('old_session', '{}')
        """)
        
        cursor.execute("""
            INSERT INTO history (session_id, action_type, action_data)
            VALUES ('old_session', 'old_command', '{"command": "test"}')
        """)
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_upgrade_from_old_format(self, old_format_db):
        """Test that old format databases can be upgraded"""
        # Check that database has no version set
        manager = MigrationManager(old_format_db)
        assert manager.get_current_version() == 0
        
        # Apply migrations (should work on existing tables)
        success = manager.apply_migrations()
        assert success
        
        # Verify data is preserved
        conn = sqlite3.connect(old_format_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_id = 'old_session'")
        assert cursor.fetchone()[0] == 1
        
        cursor.execute("SELECT COUNT(*) FROM history WHERE session_id = 'old_session'")
        assert cursor.fetchone()[0] == 1
        
        conn.close()


if __name__ == "__main__":
    if PYTEST_AVAILABLE:
        pytest.main([__file__, "-v"])
    else:
        unittest.main()
