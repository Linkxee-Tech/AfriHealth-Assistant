"""
AfriHealth Assistant - Medication Reminders
"""
import json
import streamlit as st
import config
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state

st.set_page_config(page_title=f"Medications - {config.APP_NAME}", page_icon="💊", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown("<div class='app-title'>💊 Medication Reminders</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Track your medications and schedules</div><hr>", unsafe_allow_html=True)

tab_list, tab_add = st.tabs(["📋 My Medications", "➕ Add Medication"])

with tab_add:
    st.markdown("### Add a New Medication")
    with st.form("add_medication_form"):
        col1, col2 = st.columns(2)
        with col1:
            med_name = st.text_input("Medication Name *", placeholder="e.g. Paracetamol")
            dosage = st.text_input("Dosage *", placeholder="e.g. 500mg")
            frequency = st.selectbox("Frequency *", [
                "Once daily", "Twice daily", "Three times daily",
                "Every 4 hours", "Every 6 hours", "Every 8 hours",
                "Weekly", "As needed"
            ])
        with col2:
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date (optional)")
            times_input = st.text_input("Times", placeholder="e.g. 08:00, 20:00 (comma separated)")
        notes = st.text_area("Instructions / Notes", placeholder="e.g. Take with food", height=80)
        submitted = st.form_submit_button("💊 Add Medication", type="primary")

        if submitted:
            if not med_name or not dosage:
                st.error("Please fill in the medication name and dosage.")
            else:
                times_list = [t.strip() for t in times_input.split(",") if t.strip()] if times_input else []
                result = api_client.add_medication(
                    name=med_name,
                    dosage=dosage,
                    frequency=frequency,
                    times=times_list,
                    start_date=str(start_date),
                    end_date=str(end_date) if end_date else None,
                    notes=notes,
                )
                if result.get("success"):
                    st.success(f"✅ {result.get('message', 'Medication added!')}") 
                    st.rerun()
                else:
                    st.error(result.get("detail", "Failed to add medication"))

with tab_list:
    with st.spinner("Loading medications..."):
        data = api_client.get_medications()
    meds = data.get("medications", [])

    if not meds:
        st.info("No medications added yet. Use the 'Add Medication' tab to add your first one.")
    else:
        st.markdown(f"**{len(meds)} medication(s) tracked**")
        for med in meds:
            times_str = ", ".join(med.get("times") or []) or "Not specified"
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**💊 {med['name']}** — {med.get('dosage', '')}")
                    st.caption(f"Frequency: {med.get('frequency', '')} | Times: {times_str}")
                    if med.get("notes"):
                        st.caption(f"📝 {med['notes']}")
                with col2:
                    if med.get("start_date"):
                        st.caption(f"Start: {med['start_date']}")
                    if med.get("end_date"):
                        st.caption(f"End: {med['end_date']}")
                with col3:
                    if st.button("🗑️", key=f"del_med_{med['id']}", help="Delete"):
                        result = api_client.delete_medication(med["id"])
                        if result.get("success"):
                            st.rerun()
                        else:
                            st.error("Failed to delete")
