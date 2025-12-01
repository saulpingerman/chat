"""
Sidebar UI components for CHAT.
Handles conversation management and user info display.
"""
import streamlit as st
from typing import Optional

from chat.config import (
    get_config, APP_NAME, APP_FULL_NAME, APP_VERSION,
    AUTHOR_NAME, AUTHOR_EMAIL,
    COST_PER_1M_INPUT_TOKENS, COST_PER_1M_OUTPUT_TOKENS
)
from chat.db.models import (
    get_user_conversations, create_conversation, delete_conversation,
    update_conversation, get_conversation, get_user_by_id
)
from chat.ui.auth_page import logout


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate the cost based on token usage."""
    input_cost = (input_tokens / 1_000_000) * COST_PER_1M_INPUT_TOKENS
    output_cost = (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT_TOKENS
    return input_cost + output_cost


def show_sidebar():
    """Display the sidebar with conversation management and user info."""
    user = st.session_state.get("user")
    if not user:
        return

    with st.sidebar:
        # App header
        st.markdown(
            f'<div style="text-align: center; width: 100%; margin-top: -1rem;">'
            f'<div style="font-size: 3rem; font-weight: 900; letter-spacing: 0.3rem;">{APP_NAME}</div>'
            f'<div style="font-size: 0.85rem; color: #888; margin-top: -0.5rem;">{APP_FULL_NAME}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="text-align: center; font-size: 0.8rem; color: #888; margin-bottom: 1rem;">'
            f'Created by: {AUTHOR_NAME}<br/>'
            f'<a href="mailto:{AUTHOR_EMAIL}" style="color: #888;">{AUTHOR_EMAIL}</a>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.divider()

        # New chat button
        if st.button("+ New Chat", use_container_width=True, type="primary"):
            conv = create_conversation(user.id, "New Chat")
            st.session_state["current_conversation"] = conv.id
            st.session_state["messages"] = []
            st.rerun()

        st.divider()

        # Saved conversations section
        st.markdown("### Saved Conversations")
        saved_convs = get_user_conversations(user.id, saved_only=True)

        if saved_convs:
            for conv in saved_convs[:10]:  # Show last 10
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"💬 {conv.title[:25]}..." if len(conv.title) > 25 else f"💬 {conv.title}",
                        key=f"conv_{conv.id}",
                        use_container_width=True
                    ):
                        load_conversation(conv.id)
                with col2:
                    if st.button("🗑️", key=f"del_{conv.id}", help="Delete conversation"):
                        delete_conversation(conv.id)
                        if st.session_state.get("current_conversation") == conv.id:
                            st.session_state["current_conversation"] = None
                            st.session_state["messages"] = []
                        st.rerun()
        else:
            st.caption("No saved conversations yet")

        st.divider()

        # Current conversation actions
        current_conv_id = st.session_state.get("current_conversation")
        if current_conv_id:
            current_conv = get_conversation(current_conv_id)
            if current_conv:
                st.markdown("### Current Chat")

                # Save/unsave button
                if current_conv.is_saved:
                    if st.button("📌 Saved", use_container_width=True, help="Click to unsave"):
                        update_conversation(current_conv_id, is_saved=False)
                        st.rerun()
                else:
                    if st.button("💾 Save Chat", use_container_width=True):
                        update_conversation(current_conv_id, is_saved=True)
                        st.success("Chat saved!")
                        st.rerun()

                # Rename conversation
                with st.expander("Rename"):
                    new_title = st.text_input("Title", value=current_conv.title, key="rename_input")
                    if st.button("Update", key="rename_btn"):
                        update_conversation(current_conv_id, title=new_title)
                        st.rerun()

                st.divider()

        # Token usage section
        st.markdown("### Usage Stats")
        show_token_stats(user.id, current_conv_id)

        st.divider()

        # Environment info
        config = get_config()
        st.markdown("### Backend")
        st.caption(f"🔗 {config.display_name}")
        st.caption(f"🤖 Claude Sonnet 4.5")
        st.caption(f"📦 v{APP_VERSION}")

        st.divider()

        # User info and logout
        st.markdown(f"### 👤 {user.username}")
        if st.button("Logout", use_container_width=True):
            logout()


def show_token_stats(user_id: str, conversation_id: Optional[str]):
    """Display token usage statistics."""
    # Get fresh user data
    user = get_user_by_id(user_id)
    if not user:
        return

    # Current conversation stats
    if conversation_id:
        conv = get_conversation(conversation_id)
        if conv:
            conv_cost = calculate_cost(conv.input_tokens, conv.output_tokens)
            st.markdown("**This chat:**")
            st.caption(f"📥 {conv.input_tokens:,} input tokens")
            st.caption(f"📤 {conv.output_tokens:,} output tokens")
            st.caption(f"💰 ${conv_cost:.4f}")

    # Total user stats
    total_cost = calculate_cost(user.total_input_tokens, user.total_output_tokens)
    st.markdown("**All time:**")
    st.caption(f"📥 {user.total_input_tokens:,} input tokens")
    st.caption(f"📤 {user.total_output_tokens:,} output tokens")
    st.caption(f"💰 ${total_cost:.4f}")


def load_conversation(conversation_id: str):
    """Load a conversation into the current session."""
    from chat.db.models import get_conversation_messages
    import json

    st.session_state["current_conversation"] = conversation_id
    messages = get_conversation_messages(conversation_id)

    # Convert to display format
    display_messages = []
    for msg in messages:
        content = json.loads(msg.content)
        # Extract text from content blocks
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, dict) and "text" in block:
                text_parts.append(block.get("text", ""))

        display_messages.append({
            "role": msg.role,
            "content": "\n".join(text_parts) if text_parts else str(content)
        })

    st.session_state["messages"] = display_messages
    st.rerun()
