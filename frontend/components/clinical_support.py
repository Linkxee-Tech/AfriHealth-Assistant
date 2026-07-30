"""Reusable clinical-support widgets backed by the authenticated API."""

import streamlit as st


def render_reference_tools(api_client):
    """Render guideline, drug, vaccination, and calculator tools."""
    g1, g2 = st.tabs(["Guidelines & Drugs", "Calculators & Vaccines"])
    with g1:
        query = st.text_input("Search guidelines or drugs", key="clinical_reference_query")
        if st.button("Search Reference Library", key="clinical_reference_search"):
            st.session_state["clinical_guidelines"] = api_client.get_guidelines(query=query)
            st.session_state["clinical_drugs"] = api_client.search_drugs(query)
        for item in (st.session_state.get("clinical_guidelines") or []):
            with st.expander(f"{item.get('title', 'Guideline')} — {item.get('category', '')}"):
                st.write(item.get("content", ""))
                st.caption(f"Source: {item.get('source', 'Official reference not specified')}")
                if item.get("id") and st.button("Prepare guideline PDF", key=f"guideline_pdf_{item['id']}"):
                    pdf, name = api_client.download_guideline_pdf(item["id"])
                    if pdf:
                        st.download_button("Download guideline PDF", pdf, name.split("filename=")[-1].strip('"'), "application/pdf", key=f"guideline_download_{item['id']}")
                    else:
                        st.error(name)
        for item in (st.session_state.get("clinical_drugs") or []):
            with st.expander(f"{item.get('name', '').title()} — {item.get('category', '')}"):
                st.write(f"Dose information: {item.get('dosage_info', '')}")
                st.write(f"Side effects: {item.get('side_effects', '')}")
                st.write(f"Contraindications: {item.get('contraindications', '')}")
    with g2:
        c1, c2 = st.columns(2)
        with c1:
            height = st.number_input("Height (cm)", min_value=1.0, value=170.0, key="clinical_bmi_height")
            weight = st.number_input("Weight (kg)", min_value=1.0, value=70.0, key="clinical_bmi_weight")
            if st.button("Calculate BMI", key="clinical_bmi_button"):
                st.session_state["clinical_bmi"] = api_client.calculate_bmi(height, weight)
            if st.session_state.get("clinical_bmi"):
                st.json(st.session_state["clinical_bmi"])
        with c2:
            age = st.number_input("Age (years)", min_value=1, max_value=120, value=30, key="clinical_egfr_age")
            creatinine = st.number_input("Creatinine (mg/dL)", min_value=0.01, value=1.0, key="clinical_egfr_creatinine")
            sex = st.selectbox("Sex", ["female", "male"], key="clinical_egfr_sex")
            if st.button("Calculate eGFR", key="clinical_egfr_button"):
                st.session_state["clinical_egfr"] = api_client.calculate_egfr(creatinine, age, sex)
            if st.session_state.get("clinical_egfr"):
                st.json(st.session_state["clinical_egfr"])
        vaccine_age = st.number_input("Age for vaccination schedule", min_value=0.0, max_value=120.0, value=0.0, key="clinical_vaccine_age")
        if st.button("Show vaccination schedule", key="clinical_vaccine_button"):
            st.session_state["clinical_vaccine"] = api_client.get_vaccination_schedule(vaccine_age)
        for item in st.session_state.get("clinical_vaccine", {}).get("schedule", []):
            st.write(f"**{item['vaccine']}** — {item['timing']} ({item['status']})")
        st.caption("Schedules are reference aids. Confirm the current national immunisation schedule with a qualified health worker.")
