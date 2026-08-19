from backend.services import chat_service


def test_detect_pidgin_phrase():
    phrase = "How you dey? Wetin dey happen for you?"
    detected = chat_service._detect_language(phrase, fallback="English")
    assert detected == "Pidgin"
