"""
Context Ranking Module for Janus (TICKET A4, TICKET-P2-03).

Provides relevance scoring and temporal decay for context items
to improve context awareness and memory efficiency.

Features:
- Relevance scoring based on temporal proximity and type matching
- Temporal decay for older context items (exponential decay model)
- Type-aware scoring (app->app, file->file similarity)
- Smart context loading to avoid loading entire history
- TF-IDF-based semantic similarity for command text matching (TICKET-P2-03)
- Intelligent context pruning to reduce LLM prompt size by 40%

Example usage:
    ranker = ContextRanker(decay_halflife_hours=24.0)
    intent = Intent(action='open_app', confidence=0.9, parameters={'app_name': 'Chrome'})
    ranked_items = ranker.rank_context_items(context_items, intent, max_items=20)
    
    # TICKET-P2-03: Rank commands by TF-IDF similarity
    relevant_commands = ranker.rank_commands_by_similarity(
        current_command="ouvre Safari",
        command_history=[...],
        max_items=5
    )
"""

import math
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .contracts import Intent


# TICKET-P2-03: Module-level stopwords set for French and English
# Extracted to module level for better maintainability and reusability
STOPWORDS_FR_EN = frozenset({
    # French articles, prepositions, pronouns
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
    'donc', 'car', 'ni', 'que', 'qui', 'quoi', 'dont', 'où', 'ce', 'cette',
    'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
    'notre', 'votre', 'leur', 'nos', 'vos', 'leurs', 'je', 'tu', 'il',
    'elle', 'nous', 'vous', 'ils', 'elles', 'se', 'en', 'y', 'au', 'aux',
    'avec', 'sans', 'sous', 'sur', 'dans', 'par', 'pour', 'vers', 'chez',
    'à', 'a', 'est', 'sont', 'ont', 'ai', 'as', 'avons', 'avez',
    # English articles, prepositions, pronouns, auxiliaries
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'my', 'your', 'his', 'her', 'its', 'our', 'their',
})

# TICKET-P2-03: Regex pattern for tokenization
# Uses Unicode word characters (\w) which includes accented letters
# This is more maintainable than listing all French characters explicitly
_TOKENIZE_PATTERN = re.compile(r'[^\w]+', re.UNICODE)


class ContextRanker:
    """
    Ranks and scores context items based on relevance to current intent.

    Scoring factors:
    - Temporal proximity (recent = higher score)
    - Type match (app->app, file->file)
    - Semantic similarity (if available)
    """

    def __init__(self, decay_halflife_hours: float = 24.0):
        """
        Initialize context ranker.

        Args:
            decay_halflife_hours: Hours after which context relevance is halved
        """
        self.decay_halflife_hours = decay_halflife_hours

    def score_relevance(self, context_item: Dict[str, Any], current_intent: Intent) -> float:
        """
        Score relevance of a context item to current intent.

        Args:
            context_item: Context item with 'type', 'data', 'timestamp'
            current_intent: Current user intent

        Returns:
            Relevance score (0.0 to 1.0, higher is more relevant)
        """
        score = 0.0

        # Base score for all context
        score += 0.3

        # Type matching bonus
        type_score = self._score_type_match(context_item, current_intent)
        score += type_score * 0.4

        # Temporal proximity bonus
        temporal_score = self._score_temporal_proximity(context_item)
        score += temporal_score * 0.3

        # Ensure score is in valid range
        return min(1.0, max(0.0, score))

    def _score_type_match(self, context_item: Dict[str, Any], current_intent: Intent) -> float:
        """
        Score based on type matching between context and intent.

        Returns:
            Type match score (0.0 to 1.0)
        """
        context_type = context_item.get("type", "")
        intent_action = current_intent.action
        intent_params = current_intent.parameters

        # App-related context matching app-related intents
        if context_type == "app" or context_type == "application":
            if "app" in intent_action.lower() or "app_name" in intent_params:
                # Check if same app
                context_app = context_item.get("data", {}).get("app_name", "")
                intent_app = intent_params.get("app_name", "")
                if context_app and intent_app and context_app.lower() == intent_app.lower():
                    return 1.0
                return 0.7
            return 0.3

        # File-related context matching file-related intents
        if context_type == "file" or context_type == "file_operation":
            if "file" in intent_action.lower() or "path" in intent_params:
                # Check if same file
                context_file = context_item.get("data", {}).get("file_path", "")
                intent_file = intent_params.get("path", "") or intent_params.get("file_path", "")
                if context_file and intent_file and context_file == intent_file:
                    return 1.0
                # Same directory?
                if context_file and intent_file:
                    import os

                    if os.path.dirname(context_file) == os.path.dirname(intent_file):
                        return 0.8
                return 0.7
            return 0.3

        # Browser/URL context matching browser intents
        if context_type == "browser" or context_type == "url":
            if "browser" in intent_action.lower() or "url" in intent_params:
                return 0.8
            return 0.2

        # Text/clipboard context for text operations
        if context_type == "clipboard" or context_type == "text":
            if "paste" in intent_action.lower() or "copy" in intent_action.lower():
                return 0.9
            return 0.4

        # User action context (clicks, typing)
        if context_type == "user_action":
            # User actions are generally relevant for understanding workflow
            return 0.5

        # Default moderate relevance for unknown types
        return 0.4

    def _score_temporal_proximity(self, context_item: Dict[str, Any]) -> float:
        """
        Score based on how recent the context is.

        Returns:
            Temporal proximity score (0.0 to 1.0, 1.0 = very recent)
        """
        timestamp_str = context_item.get("timestamp")
        if not timestamp_str:
            # No timestamp, assume old
            return 0.1

        try:
            # Parse timestamp
            if isinstance(timestamp_str, datetime):
                context_time = timestamp_str
            else:
                # Try parsing ISO format
                context_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Calculate age in hours
            age_hours = (datetime.now() - context_time.replace(tzinfo=None)).total_seconds() / 3600

            # Recent context (< 1 hour) gets high score
            if age_hours < 1.0:
                return 1.0

            # Use exponential decay for older context
            # After 24 hours, score is ~0.5
            # After 48 hours, score is ~0.25
            decay_score = 1.0 / (1.0 + (age_hours / 24.0))
            return decay_score

        except (ValueError, AttributeError, TypeError):
            # Invalid timestamp, assume old
            return 0.1

    def apply_decay(self, age_hours: float) -> float:
        """
        Apply temporal decay based on age.

        Older context gets lower weight. Uses exponential decay with
        configurable half-life.

        Args:
            age_hours: Age of context in hours

        Returns:
            Decay multiplier (0.0 to 1.0)
        """
        if age_hours <= 0:
            return 1.0

        # Exponential decay: weight = 1 / (1 + age/halflife)
        # This gives:
        # - age=0: weight=1.0 (100%)
        # - age=halflife: weight=0.5 (50%)
        # - age=2*halflife: weight=0.33 (33%)
        # - age=3*halflife: weight=0.25 (25%)
        decay_multiplier = 1.0 / (1.0 + (age_hours / self.decay_halflife_hours))

        return decay_multiplier

    def rank_context_items(
        self, context_items: List[Dict[str, Any]], current_intent: Intent, max_items: int = 20
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rank a list of context items by relevance.

        Args:
            context_items: List of context items to rank
            current_intent: Current user intent
            max_items: Maximum number of items to return

        Returns:
            List of (context_item, score) tuples, sorted by score descending
        """
        scored_items = []

        for item in context_items:
            # Calculate relevance score
            relevance_score = self.score_relevance(item, current_intent)

            # Apply temporal decay
            age_hours = self._get_age_hours(item)
            decay_multiplier = self.apply_decay(age_hours)

            # Final score = relevance * decay
            final_score = relevance_score * decay_multiplier

            scored_items.append((item, final_score))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Return top N
        return scored_items[:max_items]

    def _get_age_hours(self, context_item: Dict[str, Any]) -> float:
        """
        Get age of context item in hours.

        Returns:
            Age in hours, or a large value if timestamp is invalid
        """
        timestamp_str = context_item.get("timestamp")
        if not timestamp_str:
            return 168.0  # Default to 1 week old

        try:
            if isinstance(timestamp_str, datetime):
                context_time = timestamp_str
            else:
                context_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            age_seconds = (datetime.now() - context_time.replace(tzinfo=None)).total_seconds()
            return age_seconds / 3600

        except (ValueError, AttributeError, TypeError):
            return 168.0  # Default to 1 week old

    # =========================================================================
    # TICKET-P2-03: TF-IDF-based Context Pruning for LLM Prompt Optimization
    # =========================================================================

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into lowercase words, removing punctuation and stopwords.
        
        Uses the module-level STOPWORDS_FR_EN constant and compiled regex
        pattern for better maintainability and performance.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of normalized tokens
        """
        if not text:
            return []
        
        # Use compiled regex pattern for tokenization (handles Unicode)
        tokens = _TOKENIZE_PATTERN.split(text.lower())
        
        # Filter out stopwords and empty/short tokens using module-level constant
        return [t for t in tokens if t and len(t) > 1 and t not in STOPWORDS_FR_EN]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Compute Term Frequency (TF) for a list of tokens.
        
        TF(t) = (Number of times term t appears in document) / (Total terms in document)
        
        Args:
            tokens: List of tokens
            
        Returns:
            Dictionary mapping terms to their TF scores
        """
        if not tokens:
            return {}
        
        term_counts = Counter(tokens)
        total_terms = len(tokens)
        
        return {term: count / total_terms for term, count in term_counts.items()}

    def _compute_idf(self, documents: List[List[str]]) -> Dict[str, float]:
        """
        Compute Inverse Document Frequency (IDF) for all terms across documents.
        
        IDF(t) = log(N / (1 + df(t)))
        where N is total number of documents and df(t) is number of documents containing term t.
        
        Args:
            documents: List of tokenized documents
            
        Returns:
            Dictionary mapping terms to their IDF scores
        """
        if not documents:
            return {}
        
        n_docs = len(documents)
        
        # Count document frequency for each term
        doc_freq: Dict[str, int] = {}
        for doc_tokens in documents:
            # Use set to count each term only once per document
            unique_terms = set(doc_tokens)
            for term in unique_terms:
                doc_freq[term] = doc_freq.get(term, 0) + 1
        
        # Compute IDF for each term
        idf = {}
        for term, df in doc_freq.items():
            # Add 1 to denominator to avoid division by zero
            idf[term] = math.log(n_docs / (1 + df))
        
        return idf

    def _compute_tfidf(
        self, tokens: List[str], idf: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute TF-IDF scores for a document.
        
        Args:
            tokens: Tokenized document
            idf: IDF scores for all terms
            
        Returns:
            Dictionary mapping terms to their TF-IDF scores
        """
        tf = self._compute_tf(tokens)
        
        tfidf = {}
        for term, tf_score in tf.items():
            idf_score = idf.get(term, 0.0)
            tfidf[term] = tf_score * idf_score
        
        return tfidf

    def _cosine_similarity(
        self, vec1: Dict[str, float], vec2: Dict[str, float]
    ) -> float:
        """
        Compute cosine similarity between two TF-IDF vectors.
        
        Args:
            vec1: First TF-IDF vector
            vec2: Second TF-IDF vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if not vec1 or not vec2:
            return 0.0
        
        # Get intersection of terms
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # Compute dot product
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # Compute magnitudes
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)

    def rank_commands_by_similarity(
        self,
        current_command: str,
        command_history: List[Dict[str, Any]],
        max_items: int = 5,
        include_temporal_decay: bool = True,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rank command history by TF-IDF similarity to the current command.
        
        TICKET-P2-03: This method implements intelligent context pruning by
        selecting only the most relevant past commands instead of sending
        the entire history to the LLM. This reduces prompt size by ~40%.
        
        Args:
            current_command: The current user command
            command_history: List of past commands with 'raw_command' and optional 'timestamp'
            max_items: Maximum number of relevant commands to return (default: 5)
            include_temporal_decay: If True, also factor in temporal decay
            
        Returns:
            List of (command_item, score) tuples, sorted by relevance score descending
            
        Example:
            ranker = ContextRanker()
            relevant = ranker.rank_commands_by_similarity(
                current_command="ouvre Safari et va sur YouTube",
                command_history=[
                    {"raw_command": "ouvre Chrome", "timestamp": "2024-01-01T10:00:00"},
                    {"raw_command": "cherche python sur Google", "timestamp": "2024-01-01T09:00:00"},
                    {"raw_command": "ouvre Safari", "timestamp": "2024-01-01T08:00:00"},
                ],
                max_items=5
            )
            # Returns: [("ouvre Safari", 0.95), ("ouvre Chrome", 0.75), ...]
        """
        if not command_history:
            return []
        
        # Tokenize all commands (current + history)
        current_tokens = self._tokenize(current_command)
        
        if not current_tokens:
            # If current command has no meaningful tokens, return empty
            return []
        
        # Tokenize all history commands
        history_tokens = []
        for cmd in command_history:
            raw_cmd = cmd.get("raw_command", "")
            tokens = self._tokenize(raw_cmd)
            history_tokens.append(tokens)
        
        # Build corpus (current + all history) for IDF computation
        all_documents = [current_tokens] + history_tokens
        
        # Compute IDF across all documents
        idf = self._compute_idf(all_documents)
        
        # Compute TF-IDF for current command
        current_tfidf = self._compute_tfidf(current_tokens, idf)
        
        # Score each history command
        scored_commands = []
        for i, cmd in enumerate(command_history):
            # Compute TF-IDF for this command
            cmd_tfidf = self._compute_tfidf(history_tokens[i], idf)
            
            # Compute cosine similarity
            similarity = self._cosine_similarity(current_tfidf, cmd_tfidf)
            
            # Apply temporal decay if enabled
            if include_temporal_decay:
                age_hours = self._get_age_hours(cmd)
                decay = self.apply_decay(age_hours)
                # Combine similarity with decay (weighted average: 70% similarity, 30% recency)
                score = 0.7 * similarity + 0.3 * decay
            else:
                score = similarity
            
            scored_commands.append((cmd, score))
        
        # Sort by score descending
        scored_commands.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return scored_commands[:max_items]

    def get_pruned_context(
        self,
        current_command: str,
        command_history: List[Dict[str, Any]],
        max_commands: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get a pruned context containing only the most relevant commands.
        
        TICKET-P2-03: This is the main entry point for context pruning.
        It returns a cleaned list of commands that should be included in
        the LLM prompt, achieving ~40% reduction in prompt size for long sessions.
        
        Args:
            current_command: The current user command
            command_history: Full command history
            max_commands: Maximum number of commands to include (default: 5)
            
        Returns:
            List of the most relevant command dictionaries, pruned and cleaned
        """
        if not command_history:
            return []
        
        # Rank commands by similarity
        ranked = self.rank_commands_by_similarity(
            current_command=current_command,
            command_history=command_history,
            max_items=max_commands,
            include_temporal_decay=True,
        )
        
        # Extract just the command items (without scores)
        pruned_commands = []
        for cmd, score in ranked:
            # Clean the command to remove technical logs and unnecessary fields
            clean_cmd = self._clean_command_for_prompt(cmd)
            if clean_cmd:
                pruned_commands.append(clean_cmd)
        
        return pruned_commands

    def _clean_command_for_prompt(self, cmd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean a command dictionary for inclusion in LLM prompt.
        
        TICKET-P2-03: Removes technical logs and unnecessary fields to reduce
        prompt size while keeping essential information.
        
        Args:
            cmd: Raw command dictionary
            
        Returns:
            Cleaned command dictionary or None if command should be excluded
        """
        if not cmd:
            return None
        
        raw_command = cmd.get("raw_command", "")
        
        # Skip empty or very short commands
        if not raw_command or len(raw_command.strip()) < 2:
            return None
        
        # Create cleaned version with only essential fields
        cleaned = {
            "command": raw_command.strip(),
        }
        
        # Optionally include intent if it's meaningful (not 'unknown')
        intent = cmd.get("intent", "")
        if intent and intent.lower() not in ("unknown", "error", ""):
            cleaned["intent"] = intent
        
        return cleaned

    def estimate_prompt_reduction(
        self,
        full_history: List[Dict[str, Any]],
        pruned_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Estimate the prompt size reduction achieved by pruning.
        
        TICKET-P2-03: This method helps verify that we achieve the target
        40% reduction in prompt size for long sessions.
        
        Args:
            full_history: Original full command history
            pruned_history: Pruned command history
            
        Returns:
            Dictionary with reduction metrics
        """
        import json
        
        # Estimate size in characters (proxy for tokens)
        full_size = len(json.dumps(full_history, ensure_ascii=False))
        pruned_size = len(json.dumps(pruned_history, ensure_ascii=False))
        
        reduction = 0.0
        if full_size > 0:
            reduction = (full_size - pruned_size) / full_size * 100
        
        return {
            "full_history_size": full_size,
            "pruned_history_size": pruned_size,
            "reduction_percent": round(reduction, 1),
            "full_command_count": len(full_history),
            "pruned_command_count": len(pruned_history),
            "target_reduction_met": reduction >= 40.0,
        }
    
    def rank_and_cut(
        self,
        items: List[Any],
        current_intent: Optional[Intent] = None,
        max_tokens: int = 1500,
    ) -> List[Any]:
        """
        Rank items by relevance and BRUTALLY CUT at max_tokens.
        
        PERF-M4-001: This method implements the strict token budget enforcement
        required for M4 performance. Unlike get_pruned_context which returns
        a cleaned list, this method stops adding items as soon as the token
        budget is exceeded.
        
        Args:
            items: List of items to rank and cut (can be context items, commands, etc.)
            current_intent: Optional current intent for relevance scoring
            max_tokens: Maximum tokens allowed (default: 1500 for M4)
            
        Returns:
            List of items that fit within max_tokens budget
            
        Example:
            ranker = ContextRanker()
            intent = Intent(action='open_app', ...)
            
            # This will stop adding items when token budget is exceeded
            cut_items = ranker.rank_and_cut(
                items=context_items,
                current_intent=intent,
                max_tokens=1500
            )
        """
        if not items:
            return []
        
        # Rank items by relevance if intent provided
        if current_intent:
            ranked = self.rank_context_items(
                context_items=items,
                current_intent=current_intent,
                max_items=len(items)  # Don't limit by count, only by tokens
            )
            # Extract just the items (without scores)
            ranked_items = [item for item, score in ranked]
        else:
            # No intent - use items as-is (most recent first for temporal items)
            ranked_items = items
        
        # Brutally cut at max_tokens
        result = []
        current_tokens = 0
        
        for item in ranked_items:
            # Estimate tokens for this item
            item_tokens = self._estimate_item_tokens(item)
            
            # Check if adding this item would exceed budget
            if current_tokens + item_tokens > max_tokens:
                # STOP - budget exceeded
                break
            
            # Add item and update token count
            result.append(item)
            current_tokens += item_tokens
        
        return result
    
    def _estimate_item_tokens(self, item: Any) -> int:
        """
        Estimate token count for a single item.
        
        Args:
            item: Item to estimate (dict, string, or object)
            
        Returns:
            Estimated token count
        """
        import json
        
        # Convert item to string representation
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            text = json.dumps(item, ensure_ascii=False)
        else:
            # Try to serialize object
            try:
                text = str(item)
            except:
                # Fallback: assume 50 tokens for unknown objects
                return 50
        
        # Use 4-char-per-token heuristic
        return max(1, len(text) // 4)
