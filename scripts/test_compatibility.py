#!/usr/bin/env python3
"""
Automated macOS compatibility testing script
Ticket 11.3: Test on multiple macOS versions
"""
import json
import platform
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List


class MacOSCompatibilityTest:
    """Automated compatibility testing for macOS"""

    def __init__(self):
        """Initialize test suite"""
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "tests": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            },
        }

    def run_command(self, cmd: List[str], timeout: int = 30) -> tuple:
        """Run a shell command and return output"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def test_system_info(self):
        """Test: Collect system information"""
        print("Testing: System Information...")

        test_result = {"name": "System Information", "status": "pass", "data": {}}

        try:
            # Get macOS version
            returncode, stdout, _ = self.run_command(["sw_vers"])
            if returncode == 0:
                for line in stdout.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        test_result["data"][key.strip()] = value.strip()

            # Get hardware info
            test_result["data"]["machine"] = platform.machine()
            test_result["data"]["processor"] = platform.processor()

            # Store in results
            self.results["system"] = test_result["data"]

            print(f"  ✓ System info collected")
            self.results["summary"]["passed"] += 1

        except Exception as e:
            test_result["status"] = "fail"
            test_result["error"] = str(e)
            print(f"  ✗ Failed: {e}")
            self.results["summary"]["failed"] += 1

        self.results["tests"].append(test_result)

    def test_python_version(self):
        """Test: Check Python version"""
        print("Testing: Python Version...")

        test_result = {"name": "Python Version", "status": "pass", "data": {}}

        try:
            version = sys.version_info
            test_result["data"]["version"] = f"{version.major}.{version.minor}.{version.micro}"
            test_result["data"]["implementation"] = platform.python_implementation()

            if version.major >= 3 and version.minor >= 8:
                print(f"  ✓ Python {version.major}.{version.minor}.{version.micro} (OK)")
                self.results["summary"]["passed"] += 1
            else:
                test_result["status"] = "fail"
                test_result["error"] = "Python 3.8+ required"
                print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (Too old)")
                self.results["summary"]["failed"] += 1

        except Exception as e:
            test_result["status"] = "fail"
            test_result["error"] = str(e)
            print(f"  ✗ Failed: {e}")
            self.results["summary"]["failed"] += 1

        self.results["tests"].append(test_result)

    def test_required_modules(self):
        """Test: Check required Python modules"""
        print("Testing: Required Modules...")

        required = [
            "numpy",
            "pyautogui",
            "pyperclip",
            "PIL",
            "pynput",
        ]

        test_result = {"name": "Required Modules", "status": "pass", "data": {"modules": {}}}

        failed_modules = []

        for module in required:
            try:
                __import__(module)
                test_result["data"]["modules"][module] = "installed"
                print(f"  ✓ {module}")
            except ImportError:
                test_result["data"]["modules"][module] = "missing"
                failed_modules.append(module)
                print(f"  ✗ {module} (missing)")

        if failed_modules:
            test_result["status"] = "fail"
            test_result["error"] = f"Missing modules: {', '.join(failed_modules)}"
            self.results["summary"]["failed"] += 1
        else:
            self.results["summary"]["passed"] += 1

        self.results["tests"].append(test_result)

    def test_optional_modules(self):
        """Test: Check optional Python modules"""
        print("Testing: Optional Modules...")

        optional = {
            "pytesseract": "OCR support",
            "openai": "LLM integration",
            "psutil": "Performance monitoring",
        }

        test_result = {"name": "Optional Modules", "status": "pass", "data": {"modules": {}}}

        missing = []

        for module, description in optional.items():
            try:
                __import__(module)
                test_result["data"]["modules"][module] = {
                    "status": "installed",
                    "description": description,
                }
                print(f"  ✓ {module} ({description})")
            except ImportError:
                test_result["data"]["modules"][module] = {
                    "status": "missing",
                    "description": description,
                }
                missing.append(module)
                print(f"  ⚠ {module} (optional - {description})")

        if missing:
            test_result["status"] = "warning"
            test_result["warning"] = f"Optional modules not installed: {', '.join(missing)}"
            self.results["summary"]["warnings"] += 1
        else:
            self.results["summary"]["passed"] += 1

        self.results["tests"].append(test_result)

    def test_system_commands(self):
        """Test: Check system commands"""
        print("Testing: System Commands...")

        commands = {
            "osascript": "AppleScript execution",
            "which": "Command location",
        }

        test_result = {"name": "System Commands", "status": "pass", "data": {"commands": {}}}

        for cmd, description in commands.items():
            returncode, stdout, _ = self.run_command(["which", cmd])
            if returncode == 0:
                test_result["data"]["commands"][cmd] = {
                    "available": True,
                    "path": stdout.strip(),
                    "description": description,
                }
                print(f"  ✓ {cmd} ({description})")
            else:
                test_result["data"]["commands"][cmd] = {
                    "available": False,
                    "description": description,
                }
                print(f"  ✗ {cmd} (missing)")

        self.results["summary"]["passed"] += 1
        self.results["tests"].append(test_result)

    def test_janus_modules(self):
        """Test: Import Janus modules"""
        print("Testing: Janus Modules...")

        modules = [
            "janus.stt",
            "janus.parser",
            "janus.automation",
            "janus.memory",
            "janus.logging",
        ]

        test_result = {"name": "Janus Modules", "status": "pass", "data": {"modules": {}}}

        failed = []

        for module in modules:
            try:
                __import__(module)
                test_result["data"]["modules"][module] = "ok"
                print(f"  ✓ {module}")
            except Exception as e:
                test_result["data"]["modules"][module] = f"error: {str(e)}"
                failed.append(module)
                print(f"  ✗ {module}: {e}")

        if failed:
            test_result["status"] = "fail"
            test_result["error"] = f"Failed to import: {', '.join(failed)}"
            self.results["summary"]["failed"] += 1
        else:
            self.results["summary"]["passed"] += 1

        self.results["tests"].append(test_result)

    def run_all_tests(self):
        """Run all compatibility tests"""
        print("=" * 60)
        print("Janus Automated Compatibility Tests")
        print("=" * 60)
        print()

        self.test_system_info()
        print()

        self.test_python_version()
        print()

        self.test_required_modules()
        print()

        self.test_optional_modules()
        print()

        self.test_system_commands()
        print()

        self.test_janus_modules()
        print()

        print("=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Passed:   {self.results['summary']['passed']}")
        print(f"Failed:   {self.results['summary']['failed']}")
        print(f"Warnings: {self.results['summary']['warnings']}")
        print()

        if self.results["summary"]["failed"] == 0:
            print("✓ All tests passed!")
            return 0
        else:
            print("✗ Some tests failed")
            return 1

    def save_results(self, output_file: str = "compatibility_test_results.json"):
        """Save test results to file"""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point"""
    tester = MacOSCompatibilityTest()
    exit_code = tester.run_all_tests()
    tester.save_results()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
