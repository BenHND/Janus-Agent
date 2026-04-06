"""
Unit tests for janus.utils.config_loader module
Tests configuration loading, type conversions, and fallback behavior
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from janus.utils.config_loader import ConfigLoader, get_config_loader


class TestConfigLoaderInitialization:
    """Test ConfigLoader initialization"""

    def test_init_with_explicit_path(self, tmp_path):
        """Test initialization with explicit config path"""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.config_path == config_file
        assert loader.get("section1", "key1") == "value1"

    def test_init_searches_standard_locations(self, tmp_path):
        """Test that initialization searches standard locations"""
        # Create config in project root
        config_file = tmp_path / "config.ini"
        config_file.write_text("[test]\nfound = yes\n")
        
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            loader = ConfigLoader()
            # Should find the config file
            assert loader.config_path is not None

    def test_init_without_existing_config(self, tmp_path):
        """Test initialization when no config file exists"""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("janus.utils.config_loader.get_config_file_path", return_value=tmp_path / "nonexistent.ini"):
                loader = ConfigLoader()
                # Should set default path (will be cwd / config.ini)
                assert loader.config_path is not None
                # Config should be empty
                assert not loader.has_section("any_section")


class TestConfigLoaderGet:
    """Test get method for string values"""

    def test_get_existing_value(self, tmp_path):
        """Test getting existing configuration value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get("section1", "key1")
        assert result == "value1"

    def test_get_with_fallback(self, tmp_path):
        """Test getting non-existent value returns fallback"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get("section1", "nonexistent", fallback="default")
        assert result == "default"

    def test_get_nonexistent_section(self, tmp_path):
        """Test getting value from non-existent section"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get("nonexistent", "key", fallback="fallback_value")
        assert result == "fallback_value"

    def test_get_with_none_fallback(self, tmp_path):
        """Test getting non-existent value with None fallback"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get("section1", "nonexistent", fallback=None)
        assert result is None


class TestConfigLoaderGetBool:
    """Test get_bool method for boolean values"""

    def test_get_bool_true(self, tmp_path):
        """Test getting boolean true value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\nenabled = true\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_bool("settings", "enabled")
        assert result is True

    def test_get_bool_false(self, tmp_path):
        """Test getting boolean false value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\nenabled = false\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_bool("settings", "enabled")
        assert result is False

    def test_get_bool_yes_no(self, tmp_path):
        """Test boolean conversion from yes/no"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\nflag1 = yes\nflag2 = no\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.get_bool("settings", "flag1") is True
        assert loader.get_bool("settings", "flag2") is False

    def test_get_bool_with_fallback(self, tmp_path):
        """Test get_bool with fallback for non-existent key"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_bool("settings", "nonexistent", fallback=True)
        assert result is True

    def test_get_bool_invalid_value(self, tmp_path):
        """Test get_bool with invalid boolean value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\ninvalid = notabool\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_bool("settings", "invalid", fallback=False)
        assert result is False  # Should return fallback for invalid value


class TestConfigLoaderGetInt:
    """Test get_int method for integer values"""

    def test_get_int_positive(self, tmp_path):
        """Test getting positive integer"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\ncount = 42\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_int("settings", "count")
        assert result == 42

    def test_get_int_negative(self, tmp_path):
        """Test getting negative integer"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\noffset = -10\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_int("settings", "offset")
        assert result == -10

    def test_get_int_with_fallback(self, tmp_path):
        """Test get_int with fallback for non-existent key"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_int("settings", "nonexistent", fallback=100)
        assert result == 100

    def test_get_int_invalid_value(self, tmp_path):
        """Test get_int with non-integer value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\ninvalid = notanumber\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_int("settings", "invalid", fallback=0)
        assert result == 0  # Should return fallback for invalid value


class TestConfigLoaderGetFloat:
    """Test get_float method for float values"""

    def test_get_float_decimal(self, tmp_path):
        """Test getting float with decimals"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\nratio = 3.14\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_float("settings", "ratio")
        assert result == 3.14

    def test_get_float_scientific(self, tmp_path):
        """Test getting float in scientific notation"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\nbig = 1.5e10\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_float("settings", "big")
        assert result == 1.5e10

    def test_get_float_with_fallback(self, tmp_path):
        """Test get_float with fallback for non-existent key"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_float("settings", "nonexistent", fallback=2.5)
        assert result == 2.5

    def test_get_float_invalid_value(self, tmp_path):
        """Test get_float with non-float value"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[settings]\ninvalid = notafloat\n")
        
        loader = ConfigLoader(str(config_file))
        result = loader.get_float("settings", "invalid", fallback=0.0)
        assert result == 0.0  # Should return fallback for invalid value


class TestConfigLoaderChecks:
    """Test has_section and has_option methods"""

    def test_has_section_exists(self, tmp_path):
        """Test has_section with existing section"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.has_section("section1") is True

    def test_has_section_not_exists(self, tmp_path):
        """Test has_section with non-existent section"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.has_section("nonexistent") is False

    def test_has_option_exists(self, tmp_path):
        """Test has_option with existing option"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.has_option("section1", "key1") is True

    def test_has_option_not_exists(self, tmp_path):
        """Test has_option with non-existent option"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.has_option("section1", "nonexistent") is False

    def test_has_option_wrong_section(self, tmp_path):
        """Test has_option with wrong section"""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[section1]\nkey1 = value1\n")
        
        loader = ConfigLoader(str(config_file))
        assert loader.has_option("wrong_section", "key1") is False


@pytest.fixture
def reset_config_loader():
    """Fixture to reset global config loader singleton"""
    import janus.utils.config_loader
    # Store original state
    original = janus.utils.config_loader._config_loader
    # Reset for test
    janus.utils.config_loader._config_loader = None
    yield
    # Restore original state
    janus.utils.config_loader._config_loader = original


class TestGlobalConfigLoader:
    """Test global config loader singleton"""

    def test_get_config_loader_singleton(self, tmp_path, reset_config_loader):
        """Test that get_config_loader returns singleton"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text("[test]\nvalue = 1\n")
        
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            loader1 = get_config_loader()
            loader2 = get_config_loader()
            
            # Should be same instance
            assert loader1 is loader2

    def test_get_config_loader_with_path(self, tmp_path, reset_config_loader):
        """Test get_config_loader with explicit path"""
        
        config_file = tmp_path / "custom.ini"
        config_file.write_text("[test]\nvalue = custom\n")
        
        loader = get_config_loader(str(config_file))
        assert loader.get("test", "value") == "custom"


class TestConfigLoaderIntegration:
    """Integration tests for ConfigLoader"""

    def test_complex_config_file(self, tmp_path):
        """Test loading complex configuration file"""
        config_content = """
[database]
host = localhost
port = 5432
enabled = yes

[api]
timeout = 30.5
max_retries = 3
debug = false

[features]
experimental = true
"""
        config_file = tmp_path / "config.ini"
        config_file.write_text(config_content)
        
        loader = ConfigLoader(str(config_file))
        
        # Test various types
        assert loader.get("database", "host") == "localhost"
        assert loader.get_int("database", "port") == 5432
        assert loader.get_bool("database", "enabled") is True
        
        assert loader.get_float("api", "timeout") == 30.5
        assert loader.get_int("api", "max_retries") == 3
        assert loader.get_bool("api", "debug") is False
        
        assert loader.get_bool("features", "experimental") is True

    def test_empty_config_file(self, tmp_path):
        """Test loading empty configuration file"""
        config_file = tmp_path / "empty.ini"
        config_file.write_text("")
        
        loader = ConfigLoader(str(config_file))
        
        # Should handle gracefully
        assert loader.get("any", "key", "default") == "default"
        assert loader.has_section("any") is False

    def test_config_with_comments(self, tmp_path):
        """Test configuration with comments"""
        config_content = """
# This is a comment
[section1]
key1 = value1
# Another comment
key2 = value2
"""
        config_file = tmp_path / "config.ini"
        config_file.write_text(config_content)
        
        loader = ConfigLoader(str(config_file))
        assert loader.get("section1", "key1") == "value1"
        assert loader.get("section1", "key2") == "value2"
