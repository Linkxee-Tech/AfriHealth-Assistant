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
        self.supported_languages = ["English", "Swahili", "Hausa", "Yoruba", "Igbo", "French", "Pidgin"]
        self._transformers_available = False
        self._pipelines = {
            # mapping: language -> tuple(en->lang model, lang->en model)
            "Swahili": ("Helsinki-NLP/opus-mt-en-sw", "Helsinki-NLP/opus-mt-sw-en"),
            "Hausa": ("Helsinki-NLP/opus-mt-en-ha", "Helsinki-NLP/opus-mt-ha-en"),
            "French": ("Helsinki-NLP/opus-mt-en-fr", "Helsinki-NLP/opus-mt-fr-en"),
            # Note: Yoruba/Igbo/Pidgin may not have official Helsinki models; attempts will be made
            "Yoruba": ("Helsinki-NLP/opus-mt-en-yo", "Helsinki-NLP/opus-mt-yo-en"),
            "Igbo": ("Helsinki-NLP/opus-mt-en-ig", "Helsinki-NLP/opus-mt-ig-en"),
            "Pidgin": ("Helsinki-NLP/opus-mt-en-pcm", "Helsinki-NLP/opus-mt-pcm-en"),
        }
        self.en_to_lang = {}
        self.lang_to_en = {}
        
    def load_models(self):
        """Load optional local translation models when they are installed."""
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM  # type: ignore
            self._transformers_available = True
        except Exception:
            logger.warning("transformers not available; translation disabled")
            self.models_loaded = False
            return False

        any_loaded = False
        for lang, (m_en_to_x, m_x_to_en) in self._pipelines.items():
            try:
                # Attempt to create pipelines; allow failures per language
                try:
                    p1 = pipeline("translation", model=m_en_to_x)
                    self.en_to_lang[lang] = p1
                    any_loaded = True
                    logger.info("Loaded translation model %s for English->%s", m_en_to_x, lang)
                except Exception:
                    logger.warning("No English->%s model available (%s)", lang, m_en_to_x)

                try:
                    p2 = pipeline("translation", model=m_x_to_en)
                    self.lang_to_en[lang] = p2
                    any_loaded = True
                    logger.info("Loaded translation model %s for %s->English", m_x_to_en, lang)
                except Exception:
                    logger.warning("No %s->English model available (%s)", lang, m_x_to_en)

            except Exception:
                logger.exception("Unexpected error while loading models for %s", lang)

        self.models_loaded = any_loaded
        if not any_loaded:
            logger.warning("No translation models could be loaded; translation unavailable.")
        return self.models_loaded

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate a user's query into English for the LLM."""
        if source_lang == "English":
            return text

        if not self.models_loaded:
            logger.debug("Translation models not loaded; returning original text")
            return text

        if source_lang not in self.lang_to_en:
            logger.warning(f"No translation pipeline for {source_lang} -> English")
            return text

        try:
            pipeline = self.lang_to_en[source_lang]
            out = pipeline(text)
            # pipeline returns list of dicts with 'translation_text'
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
            return str(out)
        except Exception:
            logger.exception("Translation error %s -> English", source_lang)
            return text

    def translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate the LLM's English response back to the user's language."""
        if target_lang == "English":
            return text

        if not self.models_loaded:
            logger.debug("Translation models not loaded; returning original text")
            return text

        if target_lang not in self.en_to_lang:
            logger.warning(f"No translation pipeline for English -> {target_lang}")
            return text

        try:
            pipeline = self.en_to_lang[target_lang]
            out = pipeline(text)
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
            return str(out)
        except Exception:
            logger.exception("Translation error English -> %s", target_lang)
            return text

    def get_status(self) -> dict:
        return {
            "models_loaded": self.models_loaded,
            "supported_languages": self.supported_languages,
            "translation_available": self.models_loaded,
        }

multilingual_engine = MultilingualEngine()
