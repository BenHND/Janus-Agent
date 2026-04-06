"""
VisionCognitiveEngine - AI-powered visual understanding
Part of PHASE-22: Vision Cognitive & Perception IA
Updated for TICKET-ARCH-002: Structural data over literary descriptions
Updated for TICKET-ARCH-FINAL: Zero Magic String & Complete Internationalization

Features:
- Element detection with Set-of-Marks (via VisualGroundingEngine)
- Screen understanding and element detection
- Visual Q&A capabilities
- Text-image matching with CLIP
- DEPRECATED: Literary image descriptions (use structured data instead)
"""

import json
import logging
import os
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image
else:
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        np = None  # type: ignore
        Image = None  # type: ignore

logger = logging.getLogger(__name__)

# Constants for error detection
MAX_OCR_TEXT_LENGTH = 500  # Maximum OCR text length for LLM classification


class VisionCognitiveEngine:
    """
    AI-powered vision cognitive engine for screen understanding

    TICKET-ARCH-002: Updated to focus on structural data and Set-of-Marks grounding.
    
    Features:
    - detect_interactive_elements(): Set-of-Marks element detection (NEW)
    - find_element(): Locate UI elements using natural language
    - answer_question(): Answer visual questions about screen content
    - detect_errors(): Identify visual error indicators
    - describe(): Generate screen description (DEPRECATED: use structured data)

    Supports:
    - VisualGroundingEngine for Set-of-Marks element detection
    - BLIP-2 for visual Q&A (when needed)
    - CLIP for text-image matching
    - Fallback to OCR when AI models unavailable
    """

    def __init__(
        self,
        model_type: str = "blip2",
        device: str = "auto",
        enable_cache: bool = True,
        cache_size: int = 50,
        models_dir: Optional[str] = None,
        lazy_load: bool = False,
    ):
        """
        Initialize Vision Cognitive Engine

        Args:
            model_type: "blip2", "llava", or "clip"
            device: "cpu", "cuda", "mps" (Metal on Mac), or "auto"
            enable_cache: Enable caching of recent captions
            cache_size: Maximum number of cached captions
            models_dir: Directory for vision models (README #4)
            lazy_load: If True, models are not loaded immediately (load with preload_models_async)
        """
        self.model_type = model_type
        self.device = self._detect_device(device)
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self._lazy_load = lazy_load

        # README #4: Store models directory (fallback to env var or default)
        self.models_dir = models_dir or os.environ.get("SPECTRA_VISION_MODELS_DIR", "models/vision")

        # Cache for recent captions
        self._caption_cache: Dict[str, Any] = {}
        self._cache_order: List[str] = []

        # Model placeholders
        self.caption_model = None
        self.clip_model = None
        self.processor = None
        self.clip_processor = None
        
        # TICKET-ARCH-002: Visual grounding engine for Set-of-Marks
        self._grounding_engine = None
        
        # Track if models are being loaded to avoid duplicate loading
        self._loading = False
        self._models_loaded = False

        # Try to initialize models unless lazy loading is enabled
        if not lazy_load:
            self._init_models()

    def _detect_device(self, device: str) -> str:
        """Detect optimal device for inference"""
        if device != "auto":
            return device

        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            elif torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        except ImportError:
            return "cpu"

    def _init_models(self):
        """
        Initialize vision AI models (README #4: uses local models directory).
        
        TICKET 203 (B2): Uses global vision model cache to prevent reloading.
        """
        if self._loading or self._models_loaded:
            return
            
        # TICKET 203 (B2): Check cache first
        from .vision_model_cache import get_vision_cache
        cache = get_vision_cache()
        
        # Try to load from cache
        if cache.has_blip2():
            blip2_model, blip2_processor, device = cache.get_blip2()
            if blip2_model is not None:
                self.caption_model = blip2_model
                self.processor = blip2_processor
                self.device = device
                logger.info(f"✓ BLIP-2 loaded from cache (device={device})")
                self._models_loaded = True
        
        if cache.has_clip():
            clip_model, clip_processor, device = cache.get_clip()
            if clip_model is not None:
                self.clip_model = clip_model
                self.clip_processor = clip_processor
                self.device = device
                logger.info(f"✓ CLIP loaded from cache (device={device})")
                self._models_loaded = True
        
        # If both models are cached, we're done
        if cache.has_blip2() and cache.has_clip():
            logger.debug("All vision models loaded from cache")
            return
            
        self._loading = True
        try:
            import torch
            from transformers import (
                Blip2ForConditionalGeneration,
                Blip2Processor,
                CLIPModel,
                CLIPProcessor,
            )

            # Set environment variables for local models directory if not already set
            # This respects the global setup from janus.config.model_paths
            if self.models_dir:
                if "TRANSFORMERS_CACHE" not in os.environ:
                    os.environ["TRANSFORMERS_CACHE"] = self.models_dir
                if "HF_HOME" not in os.environ:
                    os.environ["HF_HOME"] = self.models_dir
                logger.info(f"Using vision models directory: {self.models_dir}")

            logger.info(f"Initializing vision models on device: {self.device}")

            # Initialize BLIP-2 for captioning (only if not cached)
            if self.model_type in ["blip2", "auto"] and not cache.has_blip2():
                try:
                    logger.info("Loading BLIP-2 model (this may take a moment)...")
                    self.processor = Blip2Processor.from_pretrained(
                        "Salesforce/blip2-opt-2.7b",
                        cache_dir=self.models_dir if self.models_dir else None,
                    )
                    self.caption_model = Blip2ForConditionalGeneration.from_pretrained(
                        "Salesforce/blip2-opt-2.7b",
                        torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                        cache_dir=self.models_dir if self.models_dir else None,
                    )
                    self.caption_model.to(self.device)
                    # TICKET 203 (B2): Cache the loaded models
                    cache.set_blip2(self.caption_model, self.processor, self.device)
                    logger.info("✓ BLIP-2 model loaded successfully and cached")
                except Exception as e:
                    logger.warning(f"Could not load BLIP-2 model: {e}")

            # Initialize CLIP for text-image matching (only if not cached)
            if not cache.has_clip():
                try:
                    logger.info("Loading CLIP model...")
                    self.clip_processor = CLIPProcessor.from_pretrained(
                        "openai/clip-vit-base-patch32",
                        cache_dir=self.models_dir if self.models_dir else None,
                    )
                    self.clip_model = CLIPModel.from_pretrained(
                        "openai/clip-vit-base-patch32",
                        cache_dir=self.models_dir if self.models_dir else None,
                    )
                    self.clip_model.to(self.device)
                    # TICKET 203 (B2): Cache the loaded models
                    cache.set_clip(self.clip_model, self.clip_processor, self.device)
                    logger.info("✓ CLIP model loaded successfully and cached")
                except Exception as e:
                    logger.warning(f"Could not load CLIP model: {e}")
            
            self._models_loaded = True

        except ImportError as e:
            logger.warning(
                f"Vision AI models not available: {e}. "
                "Install transformers and torch: pip install transformers torch"
            )
            warnings.warn(
                "VisionCognitiveEngine requires transformers and torch. "
                "Falling back to OCR-only mode."
            )
        finally:
            self._loading = False

    async def preload_models_async(self):
        """
        Asynchronously preload vision models in the background.
        
        This allows models to be loaded without blocking the main thread,
        improving application startup time when vision features are enabled.
        
        Returns:
            bool: True if models loaded successfully, False otherwise
        """
        import asyncio
        
        if self._models_loaded:
            logger.debug("Vision models already loaded")
            return True
            
        if self._loading:
            logger.debug("Vision models are already being loaded")
            # Wait for loading to complete
            while self._loading:
                await asyncio.sleep(0.1)
            return self._models_loaded
        
        logger.info("Starting async preload of vision models...")
        start_time = time.time()
        
        # Run model loading in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._init_models)
            duration = time.time() - start_time
            if self._models_loaded:
                logger.info(f"✓ Vision models preloaded successfully in {duration:.2f}s")
                return True
            else:
                logger.warning(f"Vision models preload completed but models not available ({duration:.2f}s)")
                return False
        except Exception as e:
            logger.error(f"Failed to preload vision models: {e}")
            return False

    def describe(self, image: Any, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a description of the image

        DEPRECATED: This method generates literary descriptions.
        For LLM consumption, use detect_interactive_elements() for structured data.

        Args:
            image: PIL Image to analyze
            prompt: Optional prompt to guide description

        Returns:
            Dictionary with:
            - description: Human-readable description
            - confidence: Confidence score (0-1)
            - duration_ms: Processing time
            - cached: Whether result was from cache
        """
        logger.warning(
            "describe() is deprecated. Use detect_interactive_elements() for structured data."
        )
        start_time = time.time()

        # Check cache
        cache_key = self._get_image_hash(image)
        if self.enable_cache and cache_key in self._caption_cache:
            cached_result = self._caption_cache[cache_key].copy()
            cached_result["cached"] = True
            cached_result["duration_ms"] = 0
            return cached_result

        # Generate description
        if self.caption_model and self.processor:
            try:
                import torch

                # Prepare inputs
                if prompt:
                    inputs = self.processor(image, text=prompt, return_tensors="pt")
                else:
                    inputs = self.processor(image, return_tensors="pt")

                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Generate caption
                with torch.no_grad():
                    generated_ids = self.caption_model.generate(**inputs, max_length=50)

                description = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[
                    0
                ].strip()

                result = {
                    "description": description,
                    "confidence": 0.85,  # BLIP-2 generally has high confidence
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "cached": False,
                    "method": "blip2",
                }

                # Cache result
                self._cache_result(cache_key, result)

                return result

            except Exception as e:
                logger.error(f"Error generating caption with BLIP-2: {e}")

        # Fallback to basic description
        return {
            "description": f"Image of size {image.size[0]}x{image.size[1]}",
            "confidence": 0.1,
            "duration_ms": int((time.time() - start_time) * 1000),
            "cached": False,
            "method": "fallback",
        }

    def detect_interactive_elements(
        self, image: Any, region: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, Any]:
        """
        TICKET-ARCH-002: Detect interactive elements with Set-of-Marks IDs

        This is the NEW preferred method for screen analysis. It returns
        structured data instead of literary descriptions.

        Args:
            image: PIL Image to analyze
            region: Optional region to analyze (x, y, width, height)

        Returns:
            Dictionary with:
            - elements: List of GroundedElement objects with IDs
            - llm_text: Formatted text list for LLM consumption
            - count: Number of elements detected
            - duration_ms: Processing time
            - method: Detection method used
        """
        start_time = time.time()

        # Lazy-initialize grounding engine
        if self._grounding_engine is None:
            try:
                from .visual_grounding_engine import VisualGroundingEngine

                self._grounding_engine = VisualGroundingEngine(
                    use_florence=True,  # Prefer Florence-2 if available
                    min_confidence=0.5,
                )
                logger.info("✓ Visual grounding engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize visual grounding engine: {e}")
                return {
                    "elements": [],
                    "llm_text": "Visual grounding unavailable",
                    "count": 0,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "method": "error",
                    "error": str(e),
                }

        # Detect elements
        elements = self._grounding_engine.detect_interactive_elements(image, region)

        # Generate LLM-friendly text
        llm_text = self._grounding_engine.generate_llm_list(elements)

        return {
            "elements": elements,
            "llm_text": llm_text,
            "count": len(elements),
            "duration_ms": int((time.time() - start_time) * 1000),
            "method": self._grounding_engine.get_info()["method"],
        }

    def find_element(
        self, image: Any, text_query: str, threshold: float = 0.25
    ) -> Optional[Dict[str, Any]]:
        """
        Find UI element in image using natural language

        Args:
            image: PIL Image to search
            text_query: Natural language description of element
            threshold: Minimum similarity score (0-1)

        Returns:
            Dictionary with:
            - text: Matched text
            - score: Similarity score
            - bbox: Bounding box (x, y, width, height)
            - method: Detection method used
            Or None if not found
        """
        if not self.clip_model or not self.clip_processor:
            logger.warning("CLIP model not available for element finding")
            return None

        try:
            import torch

            # Process image and text with CLIP
            inputs = self.clip_processor(
                text=[text_query], images=image, return_tensors="pt", padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.clip_model(**inputs)

            # Get similarity score
            logits_per_image = outputs.logits_per_image
            similarity = torch.nn.functional.softmax(logits_per_image, dim=1)[0, 0].item()

            if similarity >= threshold:
                # For simplicity, return center of image
                # In production, this would use object detection
                width, height = image.size
                return {
                    "text": text_query,
                    "score": similarity,
                    "bbox": (width // 4, height // 4, width // 2, height // 2),
                    "method": "clip",
                    "confidence": similarity,
                }

            return None

        except Exception as e:
            logger.error(f"Error finding element with CLIP: {e}")
            return None

    def answer_question(self, image: Any, question: str) -> Dict[str, Any]:
        """
        Answer a question about the image

        Args:
            image: PIL Image to analyze
            question: Question in natural language

        Returns:
            Dictionary with:
            - answer: Answer to the question
            - confidence: Confidence score
            - duration_ms: Processing time
        """
        start_time = time.time()

        if self.caption_model and self.processor:
            try:
                import torch

                # BLIP-2 supports visual question answering
                inputs = self.processor(image, text=question, return_tensors="pt")
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    generated_ids = self.caption_model.generate(**inputs, max_length=30)

                answer = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[
                    0
                ].strip()

                return {
                    "answer": answer,
                    "confidence": 0.8,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "method": "blip2",
                }

            except Exception as e:
                logger.error(f"Error answering question with BLIP-2: {e}")

        # Fallback
        return {
            "answer": "I cannot answer that question without vision models",
            "confidence": 0.0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "method": "fallback",
        }

    def detect_errors(self, image: Any) -> Dict[str, Any]:
        """
        Detect visual error indicators on screen using AI models.
        
        TICKET-CLEAN-GLOBAL: Removed hardcoded error_keywords list.
        Now uses CLIP model for semantic error detection based on natural language queries.

        Args:
            image: PIL Image to analyze

        Returns:
            Dictionary with:
            - has_error: Boolean indicating error presence
            - error_type: Type of error detected
            - confidence: Detection confidence
            - indicators: List of detected error indicators
        """
        # TICKET-CLEAN-GLOBAL: Use semantic CLIP-based detection instead of keyword matching
        # This allows detection of errors in any language without maintaining keyword lists
        error_concepts = [
            "error message dialog",
            "page not found error",
            "crash or warning dialog",
            "connection failure message",
            "server error page",
            "access denied message",
        ]

        detected_errors = []
        max_score = 0.0

        if self.clip_model and self.clip_processor:
            try:
                import torch

                for concept in error_concepts:
                    result = self.find_element(image, concept, threshold=0.30)
                    if result:
                        detected_errors.append({"type": concept, "score": result["score"]})
                        max_score = max(max_score, result["score"])

            except Exception as e:
                logger.error(f"Error detecting errors with CLIP: {e}")

        has_error = len(detected_errors) > 0

        return {
            "has_error": has_error,
            "error_type": detected_errors[0]["type"] if has_error else None,
            "confidence": max_score,
            "indicators": detected_errors,
            "method": "clip" if self.clip_model else "none",
        }

    def verify_action_result(
        self, image: Any, intent: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify that an action was successfully executed

        Args:
            image: PIL Image after action
            intent: The intent that was executed
            context: Context of the action

        Returns:
            Dictionary with:
            - verified: Boolean indicating success
            - confidence: Verification confidence
            - reason: Explanation of result
        """
        # Check for errors first
        error_result = self.detect_errors(image)

        if error_result["has_error"]:
            return {
                "verified": False,
                "confidence": error_result["confidence"],
                "reason": f"Error detected: {error_result['error_type']}",
                "method": "error_detection",
            }

        # Intent-specific verification
        if intent == "open_url":
            # Check if URL is visible in image
            target_url = context.get("url", "")
            if target_url:
                # Use description to check if page loaded
                desc_result = self.describe(image)
                description = desc_result.get("description", "")

                # Simple heuristic: if description mentions webpage/browser
                is_webpage = any(
                    word in description.lower()
                    for word in ["webpage", "website", "browser", "page"]
                )

                return {
                    "verified": is_webpage,
                    "confidence": desc_result.get("confidence", 0.5),
                    "reason": f"Page description: {description}",
                    "method": "description_analysis",
                }

        # Generic verification - check if screen changed
        return {
            "verified": True,
            "confidence": 0.5,
            "reason": "Cannot verify specific action without specialized check",
            "method": "generic",
        }

    def verify_goal_achievement(
        self, goal: str, screenshot: Any, language: str = "fr"
    ) -> Dict[str, Any]:
        """
        TICKET-SAFE-001: Verify that the user's goal has been achieved.

        This method performs a visual verification to ensure the task is complete
        without errors. It checks for:
        1. Visual error indicators (red text, error dialogs, alerts)
        2. Goal-specific validation using AI models or heuristics

        The verification prevents the agent from declaring "done" when errors
        are visible on screen (e.g., "Mot de passe incorrect").

        Args:
            goal: User's goal in natural language (e.g., "Se connecter à Gmail")
            screenshot: PIL Image of the final screen state
            language: Language for error messages ("fr" or "en")

        Returns:
            Dictionary with:
            - success: Boolean indicating goal achievement (True = OK, False = KO)
            - confidence: Confidence score (0-1)
            - reason: Explanation of the result
            - errors_detected: List of detected error indicators
            - method: Verification method used

        Example:
            >>> result = engine.verify_goal_achievement(
            ...     goal="Se connecter à Gmail",
            ...     screenshot=screenshot_img,
            ...     language="fr"
            ... )
            >>> if not result["success"]:
            ...     print(f"Goal NOT achieved: {result['reason']}")
        """
        start_time = time.time()

        # Step 1: Check for visual error indicators first
        error_result = self.detect_errors(screenshot)

        if error_result["has_error"]:
            # Error detected - goal NOT achieved
            error_type = error_result.get("error_type", "unknown error")
            confidence = error_result.get("confidence", 0.5)

            # TICKET-CLEAN-GLOBAL: Use i18n for error messages
            from janus.i18n.i18n_loader import get_message
            
            reason = get_message(
                "verification.error_detected",
                language=language,
                error_type=error_type
            )

            return {
                "success": False,
                "confidence": confidence,
                "reason": reason,
                "errors_detected": error_result.get("indicators", []),
                "method": "error_detection",
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        # Step 2: Use AI models for goal-specific validation (if available)
        if self.caption_model and self.processor:
            try:
                # TICKET-ARCH-FINAL: Load verification prompt from Jinja2 template
                from janus.ai.reasoning.prompt_loader import get_prompt_loader
                
                prompt_loader = get_prompt_loader()
                verification_prompt = prompt_loader.load_prompt(
                    "verification_system",
                    language=language,
                    goal=goal
                )
                
                if not verification_prompt:
                    raise FileNotFoundError(
                        f"Verification prompt template not found for language: {language}"
                    )

                # Use answer_question for goal verification
                answer_result = self.answer_question(screenshot, verification_prompt)
                answer_text = answer_result.get("answer", "").strip()

                # TICKET-ARCH-FINAL: Parse JSON response instead of text matching
                try:
                    # Try to extract JSON from the response
                    # The LLM might wrap it in markdown code blocks
                    answer_clean = answer_text
                    if "```json" in answer_text:
                        # Extract JSON from markdown code block
                        start = answer_text.find("```json") + 7
                        end = answer_text.find("```", start)
                        answer_clean = answer_text[start:end].strip()
                    elif "```" in answer_text:
                        # Try generic code block
                        start = answer_text.find("```") + 3
                        end = answer_text.find("```", start)
                        answer_clean = answer_text[start:end].strip()
                    
                    # Parse JSON
                    result_data = json.loads(answer_clean)
                    success = result_data.get("success", False)
                    reason = result_data.get("reason", "Unknown reason")
                    
                    # TICKET-ARCH-FINAL: Use i18n for verification messages
                    from janus.i18n.i18n_loader import get_message
                    
                    if success:
                        return {
                            "success": True,
                            "confidence": answer_result.get("confidence", 0.8),
                            "reason": reason,
                            "errors_detected": [],
                            "method": "ai_verification_json",
                            "duration_ms": int((time.time() - start_time) * 1000),
                        }
                    else:
                        return {
                            "success": False,
                            "confidence": answer_result.get("confidence", 0.8),
                            "reason": reason,
                            "errors_detected": [{"type": "ai_detected_issue", "description": reason}],
                            "method": "ai_verification_json",
                            "duration_ms": int((time.time() - start_time) * 1000),
                        }
                
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Failed to parse JSON from AI response: {json_err}")
                    logger.debug(f"Raw answer: {answer_text}")
                    
                    # Fallback: Use original text-based parsing for compatibility
                    # NOTE: This is a fallback for when the LLM doesn't follow instructions
                    from janus.resources.locale_loader import get_locale_loader
                    locale_loader = get_locale_loader()
                    
                    # Get positive/negative keywords from locale for parsing LLM responses
                    positive_keywords = locale_loader.get_keywords("confirmation_positive", language)
                    negative_keywords = locale_loader.get_keywords("confirmation_negative", language)
                    
                    answer_upper = answer_text.upper()
                    is_positive = any(kw.upper() in answer_upper for kw in positive_keywords)
                    is_negative = any(kw.upper() in answer_upper for kw in negative_keywords)
                    
                    from janus.i18n.i18n_loader import get_message
                    
                    if is_positive and not is_negative:
                        return {
                            "success": True,
                            "confidence": answer_result.get("confidence", 0.7),
                            "reason": get_message("verification.goal_achieved", language=language),
                            "errors_detected": [],
                            "method": "ai_verification_fallback",
                            "duration_ms": int((time.time() - start_time) * 1000),
                        }
                    elif is_negative:
                        return {
                            "success": False,
                            "confidence": answer_result.get("confidence", 0.7),
                            "reason": get_message(
                                "verification.goal_not_achieved",
                                language=language,
                                answer=answer_text[:100]
                            ),
                            "errors_detected": [{"type": "ai_detected_issue", "description": answer_text[:100]}],
                            "method": "ai_verification_fallback",
                            "duration_ms": int((time.time() - start_time) * 1000),
                        }
                    else:
                        # Ambiguous answer - default to cautious (not achieved)
                        logger.warning(f"Ambiguous AI verification answer: {answer_text}")
                        return {
                            "success": False,
                            "confidence": 0.3,
                            "reason": get_message(
                                "verification.ambiguous_result",
                                language=language,
                                answer=answer_text[:100]
                            ),
                            "errors_detected": [],
                            "method": "ai_verification_ambiguous",
                            "duration_ms": int((time.time() - start_time) * 1000),
                        }

            except Exception as e:
                logger.error(f"Error during AI verification: {e}", exc_info=True)
                # Fall through to heuristic verification

        # Step 3: Fallback to LLM-based error classification from OCR text
        # TICKET-ARCH-FINAL: No hardcoded error_keywords. Use LLM classification.
        try:
            from janus.vision.native_ocr_adapter import NativeOCRAdapter

            ocr_engine = NativeOCRAdapter(backend="auto")
            ocr_result = ocr_engine.extract_text(screenshot)
            extracted_text = ocr_result.get("text", "").lower()

            if extracted_text and len(extracted_text) > 10:
                # Use LLM to classify if text contains error indicators
                # This works for any language without maintaining keyword lists
                try:
                    # Try to use caption_model (BLIP-2) for quick analysis
                    if self.caption_model and self.processor:
                        # TICKET-ARCH-FINAL: Use structured prompt for error detection
                        from janus.ai.reasoning.prompt_loader import get_prompt_loader
                        
                        prompt_loader = get_prompt_loader()
                        error_check_prompt = prompt_loader.load_prompt(
                            "error_detection",
                            language=language,
                            text=extracted_text[:MAX_OCR_TEXT_LENGTH]
                        )
                        
                        # Fallback to simple prompt if template not available
                        if not error_check_prompt:
                            error_check_prompt = (
                                "Does this text indicate an error or failure? Answer with JSON: "
                                '{"has_error": true/false, "reason": "..."}\n'
                                f"Text: {extracted_text[:MAX_OCR_TEXT_LENGTH]}"
                            )
                        
                        # Use answer_question for quick classification
                        classification_result = self.answer_question(screenshot, error_check_prompt)
                        answer_text = classification_result.get("answer", "").strip()
                        
                        # TICKET-ARCH-FINAL: Try to parse JSON response first
                        try:
                            # Extract JSON if wrapped in markdown
                            answer_clean = answer_text
                            if "```json" in answer_text:
                                start = answer_text.find("```json") + 7
                                end = answer_text.find("```", start)
                                answer_clean = answer_text[start:end].strip()
                            elif "```" in answer_text:
                                start = answer_text.find("```") + 3
                                end = answer_text.find("```", start)
                                answer_clean = answer_text[start:end].strip()
                            
                            result_data = json.loads(answer_clean)
                            has_error = result_data.get("has_error", False)
                            
                            if has_error:
                                from janus.i18n.i18n_loader import get_message
                                
                                return {
                                    "success": False,
                                    "confidence": 0.7,
                                    "reason": get_message(
                                        "verification.error_keywords_detected",
                                        language=language,
                                        keywords="LLM detected error content"
                                    ),
                                    "errors_detected": [
                                        {"type": "llm_detected_error", "text": extracted_text[:100]}
                                    ],
                                    "method": "llm_classification_json",
                                    "duration_ms": int((time.time() - start_time) * 1000),
                                }
                        
                        except json.JSONDecodeError:
                            # Fallback: Parse text-based response using locale keywords
                            from janus.resources.locale_loader import get_locale_loader
                            locale_loader = get_locale_loader()
                            
                            positive_keywords = locale_loader.get_keywords("confirmation_positive", language)
                            answer_upper = answer_text.upper()
                            
                            # NOTE: These keywords parse the LLM's structured response, not user content.
                            # The LLM was prompted to answer about errors, so we check for confirmation.
                            if any(kw.upper() in answer_upper for kw in positive_keywords):
                                from janus.i18n.i18n_loader import get_message
                                
                                return {
                                    "success": False,
                                    "confidence": 0.7,
                                    "reason": get_message(
                                        "verification.error_keywords_detected",
                                        language=language,
                                        keywords="LLM detected error content"
                                    ),
                                    "errors_detected": [
                                        {"type": "llm_detected_error", "text": extracted_text[:100]}
                                    ],
                                    "method": "llm_classification_fallback",
                                    "duration_ms": int((time.time() - start_time) * 1000),
                                }
                except Exception as e:
                    logger.debug(f"LLM-based error classification failed: {e}")
                    # Continue to next fallback

        except Exception as e:
            logger.debug(f"OCR-based verification failed: {e}")

        # Step 4: No errors detected - assume goal is achieved
        # This is the optimistic fallback when no verification methods are available
        from janus.i18n.i18n_loader import get_message
        
        return {
            "success": True,
            "confidence": 0.6,  # Lower confidence for fallback
            "reason": get_message("verification.no_errors_detected", language=language),
            "errors_detected": [],
            "method": "fallback_optimistic",
            "duration_ms": int((time.time() - start_time) * 1000),
        }

    def _get_image_hash(self, image: Any) -> str:
        """Generate simple hash for image caching"""
        # Use image size and first pixel as simple hash
        # In production, use perceptual hashing
        return f"{image.size}_{hash(image.tobytes()[:100])}"

    def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache a result"""
        if not self.enable_cache:
            return

        # Remove oldest if cache full
        if len(self._cache_order) >= self.cache_size:
            oldest_key = self._cache_order.pop(0)
            self._caption_cache.pop(oldest_key, None)

        # Add new result
        self._caption_cache[key] = result
        self._cache_order.append(key)

    def clear_cache(self):
        """Clear the caption cache"""
        self._caption_cache.clear()
        self._cache_order.clear()
        logger.info("Vision cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._caption_cache),
            "max_size": self.cache_size,
            "enabled": self.enable_cache,
        }

    def is_available(self) -> bool:
        """Check if vision AI models are available"""
        return self.caption_model is not None or self.clip_model is not None

    def get_info(self) -> Dict[str, Any]:
        """Get engine information"""
        return {
            "model_type": self.model_type,
            "device": self.device,
            "blip2_available": self.caption_model is not None,
            "clip_available": self.clip_model is not None,
            "cache_enabled": self.enable_cache,
            "cache_stats": self.get_cache_stats(),
        }
