import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"Clinical Support — {config.APP_NAME}", page_icon="🩺", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("pages/0_🔐_Login.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown(f"<div class='app-title'>🩺 Clinical Support</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Personalized coaching, triage, medication checks, and offline protocol guidance.</div><hr>", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🧘 Health Coach", "🚑 Clinical Triage", "💊 Medication Checker", "📚 Protocol Reference"])

# -----------------------------
# 🧘 Health Coach
# -----------------------------
with t1:
    st.markdown("<br>### Personalized Health Coach", unsafe_allow_html=True)
    st.markdown("<div style='color: #8892B0; margin-bottom: 20px;'>Generate tailored lifestyle and medical advice based on your current metrics.</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        with st.form("coach_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                age = st.number_input("Age", min_value=0, max_value=120, value=st.session_state.get("coach_age", 30))
                gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"])
                pregnant = st.checkbox("Pregnant", value=st.session_state.get("coach_pregnant", False))
            with col2:
                height_cm = st.number_input("Height (cm)", min_value=0.0, value=float(st.session_state.get("coach_height_cm", 170.0)), step=0.5)
                weight_kg = st.number_input("Weight (kg)", min_value=0.0, value=float(st.session_state.get("coach_weight_kg", 70.0)), step=0.1)
                activity_level = st.selectbox("Activity Level", ["Sedentary", "Light", "Moderate", "Active", "Very Active"], index=1)
            with col3:
                metric1_type = st.selectbox("Metric 1", config.HEALTH_METRICS, key="coach_m1_t")
                metric1_value = st.text_input("Value 1", placeholder="e.g. 120/80", key="coach_m1_v")
                metric2_type = st.selectbox("Metric 2", config.HEALTH_METRICS, index=1, key="coach_m2_t")
                metric2_value = st.text_input("Value 2", placeholder="e.g. 72", key="coach_m2_v")
                
            coach_submitted = st.form_submit_button("✨ Generate Recommendations", type="primary", use_container_width=True)

    if coach_submitted:
        patient_context = {
            "age": age, "gender": gender if gender != "Prefer not to say" else None,
            "pregnant": pregnant, "height_cm": height_cm, "weight_kg": weight_kg, "activity_level": activity_level,
        }
        metrics = []
        if metric1_value.strip(): metrics.append({"metric_type": metric1_type, "value": metric1_value.strip(), "unit": config.HEALTH_METRIC_UNITS.get(metric1_type, "")})
        if metric2_value.strip(): metrics.append({"metric_type": metric2_type, "value": metric2_value.strip(), "unit": config.HEALTH_METRIC_UNITS.get(metric2_type, "")})
        
        with st.spinner("Analyzing context..."):
            st.session_state["coach_result"] = api_client.request_personalized_coach(metrics, patient_context)

    if st.session_state.get("coach_result"):
        res = st.session_state["coach_result"]
        c_i, c_a, c_r = st.columns(3)
        with c_i:
            st.markdown("#### 💡 Insights")
            for item in res.get("insights", []): st.info(item)
        with c_a:
            st.markdown("#### ⚠️ Risk Alerts")
            for item in res.get("risk_alerts", []): st.warning(item)
        with c_r:
            st.markdown("#### ✅ Recommendations")
            for item in res.get("recommendations", []): st.success(item)

# -----------------------------
# 🚑 Clinical Triage
# -----------------------------
with t2:
    st.markdown("<br>### Clinical Triage & Risk Assessment", unsafe_allow_html=True)
    st.markdown("<div style='color: #8892B0; margin-bottom: 20px;'>Fast, offline symptom analysis for preliminary triage.</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        with st.form("triage_form"):
            symptoms_text = st.text_area("Reported Symptoms (comma-separated)", placeholder="e.g. high fever, severe headache, muscle aches")
            col1, col2 = st.columns(2)
            with col1:
                triage_age = st.number_input("Age", min_value=0, max_value=120, value=30, key="t_age")
                triage_gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"], key="t_gen")
            with col2:
                triage_activity = st.selectbox("Activity Level", ["Sedentary", "Light", "Moderate", "Active", "Very Active"], index=1, key="t_act")
                triage_pregnant = st.checkbox("Pregnant", key="t_preg")
            triage_submitted = st.form_submit_button("🚑 Analyze Symptoms", type="primary", use_container_width=True)

    if triage_submitted:
        symptoms = [s.strip() for s in symptoms_text.split(",") if s.strip()]
        ctx = {"age": triage_age, "gender": triage_gender if triage_gender != "Prefer not to say" else None, "pregnant": triage_pregnant, "activity_level": triage_activity}
        with st.spinner("Triaging..."):
            st.session_state["triage_result"] = api_client.request_clinical_triage(symptoms, ctx)

    if st.session_state.get("triage_result"):
        res = st.session_state["triage_result"]
        urg_color = "#E74C3C" if res.get('urgency', '').lower() in ["high", "emergency", "critical"] else "#F5A623" if res.get('urgency', '').lower() == "medium" else "#2EAA7D"
        
        st.markdown(f"<div class='status-card' style='border-left: 4px solid {urg_color};'><h3 style='margin-top:0;'>Urgency: {res.get('urgency', 'Unknown')}</h3><p>{res.get('advice', '')}</p></div>", unsafe_allow_html=True)
        
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("#### 🛑 Do Not Do")
            for item in res.get("do_not", []): st.error(item)
        with rc2:
            st.markdown("#### 📋 Clinical Decision Support")
            st.write(f"**Risk factors:** {', '.join(res.get('identified_risk_factors', [])) or 'None'}")
            st.write(f"**Epidemiological flags:** {', '.join(res.get('epidemiological_flags', [])) or 'None'}")

# -----------------------------
# 💊 Medication Checker
# -----------------------------
with t3:
    st.markdown("<br>### Medication Interaction Checker", unsafe_allow_html=True)
    st.markdown("<div style='color: #8892B0; margin-bottom: 20px;'>Check common drug combinations for potential interaction risks.</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        with st.form("medication_form"):
            meds = st.text_area("Medications List (comma-separated)", placeholder="e.g. Amoxicillin, Ibuprofen, Paracetamol")
            med_submitted = st.form_submit_button("💊 Check Interactions", type="primary", use_container_width=True)

    if med_submitted:
        medications = [m.strip() for m in meds.split(",") if m.strip()]
        with st.spinner("Checking database..."):
            st.session_state["medication_result"] = api_client.request_medication_interactions(medications)

    if st.session_state.get("medication_result"):
        res = st.session_state["medication_result"]
        if res.get("interactions"):
            st.error("#### ⚠️ Potential Interactions Detected")
            for interaction in res["interactions"]: st.write(f"- {interaction}")
        else:
            st.success("#### ✅ No Known Interactions Detected")
            st.write("Safe to co-administer based on standard guidelines.")
        for note in res.get("notes", []):
            st.caption(f"Note: {note}")

# -----------------------------
# 📚 Protocol Reference
# -----------------------------
with t4:
    st.markdown("<br>### Treatment Protocol Reference", unsafe_allow_html=True)
    st.markdown("<div style='color: #8892B0; margin-bottom: 20px;'>Search offline clinical protocols and WHO guidelines.</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        with st.form("protocol_form"):
            condition = st.text_input("Medical Condition", placeholder="e.g. Malaria, Hypertension, Typhoid")
            protocol_submitted = st.form_submit_button("📚 Search Protocol", type="primary", use_container_width=True)

    if protocol_submitted:
        with st.spinner("Retrieving offline protocols..."):
            st.session_state["protocol_result"] = api_client.request_treatment_protocol(condition)

    if st.session_state.get("protocol_result"):
        res = st.session_state["protocol_result"]
        st.markdown(f"#### 🏥 {res.get('condition', '').title()} Protocol")
        with st.container(border=True):
            for step in res.get("protocol", []):
                st.write(f"- {step}")
            if res.get("references"):
                st.markdown("---")
                st.markdown("**📚 References:**")
                for ref in res["references"]:
                    st.write(f"- {ref}")
