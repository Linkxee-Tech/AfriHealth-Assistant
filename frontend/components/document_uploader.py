"""Document upload & analysis component."""

import streamlit as st
from utils import api_client


def render_document_uploader():
    st.markdown("#### Upload a Medical Report or Prescription")
    st.caption(
        "Offline OCR + AI interpretation. Currently a UI stub — OCR extraction "
        "(easyOCR) and RAG interpretation activate once the backend is connected."
    )

    uploaded_file = st.file_uploader(
        "Upload a document or image",
        type=["png", "jpg", "jpeg", "pdf", "docx", "txt"],
    )

    if uploaded_file is not None:
        st.success(f"Received: {uploaded_file.name} ({uploaded_file.size} bytes)")

        if st.button("🔍 Analyze Document"):
            with st.status("Processing document...", expanded=True) as status:
                st.write("Extracting text (OCR)...")
                result = api_client.analyze_document_stub(uploaded_file.name)
                st.write("Running AI interpretation...")
                status.update(label="Analysis complete", state="complete")

            st.markdown("**Extracted Text**")
            st.text_area(
                "Extracted Text", value=result["extracted_text"], height=120,
                label_visibility="collapsed",
            )

            st.markdown("**AI Interpretation**")
            st.markdown(
                f'<div class="bubble assistant">{result["analysis"]}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Source"):
                st.write(result["source"])
