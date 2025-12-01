"""
Configuration module for CHAT.
Handles environment switching between Commercial AWS and GovCloud.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os


class Environment(Enum):
    COMMERCIAL = "commercial"
    GOVCLOUD = "govcloud"


class LLMBackend(Enum):
    ANTHROPIC_DIRECT = "anthropic_direct"
    AWS_BEDROCK = "aws_bedrock"
    AWS_GOVCLOUD = "aws_govcloud"


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment."""
    name: str
    backend: LLMBackend
    region: str
    model_id: str
    display_name: str


# Environment configurations
ENVIRONMENT_CONFIGS = {
    Environment.COMMERCIAL: EnvironmentConfig(
        name="commercial",
        backend=LLMBackend.AWS_BEDROCK,
        region="us-east-1",
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        display_name="AWS Commercial (us-east-1)"
    ),
    Environment.GOVCLOUD: EnvironmentConfig(
        name="govcloud",
        backend=LLMBackend.AWS_GOVCLOUD,
        region="us-gov-west-1",
        model_id="us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0",
        display_name="AWS GovCloud (us-gov-west-1)"
    ),
}

# =============================================================================
# ACTIVE ENVIRONMENT - Change this single line to switch environments
# =============================================================================
ACTIVE_ENVIRONMENT = Environment.COMMERCIAL
# =============================================================================


def get_config() -> EnvironmentConfig:
    """Get the configuration for the active environment."""
    return ENVIRONMENT_CONFIGS[ACTIVE_ENVIRONMENT]


# Application settings
APP_NAME = "CHAT"
APP_VERSION = "1.0.0"

# Database settings
DATABASE_PATH = os.environ.get("CHAT_DB_PATH", "chat.db")

# JWT settings
JWT_SECRET_KEY = os.environ.get("CHAT_JWT_SECRET", "change-this-in-production-use-a-real-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# File upload settings
MAX_FILE_SIZE_MB = 25
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Cost estimation (per 1M tokens, Bedrock Sonnet 4.5 pricing)
COST_PER_1M_INPUT_TOKENS = 3.00
COST_PER_1M_OUTPUT_TOKENS = 15.00

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant.
You can help with a wide variety of tasks including:
- Summarization of documents and text
- Technical writing and editing
- Code review, debugging, and development
- Research assistance and analysis
- General questions and problem-solving

Be professional, accurate, and thorough in your responses. If you're unsure about something, say so.
When working with code, provide clear explanations and follow best practices."""
