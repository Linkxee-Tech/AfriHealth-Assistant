"""
Centralized session_state initialization.
Every page calls init_session_state() first.
"""

import streamlit as st
import config
import db


def init_session_state():
    db.init_db()  # idempotent - safe to call on every page load
    defaults = {
        "messages": [],
        "model_loaded": False,
        "memory_usage_gb": 0.0,
        "processing_mode": "OFFLINE",
        "gemini_configured": False,
        "language": "English",
        "theme": config.DEFAULT_THEME,
        "current_session_id": None,
        "model_settings": dict(config.DEFAULT_MODEL_SETTINGS),
        "last_response_ms": None,
        "custom_accent_color": None,   # set by color_picker in Settings
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_theme_colors() -> dict:
    """Return active theme colors, applying custom accent override if set."""
    colors = dict(config.THEMES[st.session_state.get("theme", config.DEFAULT_THEME)])
    custom = st.session_state.get("custom_accent_color")
    if custom:
        colors["accent_green"] = custom
    return colors
