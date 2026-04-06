"""
Tests for Deep Link functionality (TICKET-BIZ-003)

Tests the Generic Deep Linker system for opening SaaS applications
using native URL schemes and web fallbacks.
"""

import asyncio
import json
import platform
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

# Mock heavy dependencies before importing from janus
_mock_modules = {
    'pyautogui': MagicMock(),
    'PIL': MagicMock(),
    'PIL.Image': MagicMock(),
    'cv2': MagicMock(),
    'numpy': MagicMock(),
    'mouseinfo': MagicMock(),
}
for mod_name, mock in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock


def async_test(coro):
    """Decorator to run async tests in unittest."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestDeepLinkHandler(unittest.TestCase):
    """Test DeepLinkHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample registry data
        self.sample_registry = {
            "description": "Test registry",
            "version": "1.0.0",
            "apps": {
                "zoom": {
                    "name": "Zoom",
                    "description": "Zoom meetings",
                    "url_scheme": "zoommtg://zoom.us/join?confno={id}",
                    "web_fallback": "https://zoom.us/j/{id}",
                    "examples": ["zoommtg://zoom.us/join?confno=123456789"]
                },
                "spotify": {
                    "name": "Spotify",
                    "description": "Spotify tracks",
                    "url_scheme": "spotify:{type}:{id}",
                    "web_fallback": "https://open.spotify.com/{type}/{id}",
                    "examples": ["spotify:track:3n3Ppam7vgaVa1iaRUc9Lp"]
                }
            }
        }
    
    @patch('janus.os.app_deep_links.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_registry_success(self, mock_file, mock_exists):
        """Test successful registry loading."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.sample_registry)
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(self.sample_registry)
        
        # Mock json.load to return our sample registry
        with patch('json.load', return_value=self.sample_registry):
            handler = DeepLinkHandler()
            
            self.assertIsNotNone(handler.registry)
            self.assertEqual(len(handler.registry), 2)
            self.assertIn("zoom", handler.registry)
            self.assertIn("spotify", handler.registry)
    
    @patch('janus.os.app_deep_links.Path.exists')
    def test_load_registry_file_not_found(self, mock_exists):
        """Test registry loading when file doesn't exist."""
        from janus.platform.os.app_deep_links import DeepLinkHandler, DeepLinkError
        
        mock_exists.return_value = False
        
        with self.assertRaises(DeepLinkError) as ctx:
            DeepLinkHandler()
        
        self.assertIn("Registry file not found", str(ctx.exception))
    
    def test_get_supported_apps(self):
        """Test getting list of supported apps."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            apps = handler.get_supported_apps()
            
            self.assertIsInstance(apps, list)
            self.assertEqual(set(apps), {"zoom", "spotify"})
    
    def test_get_app_info(self):
        """Test getting app configuration."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            
            # Test existing app
            zoom_info = handler.get_app_info("zoom")
            self.assertIsNotNone(zoom_info)
            self.assertEqual(zoom_info["name"], "Zoom")
            
            # Test case-insensitive (get_app_info converts to lowercase)
            zoom_info_upper = handler.get_app_info("ZOOM")
            self.assertIsNotNone(zoom_info_upper)  # Should work case-insensitively
            self.assertEqual(zoom_info_upper["name"], "Zoom")
            
            # Test non-existent app
            unknown_info = handler.get_app_info("unknown_app")
            self.assertIsNone(unknown_info)
    
    def test_build_url_zoom(self):
        """Test building Zoom meeting URL."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            
            # Test URL scheme
            url = handler.build_url("zoom", {"id": "123-456-789"})
            self.assertEqual(url, "zoommtg://zoom.us/join?confno=123-456-789")
            
            # Test web fallback
            web_url = handler.build_url("zoom", {"id": "123-456-789"}, use_web_fallback=True)
            self.assertEqual(web_url, "https://zoom.us/j/123-456-789")
    
    def test_build_url_spotify(self):
        """Test building Spotify track URL."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            
            # Test with all required args
            url = handler.build_url("spotify", {"type": "track", "id": "abc123"})
            self.assertEqual(url, "spotify:track:abc123")
            
            # Test web fallback
            web_url = handler.build_url("spotify", {"type": "track", "id": "abc123"}, use_web_fallback=True)
            self.assertEqual(web_url, "https://open.spotify.com/track/abc123")
    
    def test_build_url_missing_args(self):
        """Test building URL with missing required arguments."""
        from janus.platform.os.app_deep_links import DeepLinkHandler, DeepLinkError
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            
            # Missing 'id' argument for Zoom
            with self.assertRaises(DeepLinkError) as ctx:
                handler.build_url("zoom", {})
            
            self.assertIn("Missing required argument", str(ctx.exception))
            self.assertIn("id", str(ctx.exception))
    
    def test_build_url_unknown_app(self):
        """Test building URL for unknown app."""
        from janus.platform.os.app_deep_links import DeepLinkHandler, DeepLinkError
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            
            with self.assertRaises(DeepLinkError) as ctx:
                handler.build_url("unknown_app", {"id": "123"})
            
            self.assertIn("Unknown app", str(ctx.exception))
            self.assertIn("zoom", str(ctx.exception))  # Should list supported apps
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_open_url_macos(self, mock_system, mock_subprocess):
        """Test opening URL on macOS."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        mock_system.return_value = "Darwin"
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            success = handler.open_url("zoommtg://zoom.us/join?confno=123")
            
            self.assertTrue(success)
            mock_subprocess.assert_called_once()
            # Verify 'open' command was used
            call_args = mock_subprocess.call_args[0][0]
            self.assertEqual(call_args[0], "open")
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_open_url_windows(self, mock_system, mock_subprocess):
        """Test opening URL on Windows."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        mock_system.return_value = "Windows"
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            success = handler.open_url("zoommtg://zoom.us/join?confno=123")
            
            self.assertTrue(success)
            mock_subprocess.assert_called_once()
            # Verify 'start' command was used
            call_args = mock_subprocess.call_args[0][0]
            self.assertIn("start", call_args)
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_open_url_linux(self, mock_system, mock_subprocess):
        """Test opening URL on Linux."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        mock_system.return_value = "Linux"
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            success = handler.open_url("zoommtg://zoom.us/join?confno=123")
            
            self.assertTrue(success)
            mock_subprocess.assert_called_once()
            # Verify 'xdg-open' command was used
            call_args = mock_subprocess.call_args[0][0]
            self.assertEqual(call_args[0], "xdg-open")
    
    @patch('webbrowser.open')
    @patch('subprocess.run')
    @patch('platform.system')
    def test_open_url_fallback_to_webbrowser(self, mock_system, mock_subprocess, mock_webbrowser):
        """Test fallback to webbrowser when subprocess fails."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        import subprocess
        
        mock_system.return_value = "Darwin"
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'open')
        mock_webbrowser.return_value = True
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            success = handler.open_url("https://zoom.us/j/123")
            
            self.assertTrue(success)
            mock_webbrowser.assert_called_once()
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_open_deep_link_integration(self, mock_system, mock_subprocess):
        """Test full open_deep_link integration."""
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        mock_system.return_value = "Darwin"
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        with patch.object(DeepLinkHandler, '_load_registry', return_value=self.sample_registry["apps"]):
            handler = DeepLinkHandler()
            success = handler.open_deep_link("zoom", {"id": "123-456-789"})
            
            self.assertTrue(success)
            mock_subprocess.assert_called_once()
            
            # Verify correct URL was opened
            call_args = mock_subprocess.call_args[0][0]
            self.assertIn("zoommtg://zoom.us/join?confno=123-456-789", call_args)


class TestSystemAgentDeepLink(unittest.TestCase):
    """Test SystemAgent integration with deep links."""
    
    @async_test
    async def test_open_deep_link_action_zoom(self):
        """Test open_deep_link action for Zoom."""
        from janus.capabilities.agents.system_agent import SystemAgent
        
        # Create agent with mocked OS interface
        mock_os_interface = MagicMock()
        mock_os_interface.is_available.return_value = True
        agent = SystemAgent(os_interface=mock_os_interface)
        
        # Mock subprocess to prevent actual URL opening
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)
            
            # Execute action
            result = await agent.execute(
                action="open_deep_link",
                args={
                    "app": "zoom",
                    "args": {"id": "123-456-789"}
                },
                context={}
            )
            
            # Verify result
            self.assertEqual(result["status"], "success")
            self.assertIn("app", result["data"])
            self.assertEqual(result["data"]["app"], "zoom")
    
    @async_test
    async def test_open_deep_link_action_spotify(self):
        """Test open_deep_link action for Spotify."""
        from janus.capabilities.agents.system_agent import SystemAgent
        
        mock_os_interface = MagicMock()
        mock_os_interface.is_available.return_value = True
        agent = SystemAgent(os_interface=mock_os_interface)
        
        # Mock subprocess to prevent actual URL opening
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)
            
            result = await agent.execute(
                action="open_deep_link",
                args={
                    "app": "spotify",
                    "args": {"type": "track", "id": "abc123"}
                },
                context={}
            )
            
            self.assertEqual(result["status"], "success")
    
    @async_test
    async def test_open_deep_link_with_web_fallback(self):
        """Test open_deep_link with web fallback option."""
        from janus.capabilities.agents.system_agent import SystemAgent
        
        mock_os_interface = MagicMock()
        mock_os_interface.is_available.return_value = True
        agent = SystemAgent(os_interface=mock_os_interface)
        
        # Mock subprocess to prevent actual URL opening
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)
            
            result = await agent.execute(
                action="open_deep_link",
                args={
                    "app": "zoom",
                    "args": {"id": "123"},
                    "use_web_fallback": True
                },
                context={}
            )
            
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["data"]["use_web_fallback"], True)
    
    @async_test
    async def test_open_deep_link_missing_app(self):
        """Test open_deep_link with missing 'app' argument."""
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.capabilities.agents.base_agent import AgentExecutionError
        
        mock_os_interface = MagicMock()
        mock_os_interface.is_available.return_value = True
        agent = SystemAgent(os_interface=mock_os_interface)
        
        with self.assertRaises(AgentExecutionError):
            await agent.execute(
                action="open_deep_link",
                args={"args": {"id": "123"}},  # Missing 'app'
                context={}
            )
    
    @async_test
    async def test_open_deep_link_invalid_args_type(self):
        """Test open_deep_link with invalid args type (not a dict)."""
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.platform.os.app_deep_links import DeepLinkHandler
        
        with patch('janus.os.app_deep_links.get_deep_link_handler') as mock_get_handler:
            mock_handler = MagicMock(spec=DeepLinkHandler)
            mock_get_handler.return_value = mock_handler
            
            mock_os_interface = MagicMock()
            mock_os_interface.is_available.return_value = True
            agent = SystemAgent(os_interface=mock_os_interface)
            
            result = await agent.execute(
                action="open_deep_link",
                args={
                    "app": "zoom",
                    "args": "not-a-dict"  # Invalid type
                },
                context={}
            )
            
            self.assertEqual(result["status"], "error")
            self.assertIn("must be a dictionary", result["error"])
    
    @async_test
    async def test_open_deep_link_unknown_app(self):
        """Test open_deep_link with unknown app."""
        from janus.capabilities.agents.system_agent import SystemAgent
        from janus.platform.os.app_deep_links import DeepLinkHandler, DeepLinkError
        
        with patch('janus.os.app_deep_links.get_deep_link_handler') as mock_get_handler:
            mock_handler = MagicMock(spec=DeepLinkHandler)
            mock_handler.open_deep_link.side_effect = DeepLinkError("Unknown app 'unknown_app'")
            mock_get_handler.return_value = mock_handler
            
            mock_os_interface = MagicMock()
            mock_os_interface.is_available.return_value = True
            agent = SystemAgent(os_interface=mock_os_interface)
            
            result = await agent.execute(
                action="open_deep_link",
                args={
                    "app": "unknown_app",
                    "args": {"id": "123"}
                },
                context={}
            )
            
            self.assertEqual(result["status"], "error")
            self.assertIn("Unknown app", result["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
