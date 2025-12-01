"""
File handling utilities for CHAT.
Processes uploaded files for the Claude API.
"""
import base64
import io
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from chat.config import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS


class FileProcessingError(Exception):
    """Raised when file processing fails."""
    pass


def validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate a file before processing.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS.keys())}"

    # Check file size
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"

    return True, ""


def get_mime_type(filename: str) -> str:
    """Get the MIME type for a file based on extension."""
    ext = Path(filename).suffix.lower()
    return ALLOWED_EXTENSIONS.get(ext, "application/octet-stream")


def process_file(filename: str, file_data: bytes) -> Dict[str, Any]:
    """
    Process an uploaded file for the Claude API.

    Args:
        filename: Original filename
        file_data: Raw file bytes

    Returns:
        Dict with 'name', 'type', 'data' (base64), and optionally 'extracted_text'
    """
    is_valid, error = validate_file(filename, len(file_data))
    if not is_valid:
        raise FileProcessingError(error)

    mime_type = get_mime_type(filename)
    ext = Path(filename).suffix.lower()

    result = {
        "name": filename,
        "type": mime_type,
        "data": base64.b64encode(file_data).decode("utf-8")
    }

    # Extract text from text-based files
    if ext in [".txt", ".md", ".csv"]:
        try:
            result["extracted_text"] = file_data.decode("utf-8")
        except UnicodeDecodeError:
            result["extracted_text"] = file_data.decode("latin-1")

    # Extract text from Word documents
    elif ext in [".doc", ".docx"]:
        result["extracted_text"] = extract_docx_text(file_data)

    return result


def extract_docx_text(file_data: bytes) -> str:
    """Extract text from a Word document."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_data))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)
    except Exception as e:
        return f"[Could not extract text from document: {str(e)}]"


def format_file_for_display(file_info: Dict[str, Any]) -> str:
    """Format file info for display in the UI."""
    filename = file_info.get("name", "Unknown file")
    mime_type = file_info.get("type", "unknown")

    if mime_type.startswith("image/"):
        return f"📷 {filename}"
    elif mime_type == "application/pdf":
        return f"📄 {filename}"
    elif "word" in mime_type or mime_type == "application/msword":
        return f"📝 {filename}"
    elif mime_type.startswith("text/"):
        return f"📃 {filename}"
    else:
        return f"📎 {filename}"


def get_file_icon(mime_type: str) -> str:
    """Get an appropriate icon for a file type."""
    if mime_type.startswith("image/"):
        return "🖼️"
    elif mime_type == "application/pdf":
        return "📕"
    elif "word" in mime_type:
        return "📘"
    elif mime_type.startswith("text/"):
        return "📄"
    else:
        return "📎"
