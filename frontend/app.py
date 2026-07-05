"""
AfriHealth Assistant - Landing Page (Entry Point)
"""
import os
import base64
import streamlit as st
import config
from utils import api_client
from utils.session_state import init_session_state, get_theme_colors
from components.custom_styles import inject_custom_css

st.set_page_config(
    page_title=f"Welcome — {config.APP_NAME}", 
    page_icon="🩺", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

init_session_state()
inject_custom_css(get_theme_colors())

# Base64 encode the background image
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

theme = st.session_state.get("theme", "Dark")
bg_file = "background_light.png" if theme == "Light" else "background.png"
bg_path = os.path.join(os.path.dirname(__file__), "assets", "images", bg_file)
if not os.path.exists(bg_path):
    bg_path = os.path.join(os.path.dirname(__file__), "assets", "images", "background.png")
if os.path.exists(bg_path):
    bg_ext = "png"
    bg_base64 = get_base64_of_bin_file(bg_path)
    bg_css = f"""
        .stApp {{
            background-image: url("data:image/{bg_ext};base64,{bg_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
    """
else:
    bg_css = ""

# Custom CSS to hide sidebar on the landing page, center everything, and set background
st.markdown(f"""
    <style>
        [data-testid="collapsedControl"] {{ display: none; }}
        section[data-testid="stSidebar"] {{ display: none; }}
        .block-container {{ padding-top: 3rem; max-width: 600px; }}
        {bg_css}
        
        /* Ensure the login container is semi-transparent to show the background */
        div[data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
        }}
        div.stTabs [data-baseweb="tab-list"] {{
            background-color: transparent !important;
        }}
    </style>
""", unsafe_allow_html=True)


def main():
    if st.session_state.get("access_token"):
        st.switch_page("pages/1_💬_Chat.py")
        return

    # Logo
    logo_file = "logo_light.png" if st.session_state.get("theme", "Dark") == "Light" else "logo.png"
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "images", logo_file)
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown(f"<h1 style='text-align: center; color: var(--text);'>{config.APP_NAME}</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: var(--secondary_grey); font-size: 1.1rem; margin-bottom: 2rem;'>Intelligent Healthcare, Offline. For Africa.</p>", unsafe_allow_html=True)

    # Glassmorphic login card
    with st.container(border=True):
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form", border=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Access Portal", use_container_width=True)
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        with st.spinner("Authenticating..."):
                            result = api_client.login(username, password)
                        if "access_token" in result:
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["username"] = username
                            st.switch_page("pages/1_💬_Chat.py")
                        else:
                            st.error(result.get("detail", "Login failed"))
                            
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form", border=False):
                new_username = st.text_input("Choose Username", placeholder="Create a unique username")
                new_password = st.text_input("Choose Password", type="password", placeholder="Create a secure password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-type password")
                register_submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if register_submitted:
                    if not new_username or not new_password:
                        st.error("Please fill all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        with st.spinner("Creating account..."):
                            result = api_client.register(new_username, new_password)
                        if "access_token" in result:
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["username"] = new_username
                            st.switch_page("pages/1_💬_Chat.py")
                        else:
                            st.error(result.get("detail", "Registration failed"))

if __name__ == "__main__":
    main()
