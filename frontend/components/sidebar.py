"""Shared sidebar component: logo, status, language, disclaimer. Present on every page."""

import os
import streamlit as st
import config
from utils.translations import t


def _get_logo_path():
    theme = st.session_state.get("theme", config.DEFAULT_THEME)
    logo_file = "logo_light.png" if theme == "Light" else "logo.png"
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images", logo_file
    )


def _logout():
    """Clear authenticated and user-scoped state before returning to login."""
    for key in (
        "access_token",
        "username",
        "current_session_id",
        "messages",
        "response_sources",
        "selected_patient_id",
        "patient_view",
        "is_admin",
    ):
        st.session_state.pop(key, None)
    st.switch_page("app.py")


def _role_badge(is_admin: bool) -> str:
    if is_admin:
        return (
            "<div style='display:inline-flex;align-items:center;gap:6px;"
            "background:linear-gradient(135deg,#e74c3c,#c0392b);"
            "color:#fff;padding:4px 12px;border-radius:20px;font-size:0.75rem;"
            "font-weight:700;letter-spacing:0.5px;margin-top:6px;'>"
            "🛡️ ADMIN</div>"
        )
    return (
        "<div style='display:inline-flex;align-items:center;gap:6px;"
        "background:linear-gradient(135deg,#2980b9,#1a5276);"
        "color:#fff;padding:4px 12px;border-radius:20px;font-size:0.75rem;"
        "font-weight:700;letter-spacing:0.5px;margin-top:6px;'>"
        "👤 HEALTHCARE WORKER</div>"
    )


def _nav_header(label: str):
    st.markdown(
        f"<div style='font-size:0.7rem;font-weight:700;letter-spacing:1.5px;"
        f"text-transform:uppercase;color:var(--text-secondary,#888);"
        f"margin:14px 0 4px 0;'>{label}</div>",
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        # Logo + App Name
        logo_col, title_col = st.columns([1, 4])
        with logo_col:
            logo_path = _get_logo_path()
            if os.path.exists(logo_path):
                st.image(logo_path, width=40)
        with title_col:
            st.markdown(f"<div class='app-title'>{config.APP_NAME}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='app-version'>v{config.APP_VERSION} — {config.APP_TAGLINE}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Determine user role
        if "is_admin" not in st.session_state:
            from utils.api_client import get_me
            profile = get_me()
            st.session_state["is_admin"] = profile.get("is_admin", False)
            st.session_state["username"] = profile.get(
                "username", st.session_state.get("username", "")
            )

        is_admin = st.session_state.get("is_admin", False)
        username = st.session_state.get("username", "")

        # ──────────────────────────────────────────────────────────────────
        # ADMIN NAVIGATION
        # ──────────────────────────────────────────────────────────────────
        if is_admin:
            st.markdown(
                "<div style='background:linear-gradient(135deg,"
                "rgba(231,76,60,0.15),rgba(192,57,43,0.08));"
                "border:1px solid rgba(231,76,60,0.4);"
                "border-radius:10px;padding:10px 12px;margin-bottom:8px;'>"
                "<span style='font-size:0.75rem;font-weight:700;"
                "letter-spacing:1px;color:#e74c3c;'>🛡️ ADMIN PANEL</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            _nav_header("Administration")
            st.page_link("pages/12_📈_Admin.py",    label="📈 Admin Dashboard")
            st.page_link("pages/7_⚙️_Settings.py", label="⚙️ System Settings")

            _nav_header("AI Tools")
            st.page_link("pages/1_💬_Chat.py",               label="💬 Chat")
            st.page_link("pages/9_🔬_Symptom_Checker.py",    label="🔬 Symptom Checker")
            st.page_link("pages/10_🚨_Outbreak_Alerts.py",   label="🚨 Outbreak Alerts")
            st.page_link("pages/11_💊_Medications.py",       label="💊 Medications")
            st.page_link("pages/6_🩺_Clinical_Support.py",  label="🩺 Clinical Support")

            _nav_header("Patient & Metrics")
            st.page_link("pages/5_👨‍⚕️_Patients.py",    label="👨‍⚕️ Patients")
            st.page_link("pages/2_📊_Health_Metrics.py", label="📊 Health Metrics")

            _nav_header("Records")
            st.page_link("pages/3_📁_Documents.py", label="📁 Documents")
            st.page_link("pages/4_📋_History.py",   label="📋 Conversation History")

            _nav_header("Info")
            st.page_link("pages/8_📖_About.py",     label="📖 About")

        # ──────────────────────────────────────────────────────────────────
        # REGULAR USER NAVIGATION
        # ──────────────────────────────────────────────────────────────────
        else:
            _nav_header("AI Tools")
            st.page_link("pages/1_💬_Chat.py",               label="💬 Chat")
            st.page_link("pages/9_🔬_Symptom_Checker.py",    label="🔬 Symptom Checker")
            st.page_link("pages/10_🚨_Outbreak_Alerts.py",   label="🚨 Outbreak Alerts")
            st.page_link("pages/11_💊_Medications.py",       label="💊 Medications")
            st.page_link("pages/6_🩺_Clinical_Support.py",  label="🩺 Clinical Support")

            _nav_header("Patient & Metrics")
            st.page_link("pages/5_👨‍⚕️_Patients.py",    label="👨‍⚕️ Patients")
            st.page_link("pages/2_📊_Health_Metrics.py", label="📊 Health Metrics")

            _nav_header("Records")
            st.page_link("pages/3_📁_Documents.py", label="📁 Documents")
            st.page_link("pages/4_📋_History.py",   label="📋 History")

            _nav_header("App")
            st.page_link("pages/7_⚙️_Settings.py", label="⚙️ Settings")
            st.page_link("pages/8_📖_About.py",     label="📖 About")

        # Language selector
        st.markdown("---")
        st.markdown("**🌍 Language**")
        st.session_state.language = st.selectbox(
            "Language",
            config.LANGUAGES,
            index=config.LANGUAGES.index(st.session_state.language),
            label_visibility="collapsed",
            key="sidebar_language_select",
        )

        st.markdown("---")

        # Role badge + username
        st.markdown(_role_badge(is_admin), unsafe_allow_html=True)
        if username:
            st.markdown(
                f"<div style='font-size:0.8rem;color:var(--text-secondary,#888);"
                f"margin-top:2px;'>@{username}</div>",
                unsafe_allow_html=True,
            )

        # Online / RAM status
        from utils.api_client import get_online_status
        online_status = get_online_status()
        is_hybrid = online_status.get("status") == "online"

        if is_hybrid:
            st.markdown(
                "<div style='background:rgba(46,170,125,0.1);"
                "border:1px solid var(--medical-green);"
                "color:var(--medical-green);padding:6px 12px;"
                "border-radius:20px;text-align:center;"
                "font-size:0.8rem;font-weight:bold;margin-top:10px;'>"
                "🌐 Hybrid Mode Active</div>",
                unsafe_allow_html=True,
            )
        else:
            offline_text = t("offline_mode")
            st.markdown(
                f"<div style='background:rgba(192,57,43,0.1);"
                f"border:1px solid #c0392b;color:#c0392b;"
                f"padding:6px 12px;border-radius:20px;"
                f"text-align:center;font-size:0.8rem;font-weight:bold;margin-top:10px;'>"
                f"{offline_text}</div>",
                unsafe_allow_html=True,
            )

        import psutil
        sys_mem = psutil.virtual_memory()
        mem_used = round(sys_mem.used / (1024**3), 1)
        mem_total = round(sys_mem.total / (1024**3), 1)
        status_icon = "🌐" if is_hybrid else "🟢"
        status_label = "Hybrid" if is_hybrid else "Local"
        st.markdown(
            f"<div style='font-size:0.85rem;margin:8px 0;'>"
            f"{status_icon} {status_label} &nbsp;|&nbsp; 💾 RAM: {mem_used}G / {mem_total}G</div>",
            unsafe_allow_html=True,
        )

        # Logout
        st.markdown("---")
        if st.button("🚪 Log out", key="sidebar_logout", use_container_width=True):
            _logout()

        # Disclaimer
        st.markdown("---")
        st.markdown(
            "<div class='disclaimer'>AfriHealth Assistant provides general health "
            "information only and does not replace professional medical advice. "
            "In an emergency, contact your nearest clinic or hospital.</div>",
            unsafe_allow_html=True,
        )
