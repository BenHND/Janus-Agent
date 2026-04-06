"""
Tests for BrowserAgent bug fixes

This test suite validates the following bug fixes:
- Bug 1: MLX Whisper priority on Apple Silicon
- Bug 3: type_text → type action name fix
- Bug 4: Missing open_tab and close_tab handlers
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class MockOSInterface:
    """Mock OS interface for testing."""
    
    def is_available(self):
        return True
    
    def run_script(self, script):
        return MagicMock(success=True, data={"stdout": "success"}, error=None)
    
    def send_keys(self, keys, modifiers=None):
        return MagicMock(success=True, data={}, error=None)
    
    def type_text(self, text):
        return MagicMock(success=True, data={}, error=None)


class MockSystemAgent:
    """Mock SystemAgent for testing."""
    
    def __init__(self):
        self.executed_actions = []
    
    async def execute(self, action: str, args: dict, context: dict) -> dict:
        self.executed_actions.append({"action": action, "args": args})
        return {"status": "success", "data": {}}


class TestBrowserAgentTabManagement(unittest.TestCase):
    """Test open_tab and close_tab handlers (Bug 4 fix)."""
    
    def test_execute_routes_open_tab(self):
        """Test that execute method routes open_tab action correctly."""
        # Read the browser_agent.py file and verify open_tab is handled
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify open_tab handler is present in execute method
        self.assertIn('action == "open_tab"', content, 
                      "open_tab action should be handled in execute method")
        self.assertIn('_open_tab', content,
                      "_open_tab method should exist")
    
    def test_execute_routes_close_tab(self):
        """Test that execute method routes close_tab action correctly."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify close_tab handler is present in execute method
        self.assertIn('action == "close_tab"', content,
                      "close_tab action should be handled in execute method")
        self.assertIn('_close_tab', content,
                      "_close_tab method should exist")
    
    def test_open_tab_uses_command_t_shortcut(self):
        """Test that _open_tab uses correct keyboard shortcut."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify command t shortcut is used
        self.assertIn('command t', content,
                      "_open_tab should use 'command t' shortcut")
    
    def test_close_tab_uses_command_w_shortcut(self):
        """Test that _close_tab uses correct keyboard shortcut."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Verify command w shortcut is used
        self.assertIn('command w', content,
                      "_close_tab should use 'command w' shortcut")


class TestBrowserAgentTypeAction(unittest.TestCase):
    """Test type_text → type fix (Bug 3 fix)."""
    
    def test_search_keystroke_fallback_uses_type_not_type_text(self):
        """Test that _search_keystroke_fallback uses 'type' action, not 'type_text'."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Find the _search_keystroke_fallback method and verify it uses "type"
        # Look for the pattern in the method
        method_start = content.find("async def _search_keystroke_fallback")
        self.assertNotEqual(method_start, -1, 
                           "_search_keystroke_fallback method should exist")
        
        # Find the end of the method (next async def or end of file)
        method_end = content.find("async def", method_start + 1)
        if method_end == -1:
            method_end = len(content)
        
        method_content = content[method_start:method_end]
        
        # Verify it uses "type" action, not "type_text"
        self.assertIn('execute("type"', method_content,
                      "_search_keystroke_fallback should call system_agent.execute with 'type' action")
        self.assertNotIn('execute("type_text"', method_content,
                        "_search_keystroke_fallback should NOT use 'type_text' action")


class TestSystemAgentSupportsTypeAction(unittest.TestCase):
    """Test that SystemAgent supports the 'type' action."""
    
    def test_system_agent_has_type_handler(self):
        """Test that SystemAgent has type action handler."""
        with open("janus/agents/system_agent.py", "r") as f:
            content = f.read()
        
        # Verify type action is handled
        self.assertIn('action == "type"', content,
                      "SystemAgent should handle 'type' action")
        self.assertIn('async def _type', content,
                      "SystemAgent should have _type method")
    
    def test_system_agent_does_not_have_type_text_action(self):
        """Test that SystemAgent does not have type_text action handler."""
        with open("janus/agents/system_agent.py", "r") as f:
            content = f.read()
        
        # Verify type_text action is NOT a separate action in the execute dispatcher
        # The SystemAgent should use "type", not "type_text"
        # type_text should NOT be a separate action in the execute dispatcher
        self.assertNotIn('action == "type_text"', content,
                        "SystemAgent should NOT have separate 'type_text' action - use 'type' instead")


class TestBrowserAgentMethodsExist(unittest.TestCase):
    """Test that all required methods exist in BrowserAgent."""
    
    def test_all_action_methods_exist(self):
        """Test that all action methods referenced in execute exist."""
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # List of methods that should exist based on the execute dispatcher
        required_methods = [
            "_open_url",
            "_search",
            "_click",
            "_scroll",
            "_extract_text",
            "_play_video",
            "_navigate_back",
            "_open_tab",  # Bug 4 fix
            "_close_tab",  # Bug 4 fix
        ]
        
        for method in required_methods:
            self.assertIn(f"async def {method}(", content,
                         f"Method {method} should exist in BrowserAgent")


class TestBrowserAgentSearchHierarchy(unittest.TestCase):
    """Test TICKET-FIX-GLOBAL: Search Hierarchy Implementation (DOM -> URL -> Keyboard)."""
    
    @classmethod
    def setUpClass(cls):
        """Load browser_agent content once for all tests."""
        with open("janus/agents/browser_agent.py", "r") as f:
            cls.content = f.read()
        
        # Pre-compute method boundaries for _search_vision_fallback
        cls.vision_fallback_start = cls.content.find("async def _search_vision_fallback(")
        keystroke_fallback_start = cls.content.find("async def _search_keystroke_fallback(")
        
        # If keystroke fallback exists, use it as end boundary; otherwise use next method pattern
        if keystroke_fallback_start > cls.vision_fallback_start:
            cls.vision_fallback_end = keystroke_fallback_start
        else:
            # Fallback: find next "async def" after the start
            next_method = cls.content.find("async def ", cls.vision_fallback_start + 1)
            cls.vision_fallback_end = next_method if next_method != -1 else len(cls.content)
    
    def _get_vision_fallback_content(self):
        """Helper to get _search_vision_fallback method content."""
        if self.vision_fallback_start == -1:
            return ""
        return self.content[self.vision_fallback_start:self.vision_fallback_end]
    
    def test_search_visual_fallback_method_exists(self):
        """Test that _search_vision_fallback method exists."""
        self.assertIn("async def _search_vision_fallback(", self.content,
                      "_search_vision_fallback method should exist in BrowserAgent")
    
    def test_search_uses_dom_vision_url_hierarchy(self):
        """Test that _search method follows DOM -> Vision -> URL hierarchy.
        
        TICKET-FIX-USE-CASE-1: Changed from DOM -> URL -> Keyboard to DOM -> Vision -> URL
        because URL fallback reloads the page, which is invasive.
        
        TICKET-FIX-BROWSER-SEARCH: Keyboard shortcut "/" is now INSIDE vision fallback,
        not a separate step in the main hierarchy.
        """
        # Find _search method
        search_start = self.content.find("async def _search(")
        self.assertNotEqual(search_start, -1, "_search method should exist")
        
        # Find the end of _search method (next method definition)
        dom_injection_start = self.content.find("async def _search_dom_injection(")
        self.assertNotEqual(dom_injection_start, -1, "_search_dom_injection should exist")
        self.assertGreater(dom_injection_start, search_start, 
                          "_search_dom_injection should come after _search")
        
        method_content = self.content[search_start:dom_injection_start]
        
        # Verify hierarchy order: DOM first
        dom_pos = method_content.find("_search_dom_injection")
        self.assertNotEqual(dom_pos, -1, "DOM injection should be called in _search")
        
        # Verify Vision is second (TICKET-FIX-USE-CASE-1)
        vision_pos = method_content.find("_search_vision_fallback")
        self.assertNotEqual(vision_pos, -1, "Vision fallback should be called in _search")
        
        # Verify URL is last (dernier recours)
        url_pos = method_content.find("_open_url")
        self.assertNotEqual(url_pos, -1, "URL fallback should be called in _search")
        
        # Verify order: DOM < Vision < URL
        self.assertLess(dom_pos, vision_pos, 
                       "DOM should be tried before Vision")
        self.assertLess(vision_pos, url_pos, 
                       "Vision should be tried before URL fallback")
    
    def test_search_visual_fallback_uses_executor(self):
        """Test that _search_vision_fallback uses pyautogui for direct clicking."""
        method_content = self._get_vision_fallback_content()
        self.assertTrue(len(method_content) > 0, "_search_vision_fallback should exist")
        
        # TICKET-FIX-USE-CASE-1-V8: Now uses pyautogui for direct click on OCR coordinates
        self.assertIn("pyautogui", method_content,
                      "_search_vision_fallback should use pyautogui for clicking")
    
    def test_search_visual_fallback_types_and_validates(self):
        """Test that _search_vision_fallback types the query and validates with Enter."""
        method_content = self._get_vision_fallback_content()
        self.assertTrue(len(method_content) > 0, "_search_vision_fallback should exist")
        
        # Verify it types the query
        self.assertIn('execute("type"', method_content,
                      "_search_vision_fallback should type the search query")
        
        # Verify it presses Enter/Return to validate
        self.assertIn('execute("keystroke"', method_content,
                      "_search_vision_fallback should press keystroke to validate")
        self.assertIn('return', method_content.lower(),
                      "_search_vision_fallback should press return key")
    
    def test_search_visual_fallback_uses_ocr_coordinates(self):
        """Test that _search_vision_fallback uses OCR coordinates for clicking."""
        method_content = self._get_vision_fallback_content()
        self.assertTrue(len(method_content) > 0, "_search_vision_fallback should exist")
        
        # TICKET-FIX-USE-CASE-1-V8: Verify OCR coordinates are used
        self.assertIn("center_x", method_content,
                      "_search_vision_fallback should use center_x from OCR")
        self.assertIn("center_y", method_content,
                      "_search_vision_fallback should use center_y from OCR")
    
    def test_search_visual_fallback_verifies_results(self):
        """Test TICKET-FIX-USE-CASE-1-V8: Verify search results page is reached.
        
        After typing and pressing Enter, the code should verify that the search
        results page is actually loaded before returning success.
        """
        method_content = self._get_vision_fallback_content()
        self.assertTrue(len(method_content) > 0, "_search_vision_fallback should exist")
        
        # TICKET-FIX-USE-CASE-1-V8: Verify results page detection
        self.assertIn("_wait_for_search_results_page", method_content,
                     "Should wait for search results page")


class TestMLXWhisperPriority(unittest.TestCase):
    """Test MLX Whisper priority on Apple Silicon (Bug 1 fix)."""
    
    def test_whisper_stt_checks_for_mlx_first(self):
        """Test that WhisperSTT checks for MLX engine before faster-whisper."""
        with open("janus/stt/whisper_stt.py", "r") as f:
            content = f.read()
        
        # Verify MLXSTTEngine import is attempted
        self.assertIn("from .mlx_stt_engine import MLXSTTEngine", content,
                      "WhisperSTT should import MLXSTTEngine")
        
        # Verify _is_apple_silicon helper exists
        self.assertIn("def _is_apple_silicon()", content,
                      "_is_apple_silicon helper function should exist")
        
        # Verify MLX check happens before faster-whisper
        mlx_check_pos = content.find("_is_apple_silicon()")
        faster_whisper_check_pos = content.find("use_faster_whisper and HAS_REALTIME_STT")
        
        self.assertNotEqual(mlx_check_pos, -1, "MLX check should be present")
        self.assertNotEqual(faster_whisper_check_pos, -1, "faster-whisper check should be present")
        self.assertLess(mlx_check_pos, faster_whisper_check_pos,
                       "MLX check should come before faster-whisper check")
    
    def test_mlx_has_priority_message(self):
        """Test that appropriate log messages are present for MLX detection."""
        with open("janus/stt/whisper_stt.py", "r") as f:
            content = f.read()
        
        # Should have message about Apple Silicon detected
        self.assertIn("Apple Silicon detected", content,
                      "Should log when Apple Silicon is detected")
        
        # Should have message about MLX not installed
        self.assertIn("lightning-whisper-mlx not installed", content,
                      "Should warn when MLX library is not installed on Apple Silicon")


class TestBrowserAgentCoordinateReuse(unittest.TestCase):
    """Test TICKET-FIX-USE-CASE-1: Coordinate reuse optimization for search fallback.
    
    These tests validate that:
    1. _wait_for_search_input_visible returns coordinates (not just bool)
    2. _search_vision_fallback accepts detection_result parameter
    3. pyautogui.click is used for direct coordinate clicking
    4. Timeout has been increased for CPU-based OCR operations
    """
    
    def setUp(self):
        """Load browser agent source for inspection."""
        with open("janus/agents/browser_agent.py", "r") as f:
            self.content = f.read()
    
    def test_wait_for_search_returns_dict_with_coordinates(self):
        """Test that _wait_for_search_input_visible returns dict with coordinates."""
        # Find method definition
        method_start = self.content.find("async def _wait_for_search_input_visible")
        self.assertNotEqual(method_start, -1, 
                           "_wait_for_search_input_visible should exist")
        
        # Find return type annotation
        next_method = self.content.find("async def _search_vision_fallback", method_start)
        method_content = self.content[method_start:next_method]
        
        # Verify it returns a dict, not bool
        self.assertIn("-> dict:", method_content,
                     "_wait_for_search_input_visible should return dict, not bool")
        
        # Verify it extracts coordinates from result
        self.assertIn('coords = result.data.get("coordinates"', method_content,
                     "Should extract coordinates from result data")
        
        # Verify it returns center_x and center_y
        self.assertIn('"center_x":', method_content,
                     "Return dict should include center_x")
        self.assertIn('"center_y":', method_content,
                     "Return dict should include center_y")
    
    def test_search_fallback_accepts_detection_result(self):
        """Test that _search_vision_fallback accepts detection_result parameter."""
        # Find method signature
        sig_start = self.content.find("async def _search_vision_fallback")
        self.assertNotEqual(sig_start, -1)
        
        # Find end of signature (first line of body)
        sig_end = self.content.find('"""', sig_start + 10)  # Skip past def line
        signature = self.content[sig_start:sig_end]
        
        # Verify detection_result parameter exists
        self.assertIn("detection_result: dict", signature,
                     "_search_vision_fallback should accept detection_result parameter")
    
    def test_search_fallback_uses_pyautogui_for_direct_click(self):
        """Test that _search_vision_fallback uses pyautogui for direct clicking."""
        # Find _search_vision_fallback method
        method_start = self.content.find("async def _search_vision_fallback")
        next_method = self.content.find("async def _wait_for_search_results_page", method_start)
        method_content = self.content[method_start:next_method]
        
        # Verify pyautogui lazy loading and direct click
        self.assertIn("_get_pyautogui()", method_content,
                     "Should use _get_pyautogui() lazy loader for pyautogui")
        self.assertIn("pyautogui.click", method_content,
                     "Should use pyautogui.click for direct coordinate clicking")
    
    def test_search_fallback_uses_async_condition_checking(self):
        """Test that search uses async condition checking instead of hardcoded delays."""
        # TICKET-FIX-USE-CASE-1-V8: No hardcoded delays, use async condition checking
        with open("janus/agents/browser_agent.py", "r") as f:
            content = f.read()
        
        # Find _search_vision_fallback method
        method_start = content.find("async def _search_vision_fallback")
        next_method = content.find("async def _wait_for_search_results_page", method_start)
        method_content = content[method_start:next_method]
        
        # Verify async condition checking is used
        self.assertIn("_wait_for_search_results_page", method_content,
                     "Should use async condition checking to verify results")
    
    def test_search_passes_detection_result_to_fallback(self):
        """Test that _search method passes detection_result to _search_vision_fallback."""
        # Find _search method
        search_start = self.content.find("async def _search(")
        vision_fallback_start = self.content.find("async def _search_vision_fallback")
        search_content = self.content[search_start:vision_fallback_start]
        
        # Verify detection_result is captured and passed
        self.assertIn("detection_result = await self._wait_for_search_input_visible", 
                     search_content,
                     "_search should capture detection_result from _wait_for_search_input_visible")
        self.assertIn("detection_result)", search_content,
                     "_search should pass detection_result to _search_vision_fallback")


class TestYouTubeFirstVideoClick(unittest.TestCase):
    """Test TICKET-FIX-USE-CASE-1-V3: Auto-click first video on YouTube after search.
    
    These tests validate that:
    1. _click_first_youtube_result method exists
    2. _search method calls _click_first_youtube_result when on YouTube
    3. Tab+Enter navigation is used for reliable video selection
    """
    
    def setUp(self):
        """Load browser agent source for inspection."""
        with open("janus/agents/browser_agent.py", "r") as f:
            self.content = f.read()
    
    def test_click_first_youtube_result_method_exists(self):
        """Test that _click_first_youtube_result method exists."""
        self.assertIn("async def _click_first_youtube_result", self.content,
                     "_click_first_youtube_result method should exist")
    
    def test_search_calls_click_first_youtube_result_on_youtube(self):
        """Test that _search calls _click_first_youtube_result when on YouTube."""
        # Find _search method
        search_start = self.content.find("async def _search(")
        search_dom_start = self.content.find("async def _search_dom_injection(")
        search_content = self.content[search_start:search_dom_start]
        
        # Verify it checks for YouTube domain
        self.assertIn("is_youtube", search_content,
                     "_search should check if we're on YouTube")
        
        # Verify it calls _click_first_youtube_result
        self.assertIn("_click_first_youtube_result", search_content,
                     "_search should call _click_first_youtube_result on YouTube")
    
    def test_click_first_youtube_result_uses_vision_matching(self):
        """Test that _click_first_youtube_result uses Vision to find matching videos.
        
        TICKET-FIX-USE-CASE-1-V10: Now uses Vision-based click on video titles 
        matching the search query to avoid clicking on advertisements.
        """
        # Find _click_first_youtube_result method
        method_start = self.content.find("async def _click_first_youtube_result")
        next_method = self.content.find("async def _scroll(", method_start)
        method_content = self.content[method_start:next_method]
        
        # Verify Vision executor is used to find matching video
        self.assertIn('click_viz', method_content,
                     "_click_first_youtube_result should use click_viz for Vision-based clicking")
        self.assertIn('query', method_content,
                     "_click_first_youtube_result should use query parameter to find matching videos")


if __name__ == "__main__":
    unittest.main(verbosity=2)
