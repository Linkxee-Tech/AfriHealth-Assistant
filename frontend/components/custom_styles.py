"""Custom CSS styles for AfriHealth Assistant, theme-aware (Dark/Light).

Loads the base stylesheet from assets/css/style.css and substitutes the
__TOKEN__ placeholders with the active theme's colours, per the project's
asset-layout spec.
"""

import os
import streamlit as st

_CSS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "css", "style.css"
)


def _load_css_template() -> str:
    with open(_CSS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def inject_custom_css(colors: dict):
    template = _load_css_template()
    css_body = (
        template
        .replace("__BG__", colors["primary_bg"])
        .replace("__CARD__", colors["card_bg"])
        .replace("__GREEN__", colors["accent_green"])
        .replace("__GREY__", colors["secondary_grey"])
        .replace("__TEXT__", colors["text"])
        .replace("__BORDER__", colors["border"])
    )
    st.markdown(f"<style>{css_body}</style>", unsafe_allow_html=True)
