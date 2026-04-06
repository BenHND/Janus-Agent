"""
Unit tests for overlay_constants module

Tests the centralized text strings and SVG icons
"""
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOverlayConstants(unittest.TestCase):
    """Test overlay constants module"""

    def test_status_texts_structure(self):
        """Test that STATUS_TEXTS has expected structure"""
        from janus.ui.overlay_constants import STATUS_TEXTS

        # Check languages exist
        self.assertIn("en", STATUS_TEXTS)
        self.assertIn("fr", STATUS_TEXTS)

        # Check English keys (including new loading and error states)
        en_texts = STATUS_TEXTS["en"]
        self.assertIn("ready", en_texts)
        self.assertIn("listening", en_texts)
        self.assertIn("thinking", en_texts)
        self.assertIn("acting", en_texts)
        self.assertIn("loading", en_texts)  # NEW
        self.assertIn("error", en_texts)    # NEW

        # Check French keys (including new loading and error states)
        fr_texts = STATUS_TEXTS["fr"]
        self.assertIn("ready", fr_texts)
        self.assertIn("listening", fr_texts)
        self.assertIn("thinking", fr_texts)
        self.assertIn("acting", fr_texts)
        self.assertIn("loading", fr_texts)  # NEW
        self.assertIn("error", fr_texts)    # NEW

    def test_get_status_text_english(self):
        """Test get_status_text returns correct English text"""
        from janus.ui.overlay_constants import get_status_text

        self.assertEqual(get_status_text("ready", "en"), "Ready")
        self.assertEqual(get_status_text("listening", "en"), "Listening...")
        self.assertEqual(get_status_text("thinking", "en"), "Thinking...")
        self.assertEqual(get_status_text("acting", "en"), "Acting...")
        self.assertEqual(get_status_text("loading", "en"), "Loading...")  # NEW
        self.assertEqual(get_status_text("error", "en"), "Error")         # NEW

    def test_get_status_text_french(self):
        """Test get_status_text returns correct French text"""
        from janus.ui.overlay_constants import get_status_text

        self.assertEqual(get_status_text("ready", "fr"), "Prêt")
        self.assertEqual(get_status_text("listening", "fr"), "Écoute...")
        self.assertEqual(get_status_text("thinking", "fr"), "Réflexion...")
        self.assertEqual(get_status_text("acting", "fr"), "Action...")
        self.assertEqual(get_status_text("loading", "fr"), "Chargement...")  # NEW
        self.assertEqual(get_status_text("error", "fr"), "Erreur")           # NEW

    def test_get_status_text_default_language(self):
        """Test get_status_text uses English by default"""
        from janus.ui.overlay_constants import get_status_text

        # Should default to English
        self.assertEqual(get_status_text("ready"), "Ready")

    def test_get_status_text_fallback(self):
        """Test get_status_text falls back to English for unknown language"""
        from janus.ui.overlay_constants import get_status_text

        # Unknown language should fall back to English
        self.assertEqual(get_status_text("ready", "de"), "Ready")

    def test_svg_icons_defined(self):
        """Test that SVG icons are defined"""
        from janus.ui.overlay_constants import MIC_OFF_SVG, MIC_ON_SVG

        # Check they are strings
        self.assertIsInstance(MIC_OFF_SVG, str)
        self.assertIsInstance(MIC_ON_SVG, str)

        # Check they contain SVG content
        self.assertIn("<svg", MIC_OFF_SVG)
        self.assertIn("</svg>", MIC_OFF_SVG)
        self.assertIn("<svg", MIC_ON_SVG)
        self.assertIn("</svg>", MIC_ON_SVG)

        # Check for stroke vs fill (outline vs solid)
        self.assertIn("stroke", MIC_OFF_SVG)  # Outline version
        self.assertIn("fill", MIC_ON_SVG)  # Solid version


if __name__ == "__main__":
    unittest.main()
