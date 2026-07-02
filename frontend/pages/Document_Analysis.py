"""Page 3: Document Analysis."""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from components.document_uploader import render_document_uploader

st.set_page_config(page_title=f"Document Analysis — {config.APP_NAME}", page_icon="📁", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown("### 📁 Document Analysis")
render_document_uploader()
