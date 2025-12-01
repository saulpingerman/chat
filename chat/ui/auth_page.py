"""
Authentication UI components for CHAT.
Uses query parameters to persist login across page refreshes.
"""
import streamlit as st
from chat.auth.jwt_auth import get_auth_provider


def show_login_form():
    """Display the login form."""
    st.markdown("### Login")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", use_container_width=True, key="login_btn"):
        if not username or not password:
            st.error("Please enter both username and password")
            return

        auth = get_auth_provider()
        result = auth.authenticate(username, password)

        if result.success:
            st.session_state["authenticated"] = True
            st.session_state["user"] = result.user
            st.session_state["token"] = result.token
            # Save token to query params for persistence across refreshes
            st.query_params["token"] = result.token
            st.rerun()
        else:
            st.error(result.error)


def show_register_form():
    """Display the registration form."""
    st.markdown("### Create Account")

    username = st.text_input("Username", key="reg_username", help="At least 3 characters")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_password", help="At least 8 characters")
    password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")

    if st.button("Create Account", use_container_width=True, key="register_btn"):
        if password != password_confirm:
            st.error("Passwords do not match")
            return

        auth = get_auth_provider()
        result = auth.register(username, email, password)

        if result.success:
            st.session_state["authenticated"] = True
            st.session_state["user"] = result.user
            st.session_state["token"] = result.token
            # Save token to query params for persistence across refreshes
            st.query_params["token"] = result.token
            st.success("Account created successfully!")
            st.rerun()
        else:
            st.error(result.error)


def show_auth_page():
    """Display the authentication page with login/register tabs."""
    st.title("CHAT")
    st.markdown("Cloud-Hosted AI Terminal")

    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            show_login_form()

        with tab2:
            show_register_form()


def logout():
    """Log out the current user."""
    # Clear query params
    st.query_params.clear()

    for key in ["authenticated", "user", "token", "current_conversation", "messages"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def check_auth() -> bool:
    """Check if user is authenticated."""
    # First check session state
    if st.session_state.get("authenticated"):
        token = st.session_state.get("token")
        if token:
            auth = get_auth_provider()
            user = auth.validate_token(token)
            if user:
                st.session_state["user"] = user
                return True

    # If not in session, try to restore from query params
    token = st.query_params.get("token")
    if token:
        auth = get_auth_provider()
        user = auth.validate_token(token)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user
            st.session_state["token"] = token
            return True

    # Not authenticated
    return False
