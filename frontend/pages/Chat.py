"""Page 1: Chat - main interaction page."""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from components.chat_interface import render_chat_interface

st.set_page_config(page_title=f"Chat — {config.APP_NAME}", page_icon="💬", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()
render_chat_interface()
