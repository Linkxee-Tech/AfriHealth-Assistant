"""Page 4: Chat History."""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from components.history_viewer import render_history_viewer

st.set_page_config(page_title=f"Chat History — {config.APP_NAME}", page_icon="📋", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown("### 📋 Chat History")
render_history_viewer()
