"""
Page 6: About

Spec requirements:
  - Project info: st.markdown
  - Team info: st.columns
  - Technology stack: st.badge, st.expander
  - Acknowledgments: st.markdown
  - License: st.code
"""

import streamlit as st
import config
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar

st.set_page_config(
    page_title=f"About — {config.APP_NAME}", page_icon="📖", layout="wide"
)
init_session_state()
inject_custom_css(get_theme_colors())
render_sidebar()

st.markdown(f"### 📖 About {config.APP_NAME}")

# ------------------------------------------------------------------
# Project Info
# ------------------------------------------------------------------
st.markdown(
    f"""
    **{config.APP_TAGLINE}**

    **{config.APP_NAME}** is a 100% offline AI medical assistant built for the
    **ADTC 2026 Challenge**, providing real-time, authoritative medical information,
    preliminary diagnostic suggestions, and medication guidance for African communities
    with limited internet access or scarce medical resources.

    It runs entirely on standard laptop hardware (Intel i5 / Ryzen 5, 8GB RAM, integrated GPU)
    with **zero reliance on cloud APIs**, combining a locally quantised LLM with
    retrieval-augmented generation (RAG) over trusted medical sources (WHO guidelines,
    medical handbooks, MIRIAD dataset).
    """
)

st.markdown("---")

# ------------------------------------------------------------------
# Team Info  (st.columns per spec)
# ------------------------------------------------------------------
st.markdown("#### 👥 Team")
t1, t2 = st.columns(2)
with t1:
    st.markdown("**Frontend & Product**")
    st.markdown(
        "- Streamlit multipage UI  \n"
        "- UX design & interaction flows  \n"
        "- Product testing & feedback  \n"
        "- Demo video & documentation  "
    )
with t2:
    st.markdown("**Backend & AI**")
    st.markdown(
        "- FastAPI backend service  \n"
        "- llama.cpp + 4-bit quantised model  \n"
        "- RAG pipeline (LangChain + ChromaDB)  \n"
        "- Streaming responses & source citation  \n"
        "- Performance profiling & tuning  "
    )

st.markdown("---")

# ------------------------------------------------------------------
# Technology Stack  (st.badge + st.expander per spec)
# ------------------------------------------------------------------
st.markdown("#### 🛠️ Technology Stack")

# st.badge for key technologies (spec requirement)
badge_row = st.columns(7)
badges = [
    ("Streamlit", "green"),
    ("FastAPI", "blue"),
    ("llama.cpp", "orange"),
    ("LangChain", "violet"),
    ("ChromaDB", "red"),
    ("SQLite", "gray"),
    ("easyOCR", "green"),
]
for col, (label, color) in zip(badge_row, badges):
    with col:
        st.badge(label, color=color)

# Detailed breakdowns in expanders (spec requirement)
with st.expander("🖥️ Frontend", expanded=True):
    st.markdown(
        "| Layer | Technology | Purpose |\n"
        "|---|---|---|\n"
        "| UI Framework | **Streamlit 1.58** | Multipage app, rapid iteration |\n"
        "| Data | **Pandas** | Health metric dataframes & charts |\n"
        "| Assets | **Pillow** | Logo & favicon generation |\n"
        "| HTTP | **Requests** | Backend API client (when connected) |\n"
        "| System | **psutil** | Live CPU & RAM monitoring |\n"
        "| DB | **SQLite** (stdlib) | Local chat history & health logs |"
    )

with st.expander("🤖 Backend / AI (in progress)"):
    st.markdown(
        "| Layer | Technology | Purpose |\n"
        "|---|---|---|\n"
        "| API | **FastAPI** | High-performance async REST + streaming |\n"
        "| Inference | **llama.cpp** | 4-bit quantised LLM on CPU |\n"
        "| Model | **Meta Llama-3-8B Q4** | 8B params, ~4–5 GB RAM footprint |\n"
        "| RAG | **LangChain** | Document loading, chunking, retrieval |\n"
        "| Vector DB | **ChromaDB** | Local embeddable vector store |\n"
        "| Embeddings | **all-MiniLM-L6-v2** | Lightweight CPU-capable embeddings |\n"
        "| OCR | **easyOCR** | Offline text extraction from images |\n"
        "| ORM | **SQLAlchemy + Alembic** | Database models & migrations |"
    )

with st.expander("📚 Knowledge Base"):
    st.markdown(
        "- **MIRIAD** dataset — Medical Image Retrieval for clinical decision support\n"
        "- **WHO Guidelines** — PDFs covering malaria, typhoid, nutrition, and primary care\n"
        "- **Local medical handbooks** — adapted for African primary healthcare contexts\n"
        "- **Drug database** — essential medicines list relevant to sub-Saharan Africa"
    )

st.markdown("---")

# ------------------------------------------------------------------
# Acknowledgments  (spec requirement)
# ------------------------------------------------------------------
st.markdown("#### 🙏 Acknowledgments")
st.markdown(
    """
    - **ADTC 2026 Challenge organisers** — for creating a platform to drive AI innovation in Africa.
    - **Meta AI** — for releasing the Llama 3 model weights under an open research licence.
    - **Georgi Gerganov** — for `llama.cpp`, making LLM inference practical on consumer hardware.
    - **LangChain & ChromaDB teams** — for open-source RAG tooling that makes this architecture possible.
    - **WHO & MIRIAD contributors** — for publishing authoritative medical knowledge that powers our knowledge base.
    - **Streamlit team** — for the framework that enables rapid, high-quality Python data apps.
    - **African healthcare workers & community health volunteers** — the real-world inspiration for this project.
    """
)

st.markdown("---")

# ------------------------------------------------------------------
# License  (st.code per spec)
# ------------------------------------------------------------------
st.markdown("#### 📄 License")
st.code(
    "MIT License\n\n"
    f"Copyright (c) 2026 {config.APP_NAME} Team\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software and associated documentation files (the \"Software\"), to deal\n"
    "in the Software without restriction, including without limitation the rights\n"
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
    "copies of the Software, subject to the MIT License conditions.",
    language="text",
)
