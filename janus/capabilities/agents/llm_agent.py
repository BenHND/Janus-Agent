"""
TICKET-AUDIT-002: Adapter layer removed. LLMAdapter deleted.
TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

LLMAgent - LLM-based Text Transformations

This agent handles LLM operations for text processing including:
- Summarizing text
- Rewriting text
- Analyzing text
- Extracting keywords
- Answering questions

NOTE: LLMAdapter has been deleted. This agent needs refactoring to call LLM services directly.
"""

import asyncio
from typing import Any, Dict

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action


class LLMAgent(BaseAgent):
    """
    Agent for LLM-based text transformations.
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Supported actions:
    - summarize(text: str)
    - rewrite(text: str, style: str)
    - analyse(text: str)
    - extract_keywords(text: str)
    - answer_question(question: str, context: str)
    """
    
    def __init__(self, provider: str = "openai"):
        """
        Initialize LLMAgent.
        
        Args:
            provider: LLM provider ("openai", "anthropic", "mistral", "local")
        """
        super().__init__("llm")
        self.provider = provider
        self._llm_adapter = None
        self._llm_service = None
    
    @property
    def llm_adapter(self):
        """
        Lazy-load LLM adapter.
        
        DEPRECATED (TICKET-AUDIT-002): Adapters have been removed.
        This property is kept for backward compatibility but always returns None.
        Use llm_service property instead.
        """
        if self._llm_adapter is None:
            self.logger.debug("LLM adapter deprecated, using llm_service instead")
        return self._llm_adapter
    
    @property
    def llm_service(self):
        """Lazy-load LLM service."""
        if self._llm_service is None:
            try:
                from janus.ai.llm.llm_service import LLMService
                self._llm_service = LLMService()
                if not self._llm_service.is_available():
                    self.logger.warning("LLM service not available")
                    self._llm_service = None
            except Exception as e:
                self.logger.warning(f"Could not load LLM service: {e}")
        return self._llm_service
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute an LLM action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing (LLM calls can be expensive)
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would execute LLM action '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": False,
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        # Route to decorated method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        else:
            raise AgentExecutionError(
                module=self.agent_name,
                action=action,
                details=f"Unsupported action: {action}",
                recoverable=False
            )
    
    @agent_action(
        description="Summarize text using LLM",
        required_args=["text"],
        optional_args={"max_length": 150},
        providers=["openai", "anthropic", "mistral", "local"],
        examples=["llm.summarize(text='Long document here...')"]
    )
    async def _summarize(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize text."""
        text = args["text"]
        max_length = args.get("max_length", 150)
        
        if self.llm_service:
            prompt = f"Summarize the following text concisely:\n\n{text}"
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                max_tokens=max_length,
                temperature=0.3
            )
            
            if response.get("success"):
                summary = response.get("content", "").strip()
                return self._success_result(
                    data={"summary": summary},
                    message="Text summarized"
                )
            else:
                return self._error_result(
                    error=response.get("error", "Failed to summarize"),
                    recoverable=True
                )
        
        return self._error_result(
            error="LLM service not available",
            recoverable=True
        )
    
    @agent_action(
        description="Rewrite text in a specific style",
        required_args=["text"],
        optional_args={"style": "professional"},
        providers=["openai", "anthropic", "mistral", "local"],
        examples=["llm.rewrite(text='Original text', style='casual')"]
    )
    async def _rewrite(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Rewrite text."""
        text = args["text"]
        style = args["style"]
        
        if self.llm_service:
            prompt = f"Rewrite the following text in a {style} style:\n\n{text}"
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                max_tokens=300,
                temperature=0.5
            )
            
            if response.get("success"):
                rewritten = response.get("content", "").strip()
                return self._success_result(
                    data={"rewritten": rewritten},
                    message="Text rewritten"
                )
            else:
                return self._error_result(
                    error=response.get("error", "Failed to rewrite"),
                    recoverable=True
                )
        
        return self._error_result(
            error="LLM service not available",
            recoverable=True
        )
    
    @agent_action(
        description="Analyze text and provide insights",
        required_args=["text"],
        providers=["openai", "anthropic", "mistral", "local"],
        examples=["llm.analyse(text='Text to analyze')"]
    )
    async def _analyse(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze text."""
        text = args["text"]
        
        if self.llm_service:
            prompt = f"Analyze the following text and provide insights:\n\n{text}"
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            if response.get("success"):
                analysis = response.get("content", "").strip()
                return self._success_result(
                    data={"analysis": analysis},
                    message="Text analyzed"
                )
            else:
                return self._error_result(
                    error=response.get("error", "Failed to analyze"),
                    recoverable=True
                )
        
        return self._error_result(
            error="LLM service not available",
            recoverable=True
        )
    
    # Alias for analyse
    _analyze_error = _analyse
    
    @agent_action(
        description="Extract keywords from text",
        required_args=["text"],
        optional_args={"max_keywords": 10},
        providers=["openai", "anthropic", "mistral", "local"],
        examples=["llm.extract_keywords(text='Text with important keywords')"]
    )
    async def _extract_keywords(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords from text."""
        text = args["text"]
        
        if self.llm_service:
            prompt = f"Extract the main keywords from the following text as a comma-separated list:\n\n{text}"
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                max_tokens=100,
                temperature=0.2
            )
            
            if response.get("success"):
                keywords_str = response.get("content", "").strip()
                keywords = [k.strip() for k in keywords_str.split(",")]
                return self._success_result(
                    data={"keywords": keywords},
                    message=f"Extracted {len(keywords)} keywords"
                )
            else:
                return self._error_result(
                    error=response.get("error", "Failed to extract keywords"),
                    recoverable=True
                )
        
        return self._error_result(
            error="LLM service not available",
            recoverable=True
        )
    
    @agent_action(
        description="Answer a question based on provided context",
        required_args=["question"],
        optional_args={"context": ""},
        providers=["openai", "anthropic", "mistral", "local"],
        examples=["llm.answer_question(question='What is AI?', context='AI is...')"]
    )
    async def _answer_question(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a question with given context."""
        question = args["question"]
        context_text = args["context"]
        
        if self.llm_service:
            if context_text:
                prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
            else:
                prompt = f"Question: {question}\n\nAnswer:"
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response.get("success"):
                answer = response.get("content", "").strip()
                return self._success_result(
                    data={"answer": answer},
                    message="Question answered"
                )
            else:
                return self._error_result(
                    error=response.get("error", "Failed to answer question"),
                    recoverable=True
                )
        
        return self._error_result(
            error="LLM service not available",
            recoverable=True
        )
