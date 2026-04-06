#!/usr/bin/env python3
"""
Pre-commit hook to detect forbidden patterns (magic strings) in Python code.

TICKET-ARCH-FINAL: Zero Magic String & Complete Internationalization

This script scans Python files for:
- Hardcoded language-specific keywords in logic (not UI text)
- Hardcoded selector patterns with language-specific text
- Suspicious response lists that should be in locale files

Usage:
    python scripts/check_magic_strings.py [--fix]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Forbidden patterns (regex) - more specific to avoid false positives
FORBIDDEN_PATTERNS = [
    # Hardcoded response lists for logic (the key issue)
    (r'(positive_responses|negative_responses|confirmation_words)\s*=\s*\[[^\]]*(?:YES|OUI|NO|NON)[^\]]*\]',
     "Hardcoded response list detected. Use locale_loader.get_keywords() instead."),
    
    # Hardcoded error keywords lists
    (r'error_keywords\s*=\s*\[[^\]]*(?:error|exception|fail)[^\]]*\]',
     "Hardcoded error keywords list detected. Use LLM classification instead."),
    
    # Hardcoded CSS selectors with language-specific placeholder text
    (r'input\[placeholder\*=["\'][^"\']*(?:Search|Recherch)[^"\']*["\']',
     "Hardcoded language-specific selector detected. Use locale_loader.get_selectors() instead."),
    
    (r'\[aria-label\*=["\'][^"\']*(?:Search|Recherch)[^"\']*["\']',
     "Hardcoded language-specific ARIA label detected. Use locale configuration instead."),
    
    # Lists of language-specific words used in logic
    (r'(?:popup_keywords|button_keywords|action_words)\s*=\s*\[[^\]]*["\'](?:ok|cancel|yes|no)["\'][^\]]*\]',
     "Hardcoded keyword list detected. Use locale configuration instead."),
]

# Files/directories to exclude from checking
EXCLUDE_PATTERNS = [
    "test_",  # Test files
    "__pycache__",
    ".pyc",
    "venv/",
    "env/",
    ".git/",
    "locale_loader.py",  # The loader itself is allowed to have references
    "i18n/__init__.py",  # i18n module defines the translations
    "check_magic_strings.py",  # This script
    "/ui/",  # UI files can have button text
    "settings.py",  # Settings parsing is OK
    "json_plan_corrector.py",  # JSON fixing is OK
    "correction_dialog.py",  # UI dialog is OK
]

# Exceptions: Lines that are allowed despite matching patterns
ALLOWED_CONTEXTS = [
    "# NOTE: These keywords parse the LLM's structured response",
    "TRANSLATIONS",  # In i18n module
    "MESSAGES",  # In i18n module
    '"fr"',  # Language codes
    '"en"',  # Language codes
    "text=",  # UI text assignment
    "label=",  # UI label assignment
    "return",  # Return statements
    "JSON",  # JSON-related
    "boolean",  # Boolean values
]


def should_exclude_file(filepath: Path) -> bool:
    """Check if file should be excluded from checking."""
    path_str = str(filepath)
    return any(pattern in path_str for pattern in EXCLUDE_PATTERNS)


def check_line_allowed(line: str, line_num: int) -> bool:
    """Check if a line is allowed despite matching a forbidden pattern."""
    # Check for allowed contexts
    if any(context in line for context in ALLOWED_CONTEXTS):
        return True
    
    # Comments are generally allowed
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    
    # JSON boolean values are OK
    if re.search(r'["\'](?:true|false)["\']', line, re.IGNORECASE):
        return True
    
    # Configuration values and method parameters are usually OK
    if "=" in line and not re.search(r'\s*=\s*\[', line):
        return True
    
    # Fallback assignments after locale loading are OK
    if "# Fallback" in line or "fallback" in line.lower():
        return True
    
    return False


def check_file(filepath: Path, verbose: bool = False) -> List[Tuple[int, str, str]]:
    """
    Check a Python file for forbidden patterns.
    
    Returns:
        List of (line_number, line_content, violation_message) tuples
    """
    violations = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return violations
    
    for line_num, line in enumerate(lines, start=1):
        # Check context (lines before and after) for fallback indicators
        context_before = ""
        if line_num > 1:
            context_before = lines[line_num - 2]
        if line_num > 2:
            context_before += lines[line_num - 3]
        
        # Skip if line is allowed
        if check_line_allowed(line, line_num):
            continue
        
        # Skip if context indicates this is a fallback
        if "fallback" in context_before.lower():
            continue
        
        # Check each forbidden pattern
        for pattern, message in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((line_num, line.strip(), message))
                if verbose:
                    print(f"  Line {line_num}: {message}")
    
    return violations


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check for magic strings in Python code")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--path", default="janus", help="Path to check (default: janus)")
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent.parent
    check_path = repo_root / args.path
    
    if not check_path.exists():
        print(f"Error: Path {check_path} does not exist", file=sys.stderr)
        return 1
    
    print(f"🔍 Scanning for magic strings in {check_path}...")
    print(f"{'='*60}")
    
    total_violations = 0
    files_with_violations = 0
    
    # Find all Python files
    py_files = list(check_path.rglob("*.py"))
    
    for py_file in py_files:
        if should_exclude_file(py_file):
            continue
        
        violations = check_file(py_file, verbose=args.verbose)
        
        if violations:
            files_with_violations += 1
            total_violations += len(violations)
            
            print(f"\n❌ {py_file.relative_to(repo_root)}")
            for line_num, line_content, message in violations:
                print(f"  Line {line_num}: {message}")
                print(f"    {line_content}")
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"  Files checked: {len(py_files)}")
    print(f"  Files with violations: {files_with_violations}")
    print(f"  Total violations: {total_violations}")
    
    if total_violations > 0:
        print(f"\n❌ Found {total_violations} magic string violations!")
        print(f"\n💡 To fix:")
        print(f"  1. Move hardcoded strings to janus/resources/locales/[fr|en].json")
        print(f"  2. Use locale_loader.get_keywords() or locale_loader.get_selectors()")
        print(f"  3. Use Jinja2 templates for prompts")
        return 1
    else:
        print(f"\n✅ No magic strings detected! Code is clean.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
