"""
Tests for Memory Service thread safety and concurrency
TICKET B2: Validate memory service thread safety
"""
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

import pytest

from janus.runtime.core.contracts import Intent
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


class TestMemoryEngineConcurrency:
    """Test concurrent access to memory engine"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # Cleanup
        try:
            Path(db_path).unlink()
        except Exception:
            pass

    @pytest.fixture
    def memory_service(self, temp_db):
        """Create a memory service instance"""
        settings = DatabaseSettings(path=temp_db, enable_wal=True)
        return MemoryEngine(settings)

    def test_concurrent_session_creation(self, memory_service):
        """Test creating sessions concurrently"""
        num_threads = 10
        sessions_created = []
        lock = threading.Lock()

        def create_session():
            session_id = memory_service.create_session()
            with lock:
                sessions_created.append(session_id)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=create_session)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All sessions should be created successfully
        assert len(sessions_created) == num_threads
        # All session IDs should be unique
        assert len(set(sessions_created)) == num_threads

    def test_concurrent_reads_and_writes(self, memory_service):
        """Test concurrent reads and writes to the same session"""
        session_id = memory_service.create_session()
        num_operations = 50
        results = []
        lock = threading.Lock()

        def write_command(i):
            try:
                memory_service.store_command(
                    session_id=session_id, request_id=f"req-{i}", raw_command=f"test command {i}"
                )
                with lock:
                    results.append(("write", i, True))
            except Exception as e:
                with lock:
                    results.append(("write", i, False, str(e)))

        def read_commands():
            try:
                commands = memory_service.get_command_history(session_id)
                with lock:
                    results.append(("read", len(commands), True))
            except Exception as e:
                with lock:
                    results.append(("read", 0, False, str(e)))

        # Mix of reads and writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Submit write operations
            for i in range(num_operations):
                futures.append(executor.submit(write_command, i))

            # Submit read operations between writes
            for _ in range(10):
                futures.append(executor.submit(read_commands))

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # Verify all writes succeeded
        write_results = [r for r in results if r[0] == "write"]
        assert len(write_results) == num_operations
        assert all(r[2] for r in write_results), "Some writes failed"

        # Verify all reads succeeded
        read_results = [r for r in results if r[0] == "read"]
        assert all(r[2] for r in read_results), "Some reads failed"

    def test_concurrent_execution_logging(self, memory_service):
        """Test concurrent execution logging"""
        session_id = memory_service.create_session()
        num_logs = 100
        errors = []

        def log_execution(i):
            try:
                memory_service.log_execution(
                    session_id=session_id,
                    request_id=f"req-{i}",
                    action=f"action-{i}",
                    status="success" if i % 2 == 0 else "failed",
                    message=f"Test log {i}",
                    duration_ms=i * 10,
                )
            except Exception as e:
                errors.append((i, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(log_execution, i) for i in range(num_logs)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all logs were stored
        logs = memory_service.get_execution_logs(session_id=session_id, limit=num_logs + 10)
        assert len(logs) == num_logs

    def test_concurrent_structured_logging(self, memory_service):
        """Test concurrent structured logging"""
        num_logs = 100
        errors = []

        def log_structured(i):
            try:
                memory_service.log_structured(
                    level="INFO" if i % 2 == 0 else "ERROR",
                    logger=f"test.logger.{i % 5}",
                    message=f"Test message {i}",
                    session_id=f"session-{i % 10}",
                    request_id=f"req-{i}",
                )
            except Exception as e:
                errors.append((i, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(log_structured, i) for i in range(num_logs)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify logs were stored
        logs = memory_service.get_structured_logs(limit=num_logs + 10)
        assert len(logs) >= num_logs

    def test_concurrent_context_operations(self, memory_service):
        """Test concurrent context storage and retrieval"""
        session_id = memory_service.create_session()
        num_contexts = 50
        errors = []

        def store_context(i):
            try:
                memory_service.store_context(
                    session_id=session_id,
                    context_type=f"type-{i % 5}",
                    data={"value": i, "timestamp": time.time()},
                )
            except Exception as e:
                errors.append(("store", i, str(e)))

        def get_context():
            try:
                contexts = memory_service.get_context(session_id)
                return len(contexts)
            except Exception as e:
                errors.append(("get", 0, str(e)))
                return 0

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []

            # Store contexts
            for i in range(num_contexts):
                futures.append(executor.submit(store_context, i))

            # Concurrent reads
            for _ in range(10):
                futures.append(executor.submit(get_context))

            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify contexts were stored
        contexts = memory_service.get_context(session_id, limit=num_contexts + 10)
        assert len(contexts) == num_contexts

    def test_concurrent_session_updates(self, memory_service):
        """Test concurrent updates to the same session"""
        session_id = memory_service.create_session()
        num_updates = 50
        errors = []

        def update_session(i):
            try:
                # Get current session
                data = memory_service.get_session(session_id) or {}

                # Update with new data
                data[f"key-{i}"] = f"value-{i}"
                memory_service.update_session(session_id, data)
            except Exception as e:
                errors.append((i, str(e)))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_session, i) for i in range(num_updates)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Final session should have some updates (may not have all due to race conditions)
        final_data = memory_service.get_session(session_id)
        assert final_data is not None
        # At least some keys should be present
        assert len(final_data) > 0

    def test_concurrent_multi_session_operations(self, memory_service):
        """Test concurrent operations across multiple sessions"""
        num_sessions = 10
        operations_per_session = 20
        errors = []

        # Create sessions
        session_ids = [memory_service.create_session() for _ in range(num_sessions)]

        def session_operations(session_id, op_id):
            try:
                # Store command
                memory_service.store_command(
                    session_id=session_id,
                    request_id=f"req-{session_id}-{op_id}",
                    raw_command=f"command {op_id}",
                )

                # Store context
                memory_service.store_context(
                    session_id=session_id, context_type="test", data={"op_id": op_id}
                )

                # Log execution
                memory_service.log_execution(
                    session_id=session_id,
                    request_id=f"req-{session_id}-{op_id}",
                    action="test_action",
                    status="success",
                    message=f"Operation {op_id}",
                )
            except Exception as e:
                errors.append((session_id, op_id, str(e)))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for session_id in session_ids:
                for op_id in range(operations_per_session):
                    futures.append(executor.submit(session_operations, session_id, op_id))

            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify operations for each session
        for session_id in session_ids:
            commands = memory_service.get_command_history(session_id)
            assert len(commands) == operations_per_session

            contexts = memory_service.get_context(session_id, limit=operations_per_session + 10)
            assert len(contexts) == operations_per_session

            logs = memory_service.get_execution_logs(session_id=session_id)
            assert len(logs) == operations_per_session

    def test_no_database_corruption_under_load(self, memory_service):
        """Test that database doesn't get corrupted under heavy concurrent load"""
        session_id = memory_service.create_session()
        num_operations = 200

        def mixed_operations(i):
            # Mix of different operations
            if i % 4 == 0:
                memory_service.store_command(
                    session_id=session_id, request_id=f"req-{i}", raw_command=f"command {i}"
                )
            elif i % 4 == 1:
                memory_service.get_command_history(session_id)
            elif i % 4 == 2:
                memory_service.log_execution(
                    session_id=session_id,
                    request_id=f"req-{i}",
                    action="test",
                    status="success",
                    message="test",
                )
            else:
                memory_service.get_session(session_id)

        # Run operations concurrently
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(num_operations)]
            for future in as_completed(futures):
                future.result()

        # Database should still be queryable
        commands = memory_service.get_command_history(session_id)
        logs = memory_service.get_execution_logs(session_id=session_id)
        session = memory_service.get_session(session_id)

        # All queries should succeed
        assert commands is not None
        assert logs is not None
        assert session is not None

    def test_concurrent_session_analytics(self, memory_service):
        """Test that analytics can be safely computed during concurrent operations"""
        # Create some sessions with data
        sessions = []
        for i in range(5):
            session_id = memory_service.create_session()
            sessions.append(session_id)

            for j in range(10):
                memory_service.store_command(
                    session_id=session_id, request_id=f"req-{i}-{j}", raw_command=f"command {j}"
                )

        errors = []

        def get_analytics():
            try:
                analytics = memory_service.get_session_analytics()
                assert "total_sessions" in analytics
                assert "total_commands" in analytics
            except Exception as e:
                errors.append(str(e))

        def write_more_data(session_id, i):
            try:
                memory_service.log_execution(
                    session_id=session_id,
                    request_id=f"req-extra-{i}",
                    action="test",
                    status="success",
                    message="concurrent write",
                )
            except Exception as e:
                errors.append(str(e))

        # Run analytics queries concurrently with writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Multiple analytics queries
            for _ in range(10):
                futures.append(executor.submit(get_analytics))

            # Concurrent writes
            for i in range(20):
                session_id = sessions[i % len(sessions)]
                futures.append(executor.submit(write_more_data, session_id, i))

            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
