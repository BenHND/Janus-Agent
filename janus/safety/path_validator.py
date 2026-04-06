"""
Path Validator - Security module for path traversal prevention

TICKET-SECURITY-001: Validates file paths to prevent:
- Path traversal attacks (../)
- Access to sensitive system directories
- Symbolic link attacks
- Null byte injection
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails"""
    pass


class PathValidator:
    r"""
    Validates file paths for security.
    
    Features:
    - Path traversal detection (.., symlinks)
    - Sensitive directory blocking (/etc, /System, C:\Windows)
    - Whitelist/blacklist support
    - Null byte detection
    - Path normalization
    """
    
    # Sensitive directories that should never be accessed
    SENSITIVE_DIRS_UNIX = {
        "/etc", "/private/etc",  # System config
        "/System", "/Library/LaunchDaemons", "/Library/LaunchAgents",  # macOS system
        "/usr/bin", "/usr/sbin", "/bin", "/sbin",  # System binaries
        "/var/log", "/var/run",  # System logs/runtime
        "/root", "/private/var/root",  # Root home
        "/.ssh", "/.gnupg", "/.aws", "/.config/gcloud",  # Credentials
    }
    
    SENSITIVE_DIRS_WINDOWS = {
        "C:\\Windows", "C:\\Windows\\System32",
        "C:\\Program Files", "C:\\Program Files (x86)",
        "C:\\Users\\Default",
        "C:\\ProgramData",
    }
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r"\.\.",  # Parent directory traversal
        r"\x00",  # Null byte injection
        r"^~root",  # Root home expansion
        r"^/dev/",  # Device files
        r"^/proc/",  # Process filesystem
        r"^/sys/",  # Kernel filesystem
    ]
    
    def __init__(
        self,
        allowed_base_dirs: Optional[List[str]] = None,
        blocked_extensions: Optional[Set[str]] = None,
        allow_symlinks: bool = False,
        max_path_length: int = 4096,
    ):
        """
        Initialize PathValidator.
        
        Args:
            allowed_base_dirs: If set, paths must be under one of these directories
            blocked_extensions: File extensions to block (e.g., {'.exe', '.sh'})
            allow_symlinks: Whether to allow symbolic links
            max_path_length: Maximum allowed path length
        """
        self.allowed_base_dirs = allowed_base_dirs
        self.blocked_extensions = blocked_extensions or set()
        self.allow_symlinks = allow_symlinks
        self.max_path_length = max_path_length
        
        # Compile dangerous patterns
        self._dangerous_re = re.compile(
            "|".join(self.DANGEROUS_PATTERNS),
            re.IGNORECASE
        )
        
        # Determine platform
        self._is_windows = os.name == "nt"
        self._sensitive_dirs = (
            self.SENSITIVE_DIRS_WINDOWS if self._is_windows 
            else self.SENSITIVE_DIRS_UNIX
        )
    
    def validate(self, path: str, operation: str = "access") -> Path:
        """
        Validate a path for security.
        
        Args:
            path: Path to validate
            operation: Operation type for logging ("read", "write", "delete", etc.)
        
        Returns:
            Validated and normalized Path object
        
        Raises:
            PathValidationError: If validation fails
        """
        if not path:
            raise PathValidationError("Empty path provided")
        
        # Check length
        if len(path) > self.max_path_length:
            raise PathValidationError(
                f"Path exceeds maximum length ({len(path)} > {self.max_path_length})"
            )
        
        # Check for dangerous patterns BEFORE normalization
        if self._dangerous_re.search(path):
            logger.warning(f"SECURITY: Blocked dangerous path pattern: {path[:100]}")
            raise PathValidationError(
                f"Path contains dangerous pattern (path traversal or injection attempt)"
            )
        
        # Normalize path
        try:
            normalized = Path(path).resolve()
        except Exception as e:
            raise PathValidationError(f"Invalid path format: {e}")
        
        normalized_str = str(normalized)
        
        # Check for sensitive directories
        for sensitive_dir in self._sensitive_dirs:
            if normalized_str.startswith(sensitive_dir):
                logger.warning(
                    f"SECURITY: Blocked access to sensitive directory: {normalized_str[:100]}"
                )
                raise PathValidationError(
                    f"Access to sensitive system directory is not allowed"
                )
        
        # Check symlinks
        if not self.allow_symlinks and normalized.is_symlink():
            raise PathValidationError("Symbolic links are not allowed")
        
        # Check allowed base directories (whitelist mode)
        if self.allowed_base_dirs:
            is_allowed = any(
                normalized_str.startswith(str(Path(base).resolve()))
                for base in self.allowed_base_dirs
            )
            if not is_allowed:
                raise PathValidationError(
                    f"Path is not under allowed directories"
                )
        
        # Check blocked extensions
        if self.blocked_extensions:
            ext = normalized.suffix.lower()
            if ext in self.blocked_extensions:
                raise PathValidationError(
                    f"File extension '{ext}' is not allowed"
                )
        
        logger.debug(f"Path validated for {operation}: {normalized_str[:100]}")
        return normalized
    
    def is_safe(self, path: str) -> bool:
        """
        Check if path is safe without raising exception.
        
        Args:
            path: Path to check
        
        Returns:
            True if safe, False otherwise
        """
        try:
            self.validate(path)
            return True
        except PathValidationError:
            return False
    
    def sanitize(self, path: str) -> str:
        """
        Attempt to sanitize a path by removing dangerous elements.
        
        WARNING: This is a best-effort sanitization. Always prefer
        validation and rejection over sanitization.
        
        Args:
            path: Path to sanitize
        
        Returns:
            Sanitized path string
        """
        # Remove null bytes
        sanitized = path.replace("\x00", "")
        
        # Remove parent directory references
        # Note: This is NOT secure for all cases, validation is preferred
        sanitized = sanitized.replace("..", "")
        
        # Normalize slashes
        sanitized = sanitized.replace("\\", "/")
        
        # Remove duplicate slashes
        while "//" in sanitized:
            sanitized = sanitized.replace("//", "/")
        
        return sanitized


# Global validator instance with safe defaults
_default_validator = None


def get_path_validator() -> PathValidator:
    """Get or create default path validator"""
    global _default_validator
    if _default_validator is None:
        # Get user home directory as allowed base
        home = str(Path.home())
        
        # Get platform-specific temporary directory
        import tempfile
        temp_dirs = [home]  # Always allow user home
        
        if os.name == "nt":
            # Windows temp directories
            temp_dir = tempfile.gettempdir()
            if temp_dir:
                temp_dirs.append(temp_dir)
        else:
            # Unix-like systems
            temp_dirs.extend(["/tmp", "/var/tmp"])
        
        _default_validator = PathValidator(
            allowed_base_dirs=temp_dirs,
            blocked_extensions={
                ".exe", ".bat", ".cmd", ".ps1",  # Windows executables
                ".sh", ".bash",  # Shell scripts
                ".plist",  # macOS config
            },
            allow_symlinks=False,
        )
    return _default_validator


def validate_path(path: str, operation: str = "access") -> Path:
    """
    Convenience function to validate a path.
    
    Args:
        path: Path to validate
        operation: Operation type for logging
    
    Returns:
        Validated Path object
    
    Raises:
        PathValidationError: If validation fails
    """
    return get_path_validator().validate(path, operation)
