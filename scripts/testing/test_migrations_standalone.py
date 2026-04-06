#!/usr/bin/env python3
"""
Standalone test script for database migrations (TICKET-DB-001)

This script can be run directly without heavy dependencies.
This script is in scripts/testing/, so we need to navigate to repo root
for proper imports.
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add repository root to Python path
# This script is in scripts/testing/, go up two levels to reach repo root
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

print(f"Repository root: {REPO_ROOT}")
print(f"Python path: {sys.path[0]}")

# Import the migration module directly to avoid loading all janus dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "db_migrations",
    REPO_ROOT / "janus" / "core" / "db_migrations.py"
)
db_migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_migrations)
MigrationManager = db_migrations.MigrationManager


def test_migration_from_scratch():
    """Test applying migrations to a new database"""
    print("\n🧪 Test: Apply migrations from scratch")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        manager = MigrationManager(db_path)
        
        # Check initial version
        current = manager.get_current_version()
        print(f"   Initial version: {current}")
        assert current == 0, f"Expected version 0, got {current}"
        
        # Apply migrations
        success = manager.apply_migrations()
        print(f"   Migrations applied: {success}")
        assert success, "Migration failed"
        
        # Check final version
        final = manager.get_current_version()
        latest = manager.get_latest_version()
        print(f"   Final version: {final}, Latest: {latest}")
        assert final == latest, f"Expected version {latest}, got {final}"
        
        # Verify schema
        verified = manager.verify_schema()
        print(f"   Schema verified: {verified}")
        assert verified, "Schema verification failed"
        
        print("   ✓ PASSED")
        return True
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_data_preservation():
    """Test that existing data is preserved during migration"""
    print("\n🧪 Test: Data preservation during migration")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # Create database at v1
        manager = MigrationManager(db_path)
        manager.apply_migrations(target_version=1)
        print(f"   Created database at v1")
        
        # Insert test data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, metadata)
            VALUES ('test_session', '{"test": true}')
        """)
        cursor.execute("""
            INSERT INTO history (session_id, action_type, action_data, result)
            VALUES ('test_session', 'test_action', '{"key": "value"}', '{"status": "ok"}')
        """)
        conn.commit()
        
        # Get original data
        cursor.execute("SELECT action_type, action_data FROM history")
        original_data = cursor.fetchone()
        conn.close()
        print(f"   Inserted test data: {original_data[0]}")
        
        # Upgrade to v2
        manager.apply_migrations(target_version=2)
        print(f"   Upgraded to v2")
        
        # Verify data is preserved
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_id = 'test_session'")
        session_count = cursor.fetchone()[0]
        print(f"   Sessions preserved: {session_count}")
        assert session_count == 1, "Session data lost"
        
        cursor.execute("SELECT action_type, action_data, risk_level FROM history")
        migrated_data = cursor.fetchone()
        print(f"   History preserved: {migrated_data[0]}, risk_level: {migrated_data[2]}")
        
        assert migrated_data[0] == original_data[0], "Action type changed"
        assert migrated_data[1] == original_data[1], "Action data changed"
        assert migrated_data[2] == 'low', "risk_level not set to default"
        
        conn.close()
        
        print("   ✓ PASSED")
        return True
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_idempotency():
    """Test that migrations can be run multiple times safely"""
    print("\n🧪 Test: Migration idempotency")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        manager = MigrationManager(db_path)
        
        # Apply migrations
        manager.apply_migrations()
        version_1 = manager.get_current_version()
        print(f"   First run: version {version_1}")
        
        # Apply again
        manager.apply_migrations()
        version_2 = manager.get_current_version()
        print(f"   Second run: version {version_2}")
        
        assert version_1 == version_2, "Version changed on second run"
        
        print("   ✓ PASSED")
        return True
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_old_database_upgrade():
    """Test upgrading an old database (v0 format without version)"""
    print("\n🧪 Test: Upgrade old database format")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # Create old format database (without version)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
        print("   Created old format database")
        
        # Apply migrations
        manager = MigrationManager(db_path)
        initial_version = manager.get_current_version()
        print(f"   Initial version: {initial_version}")
        assert initial_version == 0, "Old database should have version 0"
        
        success = manager.apply_migrations()
        print(f"   Migrations applied: {success}")
        assert success, "Migration failed"
        
        final_version = manager.get_current_version()
        print(f"   Final version: {final_version}")
        
        # Verify old data is preserved
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_id = 'old_session'")
        assert cursor.fetchone()[0] == 1, "Old session lost"
        
        cursor.execute("SELECT COUNT(*) FROM history WHERE session_id = 'old_session'")
        assert cursor.fetchone()[0] == 1, "Old history lost"
        
        conn.close()
        
        print("   ✓ PASSED")
        return True
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """Run all tests"""
    print("=" * 60)
    print("Database Migration System Tests (TICKET-DB-001)")
    print("=" * 60)
    
    tests = [
        test_migration_from_scratch,
        test_data_preservation,
        test_idempotency,
        test_old_database_upgrade,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
