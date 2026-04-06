"""
OCR Module - Platform-native OCR engines

This module provides a factory-based OCR system that selects the most appropriate
OCR engine based on the host platform:
- macOS: Apple Vision framework (fast, GPU-accelerated)
- Windows: Windows.Media.Ocr (native, DirectX-accelerated)
- Linux: RapidOCR with ONNX runtime (lightweight, CPU-optimized)

The factory pattern ensures minimal memory overhead and optimal performance
for each platform.
"""

from .factory import get_ocr_engine
from .interface import OCREngine, OCRResult

__all__ = ["get_ocr_engine", "OCREngine", "OCRResult"]
