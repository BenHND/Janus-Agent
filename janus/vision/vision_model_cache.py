"""
Vision Model Cache - TICKET 203 (B2)

Global singleton cache for BLIP-2 and CLIP models to prevent reloading.

This ensures:
1. Models are loaded only once per application lifetime
2. No duplicate model instances across different components
3. Significant performance improvement for repeated vision operations
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VisionModelCache:
    """
    Singleton cache for vision AI models (BLIP-2, CLIP).
    
    Prevents multiple loads of heavy models by caching them globally.
    """
    
    _instance: Optional['VisionModelCache'] = None
    
    def __init__(self):
        """Initialize empty cache."""
        self._blip2_model = None
        self._blip2_processor = None
        self._clip_model = None
        self._clip_processor = None
        self._device = None
        self._loaded = False
        logger.debug("VisionModelCache initialized")
    
    @classmethod
    def get_instance(cls) -> 'VisionModelCache':
        """
        Get or create the global singleton instance.
        
        Returns:
            VisionModelCache singleton instance
        """
        if cls._instance is None:
            cls._instance = VisionModelCache()
            logger.info("✓ Created global VisionModelCache singleton")
        return cls._instance
    
    def set_blip2(self, model: Any, processor: Any, device: str) -> None:
        """
        Cache BLIP-2 model and processor.
        
        Args:
            model: BLIP-2 model instance
            processor: BLIP-2 processor instance
            device: Device model is loaded on ('cpu', 'cuda', 'mps')
        """
        self._blip2_model = model
        self._blip2_processor = processor
        self._device = device
        logger.info(f"✓ BLIP-2 cached (device={device})")
    
    def get_blip2(self) -> tuple[Optional[Any], Optional[Any], Optional[str]]:
        """
        Get cached BLIP-2 model and processor.
        
        Returns:
            Tuple of (model, processor, device) or (None, None, None) if not cached
        """
        return self._blip2_model, self._blip2_processor, self._device
    
    def has_blip2(self) -> bool:
        """Check if BLIP-2 is cached."""
        return self._blip2_model is not None
    
    def set_clip(self, model: Any, processor: Any, device: str) -> None:
        """
        Cache CLIP model and processor.
        
        Args:
            model: CLIP model instance
            processor: CLIP processor instance
            device: Device model is loaded on ('cpu', 'cuda', 'mps')
        """
        self._clip_model = model
        self._clip_processor = processor
        self._device = device
        logger.info(f"✓ CLIP cached (device={device})")
    
    def get_clip(self) -> tuple[Optional[Any], Optional[Any], Optional[str]]:
        """
        Get cached CLIP model and processor.
        
        Returns:
            Tuple of (model, processor, device) or (None, None, None) if not cached
        """
        return self._clip_model, self._clip_processor, self._device
    
    def has_clip(self) -> bool:
        """Check if CLIP is cached."""
        return self._clip_model is not None
    
    def is_loaded(self) -> bool:
        """Check if any models are loaded."""
        return self._blip2_model is not None or self._clip_model is not None
    
    def clear(self) -> None:
        """
        Clear all cached models.
        
        Note: This does not deallocate GPU memory automatically.
        Models will be garbage collected when no longer referenced.
        """
        self._blip2_model = None
        self._blip2_processor = None
        self._clip_model = None
        self._clip_processor = None
        self._device = None
        self._loaded = False
        logger.info("VisionModelCache cleared")
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache status
        """
        return {
            "blip2_cached": self.has_blip2(),
            "clip_cached": self.has_clip(),
            "device": self._device,
            "any_loaded": self.is_loaded(),
        }


# Global singleton accessor
def get_vision_cache() -> VisionModelCache:
    """
    Get the global vision model cache singleton.
    
    Returns:
        VisionModelCache instance
    """
    return VisionModelCache.get_instance()


# Reset function for testing
def reset_vision_cache() -> None:
    """Reset the global vision cache (for testing)."""
    cache = get_vision_cache()
    cache.clear()
    VisionModelCache._instance = None
    logger.debug("Global vision cache reset")
