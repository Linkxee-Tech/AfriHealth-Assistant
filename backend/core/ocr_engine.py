"""
OCR Engine (Phase 2 Core)

Provides local, offline Optical Character Recognition (OCR) to extract text
from medical images (e.g., photos of prescriptions or lab results) using easyOCR.
"""
import io
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class OCREngine:
    def __init__(self):
        self.reader = None
        self.models_loaded = False
        
    def load_model(self):
        """Load easyOCR locally; never return fabricated medical text."""
        if self.models_loaded:
            return self.reader is not None
        try:
            import easyocr
            logger.info("Loading local easyOCR model...")
            self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            self.models_loaded = True
            return True
        except Exception as exc:
            logger.error("OCR model unavailable: %s", exc)
            self.models_loaded = True
            self.reader = None
            return False
        
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes."""
        if not self.models_loaded:
            self.load_model()
            
        if self.reader is None:
            return ""
        try:
            from PIL import Image
            import numpy as np
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            result = self.reader.readtext(np.asarray(image), detail=0)
            return " ".join(result).strip()
        except Exception as exc:
            logger.error("OCR extraction failed: %s", exc)
            return ""

ocr_engine = OCREngine()
