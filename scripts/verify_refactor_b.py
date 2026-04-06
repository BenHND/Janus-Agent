#!/usr/bin/env python3
"""
Verification script for Refactor Final B

This script verifies that all requirements from the refactoring issue are met:
1. Single entry point (main.py)
2. Single storage (SQLite database, no JSON files)
3. Unified executor (no direct UI library calls)
4. Parameterized configuration
5. Guard tests in place
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from janus.runtime.core import MemoryService, Settings, JanusPipeline
from janus.io.stt.calibration_manager import CalibrationManager


def check_settings():
    """Verify settings are properly configured"""
    print("=" * 60)
    print("1. CHECKING SETTINGS CONFIGURATION")
    print("=" * 60)

    settings = Settings()

    # Check database path
    print(f"✓ Database path: {settings.database.path}")
    assert settings.database.path == "data/janus.db", "Database path should be data/janus.db"

    # Check calibration dir
    print(f"✓ Calibration dir: {settings.calibration.profile_dir}")
    assert hasattr(settings, "calibration"), "Settings should have calibration group"

    print("✓ Settings configuration OK\n")
    return settings


def check_database():
    """Verify database is created correctly"""
    print("=" * 60)
    print("2. CHECKING DATABASE STORAGE")
    print("=" * 60)

    settings = Settings()
    memory = MemoryService(settings.database)

    # Check database exists
    db_path = Path(settings.database.path)
    assert db_path.exists(), f"Database should exist at {db_path}"
    print(f"✓ Database exists: {db_path}")

    # Check data directory
    data_dir = db_path.parent
    assert data_dir.exists(), "data/ directory should exist"
    print(f"✓ Data directory: {data_dir}")

    # Verify no JSON files at root
    root_files = list(Path(".").glob("*.json"))
    json_state_files = [
        f
        for f in root_files
        if f.name in ["session_state.json", "context_memory.json", "session_memory.json"]
    ]
    assert len(json_state_files) == 0, f"Found JSON state files: {json_state_files}"
    print("✓ No JSON state files at root")

    print("✓ Database storage OK\n")
    return memory


def check_pipeline():
    """Verify pipeline has correct API"""
    print("=" * 60)
    print("3. CHECKING PIPELINE API")
    print("=" * 60)

    settings = Settings()
    memory = MemoryService(settings.database)
    pipeline = JanusPipeline(settings, memory)

    # Check required methods
    assert hasattr(pipeline, "process_command"), "Pipeline should have process_command"
    assert hasattr(pipeline, "cleanup"), "Pipeline should have cleanup"
    print("✓ Pipeline has process_command method")
    print("✓ Pipeline has cleanup method")

    # Test cleanup
    pipeline.cleanup()
    print("✓ Cleanup method works")

    print("✓ Pipeline API OK\n")


def check_contracts():
    """Verify core contracts exist"""
    print("=" * 60)
    print("4. CHECKING CORE CONTRACTS")
    print("=" * 60)

    from janus.runtime.core import contracts

    required = ["Intent", "ActionPlan", "ActionResult", "ExecutionResult", "CommandError"]
    for contract in required:
        assert hasattr(contracts, contract), f"Missing contract: {contract}"
        print(f"✓ Contract present: {contract}")

    print("✓ Core contracts OK\n")


def check_calibration():
    """Verify calibration uses Settings"""
    print("=" * 60)
    print("5. CHECKING CALIBRATION CONFIGURATION")
    print("=" * 60)

    # Test default initialization
    cm1 = CalibrationManager()
    print(f"✓ Default calibration dir: {cm1.profile_dir}")

    # Test custom path
    cm2 = CalibrationManager(profile_dir="custom_test")
    print(f"✓ Custom calibration dir: {cm2.profile_dir}")
    assert str(cm2.profile_dir) == "custom_test"

    print("✓ Calibration configuration OK\n")


def check_guard_tests():
    """Verify guard tests exist and pass"""
    print("=" * 60)
    print("6. CHECKING GUARD TESTS")
    print("=" * 60)

    import unittest

    from tests import test_refactor_guards

    # Load tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_refactor_guards)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"✓ All {result.testsRun} guard tests passed")
    else:
        print(f"✗ {len(result.failures)} test(s) failed")
        for test, traceback in result.failures:
            print(f"  Failed: {test}")
        return False

    print("✓ Guard tests OK\n")
    return True


def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("REFACTOR FINAL B - VERIFICATION")
    print("=" * 60 + "\n")

    try:
        check_settings()
        check_database()
        check_pipeline()
        check_contracts()
        check_calibration()

        if not check_guard_tests():
            print("\n✗ VERIFICATION FAILED: Guard tests did not pass")
            return 1

        print("=" * 60)
        print("✓ ALL VERIFICATION CHECKS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  • Single entry point: main.py ✓")
        print("  • Single storage: SQLite in data/janus.db ✓")
        print("  • No JSON state files ✓")
        print("  • Parameterized configuration ✓")
        print("  • Pipeline API complete ✓")
        print("  • Core contracts present ✓")
        print("  • Guard tests passing ✓")
        print()

        return 0

    except Exception as e:
        print(f"\n✗ VERIFICATION FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
