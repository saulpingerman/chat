"""
Main chat UI for CHAT.
"""
import streamlit as st
import json
import base64
from typing import List, Dict, Any, Optional

from chat.config import DEFAULT_SYSTEM_PROMPT, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
from chat.llm_client import create_llm_client, format_message_with_files
from chat.db.models import (
    create_conversation, add_message, update_conversation,
    get_messages_for_api, update_user_tokens, get_conversation
)
from chat.utils.file_handler import process_file, FileProcessingError, get_file_icon


def initialize_chat_state():
    """Initialize chat-related session state."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "current_conversation" not in st.session_state:
        st.session_state["current_conversation"] = None
    if "pending_files" not in st.session_state:
        st.session_state["pending_files"] = []


def display_chat_messages():
    """Display all messages in the chat history."""
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            # Check if there are files attached
            if "files" in message and message["files"]:
                for f in message["files"]:
                    icon = get_file_icon(f.get("type", ""))
                    st.caption(f"{icon} {f.get('name', 'file')}")

            st.markdown(message["content"])


def process_uploaded_files(uploaded_files) -> List[Dict[str, Any]]:
    """Process uploaded files and return formatted file data."""
    processed = []
    for uploaded_file in uploaded_files:
        try:
            file_data = uploaded_file.read()
            file_info = process_file(uploaded_file.name, file_data)
            processed.append(file_info)
        except FileProcessingError as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        except Exception as e:
            st.error(f"Unexpected error with {uploaded_file.name}: {str(e)}")
    return processed


def build_api_message(text: str, files: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build a message in the format expected by the Bedrock API."""
    content = []

    # Add files first
    if files:
        for file in files:
            file_type = file.get("type", "")
            file_data_b64 = file.get("data", "")
            file_name = file.get("name", "file")

            # Decode base64 to bytes for API
            try:
                file_bytes = base64.b64decode(file_data_b64)
            except Exception:
                continue

            if file_type.startswith("image/"):
                # Determine image format
                format_map = {
                    "image/png": "png",
                    "image/jpeg": "jpeg",
                    "image/jpg": "jpeg",
                    "image/gif": "gif",
                    "image/webp": "webp"
                }
                img_format = format_map.get(file_type, "png")
                content.append({
                    "image": {
                        "format": img_format,
                        "source": {
                            "bytes": file_bytes
                        }
                    }
                })
            elif file_type == "application/pdf":
                content.append({
                    "document": {
                        "format": "pdf",
                        "name": file_name.replace(" ", "_")[:100],  # Sanitize name
                        "source": {
                            "bytes": file_bytes
                        }
                    }
                })
            else:
                # Text-based files - include extracted text
                extracted = file.get("extracted_text", "")
                if extracted:
                    content.append({
                        "text": f"[File: {file_name}]\n{extracted}"
                    })

    # Add user's text message
    if text:
        content.append({"text": text})

    return {
        "role": "user",
        "content": content
    }


def get_display_content(api_message: Dict[str, Any]) -> str:
    """Extract displayable text from an API message."""
    content = api_message.get("content", [])
    text_parts = []

    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text" or "text" in block:
                text_parts.append(block.get("text", ""))

    return "\n".join(text_parts)


def show_chat_page():
    """Display the main chat interface."""
    initialize_chat_state()
    user = st.session_state.get("user")

    if not user:
        st.error("Please log in to continue")
        return

    # Ensure we have a conversation
    if not st.session_state.get("current_conversation"):
        conv = create_conversation(user.id, "New Chat")
        st.session_state["current_conversation"] = conv.id

    # File upload dialog state
    if "show_file_upload" not in st.session_state:
        st.session_state["show_file_upload"] = False

    # Show file uploader at top if toggled (before chat messages)
    uploaded_files = None
    if st.session_state.get("show_file_upload"):
        uploaded_files = st.file_uploader(
            "Attach files",
            accept_multiple_files=True,
            type=[ext.lstrip('.') for ext in ALLOWED_EXTENSIONS.keys()],
            help=f"Max {MAX_FILE_SIZE_MB}MB each.",
            key="file_uploader",
            label_visibility="collapsed"
        )
        if uploaded_files:
            file_names = ", ".join([f.name for f in uploaded_files])
            st.caption(f"📎 {file_names}")

    # Display chat messages
    display_chat_messages()

    # CSS for bottom input layout with button next to chat input
    st.markdown(
        """
        <style>
        .st-key-BOTTOM-CONTAINER, .st-key-BUTTONS-CONTAINER {
            display: flex;
            flex-direction: row !important;
            flex-wrap: nowrap;
            gap: 0.5rem;
            align-items: center;
        }
        .st-key-BUTTONS-CONTAINER[data-testid="stVerticalBlock"] div {
            width: max-content !important;
        }
        .st-key-BOTTOM-CONTAINER > div:first-child {
            min-width: max-content;
            max-width: max-content;
        }
        .st-key-BOTTOM-CONTAINER > div:last-child {
            flex-grow: 1;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Use st._bottom to place elements at the bottom like chat_input does
    with st._bottom:
        with st.container(key="BOTTOM-CONTAINER"):
            buttons_container = st.container(key="BUTTONS-CONTAINER")
            input_container = st.container(key="INPUT-CONTAINER")

    # Add attach button to buttons container
    with buttons_container:
        if st.button("📎", key="attach_btn_main", help="Attach files"):
            st.session_state["show_file_upload"] = not st.session_state.get("show_file_upload", False)
            st.rerun()

    # Add chat input to input container
    with input_container:
        prompt = st.chat_input("How can I help you today?")

    # Handle chat input
    if prompt:
        # Process any uploaded files
        processed_files = []
        if uploaded_files:
            processed_files = process_uploaded_files(uploaded_files)

        # Build API message
        api_message = build_api_message(prompt, processed_files)

        # Display user message
        with st.chat_message("user"):
            if processed_files:
                for f in processed_files:
                    icon = get_file_icon(f.get("type", ""))
                    st.caption(f"{icon} {f.get('name', 'file')}")
            st.markdown(prompt)

        # Add to display messages
        st.session_state["messages"].append({
            "role": "user",
            "content": prompt,
            "files": [{"name": f["name"], "type": f["type"]} for f in processed_files]
        })

        # Save user message to database
        conv_id = st.session_state["current_conversation"]
        add_message(conv_id, "user", api_message["content"])

        # Get all messages for API
        all_messages = get_messages_for_api(conv_id)

        # Stream response from Claude
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            input_tokens = 0
            output_tokens = 0

            try:
                client = create_llm_client()

                for chunk in client.stream_message(
                    messages=all_messages,
                    system_prompt=DEFAULT_SYSTEM_PROMPT,
                    max_tokens=4096
                ):
                    if chunk.is_final:
                        input_tokens = chunk.input_tokens
                        output_tokens = chunk.output_tokens
                    else:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")

                # Final display without cursor
                response_placeholder.markdown(full_response)

            except Exception as e:
                full_response = f"Error: {str(e)}"
                response_placeholder.error(full_response)

        # Add assistant message to display
        st.session_state["messages"].append({
            "role": "assistant",
            "content": full_response
        })

        # Save assistant message to database
        add_message(
            conv_id,
            "assistant",
            [{"text": full_response}],
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Update conversation token counts
        update_conversation(
            conv_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Update user's total token usage
        update_user_tokens(user.id, input_tokens, output_tokens)

        # Auto-generate title from first message if still "New Chat"
        conv = get_conversation(conv_id)
        if conv and conv.title == "New Chat" and len(st.session_state["messages"]) >= 2:
            # Use first ~50 chars of first user message as title
            first_msg = st.session_state["messages"][0]["content"]
            new_title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
            update_conversation(conv_id, title=new_title)

        st.rerun()
