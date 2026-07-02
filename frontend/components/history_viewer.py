"""
Chat history viewer component.

Spec requirements (Page 4):
  - st.expander per session
  - st.text_input search filter
  - st.selectbox filter (sort / filter by)
  - st.date_input date range filter
  - st.chat_message for viewing full conversation
  - Delete button per session
  - Export All button
"""

import streamlit as st
from datetime import datetime, date, timedelta
import config
from utils import api_client
from utils.formatters import messages_to_report


def render_history_viewer():
    st.markdown("#### Past Conversations")
    st.caption("Saved automatically when you start a New Chat.")

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------
    f1, f2, f3 = st.columns([3, 2, 2])
    with f1:
        search_term = st.text_input("🔍 Search by keyword", placeholder="e.g. malaria")
    with f2:
        sort_by = st.selectbox("Sort by", ["Newest first", "Oldest first", "Most messages"])
    with f3:
        today = date.today()
        date_range = st.date_input(
            "Date range",
            value=(today - timedelta(days=90), today),
            key="history_date_range",
        )

    sessions = api_client.list_sessions(limit=200)

    # Apply keyword filter
    if search_term.strip():
        term = search_term.strip().lower()
        sessions = [s for s in sessions if term in s["topic"].lower()]

    # Apply date filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        filtered = []
        for s in sessions:
            try:
                s_date = datetime.strptime(s["started_at"], "%Y-%m-%d %H:%M").date()
                if start_d <= s_date <= end_d:
                    filtered.append(s)
            except (ValueError, TypeError):
                filtered.append(s)
        sessions = filtered

    # Apply sort
    if sort_by == "Oldest first":
        sessions = list(reversed(sessions))
    elif sort_by == "Most messages":
        sessions = sorted(sessions, key=lambda s: s["msg_count"], reverse=True)

    if not sessions:
        st.info("No saved conversations match your filters. Start a chat and click 'New Chat' to archive it.")
        return

    # Export All
    all_msgs_blocks = []
    for s in sessions:
        msgs = api_client.load_session(s["id"])
        all_msgs_blocks.append(messages_to_report(msgs, config.APP_NAME))

    st.download_button(
        f"⬇️ Export All ({len(sessions)} conversations)",
        data=("\n\n" + "=" * 70 + "\n\n").join(all_msgs_blocks),
        file_name=f"afrihealth_all_history_{datetime.now().strftime('%Y%m%d')}.txt",
    )

    st.markdown(f"**{len(sessions)} conversation(s) found**")
    st.markdown("---")

    # ------------------------------------------------------------------
    # Session list
    # ------------------------------------------------------------------
    for s in sessions:
        label = f"💬 {s['topic']}  ·  {s['started_at']}  ·  {s['msg_count']} messages"
        with st.expander(label):
            msgs = api_client.load_session(s["id"])

            # Render each message using st.chat_message (spec requirement)
            for m in msgs:
                with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🩺"):
                    st.markdown(m["content"])
                    if m.get("source"):
                        st.caption(f"📚 Source: {m['source']}")
                    if m.get("time"):
                        st.caption(m["time"])

            st.markdown("")
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button("📂 Load into Chat", key=f"load_{s['id']}"):
                    if st.session_state.messages:
                        api_client.save_session(st.session_state.messages)
                    st.session_state.messages = msgs
                    st.session_state.current_session_id = s["id"]
                    st.success("Loaded — open the Chat page to continue.")
            with btn2:
                if st.button("🗑️ Delete", key=f"del_{s['id']}"):
                    api_client.delete_session(s["id"])
                    st.rerun()
