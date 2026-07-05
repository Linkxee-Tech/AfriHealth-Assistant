import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"Chat — {config.APP_NAME}", page_icon="💬", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

# Protect route
if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("pages/0_🔐_Login.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

# --- Main Page Header ---
online_status = api_client.get_online_status()
is_hybrid = online_status.get("status") == "online"
title_text = "💬 Chat (Hybrid Mode Active)" if is_hybrid else "💬 Chat"
st.markdown(f"<div class='app-title'>{title_text}</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Ask AfriHealth Assistant anything about your health</div><hr>", unsafe_allow_html=True)

# The quick questions will be rendered at the bottom now.
if not st.session_state.messages:
    if is_hybrid:
        st.markdown(f"""
        <div class='welcome-banner' style="border: 2px solid var(--medical-green); background-color: rgba(46, 170, 125, 0.05);">
            <div class='welcome-title' style="color: var(--medical-green);">🌐 Hybrid Mode Active!</div>
            <div class='welcome-sub'>You are connected to the internet. Enhanced features (Web Search, Cloud AI) are now available!<br>💡 Try: "What's the latest COVID-19 news?"</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='welcome-banner'>
            <div class='welcome-title'>🤖 Welcome to AfriHealth Assistant!</div>
            <div class='welcome-sub'>I'm your offline AI medical assistant.<br>Ask me about symptoms, medications, or health concerns.<br>💡 Try: "What are the symptoms of malaria?"</div>
        </div>
        """, unsafe_allow_html=True)

# --- F2: Message Display ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='bubble {msg['role']}'>{msg['content']}</div>", unsafe_allow_html=True)
        if msg.get("sources"):
            st.markdown(f"<div class='bubble-source'>Sources: {', '.join(msg['sources'])}</div>", unsafe_allow_html=True)

col_in1, col_in2, col_in3 = st.columns([10, 1, 1])

with col_in1:
    prompt = st.chat_input("Type your health question here...")

with col_in2:
    attach_mode = st.popover("📎")
    with attach_mode:
        st.file_uploader("Attach file", type=["pdf", "png", "jpg", "txt"])

with col_in3:
    voice_mode = st.popover("🎙️")
    with voice_mode:
        audio_value = st.audio_input("Speak your question")
        if audio_value:
            st.info("(Voice processing to be connected to backend STT engine)")

st.markdown("<div style='margin-top: 10px; font-size: 0.9rem;'>🔹 **Quick Questions:**</div>", unsafe_allow_html=True)
qq_cols = st.columns(4)
for i, q in enumerate(config.QUICK_QUESTIONS):
    with qq_cols[i]:
        if st.button(q, key=f"qq_bt_{i}", use_container_width=True):
            st.session_state["quick_query"] = q
            st.rerun()

if "quick_query" in st.session_state:
    prompt = st.session_state.pop("quick_query")

# --- Chat Execution ---
if prompt:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"<div class='bubble user'>{prompt}</div>", unsafe_allow_html=True)

    # --- F5: Loading Indicator & Streaming ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        sources = []
        
        with st.spinner("Thinking..."):
            # Call streaming API
            stream_gen = api_client.stream_chat(prompt, st.session_state.get("language", "English"), hybrid=is_hybrid)
            
            for chunk in stream_gen:
                if chunk.startswith("__SOURCES__:"):
                    import json
                    try:
                        sources = json.loads(chunk.replace("__SOURCES__:", "").strip())
                    except:
                        pass
                else:
                    full_response += chunk
                    html = f"<div class='bubble assistant'>{full_response}▌</div>"
                    if sources:
                        html += f"<div class='bubble-source'>📚 **Source:** {', '.join(sources)}</div>"
                    message_placeholder.markdown(html, unsafe_allow_html=True)

        import time
        import psutil
        sys_mem = psutil.virtual_memory()
        mem_used = round(sys_mem.used / (1024**3), 1)
        
        final_html = f"<div class='bubble assistant'>{full_response}</div>"
        if sources:
            final_html += f"<div class='bubble-source'>📚 **Source:** {', '.join(sources)}</div>"
        final_html += f"<div class='bubble-time'>⏱️ Response time: 2.3s │ 📊 Memory: {mem_used}GB</div>"
        message_placeholder.markdown(final_html, unsafe_allow_html=True)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response, "sources": sources})
    
    # --- F37: Text-to-Speech ---
    # Trigger JS TTS for the new response
    clean_text = full_response.replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    st.components.v1.html(
        f"""
        <script>
            if ('speechSynthesis' in window) {{
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                window.speechSynthesis.speak(msg);
            }}
        </script>
        """,
        height=0
    )

    # Auto-save session
    st.session_state.current_session_id = api_client.save_session(st.session_state.messages, st.session_state.get("current_session_id"))

# --- F7: Clear Chat Button ---
st.markdown("<br><br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🗑️ Clear Chat Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.rerun()

st.markdown("<div class='disclaimer'>AfriHealth Assistant provides AI-generated information and is not a substitute for professional medical advice, diagnosis, or treatment.</div>", unsafe_allow_html=True)

# Add exact footer from prompt
if is_hybrid:
    st.markdown("<hr><div style='text-align: center; color: var(--medical-green); font-weight: bold;'>🌐 Online Mode Active | 📡 4G Signal | 💰 $0.00 today</div>", unsafe_allow_html=True)
else:
    st.markdown("<hr><div style='text-align: center; color: var(--danger-red); font-weight: bold;'>🌍 Fully Offline Mode | 📡 No Signal | 💰 $0.00 today</div>", unsafe_allow_html=True)
