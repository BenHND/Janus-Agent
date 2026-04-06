"""
Natural Reformatter for voice commands (Phase 16.2)

This module provides natural language reformulation of voice commands using:
- Mini-LLM (Llama 3.2 1B) for semantic understanding
- Rule-based fallback for reliability
- Async non-blocking operation
- < 400ms target latency
"""

import asyncio
import re
import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from janus.logging import get_logger

# Try to import llama-cpp-python for LLM-based reformatting
try:
    from llama_cpp import Llama

    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    warnings.warn(
        "llama-cpp-python not installed - NaturalReformatter will use rule-based fallback only"
    )


@dataclass
class ReformattedResult:
    """Result of text reformatting"""

    original: str
    reformatted: str
    method: str  # 'llm' or 'rule-based'
    confidence: float
    duration_ms: float
    tokens_used: int = 0


class NaturalReformatter:
    """
    LLM-based natural reformatter using Llama 3.2 1B

    Reformulates voice commands to be cleaner and more natural:
    - Removes filler words intelligently
    - Fixes grammatical issues
    - Maintains original intent
    - Keeps technical terms intact
    """

    REFORMATTING_PROMPT_FR = """Tu es un assistant qui reformule des commandes vocales.
Réécris proprement cette commande vocale sans changer le sens.
Retire les hésitations (euh, um, ben, etc.) et améliore la grammaire si nécessaire.
Garde tous les noms techniques et commandes exactement comme ils sont.

Commande: {text}
Commande reformulée:"""

    REFORMATTING_PROMPT_EN = """You are an assistant that reformulates voice commands.
Rewrite this voice command clearly without changing its meaning.
Remove hesitations (uh, um, like, etc.) and improve grammar if needed.
Keep all technical terms and commands exactly as they are.

Command: {text}
Reformulated command:"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = "llama",
        max_tokens: int = 100,
        temperature: float = 0.3,
        n_ctx: int = 512,
        n_threads: int = 4,
    ):
        """
        Initialize Natural Reformatter with LLM

        Args:
            model_path: Path to GGUF model file
            model_type: Model type (llama, phi, etc.)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            n_ctx: Context window size
            n_threads: Number of CPU threads
        """
        self.logger = get_logger("natural_reformatter")
        self.model_path = model_path
        self.model_type = model_type
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.n_ctx = n_ctx
        self.n_threads = n_threads

        self.model = None
        self._initialize_model()

        # Statistics
        self.stats = {
            "total_reformats": 0,
            "llm_reformats": 0,
            "rule_based_reformats": 0,
            "avg_latency_ms": 0.0,
            "total_tokens": 0,
            "errors": 0,
        }

    def _initialize_model(self):
        """Initialize the LLM model"""
        if not HAS_LLAMA_CPP:
            self.logger.warning("llama-cpp-python not available, using rule-based fallback")
            return

        if not self.model_path:
            self.logger.warning("No model path provided, using rule-based fallback")
            return

        try:
            self.logger.info(f"Loading LLM model from {self.model_path}...")
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            self.logger.info("LLM model loaded successfully")
        except Exception as e:
            self.logger.warning(f"Failed to load LLM model: {e}")
            self.logger.info("Using rule-based fallback")
            self.model = None

    def reformat(
        self,
        text: str,
        language: str = "fr",
        previous_context: Optional[str] = None,
    ) -> ReformattedResult:
        """
        Reformat text using LLM or rule-based approach

        Args:
            text: Text to reformat
            language: Language code (fr, en)
            previous_context: Optional previous context for better understanding

        Returns:
            ReformattedResult with reformatted text and metadata
        """
        start_time = time.time()

        # Try LLM first if available
        if self.model is not None:
            try:
                result = self._reformat_llm(text, language, previous_context)
                result.duration_ms = (time.time() - start_time) * 1000

                # Update statistics
                self.stats["total_reformats"] += 1
                self.stats["llm_reformats"] += 1
                self.stats["total_tokens"] += result.tokens_used
                self.stats["avg_latency_ms"] = (
                    self.stats["avg_latency_ms"] * (self.stats["total_reformats"] - 1)
                    + result.duration_ms
                ) / self.stats["total_reformats"]

                return result
            except Exception as e:
                self.logger.warning(f"LLM reformatting failed: {e}, falling back to rules")
                self.stats["errors"] += 1

        # Fallback to rule-based
        result = self._reformat_rule_based(text, language)
        result.duration_ms = (time.time() - start_time) * 1000

        # Update statistics
        self.stats["total_reformats"] += 1
        self.stats["rule_based_reformats"] += 1
        self.stats["avg_latency_ms"] = (
            self.stats["avg_latency_ms"] * (self.stats["total_reformats"] - 1) + result.duration_ms
        ) / self.stats["total_reformats"]

        return result

    async def reformat_async(
        self,
        text: str,
        language: str = "fr",
        previous_context: Optional[str] = None,
    ) -> ReformattedResult:
        """
        Async version of reformat (non-blocking)

        Args:
            text: Text to reformat
            language: Language code
            previous_context: Optional context

        Returns:
            ReformattedResult
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.reformat, text, language, previous_context)
        return result

    def _reformat_llm(
        self,
        text: str,
        language: str,
        previous_context: Optional[str],
    ) -> ReformattedResult:
        """Reformat using LLM"""
        # Select appropriate prompt
        if language.lower().startswith("fr"):
            prompt = self.REFORMATTING_PROMPT_FR.format(text=text)
        else:
            prompt = self.REFORMATTING_PROMPT_EN.format(text=text)

        # Add context if provided
        if previous_context:
            context_line = (
                f"\nContexte précédent: {previous_context}\n"
                if language.startswith("fr")
                else f"\nPrevious context: {previous_context}\n"
            )
            prompt = prompt.replace("Commande:", context_line + "Commande:")
            prompt = prompt.replace("Command:", context_line + "Command:")

        # Generate reformatted text
        output = self.model(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stop=["\n", "Commande:", "Command:", "Original:"],
            echo=False,
        )

        reformatted = output["choices"][0]["text"].strip()
        tokens_used = output["usage"]["completion_tokens"]

        # Post-process: remove any remaining prompt artifacts
        reformatted = self._clean_llm_output(reformatted, text)

        return ReformattedResult(
            original=text,
            reformatted=reformatted,
            method="llm",
            confidence=0.9,
            duration_ms=0.0,  # Will be set by caller
            tokens_used=tokens_used,
        )

    def _clean_llm_output(self, output: str, original: str) -> str:
        """Clean LLM output of artifacts"""
        # Remove quotes if present
        output = output.strip("\"'")

        # If output is empty or too short, return original
        if len(output) < 3:
            return original

        # Remove common prefixes
        prefixes = [
            "Commande reformulée:",
            "Reformulated command:",
            "Reformulated:",
            "→",
            "=>",
        ]
        for prefix in prefixes:
            if output.startswith(prefix):
                output = output[len(prefix) :].strip()

        return output if output else original

    def _reformat_rule_based(self, text: str, language: str) -> ReformattedResult:
        """Reformat using rule-based approach (fallback)"""
        reformatted = text

        # Remove filler words
        if language.lower().startswith("fr"):
            fillers = ["euh", "euh euh", "um", "uh", "ben", "bah", "alors", "donc euh", "eh bien"]
        else:
            fillers = ["uh", "um", "like", "you know", "I mean", "well", "so um", "er", "ah"]

        for filler in fillers:
            # Remove filler at beginning
            reformatted = re.sub(
                r"^\s*" + re.escape(filler) + r"\s+", "", reformatted, flags=re.IGNORECASE
            )
            # Remove filler in middle (with surrounding spaces)
            reformatted = re.sub(
                r"\s+" + re.escape(filler) + r"\s+", " ", reformatted, flags=re.IGNORECASE
            )
            # Remove filler at end
            reformatted = re.sub(
                r"\s+" + re.escape(filler) + r"\s*$", "", reformatted, flags=re.IGNORECASE
            )

        # Normalize whitespace
        reformatted = re.sub(r"\s+", " ", reformatted).strip()

        # Capitalize first letter
        if reformatted:
            reformatted = reformatted[0].upper() + reformatted[1:]

        # Remove trailing periods if it's a command
        if language.lower().startswith("fr"):
            command_verbs = ["ouvre", "lance", "ferme", "crée", "copie", "colle", "cherche", "va"]
        else:
            command_verbs = ["open", "launch", "close", "create", "copy", "paste", "search", "go"]

        first_word = reformatted.split()[0].lower() if reformatted.split() else ""
        if first_word in command_verbs:
            reformatted = reformatted.rstrip(".")

        return ReformattedResult(
            original=text,
            reformatted=reformatted if reformatted else text,
            method="rule-based",
            confidence=0.7,
            duration_ms=0.0,  # Will be set by caller
            tokens_used=0,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get reformatter statistics"""
        return {
            **self.stats,
            "model_path": self.model_path,
            "model_loaded": self.model is not None,
            "llm_available": HAS_LLAMA_CPP,
        }


class RuleBasedReformatter:
    """
    Simple rule-based reformatter (no LLM dependencies)

    Fast and reliable fallback that:
    - Removes common filler words
    - Normalizes whitespace
    - Fixes basic grammar issues
    - Preserves technical terms
    """

    def __init__(self):
        """Initialize rule-based reformatter"""
        self.stats = {
            "total_reformats": 0,
            "avg_latency_ms": 0.0,
        }

    def reformat(self, text: str, language: str = "fr") -> ReformattedResult:
        """
        Reformat text using rules

        Args:
            text: Text to reformat
            language: Language code (fr, en)

        Returns:
            ReformattedResult
        """
        start_time = time.time()

        reformatted = self._apply_rules(text, language)

        duration_ms = (time.time() - start_time) * 1000

        # Update statistics
        self.stats["total_reformats"] += 1
        self.stats["avg_latency_ms"] = (
            self.stats["avg_latency_ms"] * (self.stats["total_reformats"] - 1) + duration_ms
        ) / self.stats["total_reformats"]

        return ReformattedResult(
            original=text,
            reformatted=reformatted,
            method="rule-based",
            confidence=0.7,
            duration_ms=duration_ms,
            tokens_used=0,
        )

    async def reformat_async(self, text: str, language: str = "fr") -> ReformattedResult:
        """Async version (actually synchronous for rule-based)"""
        return self.reformat(text, language)

    def _apply_rules(self, text: str, language: str) -> str:
        """Apply reformatting rules"""
        reformatted = text

        # 1. Remove filler words
        if language.lower().startswith("fr"):
            fillers = [
                "euh euh",
                "euh",
                "um",
                "uh",
                "ben",
                "bah",
                "hein",
                "alors euh",
                "donc euh",
                "eh bien",
                "tu vois",
                "tu sais",
                "en fait",
                "genre",
                "quoi",
            ]
        else:
            fillers = [
                "um um",
                "uh uh",
                "um",
                "uh",
                "like",
                "you know",
                "I mean",
                "well",
                "so um",
                "so like",
                "er",
                "ah",
                "kind of",
                "sort of",
                "basically",
            ]

        # Sort by length (longest first) to avoid partial matches
        fillers.sort(key=len, reverse=True)

        for filler in fillers:
            # Remove at beginning
            pattern = r"^\s*" + re.escape(filler) + r"\s+"
            reformatted = re.sub(pattern, "", reformatted, flags=re.IGNORECASE)

            # Remove in middle
            pattern = r"\s+" + re.escape(filler) + r"\s+"
            reformatted = re.sub(pattern, " ", reformatted, flags=re.IGNORECASE)

            # Remove at end
            pattern = r"\s+" + re.escape(filler) + r"\s*$"
            reformatted = re.sub(pattern, "", reformatted, flags=re.IGNORECASE)

        # 2. Expand common contractions
        if language.lower().startswith("fr"):
            contractions = {
                r"\bj\s+": "je ",
                r"\bd\s+": "de ",
                r"\bl\s+": "le ",
                r"\bqu\s+": "que ",
                r"\bm\s+": "me ",
                r"\bt\s+": "te ",
                r"\bs\s+": "se ",
            }
        else:
            contractions = {
                r"\bI\'m\b": "I am",
                r"\byou\'re\b": "you are",
                r"\bhe\'s\b": "he is",
                r"\bshe\'s\b": "she is",
                r"\bit\'s\b": "it is",
                r"\bwe\'re\b": "we are",
                r"\bthey\'re\b": "they are",
                r"\bcan\'t\b": "cannot",
                r"\bwon\'t\b": "will not",
                r"\bdon\'t\b": "do not",
            }

        for pattern, replacement in contractions.items():
            reformatted = re.sub(pattern, replacement, reformatted, flags=re.IGNORECASE)

        # 3. Normalize whitespace
        reformatted = re.sub(r"\s+", " ", reformatted).strip()

        # 4. Fix capitalization
        if reformatted:
            reformatted = reformatted[0].upper() + reformatted[1:]

        # 5. Remove repeated words (e.g., "le le" → "le")
        reformatted = re.sub(r"\b(\w+)\s+\1\b", r"\1", reformatted, flags=re.IGNORECASE)

        # 6. Clean up punctuation
        reformatted = re.sub(r"\s+([,;:.!?])", r"\1", reformatted)
        reformatted = re.sub(r"([,;:.!?])+", r"\1", reformatted)  # Remove duplicate punctuation

        # 7. Remove trailing periods for commands
        if language.lower().startswith("fr"):
            command_verbs = [
                "ouvre",
                "ouvrir",
                "lance",
                "lancer",
                "ferme",
                "fermer",
                "crée",
                "créer",
                "copie",
                "copier",
                "colle",
                "coller",
                "cherche",
                "chercher",
                "va",
                "aller",
                "affiche",
                "afficher",
            ]
        else:
            command_verbs = [
                "open",
                "launch",
                "close",
                "create",
                "copy",
                "paste",
                "search",
                "go",
                "show",
                "display",
                "find",
                "run",
            ]

        first_word = reformatted.split()[0].lower() if reformatted.split() else ""
        if first_word in command_verbs:
            reformatted = reformatted.rstrip(".")

        return reformatted if reformatted else text

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        return self.stats


def create_natural_reformatter(
    model_path: Optional[str] = None, use_llm: bool = True, **kwargs
) -> Union[NaturalReformatter, RuleBasedReformatter]:
    """
    Factory function to create a reformatter instance

    Args:
        model_path: Path to LLM model (GGUF format)
        use_llm: Try to use LLM if available
        **kwargs: Additional arguments for NaturalReformatter

    Returns:
        NaturalReformatter (with LLM) or RuleBasedReformatter (fallback)
    """
    if use_llm and (HAS_LLAMA_CPP and model_path):
        return NaturalReformatter(model_path=model_path, **kwargs)
    else:
        if use_llm and not HAS_LLAMA_CPP:
            from janus.logging import get_logger

            logger = get_logger("natural_reformatter")
            logger.warning("llama-cpp-python not available, using rule-based reformatter")
        return RuleBasedReformatter()
