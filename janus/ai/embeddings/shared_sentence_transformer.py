"""Shared SentenceTransformer loader.

Centralizes SentenceTransformer initialization to avoid loading the same
~80MB model multiple times (MemoryEngine, SemanticRouter, tool retrieval, etc.).

This module intentionally keeps the interface tiny.
"""

from __future__ import annotations

import threading
from typing import Optional

from janus.runtime.core.memory_engine import DEFAULT_EMBEDDING_MODEL


_lock = threading.Lock()
_cached_model = None
_cached_name: Optional[str] = None


def get_sentence_transformer(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Return a singleton SentenceTransformer instance for the process."""
    global _cached_model, _cached_name

    if _cached_model is not None and _cached_name == model_name:
        return _cached_model

    with _lock:
        if _cached_model is not None and _cached_name == model_name:
            return _cached_model

        from sentence_transformers import SentenceTransformer

        _cached_model = SentenceTransformer(model_name)
        _cached_name = model_name
        return _cached_model

def is_sentence_transformer_loaded() -> bool:
    """Check if the SentenceTransformer model is loaded."""
    return _cached_model is not None
