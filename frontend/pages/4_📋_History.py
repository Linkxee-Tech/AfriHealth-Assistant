import json
import pandas as pd
import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"History — {config.APP_NAME}", page_icon="📋", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown(f"<div class='app-title'>📋 Chat History</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

sessions = api_client.list_sessions(limit=200)

col1, col2, col3, _ = st.columns([3, 2, 2, 4])
with col1:
    search_query = st.text_input("🔍 Search", placeholder="Keywords...", label_visibility="collapsed")
with col2:
    filter_date = st.date_input("📅 Date Range", value=None, label_visibility="collapsed")
with col3:
    st.button("🔍 Filter", width="stretch")

filtered_sessions = []
for s in sessions:
    search_match = search_query.lower() in str(s.get("preview", "")).lower() or search_query.lower() in s.get("session_id", "").lower()
    
    date_match = True
    if filter_date:
        session_date_str = s.get("created_at", "")
        if session_date_str:
            try:
                session_date = pd.to_datetime(session_date_str).date()
                if session_date != filter_date:
                    date_match = False
            except:
                pass
                
    if search_match and date_match:
        filtered_sessions.append(s)

st.markdown(f"**📊 Total Conversations: {len(filtered_sessions)}**")
st.markdown("<br>", unsafe_allow_html=True)

if not filtered_sessions:
    st.info("No chat history found.")
else:
    # Pagination over the real backend/local history records.
    items_per_page = 5
    total_pages = max(1, (len(filtered_sessions) + items_per_page - 1) // items_per_page)
    
    # Store page in session state
    if "history_page" not in st.session_state:
        st.session_state.history_page = 1
        
    page = st.session_state.history_page
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    page_items = filtered_sessions[start_idx:end_idx]
    
    for s in page_items:
        sid = s["session_id"]
        date_str = s.get("created_at", "Unknown Date")
        preview = s.get("preview", "Empty conversation")
        
        st.markdown(f"""
        <div class='status-card' style='margin-bottom: 12px;'>
            <div style='color: #8892B0; font-size: 0.85rem; margin-bottom: 8px;'>📅 {date_str} &nbsp;|&nbsp; 💬 "{preview[:30]}..."</div>
            <div style='border-top: 1px solid #2A3A54; margin: 8px 0;'></div>
            <div style='margin-bottom: 12px;'>"{preview[30:80]}..."</div>
        """, unsafe_allow_html=True)
        
        c1, c2, _ = st.columns([1, 1, 6])
        with c1:
            if st.button("👁️ View", key=f"view_{sid}", width="stretch"):
                st.session_state.current_session_id = sid
                st.session_state.messages = api_client.load_session(sid)
                st.switch_page("pages/1_💬_Chat.py")
        with c2:
            if st.button("🗑️ Delete", key=f"del_{sid}", width="stretch"):
                api_client.delete_session(sid)
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    b1, b2, _ = st.columns([2, 2, 8])
    with b1:
        export_data = json.dumps(sessions, indent=2)
        st.download_button(
            label="📥 Export All History",
            data=export_data,
            file_name="afrihealth_history.json",
            mime="application/json",
            width="stretch"
        )
    with b2:
        confirm_clear = st.checkbox("Confirm clear", key="confirm_clear_history")
        if st.button("🗑️ Clear All History", width="stretch", disabled=not confirm_clear):
            result = api_client.clear_chat_history()
            if result.get("success"):
                st.success(result.get("message", "Chat history cleared."))
                st.rerun()
            else:
                st.error(result.get("message", result.get("detail", "Unable to clear history.")))
            
    st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
    cols = st.columns([4, 1, 1, 1, 1, 1, 4])
    with cols[1]:
        if st.button("◀", disabled=(page == 1)):
            st.session_state.history_page -= 1
            st.rerun()
    with cols[2]:
        st.button("1", disabled=True if page==1 else False)
    with cols[3]:
        st.button("2", disabled=True if page==2 else False)
    with cols[4]:
        st.button("3", disabled=True if page==3 else False)
    with cols[5]:
        if st.button("▶", disabled=(page == total_pages)):
            st.session_state.history_page += 1
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
