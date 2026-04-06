"""
Whisper STT - Post-Processing Module
Handles text corrections, normalization, and semantic enhancement

TICKET: Unified LLM Architecture
- Semantic correction now uses main LLM from [llm] section by default
- Local model paths are optional overrides for offline/specific use cases
"""

from pathlib import Path
from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("whisper_post_processor")


class WhisperPostProcessor:
    """Post-processing for transcribed text"""

    def __init__(
        self,
        enable_corrections: bool = True,
        enable_normalization: bool = True,
        enable_semantic_correction: bool = True,  # Default True for production (TICKET: Unified LLM)
        enable_natural_reformatter: bool = False,
        correction_dict_path: Optional[str] = None,
        semantic_correction_model_path: Optional[str] = None,
        natural_reformatter_model_path: Optional[str] = None,
        llm_service=None,  # NEW: Centralized LLM service for semantic correction
        sample_rate: int = 16000,
        voice_cache=None,
        context_buffer=None,
    ):
        """
        Initialize post-processor

        Args:
            enable_corrections: Enable correction dictionary
            enable_normalization: Enable text normalization
            enable_semantic_correction: Enable LLM-based semantic correction (default True)
            enable_natural_reformatter: Enable natural language reformatting
            correction_dict_path: Optional path to custom correction dictionary
            semantic_correction_model_path: Optional path to dedicated local GGUF model for semantic correction
            natural_reformatter_model_path: Optional path to dedicated local LLM model for reformatting
            llm_service: Centralized LLM service (uses main LLM from [llm] section)
            sample_rate: Audio sample rate
            voice_cache: Optional voice adaptation cache
            context_buffer: Optional context buffer
            
        Note on semantic correction:
            - Default is True to align with production config ([features] enable_semantic_correction = true)
            - If llm_service is provided AND no local model path is given: uses main LLM
            - If semantic_correction_model_path is provided: uses dedicated local model
            - Otherwise: uses simple rule-based corrector as fallback
            
        MIGRATION NOTE (TICKET: Unified LLM):
            - Previously defaulted to False, now True for production readiness
            - Controlled by [features] enable_semantic_correction in config.ini
            - Users should explicitly set enable_semantic_correction=False if unwanted
        """
        self.enable_corrections = enable_corrections
        self.enable_normalization = enable_normalization
        self.enable_semantic_correction = enable_semantic_correction
        self.enable_natural_reformatter = enable_natural_reformatter
        self.voice_cache = voice_cache
        self.context_buffer = context_buffer
        self.llm_service = llm_service

        # Initialize correction dictionary
        if self.enable_corrections:
            from .correction_dictionary import CorrectionDictionary

            self.correction_dict = CorrectionDictionary(dictionary_path=correction_dict_path)
        else:
            self.correction_dict = None

        # Initialize text normalizer
        if self.enable_normalization:
            from .text_normalizer import TextNormalizer

            self.normalizer = TextNormalizer()
        else:
            self.normalizer = None

        # Initialize semantic corrector
        if self.enable_semantic_correction:
            # Priority 1: Use dedicated local model if path provided
            if semantic_correction_model_path:
                try:
                    from .semantic_corrector import SemanticCorrector
                    
                    self.semantic_corrector = SemanticCorrector(
                        model_path=semantic_correction_model_path, sample_rate=sample_rate
                    )
                    logger.info(
                        f"Semantic correction using dedicated local model: {semantic_correction_model_path}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load dedicated local model: {e}. Falling back to main LLM."
                    )
                    self.semantic_corrector = self._create_llm_corrector()
            # Priority 2: Use centralized LLM service
            elif self.llm_service:
                self.semantic_corrector = self._create_llm_corrector()
                logger.info("Semantic correction using main LLM from [llm] config")
            # Priority 3: Fallback to simple rule-based corrector
            else:
                try:
                    from .semantic_corrector import SimpleSemanticCorrector
                    
                    self.semantic_corrector = SimpleSemanticCorrector()
                    logger.info("Semantic correction using rule-based fallback")
                except ImportError:
                    logger.info("Semantic correction requested but no method available.")
                    self.semantic_corrector = None
        else:
            self.semantic_corrector = None

        # Initialize natural reformatter
        if self.enable_natural_reformatter:
            # Priority 1: Use dedicated local model if path provided
            if natural_reformatter_model_path:
                try:
                    from .natural_reformatter import NaturalReformatter
                    
                    self.natural_reformatter = NaturalReformatter(
                        model_path=natural_reformatter_model_path,
                    )
                    logger.info(
                        f"Natural reformatter using dedicated local model: {natural_reformatter_model_path}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load dedicated reformatter model: {e}. Falling back to main LLM."
                    )
                    self.natural_reformatter = self._create_llm_reformatter()
            # Priority 2: Use centralized LLM service
            elif self.llm_service:
                self.natural_reformatter = self._create_llm_reformatter()
                logger.info("Natural reformatter using main LLM from [llm] config")
            # Priority 3: Fallback to rule-based reformatter
            else:
                try:
                    from .natural_reformatter import RuleBasedReformatter
                    
                    self.natural_reformatter = RuleBasedReformatter()
                    logger.info("Natural reformatter using rule-based fallback")
                except ImportError:
                    logger.info("Natural reformatter requested but no method available.")
                    self.natural_reformatter = None
        else:
            self.natural_reformatter = None
    
    def _create_llm_corrector(self):
        """Create an LLM-based corrector using the centralized LLM service"""
        from janus.ai.llm.llm_text_corrector import LLMTextCorrector
        
        corrector = LLMTextCorrector(self.llm_service)
        
        # Wrap it to match SemanticCorrector interface
        class LLMCorrectorAdapter:
            def __init__(self, llm_corrector):
                self.llm_corrector = llm_corrector
            
            def correct_transcript(self, text, language="en", previous_context=None):
                return self.llm_corrector.correct_transcript(text, language, previous_context)
            
            def get_statistics(self):
                return self.llm_corrector.get_statistics()
        
        return LLMCorrectorAdapter(corrector)
    
    def _create_llm_reformatter(self):
        """Create an LLM-based reformatter using the centralized LLM service"""
        from janus.ai.llm.llm_text_corrector import LLMTextCorrector
        
        reformatter = LLMTextCorrector(self.llm_service)
        
        # Wrap it to match NaturalReformatter interface
        class LLMReformatterAdapter:
            def __init__(self, llm_reformatter):
                self.llm_reformatter = llm_reformatter
            
            def reformat(self, text, language="fr", previous_context=None):
                result = self.llm_reformatter.reformat_text(text, language, previous_context)
                # Convert to ReformattedResult-like object
                class ReformattedResult:
                    def __init__(self, data):
                        self.original = data.get("original", text)
                        self.reformatted = data.get("reformatted", text)
                        self.method = data.get("method", "llm")
                        self.confidence = data.get("confidence", 0.9)
                        self.duration_ms = 0.0
                        self.tokens_used = 0
                
                return ReformattedResult(result)
            
            def get_statistics(self):
                return self.llm_reformatter.get_statistics()
        
        return LLMReformatterAdapter(reformatter)

    def process(
        self,
        raw_text: str,
        language: str,
        audio_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process transcribed text with corrections, normalization, and enhancements

        Args:
            raw_text: Raw transcribed text
            language: Language code
            audio_path: Optional path to audio file (for voice cache)

        Returns:
            Dictionary with processed text at various stages
        """
        # Check voice cache first
        cached_correction = None
        if self.voice_cache and audio_path:
            try:
                audio_bytes = Path(audio_path).read_bytes()
                cached_correction = self.voice_cache.get_correction(audio_bytes, raw_text)
                if cached_correction:
                    logger.info(f"✓ Voice cache hit: '{cached_correction}'")
                    raw_text = cached_correction
            except Exception as e:
                logger.debug(f"Voice cache lookup failed: {e}")

        # Apply corrections
        corrected_text = raw_text
        if self.enable_corrections and self.correction_dict:
            corrected_text = self.correction_dict.correct_text(raw_text)
            if corrected_text != raw_text:
                logger.info(f"After corrections: '{corrected_text}'")

        # Apply normalization
        normalized_text = corrected_text
        if self.enable_normalization and self.normalizer:
            normalized_text = self.normalizer.normalize(corrected_text)
            if normalized_text != corrected_text:
                logger.info(f"After normalization: '{normalized_text}'")

        # Apply natural reformatter
        reformatted_text = normalized_text
        if self.enable_natural_reformatter and self.natural_reformatter:
            reformat_result = self.natural_reformatter.reformat(
                normalized_text,
                language=language,
            )
            reformatted_text = reformat_result.reformatted
            if reformatted_text != normalized_text:
                logger.info(f"After natural reformatter: '{reformatted_text}'")

        # Apply semantic correction (if not using reformatter)
        semantic_corrected_text = reformatted_text
        if (
            self.enable_semantic_correction
            and self.semantic_corrector
            and not self.enable_natural_reformatter
        ):
            # Get previous context from context buffer if available
            previous_context = None
            if self.context_buffer and len(self.context_buffer.audio_buffer) > 1:
                previous_context = None  # Could be enhanced to store previous text

            correction_result = self.semantic_corrector.correct_transcript(
                reformatted_text, language=language, previous_context=previous_context
            )
            semantic_corrected_text = correction_result["corrected"]
            if semantic_corrected_text != reformatted_text:
                logger.info(f"After semantic correction: '{semantic_corrected_text}'")

        # Check for duplicates
        is_duplicate = False
        if self.context_buffer and semantic_corrected_text:
            is_duplicate = self.context_buffer.is_duplicate_text(semantic_corrected_text)
            if is_duplicate:
                logger.info("Duplicate text detected (overlap), skipping...")

        # Update voice cache if corrections were made
        if self.voice_cache and semantic_corrected_text != raw_text and audio_path:
            try:
                audio_bytes = Path(audio_path).read_bytes()
                self.voice_cache.add_correction(
                    audio_bytes,
                    raw_text,
                    semantic_corrected_text,
                    language=language,
                    confidence=0.9,
                )
                logger.info(f"✓ Added to voice cache: '{raw_text}' → '{semantic_corrected_text}'")
            except Exception as e:
                logger.info(f"Failed to update voice cache: {e}")

        return {
            "raw": raw_text,
            "corrected": corrected_text,
            "normalized": normalized_text,
            "reformatted": reformatted_text,
            "semantic_corrected": semantic_corrected_text,
            "final": semantic_corrected_text,
            "is_duplicate": is_duplicate,
        }

    def add_custom_correction(self, error: str, correction: str):
        """
        Add a custom correction to the dictionary

        Args:
            error: The erroneous text
            correction: The correct text
        """
        if self.correction_dict:
            self.correction_dict.add_correction(error, correction)
