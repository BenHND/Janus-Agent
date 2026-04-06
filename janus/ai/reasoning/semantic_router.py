"""
Semantic Router - Ultra-light input filter for Janus (TICKET-401)

This module filters user input BEFORE expensive LLM reasoning calls to:
1. Ignore noise (politeness, affirmations, incomplete input)
2. Handle chat/conversation separately 
3. Route only actionable commands to the Reasoner

Performance target: <50ms classification vs 2-10s for full reasoning

TICKET-ROUTER-001: Zero-shot classification using embeddings
- Uses sentence-transformers embeddings for semantic classification
- Calculates distance to 3 pre-computed centroids (NOISE, CHAT, ACTION)
- Handles linguistic variations (e.g., franglais "check mes mails")
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .reasoner_llm import ReasonerLLM

logger = logging.getLogger(__name__)

# TICKET-500: Default classification for fail-open behavior
# When JSON parsing fails, we default to ACTION to avoid blocking users
DEFAULT_CLASSIFICATION_ON_ERROR = "ACTION"

# TICKET-ROUTER-001: Path to representative examples configuration
# File lives in janus/ai/resources/i18n/semantic_router_examples.json
EXAMPLES_CONFIG_PATH = Path(__file__).parent / "resources" / "i18n" / "semantic_router_examples.json"

# TICKET-ROUTER-001: Lazy imports for embedding-based classification
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    np = None  # type: ignore
    logger.warning("sentence-transformers/numpy not available, semantic router will use keyword-based fallback. "
                  "Install with: pip install sentence-transformers numpy")


class SemanticRouter:
    """
    Ultra-light semantic input classifier.
    
    Filters input into 3 categories BEFORE expensive reasoning:
    - NOISE: Politeness (merci, salut), affirmations (ok, d'accord), incomplete
    - CHAT: General conversation, questions, jokes
    - ACTION: Commands requiring system actions
    
    Configuration:
    - max_tokens=10 (just need 1 word)
    - temperature=0.0 (deterministic)
    - Ultra-short prompt for speed
    """
    
    # System prompt for ultra-fast classification (JSON MODE - TICKET-500)
    # CRITICAL: Requires strict JSON output format
    CLASSIFICATION_PROMPT = """CLASSIFY INPUT into one of three categories.
OUTPUT MUST BE VALID JSON with this exact structure: {{"intent": "NOISE|CHAT|ACTION"}}

Categories:
- "NOISE": Politesse (merci, salut), affirmation (ok, d'accord), incomplet, bruit.
- "CHAT": Question culture générale, blague, conversation, question non-actionnable.
- "ACTION": Demande d'action système (ouvrir, chercher, envoyer, mettre, créer, supprimer).

INPUT: "{text}"
JSON OUTPUT:"""
    
    def __init__(
        self,
        reasoner: Optional[ReasonerLLM] = None,
        enable_embeddings: bool = True,
        learning_manager: Optional[Any] = None,
    ):
        """
        Initialize Semantic Router.
        
        Args:
            reasoner: Optional ReasonerLLM instance. If None or in mock mode, uses keyword-based fallback.
            enable_embeddings: Enable embedding-based classification (TICKET-ROUTER-001)
            learning_manager: Optional LearningManager for skill caching (LEARNING-001)
        """
        self.reasoner = reasoner
        self.learning_manager = learning_manager  # LEARNING-001
        
        # Check if reasoner is actually usable (not mock)
        self.use_llm = (
            reasoner is not None 
            and reasoner.available 
            and reasoner.backend.value != "mock"
        )
        
        # Fallback keyword rules when LLM unavailable
        self.noise_keywords = [
            "merci", "salut", "bonjour", "au revoir", "ok", "d'accord", 
            "oui", "non", "euh", "hum", "ah", "oh", "bonsoir", "coucou",
            "thanks", "hello", "hi", "bye", "okay", "yeah", "yep", "nope"
        ]
        
        self.action_keywords = [
            "ouvre", "ouvrir", "ferme", "fermer", "lance", "lancer",
            "cherche", "chercher", "trouve", "trouver", "envoie", "envoyer",
            "créé", "créer", "supprime", "supprimer", "copie", "copier",
            "colle", "coller", "sauvegarde", "sauvegarder", "déplace", "déplacer",
            "open", "close", "launch", "search", "find", "send", "create",
            "delete", "copy", "paste", "save", "move", "click", "type"
        ]
        
        # TICKET-ROUTER-001: Initialize embedding-based classification
        self._embedding_model = None
        self._centroids = None
        self._use_embeddings = False
        
        if enable_embeddings and EMBEDDINGS_AVAILABLE:
            try:
                self._init_embedding_classifier()
                self._use_embeddings = True
                logger.info("SemanticRouter: Embedding-based classification enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding classifier: {e}")
        
        logger.info(
            f"SemanticRouter initialized (llm={'available' if self.use_llm else 'fallback'}, "
            f"embeddings={'enabled' if self._use_embeddings else 'disabled'}, "
            f"skill_cache={'enabled' if learning_manager else 'disabled'})"
        )
    
    def _load_representative_examples(self) -> Dict[str, List[str]]:
        """
        Load representative examples from configuration file.
        
        Reads examples from semantic_router_examples.json to avoid hardcoded
        language-specific strings in the code.
        
        Returns:
            Dictionary mapping categories to list of example strings
        """
        try:
            if not EXAMPLES_CONFIG_PATH.exists():
                logger.warning(f"Examples config not found at {EXAMPLES_CONFIG_PATH}, using fallback")
                return self._get_fallback_examples()
            
            with open(EXAMPLES_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Combine examples from all languages for each category
            representative_examples = {}
            for category, data in config.get("categories", {}).items():
                examples = []
                # Merge examples from all language variants
                for lang_examples in data.get("examples", {}).values():
                    examples.extend(lang_examples)
                representative_examples[category] = examples
            
            logger.info(f"Loaded {sum(len(v) for v in representative_examples.values())} examples from config")
            return representative_examples
            
        except Exception as e:
            logger.error(f"Failed to load examples config: {e}, using fallback")
            return self._get_fallback_examples()
    
    def _get_fallback_examples(self) -> Dict[str, List[str]]:
        """
        Fallback representative examples if config file cannot be loaded.
        
        Minimal set to ensure system continues working.
        
        Returns:
            Dictionary mapping categories to list of example strings
        """
        return {
            "NOISE": ["Hello", "Thanks", "Ok", "Bye"],
            "CHAT": ["What is the weather", "Tell me a joke"],
            "ACTION": ["Open Chrome", "Close Safari", "Check my emails"],
        }
    
    def _init_embedding_classifier(self):
        """
        Initialize embedding-based classifier with pre-computed centroids (TICKET-ROUTER-001).
        
        Uses sentence-transformers to compute embeddings for representative examples
        of each category (NOISE, CHAT, ACTION).
        
        Note: Model loading is a one-time cost (~1-2s on first run, cached thereafter).
        Centroids are computed once during initialization.
        """
        if not EMBEDDINGS_AVAILABLE:
            return
        
        from janus.ai.embeddings.shared_sentence_transformer import (
            get_sentence_transformer,
            is_sentence_transformer_loaded,
        )

        if is_sentence_transformer_loaded():
            logger.info("Reusing shared embedding model for intent routing")
        else:
            logger.info("Loading embedding model for intent routing...")

        self._embedding_model = get_sentence_transformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Load representative examples from configuration file (TICKET-ROUTER-001)
        # Externalized to avoid hardcoded language-specific strings
        representative_examples = self._load_representative_examples()
        
        # Compute centroids for each category
        self._centroids = {}
        for category, examples in representative_examples.items():
            embeddings = self._embedding_model.encode(examples)
            # Centroid is the mean of all example embeddings
            centroid = np.mean(embeddings, axis=0)
            # Pre-normalize centroid for faster cosine similarity computation
            centroid = centroid / np.linalg.norm(centroid)
            self._centroids[category] = centroid
        
        logger.info(f"Computed centroids for {len(self._centroids)} categories")
    
    def classify_intent(self, text: str) -> str:
        """
        Classify user input into NOISE, CHAT, or ACTION.
        
        Args:
            text: Raw user input
            
        Returns:
            Classification string: "NOISE", "CHAT", or "ACTION"
        """
        if not text or not text.strip():
            return "NOISE"
        
        text = text.strip()
        
        # Try LLM classification if available and not mock
        if self.use_llm:
            try:
                return self._classify_with_llm(text)
            except Exception as e:
                logger.warning(f"LLM classification failed, using fallback: {e}")
        
        # TICKET-ROUTER-001: Try embedding-based classification
        if self._use_embeddings:
            try:
                return self._classify_with_embeddings(text)
            except Exception as e:
                logger.warning(f"Embedding classification failed, using keyword fallback: {e}")
        
        # Fallback to keyword-based classification
        return self._classify_with_keywords(text)
    
    def _classify_with_embeddings(self, text: str) -> str:
        """
        Use embedding-based zero-shot classification (TICKET-ROUTER-001).
        
        Computes the embedding of the input text and finds the nearest centroid
        using cosine similarity. This approach handles linguistic variations
        (e.g., franglais "check mes mails") better than keyword matching.
        
        Args:
            text: User input
            
        Returns:
            Classification: "NOISE", "CHAT", or "ACTION"
        """
        # Compute embedding for input text
        text_embedding = self._embedding_model.encode([text])[0]
        
        # Normalize text embedding for faster cosine similarity computation
        embedding_norm = np.linalg.norm(text_embedding)
        if embedding_norm == 0:
            # Edge case: zero vector (shouldn't happen with real text, but handle safely)
            logger.warning(f"Zero-norm embedding for text: '{text[:50]}', defaulting to ACTION")
            return DEFAULT_CLASSIFICATION_ON_ERROR
        text_embedding_norm = text_embedding / embedding_norm
        
        # Calculate cosine similarity to each centroid
        # Since both vectors are normalized, cosine similarity = dot product
        similarities = {}
        for category, centroid in self._centroids.items():
            # Optimized: dot product of normalized vectors = cosine similarity
            similarity = np.dot(text_embedding_norm, centroid)
            similarities[category] = similarity
        
        # Return category with highest similarity
        best_category = max(similarities, key=similarities.get)
        best_similarity = similarities[best_category]
        
        logger.debug(
            f"Embedding classification: '{text[:30]}...' → {best_category} "
            f"(similarity: {best_similarity:.3f}, all: {similarities})"
        )
        
        return best_category
    
    def _classify_with_llm(self, text: str) -> str:
        """
        Use LLM for semantic classification with JSON mode (TICKET-500).
        
        Uses strict JSON output format to avoid parsing errors with verbose LLMs.
        The LLM API's json_mode ensures valid JSON response structure.
        
        Args:
            text: User input
            
        Returns:
            Classification: "NOISE", "CHAT", or "ACTION"
        """
        prompt = self.CLASSIFICATION_PROMPT.format(text=text)
        
        # TICKET-500: Enable JSON mode to force structured output
        # This prevents "bavard" responses like "La réponse est ACTION"
        # Ultra-light inference: max_tokens=10 (only need JSON object)
        # Use the public ReasonerLLM API.
        response = self.reasoner.run_inference(
            prompt,
            max_tokens=10,
            json_mode=True,  # CRITICAL: Force JSON output from API
        )
        
        # Extract classification from JSON response
        classification = self._extract_classification(response)
        
        logger.debug(f"LLM classified '{text[:30]}...' as {classification} (JSON mode)")
        return classification
    
    def _extract_classification(self, response: str) -> str:
        """
        Extract classification from JSON LLM response (TICKET-500).
        
        Replaces regex/text search with direct JSON parsing for reliability.
        Falls back to ACTION (fail-open) on errors to avoid blocking user.
        
        Args:
            response: Raw LLM output (should be JSON)
            
        Returns:
            Normalized classification: "NOISE", "CHAT", or "ACTION"
        """
        if not response:
            # Empty response - default to ACTION (fail-open)
            logger.warning(f"Empty LLM response, defaulting to {DEFAULT_CLASSIFICATION_ON_ERROR} (fail-open)")
            return DEFAULT_CLASSIFICATION_ON_ERROR
        
        try:
            # TICKET-500: Parse JSON response directly (no regex)
            data = json.loads(response.strip())
            
            # Extract intent from JSON object
            intent = data.get("intent", "").upper()
            
            # Validate intent value
            if intent in ["NOISE", "CHAT", "ACTION"]:
                logger.debug(f"Successfully parsed JSON intent: {intent}")
                return intent
            else:
                # Invalid intent value - log and default to ACTION
                logger.warning(f"Invalid intent value '{intent}' in JSON, defaulting to {DEFAULT_CLASSIFICATION_ON_ERROR}")
                return DEFAULT_CLASSIFICATION_ON_ERROR
                
        except json.JSONDecodeError as e:
            # JSON parsing failed - this should be rare in json_mode
            # Log the raw response for debugging
            logger.error(
                f"JSON parse error in SemanticRouter (fail-open to {DEFAULT_CLASSIFICATION_ON_ERROR}): {e}. "
                f"Raw response: {response[:100]}"
            )
            # TICKET-500: Fail-open to ACTION (don't block user on parse errors)
            return DEFAULT_CLASSIFICATION_ON_ERROR
        except Exception as e:
            # Unexpected error - fail-open to ACTION
            logger.error(f"Unexpected error parsing classification: {e}, defaulting to {DEFAULT_CLASSIFICATION_ON_ERROR}")
            return DEFAULT_CLASSIFICATION_ON_ERROR
    
    def _classify_with_keywords(self, text: str) -> str:
        """
        Keyword-based fallback classification.
        
        Args:
            text: User input
            
        Returns:
            Classification: "NOISE", "CHAT", or "ACTION"
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        # Very short input (1-2 words) is likely noise or chat
        if len(words) <= 2:
            # Check if it's a simple politeness/affirmation
            if any(keyword in text_lower for keyword in self.noise_keywords):
                return "NOISE"
            # Check if it's an action keyword (e.g., "ouvre Safari")
            if any(keyword in text_lower for keyword in self.action_keywords):
                return "ACTION"
            # Short unclear input -> NOISE
            return "NOISE"
        
        # Check for action keywords
        if any(keyword in text_lower for keyword in self.action_keywords):
            return "ACTION"
        
        # Check for noise keywords
        if any(keyword in text_lower for keyword in self.noise_keywords):
            # If sentence is longer but starts with noise, it might still be action
            # e.g., "Merci et maintenant ouvre Safari"
            if any(keyword in text_lower for keyword in self.action_keywords):
                return "ACTION"
            return "NOISE"
        
        # Question patterns (culture générale, blague)
        question_indicators = ["?", "qui", "quoi", "où", "quand", "comment", "pourquoi", 
                               "quel", "quelle", "what", "who", "where", "when", "how", "why"]
        if any(indicator in text_lower for indicator in question_indicators):
            return "CHAT"
        
        # Default: if unclear and no action keywords, treat as CHAT
        # (safer to handle in chat mode than ignore completely)
        return "CHAT"

    # LEARNING-001: Skill Cache Methods
    def check_skill_cache(
        self,
        text: str,
        context_data: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.8,
    ) -> Optional["SkillHint"]:
        """
        Check if a cached skill exists for this intent (Hint Mode)
        
        LEARNING-001: Returns a SkillHint (suggestion) instead of directly executable actions.
        The hint is provided to the LLM Reasoner as context, not executed automatically.

        This method should be called BEFORE the expensive LLM reasoning to check
        if we have a learned action sequence that can serve as a hint.

        Args:
            text: User's intent/command
            context_data: Optional visual/contextual state
            similarity_threshold: Minimum similarity for vector matching

        Returns:
            SkillHint if found, None otherwise
        """
        if not self.learning_manager:
            return None

        try:
            from janus.runtime.core.contracts import SkillHint
            
            # Generate intent vector if embeddings are available
            intent_vector = None
            if self._use_embeddings and self._embedding_model and EMBEDDINGS_AVAILABLE:
                import numpy as np_local
                embedding = self._embedding_model.encode([text])[0]
                intent_vector = embedding.astype(np_local.float32).tobytes()

            # Retrieve cached skill
            skill_data = self.learning_manager.retrieve_cached_skill(
                intent_text=text,
                intent_vector=intent_vector,
                context_data=context_data,
                similarity_threshold=similarity_threshold,
                return_metadata=True,  # Get full metadata, not just actions
            )

            if skill_data:
                # Create SkillHint from the cached skill
                hint = SkillHint(
                    skill_id=skill_data.get("skill_id", 0),
                    intent_text=skill_data.get("intent_text", text),
                    suggested_actions=skill_data.get("action_sequence", []),
                    context_hash=skill_data.get("context_hash", ""),
                    success_count=skill_data.get("success_count", 1),
                    last_used=skill_data.get("last_used", ""),
                    confidence=skill_data.get("similarity", 0.0),
                )
                
                logger.info(
                    f"💡 HINT MODE: Found skill hint for '{text[:50]}...' "
                    f"(confidence: {hint.confidence:.2f}, used {hint.success_count}x) - "
                    f"will suggest to LLM, NOT execute automatically"
                )
                
                return hint

            return None

        except Exception as e:
            logger.warning(f"Error checking skill cache: {e}")
            return None

    def store_successful_sequence(
        self,
        text: str,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Store the current session's successful action sequence as a learned skill

        This should be called after a user correction that results in success.

        Args:
            text: User's intent/command
            context_data: Optional visual/contextual state

        Returns:
            Skill ID if stored, None otherwise
        """
        if not self.learning_manager:
            return None

        try:
            # Generate intent vector if embeddings are available
            intent_vector = None
            if self._use_embeddings and self._embedding_model and EMBEDDINGS_AVAILABLE:
                import numpy as np_local
                embedding = self._embedding_model.encode([text])[0]
                intent_vector = embedding.astype(np_local.float32).tobytes()

            # Store the skill
            skill_id = self.learning_manager.store_corrective_sequence(
                intent_text=text,
                intent_vector=intent_vector,
                context_data=context_data,
            )

            if skill_id:
                logger.info(f"💾 Stored corrective sequence as skill {skill_id} for '{text[:50]}...'")

            return skill_id

        except Exception as e:
            logger.error(f"Error storing successful sequence: {e}")
            return None
