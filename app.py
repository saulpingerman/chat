"""
CHAT - Cloud-Hosted AI Terminal
Main Streamlit application entry point.
"""
import streamlit as st

# Must be first Streamlit command
st.set_page_config(
    page_title="CHAT",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

from chat.db.models import init_database
from chat.ui.styles import apply_styles
from chat.ui.auth_page import show_auth_page, check_auth
from chat.ui.chat_page import show_chat_page
from chat.ui.sidebar import show_sidebar


def main():
    """Main application entry point."""
    # Initialize database
    init_database()

    # Apply custom styles
    apply_styles()

    # Check authentication (checks session state and query params)
    if not check_auth():
        show_auth_page()
        return

    # Show main app
    show_sidebar()
    show_chat_page()


if __name__ == "__main__":
    main()
