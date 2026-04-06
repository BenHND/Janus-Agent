"""
TICKET-SAFE-001: Validation de Succès Obligatoire (Double Check)

Tests for mandatory goal verification before task completion.

This feature ensures the agent cannot declare "done" when visual error
indicators are present on screen (e.g., "Mot de passe incorrect").

Test scenarios:
1. Agent declares done with no errors → Task completes
2. Agent declares done with visible error → Task continues for self-correction
3. Vision verification correctly detects error indicators
4. Agent successfully self-corrects after failed verification
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from PIL import Image
import numpy as np

from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent, ActionResult, ErrorType
from janus.vision.vision_cognitive_engine import VisionCognitiveEngine
from janus.constants import IntentType


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestVisionGoalVerification(unittest.TestCase):
    """Test VisionCognitiveEngine.verify_goal_achievement()"""
    
    def setUp(self):
        """Set up test environment"""
        # Create vision engine without loading models (testing logic only)
        self.vision_engine = VisionCognitiveEngine(lazy_load=True)
        
        # Create mock screenshot
        self.mock_screenshot = Image.new("RGB", (800, 600), color="white")
    
    def test_verify_goal_achievement_no_errors(self):
        """Test: verify_goal_achievement returns success when no errors detected"""
        # Mock detect_errors to return no errors
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": False,
                "confidence": 0.0,
                "indicators": [],
            }
            
            result = self.vision_engine.verify_goal_achievement(
                goal="Se connecter à Gmail",
                screenshot=self.mock_screenshot,
                language="fr"
            )
            
            # Should return success when no errors detected
            self.assertTrue(result["success"], "Should succeed when no errors detected")
            self.assertIn("confidence", result)
            self.assertIn("reason", result)
            self.assertEqual(result["errors_detected"], [])
    
    def test_verify_goal_achievement_with_visual_error(self):
        """Test: verify_goal_achievement returns failure when error detected"""
        # Mock detect_errors to return an error
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": True,
                "error_type": "error message",
                "confidence": 0.85,
                "indicators": [{"type": "error message", "score": 0.85}],
            }
            
            result = self.vision_engine.verify_goal_achievement(
                goal="Se connecter à Gmail",
                screenshot=self.mock_screenshot,
                language="fr"
            )
            
            # Should return failure when error detected
            self.assertFalse(result["success"], "Should fail when error detected")
            self.assertGreater(result["confidence"], 0.5)
            self.assertIn("Erreur", result["reason"])
            self.assertEqual(len(result["errors_detected"]), 1)
    
    def test_verify_goal_achievement_with_ai_verification(self):
        """Test: verify_goal_achievement uses AI when models available"""
        # Mock AI models as available
        self.vision_engine.caption_model = MagicMock()
        self.vision_engine.processor = MagicMock()
        
        # Mock detect_errors to return no errors (so we reach AI verification)
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": False,
                "confidence": 0.0,
                "indicators": [],
            }
            
            # Mock answer_question to return YES
            with patch.object(self.vision_engine, 'answer_question') as mock_qa:
                mock_qa.return_value = {
                    "answer": "OUI",
                    "confidence": 0.9,
                }
                
                result = self.vision_engine.verify_goal_achievement(
                    goal="Se connecter à Gmail",
                    screenshot=self.mock_screenshot,
                    language="fr"
                )
                
                # Should succeed with AI verification
                self.assertTrue(result["success"])
                self.assertEqual(result["method"], "ai_verification")
                self.assertGreater(result["confidence"], 0.7)
    
    def test_verify_goal_achievement_with_ai_detects_error(self):
        """Test: AI verification can detect errors not caught by heuristics"""
        # Mock AI models as available
        self.vision_engine.caption_model = MagicMock()
        self.vision_engine.processor = MagicMock()
        
        # Mock detect_errors to return no errors (so we reach AI verification)
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": False,
                "confidence": 0.0,
                "indicators": [],
            }
            
            # Mock answer_question to return NO (AI detects error)
            with patch.object(self.vision_engine, 'answer_question') as mock_qa:
                mock_qa.return_value = {
                    "answer": "NON, je vois un message d'erreur",
                    "confidence": 0.85,
                }
                
                result = self.vision_engine.verify_goal_achievement(
                    goal="Se connecter à Gmail",
                    screenshot=self.mock_screenshot,
                    language="fr"
                )
                
                # Should fail with AI verification
                self.assertFalse(result["success"], "AI should detect error")
                self.assertEqual(result["method"], "ai_verification")
                self.assertIn("NON atteint", result["reason"])


class TestAgentExecutorGoalVerification(unittest.TestCase):
    """Test AgentExecutorV3 integration with goal verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.registry = AgentRegistry()
        self.executor = AgentExecutorV3(
            agent_registry=self.registry,
            enable_vision_recovery=True,
            enable_replanning=True,
        )
        
        # Mock vision engine
        self.mock_vision = MagicMock(spec=VisionCognitiveEngine)
        self.executor._vision_engine = self.mock_vision
        
        # Mock reasoner
        self.mock_reasoner = MagicMock()
        self.executor._reasoner = self.mock_reasoner
        
        self.intent = Intent(
            action="navigate_url",
            confidence=0.9,
            raw_command="Se connecter à Gmail",
            parameters={"language": "fr"},
        )
    
    @async_test
    async def test_done_action_triggers_verification(self):
        """Test: 'done' action triggers mandatory verification"""
        # Mock screenshot capture by mocking the screenshot_engine module directly
        mock_screenshot = Image.new("RGB", (800, 600), color="white")
        
        # Import and patch at module level
        import janus.vision.screenshot_engine as screenshot_module
        original_screenshot_class = screenshot_module.ScreenshotEngine
        
        # Create mock class
        class MockScreenshotEngine:
            def capture_screen(self):
                return mock_screenshot
        
        # Temporarily replace the class
        screenshot_module.ScreenshotEngine = MockScreenshotEngine
        
        try:
            # Mock reasoner to return 'done' action immediately
            self.mock_reasoner.decide_next_action.return_value = {
                "action": "done",
                "reasoning": "Task completed"
            }
            
            # Mock verification to succeed
            self.mock_vision.verify_goal_achievement.return_value = {
                "success": True,
                "confidence": 0.9,
                "reason": "Goal achieved",
                "errors_detected": [],
                "method": "ai_verification"
            }
            
            # Execute dynamic loop
            result = await self.executor.execute_dynamic_loop(
                user_goal="Se connecter à Gmail",
                intent=self.intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=5
            )
            
            # Verify that verification was called
            self.mock_vision.verify_goal_achievement.assert_called_once()
            call_args = self.mock_vision.verify_goal_achievement.call_args
            self.assertEqual(call_args[1]["goal"], "Se connecter à Gmail")
            self.assertEqual(call_args[1]["language"], "fr")
            
            # Verify task completed successfully
            self.assertTrue(result.success, "Task should complete when verification passes")
            self.assertEqual(len(result.results), 1)
            self.assertEqual(result.results[0].action_type, "done")
        finally:
            # Restore original class
            screenshot_module.ScreenshotEngine = original_screenshot_class
    
    @async_test
    async def test_verification_failure_prevents_completion(self):
        """Test: Failed verification prevents task completion and triggers retry"""
        # Mock screenshot capture
        mock_screenshot = Image.new("RGB", (800, 600), color="white")
        
        # Import and patch at module level
        import janus.vision.screenshot_engine as screenshot_module
        original_screenshot_class = screenshot_module.ScreenshotEngine
        
        # Create mock class
        class MockScreenshotEngine:
            def capture_screen(self):
                return mock_screenshot
        
        # Temporarily replace the class
        screenshot_module.ScreenshotEngine = MockScreenshotEngine
        
        try:
            # Mock reasoner to return 'done' first, then another action, then done again
            self.mock_reasoner.decide_next_action.side_effect = [
                {"action": "done", "reasoning": "Task completed"},  # First attempt (will fail verification)
                {"action": "click", "args": {"text": "Réessayer"}},  # Self-correction
                {"action": "done", "reasoning": "Task completed"},  # Second attempt (will pass)
            ]
            
            # Mock verification: first fails, second succeeds
            self.mock_vision.verify_goal_achievement.side_effect = [
                {
                    "success": False,
                    "confidence": 0.85,
                    "reason": "Mot de passe incorrect détecté",
                    "errors_detected": [{"type": "error_keyword", "keyword": "incorrect"}],
                    "method": "ocr_heuristic"
                },
                {
                    "success": True,
                    "confidence": 0.9,
                    "reason": "Goal achieved",
                    "errors_detected": [],
                    "method": "ai_verification"
                }
            ]
            
            # Mock agent registry to simulate click action
            async def mock_execute_async(module, action, args, context):
                return {
                    "status": "success",
                    "message": "Clicked",
                    "data": {}
                }
            
            self.registry.execute_async = mock_execute_async
            
            # Execute dynamic loop
            result = await self.executor.execute_dynamic_loop(
                user_goal="Se connecter à Gmail",
                intent=self.intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=10
            )
            
            # Verify that verification was called twice
            self.assertEqual(self.mock_vision.verify_goal_achievement.call_count, 2,
                           "Verification should be called twice (failed then succeeded)")
            
            # Verify task completed after self-correction
            self.assertTrue(result.success, "Task should complete after self-correction")
            
            # Check that first verification failure was recorded
            verification_failed_result = next(
                (r for r in result.results if r.action_type == "done_verification_failed"),
                None
            )
            self.assertIsNotNone(verification_failed_result, "Should record verification failure")
            self.assertFalse(verification_failed_result.success)
            self.assertIn("incorrect", verification_failed_result.error.lower())
        finally:
            # Restore original class
            screenshot_module.ScreenshotEngine = original_screenshot_class
    
    @async_test
    async def test_verification_error_injected_into_context(self):
        """Test: Verification error is injected into reasoner context"""
        # Mock screenshot capture
        mock_screenshot = Image.new("RGB", (800, 600), color="white")
        
        # Import and patch at module level
        import janus.vision.screenshot_engine as screenshot_module
        original_screenshot_class = screenshot_module.ScreenshotEngine
        
        # Create mock class
        class MockScreenshotEngine:
            def capture_screen(self):
                return mock_screenshot
        
        # Temporarily replace the class
        screenshot_module.ScreenshotEngine = MockScreenshotEngine
        
        try:
            # Track memory updates across iterations
            memory_snapshots = []
            
            # Mock reasoner to return 'done' once (will fail), then capture memory
            call_count = [0]
            def mock_decide(user_goal, system_state, visual_context, memory, language):
                call_count[0] += 1
                if call_count[0] == 1:
                    return {"action": "done", "reasoning": "Task completed"}
                else:
                    # Capture memory to verify error was injected
                    memory_snapshots.append(memory.copy())
                    return {"action": "done", "reasoning": "Really done now"}
            
            self.mock_reasoner.decide_next_action.side_effect = mock_decide
            
            # Mock verification: first fails, second succeeds
            self.mock_vision.verify_goal_achievement.side_effect = [
                {
                    "success": False,
                    "confidence": 0.85,
                    "reason": "Erreur de connexion détectée",
                    "errors_detected": [{"type": "connection_error"}],
                    "method": "error_detection"
                },
                {
                    "success": True,
                    "confidence": 0.9,
                    "reason": "Goal achieved",
                    "errors_detected": [],
                    "method": "ai_verification"
                }
            ]
            
            # Execute dynamic loop
            result = await self.executor.execute_dynamic_loop(
                user_goal="Se connecter à Gmail",
                intent=self.intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=5
            )
            
            # Verify error was injected into memory
            self.assertGreater(len(memory_snapshots), 0, "Should have captured memory snapshot")
            memory = memory_snapshots[0]
            
            self.assertIn("verification_failed", memory, "Should flag verification failure")
            self.assertTrue(memory["verification_failed"])
            self.assertIn("verification_error", memory)
            self.assertIn("last_error", memory)
            self.assertIn("pensais avoir fini", memory["last_error"].lower())
        finally:
            # Restore original class
            screenshot_module.ScreenshotEngine = original_screenshot_class


class TestGoalVerificationEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.vision_engine = VisionCognitiveEngine(lazy_load=True)
        self.mock_screenshot = Image.new("RGB", (800, 600), color="white")
    
    def test_verify_goal_with_ocr_fallback(self):
        """Test: OCR fallback detects error keywords when AI unavailable"""
        # Ensure AI models are not available
        self.vision_engine.caption_model = None
        self.vision_engine.processor = None
        
        # Mock detect_errors to return no errors (forcing OCR fallback)
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": False,
                "confidence": 0.0,
                "indicators": [],
            }
            
            # Mock OCR to return text with error keywords
            with patch('janus.vision.ocr_engine.OCREngine') as MockOCR:
                mock_ocr = MockOCR.return_value
                mock_ocr.extract_text.return_value = {
                    "text": "Mot de passe incorrect. Veuillez réessayer.",
                    "confidence": 0.9
                }
                
                result = self.vision_engine.verify_goal_achievement(
                    goal="Se connecter",
                    screenshot=self.mock_screenshot,
                    language="fr"
                )
                
                # Should detect error via OCR
                self.assertFalse(result["success"], "OCR should detect error keywords")
                self.assertEqual(result["method"], "ocr_heuristic")
                self.assertGreater(len(result["errors_detected"]), 0)
    
    def test_verify_goal_fallback_when_vision_unavailable(self):
        """Test: Graceful fallback when vision is completely unavailable"""
        # Ensure all vision components are unavailable
        self.vision_engine.caption_model = None
        self.vision_engine.processor = None
        
        # Mock detect_errors to return no errors
        with patch.object(self.vision_engine, 'detect_errors') as mock_detect:
            mock_detect.return_value = {
                "has_error": False,
                "confidence": 0.0,
                "indicators": [],
            }
            
            # Mock OCR to fail
            with patch('janus.vision.ocr_engine.OCREngine') as MockOCR:
                MockOCR.side_effect = Exception("OCR unavailable")
                
                result = self.vision_engine.verify_goal_achievement(
                    goal="Se connecter",
                    screenshot=self.mock_screenshot,
                    language="fr"
                )
                
                # Should return optimistic fallback
                self.assertTrue(result["success"], "Should optimistically assume success when no verification available")
                self.assertEqual(result["method"], "fallback_optimistic")
                self.assertLess(result["confidence"], 0.7, "Confidence should be lower for fallback")


if __name__ == '__main__':
    unittest.main()
