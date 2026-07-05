import streamlit as st
import pandas as pd
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"Health Metrics — {config.APP_NAME}", page_icon="📊", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("pages/0_🔐_Login.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown(f"<div class='app-title'>📊 Health Metrics Dashboard</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# Fetch metrics
metrics_data = api_client.get_health_metrics()

# --- TOP: 4 Columns ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""<div class='status-card'>
        <div><b>❤️ Heart Rate</b></div>
        <div style='font-size: 1.5rem; font-weight: 700;'>72 bpm</div>
        <div style='color: #2EAA7D; font-size: 0.9rem;'>✅ Normal</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown("""<div class='status-card'>
        <div><b>💉 Blood Pressure</b></div>
        <div style='font-size: 1.5rem; font-weight: 700;'>120/80 mmHg</div>
        <div style='color: #2EAA7D; font-size: 0.9rem;'>✅ Normal</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown("""<div class='status-card'>
        <div><b>🩸 Blood Sugar</b></div>
        <div style='font-size: 1.5rem; font-weight: 700;'>5.6 mmol/L</div>
        <div style='color: #2EAA7D; font-size: 0.9rem;'>✅ Normal</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown("""<div class='status-card'>
        <div><b>⚖️ Weight</b></div>
        <div style='font-size: 1.5rem; font-weight: 700;'>72 kg</div>
        <div style='color: #2EAA7D; font-size: 0.9rem;'>✅ Normal</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- MIDDLE: Trend Chart ---
st.markdown("### 📈 Blood Pressure Trend (Last 30 Days)")
if not metrics_data:
    st.info("No real health metrics recorded yet. Showing placeholder trend.")
    
# Dummy data for the chart to match mockup
import numpy as np
dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
bp_sys = np.random.normal(120, 5, 30)
bp_dia = np.random.normal(80, 3, 30)
df_trend = pd.DataFrame({"Systolic": bp_sys, "Diastolic": bp_dia}, index=dates)
st.line_chart(df_trend, color=["#E74C3C", "#2EAA7D"])

st.markdown("---")

# --- BOTTOM: Record New Metric ---
st.markdown("### ➕ Record New Health Metric")

with st.form("metric_form"):
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 3])
    with f_col1:
        metric_type = st.selectbox("📋 Select Metric", config.HEALTH_METRICS)
    with f_col2:
        unit = config.HEALTH_METRIC_UNITS[metric_type]
        value = st.number_input(f"📊 Value ({unit})", step=0.1)
    with f_col3:
        record_date = st.date_input("📅 Date")
        record_time = st.time_input("🕐 Time")
    with f_col4:
        notes = st.text_input("📝 Notes")
    
    submit_col1, submit_col2, _ = st.columns([2, 2, 6])
    with submit_col1:
        submitted = st.form_submit_button("💾 Save Metric", use_container_width=True)
    with submit_col2:
        st.form_submit_button("🗑️ Cancel", use_container_width=True)
        
    if submitted:
        api_client.add_health_metric(metric_type, str(value), unit, notes)
        st.success(f"Saved {metric_type}: {value} {unit}")
        st.rerun()
