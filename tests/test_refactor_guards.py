"""
Guard tests to prevent architectural regressions.

These tests enforce:
1. Single entry point (main.py only)
2. No direct UI library usage in modules
3. No JSON state file writes at runtime
4. Core contracts exist
5. Pipeline API is complete
"""
import importlib
import os
import re
import unittest
from pathlib import Path

# Get absolute paths
ROOT = Path(__file__).parent.parent.absolute()
SPECTRA_DIR = ROOT / "janus"
MODULES_DIR = SPECTRA_DIR / "modules"


class TestRefactorGuards(unittest.TestCase):
    """Guard tests for refactoring final B"""

    def test_modules_do_not_use_ui_libs_directly(self):
        """
        Test that modules do not use pyautogui, appscript, or osascript directly.
        All UI automation must go through the UIExecutor.
        """
        offenders = []

        # Check all Python files in janus/modules/
        for py_file in MODULES_DIR.rglob("*.py"):
            if py_file.name == "__init__.py":
                # __init__.py is allowed to import for backward compatibility warnings
                continue

            # Skip example/documentation files that show migration patterns
            if "unified" in py_file.name and "example" in py_file.stem.lower():
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                # Remove all docstrings and comments to avoid false positives
                # This removes triple-quoted strings and # comments
                content_no_docs = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
                content_no_docs = re.sub(r"'''.*?'''", "", content_no_docs, flags=re.DOTALL)
                content_no_docs = re.sub(r"#.*$", "", content_no_docs, flags=re.MULTILINE)

                # Check for direct usage of UI libraries in actual code
                if re.search(r"\bpyautogui\.", content_no_docs):
                    offenders.append(f"{py_file.relative_to(ROOT)}: uses pyautogui")

                if re.search(r"\bappscript\.", content_no_docs):
                    offenders.append(f"{py_file.relative_to(ROOT)}: uses appscript")

                if re.search(r"subprocess\..*osascript", content_no_docs):
                    offenders.append(f"{py_file.relative_to(ROOT)}: uses subprocess.osascript")

            except Exception as e:
                print(f"Warning: Could not read {py_file}: {e}")

        self.assertEqual(
            offenders,
            [],
            f"Modules must use UIExecutor only, found direct UI calls in:\n"
            + "\n".join(f"  - {o}" for o in offenders),
        )

    def test_single_entrypoint(self):
        """
        Test that only main.py has a __main__ entry point.
        Examples and scripts are allowed to have entry points, but not production code.
        """
        extra_entrypoints = []

        # Check all Python files except main.py, examples/, and scripts/
        for py_file in ROOT.rglob("*.py"):
            # Skip main.py
            if py_file.relative_to(ROOT) == Path("main.py"):
                continue

            # Skip examples and scripts directories
            rel_path = py_file.relative_to(ROOT)
            if rel_path.parts[0] in ("examples", "scripts"):
                continue

            # Skip tests directory
            if rel_path.parts[0] == "tests":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                # Remove all template strings (triple quotes) to avoid false positives
                content_no_templates = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
                content_no_templates = re.sub(
                    r"'''.*?'''", "", content_no_templates, flags=re.DOTALL
                )

                # Check for __main__ block in actual code
                if re.search(r'if __name__ == ["\']__main__["\']:', content_no_templates):
                    extra_entrypoints.append(str(rel_path))

            except Exception as e:
                print(f"Warning: Could not read {py_file}: {e}")

        self.assertEqual(
            extra_entrypoints,
            [],
            f"Only main.py must be executable; extra entrypoints found in:\n"
            + "\n".join(f"  - {e}" for e in extra_entrypoints),
        )

    def test_no_json_state_writes(self):
        """
        Test that no code writes to JSON state files at runtime.
        All state must be stored in the SQLite database.
        """
        offenders = []

        # Patterns indicating JSON state file usage
        json_state_files = ["session_state.json", "context_memory.json", "session_memory.json"]

        # Check all Python files in janus/
        for py_file in SPECTRA_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")

                # Check if file references JSON state files and has write operations
                for json_file in json_state_files:
                    if json_file in content:
                        # Check for file write operations
                        if "json.dump" in content or "open(" in content and "w" in content:
                            offenders.append(
                                f"{py_file.relative_to(ROOT)}: references {json_file} with write operations"
                            )
                            break

            except Exception as e:
                print(f"Warning: Could not read {py_file}: {e}")

        self.assertEqual(
            offenders,
            [],
            f"JSON state files must not be used at runtime, found usage in:\n"
            + "\n".join(f"  - {o}" for o in offenders),
        )

    def test_contracts_present(self):
        """
        Test that core contracts are defined and available.
        """
        try:
            core_contracts = importlib.import_module("janus.core.contracts")
        except ImportError as e:
            self.fail(f"Cannot import janus.core.contracts: {e}")

        required_contracts = [
            "Intent",
            "ActionPlan",
            "ActionResult",
            "ExecutionResult",
            "CommandError",
        ]

        for contract_name in required_contracts:
            with self.subTest(contract=contract_name):
                self.assertTrue(
                    hasattr(core_contracts, contract_name), f"Missing contract: {contract_name}"
                )

    def test_pipeline_api_complete(self):
        """
        Test that JanusPipeline has the required API methods.
        """
        try:
            pipeline_module = importlib.import_module("janus.core.pipeline")
        except ImportError as e:
            self.fail(f"Cannot import janus.core.pipeline: {e}")

        self.assertTrue(
            hasattr(pipeline_module, "JanusPipeline"), "Missing JanusPipeline class"
        )

        pipeline_class = getattr(pipeline_module, "JanusPipeline")

        required_methods = ["process_command", "cleanup"]

        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(pipeline_class, method_name),
                    f"JanusPipeline missing method: {method_name}",
                )


if __name__ == "__main__":
    unittest.main()
