"""
Health metrics dashboard component.

Spec requirements (Page 2):
  - st.form + st.number_input + st.selectbox  (metric input form)
  - st.line_chart, st.bar_chart, st.area_chart  (all three chart types)
  - st.metric cards (latest readings)
  - st.date_input + st.slider  (date filter)
  - st.download_button (export)
  - notes field (per data model spec)
  - trackable metrics: Blood Pressure, Heart Rate, Blood Sugar,
    Weight, Temperature, Oxygen Saturation (SpO2), Sleep Hours
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import config
from utils import api_client


def render_metrics_dashboard():
    st.markdown("#### Log a Health Metric")
    st.caption("Stored locally on this device — fully offline.")

    with st.form("health_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            metric_type = st.selectbox("Metric", config.HEALTH_METRICS)
        with c2:
            unit_default = config.HEALTH_METRIC_UNITS.get(metric_type, "")
            # Use number_input for numeric metrics, text_input for BP (e.g. "120/80")
            if metric_type == "Blood Pressure":
                value_str = st.text_input("Value", placeholder="e.g. 120/80")
                value_num = None
            else:
                value_num = st.number_input(
                    "Value",
                    min_value=0.0, max_value=9999.0, step=0.1, format="%.1f"
                )
                value_str = None
        with c3:
            unit = st.text_input("Unit", value=unit_default)

        notes = st.text_input("Notes (optional)", placeholder="e.g. after exercise")
        log_submitted = st.form_submit_button("➕ Add Entry")

    if log_submitted:
        final_value = value_str if metric_type == "Blood Pressure" else str(value_num)
        if final_value and final_value.strip() and final_value != "0.0":
            api_client.add_health_entry(metric_type, final_value.strip(), unit.strip(), notes.strip() or None)
            st.success(f"Logged {metric_type}: {final_value} {unit}")
            st.rerun()
        else:
            st.warning("Enter a value before submitting.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Latest readings as st.metric cards
    # ------------------------------------------------------------------
    st.markdown("#### Latest Readings")
    all_entries = api_client.get_health_entries()
    latest_by_metric = {}
    for e in all_entries:
        if e["metric_type"] not in latest_by_metric:
            latest_by_metric[e["metric_type"]] = e

    if latest_by_metric:
        cols = st.columns(min(4, len(latest_by_metric)))
        for i, (mtype, entry) in enumerate(latest_by_metric.items()):
            with cols[i % len(cols)]:
                st.metric(mtype, f"{entry['value']} {entry['unit'] or ''}".strip())
    else:
        st.info("No health entries logged yet. Add your first entry above.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Filters: metric selectbox + date range (st.date_input) + st.slider
    # ------------------------------------------------------------------
    st.markdown("#### History & Trends")

    fc1, fc2 = st.columns([2, 3])
    with fc1:
        filter_metric = st.selectbox(
            "Filter by metric", ["All"] + config.HEALTH_METRICS, key="health_filter"
        )
    with fc2:
        # st.date_input for range
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        date_range = st.date_input(
            "Date range",
            value=(thirty_days_ago, today),
            key="health_date_range",
        )

    # st.slider for days-back (spec lists slider alongside date_input)
    days_back = st.slider("Or show last N days", min_value=1, max_value=365, value=30, step=1)

    entries = api_client.get_health_entries(
        metric_type=None if filter_metric == "All" else filter_metric
    )

    # Apply date filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        end_d = today
        start_d = today - timedelta(days=days_back)

    filtered = []
    for e in entries:
        try:
            logged_d = datetime.strptime(e["logged_at"], "%Y-%m-%d %H:%M").date()
            if start_d <= logged_d <= end_d:
                filtered.append(e)
        except (ValueError, TypeError):
            filtered.append(e)
    entries = filtered

    if not entries:
        st.info("No entries match the current filters.")
        return

    df = pd.DataFrame(entries)
    display_df = df[["logged_at", "metric_type", "value", "unit", "notes"]].copy()
    display_df.columns = ["Logged At", "Metric", "Value", "Unit", "Notes"]
    st.dataframe(display_df, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # Charts: line + bar + area  (all three per spec)
    # ------------------------------------------------------------------
    if filter_metric != "All":
        try:
            chart_df = df[["logged_at", "value"]].copy()
            chart_df["value"] = pd.to_numeric(chart_df["value"], errors="coerce")
            chart_df = chart_df.dropna().sort_values("logged_at")
            if len(chart_df) >= 2:
                chart_df = chart_df.set_index("logged_at")
                t1, t2, t3 = st.tabs(["📈 Line", "📊 Bar", "🏔 Area"])
                with t1:
                    st.line_chart(chart_df)
                with t2:
                    st.bar_chart(chart_df)
                with t3:
                    st.area_chart(chart_df)
        except Exception:
            pass  # BP "120/80" or other non-numeric; skip charting

    st.markdown("---")

    # Export + delete
    ex_col, del_col = st.columns(2)
    with ex_col:
        st.download_button(
            "⬇️ Export Health Data (CSV)",
            data=display_df.to_csv(index=False),
            file_name="afrihealth_health_data.csv",
            mime="text/csv",
        )
    with del_col:
        del_id = st.selectbox(
            "Delete entry by ID", [None] + [e["id"] for e in entries], key="del_health_id"
        )
        if del_id and st.button("🗑️ Delete Selected Entry"):
            api_client.delete_health_entry(del_id)
            st.rerun()
