"""
AfriHealth Assistant - Guided Symptom Checker
Step-by-step triage flow that collects patient info and returns an AI assessment.
"""
import streamlit as st
import config
from components.custom_styles import inject_custom_css
from components.sidebar import render_sidebar
from utils import api_client
from utils.session_state import get_theme_colors, init_session_state

st.set_page_config(page_title=f"Symptom Checker - {config.APP_NAME}", page_icon="🔬", layout="wide")
init_session_state()
inject_custom_css(get_theme_colors())

if not st.session_state.get("access_token"):
    st.info("Please login to access the application.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

render_sidebar()

st.markdown("<div class='app-title'>🔬 Symptom Checker</div>", unsafe_allow_html=True)
st.markdown("<div class='app-version'>Guided triage to help assess your symptoms</div><hr>", unsafe_allow_html=True)

st.info("⚠️ This symptom checker is for informational purposes only and does NOT replace a professional medical diagnosis. Always consult a qualified healthcare provider.")

# Session state for checker flow
if "sc_session_id" not in st.session_state:
    st.session_state.sc_session_id = None
if "sc_step" not in st.session_state:
    st.session_state.sc_step = 0
if "sc_total" not in st.session_state:
    st.session_state.sc_total = 7
if "sc_current_q" not in st.session_state:
    st.session_state.sc_current_q = None
if "sc_complete" not in st.session_state:
    st.session_state.sc_complete = False
if "sc_assessment" not in st.session_state:
    st.session_state.sc_assessment = None

def reset_checker():
    st.session_state.sc_session_id = None
    st.session_state.sc_step = 0
    st.session_state.sc_current_q = None
    st.session_state.sc_complete = False
    st.session_state.sc_assessment = None

# Start screen
if st.session_state.sc_session_id is None and not st.session_state.sc_complete:
    st.markdown("### How it works")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Step 1** 📝\n\nAnswer a few simple questions about your symptoms")
    with col2:
        st.markdown("**Step 2** 🤖\n\nOur AI analyses your responses using WHO guidelines")
    with col3:
        st.markdown("**Step 3** 📋\n\nGet a triage assessment with recommended next steps")
    st.markdown("---")
    language = st.selectbox("Select your language", config.LANGUAGES, key="sc_language")
    if st.button("🚀 Start Symptom Check", type="primary"):
        with st.spinner("Starting session..."):
            result = api_client.start_symptom_checker(language)
        if result.get("session_id"):
            st.session_state.sc_session_id = result["session_id"]
            st.session_state.sc_step = result.get("step", 1)
            st.session_state.sc_total = result.get("total_steps", 7)
            st.session_state.sc_current_q = result
            st.rerun()
        else:
            st.error(result.get("detail", "Failed to start session"))

# Question flow
elif st.session_state.sc_current_q and not st.session_state.sc_complete:
    q = st.session_state.sc_current_q
    progress = st.session_state.sc_step / st.session_state.sc_total
    st.progress(progress, text=f"Step {st.session_state.sc_step} of {st.session_state.sc_total}")
    st.markdown(f"### {q.get('question', '')}")

    answer = None
    q_type = q.get("type", "text")
    options = q.get("options")
    placeholder = q.get("placeholder", "Enter your answer")

    if q_type == "choice" and options:
        answer = st.radio("Select one:", options, key=f"sc_radio_{q.get('question_id')}")
    elif q_type == "number":
        val = st.number_input(placeholder, min_value=0, max_value=120, step=1, key=f"sc_num_{q.get('question_id')}")
        answer = str(int(val)) if val else None
    else:
        answer = st.text_area(placeholder, height=100, key=f"sc_text_{q.get('question_id')}")

    col_back, col_next = st.columns([1, 4])
    with col_back:
        if st.button("← Back") and st.session_state.sc_step > 1:
            reset_checker()
            st.rerun()
    with col_next:
        if st.button("Next →", type="primary", disabled=not answer):
            with st.spinner("Processing..."):
                result = api_client.answer_symptom_checker(
                    session_id=st.session_state.sc_session_id,
                    question_id=q.get("question_id"),
                    answer=str(answer),
                )
            if result.get("complete"):
                st.session_state.sc_complete = True
                # Fetch the assessment
                with st.spinner("Generating your health assessment... this may take a moment."):
                    assessment = api_client.get_symptom_result(st.session_state.sc_session_id)
                st.session_state.sc_assessment = assessment
            else:
                st.session_state.sc_step = result.get("step", st.session_state.sc_step + 1)
                st.session_state.sc_current_q = result
            st.rerun()

# Results screen
elif st.session_state.sc_complete and st.session_state.sc_assessment:
    assessment = st.session_state.sc_assessment
    st.success("✅ Assessment Complete")
    st.markdown("### Your Health Assessment")
    st.markdown(assessment.get("assessment", "Assessment not available"))
    st.markdown("---")
    st.warning(assessment.get("disclaimer", "This is not a medical diagnosis."))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Start New Check", type="primary"):
            reset_checker()
            st.rerun()
    with col2:
        if st.button("💬 Discuss with AI Assistant"):
            symptoms = assessment.get("answers", {}).get("symptoms", "")
            if symptoms:
                st.session_state["quick_query"] = f"I have these symptoms: {symptoms}. What should I do?"
            st.switch_page("pages/1_💬_Chat.py")
