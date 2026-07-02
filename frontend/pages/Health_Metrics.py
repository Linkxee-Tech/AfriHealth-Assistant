"""Page 2: Health Metrics dashboard."""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from components.metrics_display import render_metrics_dashboard

st.set_page_config(page_title=f"Health Metrics — {config.APP_NAME}", page_icon="📊", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown("### 📊 Health Metrics")
render_metrics_dashboard()
