import streamlit as st
import config
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"Admin Dashboard - {config.APP_NAME}", page_icon="📈", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown("<div class='app-title'>📈 Admin Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>System usage statistics and feedback</div><hr>", unsafe_allow_html=True)

if not config.BACKEND_CONNECTED:
    st.warning("Admin Dashboard requires the FastAPI backend to be running.")
    st.stop()

with st.spinner("Fetching statistics..."):
    # Reusing the private helper _get to fetch the stats since it's a new endpoint
    try:
        stats = api_client._get("/admin/stats")
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")
        st.stop()

if "detail" in stats:
    st.error(stats["detail"])
    st.stop()

st.subheader("Global Usage Statistics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Users", value=stats.get("users", 0))
    st.metric(label="Total Patients", value=stats.get("patients", 0))
with col2:
    st.metric(label="Total Conversations", value=stats.get("conversations", 0))
    st.metric(label="Total Messages", value=stats.get("messages", 0))
with col3:
    st.metric(label="Total Documents", value=stats.get("documents", 0))

st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("User Feedback")
fb_col1, fb_col2, fb_col3 = st.columns(3)
with fb_col1:
    st.metric(label="👍 Thumbs Up", value=stats.get("feedback", {}).get("up", 0))
with fb_col2:
    st.metric(label="👎 Thumbs Down", value=stats.get("feedback", {}).get("down", 0))
with fb_col3:
    total_feedback = stats.get("feedback", {}).get("up", 0) + stats.get("feedback", {}).get("down", 0)
    approval_rate = (stats.get("feedback", {}).get("up", 0) / total_feedback * 100) if total_feedback > 0 else 0
    st.metric(label="Approval Rate", value=f"{approval_rate:.1f}%")

st.markdown("<br><div class='disclaimer'>Statistics are updated in real-time.</div>", unsafe_allow_html=True)
