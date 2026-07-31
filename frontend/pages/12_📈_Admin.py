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

if not st.session_state.get("is_admin"):
    st.error("🚫 Access Denied: Admins only.")
    st.page_link("pages/1_💬_Chat.py", label="← Back to Chat")
    st.stop()

render_sidebar()

st.markdown("<div class='app-title'>📈 Admin Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>System administration & user management</div><hr>", unsafe_allow_html=True)

if not config.BACKEND_CONNECTED:
    st.warning("Admin Dashboard requires the FastAPI backend to be running.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_stats, tab_users = st.tabs(["📊 Usage Statistics", "👥 User Management"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Statistics
# ─────────────────────────────────────────────────────────────────────────────
with tab_stats:
    with st.spinner("Fetching statistics..."):
        stats = api_client._get("/admin/stats")

    if "detail" in stats:
        st.error(stats["detail"])
    else:
        st.subheader("Global Usage Statistics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("👤 Total Users",         stats.get("users", 0))
        c2.metric("🧑‍⚕️ Total Patients",    stats.get("patients", 0))
        c3.metric("💬 Conversations",        stats.get("conversations", 0))
        c4.metric("📨 Messages",            stats.get("messages", 0))
        c5.metric("📄 Documents",           stats.get("documents", 0))

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("User Feedback")
        fb1, fb2, fb3 = st.columns(3)
        up   = stats.get("feedback", {}).get("up", 0)
        down = stats.get("feedback", {}).get("down", 0)
        total = up + down
        rate = (up / total * 100) if total > 0 else 0
        fb1.metric("👍 Thumbs Up",   up)
        fb2.metric("👎 Thumbs Down", down)
        fb3.metric("✅ Approval Rate", f"{rate:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — User Management
# ─────────────────────────────────────────────────────────────────────────────
with tab_users:
    st.subheader("User Management")
    st.markdown(
        "Block or unblock user accounts. Blocked users will be prevented from logging in. "
        "Deleted users are permanently removed.",
        unsafe_allow_html=False,
    )

    if st.button("🔄 Refresh User List", key="refresh_users"):
        st.rerun()

    users = api_client.admin_list_users()

    if not users:
        st.info("No users found or unable to fetch user list.")
    else:
        # ── Header row ──────────────────────────────────────────────────────
        h1, h2, h3, h4, h5, h6 = st.columns([2, 2.5, 1.2, 1.2, 1.5, 1.5])
        h1.markdown("**Username**")
        h2.markdown("**Email**")
        h3.markdown("**Role**")
        h4.markdown("**Status**")
        h5.markdown("**Action**")
        h6.markdown("**Delete**")
        st.markdown("---")

        for u in users:
            uid      = u["id"]
            uname    = u["username"]
            email    = u.get("email") or "—"
            is_admin = u.get("is_admin", False)
            is_active = u.get("is_active", True)

            col1, col2, col3, col4, col5, col6 = st.columns([2, 2.5, 1.2, 1.2, 1.5, 1.5])

            with col1:
                st.markdown(f"**{uname}**")
            with col2:
                st.markdown(f"<span style='font-size:0.85rem'>{email}</span>", unsafe_allow_html=True)
            with col3:
                badge_color = "#e74c3c" if is_admin else "#2980b9"
                badge_label = "🛡️ Admin" if is_admin else "👤 User"
                st.markdown(
                    f"<span style='background:{badge_color};color:#fff;"
                    f"padding:2px 8px;border-radius:12px;font-size:0.75rem;'>{badge_label}</span>",
                    unsafe_allow_html=True,
                )
            with col4:
                if is_active:
                    st.markdown(
                        "<span style='background:#27ae60;color:#fff;"
                        "padding:2px 8px;border-radius:12px;font-size:0.75rem;'>🟢 Active</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<span style='background:#c0392b;color:#fff;"
                        "padding:2px 8px;border-radius:12px;font-size:0.75rem;'>🔴 Blocked</span>",
                        unsafe_allow_html=True,
                    )
            with col5:
                if not is_admin:
                    if is_active:
                        if st.button("🔒 Block", key=f"block_{uid}", use_container_width=True):
                            result = api_client.admin_set_user_status(uid, is_active=False)
                            if result.get("success"):
                                st.success(f"User '{uname}' has been blocked.")
                                st.rerun()
                            else:
                                st.error(result.get("detail", "Failed to block user."))
                    else:
                        if st.button("🔓 Unblock", key=f"unblock_{uid}", use_container_width=True):
                            result = api_client.admin_set_user_status(uid, is_active=True)
                            if result.get("success"):
                                st.success(f"User '{uname}' has been unblocked.")
                                st.rerun()
                            else:
                                st.error(result.get("detail", "Failed to unblock user."))
                else:
                    st.markdown("<span style='color:#888;font-size:0.8rem;'>Protected</span>", unsafe_allow_html=True)

            with col6:
                if not is_admin:
                    if st.button("🗑️ Delete", key=f"delete_{uid}", use_container_width=True):
                        result = api_client.admin_delete_user(uid)
                        if result.get("success"):
                            st.success(f"User '{uname}' permanently deleted.")
                            st.rerun()
                        else:
                            st.error(result.get("detail", "Failed to delete user."))
                else:
                    st.markdown("<span style='color:#888;font-size:0.8rem;'>Protected</span>", unsafe_allow_html=True)

            st.markdown(
                "<div style='height:1px;background:rgba(255,255,255,0.07);margin:4px 0;'></div>",
                unsafe_allow_html=True,
            )

st.markdown("<br><div class='disclaimer'>Admin actions are permanent. Blocked users cannot log in until unblocked.</div>", unsafe_allow_html=True)
