"""
Semantic Correction using Lightweight LLM
Phase 15.5 - Post-correction of transcripts using local mini-LLM for grammar and filler cleanup
"""

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("semantic_corrector")

try:
    from llama_cpp import Llama

    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    warnings.warn("llama-cpp-python not installed - SemanticCorrector will not be available")


class SemanticCorrector:
    """
    Lightweight LLM-based semantic correction for transcripts

    Features:
    - Grammar correction
    - Filler word cleanup
    - Phonetic error correction
    - Context-aware improvements
    - Async non-blocking operation
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = "phi",  # phi, llama, mistral
        n_ctx: int = 512,
        n_threads: int = 4,
        temperature: float = 0.3,
        max_tokens: int = 100,
    ):
        """
        Initialize Semantic Corrector

        Args:
            model_path: Path to GGUF model file (e.g., phi-2.Q4_K_M.gguf)
            model_type: Type of model (phi, llama, mistral)
            n_ctx: Context window size
            n_threads: Number of CPU threads to use
            temperature: Sampling temperature (lower = more conservative)
            max_tokens: Maximum tokens to generate
        """
        if not HAS_LLAMA_CPP:
            raise RuntimeError(
                "llama-cpp-python is required for SemanticCorrector. "
                "Install with: pip install llama-cpp-python"
            )

        self.model_path = model_path
        self.model_type = model_type
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Model instance
        self.model = None

        # Thread pool for async processing
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Statistics
        self.total_corrections = 0
        self.total_tokens_processed = 0

        # Load model if path provided
        if model_path:
            self._load_model()

    def _load_model(self):
        """Load GGUF model"""
        if not self.model_path:
            raise ValueError("model_path must be provided to load model")

        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            logger.info(f"Loaded LLM model: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load LLM model: {e}")

    def _build_correction_prompt(
        self, raw_transcript: str, language: str = "en", previous_context: Optional[str] = None
    ) -> str:
        """
        Build prompt for correction

        Args:
            raw_transcript: Raw transcript to correct
            language: Language code (fr or en)
            previous_context: Optional previous context

        Returns:
            Formatted prompt
        """
        if language == "fr":
            system_msg = """Tu es un assistant de correction de transcriptions audio.
Corrige la grammaire, supprime les mots de remplissage (euh, um, etc.),
et améliore la clarté sans changer le sens. Réponds UNIQUEMENT avec le texte corrigé."""

            if previous_context:
                prompt = f"""{system_msg}

Contexte précédent: {previous_context}

Transcription brute: {raw_transcript}

Transcription corrigée:"""
            else:
                prompt = f"""{system_msg}

Transcription brute: {raw_transcript}

Transcription corrigée:"""
        else:  # English
            system_msg = """You are an audio transcription correction assistant.
Fix grammar, remove filler words (uh, um, like, etc.),
and improve clarity without changing the meaning. Respond ONLY with the corrected text."""

            if previous_context:
                prompt = f"""{system_msg}

Previous context: {previous_context}

Raw transcript: {raw_transcript}

Corrected transcript:"""
            else:
                prompt = f"""{system_msg}

Raw transcript: {raw_transcript}

Corrected transcript:"""

        return prompt

    def correct_transcript(
        self, raw_transcript: str, language: str = "en", previous_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct transcript using LLM (synchronous)

        Args:
            raw_transcript: Raw transcript text
            language: Language code (fr or en)
            previous_context: Optional previous context for coherence

        Returns:
            Dictionary with correction results
        """
        if not self.model:
            # Fallback: return raw transcript
            return {
                "corrected": raw_transcript,
                "raw": raw_transcript,
                "model_used": False,
                "tokens_used": 0,
            }

        # Build prompt
        prompt = self._build_correction_prompt(raw_transcript, language, previous_context)

        try:
            # Generate correction
            output = self.model(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["\n\n", "Raw transcript:", "Transcription brute:"],
                echo=False,
            )

            # Extract corrected text
            corrected_text = output["choices"][0]["text"].strip()
            tokens_used = output["usage"]["total_tokens"]

            # Update statistics
            self.total_corrections += 1
            self.total_tokens_processed += tokens_used

            return {
                "corrected": corrected_text,
                "raw": raw_transcript,
                "model_used": True,
                "tokens_used": tokens_used,
            }

        except Exception as e:
            warnings.warn(f"Correction failed: {e}")
            return {
                "corrected": raw_transcript,
                "raw": raw_transcript,
                "model_used": False,
                "tokens_used": 0,
                "error": str(e),
            }

    async def correct_transcript_async(
        self, raw_transcript: str, language: str = "en", previous_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct transcript using LLM (asynchronous, non-blocking)

        Args:
            raw_transcript: Raw transcript text
            language: Language code (fr or en)
            previous_context: Optional previous context for coherence

        Returns:
            Dictionary with correction results
        """
        # Run correction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor, self.correct_transcript, raw_transcript, language, previous_context
        )
        return result

    def batch_correct(self, transcripts: list, language: str = "en") -> list:
        """
        Correct multiple transcripts in batch

        Args:
            transcripts: List of transcript strings
            language: Language code

        Returns:
            List of correction results
        """
        results = []
        for transcript in transcripts:
            result = self.correct_transcript(transcript, language)
            results.append(result)
        return results

    def set_model_path(self, model_path: str):
        """
        Set model path and load model

        Args:
            model_path: Path to GGUF model file
        """
        self.model_path = model_path
        self._load_model()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get correction statistics

        Returns:
            Dictionary with statistics
        """
        avg_tokens = 0
        if self.total_corrections > 0:
            avg_tokens = self.total_tokens_processed / self.total_corrections

        return {
            "total_corrections": self.total_corrections,
            "total_tokens_processed": self.total_tokens_processed,
            "avg_tokens_per_correction": avg_tokens,
            "model_loaded": self.model is not None,
            "model_path": self.model_path,
        }

    def __del__(self):
        """Cleanup executor"""
        try:
            self.executor.shutdown(wait=False)
        except Exception as e:
            logger.debug(f"Failed to shutdown executor: {e}")
            pass


class SimpleSemanticCorrector:
    """
    Simplified semantic corrector using rule-based approach (no LLM required)

    This is a fallback when LLM is not available or desired.
    Provides basic cleanup without heavy dependencies.
    """

    # Common filler words to remove
    FILLER_WORDS_EN = {"uh", "um", "like", "you know", "actually", "basically", "literally"}
    FILLER_WORDS_FR = {"euh", "heu", "bah", "ben", "voilà", "quoi", "genre"}

    def __init__(self):
        """Initialize simple corrector"""
        self.total_corrections = 0

    def correct_transcript(
        self, raw_transcript: str, language: str = "en", previous_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct transcript using rules

        Args:
            raw_transcript: Raw transcript text
            language: Language code (fr or en)
            previous_context: Ignored in simple corrector

        Returns:
            Dictionary with correction results
        """
        # Select filler words based on language
        fillers = self.FILLER_WORDS_FR if language == "fr" else self.FILLER_WORDS_EN

        # Split into words
        words = raw_transcript.split()

        # Remove filler words
        cleaned_words = [w for w in words if w.lower() not in fillers]

        # Rejoin
        corrected = " ".join(cleaned_words)

        # Basic capitalization
        if corrected:
            corrected = (
                corrected[0].upper() + corrected[1:] if len(corrected) > 1 else corrected.upper()
            )

        self.total_corrections += 1

        return {
            "corrected": corrected,
            "raw": raw_transcript,
            "model_used": False,
            "tokens_used": 0,
        }

    async def correct_transcript_async(
        self, raw_transcript: str, language: str = "en", previous_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async version (just calls sync version)"""
        return self.correct_transcript(raw_transcript, language, previous_context)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "total_corrections": self.total_corrections,
            "model_loaded": False,
            "model_path": None,
        }
