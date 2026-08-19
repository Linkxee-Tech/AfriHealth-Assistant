from backend.core.multilingual import multilingual_engine


def test_translate_fallback_no_models():
    # Ensure that when no translation models are loaded, translations are no-ops
    multilingual_engine.models_loaded = False
    text = "This is a test answer."
    assert multilingual_engine.translate_from_english(text, "Pidgin") == text
    assert multilingual_engine.translate_to_english(text, "Pidgin") == text
