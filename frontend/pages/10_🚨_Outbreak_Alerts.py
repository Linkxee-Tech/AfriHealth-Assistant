"""
AfriHealth Assistant - Disease Outbreak Alerts
Displays real-time WHO disease outbreak news.
"""
import streamlit as st
import config
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state

st.set_page_config(page_title=f"Outbreak Alerts - {config.APP_NAME}", page_icon="🚨", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown("<div class='app-title'>🚨 Outbreak Alerts</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Real-time WHO Disease Outbreak News</div><hr>", unsafe_allow_html=True)

col_filter, col_refresh = st.columns([4, 1])
with col_filter:
    region_filter = st.text_input("🔍 Filter by region or disease", placeholder="e.g. Africa, malaria, cholera")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh", use_container_width=True)

with st.spinner("Fetching latest outbreak alerts from WHO..."):
    data = api_client.get_outbreaks(region=region_filter if region_filter else None)

alerts = data.get("alerts", [])

if not alerts:
    st.info("No outbreak alerts found" + (f" for '{region_filter}'" if region_filter else "") + ". The WHO feed may be temporarily unavailable or no alerts match your filter.")
else:
    st.markdown(f"**{len(alerts)} alert(s) found** (Source: WHO RSS — updates every 30 minutes)")
    st.markdown("---")
    for i, alert in enumerate(alerts):
        with st.expander(f"🔴 {alert.get('title', 'Untitled Alert')}", expanded=(i < 2)):
            if alert.get("published"):
                st.caption(f"📅 Published: {alert['published']}")
            st.markdown(alert.get("summary", "No summary available."))
            if alert.get("link"):
                st.markdown(f"[Read full report on WHO website ↗]({alert['link']})")

st.markdown("---")
st.caption("Data sourced from WHO RSS feeds. AfriHealth Assistant is not responsible for the accuracy of WHO publications.")
