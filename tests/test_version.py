"""
Tests for version management and CLI version display
"""
import subprocess
import sys
import unittest
from io import StringIO


class TestVersionManagement(unittest.TestCase):
    """Test version management functionality"""

    def test_version_import(self):
        """Test that version can be imported from janus"""
        from janus import __version__

        self.assertIsNotNone(__version__)
        self.assertIsInstance(__version__, str)
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")  # SemVer format

    def test_version_consistency(self):
        """Test that version is consistent between __init__.py and setup.py"""
        from janus import __version__ as init_version

        # Read version from setup.py
        with open("setup.py", "r") as f:
            setup_content = f.read()

        # Extract VERSION from setup.py
        import re

        match = re.search(r"VERSION = '([^']+)'", setup_content)
        self.assertIsNotNone(match, "VERSION not found in setup.py")
        setup_version = match.group(1)

        # Versions should match
        self.assertEqual(
            init_version,
            setup_version,
            f"Version mismatch: __init__.py={init_version}, setup.py={setup_version}",
        )

    def test_cli_version_flag(self):
        """Test that CLI --version flag works"""
        # Run main.py --version
        result = subprocess.run(
            [sys.executable, "main.py", "--version"], capture_output=True, text=True, timeout=10
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")

        # Should output version
        output = result.stdout + result.stderr
        self.assertIn("1.0.0", output, "Version 1.0.0 not found in output")

    def test_version_format(self):
        """Test that version follows Semantic Versioning"""
        from janus import __version__

        # Split version into parts
        parts = __version__.split(".")

        # Should have exactly 3 parts (MAJOR.MINOR.PATCH)
        self.assertEqual(len(parts), 3, "Version should have format MAJOR.MINOR.PATCH")

        # All parts should be numeric
        for part in parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' is not numeric")

    def test_changelog_exists(self):
        """Test that CHANGELOG.md exists and has proper structure"""
        import os

        # Check file exists
        self.assertTrue(os.path.exists("CHANGELOG.md"), "CHANGELOG.md does not exist")

        # Read and check content
        with open("CHANGELOG.md", "r") as f:
            content = f.read()

        # Should have proper structure
        self.assertIn("# Changelog", content)
        self.assertIn("[Unreleased]", content)
        self.assertIn("Semantic Versioning", content)
        self.assertIn("[1.0.0]", content)

    def test_release_process_docs_exist(self):
        """Test that release process documentation exists"""
        import os

        # Check file exists
        self.assertTrue(
            os.path.exists("docs/RELEASE_PROCESS.md"), "docs/RELEASE_PROCESS.md does not exist"
        )

        # Read and check content
        with open("docs/RELEASE_PROCESS.md", "r") as f:
            content = f.read()

        # Should have key sections
        self.assertIn("Version Management", content)
        self.assertIn("Release Preparation", content)
        self.assertIn("Creating a Release", content)
        self.assertIn("Semantic Versioning", content)


if __name__ == "__main__":
    unittest.main()
