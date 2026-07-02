"""
AfriHealth Assistant - Main entry point (Streamlit multipage app).
Individual pages live in pages/. This file renders the landing screen.
"""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

import os

_FAVICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "favicon.ico")

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=_FAVICON_PATH if os.path.exists(_FAVICON_PATH) else "🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown(
    f"""
    <div class="welcome-banner">
        <div class="welcome-title">🩺 {config.APP_NAME}</div>
        <div class="welcome-sub">{config.APP_TAGLINE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("#### Get started")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/1_💬_Chat.py", label="💬 Chat", help="Ask a health question")
with c2:
    st.page_link("pages/2_📊_Health_Metrics.py", label="📊 Health Metrics", help="Log vitals & trends")
with c3:
    st.page_link("pages/3_📁_Document_Analysis.py", label="📁 Document Analysis", help="Upload a report")
with c4:
    st.page_link("pages/4_📋_Chat_History.py", label="📋 Chat History", help="Review past chats")

c5, c6 = st.columns(2)
with c5:
    st.page_link("pages/5_⚙️_Settings.py", label="⚙️ Settings", help="Model & appearance settings")
with c6:
    st.page_link("pages/6_📖_About.py", label="📖 About", help="Project & team info")

st.markdown("---")
st.markdown(
    "AfriHealth Assistant runs **100% offline** on standard laptop hardware, "
    "combining a locally quantised LLM with retrieval-augmented generation "
    "over trusted medical sources (WHO guidelines, medical handbooks)."
)
