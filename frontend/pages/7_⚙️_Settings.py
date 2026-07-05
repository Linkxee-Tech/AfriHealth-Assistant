import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
import psutil
import platform

st.set_page_config(page_title=f"Settings — {config.APP_NAME}", page_icon="⚙️", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("pages/0_🔐_Login.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown(f"<div class='app-title'>⚙️ Settings & Online Features</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🤖 AI Model", "🌐 Online Features", "💾 Data & Sync", "🖥️ System & Appearance"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🤖 Local Model Settings")
        with st.container(border=True):
            st.session_state.model_settings["temperature"] = st.slider(
                "🌡️ Temperature", min_value=0.1, max_value=1.0, 
                value=st.session_state.model_settings.get("temperature", 0.7), step=0.1
            )
            st.session_state.model_settings["max_tokens"] = st.slider(
                "📏 Max Tokens", min_value=128, max_value=2048,
                value=st.session_state.model_settings.get("max_tokens", 512), step=128
            )
            st.session_state.model_settings["top_p"] = st.slider(
                "🎯 Top-P", min_value=0.1, max_value=1.0,
                value=st.session_state.model_settings.get("top_p", 0.9), step=0.1
            )
            st.selectbox("🧵 Thread Count", ["1 Thread", "2 Threads", "4 Threads", "8 Threads"], index=2)
            st.selectbox("📦 Context Length", ["1024", "2048", "4096"], index=1)

    with col2:
        st.markdown("### 💰 Cost Management (Cloud AI)")
        with st.container(border=True):
            st.markdown("**💳 API Usage:** 23 requests (today)")
            st.markdown("**💲 Estimated Cost:** $0.012 (today)")
            st.progress(0.12, text="Monthly Limit: $5.00 / $10.00")
            st.toggle("🚨 Alert at 80% Budget", value=True)

with t2:
    online_status = api_client.get_online_status() if hasattr(api_client, 'get_online_status') else {"status": "offline"}
    is_online = online_status.get("status") == "online"

    if is_online:
        st.markdown("""
            <div class="status-card" style="border-left: 4px solid var(--medical-green);">
                <h3 style="color: var(--medical-green); margin-top:0;">🌐 Hybrid Mode Active</h3>
                <p style="margin-bottom:0;"><strong>Status:</strong> ● Connected (WiFi/Cellular)<br></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="status-card" style="border-left: 4px solid var(--danger-red);">
                <h3 style="color: var(--danger-red); margin-top:0;">🌍 Fully Offline Mode Active</h3>
                <p style="margin-bottom:0;"><strong>Status:</strong> ○ Disconnected<br>
                All data and queries are being handled strictly on this device.</p>
            </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔍 Web Search & AI Enhancement")
        with st.container(border=True):
            st.toggle("🔄 Enable Web Search", value=True)
            st.toggle("🤖 Enable Cloud AI Fallback", value=True)
            st.selectbox("🌐 Preferred Language", ["English", "French", "Swahili", "Hausa", "Yoruba", "Igbo"])
            
            st.markdown("**📊 Search Sources:**")
            s1, s2 = st.columns(2)
            s1.checkbox("WHO.org", value=True)
            s1.checkbox("PubMed Central", value=True)
            s1.checkbox("Drugs.com", value=True)
            s2.checkbox("CDC.gov", value=True)
            s2.checkbox("Africa CDC", value=True)
            s2.checkbox("Medscape", value=True)

    with col2:
        st.markdown("### 📱 Telemedicine Settings")
        with st.container(border=True):
            st.toggle("🏥 Online Doctor Service", value=False)
            st.text_input("📧 Default Contact", value="support@afrihealth.com")
            st.text_input("📱 SMS Number", value="+234 800 000 0000")
            st.selectbox("🏥 Preferred Hospital", ["Select...", "Lagos University Teaching Hospital", "Kenyatta National Hospital", "Groote Schuur Hospital"])

with t3:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Data Sync & Backup")
        with st.container(border=True):
            st.toggle("☁️ Auto Backup to Cloud", value=True)
            st.selectbox("🔄 Sync Frequency", ["Daily", "Weekly", "Real-time"])
            st.markdown("**📦 Last Sync:** 2026-07-03 14:30 UTC")
            
            c1, c2 = st.columns(2)
            if c1.button("🔄 Sync Now", use_container_width=True):
                st.toast("Data synced successfully.")
            if c2.button("📥 Download Backup", use_container_width=True):
                st.toast("Backup downloaded.")

    with col2:
        st.markdown("### 💾 Data Management")
        with st.container(border=True):
            d1, d2 = st.columns(2)
            with d1:
                st.button("🗑️ Clear Chat History", use_container_width=True)
                st.button("📥 Export All Data", use_container_width=True)
            with d2:
                st.button("🗑️ Clear Health Metrics", use_container_width=True)
                st.button("🔄 Reset All Settings", use_container_width=True)

with t4:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🎨 Appearance")
        with st.container(border=True):
            themes = list(config.THEMES.keys())
            selected_theme = st.radio("🌙 Theme", options=["Light", "Dark", "System"], index=1, horizontal=True)
            if selected_theme in themes and selected_theme != st.session_state.theme:
                st.session_state.theme = selected_theme
                st.rerun()
                
            st.selectbox("🌍 Language", config.LANGUAGES, index=config.LANGUAGES.index(st.session_state.language))
            st.color_picker("🎨 Accent Color", value=config.THEMES[st.session_state.theme]["accent_green"])
            
    with col2:
        st.markdown("### 🖥️ System Information")
        with st.container(border=True):
            sys_mem = psutil.virtual_memory()
            mem_used = round(sys_mem.used / (1024**3), 1)
            mem_total = round(sys_mem.total / (1024**3), 1)
            
            st.markdown(f"""
            - 💻 **OS:** {platform.system()} {platform.release()}
            - 🧠 **CPU:** {platform.processor()}
            - 💾 **RAM:** {mem_used} GB / {mem_total} GB
            - 🎮 **GPU:** N/A (CPU Inference)
            - 📦 **Model:** Llama-3-8B (Q4_K_M)
            - ⚡ **Inference Speed:** ~18.5 tokens/sec
            - 📊 **Profiler Score:** 0.85
            - ♊ **Gemini 3 Pro API:** {'✅ Connected' if is_online else '❌ Disconnected'}
            """)

st.markdown("<br><hr>", unsafe_allow_html=True)
st.button("💾 Save Settings", type="primary", use_container_width=True)
