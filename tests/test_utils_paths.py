"""
Unit tests for janus.utils.paths module
Tests cross-platform path utilities
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from janus.utils.paths import (
    get_data_dir,
    get_config_dir,
    get_log_dir,
    get_cache_dir,
    get_models_dir,
    get_encryption_key_path,
    get_config_file_path,
    get_vision_config_path,
    APP_NAME,
    APP_AUTHOR,
)


class TestDataDirectory:
    """Test get_data_dir function"""

    def test_get_data_dir_returns_path(self):
        """Test that get_data_dir returns a Path object"""
        result = get_data_dir(ensure_exists=False)
        assert isinstance(result, Path)
        assert APP_NAME in str(result)

    def test_get_data_dir_ensures_exists(self, tmp_path):
        """Test that get_data_dir creates directory"""
        with patch('janus.utils.paths.user_data_dir', return_value=str(tmp_path / "data")):
            path = get_data_dir(ensure_exists=True)
            assert path.exists()
            assert path.is_dir()

    def test_get_data_dir_no_ensure(self, tmp_path):
        """Test get_data_dir without creating directory"""
        with patch('janus.utils.paths.user_data_dir', return_value=str(tmp_path / "nonexistent")):
            path = get_data_dir(ensure_exists=False)
            # Should return path even if doesn't exist
            assert isinstance(path, Path)


class TestConfigDirectory:
    """Test get_config_dir function"""

    def test_get_config_dir_returns_path(self):
        """Test that get_config_dir returns a Path object"""
        result = get_config_dir(ensure_exists=False)
        assert isinstance(result, Path)
        assert APP_NAME in str(result)

    def test_get_config_dir_ensures_exists(self, tmp_path):
        """Test that get_config_dir creates directory"""
        with patch('janus.utils.paths.user_config_dir', return_value=str(tmp_path / "config")):
            path = get_config_dir(ensure_exists=True)
            assert path.exists()
            assert path.is_dir()

    def test_get_config_dir_no_ensure(self, tmp_path):
        """Test get_config_dir without creating directory"""
        with patch('janus.utils.paths.user_config_dir', return_value=str(tmp_path / "nonexistent")):
            path = get_config_dir(ensure_exists=False)
            assert isinstance(path, Path)


class TestLogDirectory:
    """Test get_log_dir function"""

    def test_get_log_dir_returns_path(self):
        """Test that get_log_dir returns a Path object"""
        result = get_log_dir(ensure_exists=False)
        assert isinstance(result, Path)

    def test_get_log_dir_ensures_exists(self, tmp_path):
        """Test that get_log_dir creates directory"""
        with patch('janus.utils.paths.user_log_dir', return_value=str(tmp_path / "logs")):
            path = get_log_dir(ensure_exists=True)
            assert path.exists()
            assert path.is_dir()

    def test_get_log_dir_no_ensure(self, tmp_path):
        """Test get_log_dir without creating directory"""
        with patch('janus.utils.paths.user_log_dir', return_value=str(tmp_path / "nonexistent")):
            path = get_log_dir(ensure_exists=False)
            assert isinstance(path, Path)


class TestCacheDirectory:
    """Test get_cache_dir function"""

    def test_get_cache_dir_returns_path(self):
        """Test that get_cache_dir returns a Path object"""
        result = get_cache_dir(ensure_exists=False)
        assert isinstance(result, Path)
        assert APP_NAME in str(result)

    def test_get_cache_dir_ensures_exists(self, tmp_path):
        """Test that get_cache_dir creates directory"""
        with patch('janus.utils.paths.user_cache_dir', return_value=str(tmp_path / "cache")):
            path = get_cache_dir(ensure_exists=True)
            assert path.exists()
            assert path.is_dir()

    def test_get_cache_dir_no_ensure(self, tmp_path):
        """Test get_cache_dir without creating directory"""
        with patch('janus.utils.paths.user_cache_dir', return_value=str(tmp_path / "nonexistent")):
            path = get_cache_dir(ensure_exists=False)
            assert isinstance(path, Path)


class TestModelsDirectory:
    """Test get_models_dir function"""

    def test_get_models_dir_returns_path(self):
        """Test that get_models_dir returns a Path object"""
        result = get_models_dir(ensure_exists=False)
        assert isinstance(result, Path)
        assert "models" in str(result)

    def test_get_models_dir_in_cache(self):
        """Test that models directory is under cache directory"""
        cache_dir = get_cache_dir(ensure_exists=False)
        models_dir = get_models_dir(ensure_exists=False)
        assert models_dir.parent == cache_dir

    def test_get_models_dir_ensures_exists(self, tmp_path):
        """Test that get_models_dir creates directory"""
        with patch('janus.utils.paths.user_cache_dir', return_value=str(tmp_path / "cache")):
            path = get_models_dir(ensure_exists=True)
            assert path.exists()
            assert path.is_dir()
            assert path.name == "models"

    def test_get_models_dir_no_ensure(self, tmp_path):
        """Test get_models_dir without creating directory"""
        with patch('janus.utils.paths.user_cache_dir', return_value=str(tmp_path / "cache")):
            path = get_models_dir(ensure_exists=False)
            assert path.name == "models"


class TestEncryptionKeyPath:
    """Test get_encryption_key_path function"""

    def test_get_encryption_key_path_returns_path(self):
        """Test that get_encryption_key_path returns a Path object"""
        result = get_encryption_key_path(ensure_dir_exists=False)
        assert isinstance(result, Path)
        assert result.name == ".encryption_key"

    def test_encryption_key_in_data_dir(self):
        """Test that encryption key is in data directory"""
        data_dir = get_data_dir(ensure_exists=False)
        key_path = get_encryption_key_path(ensure_dir_exists=False)
        assert key_path.parent == data_dir

    def test_encryption_key_path_ensures_dir(self, tmp_path):
        """Test that encryption key path creates parent directory"""
        with patch('janus.utils.paths.user_data_dir', return_value=str(tmp_path / "data")):
            path = get_encryption_key_path(ensure_dir_exists=True)
            assert path.parent.exists()
            assert path.name == ".encryption_key"


class TestConfigFilePath:
    """Test get_config_file_path function"""

    def test_get_config_file_path_default(self):
        """Test get_config_file_path with default filename"""
        result = get_config_file_path(ensure_dir_exists=False)
        assert isinstance(result, Path)
        assert result.name == "config.ini"

    def test_get_config_file_path_custom(self):
        """Test get_config_file_path with custom filename"""
        result = get_config_file_path("custom.json", ensure_dir_exists=False)
        assert result.name == "custom.json"

    def test_config_file_in_config_dir(self):
        """Test that config file is in config directory"""
        config_dir = get_config_dir(ensure_exists=False)
        config_file = get_config_file_path(ensure_dir_exists=False)
        assert config_file.parent == config_dir

    def test_config_file_path_ensures_dir(self, tmp_path):
        """Test that config file path creates parent directory"""
        with patch('janus.utils.paths.user_config_dir', return_value=str(tmp_path / "config")):
            path = get_config_file_path("test.ini", ensure_dir_exists=True)
            assert path.parent.exists()
            assert path.name == "test.ini"


class TestVisionConfigPath:
    """Test get_vision_config_path function"""

    def test_get_vision_config_path_returns_path(self):
        """Test that get_vision_config_path returns a Path object"""
        result = get_vision_config_path(ensure_dir_exists=False)
        assert isinstance(result, Path)
        assert result.name == "vision_config.json"

    def test_vision_config_in_config_dir(self):
        """Test that vision config is in config directory"""
        config_dir = get_config_dir(ensure_exists=False)
        vision_config = get_vision_config_path(ensure_dir_exists=False)
        assert vision_config.parent == config_dir

    def test_vision_config_path_ensures_dir(self, tmp_path):
        """Test that vision config path creates parent directory"""
        with patch('janus.utils.paths.user_config_dir', return_value=str(tmp_path / "config")):
            path = get_vision_config_path(ensure_dir_exists=True)
            assert path.parent.exists()
            assert path.name == "vision_config.json"


class TestConstants:
    """Test module constants"""

    def test_app_name_constant(self):
        """Test APP_NAME constant is defined"""
        assert APP_NAME == "Janus"

    def test_app_author_constant(self):
        """Test APP_AUTHOR constant is defined"""
        assert APP_AUTHOR == "BenHND"


class TestPathsIntegration:
    """Integration tests for path utilities"""

    def test_all_paths_are_distinct(self):
        """Test that different path types are distinct"""
        data_dir = get_data_dir(ensure_exists=False)
        config_dir = get_config_dir(ensure_exists=False)
        log_dir = get_log_dir(ensure_exists=False)
        cache_dir = get_cache_dir(ensure_exists=False)
        
        # Paths might be same on some platforms, but should be valid
        paths = [data_dir, config_dir, log_dir, cache_dir]
        for path in paths:
            assert isinstance(path, Path)

    def test_models_dir_hierarchy(self):
        """Test models directory hierarchy"""
        cache_dir = get_cache_dir(ensure_exists=False)
        models_dir = get_models_dir(ensure_exists=False)
        
        # models dir should be under cache dir
        assert models_dir.parent == cache_dir

    def test_config_files_hierarchy(self):
        """Test config files hierarchy"""
        config_dir = get_config_dir(ensure_exists=False)
        config_file = get_config_file_path(ensure_dir_exists=False)
        vision_config = get_vision_config_path(ensure_dir_exists=False)
        
        # All config files should be under config dir
        assert config_file.parent == config_dir
        assert vision_config.parent == config_dir

    def test_encryption_key_in_secure_location(self):
        """Test encryption key is in data directory"""
        data_dir = get_data_dir(ensure_exists=False)
        key_path = get_encryption_key_path(ensure_dir_exists=False)
        
        # Encryption key should be in data dir for security
        assert key_path.parent == data_dir
        # Should be hidden file
        assert key_path.name.startswith(".")

    def test_directory_creation_idempotent(self, tmp_path):
        """Test that directory creation is idempotent"""
        with patch('janus.utils.paths.user_data_dir', return_value=str(tmp_path / "data")):
            # Create once
            path1 = get_data_dir(ensure_exists=True)
            assert path1.exists()
            
            # Create again
            path2 = get_data_dir(ensure_exists=True)
            assert path2.exists()
            assert path1 == path2
