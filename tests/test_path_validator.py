"""
Unit tests for PathValidator

Tests security features:
- Path traversal detection
- Sensitive directory blocking
- Null byte injection detection
- Whitelist/blacklist enforcement
"""

import os
import tempfile
from pathlib import Path
import pytest

from janus.safety.path_validator import PathValidator, PathValidationError, validate_path


class TestPathValidator:
    """Test cases for PathValidator"""

    def test_blocks_path_traversal_parent_dir(self):
        """Test that parent directory traversal is blocked"""
        validator = PathValidator()
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("../../../etc/passwd")
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("/home/user/../../../etc/shadow")
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("./../../etc/hosts")

    def test_blocks_sensitive_directories_unix(self):
        """Test that access to sensitive Unix directories is blocked"""
        validator = PathValidator()
        
        # Skip on Windows
        if os.name == "nt":
            pytest.skip("Unix-specific test")
        
        with pytest.raises(PathValidationError, match="sensitive system directory"):
            validator.validate("/etc/passwd")
        
        with pytest.raises(PathValidationError, match="sensitive system directory"):
            validator.validate("/System/Library/LaunchDaemons/evil.plist")
        
        with pytest.raises(PathValidationError, match="sensitive system directory"):
            validator.validate("/usr/bin/sudo")

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked"""
        validator = PathValidator()
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("/home/user/file.txt\x00.jpg")
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("test\x00/path")

    def test_blocks_dev_proc_sys_access(self):
        """Test that device files and kernel filesystems are blocked"""
        validator = PathValidator()
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("/dev/null")
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("/proc/self/mem")
        
        with pytest.raises(PathValidationError, match="dangerous pattern"):
            validator.validate("/sys/kernel/debug")

    def test_allows_safe_paths_under_home(self):
        """Test that safe paths under user home are allowed"""
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home])
        
        # Create a temp file in home for testing
        with tempfile.NamedTemporaryFile(dir=home, delete=False, suffix=".txt") as f:
            temp_path = f.name
        
        try:
            # This should succeed
            result = validator.validate(temp_path)
            assert isinstance(result, Path)
            assert str(result) == str(Path(temp_path).resolve())
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_allows_tmp_directory(self):
        """Test that /tmp is accessible when whitelisted"""
        validator = PathValidator(allowed_base_dirs=["/tmp"])
        
        # Skip on Windows (different temp structure)
        if os.name == "nt":
            pytest.skip("Unix-specific test")
        
        # This should succeed
        result = validator.validate("/tmp/test.txt")
        assert isinstance(result, Path)

    def test_blocks_paths_outside_whitelist(self):
        """Test that paths outside whitelist are blocked"""
        validator = PathValidator(allowed_base_dirs=["/home/testuser"])
        
        with pytest.raises(PathValidationError, match="not under allowed directories"):
            validator.validate("/home/otheruser/file.txt")

    def test_blocks_dangerous_extensions(self):
        """Test that dangerous file extensions are blocked"""
        home = str(Path.home())
        validator = PathValidator(
            allowed_base_dirs=[home],
            blocked_extensions={".exe", ".sh", ".bat"}
        )
        
        with pytest.raises(PathValidationError, match="extension.*not allowed"):
            validator.validate(f"{home}/malware.exe")
        
        with pytest.raises(PathValidationError, match="extension.*not allowed"):
            validator.validate(f"{home}/script.sh")

    def test_rejects_empty_path(self):
        """Test that empty paths are rejected"""
        validator = PathValidator()
        
        with pytest.raises(PathValidationError, match="Empty path"):
            validator.validate("")

    def test_rejects_too_long_path(self):
        """Test that overly long paths are rejected"""
        validator = PathValidator(max_path_length=100)
        
        long_path = "/home/" + "a" * 200
        with pytest.raises(PathValidationError, match="exceeds maximum length"):
            validator.validate(long_path)

    def test_is_safe_method(self):
        """Test the is_safe convenience method"""
        validator = PathValidator()
        
        # Safe path (relative to test)
        assert validator.is_safe(str(Path.home() / "test.txt"))
        
        # Unsafe paths
        assert not validator.is_safe("../../../etc/passwd")
        assert not validator.is_safe("/etc/passwd")
        assert not validator.is_safe("test\x00.txt")

    def test_sanitize_method(self):
        """Test path sanitization"""
        validator = PathValidator()
        
        # Remove parent directory references
        assert ".." not in validator.sanitize("../test/../file.txt")
        
        # Remove null bytes
        assert "\x00" not in validator.sanitize("file\x00.txt")
        
        # Normalize slashes
        assert "\\" not in validator.sanitize("path\\to\\file")
        
        # Remove duplicate slashes
        assert "//" not in validator.sanitize("path//to//file")

    def test_default_validator_function(self):
        """Test the validate_path convenience function"""
        home = str(Path.home())
        
        # Create temp file
        with tempfile.NamedTemporaryFile(dir=home, delete=False, suffix=".txt") as f:
            temp_path = f.name
        
        try:
            # Should use default validator with home whitelist
            result = validate_path(temp_path, operation="test")
            assert isinstance(result, Path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_operation_logging(self):
        """Test that operation type is included in validation"""
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home])
        
        with tempfile.NamedTemporaryFile(dir=home, delete=False) as f:
            temp_path = f.name
        
        try:
            # Different operations should all work
            validator.validate(temp_path, operation="read")
            validator.validate(temp_path, operation="write")
            validator.validate(temp_path, operation="delete")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_symlinks_blocked_by_default(self):
        """Test that symlinks are blocked by default"""
        # Skip on Windows (different symlink handling)
        if os.name == "nt":
            pytest.skip("Unix-specific test")
        
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home], allow_symlinks=False)
        
        # Create a temp file and symlink
        with tempfile.NamedTemporaryFile(dir=home, delete=False) as f:
            temp_file = f.name
        
        symlink_path = f"{home}/test_symlink"
        
        try:
            os.symlink(temp_file, symlink_path)
            
            # Symlink should be blocked
            with pytest.raises(PathValidationError, match="Symbolic links"):
                validator.validate(symlink_path)
        finally:
            if os.path.exists(symlink_path):
                os.unlink(symlink_path)
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_symlinks_allowed_when_enabled(self):
        """Test that symlinks can be allowed"""
        # Skip on Windows
        if os.name == "nt":
            pytest.skip("Unix-specific test")
        
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home], allow_symlinks=True)
        
        with tempfile.NamedTemporaryFile(dir=home, delete=False) as f:
            temp_file = f.name
        
        symlink_path = f"{home}/test_symlink_allowed"
        
        try:
            os.symlink(temp_file, symlink_path)
            
            # Should succeed when symlinks allowed
            result = validator.validate(symlink_path)
            assert isinstance(result, Path)
        finally:
            if os.path.exists(symlink_path):
                os.unlink(symlink_path)
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestPathValidatorIntegration:
    """Integration tests for path validator"""

    def test_multiple_validation_calls(self):
        """Test that validator can be used multiple times"""
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home])
        
        # Create multiple temp files
        temp_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(dir=home, delete=False) as f:
                temp_files.append(f.name)
        
        try:
            # Validate all of them
            for temp_file in temp_files:
                result = validator.validate(temp_file)
                assert isinstance(result, Path)
        finally:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

    def test_validator_reuse(self):
        """Test that validator instance can be reused"""
        home = str(Path.home())
        validator = PathValidator(allowed_base_dirs=[home])
        
        # Use it multiple times
        for _ in range(10):
            # Safe check
            assert validator.is_safe(f"{home}/test.txt")
            
            # Unsafe check
            assert not validator.is_safe("../../../etc/passwd")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
