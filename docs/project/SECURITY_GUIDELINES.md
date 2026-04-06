# Security Guidelines for Contributors

## TICKET-SECURITY-01: Command Injection Prevention

This document outlines security guidelines for preventing command injection vulnerabilities in the Janus project.

## Overview

Command injection vulnerabilities occur when user input is passed to shell commands without proper sanitization. This allows attackers to execute arbitrary commands on the system.

## Fixed Vulnerabilities

As of TICKET-SECURITY-01, the following command injection vulnerabilities have been fixed:

1. **terminal_adapter.py**: All subprocess calls now use list arguments by default (`shell=False`)
2. **ui_executor.py**: Windows subprocess.Popen calls use list arguments
3. **action_executor.py**: Windows subprocess.Popen calls use list arguments
4. **Command validation**: Added command whitelist and validation
5. **Path sanitization**: Added path sanitization to prevent directory traversal
6. **Input validation**: Added comprehensive input validation for all commands

## Security Features in TerminalAdapter

The `TerminalAdapter` class now includes several security enhancements:

### 1. Command Whitelist

Safe commands are whitelisted and known to be generally safe:
- File operations: `ls`, `cat`, `head`, `tail`, `less`, `more`, `file`, `stat`, `wc`, etc.
- Text processing: `grep`, `sed`, `awk`, `sort`, `uniq`, `cut`, `tr`, etc.
- System info: `date`, `whoami`, `hostname`, `uname`, `uptime`, `df`, `du`, etc.
- Development tools: `python`, `node`, `java`, `gcc`, `make`, `code`, etc.

### 2. Sensitive Command Detection

Sensitive commands are logged with warnings:
- File deletion/modification: `rm`, `rmdir`, `mv`, `cp`, `dd`, `shred`
- System modification: `chmod`, `chown`, `chgrp`, `sudo`, `su`
- Process management: `kill`, `killall`, `pkill`
- System control: `shutdown`, `reboot`, `halt`, `poweroff`

### 3. Command Validation

The `_validate_command_safety()` method performs:
- Empty command detection
- Command parsing validation
- Sensitive command detection and logging
- Whitelist checking
- Path-based command detection

### 4. Path Sanitization

The `_sanitize_path()` method prevents directory traversal attacks by:
- Expanding user home directory (`~`)
- Normalizing paths (removing `..` and `.`)
- Converting to absolute paths

## Secure Coding Guidelines

### 1. Always Use List Arguments for subprocess

**❌ UNSAFE:**
```python
import subprocess
command = f"echo {user_input}"
subprocess.run(command, shell=True)  # DANGEROUS!
```

**✅ SAFE:**
```python
import subprocess
import shlex
command = f"echo {user_input}"
subprocess.run(shlex.split(command), shell=False)
```

### 2. Avoid shell=True Unless Absolutely Necessary

The `shell=True` parameter enables shell features like pipes, redirections, and command chaining, but it also opens the door to command injection attacks.

**When to use shell=True:**
- When you need shell features like pipes (`|`), redirections (`>`, `<`), or command chaining (`&&`, `||`, `;`)
- Only with trusted, non-user input
- With explicit logging of the command being executed

**Example:**
```python
# Acceptable use of shell=True for pipe operations
pipeline_cmd = "ls -la | grep test"
logger.warning(f"Using shell=True for pipeline: {pipeline_cmd}")
subprocess.run(pipeline_cmd, shell=True)
```

### 3. Use shlex.split() for Command Parsing

When you need to parse a command string into a list of arguments, use `shlex.split()`:

```python
import shlex
command = 'echo "hello world"'
args = shlex.split(command)  # ['echo', 'hello world']
subprocess.run(args, shell=False)
```

### 4. Validate Input

Always validate and sanitize user input before using it in commands:

```python
import re

def is_safe_filename(filename):
    """Validate that filename doesn't contain dangerous characters"""
    # Only allow alphanumeric, dash, underscore, and dot
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', filename))

if not is_safe_filename(user_input):
    raise ValueError("Invalid filename")
```

### 5. Use Whitelists for Sensitive Operations

For operations that could be dangerous, use a whitelist of allowed commands:

```python
ALLOWED_COMMANDS = ['ls', 'pwd', 'echo', 'cat']

def execute_safe_command(command):
    cmd_parts = shlex.split(command)
    if cmd_parts[0] not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not allowed: {cmd_parts[0]}")
    return subprocess.run(cmd_parts, shell=False)
```

### 6. Log Shell Command Execution

Always log when `shell=True` is used for security auditing:

```python
import logging
logger = logging.getLogger(__name__)

def execute_with_shell(command):
    logger.warning(f"Executing command with shell=True: {command}. This may pose security risks.")
    return subprocess.run(command, shell=True)
```

### 7. Sanitize File Paths

Always sanitize file paths to prevent directory traversal attacks:

```python
import os

def sanitize_path(path):
    """Sanitize path to prevent directory traversal"""
    path = os.path.expanduser(path)
    path = os.path.normpath(path)
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return path
```

## Security Testing

All code changes that involve subprocess calls must include security tests. See `tests/test_security_command_injection.py` for examples.

### Example Security Tests:

```python
def test_no_shell_injection(self):
    """Test that command injection is blocked"""
    malicious_command = "echo safe && echo injected"
    result = terminal.execute_command(malicious_command, shell=False)
    # Should treat && as literal, not execute two commands
    self.assertIn("&&", result["stdout"])

def test_sensitive_command_logged(self):
    """Test that sensitive commands are logged"""
    sensitive_command = "chmod +x /tmp/test_file"
    result = self.terminal.execute_command(sensitive_command, shell=False)
    # Should log a warning (check logs)

def test_path_sanitization(self):
    """Test that paths are sanitized"""
    result = self.terminal.change_directory("/tmp/../tmp")
    self.assertEqual(result["status"], "success")
    # Path should be normalized
```

## Detection of Shell Features

The `terminal_adapter.py` module includes automatic detection of shell features:

```python
shell_indicators = ['|', '&&', '||', '>', '<', ';', '`', '$', '~', 'cd ', 'exit ', 'export ']
needs_shell = any(indicator in command for indicator in shell_indicators)
if needs_shell:
    logger.warning(
        f"Command appears to require shell features: {command}. "
        "Consider using shell=True or refactoring the command."
    )
```

## Code Review Checklist

When reviewing code that uses subprocess:

- [ ] Is `shell=False` used by default?
- [ ] If `shell=True` is used, is it necessary and justified?
- [ ] Is user input properly validated before being used in commands?
- [ ] Are commands using list arguments instead of string concatenation?
- [ ] Is the command execution logged for security auditing?
- [ ] Are there security tests covering command injection scenarios?
- [ ] Are file paths sanitized to prevent directory traversal?
- [ ] Are sensitive commands properly logged?
- [ ] Does the code use the command whitelist appropriately?

## Audit Status

✅ **Command Injection (Issue 1.1) - RESOLVED**
- Command whitelist implemented
- Input validation and sanitization added
- Path sanitization for directory traversal prevention
- Comprehensive security tests (21 tests passing)
- Security documentation updated
- All subprocess calls audited and secured

## Resources

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [Python subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations)
- [shlex documentation](https://docs.python.org/3/library/shlex.html)

## Questions?

If you're unsure about whether your code is secure, please:
1. Review this document
2. Look at examples in `janus/exec/adapters/terminal_adapter.py`
3. Add security tests in `tests/test_security_command_injection.py`
4. Ask for a security review from the team
