import json
import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"Documents — {config.APP_NAME}", page_icon="📁", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown(f"<div class='app-title'>📁 Document Analysis</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("### 📤 Upload Document for AI Analysis")
uploaded_file = st.file_uploader(
    "📂 Drag & Drop Your File Here (Supported: PDF, DOCX, TXT, JPG, PNG)", 
    type=["pdf", "docx", "txt", "png", "jpg"],
    label_visibility="collapsed"
)

if uploaded_file and st.button("Process Document", width="stretch"):
    with st.status(f"🔄 Processing... {uploaded_file.name}", expanded=True) as status:
        st.write("Extracting text and running OCR...")
        result = api_client.upload_document(uploaded_file.getvalue(), uploaded_file.name)
        
        if "status" in result and result["status"] == "processing":
            import time
            time.sleep(2)
            st.write("Running AI interpretation...")
            analysis_result = api_client.analyze_document(uploaded_file.name)
            status.update(label="Analysis Complete!", state="complete", expanded=False)
            st.session_state["last_doc_result"] = analysis_result
        elif "status" in result and result["status"] == "success":
             status.update(label="Analysis Complete!", state="complete", expanded=False)
             st.session_state["last_doc_result"] = result
        else:
            status.update(label="Error processing document", state="error")
            st.error(result.get("detail", "Unknown error"))

st.markdown("<br>", unsafe_allow_html=True)

doc_result = st.session_state.get("last_doc_result")

if doc_result:
    st.markdown("### 📄 Extracted Text")
    extracted = doc_result.get("extracted_text_preview", doc_result.get("extracted_text", ""))
    st.markdown(f"""
    <div class='status-card' style='font-family: "Open Sans", sans-serif; white-space: pre-wrap; font-size: 0.95rem;'>
{extracted if extracted else 'No raw text available.'}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 🤖 AI Analysis")
    st.markdown(f"""
    <div class='status-card'>
{doc_result.get("analysis", "No analysis available.")}
<br><br>
<span style='color: #8892B0; font-size: 0.85rem;'>📚 Source: {doc_result.get('filename', doc_result.get('source', 'Unknown'))}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, _ = st.columns([2, 2, 8])
    with col1:
        st.download_button(
            "📥 Download Analysis Report",
            data=json.dumps(doc_result, indent=2),
            file_name=f"{doc_result.get('filename', 'document')}.analysis.json",
            mime="application/json",
            width="stretch",
        )
    with col2:
        if st.button("🗑️ Clear", width="stretch"):
            st.session_state.pop("last_doc_result", None)
            st.rerun()
