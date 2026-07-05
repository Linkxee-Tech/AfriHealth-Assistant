import os
import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(page_title=f"About — {config.APP_NAME}", page_icon="📖", layout="wide")

init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown(f"<div class='app-title'>📖 About AfriHealth Assistant</div>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🌍 AfriHealth Assistant")
    st.markdown("**Intelligent Healthcare, Offline. For Africa.**")
    st.markdown("---")
    
    st.markdown("### 🚀 Strategic Roadmap")
    st.markdown(
        """
        ✅ **Phase 1 (MVP)**: Deliver the core AI consultation experience with offline inference, RAG, document analysis, health metrics, and a polished UI.<br>
        ✅ **Phase 2**: Add multilingual support, OCR, voice, reporting, advanced analytics, and broader clinical tools.<br>
        ✅ **Phase 3**: Expand into a comprehensive offline clinical decision-support platform for healthcare providers and communities.
        """, unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    st.markdown("### 💻 Technology Stack")
    st.markdown(
        """
        - **Frontend**: Streamlit
        - **Backend**: FastAPI
        - **AI Engine**: llama.cpp (Offline Inference)
        - **Knowledge Base**: LangChain + ChromaDB
        - **Database**: SQLite (Local, Private Storage)
        - **Authentication**: JWT Bearer Tokens
        """
    )

with col2:
    theme = st.session_state.get("theme", "Dark")
    logo_file = "logo_light.png" if theme == "Light" else "logo.png"
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "images", logo_file)
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)

    st.markdown("### 👥 The Team")
    st.markdown(
        """
        **Lead Developer / AI Engineer**<br>
        <span style="color:#8892B0; font-size: 0.9rem;">Designing the architecture & building the RAG pipeline.</span>
        
        <br>**Product / Frontend**<br>
        <span style="color:#8892B0; font-size: 0.9rem;">UI/UX Design & Feature Specifications.</span>
        """, unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    st.markdown("### 📝 License")
    st.code(
        """MIT License
Copyright (c) 2026 AfriHealth Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software")...""", 
        language="text"
    )

st.markdown("<br><br><div class='disclaimer'>Built with ❤️ for Africa</div>", unsafe_allow_html=True)
