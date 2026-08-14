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
        div[data-testid="stImageContainer"] {{
            max-width: 50%;
            width: 50%;
            margin: 0 auto 1rem auto;
            display: block;
        }}
        div[data-testid="stImageContainer"] img {{
            display: block;
            width: 100%;
            height: auto;
            margin: 0 auto;
        }}
    </style>
""", unsafe_allow_html=True)


def main():
    login_notice = st.session_state.pop("login_notice", None)
    if login_notice:
        st.success(login_notice)

    if st.session_state.get("access_token"):
        st.switch_page("pages/1_💬_Chat.py")
        return

    # Logo
    logo_file = "logo_light.png" if st.session_state.get("theme", "Dark") == "Light" else "logo.png"
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "images", logo_file)
    if os.path.exists(logo_path):
        st.image(logo_path, width="stretch")
    else:
        st.markdown(f"<h1 style='text-align: center; color: var(--text);'>{config.APP_NAME}</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: var(--secondary_grey); font-size: 1.1rem; margin-bottom: 2rem;'>Intelligent Healthcare, Offline. For Africa.</p>", unsafe_allow_html=True)

    # Glassmorphic login card
    with st.container(border=True):
        tab1, tab2, tab3, tab4 = st.tabs(["Login", "Register", "Forgot password", "Admin Login"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form", border=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Access Portal", width="stretch")
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        with st.spinner("Authenticating..."):
                            result = api_client.login(username, password)
                        if "access_token" in result:
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["username"] = username
                            profile = api_client.get_me()
                            st.session_state["is_admin"] = profile.get("is_admin", False)
                            if profile.get("is_admin"):
                                st.switch_page("pages/12_📈_Admin.py")
                            else:
                                st.switch_page("pages/1_💬_Chat.py")
                        else:
                            st.error(result.get("detail", "Login failed"))
                
                st.markdown("<div style='text-align: center; color: var(--text-secondary, #888); font-size: 0.8rem; margin-top: 10px;'>💡 Hint: Remember your login <b>password</b></div>", unsafe_allow_html=True)
                            
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form", border=False):
                new_username = st.text_input("Choose Username", placeholder="Create a unique username")
                new_email = st.text_input("Recovery Email (optional)", placeholder="you@example.com")
                new_password = st.text_input("Choose Password", type="password", placeholder="Create a secure password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-type password")
                register_submitted = st.form_submit_button("Create Account", width="stretch")
                
                if register_submitted:
                    if not new_username or not new_password:
                        st.error("Please fill all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        with st.spinner("Creating account..."):
                            result = api_client.register(new_username, new_password, new_email)
                        if "access_token" in result:
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["username"] = new_username
                            profile = api_client.get_me()
                            st.session_state["is_admin"] = profile.get("is_admin", False)
                            if profile.get("is_admin"):
                                st.switch_page("pages/12_📈_Admin.py")
                            else:
                                st.switch_page("pages/1_💬_Chat.py")
                        else:
                            st.error(result.get("detail", "Registration failed"))

        with tab3:
            st.markdown("Use your username for offline recovery, or your registered email when SMTP is configured.")
            with st.form("forgot_password_form", border=False):
                recovery_username = st.text_input("Username (local recovery)")
                recovery_email = st.text_input("Email (email recovery)")
                forgot_submitted = st.form_submit_button("Prepare Recovery", width="stretch")
                if forgot_submitted:
                    if not recovery_username.strip() and not recovery_email.strip():
                        st.error("Enter a username or email.")
                    else:
                        result = api_client.request_password_reset(recovery_username, recovery_email)
                        if result.get("success"):
                            st.success(result.get("message", "Recovery instructions prepared."))
                            if result.get("recovery_token"):
                                st.code(result["recovery_token"], language="text")
                                st.caption("This local token expires and can be used once. Keep it private.")
                        else:
                            st.error(result.get("detail", "Recovery request failed."))

            with st.form("reset_password_form", border=False):
                reset_token = st.text_input("Recovery token")
                reset_new_password = st.text_input("New password", type="password")
                reset_confirm = st.text_input("Confirm new password", type="password")
                reset_submitted = st.form_submit_button("Reset Password", width="stretch")
                if reset_submitted:
                    if reset_new_password != reset_confirm:
                        st.error("Passwords do not match.")
                    elif not reset_token or len(reset_new_password) < 8:
                        st.error("Enter a valid token and a password of at least 8 characters.")
                    else:
                        result = api_client.reset_password(reset_token, reset_new_password)
                        if result.get("success"):
                            st.session_state.pop("access_token", None)
                            st.session_state.pop("username", None)
                            st.session_state["login_notice"] = result.get(
                                "message", "Password reset successfully. You can now sign in."
                            )
                            st.rerun()
                        else:
                            st.error(result.get("detail", "Password reset failed."))

        with tab4:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("admin_login_form", border=False):
                admin_username = st.text_input("Admin Username", placeholder="Enter admin username")
                admin_password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
                admin_submitted = st.form_submit_button("Access Admin Panel", width="stretch")
                
                st.markdown("<div style='text-align: center; color: var(--text-secondary, #888); font-size: 0.8rem; margin-top: 10px;'>💡 Hint: Default Admin Login is <b>admin</b> / <b>adminpassword</b></div>", unsafe_allow_html=True)
                 
                if admin_submitted:
                    if not admin_username or not admin_password:
                        st.error("Please enter username and password")
                    else:
                        with st.spinner("Authenticating Admin..."):
                            result = api_client.login(admin_username, admin_password)
                        if "access_token" in result:
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["username"] = admin_username
                            profile = api_client.get_me()
                            if profile.get("is_admin"):
                                st.session_state["is_admin"] = True
                                st.switch_page("pages/12_📈_Admin.py")
                            else:
                                # Log out and show error
                                st.session_state.pop("access_token", None)
                                st.session_state.pop("username", None)
                                st.error("Access Denied: You do not have administrator privileges.")
                        else:
                             st.error(result.get("detail", "Login failed"))

if __name__ == "__main__":
    main()
