import platform

import psutil
import streamlit as st

import config
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state


@st.cache_data
def get_cpu_info():
    try:
        return platform.processor() or "Unknown"
    except Exception:
        return "Unknown"


st.set_page_config(page_title=f"Settings — {config.APP_NAME}", page_icon="⚙️", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

DEFAULTS = {
    "model_temperature": "0.7",
    "max_tokens": "512",
    "top_p": "0.9",
    "thread_count": "4",
    "context_length": "2048",
    "enable_web_search": "True",
    "enable_cloud_fallback": "True",
    "preferred_language": "English",
    "online_doctor_service": "False",
    "default_contact": "",
    "sms_number": "",
    "preferred_hospital": "Select...",
    "auto_backup": "False",
    "sync_frequency": "Weekly",
}


def _as_bool(value, fallback=False):
    return str(value).strip().lower() in {"true", "1", "yes", "on"} if value is not None else fallback


if "remote_settings" not in st.session_state:
    loaded = api_client.get_settings()
    st.session_state.remote_settings = {
        **DEFAULTS,
        **({} if loaded.get("error") else loaded),
    }
    if loaded.get("error"):
        st.warning(f"Settings could not be loaded from the backend: {loaded['error']}")

settings = st.session_state.remote_settings
online_status = api_client.get_online_status()
system_status = api_client.get_system_status()
is_online = online_status.get("status") == "online"

st.markdown(f"<div class='app-title'>⚙️ Settings & Online Features</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🤖 AI Model", "🌐 Online Features", "💾 Data & Sync", "🖥️ System & Appearance"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🤖 Local Model Settings")
        with st.container(border=True):
            st.slider("🌡️ Temperature", 0.1, 1.0, float(settings["model_temperature"]), 0.1, key="settings_temperature")
            st.slider("📏 Max Tokens", 128, 2048, int(settings["max_tokens"]), 128, key="settings_max_tokens")
            st.slider("🎯 Top-P", 0.1, 1.0, float(settings["top_p"]), 0.1, key="settings_top_p")
            st.selectbox("🧵 Thread Count", ["1", "2", "4", "8"], index=["1", "2", "4", "8"].index(str(settings["thread_count"])), key="settings_threads")
            st.selectbox("📦 Context Length", ["1024", "2048", "4096"], index=["1024", "2048", "4096"].index(str(settings["context_length"])), key="settings_context")

    with col2:
        st.markdown("### 💰 Cost Management (Cloud AI)")
        with st.container(border=True):
            usage = api_client.get_online_cost()
            if usage.get("error"):
                st.warning(f"Usage unavailable: {usage['error']}")
            else:
                st.metric("API tokens used", usage.get("tokens_used", 0))
                st.metric("Estimated cost (USD)", f"${usage.get('estimated_cost_usd', 0.0):.6f}")
                st.caption("This is an application-side estimate; provider billing is authoritative.")
            st.toggle("🚨 Alert at 80% Budget", value=False, key="settings_budget_alert")

with t2:
    if is_online:
        st.success("🌐 Hybrid mode active — network connectivity detected.")
    else:
        st.warning("🌍 Offline mode active — local data and local model services are used.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔍 Web Search & AI Enhancement")
        with st.container(border=True):
            st.toggle("🔄 Enable Web Search", value=_as_bool(settings["enable_web_search"], True), key="settings_web_search")
            st.toggle("🤖 Enable Cloud AI Fallback", value=_as_bool(settings["enable_cloud_fallback"], True), key="settings_cloud_fallback")
            st.selectbox("🌐 Preferred Language", config.LANGUAGES, index=config.LANGUAGES.index(settings["preferred_language"]) if settings["preferred_language"] in config.LANGUAGES else 0, key="settings_language")
            st.caption("Search sources are controlled by the configured hybrid provider.")

    with col2:
        st.markdown("### 📱 Telemedicine Settings")
        with st.container(border=True):
            st.toggle("🏥 Online Doctor Service", value=_as_bool(settings["online_doctor_service"]), key="settings_doctor")
            st.text_input("📧 Default Contact", value=settings["default_contact"], key="settings_contact")
            st.text_input("📱 SMS Number", value=settings["sms_number"], key="settings_sms")
            hospitals = ["Select...", "Lagos University Teaching Hospital", "Kenyatta National Hospital", "Groote Schuur Hospital"]
            st.selectbox("🏥 Preferred Hospital", hospitals, index=hospitals.index(settings["preferred_hospital"]) if settings["preferred_hospital"] in hospitals else 0, key="settings_hospital")
            st.caption("No telemedicine provider is configured; enabling this option does not create a connection.")

with t3:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Data Sync & Backup")
        with st.container(border=True):
            st.toggle("☁️ Auto Backup", value=_as_bool(settings["auto_backup"]), key="settings_auto_backup")
            st.selectbox("🔄 Sync Frequency", ["Daily", "Weekly", "Real-time"], index=["Daily", "Weekly", "Real-time"].index(settings["sync_frequency"]) if settings["sync_frequency"] in ["Daily", "Weekly", "Real-time"] else 1, key="settings_sync_frequency")
            st.caption("Cloud sync is unavailable until a provider is configured. Local backup is available below.")
            c1, c2 = st.columns(2)
            if c1.button("🔄 Sync Now", width="stretch"):
                result = api_client.sync_data()
                st.warning(result.get("message") or result.get("detail") or "Sync unavailable.")
            if c2.button("📥 Prepare Backup", width="stretch"):
                backup, name = api_client.download_backup()
                if backup:
                    st.session_state.backup_bytes = backup
                    st.session_state.backup_name = name.split("filename=")[-1].strip('"')
                    st.success("Local backup prepared.")
                else:
                    st.error(name)
            if st.session_state.get("backup_bytes"):
                st.download_button("Download Local Backup", st.session_state.backup_bytes, st.session_state.get("backup_name", "afrihealth-backup.json"), "application/json", width="stretch")

    with col2:
        st.markdown("### 💾 Data Management")
        with st.container(border=True):
            confirm = st.checkbox("I understand these actions permanently delete my records.", key="settings_confirm_delete")
            d1, d2 = st.columns(2)
            if d1.button("🗑️ Clear Chat History", width="stretch", disabled=not confirm):
                st.info(api_client.clear_chat_history().get("message", "Request completed."))
            if d1.button("🗑️ Clear Health Metrics", width="stretch", disabled=not confirm):
                st.info(api_client.clear_health_metrics().get("message", "Request completed."))
            if d2.button("📥 Export All Data", width="stretch"):
                backup, name = api_client.download_backup()
                if backup:
                    st.download_button("Download Export", backup, name.split("filename=")[-1].strip('"'), "application/json", width="stretch")
                else:
                    st.error(name)
            if d2.button("🔄 Reset All Settings", width="stretch"):
                result = api_client.reset_settings()
                if "error" not in result:
                    st.session_state.remote_settings = {**DEFAULTS, **result}
                    st.success("Settings reset to defaults. Save to apply the visible values.")
                else:
                    st.error(result["error"])

with t4:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🎨 Appearance")
        with st.container(border=True):
            themes = list(config.THEMES.keys())
            selected_theme = st.radio("🌙 Theme", options=themes, index=themes.index(st.session_state.theme), horizontal=True, key="settings_theme")
            if selected_theme != st.session_state.theme:
                st.session_state.theme = selected_theme
                st.rerun()
            st.selectbox("🌍 Language", config.LANGUAGES, index=config.LANGUAGES.index(st.session_state.language), key="settings_ui_language")
            st.color_picker("🎨 Accent Color", value=config.THEMES[st.session_state.theme]["accent_green"])

    with col2:
        st.markdown("### 🖥️ System Information")
        with st.container(border=True):
            memory = psutil.virtual_memory()
            model_name = system_status.get("model_path") or "Not configured"
            st.markdown(
                f"- **OS:** {platform.system()} {platform.release()}\n"
                f"- **CPU:** {get_cpu_info()}\n"
                f"- **RAM:** {memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB\n"
                f"- **Model:** `{model_name}`\n"
                f"- **Model loaded:** {'Yes' if system_status.get('model_loaded') else 'No'}\n"
                f"- **Knowledge-base vectors:** {system_status.get('knowledge_base_docs', 0)}\n"
                f"- **Gemini:** {'Configured' if system_status.get('gemini_configured') else 'Not configured'}"
            )
            if system_status.get("load_error"):
                st.caption(f"Model status: {system_status['load_error']}")


st.markdown("<br><hr>", unsafe_allow_html=True)
if st.button("💾 Save Settings", type="primary", width="stretch"):
    values = {
        "model_temperature": st.session_state.settings_temperature,
        "max_tokens": st.session_state.settings_max_tokens,
        "top_p": st.session_state.settings_top_p,
        "thread_count": st.session_state.settings_threads,
        "context_length": st.session_state.settings_context,
        "enable_web_search": st.session_state.settings_web_search,
        "enable_cloud_fallback": st.session_state.settings_cloud_fallback,
        "preferred_language": st.session_state.settings_language,
        "online_doctor_service": st.session_state.settings_doctor,
        "default_contact": st.session_state.settings_contact,
        "sms_number": st.session_state.settings_sms,
        "preferred_hospital": st.session_state.settings_hospital,
        "auto_backup": st.session_state.settings_auto_backup,
        "sync_frequency": st.session_state.settings_sync_frequency,
        "theme": st.session_state.settings_theme,
    }
    result = api_client.update_settings(values)
    if "error" in result:
        st.error(result["error"])
    else:
        st.session_state.remote_settings = {**DEFAULTS, **result}
        st.success("Settings saved.")
