"""
AfriHealth Assistant - Patient Management Module (Phase 3)
A lightweight EMR and Clinical Decision Support System.
"""
import streamlit as st
import datetime
import json
import pandas as pd
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client

st.set_page_config(page_title="Patients - AfriHealth Assistant", page_icon="👨‍⚕️", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

# Authentication check
if not st.session_state.get("access_token"):
    st.warning("Please login to access Patient Management.")
    st.stop()

# View routing state
if "patient_view" not in st.session_state:
    st.session_state["patient_view"] = "directory" # 'directory', 'register', 'profile', 'visit'
if "selected_patient_id" not in st.session_state:
    st.session_state["selected_patient_id"] = None

def navigate(view: str, patient_id=None):
    st.session_state["patient_view"] = view
    if patient_id:
        st.session_state["selected_patient_id"] = patient_id
    st.rerun()

st.title("👨‍⚕️ Patient Management")

# -----------------------------------------------------------------------------
# View 1: Patient Directory
# -----------------------------------------------------------------------------
if st.session_state["patient_view"] == "directory":
    st.markdown("### Patient Directory")
    
    patients = api_client.get_patients()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Patients", len(patients))
        
    # PM8: Calculate New Today and Gender Distribution
    today_str = datetime.date.today().isoformat()
    new_today = sum(1 for p in patients if p.get('created_at', '').startswith(today_str))
    males = sum(1 for p in patients if p.get('gender') == "Male")
    females = sum(1 for p in patients if p.get('gender') == "Female")
    
    with col2:
        st.metric("New Today", new_today)
    with col3:
        st.metric("Gender Split", f"{males}M / {females}F")
    with col4:
        if st.button("➕ Register Patient", width="stretch", type="primary"):
            navigate("register")
            
    st.markdown("---")
    
    search_term = st.text_input("🔍 Search Patients (Name, MRN, Phone)", placeholder="Type to search...")
    
    # PM4 & PM5: Basic filtering (locally filtering the results)
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        gender_filter = st.selectbox("Filter by Gender", ["All", "Male", "Female", "Other"])
    with f_col2:
        sort_by = st.selectbox("Sort by", ["Newest First", "Oldest First", "Name (A-Z)"])

    patients = api_client.get_patients(search=search_term if search_term else None)
    
    # Apply local filters
    if gender_filter != "All":
        patients = [p for p in patients if p.get('gender') == gender_filter]
        
    if sort_by == "Oldest First":
        patients.reverse() # Since default is newest
    elif sort_by == "Name (A-Z)":
        patients.sort(key=lambda x: (x.get('first_name', ''), x.get('last_name', '')))
    
    if not patients:
        st.info("No patients found.")
    else:
        # Display as a full grid of cards
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Paginate the real patient results returned by the backend.
        items_per_page = 8
        if "patient_page" not in st.session_state:
            st.session_state.patient_page = 1
            
        page = st.session_state.patient_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = patients[start_idx:end_idx]
        
        # Grid
        cols = st.columns(4)
        for i, p in enumerate(page_items):
            with cols[i % 4]:
                st.markdown(f"""
                <div class='status-card'>
                    <div style='font-weight:600; font-size:1.1rem; color:__TEXT__;'>👤 {p['first_name']} {p['last_name']}</div>
                    <hr style='margin: 8px 0; border-color: #2A3A54;'>
                    <div style='font-size:0.85rem; color:#8892B0;'>
                        MRN: {p['mrn']}<br>
                        🩺 {p.get('gender', 'Unknown')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("👤 View", key=f"view_{p['id']}", width="stretch"):
                    navigate("profile", p["id"])
                    
        total_pages = max(1, (len(patients) + items_per_page - 1) // items_per_page)
        st.session_state.patient_page = min(page, total_pages)
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col1:
            if st.button("Previous", disabled=page <= 1, width="stretch"):
                st.session_state.patient_page = page - 1
                st.rerun()
        with page_col2:
            st.caption(f"Page {page} of {total_pages} · {len(patients)} patient(s)")
        with page_col3:
            if st.button("Next", disabled=page >= total_pages, width="stretch"):
                st.session_state.patient_page = page + 1
                st.rerun()

# -----------------------------------------------------------------------------
# View 2: Register Patient
# -----------------------------------------------------------------------------
elif st.session_state["patient_view"] == "register":
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### Register New Patient")
    with col2:
        if st.button("🔙 Back to Directory"):
            navigate("directory")
            
    with st.form("register_patient_form"):
        st.markdown("#### Demographics")
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First Name *")
            gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
            phone = st.text_input("Phone Number *")
        with c2:
            last_name = st.text_input("Last Name *")
            dob = st.date_input("Date of Birth *", min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today())
            emergency = st.text_input("Emergency Contact")
            
        st.markdown("#### Clinical Information")
        c3, c4 = st.columns(2)
        with c3:
            blood_type = st.selectbox("Blood Type", ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            allergies = st.text_area("Allergies", placeholder="Drug or food allergies...")
            notes = st.text_area("Administrative Notes", placeholder="Any other important info...")
        with c4:
            history = st.text_area("Medical History", placeholder="Chronic diseases, past surgeries...")
            address = st.text_area("Residential Address")
            
        submitted = st.form_submit_button("Save Patient Record", type="primary")
        if submitted:
            if not first_name or not last_name or not phone:
                st.error("First Name, Last Name, and Phone are required fields.")
            else:
                payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "gender": gender,
                    "date_of_birth": dob.isoformat(),
                    "phone": phone,
                    "emergency_contact": emergency,
                    "address": address,
                    "blood_type": blood_type,
                    "allergies": allergies,
                    "medical_history": history,
                    "notes": notes
                }
                with st.spinner("Registering..."):
                    res = api_client.create_patient(payload)
                if res.get("success"):
                    st.success("Patient registered successfully!")
                    st.balloons()
                    navigate("profile", res["patient_id"])
                else:
                    st.error(f"Failed to register: {res.get('detail')}")

# -----------------------------------------------------------------------------
# View 3: Patient Profile
# -----------------------------------------------------------------------------
elif st.session_state["patient_view"] == "profile":
    patient_id = st.session_state.get("selected_patient_id")
    if not patient_id:
        navigate("directory")
        
    patient = api_client.get_patient(patient_id)
    if not patient:
        st.error("Patient not found.")
        if st.button("Back"): navigate("directory")
        st.stop()
        
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.markdown(f"### {patient['first_name']} {patient['last_name']}")
    with c2:
        if st.button("🔙 Back", width="stretch"):
            navigate("directory")
            
    # Calculate age
    age = "Unknown"
    if patient.get('date_of_birth'):
        dob_dt = datetime.datetime.fromisoformat(patient['date_of_birth'])
        today = datetime.date.today()
        age = today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))

    # Top Metrics Profile Card
    st.markdown(f"""
    <div class='status-card' style='padding: 24px;'>
        <div style='font-size: 1.5rem; font-weight: 700; color: #2EAA7D;'>👤 {patient['first_name']} {patient['last_name']}</div>
        <div style='font-size: 1rem; color: #8892B0; margin-bottom: 12px;'>🩺 MRN: {patient['mrn']}</div>
        <div style='display: flex; gap: 24px; font-size: 0.95rem; margin-bottom: 12px;'>
            <div>🧑 {patient['gender']}</div>
            <div>📅 {age} yrs</div>
            <div>📱 {patient['phone']}</div>
            <div>🩸 Blood Type: {patient.get('blood_type', 'N/A')}</div>
        </div>
        <hr style='border-color: #2A3A54; margin: 16px 0;'>
        <div style='font-size: 0.95rem;'>
            <b>💊 Allergies:</b> <span style='color: #E74C3C;'>{patient.get('allergies', 'None recorded')}</span><br>
            <b>📋 Medical History:</b> {patient.get('medical_history', 'None recorded')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    a1, a2, a3, a4, _ = st.columns([2, 2, 2, 2, 4])
    with a1:
        st.button("✏️ Edit Profile", width="stretch")
    with a2:
        st.button("🗑️ Delete", width="stretch")
    with a3:
        export_data = api_client.export_patient(patient_id)
        st.download_button(
            "📥 Export JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"patient_{patient.get('mrn', patient_id)}.json",
            mime="application/json",
            width="stretch",
        )
    with a4:
        pdf_bytes, pdf_filename = api_client.download_patient_pdf(patient_id)
        if pdf_bytes:
            # Extract clean filename if content-disposition header returned
            if "filename=" in pdf_filename:
                pdf_filename = pdf_filename.split("filename=")[1].strip('"')
            st.download_button(
                "📄 Export PDF",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.button("📄 Export PDF", disabled=True, width="stretch", help="PDF export unavailable")

    # Detailed Tabs
    t1, t2, t3, t4, t5 = st.tabs(["📋 Visit History", "🏥 Medical Details", "📊 Health Trends", "📁 Test Reports", "⚙️ Manage"])
    
    with t1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Record New Visit", type="primary"):
            navigate("visit", patient_id)
            
        st.markdown("---")
        visits = api_client.get_patient_visits(patient_id)
        if not visits:
            st.info("No visit history found for this patient.")
        else:
            for v in visits:
                date_str = pd.to_datetime(v['visit_date']).strftime('%B %d, %Y - %H:%M')
                with st.expander(f"{date_str} | {v.get('visit_type', 'Follow-up')}", expanded=False):
                    vc1, vc2 = st.columns(2)
                    with vc1:
                        st.markdown("**Chief Complaint:**")
                        st.info(v.get('chief_complaint', 'N/A'))
                        st.markdown("**AI Diagnosis Suggestions:**")
                        st.success(v.get('ai_suggestions', 'N/A'))
                    with vc2:
                        st.markdown("**Medications Prescribed:**")
                        st.warning(v.get('medications', 'None recorded'))
                        if v.get('next_visit'):
                            next_v = pd.to_datetime(v['next_visit']).strftime('%B %d, %Y')
                            st.markdown(f"**Next Visit Scheduled:** {next_v}")

    with t2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # PM28: Medication History (aggregate from visits)
        st.markdown("#### Medication History")
        visits = api_client.get_patient_visits(patient_id)
        meds_data = []
        for v in visits:
            if v.get('medications'):
                date_str = pd.to_datetime(v['visit_date']).strftime('%Y-%m-%d')
                meds_data.append({"Date": date_str, "Medication": v['medications']})
        
        if meds_data:
            st.dataframe(pd.DataFrame(meds_data), width="stretch", hide_index=True)
        else:
            st.info("No medication history found.")
            
        st.markdown("#### Active Medication Reminders")
        active_meds = api_client.get_medications(patient_id=patient_id).get("medications", [])
        if active_meds:
            med_list = [{"Name": m["name"], "Dosage": m["dosage"], "Frequency": m["frequency"]} for m in active_meds]
            st.dataframe(pd.DataFrame(med_list), width="stretch", hide_index=True)
        else:
            st.info("No active medication reminders for this patient.")

        st.markdown("---")
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("#### Allergies")
            st.error(patient.get('allergies', 'None recorded'))
        with mc2:
            st.markdown("#### Medical History")
            st.info(patient.get('medical_history', 'None recorded'))

    with t3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Health Metrics Trends")
        
        metrics = api_client.get_health_metrics(patient_id=patient_id)
        if not metrics:
            st.info("No health metrics recorded for this patient.")
        else:
            df = pd.DataFrame(metrics)
            if 'recorded_at' in df.columns:
                df['Date'] = pd.to_datetime(df['recorded_at'])
                
                m1, m2 = st.columns(2)
                with m1:
                    bp_data = df[df['metric_type'] == 'Blood Pressure']
                    if not bp_data.empty:
                        st.markdown("**Blood Pressure Trend (mmHg)**")
                        # Extract systolic for simple charting
                        bp_data['Systolic'] = bp_data['value'].apply(lambda x: int(x.split('/')[0]) if '/' in x else 0)
                        st.line_chart(bp_data.set_index('Date')['Systolic'])
                    else:
                        st.info("No Blood Pressure records.")
                with m2:
                    bs_data = df[df['metric_type'] == 'Blood Sugar']
                    if not bs_data.empty:
                        st.markdown("**Blood Sugar Trend (mg/dL)**")
                        bs_data['Value'] = pd.to_numeric(bs_data['value'], errors='coerce')
                        st.line_chart(bs_data.set_index('Date')['Value'])
                    else:
                        st.info("No Blood Sugar records.")
        
        st.markdown("---")
        with st.expander("➕ Record New Health Metric"):
            with st.form("new_metric_form"):
                mc1, mc2 = st.columns(2)
                m_type = mc1.selectbox("Metric Type", ["Blood Pressure", "Blood Sugar", "Heart Rate", "Weight", "Temperature"])
                m_val = mc2.text_input("Value")
                m_unit = mc1.text_input("Unit (Optional)")
                m_notes = mc2.text_input("Notes (Optional)")
                if st.form_submit_button("Save Metric", type="primary"):
                    if m_val:
                        api_client.add_health_metric(metric_type=m_type, value=m_val, unit=m_unit, notes=m_notes, patient_id=patient_id)
                        st.success("Metric saved!")
                        st.rerun()
                    else:
                        st.error("Value is required")

    with t4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Test Reports & Documents")
        
        docs = api_client.get_documents(patient_id=patient_id)
        if not docs:
            st.info("No documents uploaded for this patient.")
        else:
            for d in docs:
                with st.container(border=True):
                    dc1, dc2 = st.columns([0.8, 0.2])
                    dc1.markdown(f"**{d.get('filename')}**")
                    date_str = pd.to_datetime(d.get('uploaded_at')).strftime('%Y-%m-%d %H:%M') if d.get('uploaded_at') else "Unknown"
                    dc1.caption(f"Uploaded: {date_str}")
                    if dc2.button("View Details", key=f"doc_{d.get('id')}"):
                        st.session_state["viewing_doc"] = d
                        
            if st.session_state.get("viewing_doc"):
                st.markdown("---")
                v_doc = st.session_state["viewing_doc"]
                st.markdown(f"##### Analysis: {v_doc.get('filename')}")
                st.info(v_doc.get('analysis_result', 'No analysis available.'))
                if st.button("Close Viewer"):
                    st.session_state["viewing_doc"] = None
                    st.rerun()
                    
        st.markdown("---")
        with st.expander("➕ Upload New Report"):
            uploaded_file = st.file_uploader("Upload Medical Document", type=["pdf", "png", "jpg", "docx"])
            if uploaded_file is not None:
                if st.button("Process & Save Document", type="primary"):
                    with st.spinner("Uploading and analyzing..."):
                        res = api_client.upload_document(uploaded_file, uploaded_file.name, patient_id=patient_id)
                        if res.get("status") in ["processing", "success"]:
                            st.success("Document uploaded successfully!")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Upload failed"))

    with t5:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # PM24: Edit Personal Information
        with st.expander("✏️ Edit Personal Information"):
            with st.form("edit_patient_form"):
                e_c1, e_c2 = st.columns(2)
                with e_c1:
                    e_first_name = st.text_input("First Name", value=patient.get("first_name", ""))
                    e_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(patient.get("gender", "Male")))
                    e_phone = st.text_input("Phone Number", value=patient.get("phone", ""))
                    e_allergies = st.text_area("Allergies", value=patient.get("allergies", ""))
                with e_c2:
                    e_last_name = st.text_input("Last Name", value=patient.get("last_name", ""))
                    e_blood_type = st.selectbox("Blood Type", ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], index=["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].index(patient.get("blood_type", "Unknown")))
                    e_address = st.text_area("Address", value=patient.get("address", ""))
                    e_history = st.text_area("Medical History", value=patient.get("medical_history", ""))
                    
                if st.form_submit_button("Update Patient Info", type="primary"):
                    payload = {
                        "first_name": e_first_name,
                        "last_name": e_last_name,
                        "gender": e_gender,
                        "phone": e_phone,
                        "blood_type": e_blood_type,
                        "address": e_address,
                        "allergies": e_allergies,
                        "medical_history": e_history
                    }
                    result = api_client.update_patient(patient_id, payload)
                    if result.get("success"):
                        st.success("Patient updated!")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Patient update failed."))

        st.markdown("---")
        st.warning("Administrative actions")
        if st.button("Prepare Patient Record (PDF)", width="stretch"):
            pdf_bytes, pdf_name = api_client.download_patient_pdf(patient_id)
            if pdf_bytes:
                st.session_state[f"patient_pdf_{patient_id}"] = pdf_bytes
                st.session_state[f"patient_pdf_name_{patient_id}"] = pdf_name.split("filename=")[-1].strip('"')
            else:
                st.error(f"PDF export unavailable: {pdf_name}")
        pdf_bytes = st.session_state.get(f"patient_pdf_{patient_id}")
        if pdf_bytes:
            st.download_button(
                "Export Patient Record (PDF)",
                data=pdf_bytes,
                file_name=st.session_state.get(f"patient_pdf_name_{patient_id}", f"patient-{patient_id}.pdf"),
                mime="application/pdf",
                width="stretch",
            )
        
        # PM31: Delete Patient logic
        if st.button("Delete Patient", type="primary"):
            st.session_state["confirm_delete"] = True
            
        if st.session_state.get("confirm_delete"):
            st.error(f"Are you sure you want to completely delete {patient['first_name']} {patient['last_name']}? This cannot be undone.")
            d_c1, d_c2 = st.columns(2)
            with d_c1:
                if st.button("Yes, Delete Patient", width="stretch"):
                    result = api_client.delete_patient(patient_id)
                    if result.get("success"):
                        st.session_state["confirm_delete"] = False
                        navigate("directory")
                    else:
                        st.error(result.get("detail", "Patient deletion failed."))
            with d_c2:
                if st.button("Cancel Deletion", width="stretch"):
                    st.session_state["confirm_delete"] = False
                    st.rerun()


# -----------------------------------------------------------------------------
# View 4: Visit Record
# -----------------------------------------------------------------------------
elif st.session_state["patient_view"] == "visit":
    patient_id = st.session_state.get("selected_patient_id")
    if not patient_id: navigate("directory")
    
    patient = api_client.get_patient(patient_id)
    
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.markdown(f"### Record Clinical Visit: {patient['first_name']} {patient['last_name']}")
    with c2:
        if st.button("Cancel"):
            navigate("profile", patient_id)
            
    with st.form("visit_form"):
        st.markdown("#### Clinical Notes")
        c1, c2 = st.columns(2)
        with c1:
            visit_date = st.date_input("Visit Date *", value=datetime.date.today(), max_value=datetime.date.today())
        with c2:
            vtype = st.selectbox("Visit Type", ["Initial Consultation", "Follow-up", "Emergency", "Routine Checkup"])
            
        complaint = st.text_area("Chief Complaint *", placeholder="Patient describes...", height=100)
        history = st.text_area("History of Presenting Illness", placeholder="Details of the complaint...")
        
        c3, c4 = st.columns(2)
        with c3:
            v_bp = st.text_input("BP (mmHg)", placeholder="120/80")
            v_hr = st.text_input("HR (bpm)", placeholder="72")
        with c4:
            v_temp = st.text_input("Temp (°C)", placeholder="37.2")
            v_spo2 = st.text_input("SpO2 (%)", placeholder="98")
            
        st.markdown("#### 🤖 AI Diagnosis Suggestions")
        st.info("💡 Generate AI suggestions based on vitals and symptoms.")
        if st.form_submit_button("🔄 Generate AI Suggestions"):
             st.success("AI Suggestions will appear here once linked.")
        
        st.markdown("#### Treatment & Plan")
        diagnosis = st.text_area("Doctor's Diagnosis", placeholder="Enter diagnosis (Leave blank to auto-generate AI suggestions upon save)")
        
        # PM39: Multi-select medications
        common_meds = [
            "Paracetamol 500mg", "Amoxicillin 500mg", "Ibuprofen 400mg", 
            "Artemether-Lumefantrine", "ORS (Oral Rehydration Salts)", 
            "Ciprofloxacin 500mg", "Metronidazole 400mg"
        ]
        selected_meds = st.multiselect("Prescribed Medications", common_meds)
        custom_meds = st.text_input("Additional Medications / Dosage Instructions", placeholder="E.g., Paracetamol 2 tabs BD x 5 days")
        
        tests = st.text_area("Recommended Tests")
        
        c3, c4 = st.columns(2)
        with c3:
            referral = st.text_area("Referral Recommendations", placeholder="E.g., Refer to district hospital")
        with c4:
            dr_notes = st.text_area("Doctor's Notes", placeholder="Internal remarks...")
            
        next_visit = st.date_input("Schedule Next Visit", min_value=datetime.date.today(), value=None)
        
        c5, c6 = st.columns(2)
        with c5:
            submitted = st.form_submit_button("Save Visit Record", type="primary", width="stretch")
        with c6:
            print_requested = st.form_submit_button("Print Prescription", width="stretch")
            
        if submitted or print_requested:
            if not complaint:
                st.error("Chief Complaint is required.")
            else:
                examination = "; ".join(
                    part for part in (
                        f"BP: {v_bp}" if v_bp else "",
                        f"HR: {v_hr}" if v_hr else "",
                        f"Temp: {v_temp}" if v_temp else "",
                        f"SpO2: {v_spo2}" if v_spo2 else "",
                    ) if part
                )
                payload = {
                    "visit_date": visit_date.isoformat(),
                    "visit_type": vtype,
                    "chief_complaint": complaint,
                    "history": history,
                    "examination": examination,
                    "diagnosis": diagnosis,
                    "medications": ", ".join(selected_meds) + (" | " + custom_meds if custom_meds else ""),
                    "tests": tests,
                    "referral": referral,
                    "notes": dr_notes,
                    "next_visit": next_visit.isoformat() if next_visit else None
                }
                
                with st.spinner("Saving record & running AI analysis..."):
                    res = api_client.create_visit(patient_id, payload)
                    
                if res.get("success"):
                    st.success("Visit recorded successfully!")
                    if print_requested:
                        pdf_bytes, pdf_name = api_client.download_prescription_pdf(res.get("visit_id"))
                        if pdf_bytes:
                            st.download_button("Download Prescription PDF", pdf_bytes, pdf_name.split("filename=")[-1].strip('"'), "application/pdf", width="stretch")
                        else:
                            st.error(f"Prescription export unavailable: {pdf_name}")
                    else:
                        st.balloons()
                        navigate("profile", patient_id)
                else:
                    st.error(f"Failed to record visit: {res.get('detail')}")
