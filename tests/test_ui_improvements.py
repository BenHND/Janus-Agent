"""
Unit tests for UI improvements (Issue: Improve UI)
Tests for new ERROR states, colors, and font size
"""
import re
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUIImprovements(unittest.TestCase):
    """Test UI improvements for colors, icons, and font size"""

    def test_error_state_in_mic_state(self):
        """Test that MicState has ERROR state"""
        from janus.ui.overlay_types import MicState

        # Test ERROR state exists
        self.assertTrue(hasattr(MicState, "ERROR"), "MicState should have ERROR state")
        self.assertEqual(MicState.ERROR.value, "error", "MicState.ERROR value should be 'error'")

        # Test it's properly enumerated
        all_states = [state.value for state in MicState]
        self.assertIn("error", all_states, "error should be in MicState values")

    def test_error_state_in_status_state(self):
        """Test that StatusState has ERROR state"""
        from janus.ui.overlay_types import StatusState

        # Test ERROR state exists
        self.assertTrue(hasattr(StatusState, "ERROR"), "StatusState should have ERROR state")
        self.assertEqual(StatusState.ERROR.value, "error", "StatusState.ERROR value should be 'error'")

        # Test it's properly enumerated
        all_states = [state.value for state in StatusState]
        self.assertIn("error", all_states, "error should be in StatusState values")

    def test_error_status_text_english(self):
        """Test error status text in English"""
        from janus.ui.overlay_constants import get_status_text

        error_text = get_status_text("error", "en")
        self.assertEqual(error_text, "Error", "English error text should be 'Error'")

    def test_error_status_text_french(self):
        """Test error status text in French"""
        from janus.ui.overlay_constants import get_status_text

        error_text = get_status_text("error", "fr")
        self.assertEqual(error_text, "Erreur", "French error text should be 'Erreur'")

    def test_loading_status_text_english(self):
        """Test loading status text in English"""
        from janus.ui.overlay_constants import get_status_text

        loading_text = get_status_text("loading", "en")
        self.assertEqual(loading_text, "Loading...", "English loading text should be 'Loading...'")

    def test_loading_status_text_french(self):
        """Test loading status text in French"""
        from janus.ui.overlay_constants import get_status_text

        loading_text = get_status_text("loading", "fr")
        self.assertEqual(loading_text, "Chargement...", "French loading text should be 'Chargement...'")

    def test_mic_svg_icons_format(self):
        """Test that SVG icons are properly formatted"""
        from janus.ui.overlay_constants import MIC_OFF_SVG, MIC_ON_SVG

        # Test MIC_OFF_SVG is outline version
        self.assertIn("<svg", MIC_OFF_SVG, "MIC_OFF_SVG should contain SVG tag")
        self.assertIn("stroke=", MIC_OFF_SVG, "MIC_OFF_SVG should be outline (has stroke)")
        self.assertIn('fill="none"', MIC_OFF_SVG, "MIC_OFF_SVG should have fill=none")

        # Test MIC_ON_SVG is solid version
        self.assertIn("<svg", MIC_ON_SVG, "MIC_ON_SVG should contain SVG tag")
        self.assertIn('fill="currentColor"', MIC_ON_SVG, "MIC_ON_SVG should be solid (has fill)")

    def test_ui_uses_dynamic_mic_icons(self):
        """Test that overlay_ui.py uses dynamic microphone icons"""
        ui_path = Path(__file__).parent.parent / "janus/ui/overlay_ui.py"
        content = ui_path.read_text()

        # Test that both SVG icons are imported
        self.assertIn(
            "MIC_OFF_SVG, MIC_ON_SVG",
            content,
            "Should import both MIC_OFF_SVG and MIC_ON_SVG from overlay_constants",
        )

        # Test that separate pixmaps are created
        self.assertIn("pix_mic_off", content, "Should create pix_mic_off pixmap")
        self.assertIn("pix_mic_on", content, "Should create pix_mic_on pixmap")

        # Test that set_icon method exists
        self.assertIn("def set_icon(self", content, "AnimatedMicBtn should have set_icon method")

        # Test that icon is updated based on state
        self.assertIn(
            "self.btn_mic.set_icon",
            content,
            "Should call set_icon to update microphone icon dynamically",
        )

    def test_ui_file_colors(self):
        """Test that overlay_ui.py has correct halo colors"""
        ui_path = Path(__file__).parent.parent / "janus/ui/overlay_ui.py"
        content = ui_path.read_text()

        # Test loading color (Blue/Cyan: 0,191,255)
        self.assertIn(
            "QColor(0, 191, 255",
            content,
            "Loading halo should use Blue/Cyan color (RGB: 0,191,255)",
        )

        # Test error color (Red: 255,59,48)
        self.assertIn(
            "QColor(255, 59, 48",
            content,
            "Error halo should use Red color (RGB: 255,59,48)",
        )

    def test_ui_file_font_size(self):
        """Test that overlay_ui.py has correct font size"""
        ui_path = Path(__file__).parent.parent / "janus/ui/overlay_ui.py"
        content = ui_path.read_text()

        # Test font size is 16px
        self.assertIn("font-size: 16px", content, "Status label should have 16px font-size")

        # Test that 19px is not in status_label style
        status_label_match = re.search(r"#status_label\s*\{[^}]*\}", content, re.DOTALL)
        if status_label_match:
            status_label_style = status_label_match.group()
            self.assertNotIn(
                "19px", status_label_style, "Status label should not have 19px font-size"
            )

    def test_ui_file_error_handling(self):
        """Test that overlay_ui.py handles error state"""
        ui_path = Path(__file__).parent.parent / "janus/ui/overlay_ui.py"
        content = ui_path.read_text()

        # Test error state handling in set_mic_state
        self.assertIn(
            'state_str == "error"', content, "Should handle error state in set_mic_state"
        )

        # Test that get_status_text uses centralized i18n function
        self.assertIn(
            "get_status_text_i18n",
            content,
            "Should use centralized i18n function from overlay_constants",
        )

        # Test error state in set_status
        self.assertIn(
            'status_str == "error"', content, "Should handle error state in set_status"
        )

    def test_ui_file_loading_handling(self):
        """Test that overlay_ui.py handles loading state correctly"""
        ui_path = Path(__file__).parent.parent / "janus/ui/overlay_ui.py"
        content = ui_path.read_text()

        # Test loading state handling in set_mic_state
        self.assertIn(
            'state_str == "loading"', content, "Should handle loading state in set_mic_state"
        )

        # Test loading state in set_status (the critical fix)
        self.assertIn(
            'status_str == "loading"', content, "Should handle loading state in set_status"
        )

        # Verify that set_status calls set_mic_state for loading
        # This ensures the blue halo is applied
        set_status_section = re.search(
            r'def set_status\(.*?\):(.*?)(?=\n    def |\Z)', content, re.DOTALL
        )
        self.assertIsNotNone(set_status_section, "Should find set_status method")
        if set_status_section:
            method_body = set_status_section.group(1)
            self.assertIn(
                "MicState.LOADING",
                method_body,
                "set_status should call set_mic_state(MicState.LOADING) for loading state",
            )


if __name__ == "__main__":
    unittest.main()
