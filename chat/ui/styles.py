"""
CSS styles for CHAT Streamlit app.
"""

MAIN_CSS = """
<style>
/* Main container styling */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Chat message styling */
.stChatMessage {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
}

/* User message styling */
[data-testid="stChatMessageContent"] {
    font-size: 1rem;
    line-height: 1.6;
}

/* Code block styling in chat */
.stChatMessage pre {
    background-color: #1e1e1e;
    border-radius: 0.5rem;
    padding: 1rem;
    overflow-x: auto;
}

/* Sidebar styling - dark mode compatible */
section[data-testid="stSidebar"] {
    background-color: #262730;
    padding: 1rem;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}

/* Ensure sidebar text is visible in dark mode */
section[data-testid="stSidebar"] * {
    color: inherit;
}

/* Button styling */
.stButton > button {
    width: 100%;
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* File uploader styling */
.stFileUploader {
    border: 2px dashed #ccc;
    border-radius: 0.5rem;
    padding: 1rem;
}

.stFileUploader:hover {
    border-color: #666;
}

/* Token counter styling */
.token-counter {
    background-color: #f0f2f6;
    border-radius: 0.5rem;
    padding: 0.75rem;
    font-size: 0.85rem;
    margin-top: 1rem;
}

/* Conversation list styling */
.conversation-item {
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: background-color 0.2s;
}

.conversation-item:hover {
    background-color: #e9ecef;
}

/* Login/Register form styling */
.auth-form {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
}

/* Cost display styling */
.cost-display {
    color: #28a745;
    font-weight: 600;
}

/* Warning/info boxes */
.info-box {
    background-color: #e7f3ff;
    border-left: 4px solid #0066cc;
    padding: 1rem;
    border-radius: 0 0.5rem 0.5rem 0;
    margin: 1rem 0;
}

.warning-box {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 1rem;
    border-radius: 0 0.5rem 0.5rem 0;
    margin: 1rem 0;
}

/* Uploaded file display */
.uploaded-file {
    display: inline-flex;
    align-items: center;
    background-color: #e9ecef;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    margin: 0.25rem;
    font-size: 0.85rem;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main .block-container {
        padding: 1rem;
    }
}
</style>
"""


def apply_styles():
    """Apply custom CSS styles to the Streamlit app."""
    import streamlit as st
    st.markdown(MAIN_CSS, unsafe_allow_html=True)
