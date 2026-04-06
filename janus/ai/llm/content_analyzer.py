"""
Content Analyzer for code and text analysis
Uses UnifiedLLMClient for all content analysis operations.
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from janus.constants import MAX_CONTENT_SUMMARY_LENGTH, ActionStatus

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Supported content types"""

    TEXT = "text"
    CODE = "code"
    JSON = "json"
    MARKDOWN = "markdown"
    LOG = "log"
    ERROR = "error"


class AnalysisTask(Enum):
    """Supported analysis tasks"""

    SUMMARIZE = "summarize"
    ANALYZE = "analyze"
    EXPLAIN = "explain"
    DEBUG = "debug"
    REVIEW = "review"
    EXTRACT = "extract"


class ContentAnalyzer:
    """
    Analyzes content using LLM
    Supports code analysis, summarization, and content understanding
    """

    def __init__(self, llm_client=None):
        """
        Initialize content analyzer

        Args:
            llm_client: UnifiedLLMClient instance (optional)
        """
        self.llm_client = llm_client

    def analyze(
        self,
        content: str,
        content_type: str = "text",
        task: str = "summarize",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze content

        Args:
            content: Content to analyze
            content_type: Type of content (text, code, json, etc.)
            task: Analysis task (summarize, analyze, explain, etc.)
            context: Optional context information

        Returns:
            Analysis result dictionary
        """
        # Validate inputs
        try:
            content_type_enum = ContentType(content_type)
            task_enum = AnalysisTask(task)
        except ValueError as e:
            return {"status": "error", "error": f"Invalid content_type or task: {e}"}

        # Use LLM if available
        if self.llm_client:
            return self.llm_client.analyze_content(content, content_type, task)

        # Fallback to basic analysis
        return self._basic_analysis(content, content_type_enum, task_enum, context)

    def summarize_code(self, code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Summarize code snippet

        Args:
            code: Code to summarize
            language: Programming language (optional)

        Returns:
            Summary result
        """
        context = {"language": language} if language else None
        return self.analyze(code, "code", "summarize", context)

    def explain_code(self, code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Explain what code does

        Args:
            code: Code to explain
            language: Programming language (optional)

        Returns:
            Explanation result
        """
        context = {"language": language} if language else None
        return self.analyze(code, "code", "explain", context)

    def debug_code(
        self, code: str, error: Optional[str] = None, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze code for potential bugs or issues

        Args:
            code: Code to debug
            error: Error message (optional)
            language: Programming language (optional)

        Returns:
            Debug analysis result
        """
        context = {"language": language, "error": error}
        return self.analyze(code, "code", "debug", context)

    def review_code(self, code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Review code for quality and best practices

        Args:
            code: Code to review
            language: Programming language (optional)

        Returns:
            Code review result
        """
        context = {"language": language} if language else None
        return self.analyze(code, "code", "review", context)

    def summarize_text(self, text: str, max_length: Optional[int] = None) -> Dict[str, Any]:
        """
        Summarize text content

        Args:
            text: Text to summarize
            max_length: Maximum summary length (optional)

        Returns:
            Summary result
        """
        context = {"max_length": max_length} if max_length else None
        return self.analyze(text, "text", "summarize", context)

    def extract_info(
        self, content: str, extraction_target: str, content_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Extract specific information from content

        Args:
            content: Content to extract from
            extraction_target: What to extract (e.g., "emails", "dates", "names")
            content_type: Type of content

        Returns:
            Extraction result
        """
        context = {"extraction_target": extraction_target}
        return self.analyze(content, content_type, "extract", context)

    def _basic_analysis(
        self,
        content: str,
        content_type: ContentType,
        task: AnalysisTask,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Basic analysis without LLM (fallback)

        Args:
            content: Content to analyze
            content_type: Content type enum
            task: Analysis task enum
            context: Optional context

        Returns:
            Basic analysis result
        """
        result = {
            "status": ActionStatus.SUCCESS.value,
            "content_type": content_type.value,
            "task": task.value,
            "analysis_method": "basic",
        }

        # Basic statistics
        result["stats"] = {
            "length": len(content),
            "lines": content.count("\n") + 1,
            "words": len(content.split()),
            "characters": len(content),
        }

        # Task-specific basic analysis
        if task == AnalysisTask.SUMMARIZE:
            # Simple truncation for summary
            if len(content) > MAX_CONTENT_SUMMARY_LENGTH:
                result["summary"] = content[:MAX_CONTENT_SUMMARY_LENGTH] + "..."
            else:
                result["summary"] = content

        elif task == AnalysisTask.ANALYZE:
            result["analysis"] = (
                f"Basic analysis: {content_type.value} with {result['stats']['lines']} lines"
            )

        elif task == AnalysisTask.EXPLAIN:
            result["explanation"] = (
                f"This is {content_type.value} content with {result['stats']['words']} words"
            )

        elif task == AnalysisTask.DEBUG:
            # TICKET-ARCH-FINAL: Removed hardcoded error_keywords.
            # Use LLM service for intelligent debugging instead of keyword matching.
            result["debug"] = {
                "suggestion": "Use LLM service for detailed debugging and error analysis",
                "note": "Keyword-based error detection removed in favor of AI-based analysis"
            }

        elif task == AnalysisTask.REVIEW:
            result["review"] = "Basic review: Use LLM service for detailed code review"

        elif task == AnalysisTask.EXTRACT:
            target = context.get("extraction_target", "unknown") if context else "unknown"
            result["extraction"] = (
                f"Extraction target: {target}. Use LLM service for accurate extraction."
            )

        return result

    def detect_content_type(self, content: str, filename: Optional[str] = None) -> str:
        """
        Detect content type from content or filename

        Args:
            content: Content to analyze
            filename: Optional filename for extension-based detection

        Returns:
            Detected content type
        """
        if filename:
            # Detect by extension
            ext_map = {
                ".py": "code",
                ".js": "code",
                ".ts": "code",
                ".java": "code",
                ".cpp": "code",
                ".c": "code",
                ".go": "code",
                ".rs": "code",
                ".rb": "code",
                ".php": "code",
                ".json": "json",
                ".md": "markdown",
                ".txt": "text",
                ".log": "log",
            }

            for ext, ctype in ext_map.items():
                if filename.endswith(ext):
                    return ctype

        # Detect by content
        content_lower = content.lower()

        # Check for JSON
        if content.strip().startswith(("{", "[")):
            try:
                import json

                json.loads(content)
                return "json"
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Content is not valid JSON: {e}")
                pass

        # Check for code patterns
        code_indicators = ["def ", "function ", "class ", "import ", "const ", "var ", "let "]
        if any(indicator in content_lower for indicator in code_indicators):
            return "code"

        # Check for error patterns
        error_indicators = ["error:", "exception:", "traceback", "stack trace"]
        if any(indicator in content_lower for indicator in error_indicators):
            return "error"

        # Default to text
        return "text"
