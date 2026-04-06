"""
Voice Reasoning Engine - Modern LLM-based Architecture

This module provides intent recognition and reasoning capabilities for voice commands.
It includes:
- ReasonerLLM: LLM-based cognitive planner (the primary reasoning engine)
- SemanticRouter: Ultra-fast input filtering (NOISE/CHAT/ACTION classification)
- ContextRouter: AI-powered context pruning for performance optimization

Legacy components removed:
- CommandClassifier (ML-based intent classification) - REMOVED
- EnhancedCommandParser (pattern-based parsing) - REMOVED  
- VoiceReasoner (hybrid engine) - REMOVED
- ContextMemory (replaced by MemoryEngine) - REMOVED
"""

from .context_router import ContextRouter, MockContextRouter
from .reasoner_llm import LLMBackend, LLMConfig, ReasonerLLM
from .semantic_router import SemanticRouter

__all__ = [
    "ReasonerLLM",
    "LLMBackend",
    "LLMConfig",
    "ContextRouter",
    "MockContextRouter",
    "SemanticRouter",
]
