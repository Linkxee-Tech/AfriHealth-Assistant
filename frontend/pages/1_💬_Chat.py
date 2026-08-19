import json
import time

import psutil
import streamlit as st

import config
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state


st.set_page_config(page_title=f"Chat - {config.APP_NAME}", page_icon="💬", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()
online_status = api_client.get_online_status()
is_hybrid = online_status.get("status") == "online"
mode_label = "Hybrid/Online" if is_hybrid else "Offline"

st.markdown(f"<div class='app-title'>💬 Chat ({mode_label})</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Ask AfriHealth Assistant anything about your health</div><hr>", unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown(
        "<div class='welcome-banner'><div class='welcome-title'>Welcome to AfriHealth Assistant</div>"
        "<div class='welcome-sub'>Ask about symptoms, medication, or common illnesses. "
        "Information is not a diagnosis.</div></div>",
        unsafe_allow_html=True,
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        sources = message.get("sources") or []
        if sources:
            with st.expander("📚 View Sources", expanded=False):
                for src in sources:
                    st.markdown(f"• {src}")
        
        if message["role"] == "assistant":
            fb_col1, fb_col2, _ = st.columns([1, 1, 15])
            current_fb = message.get("feedback", 0)
            with fb_col1:
                if st.button("👍", key=f"fb_up_{i}", help="Good response", type="primary" if current_fb == 1 else "secondary"):
                    if current_fb != 1:
                        st.session_state.messages[i]["feedback"] = 1
                        st.session_state.current_session_id = api_client.save_session(
                            st.session_state.messages, st.session_state.get("current_session_id")
                        )
                        st.rerun()
            with fb_col2:
                if st.button("👎", key=f"fb_down_{i}", help="Poor response", type="primary" if current_fb == -1 else "secondary"):
                    if current_fb != -1:
                        st.session_state.messages[i]["feedback"] = -1
                        st.session_state.current_session_id = api_client.save_session(
                            st.session_state.messages, st.session_state.get("current_session_id")
                        )
                        st.rerun()

col_mode, col_lang, col_detail = st.columns([2, 2, 2])
with col_mode:
    clinical_mode = st.selectbox(
        "⚕️ Mode", ["Auto (Standard Chat)"] + config.CLINICAL_MODES,
        index=0,
        key="chat_clinical_mode",
        label_visibility="collapsed",
        help="Select a clinical mode for focused decision support"
    )
    # Convert 'Auto' back to None for the backend
    active_mode = None if clinical_mode.startswith("Auto") else clinical_mode
    
with col_lang:
    selected_language = st.selectbox(
        "🌍 Language", config.LANGUAGES,
        index=config.LANGUAGES.index(st.session_state.get("language", "English")) if st.session_state.get("language", "English") in config.LANGUAGES else 0,
        key="chat_language_select",
        label_visibility="collapsed"
    )
    st.session_state["language"] = selected_language
with col_detail:
    detail_level = st.selectbox(
        "📏 Detail", ["Brief", "Standard", "Detailed"],
        index=1,
        key="chat_detail_level",
        label_visibility="collapsed"
    )

col_input, col_attach, col_voice = st.columns([10, 1, 1])
with col_input:
    prompt = st.chat_input("Type your health question here...")
with col_attach:
    with st.popover("📎"):
        attached_file = st.file_uploader(
            "Attach file",
            type=["pdf", "docx", "txt", "png", "jpg"],
            key="chat_attachment",
        )
        if attached_file:
            st.caption(f"Ready: {attached_file.name}")
            if st.button("Send file", key="send_chat_attachment", width="stretch"):
                with st.spinner("Uploading and reading the file..."):
                    upload_result = api_client.upload_document(
                        attached_file.getvalue(), attached_file.name
                    )
                    if upload_result.get("status") == "processing":
                        document_result = api_client.analyze_document(attached_file.name)
                    else:
                        document_result = upload_result
                document_text = (
                    document_result.get("analysis")
                    or document_result.get("extracted_text_preview")
                    or document_result.get("detail")
                    or document_result.get("message")
                )
                if document_text and document_result.get("status") not in {"error", "unavailable"}:
                    st.session_state["quick_query"] = (
                        "Explain this medical document in simple language for a patient. "
                        "Separate what it says, what the person should do, warning signs, "
                        "and what must be confirmed by a healthcare professional.\n\n"
                        f"Document content:\n{document_text}"
                    )
                    st.rerun()
                else:
                    st.error(document_result.get("detail") or document_result.get("message", "File could not be sent."))
with col_voice:
    with st.popover("🎙️"):
        audio_value = st.audio_input("Speak your question")
        if audio_value:
            st.caption("Audio captured. Press Send voice to transcribe it.")
            if st.button("Send voice", key="send_voice_question", width="stretch"):
                with st.spinner("Transcribing your question..."):
                    transcription = api_client.transcribe_audio(
                        audio_value.getvalue(), audio_value.type or "audio/wav"
                    )
                if transcription.get("text"):
                    st.session_state["quick_query"] = transcription["text"]
                    st.rerun()
                else:
                    st.error(
                        transcription.get("detail")
                        or transcription.get("error")
                        or "Voice transcription is unavailable. You can type the question instead."
                    )

st.markdown("Quick Questions:")
quick_columns = st.columns(len(config.QUICK_QUESTIONS))
for index, question in enumerate(config.QUICK_QUESTIONS):
    with quick_columns[index]:
        if st.button(question, key=f"quick_question_{index}", width="stretch"):
            st.session_state["quick_query"] = question
            st.rerun()
if "quick_query" in st.session_state:
    prompt = st.session_state.pop("quick_query")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = ""
        sources = []
        started = time.perf_counter()
        with st.spinner("Thinking..."):
            for chunk in api_client.stream_chat(prompt, st.session_state.get("language", "English"), clinical_mode=active_mode, hybrid=is_hybrid, detail_level=detail_level):
                if chunk.startswith("__SOURCES__:"):
                    try:
                        sources = json.loads(chunk.split(":", 1)[1].strip())
                    except (TypeError, ValueError):
                        sources = []
                    continue
                response += chunk
                placeholder.markdown(response + " ▌")
        elapsed = time.perf_counter() - started
        placeholder.markdown(response)
        if sources:
            with st.expander("📚 View Sources", expanded=False):
                for src in sources:
                    st.markdown(f"• {src}")
        memory_gb = psutil.virtual_memory().used / (1024 ** 3)
        st.caption(f"Response time: {elapsed:.2f}s | System memory: {memory_gb:.1f} GB")

    st.session_state.messages.append({"role": "assistant", "content": response, "sources": sources})
    st.session_state.current_session_id = api_client.save_session(
        st.session_state.messages, st.session_state.get("current_session_id")
    )
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🗑️ Clear Chat Session", width="stretch"):
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.rerun()

st.markdown(
    "<div class='disclaimer'>AfriHealth Assistant provides general health information only "
    "and does not replace professional medical advice.</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<hr><div style='text-align:center;font-weight:bold;'>Processing mode: {mode_label} | "
    f"Cloud fallback: {'configured' if st.session_state.get('gemini_configured') else 'unavailable'}</div>",
    unsafe_allow_html=True,
)
