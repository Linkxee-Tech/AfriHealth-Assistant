import streamlit as st

# A simple translation dictionary to fulfill F40 (Multilingual UI)
# In a real production app, this would be loaded from JSON/YAML files.

TRANSLATIONS = {
    "English": {
        "welcome": "Welcome",
        "chat": "Chat",
        "health_metrics": "Health Metrics",
        "documents": "Documents",
        "history": "History",
        "settings": "Settings",
        "about": "About",
        "language": "Language",
        "offline_mode": "🔌 OFFLINE MODE / LOCAL FALLBACK"
    },
    "Swahili": {
        "welcome": "Karibu",
        "chat": "Ongea",
        "health_metrics": "Vipimo vya Afya",
        "documents": "Nyaraka",
        "history": "Historia",
        "settings": "Mipangilio",
        "about": "Kuhusu",
        "language": "Lugha",
        "offline_mode": "🔌 HALI YA NJE YA MTANDAO"
    },
    "Hausa": {
        "welcome": "Sannu",
        "chat": "Tattaunawa",
        "health_metrics": "Ma'aunin Lafiya",
        "documents": "Takardu",
        "history": "Tarihi",
        "settings": "Saituna",
        "about": "Game da",
        "language": "Harshe",
        "offline_mode": "🔌 YANAYIN RASHIN YANAR GIZO"
    },
    "Yoruba": {
        "welcome": "Kaabo",
        "chat": "Iwire",
        "health_metrics": "Awọn wiwọn Ilera",
        "documents": "Awọn iwe aṣẹ",
        "history": "Itan",
        "settings": "Eto",
        "about": "Nipa",
        "language": "Ede",
        "offline_mode": "🔌 IPIN OFFLINE"
    }
}

def t(key: str) -> str:
    """Translate a key based on the current session state language."""
    # Ensure language exists in session state; default to English
    lang = st.session_state.get("language", "English")
    
    # Fallback to English if language not found
    if lang not in TRANSLATIONS:
        lang = "English"
        
    return TRANSLATIONS[lang].get(key, TRANSLATIONS["English"].get(key, key))
