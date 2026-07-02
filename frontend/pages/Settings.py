"""
Page 5: Settings

Spec requirements:
  - Model settings: st.selectbox, st.slider (temperature, max_tokens, top_p, threads)
  - Appearance: st.radio (theme), st.color_picker (accent colour)
  - Language settings: st.selectbox
  - Data management: clear cache, export all data, reset to defaults
  - System info: st.metric, st.info
"""

import streamlit as st
import psutil
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.formatters import messages_to_report, now_datetime

st.set_page_config(
    page_title=f"Settings — {config.APP_NAME}", page_icon="⚙️", layout="wide"
)
init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown("### ⚙️ Settings")

# ------------------------------------------------------------------
# 1. Model Configuration
# ------------------------------------------------------------------
st.markdown("#### 🤖 Model Configuration")
st.caption("These parameters are forwarded to the backend once the LLM engine is connected.")

ms = st.session_state.model_settings
c1, c2 = st.columns(2)
with c1:
    ms["temperature"] = st.slider("Temperature", 0.1, 1.0, float(ms["temperature"]), 0.05,
                                   help="Higher = more creative, lower = more focused")
    ms["top_p"] = st.slider("Top-P", 0.1, 1.0, float(ms["top_p"]), 0.05,
                             help="Nucleus sampling threshold")
with c2:
    ms["max_tokens"] = st.slider("Max Tokens", 100, 2048, int(ms["max_tokens"]), 16,
                                  help="Maximum tokens in the generated response")
    ms["num_threads"] = st.slider("Thread Count", 1, 8, int(ms["num_threads"]), 1,
                                   help="CPU threads available for llama.cpp inference")
st.session_state.model_settings = ms

st.markdown("---")

# ------------------------------------------------------------------
# 2. Appearance  (theme radio + st.color_picker per spec)
# ------------------------------------------------------------------
st.markdown("#### 🎨 Appearance")

ap1, ap2, ap3 = st.columns(3)
with ap1:
    theme_choice = st.radio(
        "Theme", ["Dark", "Light"],
        index=["Dark", "Light"].index(st.session_state.theme)
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

with ap2:
    # st.color_picker — spec requirement for Appearance section
    accent_default = config.THEMES[st.session_state.theme]["accent_green"]
    custom_accent = st.color_picker(
        "Accent Colour", value=accent_default,
        help="Overrides the Medical Green accent for this session"
    )
    if custom_accent != accent_default:
        # Store override in session and re-inject CSS with the custom colour
        st.session_state["custom_accent_color"] = custom_accent

with ap3:
    if st.button("↩️ Reset Accent Colour"):
        st.session_state.pop("custom_accent_color", None)
        st.rerun()

st.markdown("---")

# ------------------------------------------------------------------
# 3. Language Settings
# ------------------------------------------------------------------
st.markdown("#### 🌍 Language")
st.session_state.language = st.selectbox(
    "Interface Language",
    config.LANGUAGES,
    index=config.LANGUAGES.index(st.session_state.language),
    help="Language used for AI responses once multilingual backend is connected"
)

st.markdown("---")

# ------------------------------------------------------------------
# 4. Data Management  (clear, export ALL data, reset)
# ------------------------------------------------------------------
st.markdown("#### 🗄️ Data Management")

d1, d2, d3, d4 = st.columns(4)

with d1:
    if st.button("🗑️ Clear Current Chat"):
        st.session_state.messages = []
        st.success("Current chat cleared.")

with d2:
    sessions = api_client.list_sessions(limit=9999)
    health_entries = api_client.get_health_entries(limit=9999)

    # Build combined export payload
    all_blocks = []
    for s in sessions:
        msgs = api_client.load_session(s["id"])
        all_blocks.append(messages_to_report(msgs, config.APP_NAME))
    chat_text = ("\n\n" + "=" * 70 + "\n\n").join(all_blocks) if all_blocks else "No chat history."

    import pandas as pd
    if health_entries:
        health_csv = pd.DataFrame(health_entries)[
            ["logged_at","metric_type","value","unit","notes"]
        ].to_csv(index=False)
    else:
        health_csv = "No health entries."

    combined_export = (
        f"AfriHealth Assistant — Full Data Export\n"
        f"Generated: {now_datetime()}\n"
        f"{'='*70}\n\n"
        f"=== CHAT HISTORY ===\n\n{chat_text}\n\n"
        f"=== HEALTH DATA (CSV) ===\n\n{health_csv}"
    )
    st.download_button(
        "⬇️ Export All Data",
        data=combined_export,
        file_name=f"afrihealth_full_export_{now_datetime().replace(' ','_').replace(':','')}.txt",
    )

with d3:
    if st.button(f"🧹 Delete All History ({len(sessions)})", disabled=len(sessions) == 0):
        for s in sessions:
            api_client.delete_session(s["id"])
        st.success("All chat history deleted.")
        st.rerun()

with d4:
    if st.button("↩️ Reset All Defaults"):
        st.session_state.model_settings = dict(config.DEFAULT_MODEL_SETTINGS)
        st.session_state.theme = config.DEFAULT_THEME
        st.session_state.language = "English"
        st.session_state.pop("custom_accent_color", None)
        st.success("Settings reset to defaults.")
        st.rerun()

st.markdown("---")

# ------------------------------------------------------------------
# 5. System Info  (st.metric + st.info per spec)
# ------------------------------------------------------------------
st.markdown("#### 🖥️ System Info")

sys_mem = psutil.virtual_memory()
cpu_count = psutil.cpu_count(logical=True)
cpu_pct   = psutil.cpu_percent(interval=0.2)
mem_used  = round(sys_mem.used / 1024**3, 1)
mem_total = round(sys_mem.total / 1024**3, 1)

status = api_client.get_system_status()

i1, i2, i3, i4, i5 = st.columns(5)
i1.metric("Model Status", "Loaded ✅" if status.get("model_loaded") else "Not Loaded ❌")
i2.metric("Model RAM", f"{status.get('memory_usage_gb', '—')} GB")
i3.metric("System RAM", f"{mem_used}/{mem_total} GB")
i4.metric("CPU", f"{cpu_pct:.0f}%")
i5.metric("Backend", "Connected ✅" if config.BACKEND_CONNECTED else "Stub mode ⚡")

st.info(
    f"**CPU cores:** {cpu_count}  |  "
    f"**RAM:** {mem_total} GB total, {mem_used} GB used  |  "
    f"**Backend URL:** {config.BACKEND_BASE_URL}  |  "
    f"**App version:** v{config.APP_VERSION}"
)
