"""Shared sidebar component: logo, status, language, disclaimer. Present on every page."""

import os
import streamlit as st
import config
from components.status_indicator import render_status_indicator

_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images", "logo.png"
)


def render_sidebar():
    with st.sidebar:
        logo_col, title_col = st.columns([1, 4])
        with logo_col:
            if os.path.exists(_LOGO_PATH):
                st.image(_LOGO_PATH, width=40)
        with title_col:
            st.markdown(f'<div class="app-title">{config.APP_NAME}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="app-version">v{config.APP_VERSION} — {config.APP_TAGLINE}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        render_status_indicator()

        st.markdown("**Language**")
        st.session_state.language = st.selectbox(
            "Language",
            config.LANGUAGES,
            index=config.LANGUAGES.index(st.session_state.language),
            label_visibility="collapsed",
            key="sidebar_language_select",
        )

        st.markdown("---")
        st.markdown(
            '<div class="disclaimer">AfriHealth Assistant provides general health '
            "information only and does not replace professional medical advice. "
            "In an emergency, contact your nearest clinic or hospital.</div>",
            unsafe_allow_html=True,
        )
