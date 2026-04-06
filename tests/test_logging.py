"""
Tests for Janus logging module
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from janus.logging import (
    DiagnosticCollector,
    LogFormatter,
    LogLevel,
    PerformanceLogger,
    JanusLogger,
    configure_logging,
    get_logger,
)


class TestJanusLogger(unittest.TestCase):
    """Test JanusLogger functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = JanusLogger("test", log_dir=self.test_dir)

        self.assertEqual(logger.name, "test")
        self.assertTrue(logger.log_dir.exists())

        # Check that log file was created
        log_files = list(logger.log_dir.glob("test.log"))
        self.assertEqual(len(log_files), 1)

    def test_log_levels(self):
        """Test different log levels"""
        logger = JanusLogger(
            "test_levels", log_dir=self.test_dir, level=LogLevel.DEBUG, console_output=False
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Read log file and verify messages
        log_file = logger.log_dir / "test_levels.log"
        with open(log_file, "r") as f:
            content = f.read()

        self.assertIn("Debug message", content)
        self.assertIn("Info message", content)
        self.assertIn("Warning message", content)
        self.assertIn("Error message", content)
        self.assertIn("Critical message", content)

    def test_log_with_extra_data(self):
        """Test logging with extra data"""
        logger = JanusLogger(
            "test_extra",
            log_dir=self.test_dir,
            formatter=LogFormatter.DETAILED,
            console_output=False,
        )

        logger.info("Test message", extra={"key": "value", "number": 42})

        # Log file should exist
        log_file = logger.log_dir / "test_extra.log"
        self.assertTrue(log_file.exists())

    def test_log_rotation(self):
        """Test log file rotation"""
        logger = JanusLogger(
            "test_rotation",
            log_dir=self.test_dir,
            max_bytes=100,  # Small size for testing
            backup_count=2,
            console_output=False,
        )

        # Write enough to trigger rotation
        for i in range(50):
            logger.info(f"Message {i} with some padding to increase size")

        # Should have multiple log files
        log_files = logger.get_log_files()
        self.assertGreater(len(log_files), 1)

    def test_set_level(self):
        """Test changing log level"""
        logger = JanusLogger(
            "test_set_level", log_dir=self.test_dir, level=LogLevel.INFO, console_output=False
        )

        # DEBUG should not be logged initially
        logger.debug("Debug 1")

        # Change to DEBUG
        logger.set_level(LogLevel.DEBUG)
        logger.debug("Debug 2")

        # Read log file
        log_file = logger.log_dir / "test_set_level.log"
        with open(log_file, "r") as f:
            content = f.read()

        self.assertNotIn("Debug 1", content)
        self.assertIn("Debug 2", content)

    def test_get_logger(self):
        """Test get_logger function"""
        logger1 = get_logger("test_get", log_dir=self.test_dir)
        logger2 = get_logger("test_get")

        # Should return same instance
        self.assertIs(logger1, logger2)

    def test_json_formatter(self):
        """Test JSON formatter"""
        logger = JanusLogger(
            "test_json", log_dir=self.test_dir, formatter=LogFormatter.JSON, console_output=False
        )

        logger.info("JSON test", extra={"data": "value"})

        # Read and parse log file (skip initialization line)
        log_file = logger.log_dir / "test_json.log"
        with open(log_file, "r") as f:
            lines = f.readlines()

        # Find the JSON test line
        test_line = None
        for line in lines:
            log_data = json.loads(line.strip())
            if log_data["message"] == "JSON test":
                test_line = log_data
                break

        # Should be valid JSON with correct data
        self.assertIsNotNone(test_line)
        self.assertEqual(test_line["message"], "JSON test")
        self.assertEqual(test_line["level"], "INFO")


class TestPerformanceLogger(unittest.TestCase):
    """Test PerformanceLogger functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_timer_basic(self):
        """Test basic timer functionality"""
        perf_logger = PerformanceLogger("test_perf")

        perf_logger.start_timer("operation1")
        import time

        time.sleep(0.1)
        duration = perf_logger.end_timer("operation1", log_result=False)

        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0.09)
        self.assertLess(duration, 0.2)

    def test_timer_context_manager(self):
        """Test timer context manager"""
        perf_logger = PerformanceLogger("test_perf_ctx")

        import time

        with perf_logger.measure("context_operation"):
            time.sleep(0.1)

        # Timer should be completed
        self.assertNotIn("context_operation", perf_logger.timers)

    def test_memory_logging(self):
        """Test memory usage logging"""
        perf_logger = PerformanceLogger("test_memory")

        # Should not raise exception
        perf_logger.log_memory_usage("test context")

    def test_cpu_logging(self):
        """Test CPU usage logging"""
        perf_logger = PerformanceLogger("test_cpu")

        # Should not raise exception
        perf_logger.log_cpu_usage("test context")

    def test_system_resources_logging(self):
        """Test system resources logging"""
        perf_logger = PerformanceLogger("test_resources")

        # Should not raise exception
        perf_logger.log_system_resources("test context")

    def test_operation_stats(self):
        """Test operation statistics logging"""
        perf_logger = PerformanceLogger("test_stats")

        perf_logger.log_operation_stats(
            "test_op", success=True, duration=1.5, extra={"data": "value"}
        )

        perf_logger.log_operation_stats("test_op_fail", success=False, duration=0.5)


class TestDiagnosticCollector(unittest.TestCase):
    """Test DiagnosticCollector functionality"""

    def test_system_info_collection(self):
        """Test system info collection"""
        collector = DiagnosticCollector()
        info = collector.collect_system_info()

        self.assertIn("platform", info)
        self.assertIn("python", info)
        self.assertIn("environment", info)

        self.assertIn("system", info["platform"])
        self.assertIn("version", info["python"])

    def test_dependencies_collection(self):
        """Test dependencies collection"""
        collector = DiagnosticCollector()
        deps = collector.collect_dependencies()

        self.assertIsInstance(deps, dict)
        # Should have at least some packages
        self.assertGreater(len(deps), 0)

    def test_config_collection(self):
        """Test Janus config collection"""
        collector = DiagnosticCollector()
        config = collector.collect_janus_config()

        self.assertIsInstance(config, dict)

    def test_requirements_check(self):
        """Test requirements checking"""
        collector = DiagnosticCollector()
        requirements = collector.check_requirements()

        self.assertIn("python_version", requirements)
        self.assertIn("platform", requirements)
        self.assertIn("modules", requirements)

        # Python version should be satisfied
        self.assertTrue(requirements["python_version"]["satisfied"])

    def test_generate_diagnostic_report(self):
        """Test diagnostic report generation"""
        collector = DiagnosticCollector()
        report = collector.generate_diagnostic_report()

        # Should be valid JSON
        data = json.loads(report)

        self.assertIn("timestamp", data)
        self.assertIn("system_info", data)
        self.assertIn("dependencies", data)
        self.assertIn("requirements", data)

    def test_save_diagnostic_report(self):
        """Test saving diagnostic report"""
        collector = DiagnosticCollector()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report.json")
            result_path = collector.save_diagnostic_report(output_path)

            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))

            # Should be valid JSON
            with open(output_path, "r") as f:
                data = json.load(f)

            self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
