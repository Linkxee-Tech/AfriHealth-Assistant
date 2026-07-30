import datetime
import pandas as pd
import streamlit as st
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
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()
st.markdown(f"<div class='app-title'>📊 Health Metrics Dashboard</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

metrics_data = api_client.get_health_metrics(limit=500)
latest_by_metric = {}
for entry in metrics_data:
    latest_by_metric.setdefault(entry.get("metric_type"), entry)

cards = ["Heart Rate", "Blood Pressure", "Blood Sugar", "Weight"]
columns = st.columns(4)
for column, metric_name in zip(columns, cards):
    entry = latest_by_metric.get(metric_name)
    with column:
        if entry:
            value = str(entry.get("value", ""))
            check = api_client.check_vitals(metric_name, value)
            status = check.get("status", "unknown").replace("_", " ").title()
            st.metric(metric_name, f"{value} {entry.get('unit', '')}".strip(), status)
        else:
            st.metric(metric_name, "No reading", "Not recorded")

st.markdown("### 📈 Blood Pressure Trend")
bp_rows = []
for entry in metrics_data:
    if entry.get("metric_type") != "Blood Pressure":
        continue
    try:
        systolic, diastolic = (float(part.strip()) for part in str(entry["value"]).split("/", 1))
        timestamp = entry.get("recorded_at") or entry.get("logged_at")
        bp_rows.append({"date": pd.to_datetime(timestamp), "Systolic": systolic, "Diastolic": diastolic})
    except (KeyError, TypeError, ValueError):
        continue
if bp_rows:
    chart = pd.DataFrame(bp_rows).sort_values("date").set_index("date")
    st.line_chart(chart[["Systolic", "Diastolic"]])
else:
    st.info("No blood-pressure readings recorded yet; the chart will populate from real entries.")

st.markdown("---")
st.markdown("### ➕ Record New Health Metric")
with st.form("metric_form"):
    c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
    with c1:
        metric_type = st.selectbox("📋 Select Metric", config.HEALTH_METRICS)
    with c2:
        unit = config.HEALTH_METRIC_UNITS[metric_type]
        value = st.text_input(f"📊 Value ({unit})", placeholder="120/80" if metric_type == "Blood Pressure" else "72")
    with c3:
        record_date = st.date_input("📅 Date", value=datetime.date.today())
        record_time = st.time_input("🕐 Time", value=datetime.datetime.now().time().replace(second=0, microsecond=0))
    with c4:
        notes = st.text_input("📝 Notes")
    submitted = st.form_submit_button("💾 Save Metric", width="stretch", type="primary")

if submitted:
    if not value.strip():
        st.error("Enter a metric value before saving.")
    else:
        recorded_at = datetime.datetime.combine(record_date, record_time)
        result = api_client.add_health_metric(metric_type, value.strip(), unit, notes.strip(), recorded_at=recorded_at)
        if isinstance(result, dict) and result.get("success", True) is False:
            st.error(result.get("detail", "Metric could not be saved."))
        else:
            st.success(f"Saved {metric_type}: {value.strip()} {unit}")
            st.rerun()

if metrics_data:
    st.markdown("### Recorded Data")
    st.dataframe(pd.DataFrame(metrics_data), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Export Health Data (CSV)",
        data=pd.DataFrame(metrics_data).to_csv(index=False),
        file_name="afrihealth_health_data.csv",
        mime="text/csv",
    )
