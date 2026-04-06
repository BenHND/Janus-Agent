"""
Test suite for TICKET-403: System Context (Grounding) injection

Tests the system_info module and its integration into the pipeline.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSystemInfo:
    """Test system context detection functions"""
    
    def test_get_active_context_structure(self):
        """Test that get_active_context returns proper structure"""
        from janus.platform.os.system_info import get_active_context
        context = get_active_context()
        
        # Check that required keys are present
        assert "active_app" in context
        assert "window_title" in context
        assert "browser_url" in context
        assert "platform" in context
    
    def test_get_active_context_unsupported_platform(self):
        """Test behavior on unsupported platforms"""
        from janus.platform.os.system_info import get_active_context
        with patch("janus.os.system_info.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"
            
            context = get_active_context()
            
            assert context["platform"] == "Linux"
            assert "error" in context
            assert "not supported" in context["error"]
    
    def test_get_safari_url_function_exists(self):
        """Test that Safari URL function exists and has correct signature"""
        from janus.platform.os.system_info import _get_safari_url
        import inspect
        
        # Check function exists
        assert callable(_get_safari_url)
        
        # Check function signature
        sig = inspect.signature(_get_safari_url)
        assert len(sig.parameters) == 1  # Should accept executor parameter
    
    def test_get_chrome_url_function_exists(self):
        """Test that Chrome URL function exists and has correct signature"""
        from janus.platform.os.system_info import _get_chrome_url
        import inspect
        
        # Check function exists
        assert callable(_get_chrome_url)
        
        # Check function signature
        sig = inspect.signature(_get_chrome_url)
        assert len(sig.parameters) == 1  # Should accept executor parameter
    
    def test_get_firefox_url_function_exists(self):
        """Test that Firefox URL function exists and has correct signature"""
        from janus.platform.os.system_info import _get_firefox_url
        import inspect
        
        # Check function exists
        assert callable(_get_firefox_url)
        
        # Check function signature
        sig = inspect.signature(_get_firefox_url)
        assert len(sig.parameters) == 1  # Should accept executor parameter
    
    def test_firefox_url_extraction_logic(self):
        """Test Firefox URL extraction logic with mock executor"""
        from janus.platform.os.system_info import _get_firefox_url
        
        # Mock executor
        mock_executor = Mock()
        
        # Test case 1: Standard Firefox window title with " - Mozilla Firefox"
        mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "Example Page - Mozilla Firefox"
        }
        
        result = _get_firefox_url(mock_executor)
        assert result == "Firefox: Example Page"
        
        # Test case 2: Firefox window title with " — Mozilla Firefox" (em dash)
        mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "GitHub — Mozilla Firefox"
        }
        
        result = _get_firefox_url(mock_executor)
        assert result == "Firefox: GitHub"
        
        # Test case 3: Firefox window title without standard suffix
        mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "Custom Window Title"
        }
        
        result = _get_firefox_url(mock_executor)
        assert result == "Firefox: Custom Window Title"
        
        # Test case 4: Executor fails
        mock_executor.execute.return_value = {
            "status": "error",
            "error": "Firefox not running"
        }
        
        result = _get_firefox_url(mock_executor)
        assert result is None


class TestSystemContextIntegration:
    """Test integration of system context into pipeline"""
    
    def test_system_context_import(self):
        """Test that system context functions can be imported"""
        from janus.platform.os.system_info import get_active_context
        
        # Verify function can be called
        context = get_active_context()
        
        assert context is not None
        assert isinstance(context, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
