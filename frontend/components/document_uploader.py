"""Document upload & analysis component."""

import streamlit as st
from utils import api_client


def render_document_uploader():
    st.markdown("#### Upload a Medical Report or Prescription")
    st.caption("Upload a supported file for local extraction, RAG indexing, and model analysis.")

    uploaded_file = st.file_uploader(
        "Upload a document or image",
        type=["png", "jpg", "jpeg", "pdf", "docx", "txt"],
    )

    if uploaded_file is not None:
        st.success(f"Received: {uploaded_file.name} ({uploaded_file.size} bytes)")

        if st.button("🔍 Analyze Document"):
            with st.status("Processing document...", expanded=True) as status:
                st.write("Extracting text and indexing the document...")
                result = api_client.upload_document(uploaded_file.getvalue(), uploaded_file.name)
                if result.get("status") == "processing":
                    st.write("Waiting for document processing...")
                    result = api_client.analyze_document(uploaded_file.name)
                if result.get("analysis") or result.get("extracted_text_preview"):
                    status.update(label="Analysis complete", state="complete")
                else:
                    status.update(label="Analysis unavailable", state="error")
                    st.error(result.get("detail") or result.get("message", "Document processing failed."))
                    return

            st.markdown("**Extracted Text**")
            extracted = result.get("extracted_text_preview", result.get("extracted_text", ""))
            st.text_area(
                "Extracted Text", value=extracted, height=120,
                label_visibility="collapsed",
            )

            st.markdown("**AI Interpretation**")
            st.markdown(
                f'<div class="bubble assistant">{result.get("analysis", "No analysis available.")}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Source"):
                st.write(result.get("filename", result.get("source", "Unknown")))
