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
        """Loads the easyOCR models into memory (offline)."""
        logger.info("Loading OCR models... (stub)")
        # In real implementation: 
        # import easyocr
        # self.reader = easyocr.Reader(['en'], gpu=False) # GPU False for low-end hardware
        self.models_loaded = True
        return True
        
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes."""
        if not self.models_loaded:
            self.load_model()
            
        logger.debug("Running OCR on image bytes...")
        
        # Stub implementation
        # Real implementation:
        # try:
        #     from PIL import Image
        #     import numpy as np
        #     img = Image.open(io.BytesIO(image_bytes))
        #     img_np = np.array(img)
        #     result = self.reader.readtext(img_np, detail=0)
        #     return " ".join(result)
        # except Exception as e:
        #     logger.error(f"OCR Failed: {e}")
        #     return ""
        
        return "[OCR Extraction: The patient's blood pressure is 120/80. Glucose levels are normal.]"

ocr_engine = OCREngine()
