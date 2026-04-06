"""
I18N Message Loader

TICKET-CLEAN-GLOBAL: Infrastructure for loading internationalized system messages.
This replaces hardcoded strings in the codebase with externalized JSON messages.
"""

import json
import functools
from pathlib import Path
from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("i18n_loader")

# Path to i18n messages directory
I18N_DIR = Path(__file__).parent.parent / "resources" / "i18n"


class I18NLoader:
    """
    Load internationalized messages from JSON files.
    
    Features:
    - Message caching for performance
    - Fallback to English if translation missing
    - String formatting with parameters
    """
    
    def __init__(self, i18n_dir: Optional[Path] = None):
        """
        Initialize the I18N loader.
        
        Args:
            i18n_dir: Optional custom path to i18n directory.
                     Defaults to janus/resources/i18n/
        """
        self.i18n_dir = i18n_dir or I18N_DIR
        self._messages_cache: Dict[str, Dict[str, Any]] = {}
        
        if not self.i18n_dir.exists():
            logger.warning(f"I18N directory not found: {self.i18n_dir}")
    
    @functools.lru_cache(maxsize=8)
    def _load_messages_file(self, filename: str) -> Dict[str, Any]:
        """
        Load and cache a messages JSON file.
        
        Args:
            filename: Name of the JSON file (e.g., 'system_messages.json')
            
        Returns:
            Dictionary of messages, or empty dict if not found
        """
        filepath = self.i18n_dir / filename
        
        if not filepath.exists():
            logger.error(f"Messages file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                return messages
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}
    
    def get(
        self,
        key: str,
        language: str = "fr",
        filename: str = "system_messages.json",
        **kwargs: Any
    ) -> str:
        """
        Get a message by key and format it with parameters.
        
        Args:
            key: Dot-separated message key (e.g., 'verification.finish_error')
            language: Language code ('fr' or 'en')
            filename: Messages file to load from
            **kwargs: Parameters for string formatting
            
        Returns:
            Formatted message string
            
        Example:
            loader = I18NLoader()
            msg = loader.get(
                'verification.finish_error',
                language='fr',
                reason='Mot de passe incorrect'
            )
        """
        # Load messages file
        messages = self._load_messages_file(filename)
        
        if not messages:
            logger.error(f"No messages loaded from {filename}")
            return f"[Missing message: {key}]"
        
        # Navigate through nested keys
        keys = key.split('.')
        current = messages
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                logger.error(f"Message key not found: {key} in {filename}")
                return f"[Missing message: {key}]"
            current = current[k]
        
        # Get language-specific message
        if isinstance(current, dict):
            message = current.get(language)
            
            # Fallback to English if requested language not found
            if message is None and language != "en":
                message = current.get("en")
                if message:
                    logger.debug(f"Falling back to English for {key}")
            
            if message is None:
                logger.error(f"No translation found for {key} in language {language}")
                return f"[Missing translation: {key}@{language}]"
        else:
            message = current
        
        # Format with parameters
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format parameter {e} for message {key}")
            return message  # Return unformatted message
        except Exception as e:
            logger.error(f"Error formatting message {key}: {e}")
            return message
    
    def clear_cache(self) -> None:
        """Clear the messages cache."""
        self._load_messages_file.cache_clear()
        self._messages_cache.clear()
        logger.debug("I18N cache cleared")


# Global singleton instance for efficient reuse
_global_loader: Optional[I18NLoader] = None


def get_i18n_loader() -> I18NLoader:
    """
    Get the global I18NLoader instance.
    
    Returns:
        Singleton I18NLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = I18NLoader()
    return _global_loader


def get_message(key: str, language: str = "fr", **kwargs: Any) -> str:
    """
    Convenience function to get a message using the global loader.
    
    Args:
        key: Dot-separated message key
        language: Language code ('fr' or 'en')
        **kwargs: Parameters for string formatting
        
    Returns:
        Formatted message string
    """
    return get_i18n_loader().get(key, language, **kwargs)
