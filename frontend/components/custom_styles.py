"""Custom CSS styles for AfriHealth Assistant, theme-aware (Dark/Light).

Loads the base stylesheet from assets/css/style.css and substitutes the
__TOKEN__ placeholders with the active theme's colours, per the project's
asset-layout spec.
"""

import os
import base64
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
        .replace("__GOLD__", colors["accent_gold"])
        .replace("__GREY__", colors["secondary_grey"])
        .replace("__TEXT__", colors["text"])
        .replace("__BORDER__", colors["border"])
    )

    css_body = f"""
        :root {{
            --bg: {colors['primary_bg']};
            --card: {colors['card_bg']};
            --green: {colors['accent_green']};
            --gold: {colors['accent_gold']};
            --grey: {colors['secondary_grey']};
            --text: {colors['text']};
            --border: {colors['border']};
        }}
    """ + css_body
    
    # Inject background image for the dashboard/app based on theme
    theme = st.session_state.get("theme", "Dark")
    bg_file = "background_light.png" if theme == "Light" else "background.png"
    bg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images", bg_file
    )
    if not os.path.exists(bg_path):
        bg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images", "background.png"
        )

    if os.path.exists(bg_path):
        with open(bg_path, 'rb') as f:
            bg_base64 = base64.b64encode(f.read()).decode()

        # Convert hex to rgba for the overlay
        hex_bg = colors['primary_bg'].lstrip('#')
        if len(hex_bg) == 6:
            r, g, b = tuple(int(hex_bg[i:i+2], 16) for i in (0, 2, 4))
            rgba_bg = f"rgba({r}, {g}, {b}, 0.85)"
        else:
            rgba_bg = "rgba(10, 25, 47, 0.85)" # fallback

        bg_css = f"""
        .stApp, section[data-testid="stSidebar"] {{
            background-image: linear-gradient({rgba_bg}, {rgba_bg}), url("data:image/png;base64,{bg_base64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: transparent !important;
            box-shadow: none !important;
        }}
        
        /* Force Streamlit base text to match theme */
        .stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp div {{
            color: var(--text);
        }}
        
        /* Explicitly style Streamlit containers to use card_bg */
        div[data-testid="stExpander"] {{
            background-color: var(--card) !important;
            border-color: var(--border) !important;
        }}
        div[data-testid="stMetricValue"] {{
            color: var(--text) !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: var(--grey) !important;
        }}
        """
        css_body += bg_css
        
    st.markdown(f"<style>{css_body}</style>", unsafe_allow_html=True)
