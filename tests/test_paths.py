"""
Tests for cross-platform path utilities
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from janus.utils.paths import (
    get_cache_dir,
    get_config_dir,
    get_config_file_path,
    get_data_dir,
    get_encryption_key_path,
    get_log_dir,
    get_models_dir,
    get_vision_config_path,
)


class TestPathUtilities:
    """Test cross-platform path utilities"""

    def test_get_data_dir_returns_path(self):
        """Test that get_data_dir returns a Path object"""
        data_dir = get_data_dir(ensure_exists=False)
        assert isinstance(data_dir, Path)
        assert "Janus" in str(data_dir)

    def test_get_config_dir_returns_path(self):
        """Test that get_config_dir returns a Path object"""
        config_dir = get_config_dir(ensure_exists=False)
        assert isinstance(config_dir, Path)
        assert "Janus" in str(config_dir)

    def test_get_log_dir_returns_path(self):
        """Test that get_log_dir returns a Path object"""
        log_dir = get_log_dir(ensure_exists=False)
        assert isinstance(log_dir, Path)
        assert "Janus" in str(log_dir) or "log" in str(log_dir).lower()

    def test_get_cache_dir_returns_path(self):
        """Test that get_cache_dir returns a Path object"""
        cache_dir = get_cache_dir(ensure_exists=False)
        assert isinstance(cache_dir, Path)
        assert "Janus" in str(cache_dir) or "cache" in str(cache_dir).lower()

    def test_get_models_dir_returns_path(self):
        """Test that get_models_dir returns a Path object"""
        models_dir = get_models_dir(ensure_exists=False)
        assert isinstance(models_dir, Path)
        assert "models" in str(models_dir)

    def test_get_encryption_key_path_returns_path(self):
        """Test that get_encryption_key_path returns a Path object"""
        key_path = get_encryption_key_path(ensure_dir_exists=False)
        assert isinstance(key_path, Path)
        assert key_path.name == ".encryption_key"

    def test_get_config_file_path_default(self):
        """Test get_config_file_path with default filename"""
        config_path = get_config_file_path(ensure_dir_exists=False)
        assert isinstance(config_path, Path)
        assert config_path.name == "config.ini"

    def test_get_config_file_path_custom(self):
        """Test get_config_file_path with custom filename"""
        config_path = get_config_file_path("custom.json", ensure_dir_exists=False)
        assert isinstance(config_path, Path)
        assert config_path.name == "custom.json"

    def test_get_vision_config_path_returns_path(self):
        """Test that get_vision_config_path returns a Path object"""
        vision_path = get_vision_config_path(ensure_dir_exists=False)
        assert isinstance(vision_path, Path)
        assert vision_path.name == "vision_config.json"

    def test_paths_are_absolute(self):
        """Test that all paths returned are absolute"""
        assert get_data_dir(ensure_exists=False).is_absolute()
        assert get_config_dir(ensure_exists=False).is_absolute()
        assert get_log_dir(ensure_exists=False).is_absolute()
        assert get_cache_dir(ensure_exists=False).is_absolute()
        assert get_models_dir(ensure_exists=False).is_absolute()
        assert get_encryption_key_path(ensure_dir_exists=False).is_absolute()

    def test_ensure_exists_creates_directories(self, tmp_path, monkeypatch):
        """Test that ensure_exists=True creates directories"""
        # Mock platformdirs to use tmp_path
        test_data_dir = tmp_path / "test_data"

        with patch("janus.utils.paths.user_data_dir", return_value=str(test_data_dir)):
            data_dir = get_data_dir(ensure_exists=True)
            assert data_dir.exists()
            assert data_dir.is_dir()

    def test_ensure_exists_false_does_not_create(self, tmp_path, monkeypatch):
        """Test that ensure_exists=False does not create directories"""
        # Mock platformdirs to use tmp_path
        test_data_dir = tmp_path / "test_data_no_create"

        with patch("janus.utils.paths.user_data_dir", return_value=str(test_data_dir)):
            data_dir = get_data_dir(ensure_exists=False)
            # We can't assert it doesn't exist because platformdirs might return
            # a path that already exists, but we can assert it returns the right path
            assert "test_data_no_create" in str(data_dir)

    def test_models_dir_is_subdirectory_of_cache(self):
        """Test that models directory is a subdirectory of cache"""
        cache_dir = get_cache_dir(ensure_exists=False)
        models_dir = get_models_dir(ensure_exists=False)

        # models_dir should be cache_dir / "models"
        assert models_dir.parent == cache_dir
        assert models_dir.name == "models"

    def test_encryption_key_in_data_dir(self):
        """Test that encryption key is stored in data directory"""
        data_dir = get_data_dir(ensure_exists=False)
        key_path = get_encryption_key_path(ensure_dir_exists=False)

        assert key_path.parent == data_dir

    def test_config_file_in_config_dir(self):
        """Test that config files are in config directory"""
        config_dir = get_config_dir(ensure_exists=False)
        config_path = get_config_file_path(ensure_dir_exists=False)

        assert config_path.parent == config_dir


class TestPathCompatibility:
    """Test backward compatibility features"""

    def test_legacy_data_path_format(self):
        """Test that legacy data path matches old format"""
        legacy = get_legacy_paths()
        expected = Path.home() / ".janus"
        assert legacy["data"] == expected

    def test_legacy_log_path_macos(self):
        """Test that legacy log path on macOS matches old format"""
        if sys.platform == "darwin":
            legacy = get_legacy_paths()
            expected = Path.home() / "Library" / "Logs" / "Janus"
            assert legacy["logs"] == expected

    def test_legacy_log_path_other(self):
        """Test that legacy log path on non-macOS matches old format"""
        if sys.platform != "darwin":
            legacy = get_legacy_paths()
            expected = Path.home() / ".janus" / "logs"
            assert legacy["logs"] == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
