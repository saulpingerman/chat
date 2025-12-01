"""
Authentication UI components for CHAT.
"""
import streamlit as st
from chat.auth.jwt_auth import get_auth_provider


def show_login_form():
    """Display the login form."""
    st.markdown("### Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                return

            auth = get_auth_provider()
            result = auth.authenticate(username, password)

            if result.success:
                st.session_state["authenticated"] = True
                st.session_state["user"] = result.user
                st.session_state["token"] = result.token
                st.rerun()
            else:
                st.error(result.error)


def show_register_form():
    """Display the registration form."""
    st.markdown("### Create Account")

    with st.form("register_form"):
        username = st.text_input("Username", help="At least 3 characters")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password", help="At least 8 characters")
        password_confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            if password != password_confirm:
                st.error("Passwords do not match")
                return

            auth = get_auth_provider()
            result = auth.register(username, email, password)

            if result.success:
                st.session_state["authenticated"] = True
                st.session_state["user"] = result.user
                st.session_state["token"] = result.token
                st.success("Account created successfully!")
                st.rerun()
            else:
                st.error(result.error)


def show_auth_page():
    """Display the authentication page with login/register tabs."""
    st.title("CHAT")
    st.markdown("Cloud-Hosted AI Terminal")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            show_login_form()

        with tab2:
            show_register_form()


def logout():
    """Log out the current user."""
    for key in ["authenticated", "user", "token", "current_conversation"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def check_auth() -> bool:
    """Check if user is authenticated."""
    if not st.session_state.get("authenticated"):
        return False

    # Validate token is still valid
    token = st.session_state.get("token")
    if token:
        auth = get_auth_provider()
        user = auth.validate_token(token)
        if user:
            st.session_state["user"] = user
            return True

    # Token invalid, clear session
    logout()
    return False
