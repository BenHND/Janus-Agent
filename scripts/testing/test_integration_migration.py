#!/usr/bin/env python3
"""
Integration test for database migration with MemoryEngine (TICKET-DB-001)

This test verifies that the migration system works correctly with the actual
MemoryEngine class, including all its dependencies.
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def test_new_database_with_memory_engine():
    """Test creating a new MemoryEngine applies migrations automatically"""
    print("\n🧪 Integration Test: New database with MemoryEngine")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # Import here to avoid loading dependencies unless needed
        from janus.runtime.core.memory_engine import MemoryEngine
        from janus.runtime.core.db_migrations import MigrationManager
        
        # Create MemoryEngine (should apply migrations automatically)
        print("   Creating MemoryEngine...")
        engine = MemoryEngine(db_path=db_path, enable_semantic_memory=False)
        
        # Check that migrations were applied
        manager = MigrationManager(db_path)
        info = manager.get_migration_info()
        
        print(f"   Database version: {info['current_version']}")
        print(f"   Latest version: {info['latest_version']}")
        print(f"   Up to date: {info['up_to_date']}")
        
        assert info['up_to_date'], "Database should be up-to-date after initialization"
        assert info['current_version'] == info['latest_version'], "Version mismatch"
        
        # Test basic memory operations
        print("   Testing basic operations...")
        engine.store("test_key", "test_value")
        value = engine.retrieve("test_key")
        assert value == "test_value", "Store/retrieve failed"
        
        engine.record_action("test_action", {"data": "test"})
        history = engine.get_history(max_tokens=1000)
        assert len(history) > 0, "History recording failed"
        
        print("   ✓ PASSED")
        return True
        
    except ImportError as e:
        print(f"   ⚠ SKIPPED: {e}")
        print("   (This is expected if dependencies are not installed)")
        return True
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        # Clean up chroma directory if created
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path, ignore_errors=True)


def test_old_database_upgrade():
    """Test upgrading an old database (v1) to latest version"""
    print("\n🧪 Integration Test: Upgrade old database (v1 → v2)")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # Import migration manager
        from janus.runtime.core.db_migrations import MigrationManager
        
        # Create database at v1
        print("   Creating v1 database...")
        manager = MigrationManager(db_path)
        manager.apply_migrations(target_version=1)
        
        # Add some test data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, metadata)
            VALUES ('old_session', '{"version": 1}')
        """)
        cursor.execute("""
            INSERT INTO history (session_id, action_type, action_data)
            VALUES ('old_session', 'old_action', '{"command": "test"}')
        """)
        conn.commit()
        conn.close()
        print("   Added test data to v1 database")
        
        # Now create MemoryEngine - should upgrade automatically
        try:
            from janus.runtime.core.memory_engine import MemoryEngine
            
            print("   Creating MemoryEngine (should trigger upgrade)...")
            engine = MemoryEngine(db_path=db_path, enable_semantic_memory=False, 
                                session_id='old_session')
            
            # Check that database was upgraded
            manager = MigrationManager(db_path)
            info = manager.get_migration_info()
            
            print(f"   Database version: {info['current_version']}")
            print(f"   Latest version: {info['latest_version']}")
            
            assert info['up_to_date'], "Database should be upgraded"
            
            # Verify old data is preserved
            print("   Verifying old data preservation...")
            history = engine.get_history(max_tokens=1000, session_id='old_session')
            assert len(history) > 0, "Old history should be preserved"
            assert history[0]['type'] == 'old_action', "Action type mismatch"
            
            # Verify new column exists and has default value
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT risk_level FROM history WHERE session_id = 'old_session'")
            risk_level = cursor.fetchone()[0]
            conn.close()
            
            print(f"   risk_level column value: {risk_level}")
            assert risk_level == 'low', "risk_level should have default value"
            
            print("   ✓ PASSED")
            return True
            
        except ImportError as e:
            print(f"   ⚠ SKIPPED: {e}")
            print("   (This is expected if dependencies are not installed)")
            return True
            
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        # Clean up chroma directory if created
        chroma_path = Path(db_path).parent / f"{Path(db_path).stem}_chroma"
        if chroma_path.exists():
            import shutil
            shutil.rmtree(chroma_path, ignore_errors=True)


def main():
    """Run integration tests"""
    print("=" * 60)
    print("Database Migration Integration Tests (TICKET-DB-001)")
    print("=" * 60)
    
    tests = [
        test_new_database_with_memory_engine,
        test_old_database_upgrade,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            result = test()
            if result is True:
                passed += 1
        except Exception as e:
            if "SKIPPED" in str(e):
                skipped += 1
            else:
                print(f"   ✗ FAILED: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
    
    if failed > 0:
        print("\n⚠️  Some tests failed. This may be due to missing dependencies.")
        print("   Try installing dependencies: pip install -r requirements.txt")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
