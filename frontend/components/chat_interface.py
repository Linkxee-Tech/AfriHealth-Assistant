"""
Chat interface component.

Spec requirements (Page 1):
  - Header: st.title, st.columns, st.image
  - Sidebar: model status, memory bar, quick actions, clear/export
  - Chat container with st.chat_message
  - Multi-line input + prominent Send button
  - Quick action chips
  - Status bar (st.progress, st.metric)
  - Export button
  - Streaming responses with source citation
  - Right panel: source references
"""

import os
import time
import streamlit as st
import config
from utils import api_client
from utils.formatters import now_time, truncate, messages_to_report

def _get_page_logo_path():
    theme = st.session_state.get("theme", "Dark")
    logo_file = "logo_light.png" if theme == "Light" else "logo.png"
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "images", logo_file
    )
    if not os.path.exists(path):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "images", "logo.png"
        )
    return path


def render_chat_interface():
    # ------------------------------------------------------------------
    # SIDEBAR additions specific to the chat page
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("**Quick Questions**")
        for q in config.QUICK_QUESTIONS:
            if st.button(q, key=f"quick_{q}"):
                st.session_state.pending_query = q

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🆕 New Chat"):
                if st.session_state.messages:
                    api_client.save_session(st.session_state.messages)
                st.session_state.messages = []
                st.session_state.current_session_id = None
                st.rerun()
        with col_b:
            export_disabled = len(st.session_state.messages) == 0
            export_data = (
                messages_to_report(st.session_state.messages, config.APP_NAME)
                if not export_disabled else "No conversation yet."
            )
            st.download_button(
                "⬇️ Export",
                data=export_data,
                file_name=f"afrihealth_report_{now_time().replace(':','')}.txt",
                disabled=export_disabled,
            )

    # ------------------------------------------------------------------
    # HEADER  (st.title + st.columns + st.image per spec)
    # ------------------------------------------------------------------
    h_col1, h_col2 = st.columns([1, 8])
    with h_col1:
        logo_path = _get_page_logo_path()
        if os.path.exists(logo_path):
            st.image(logo_path, width=52)
    with h_col2:
        st.title(config.APP_NAME)

    # ------------------------------------------------------------------
    # STATUS BAR  (st.progress + st.metric per spec)
    # ------------------------------------------------------------------
    import psutil
    sys_mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    mem_pct = sys_mem.percent
    last_ms = st.session_state.get("last_response_ms")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Model", "Loaded ✅" if st.session_state.get("model_loaded") else "Not Loaded ❌")
    s2.metric("RAM", f"{mem_pct:.0f}%")
    s3.metric("CPU", f"{cpu_pct:.0f}%")
    s4.metric("Last Response", f"{last_ms:.0f} ms" if last_ms else "—")

    # ------------------------------------------------------------------
    # TOPIC HEADER / WELCOME BANNER
    # ------------------------------------------------------------------
    if not st.session_state.messages:
        st.markdown(
            """
            <div class="welcome-banner">
                <div class="welcome-title">Welcome to AfriHealth Assistant 👋</div>
                <div class="welcome-sub">
                    Ask about symptoms, medication, or common illnesses.
                    All answers run fully offline — no internet required.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        topic = truncate(st.session_state.messages[0]["content"])
        st.markdown(
            f"""
            <div class="topic-header">
                <div class="topic-header-title">💬 {topic}</div>
                <div class="topic-header-meta">
                    {len(st.session_state.messages)} messages · offline session
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # MAIN LAYOUT: chat (left) + source references right panel
    # ------------------------------------------------------------------
    main_col, ref_col = st.columns([3, 1])

    with main_col:
        # Render message history using st.chat_message
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🩺"):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("source"):
                    st.caption(f"📚 Source: {msg['source']}")
                if msg.get("time"):
                    st.caption(msg["time"])

    with ref_col:
        st.markdown("**📋 Source References**")
        sources = [m for m in st.session_state.messages
                   if m.get("role") == "assistant" and m.get("source")]
        if sources:
            for i, m in enumerate(sources[-5:], 1):   # show last 5 sources
                with st.expander(f"Ref {i}", expanded=False):
                    st.write(m.get("source", "—"))
                    st.caption(m.get("time", ""))
        else:
            st.caption("Sources will appear here after AI responses.")

    # ------------------------------------------------------------------
    # INPUT AREA
    # ------------------------------------------------------------------
    pending = st.session_state.pop("pending_query", None)

    if st.session_state.get("_clear_input_next_run"):
        st.session_state["typed_input"] = ""
        st.session_state["_clear_input_next_run"] = False

    with st.form(key="message_form", clear_on_submit=False):
        col_input, col_send = st.columns([6, 1])
        with col_input:
            st.markdown('<div class="chat-input-row">', unsafe_allow_html=True)
            typed_input = st.text_area(
                "Your question",
                placeholder="Type your health question here... (Shift+Enter for a new line)",
                label_visibility="collapsed",
                height=80,
                key="typed_input",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with col_send:
            send_clicked = st.form_submit_button("Send ➤")

    user_input = typed_input.strip() if send_clicked and typed_input and typed_input.strip() else None
    query_to_process = pending or user_input

    if query_to_process:
        if user_input:
            st.session_state["_clear_input_next_run"] = True

        st.session_state.messages.append(
            {"role": "user", "content": query_to_process, "time": now_time()}
        )

        # Stream response and time it
        stream_placeholder = st.empty()
        accumulated = ""
        t_start = time.time()
        for chunk in api_client.stream_chat(query_to_process, st.session_state.language):
            accumulated += chunk
            stream_placeholder.markdown(
                f'<div class="chat-row assistant">'
                f'<div class="bubble assistant">{accumulated}▌</div></div>',
                unsafe_allow_html=True,
            )
        elapsed_ms = (time.time() - t_start) * 1000
        st.session_state["last_response_ms"] = elapsed_ms
        stream_placeholder.empty()

        st.session_state.messages.append({
            "role": "assistant",
            "content": accumulated,
            "source": api_client.get_response_source_stub(),
            "time": now_time(),
        })
        st.rerun()
