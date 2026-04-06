"""
Test i18n JSON key consistency - Vigilance Point #1

This test ensures that all i18n keys used in the codebase exist in the JSON files.
It prevents runtime errors from typos in i18n key names.

TICKET: QA Vigilance Points ("Punchlist") - Point 1
"""

import ast
import json
import pytest
from pathlib import Path
from typing import Set, Dict, List, Tuple

# Supported languages for validation
SUPPORTED_LANGUAGES = ["fr", "en"]


class I18NKeyVisitor(ast.NodeVisitor):
    """AST visitor to find i18n key usage in Python code."""
    
    def __init__(self):
        self.keys_found: List[Tuple[str, str, int]] = []  # (key, filename, line_number)
        self.has_i18n_import = False
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track if file imports i18n modules."""
        if node.module and "i18n" in node.module:
            self.has_i18n_import = True
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Visit function calls to find get_message() and loader.get() calls."""
        # Check for get_message(key, ...)
        if isinstance(node.func, ast.Name) and node.func.id == "get_message":
            if node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
                if isinstance(key, str):
                    self.keys_found.append((key, "", node.lineno))
        
        # Check for loader.get(key, ...) where loader is an i18n loader
        # Only check if file has i18n imports
        elif self.has_i18n_import and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            # Check if called on something with 'loader' or 'i18n' in name
            if isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                if "loader" in var_name.lower() or "i18n" in var_name.lower():
                    if node.args and isinstance(node.args[0], ast.Constant):
                        key = node.args[0].value
                        if isinstance(key, str) and "." in key:  # i18n keys typically have dots
                            self.keys_found.append((key, "", node.lineno))
        
        self.generic_visit(node)


def find_i18n_keys_in_file(file_path: Path) -> List[Tuple[str, str, int]]:
    """Find all i18n keys used in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        visitor = I18NKeyVisitor()
        visitor.visit(tree)
        
        # Add filename to each key
        return [(key, str(file_path), line) for key, _, line in visitor.keys_found]
    except (SyntaxError, UnicodeDecodeError) as e:
        # Skip files that can't be parsed
        return []


def find_all_i18n_keys_in_codebase(base_path: Path) -> List[Tuple[str, str, int]]:
    """Find all i18n keys used in the entire codebase."""
    all_keys = []
    
    # Search in janus directory
    janus_dir = base_path / "janus"
    if janus_dir.exists():
        for py_file in janus_dir.rglob("*.py"):
            keys = find_i18n_keys_in_file(py_file)
            all_keys.extend(keys)
    
    return all_keys


def load_json_keys(json_file: Path) -> Set[str]:
    """Load all keys from a JSON file, supporting nested structure."""
    if not json_file.exists():
        return set()
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    def extract_keys(obj, prefix=""):
        """Recursively extract all keys from nested dict."""
        keys = set()
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                if isinstance(value, dict) and not all(k in ["fr", "en"] for k in value.keys()):
                    # If it's not a language dict, recurse
                    keys.update(extract_keys(value, full_key))
        return keys
    
    return extract_keys(data)


@pytest.fixture
def repo_root():
    """Get repository root path."""
    return Path(__file__).parent.parent


@pytest.fixture
def system_messages_path(repo_root):
    """Get path to system_messages.json."""
    return repo_root / "janus" / "resources" / "i18n" / "system_messages.json"


@pytest.fixture
def available_keys(system_messages_path):
    """Get all available i18n keys from JSON files."""
    return load_json_keys(system_messages_path)


def test_i18n_keys_exist(repo_root, available_keys):
    """
    Test that all i18n keys used in code exist in JSON files.
    
    This is Vigilance Point #1: Ensure no typos in i18n keys.
    """
    # Find all keys used in codebase
    used_keys = find_all_i18n_keys_in_codebase(repo_root)
    
    # Check each used key exists
    missing_keys = []
    for key, file_path, line_num in used_keys:
        if key not in available_keys:
            missing_keys.append((key, file_path, line_num))
    
    # Report results
    if missing_keys:
        error_msg = "Missing i18n keys found:\n"
        for key, file_path, line_num in missing_keys:
            # Make path relative for readability
            rel_path = Path(file_path).relative_to(repo_root) if repo_root in Path(file_path).parents else file_path
            error_msg += f"  - '{key}' used in {rel_path}:{line_num}\n"
        error_msg += f"\nAvailable keys: {sorted(available_keys)}"
        pytest.fail(error_msg)


def test_json_files_are_valid(system_messages_path):
    """Test that JSON files are valid and can be loaded."""
    assert system_messages_path.exists(), f"system_messages.json not found at {system_messages_path}"
    
    with open(system_messages_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert isinstance(data, dict), "system_messages.json must be a dictionary"
    assert len(data) > 0, "system_messages.json is empty"


def test_all_keys_have_both_languages(system_messages_path):
    """Test that all message keys have both French and English translations."""
    with open(system_messages_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    def check_translations(obj, path=""):
        """Recursively check that all leaf nodes have both fr and en."""
        issues = []
        if isinstance(obj, dict):
            # Check if this is a language dict (has 'fr' or 'en')
            if any(k in SUPPORTED_LANGUAGES for k in obj.keys()):
                # This should be a complete language dict
                for lang in SUPPORTED_LANGUAGES:
                    if lang not in obj:
                        issues.append(f"{path}: missing '{lang}' translation")
            else:
                # Recurse into nested structure
                for key, value in obj.items():
                    full_path = f"{path}.{key}" if path else key
                    issues.extend(check_translations(value, full_path))
        return issues
    
    issues = check_translations(data)
    if issues:
        pytest.fail("Translation issues found:\n" + "\n".join(f"  - {issue}" for issue in issues))


def test_i18n_loader_functionality(system_messages_path):
    """Test that the I18NLoader can load and retrieve messages."""
    from janus.i18n.i18n_loader import I18NLoader
    
    loader = I18NLoader()
    
    # Test getting a known message
    msg_fr = loader.get("verification.goal_achieved", language="fr")
    msg_en = loader.get("verification.goal_achieved", language="en")
    
    assert msg_fr, "French message should not be empty"
    assert msg_en, "English message should not be empty"
    assert msg_fr != msg_en, "French and English messages should be different"
    
    # Test getting a non-existent key returns error message
    missing_msg = loader.get("nonexistent.key.that.does.not.exist", language="fr")
    assert "[Missing message:" in missing_msg, "Should return error message for missing key"


def test_no_hardcoded_strings_in_critical_files(repo_root):
    """
    Test that critical files don't have hardcoded user-facing strings.
    
    This is a soft check - we look for suspicious patterns but don't fail hard.
    """
    critical_files = [
        repo_root / "janus" / "vision" / "vision_cognitive_engine.py",
        repo_root / "janus" / "core" / "agent_executor_v3.py",
    ]
    
    suspicious_patterns = []
    
    for file_path in critical_files:
        if not file_path.exists():
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            # Look for French user-facing messages (common pattern: strings with "é", "à", etc.)
            if any(char in line for char in ["'", '"']) and any(char in line for char in ["é", "à", "è", "ê", "ç", "ô"]):
                # Check if it's not in a comment
                if "#" not in line or line.index("#") > line.index('"'):
                    rel_path = file_path.relative_to(repo_root)
                    suspicious_patterns.append(f"{rel_path}:{i}: {line.strip()[:80]}")
    
    # This is informational - we don't fail the test but log warnings
    if suspicious_patterns:
        print("\n⚠️  Potentially hardcoded French strings found (should use i18n):")
        for pattern in suspicious_patterns[:10]:  # Show first 10
            print(f"  {pattern}")


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])
