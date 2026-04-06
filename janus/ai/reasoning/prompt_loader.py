"""
Prompt Template Loader for ReasonerLLM

TICKET-306: Externalization of prompts to Jinja2 templates.
This module provides a clean interface for loading and rendering
prompt templates from external files.
"""

import functools
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from janus.logging import get_logger

logger = get_logger("prompt_loader")

# Path to prompt templates directory
PROMPTS_DIR = Path(__file__).parent.parent / "resources" / "prompts"


class PromptLoader:
    """
    Load and render Jinja2 prompt templates.
    
    Features:
    - Template caching for performance
    - Fallback to default language (French)
    - Type-safe template rendering
    - Strict mode for fail-fast behavior (TICKET-CLEAN-GLOBAL)
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None, strict_mode: bool = False):
        """
        Initialize the prompt loader.
        
        Args:
            prompts_dir: Optional custom path to prompts directory.
                        Defaults to janus/resources/prompts/
            strict_mode: If True, raise FileNotFoundError when template is missing.
                        TICKET-CLEAN-GLOBAL: Enables fail-fast behavior.
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self.strict_mode = strict_mode
        
        if not self.prompts_dir.exists():
            if strict_mode:
                raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            self._env = None
        else:
            self._env = Environment(
                loader=FileSystemLoader(str(self.prompts_dir)),
                autoescape=False,  # Prompts are plain text, not HTML
                trim_blocks=True,
                lstrip_blocks=True,
            )
            logger.debug(f"PromptLoader initialized with directory: {self.prompts_dir}")
    
    @functools.lru_cache(maxsize=32)
    def _load_template_cached(self, template_name: str) -> Optional[Template]:
        """
        Load and cache a template file.
        
        Args:
            template_name: Name of the template file (e.g., 'parse_command_fr.jinja2')
            
        Returns:
            Jinja2 Template object, or None if not found
        """
        if self._env is None:
            return None
            
        try:
            template = self._env.get_template(template_name)
            return template
        except TemplateNotFound:
            logger.warning(f"Template not found: {template_name}")
            return None
    
    def load_prompt(
        self,
        template_name: str,
        language: str = "fr",
        **kwargs: Any
    ) -> Optional[str]:
        """
        Load and render a prompt template.
        
        TICKET-CLEAN-GLOBAL: In strict mode, raises FileNotFoundError if template missing.
        
        Args:
            template_name: Base name of the template (without language suffix)
                          e.g., 'parse_command', 'reasoner_v3_system'
            language: Language code ('fr' or 'en')
            **kwargs: Variables to pass to the template for rendering
            
        Returns:
            Rendered prompt string, or None if template not found (non-strict mode)
            
        Raises:
            FileNotFoundError: If template not found and strict_mode=True
            
        Example:
            loader = PromptLoader()
            prompt = loader.load_prompt(
                'reasoner_v3_system',
                language='fr',
                schema_section='...'
            )
        """
        # Try language-specific template first
        full_name = f"{template_name}_{language}.jinja2"
        template = self._load_template_cached(full_name)
        
        # Fallback to French if requested language not found
        if template is None and language != "fr":
            logger.debug(f"Falling back to French template for {template_name}")
            full_name = f"{template_name}_fr.jinja2"
            template = self._load_template_cached(full_name)
        
        if template is None:
            error_msg = f"No template found for {template_name} in any language"
            if self.strict_mode:
                raise FileNotFoundError(error_msg)
            logger.error(error_msg)
            return None
        
        try:
            rendered = template.render(**kwargs)
            return rendered
        except Exception as e:
            error_msg = f"Error rendering template {full_name}: {e}"
            if self.strict_mode:
                raise RuntimeError(error_msg) from e
            logger.error(error_msg)
            return None
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._load_template_cached.cache_clear()
        logger.debug("Template cache cleared")
    
    def template_exists(self, template_name: str, language: str = "fr") -> bool:
        """
        Check if a template exists.
        
        Args:
            template_name: Base name of the template
            language: Language code
            
        Returns:
            True if template exists, False otherwise
        """
        full_name = f"{template_name}_{language}.jinja2"
        template_path = self.prompts_dir / full_name
        return template_path.exists()


# Global singleton instance for efficient reuse
_global_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    Get the global PromptLoader instance.
    
    Returns:
        Singleton PromptLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = PromptLoader()
    return _global_loader


def load_prompt(template_name: str, language: str = "fr", **kwargs: Any) -> Optional[str]:
    """
    Convenience function to load a prompt using the global loader.
    
    Args:
        template_name: Base name of the template
        language: Language code ('fr' or 'en')
        **kwargs: Variables for template rendering
        
    Returns:
        Rendered prompt string, or None if not found
    """
    return get_prompt_loader().load_prompt(template_name, language, **kwargs)
