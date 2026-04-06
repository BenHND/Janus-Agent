"""
Unit tests for TICKET-4: Vision grounding & UI actions fast-path

Tests:
1. Stable element_id generation (hash-based)
2. bbox exposure in reasoner format
3. UIAgent fast-path click with element_id
4. Hash-based verification in ActionVerifier
"""
import asyncio
import hashlib
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

try:
    from janus.vision.set_of_marks import InteractiveElement, SetOfMarksEngine
    from janus.vision.action_verifier import ActionVerifier
    from janus.capabilities.agents.ui_agent import UIAgent
    from janus.platform.os.system_bridge import SystemBridgeResult, SystemBridgeStatus

    VISION_AVAILABLE = True
except ImportError as e:
    VISION_AVAILABLE = False
    print(f"Skipping tests: {e}")


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestStableElementID(unittest.TestCase):
    """Test stable element_id generation (TICKET-4 Work Item 1)"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_screenshot_engine = Mock()
        self.mock_ocr_engine = Mock()
        self.mock_element_locator = Mock()

    def test_element_id_stability_same_content(self):
        """Test that same element content produces same element_id"""
        # Create SOM engine
        som = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            element_locator=self.mock_element_locator,
            enable_cache=False,
        )

        # Generate element_id for same content multiple times
        element_type = "button"
        text = "Submit"
        bbox = (100, 200, 80, 40)

        id1 = som._generate_element_id(element_type, text, bbox)
        id2 = som._generate_element_id(element_type, text, bbox)

        # Should generate same ID
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("button_"))

    def test_element_id_changes_with_content(self):
        """Test that different content produces different element_id"""
        som = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            element_locator=self.mock_element_locator,
            enable_cache=False,
        )

        # Different text should produce different IDs
        id1 = som._generate_element_id("button", "Submit", (100, 200, 80, 40))
        id2 = som._generate_element_id("button", "Cancel", (100, 200, 80, 40))
        self.assertNotEqual(id1, id2)

        # Different bbox should produce different IDs
        id3 = som._generate_element_id("button", "Submit", (100, 200, 80, 40))
        id4 = som._generate_element_id("button", "Submit", (200, 300, 80, 40))
        self.assertNotEqual(id3, id4)

    def test_element_id_bbox_quantization(self):
        """Test that bbox quantization makes IDs stable for small movements"""
        som = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            element_locator=self.mock_element_locator,
            enable_cache=False,
        )

        # Small bbox differences (within 10px) should produce same ID
        id1 = som._generate_element_id("button", "Submit", (100, 200, 80, 40))
        id2 = som._generate_element_id("button", "Submit", (102, 203, 81, 39))
        id3 = som._generate_element_id("button", "Submit", (108, 207, 82, 44))

        # Within same quantization bucket (10px)
        self.assertEqual(id1, id2)
        self.assertEqual(id1, id3)

        # Larger difference should produce different ID
        id4 = som._generate_element_id("button", "Submit", (120, 220, 80, 40))
        self.assertNotEqual(id1, id4)

    def test_element_id_text_normalization(self):
        """Test that text normalization makes IDs case-insensitive"""
        som = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            element_locator=self.mock_element_locator,
            enable_cache=False,
        )

        # Case differences should produce same ID
        id1 = som._generate_element_id("button", "Submit", (100, 200, 80, 40))
        id2 = som._generate_element_id("button", "SUBMIT", (100, 200, 80, 40))
        id3 = som._generate_element_id("button", "submit", (100, 200, 80, 40))

        self.assertEqual(id1, id2)
        self.assertEqual(id1, id3)

        # Whitespace should be normalized
        id4 = som._generate_element_id("button", " Submit ", (100, 200, 80, 40))
        self.assertEqual(id1, id4)


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestBboxExposure(unittest.TestCase):
    """Test bbox exposure in reasoner format (TICKET-4 Work Item 2)"""

    def test_to_reasoner_format_includes_bbox(self):
        """Test that to_reasoner_format includes bbox"""
        element = InteractiveElement(
            element_id="button_a3f2",
            element_type="button",
            text="Submit Form",
            bbox=(100, 200, 80, 40),
            confidence=0.95,
        )

        reasoner_format = element.to_reasoner_format()

        # Should include all expected fields
        self.assertIn("id", reasoner_format)
        self.assertIn("t", reasoner_format)
        self.assertIn("txt", reasoner_format)
        self.assertIn("bb", reasoner_format)  # TICKET-4: bbox included

        # Verify values
        self.assertEqual(reasoner_format["id"], "button_a3f2")
        self.assertEqual(reasoner_format["t"], "button")
        self.assertEqual(reasoner_format["txt"], "Submit Form")
        self.assertEqual(reasoner_format["bb"], (100, 200, 80, 40))

    def test_reasoner_format_truncates_long_text(self):
        """Test that long text is truncated for token efficiency"""
        long_text = "A" * 100
        element = InteractiveElement(
            element_id="text_9b4e",
            element_type="text",
            text=long_text,
            bbox=(50, 100, 200, 30),
            confidence=0.85,
        )

        reasoner_format = element.to_reasoner_format()

        # Text should be truncated to 80 chars
        self.assertEqual(len(reasoner_format["txt"]), 80)
        self.assertEqual(reasoner_format["txt"], long_text[:80])


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestUIAgentFastPath(unittest.TestCase):
    """Test UIAgent fast-path click (TICKET-4 Work Item 3)"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_bridge = Mock()
        self.ui_agent = UIAgent(system_bridge=self.mock_bridge)

    @patch("asyncio.to_thread")
    def test_fast_path_click_with_element_id(self, mock_to_thread):
        """Test fast-path click when element_id resolves in SOM"""
        # Create mock SOM engine with element
        mock_som = Mock()
        mock_som.is_available.return_value = True
        mock_element = InteractiveElement(
            element_id="button_a3f2",
            element_type="button",
            text="Submit",
            bbox=(100, 200, 80, 40),  # Center: (140, 220)
            confidence=0.95,
        )
        mock_som.get_element_by_id.return_value = mock_element

        # Mock SystemBridge click success
        self.mock_bridge.click.return_value = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS
        )

        # Configure async mock
        async def mock_async():
            return SystemBridgeResult(status=SystemBridgeStatus.SUCCESS)

        mock_to_thread.return_value = mock_async()

        # Execute click with element_id
        args = {"element_id": "button_a3f2"}
        context = {"vision_engine": mock_som}

        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.ui_agent._click(args, context))

            # Should succeed via fast-path
            self.assertEqual(result["status"], "success")
            self.assertIn("fast-path", result["message"])

            # Should have called SOM to resolve element
            mock_som.get_element_by_id.assert_called_once_with("button_a3f2")

            # Should have clicked at center of bbox
            # Note: asyncio.to_thread is mocked, so we can't verify the exact call
            # In real execution, bridge.click would be called with (140, 220)
        finally:
            loop.close()

    @patch("janus.capabilities.agents.ui_agent.VisionActionMapper")
    def test_fallback_to_vam_when_element_id_not_found(self, mock_vam_class):
        """Test fallback to VisionActionMapper when element_id not in SOM"""
        # Create mock SOM engine without element
        mock_som = Mock()
        mock_som.is_available.return_value = True
        mock_som.get_element_by_id.return_value = None  # Element not found

        # Mock VisionActionMapper
        mock_vam = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_vam.click_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        # Execute click with element_id
        args = {"element_id": "button_xyz"}
        context = {"vision_engine": mock_som}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.ui_agent._click(args, context))

            # Should fall back to VisionActionMapper
            self.assertEqual(result["status"], "success")
            mock_vam.click_viz.assert_called_once()
        finally:
            loop.close()

    def test_fast_path_performance(self):
        """Test that fast-path click is fast (<300ms target)"""
        # Create mock SOM engine with element
        mock_som = Mock()
        mock_som.is_available.return_value = True
        mock_element = InteractiveElement(
            element_id="button_fast",
            element_type="button",
            text="Quick",
            bbox=(100, 200, 80, 40),
            confidence=0.95,
        )
        mock_som.get_element_by_id.return_value = mock_element

        # Mock instant click
        self.mock_bridge.click.return_value = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS
        )

        args = {"element_id": "button_fast"}
        context = {"vision_engine": mock_som}

        # Measure time
        start = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.ui_agent._click(args, context))
            duration_ms = (time.time() - start) * 1000

            # Should be very fast (well under 300ms in mock scenario)
            # In real scenario with actual screenshot, should still be <300ms
            self.assertLess(duration_ms, 100)  # Mock should be near-instant
            self.assertEqual(result["status"], "success")
        finally:
            loop.close()


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestHashBasedVerification(unittest.TestCase):
    """Test hash-based verification (TICKET-4 Work Item 4)"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_screenshot_engine = Mock()
        self.verifier = ActionVerifier(screenshot_engine=self.mock_screenshot_engine)

    def test_verify_action_detects_change(self):
        """Test that hash-based verification detects screen changes"""
        # Create two different screenshots
        from PIL import Image

        pre_screenshot = Image.new("RGB", (100, 100), color="red")
        post_screenshot = Image.new("RGB", (100, 100), color="blue")

        self.mock_screenshot_engine.capture_screen.return_value = post_screenshot

        # Verify action
        result = self.verifier.verify_action("click", "button", pre_screenshot)

        # Should detect change
        self.assertTrue(result["verified"])
        self.assertGreater(result["confidence"], 0.8)
        self.assertIn("hash mismatch", result["reason"].lower())

    def test_verify_action_no_change(self):
        """Test verification when screen doesn't change"""
        from PIL import Image

        # Same screenshot before and after
        screenshot = Image.new("RGB", (100, 100), color="red")

        self.mock_screenshot_engine.capture_screen.return_value = screenshot

        # Verify action
        result = self.verifier.verify_action("click", "button", screenshot)

        # Should still verify as success (no change is valid for some actions)
        self.assertTrue(result["verified"])
        self.assertIn("unchanged", result["reason"].lower())

    def test_screenshot_hash_computation(self):
        """Test screenshot hash computation"""
        from PIL import Image

        screenshot = Image.new("RGB", (100, 100), color="red")
        hash1 = self.verifier._compute_screenshot_hash(screenshot)

        # Hash should be consistent
        hash2 = self.verifier._compute_screenshot_hash(screenshot)
        self.assertEqual(hash1, hash2)

        # Hash should be 16 characters
        self.assertEqual(len(hash1), 16)

        # Different screenshot should have different hash
        screenshot2 = Image.new("RGB", (100, 100), color="blue")
        hash3 = self.verifier._compute_screenshot_hash(screenshot2)
        self.assertNotEqual(hash1, hash3)


if __name__ == "__main__":
    unittest.main()
