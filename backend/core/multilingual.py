"""
Multilingual Engine (Phase 2 Core)

Provides local, offline translation capabilities between English and supported
African languages (Swahili, Hausa, Yoruba) using lightweight models like MarianMT.
"""
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class MultilingualEngine:
    def __init__(self):
        self.models_loaded = False
        self.supported_languages = ["English", "Swahili", "Hausa", "Yoruba"]
        # In a real offline setup, we would load local HuggingFace translation pipelines here:
        # e.g., self.en_to_sw = pipeline("translation_en_to_sw", model="Helsinki-NLP/opus-mt-en-sw")
        
    def load_models(self):
        """Load optional local translation models when they are installed."""
        logger.warning(
            "No local translation models are bundled; multilingual translation remains unavailable."
        )
        self.models_loaded = False
        return False

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate a user's query into English for the LLM."""
        if source_lang == "English" or not self.models_loaded:
            return text
            
        if source_lang not in self.supported_languages:
            logger.warning(f"Unsupported source language: {source_lang}")
            return text
            
        logger.warning("Translation model unavailable for %s -> English", source_lang)
        return text

    def translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate the LLM's English response back to the user's language."""
        if target_lang == "English" or not self.models_loaded:
            return text
            
        if target_lang not in self.supported_languages:
            logger.warning(f"Unsupported target language: {target_lang}")
            return text
            
        logger.warning("Translation model unavailable for English -> %s", target_lang)
        return text

    def get_status(self) -> dict:
        return {
            "models_loaded": self.models_loaded,
            "supported_languages": self.supported_languages,
            "translation_available": self.models_loaded,
        }

multilingual_engine = MultilingualEngine()
