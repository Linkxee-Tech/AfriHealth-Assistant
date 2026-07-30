"""Gemini/cloud-fallback status widget; never reports an unverified connection."""

import streamlit as st


def render_gemini_status(status: dict | None = None):
    status = status or {}
    configured = bool(status.get("gemini_configured"))
    if configured:
        st.success("Cloud AI fallback configured")
    else:
        st.warning("Cloud AI fallback unavailable; local/offline services remain available")
