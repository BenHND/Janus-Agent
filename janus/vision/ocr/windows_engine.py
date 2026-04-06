"""
Windows OCR Engine - Windows.Media.Ocr

Uses Windows 10/11 native OCR capabilities via Windows Runtime (WinRT) APIs.

Performance:
- RAM Overhead: ~15-30 MB (native Windows API)
- Latency: 100-200ms
- Uses DirectX acceleration (no NVIDIA GPU required)

Requirements:
- Windows 10 or later
- winsdk package (Python bindings for WinRT)
"""

import asyncio
import io
import logging
import platform
from typing import List, Union

from PIL import Image

from .interface import OCREngine, OCRResult

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CONFIDENCE = 90.0  # Windows OCR doesn't provide per-line confidence


class WindowsEngine(OCREngine):
    """
    Native Windows OCR using Windows.Media.Ocr
    
    This engine uses the built-in Windows OCR which provides:
    - Fast DirectX-accelerated text recognition
    - Good accuracy for printed text
    - No external dependencies or model downloads
    - Minimal memory footprint
    """
    
    def __init__(self):
        """Initialize Windows OCR engine"""
        self._available = False
        self._ocr_engine = None
        self._initialized = False
        self._loop = None
        
    def initialize(self) -> None:
        """Lazy initialization of Windows OCR"""
        if self._initialized:
            return
            
        if not self.is_available():
            raise RuntimeError("Windows OCR not available on this platform")
        
        try:
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.globalization import Language
            
            # Get the default OCR engine (usually English)
            # Use asyncio to initialize the engine
            async def init_engine():
                # Try to get the first available language
                available_languages = OcrEngine.get_available_recognizer_languages()
                if available_languages and len(available_languages) > 0:
                    # Use first available language (usually English)
                    first_lang = list(available_languages)[0]
                    return OcrEngine.try_create_from_language(first_lang)
                else:
                    # Fallback to user language
                    user_lang = Language(Language.current_input_method_language_tag())
                    return OcrEngine.try_create_from_language(user_lang)
            
            # Run async initialization - use asyncio.run to avoid loop conflicts
            try:
                self._ocr_engine = asyncio.run(init_engine())
            except RuntimeError:
                # If event loop is already running, create new loop
                loop = asyncio.new_event_loop()
                self._ocr_engine = loop.run_until_complete(init_engine())
                self._loop = loop
                loop.close()
                self._loop = None  # Don't keep the loop around
            
            if not self._ocr_engine:
                raise RuntimeError("Failed to create Windows OCR engine")
            
            self._initialized = True
            logger.info("✓ Windows OCR initialized (DirectX acceleration)")
            
        except ImportError as e:
            logger.error(f"Failed to import Windows OCR: {e}")
            raise RuntimeError(
                "Windows OCR not available. Install with: pip install winsdk"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Windows OCR: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Windows OCR is available"""
        if self._available:
            return True
            
        if platform.system() != "Windows":
            logger.debug("Not on Windows, Windows OCR not available")
            return False
        
        try:
            from winsdk.windows.media.ocr import OcrEngine
            self._available = True
            return True
        except ImportError:
            logger.debug("Windows OCR not available (install winsdk)")
            return False
    
    def process_image(self, image: Union[Image.Image, str, bytes]) -> List[OCRResult]:
        """
        Process image using Windows OCR
        
        Args:
            image: PIL Image, file path, or image bytes
        
        Returns:
            List of OCRResult objects with detected text
        """
        if not self._initialized:
            self.initialize()
        
        # Convert input to PIL Image if needed
        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, bytes):
            image = Image.open(io.BytesIO(image))
        
        try:
            from winsdk.windows.graphics.imaging import (
                BitmapDecoder,
                BitmapPixelFormat,
                SoftwareBitmap,
            )
            from winsdk.windows.storage.streams import (
                DataWriter,
                InMemoryRandomAccessStream,
            )
            
            # Convert PIL Image to SoftwareBitmap
            async def convert_and_recognize():
                # Convert PIL image to bytes
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
                
                # Create InMemoryRandomAccessStream
                stream = InMemoryRandomAccessStream()
                writer = DataWriter(stream)
                writer.write_bytes(list(image_bytes))
                await writer.store_async()
                await writer.flush_async()
                stream.seek(0)
                
                # Decode to SoftwareBitmap
                decoder = await BitmapDecoder.create_async(stream)
                software_bitmap = await decoder.get_software_bitmap_async()
                
                # Run OCR
                result = await self._ocr_engine.recognize_async(software_bitmap)
                
                return result
            
            # Run async OCR
            ocr_result = self._loop.run_until_complete(convert_and_recognize())
            
            if not ocr_result or not ocr_result.lines:
                logger.debug("No text found in image")
                return []
            
            # Parse results into OCRResult objects
            results = []
            img_width, img_height = image.size
            
            for line in ocr_result.lines:
                text = line.text
                
                # Get bounding box (Windows uses normalized coordinates)
                # Note: Windows OCR doesn't provide per-word confidence,
                # so we use a default high confidence for all results
                rect = line.bounding_rect
                
                # Convert from normalized/absolute coordinates
                x = int(rect.x)
                y = int(rect.y)
                width = int(rect.width)
                height = int(rect.height)
                
                # Windows OCR doesn't provide confidence per line,
                # so we use a default high value
                confidence = DEFAULT_CONFIDENCE
                
                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=(x, y, width, height)
                ))
            
            logger.debug(f"Windows OCR found {len(results)} text lines")
            return results
            
        except Exception as e:
            logger.error(f"Error during Windows OCR processing: {e}", exc_info=True)
            return []
    
    def shutdown(self) -> None:
        """Clean up resources"""
        if self._loop:
            self._loop.close()
            self._loop = None
        self._initialized = False
        self._ocr_engine = None
        logger.debug("Windows OCR shut down")
