"""
Unit tests for text input dialog feature

These tests verify the text input dialog integration without requiring Qt/display.
"""
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTextInputFeatureIntegration(unittest.TestCase):
    """Test text input feature integration logic"""

    def test_text_input_dialog_file_exists(self):
        """Test that text_input_dialog.py module exists"""
        import janus.ui
        module_path = Path(janus.ui.__file__).parent / 'text_input_dialog.py'
        self.assertTrue(module_path.exists(), "text_input_dialog.py should exist")

    def test_overlay_ui_has_text_submit_parameter(self):
        """Test that overlay_ui.py has been modified to support text submission"""
        # Read the overlay_ui.py source code
        import janus.ui
        overlay_path = Path(janus.ui.__file__).parent / 'overlay_ui.py'
        source = overlay_path.read_text()
        
        # Check for key additions
        self.assertIn('on_text_submit', source, "overlay_ui should accept on_text_submit callback")
        self.assertIn('_handle_text_input', source, "overlay_ui should have _handle_text_input method")
        self.assertIn('_on_text_submitted', source, "overlay_ui should have _on_text_submitted method")
        self.assertIn('SVG_CHAT', source, "overlay_ui should have SVG_CHAT icon")
        self.assertIn('AnimatedChatBtn', source, "overlay_ui should have AnimatedChatBtn class")

    def test_ui_mode_has_text_submit_handler(self):
        """Test that ui_mode.py has been modified to handle text submission"""
        # Read the ui_mode.py source code
        import janus.modes
        ui_mode_path = Path(janus.modes.__file__).parent / 'ui_mode.py'
        source = ui_mode_path.read_text()
        
        # Check for on_text_submit function
        self.assertIn('def on_text_submit', source, "ui_mode should have on_text_submit function")
        self.assertIn('on_text_submit=on_text_submit', source, "ui_mode should pass on_text_submit to OverlayUI")
        self.assertIn('start_command_worker(text)', source, "on_text_submit should call start_command_worker")

    def test_chat_icon_svg_defined(self):
        """Test that the chat icon SVG is defined in overlay_ui.py"""
        import janus.ui
        overlay_path = Path(janus.ui.__file__).parent / 'overlay_ui.py'
        source = overlay_path.read_text()
        
        # Check for SVG_CHAT definition
        self.assertIn('SVG_CHAT =', source, "SVG_CHAT should be defined")
        # Check it's an SVG with viewBox
        self.assertIn('viewBox="0 0 24 24"', source, "Chat icon should be an SVG")

    def test_settings_button_moved_to_header(self):
        """Test that settings button has been moved to header section"""
        import janus.ui
        overlay_path = Path(janus.ui.__file__).parent / 'overlay_ui.py'
        source = overlay_path.read_text()
        
        # The settings button should now be in the header section (after "header.addStretch()")
        # and before "layout.addLayout(header)"
        header_section = source[source.find('# --- HEADER ---'):source.find('layout.addLayout(header)')]
        
        self.assertIn('self.btn_conf', header_section, "Settings button should be in header")
        self.assertIn('SharpRotatingSettingsBtn', header_section, "Settings button should be created in header")

    def test_chat_button_in_content_area(self):
        """Test that chat button is in the content area"""
        import janus.ui
        overlay_path = Path(janus.ui.__file__).parent / 'overlay_ui.py'
        source = overlay_path.read_text()
        
        # The chat button should be in the content section (after "# --- CONTENU ---")
        content_section = source[source.find('# --- CONTENU ---'):source.find('self._apply_styles')]
        
        self.assertIn('self.btn_chat', content_section, "Chat button should be in content area")
        self.assertIn('AnimatedChatBtn', content_section, "Chat button should use AnimatedChatBtn class")
        self.assertIn('_handle_text_input', content_section, "Chat button should connect to _handle_text_input")


class TestDocumentationUpdates(unittest.TestCase):
    """Test that documentation has been updated"""

    def test_user_manual_updated(self):
        """Test that USER_MANUAL.md has been updated with text input feature"""
        doc_path = Path(__file__).parent.parent / 'docs' / 'user' / 'USER_MANUAL.md'
        content = doc_path.read_text()
        
        self.assertIn('Text Input', content, "USER_MANUAL should mention Text Input")
        self.assertIn('💬', content, "USER_MANUAL should include chat icon")
        # Check case-insensitively for typing instructions
        self.assertIn('type', content.lower(), "USER_MANUAL should explain how to type commands")

    def test_readme_updated(self):
        """Test that README.md has been updated with text input feature"""
        readme_path = Path(__file__).parent.parent / 'README.md'
        content = readme_path.read_text()
        
        self.assertIn('Text Input', content, "README should mention Text Input")
        # Check case-insensitively for dual input explanation
        lower_content = content.lower()
        self.assertTrue(
            'text' in lower_content and 'voice' in lower_content,
            "README should explain dual input methods"
        )

if __name__ == '__main__':
    unittest.main()
