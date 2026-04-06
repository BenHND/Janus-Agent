"""
Locale Loader for Language-Specific Resources

This module loads language-specific resources like keywords, selectors, and UI strings
from JSON files. It's part of the internationalization system to eliminate magic strings.

TICKET-ARCH-FINAL: Zero Magic String & Complete Internationalization
"""

import json
import functools
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.logging import get_logger

logger = get_logger("locale_loader")

# Path to locales directory
LOCALES_DIR = Path(__file__).parent.parent / "resources" / "locales"


class LocaleLoader:
    """
    Load language-specific resources from JSON files.
    
    Features:
    - Keyword lists (confirmation responses, etc.)
    - CSS/XPath selectors for different languages
    - UI string resources
    - Fallback to English if translation missing
    """
    
    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Initialize the Locale loader.
        
        Args:
            locales_dir: Optional custom path to locales directory.
                        Defaults to janus/resources/locales/
        """
        self.locales_dir = locales_dir or LOCALES_DIR
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        if not self.locales_dir.exists():
            logger.warning(f"Locales directory not found: {self.locales_dir}")
    
    @functools.lru_cache(maxsize=8)
    def _load_locale_file(self, language: str) -> Dict[str, Any]:
        """
        Load and cache a locale JSON file.
        
        Args:
            language: Language code (e.g., 'fr', 'en')
            
        Returns:
            Dictionary of locale data, or empty dict if not found
        """
        filepath = self.locales_dir / f"{language}.json"
        
        if not filepath.exists():
            logger.error(f"Locale file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                locale_data = json.load(f)
                logger.debug(f"Loaded locale file: {filepath}")
                return locale_data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return {}
    
    def get(
        self,
        key: str,
        language: str = "fr",
        default: Any = None
    ) -> Any:
        """
        Get a locale resource by key.
        
        Args:
            key: Dot-separated resource key (e.g., 'keywords.confirmation_positive')
            language: Language code ('fr' or 'en')
            default: Default value if key not found
            
        Returns:
            Resource value (string, list, dict, etc.)
            
        Example:
            loader = LocaleLoader()
            keywords = loader.get('keywords.confirmation_positive', language='fr')
            # Returns: ['oui', 'ok', 'd\'accord', 'valider', 'confirmer']
        """
        # Load locale file
        locale_data = self._load_locale_file(language)
        
        if not locale_data:
            # Try fallback to English
            if language != "en":
                logger.debug(f"Falling back to English for {key}")
                locale_data = self._load_locale_file("en")
            
            if not locale_data:
                logger.error(f"No locale data loaded for language: {language}")
                return default
        
        # Navigate through nested keys
        keys = key.split('.')
        current = locale_data
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                # Try fallback to English
                if language != "en":
                    logger.debug(f"Key {key} not found in {language}, trying English")
                    return self.get(key, language="en", default=default)
                logger.warning(f"Locale key not found: {key} in {language}")
                return default
            current = current[k]
        
        return current
    
    def get_keywords(self, category: str, language: str = "fr") -> List[str]:
        """
        Get keyword list for a category.
        
        Args:
            category: Keyword category (e.g., 'confirmation_positive')
            language: Language code
            
        Returns:
            List of keywords, or empty list if not found
        """
        keywords = self.get(f"keywords.{category}", language=language, default=[])
        if not isinstance(keywords, list):
            logger.warning(f"Keywords {category} is not a list: {type(keywords)}")
            return []
        return keywords
    
    def get_selectors(self, category: str, language: str = "fr") -> List[str]:
        """
        Get CSS/XPath selector list for a category.
        
        Args:
            category: Selector category (e.g., 'search_inputs')
            language: Language code
            
        Returns:
            List of selectors, or empty list if not found
        """
        selectors = self.get(f"selectors.{category}", language=language, default=[])
        if not isinstance(selectors, list):
            logger.warning(f"Selectors {category} is not a list: {type(selectors)}")
            return []
        return selectors
    
    def get_ui_string(self, key: str, language: str = "fr", default: str = "") -> str:
        """
        Get a UI string.
        
        Args:
            key: UI string key (e.g., 'search_field')
            language: Language code
            default: Default value if not found
            
        Returns:
            UI string
        """
        ui_string = self.get(f"ui.{key}", language=language, default=default)
        if not isinstance(ui_string, str):
            logger.warning(f"UI string {key} is not a string: {type(ui_string)}")
            return default
        return ui_string
    
    def clear_cache(self) -> None:
        """Clear the locale cache."""
        self._load_locale_file.cache_clear()
        self._cache.clear()
        logger.debug("Locale cache cleared")


# Global singleton instance for efficient reuse
_global_loader: Optional[LocaleLoader] = None


def get_locale_loader() -> LocaleLoader:
    """
    Get the global LocaleLoader instance.
    
    Returns:
        Singleton LocaleLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = LocaleLoader()
    return _global_loader


def get_locale_resource(key: str, language: str = "fr", default: Any = None) -> Any:
    """
    Convenience function to get a locale resource using the global loader.
    
    Args:
        key: Dot-separated resource key
        language: Language code ('fr' or 'en')
        default: Default value if key not found
        
    Returns:
        Resource value
    """
    return get_locale_loader().get(key, language, default)
