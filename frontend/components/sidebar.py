"""Shared sidebar component: logo, status, language, disclaimer. Present on every page."""

import os
import streamlit as st
import config
from components.status_indicator import render_status_indicator
from utils.translations import t

def _get_logo_path():
    theme = st.session_state.get("theme", config.DEFAULT_THEME)
    logo_file = "logo_light.png" if theme == "Light" else "logo.png"
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images", logo_file
    )


def render_sidebar():
    with st.sidebar:
        logo_col, title_col = st.columns([1, 4])
        with logo_col:
            logo_path = _get_logo_path()
            if os.path.exists(logo_path):
                st.image(logo_path, width=40)
        with title_col:
            st.markdown(f'<div class="app-title">{config.APP_NAME}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="app-version">v{config.APP_VERSION} — {config.APP_TAGLINE}</div>',
            unsafe_allow_html=True,
        )
        
        # F39 / Hybrid Mode Status Indicator
        from utils.api_client import get_online_status
        online_status = get_online_status()
        is_hybrid = online_status.get("status") == "online"
        
        if is_hybrid:
            st.markdown(
                f'<div style="background-color: rgba(46, 170, 125, 0.1); border: 1px solid var(--medical-green); color: var(--medical-green); padding: 6px 12px; border-radius: 20px; text-align: center; font-size: 0.8rem; font-weight: bold; margin-top: 10px;">🌐 Hybrid Mode Active</div>',
                unsafe_allow_html=True,
            )
        else:
             offline_text = t("offline_mode")
             st.markdown(
                f'<div style="background-color: rgba(192, 57, 43, 0.1); border: 1px solid #c0392b; color: #c0392b; padding: 6px 12px; border-radius: 20px; text-align: center; font-size: 0.8rem; font-weight: bold; margin-top: 10px;">{offline_text}</div>',
                unsafe_allow_html=True,
            )
             
        st.markdown("---")

        import psutil
        sys_mem = psutil.virtual_memory()
        mem_used = round(sys_mem.used / (1024**3), 1)
        mem_total = round(sys_mem.total / (1024**3), 1)
        
        if is_hybrid:
            status_html = f'<span style="color:var(--medical-green)">🌐</span> Signal: Strong ⚡ 4G &nbsp;│&nbsp; '
        else:
            status_html = f'<span style="color:#c0392b">🟢</span> Local &nbsp;│&nbsp; '
            
        st.markdown(
            f'<div style="font-size:0.9rem; margin-top:10px; margin-bottom:10px;">'
            f'{status_html}'
            f'💾 RAM: {mem_used}G / {mem_total}G'
            f'</div>',
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
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
