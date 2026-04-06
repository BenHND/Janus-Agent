"""
OCR Factory - Platform-specific engine selection

This module provides a factory function that automatically selects and returns
the best OCR engine for the current platform:
- macOS: Apple Vision framework
- Windows: Windows.Media.Ocr
- Linux: RapidOCR with ONNX runtime

The factory ensures optimal performance and minimal memory overhead by loading
only the engine needed for the current platform.
"""

import logging
import sys

from .interface import OCREngine

logger = logging.getLogger(__name__)


def get_ocr_engine() -> OCREngine:
    """
    Get the optimal OCR engine for the current platform
    
    This factory function automatically detects the platform and returns
    the most appropriate OCR engine:
    - macOS (darwin): MacOSEngine using Vision.framework
    - Windows (win32): WindowsEngine using Windows.Media.Ocr
    - Linux: LinuxEngine using RapidOCR with ONNX
    
    Returns:
        OCREngine instance optimized for the current platform
    
    Raises:
        RuntimeError: If no suitable OCR engine is available
    """
    platform = sys.platform
    
    if platform == 'darwin':
        # macOS - Use Apple Vision framework
        try:
            from .macos_engine import MacOSEngine
            engine = MacOSEngine()
            
            if engine.is_available():
                logger.info("🍎 Using macOS Vision framework for OCR (Neural Engine)")
                return engine
            else:
                logger.warning("macOS Vision framework not available, trying fallback")
        except Exception as e:
            logger.warning(f"Failed to load macOS Vision OCR: {e}")
    
    elif platform == 'win32':
        # Windows - Use Windows.Media.Ocr
        try:
            from .windows_engine import WindowsEngine
            engine = WindowsEngine()
            
            if engine.is_available():
                logger.info("🪟 Using Windows native OCR (DirectX acceleration)")
                return engine
            else:
                logger.warning("Windows OCR not available, trying fallback")
        except Exception as e:
            logger.warning(f"Failed to load Windows OCR: {e}")
    
    else:
        # Linux or other Unix-like systems - Use RapidOCR
        try:
            from .linux_engine import LinuxEngine
            engine = LinuxEngine()
            
            if engine.is_available():
                logger.info("🐧 Using RapidOCR with ONNX runtime for Linux")
                return engine
            else:
                logger.warning("RapidOCR not available, trying fallback")
        except Exception as e:
            logger.warning(f"Failed to load RapidOCR: {e}")
    
    # If we get here, no native engine is available - fail fast
    logger.error("❌ CRITICAL: No Native OCR Engine available for this platform.")
    raise RuntimeError(
        "Native OCR initialization failed. Check platform dependencies:\n"
        "  macOS: pip install pyobjc-core==10.1 pyobjc-framework-Cocoa==10.1 "
        "pyobjc-framework-Quartz==10.1 pyobjc-framework-Vision==10.1\n"
        "  Windows: pip install winsdk\n"
        "  Linux: pip install rapidocr_onnxruntime"
    )
