"""
LLM Client abstraction layer for CHAT.
Supports AWS Bedrock (Commercial and GovCloud) with streaming responses.
"""
from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any, Optional
from dataclasses import dataclass
import json

import boto3
from botocore.config import Config

from chat.config import get_config, LLMBackend, COST_PER_1M_INPUT_TOKENS, COST_PER_1M_OUTPUT_TOKENS


@dataclass
class StreamChunk:
    """Represents a chunk of streamed response."""
    text: str
    is_final: bool = False
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def input_cost(self) -> float:
        return (self.input_tokens / 1_000_000) * COST_PER_1M_INPUT_TOKENS

    @property
    def output_cost(self) -> float:
        return (self.output_tokens / 1_000_000) * COST_PER_1M_OUTPUT_TOKENS

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def stream_message(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Generator[StreamChunk, None, None]:
        """
        Stream a message to the LLM and yield response chunks.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response

        Yields:
            StreamChunk objects containing text and metadata
        """
        pass


class AWSBedrockClient(BaseLLMClient):
    """Client for AWS Bedrock (Commercial)."""

    def __init__(self):
        config = get_config()
        self.model_id = config.model_id
        self.region = config.region

        boto_config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )
        self.client = boto3.client(
            "bedrock-runtime",
            config=boto_config
        )

    def stream_message(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Generator[StreamChunk, None, None]:
        """Stream a message using AWS Bedrock converse_stream API."""

        # Build the request
        request = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
            }
        }

        if system_prompt:
            request["system"] = [{"text": system_prompt}]

        # Make the streaming request
        response = self.client.converse_stream(**request)

        input_tokens = 0
        output_tokens = 0

        # Process the stream
        for event in response.get("stream", []):
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    yield StreamChunk(text=delta["text"])

            elif "metadata" in event:
                usage = event["metadata"].get("usage", {})
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)

        # Yield final chunk with token counts
        yield StreamChunk(
            text="",
            is_final=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


class AWSGovCloudClient(BaseLLMClient):
    """Client for AWS GovCloud Bedrock."""

    def __init__(self):
        config = get_config()
        self.model_id = config.model_id
        self.region = config.region

        boto_config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )
        self.client = boto3.client(
            "bedrock-runtime",
            config=boto_config
        )

    def stream_message(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> Generator[StreamChunk, None, None]:
        """Stream a message using AWS GovCloud Bedrock converse_stream API."""

        # Build the request - same as commercial
        request = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
            }
        }

        if system_prompt:
            request["system"] = [{"text": system_prompt}]

        # Make the streaming request
        response = self.client.converse_stream(**request)

        input_tokens = 0
        output_tokens = 0

        # Process the stream
        for event in response.get("stream", []):
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    yield StreamChunk(text=delta["text"])

            elif "metadata" in event:
                usage = event["metadata"].get("usage", {})
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)

        # Yield final chunk with token counts
        yield StreamChunk(
            text="",
            is_final=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


def create_llm_client() -> BaseLLMClient:
    """
    Factory function to create the appropriate LLM client
    based on the active environment configuration.
    """
    config = get_config()

    if config.backend == LLMBackend.AWS_BEDROCK:
        return AWSBedrockClient()
    elif config.backend == LLMBackend.AWS_GOVCLOUD:
        return AWSGovCloudClient()
    else:
        raise ValueError(f"Unsupported backend: {config.backend}")


def format_message_with_files(
    text: str,
    files: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Format a user message with optional file attachments for the Bedrock API.

    Args:
        text: The user's text message
        files: List of file dicts with 'name', 'type', and 'data' (base64 encoded)

    Returns:
        A properly formatted message dict for the Bedrock converse API
    """
    content = []

    # Add file content first (images, documents)
    if files:
        for file in files:
            file_type = file.get("type", "")
            file_data = file.get("data")  # base64 encoded
            file_name = file.get("name", "file")

            if file_type.startswith("image/"):
                # Image content
                content.append({
                    "image": {
                        "format": file_type.split("/")[1],  # e.g., "png", "jpeg"
                        "source": {
                            "bytes": file_data
                        }
                    }
                })
            elif file_type == "application/pdf":
                # PDF document
                content.append({
                    "document": {
                        "format": "pdf",
                        "name": file_name,
                        "source": {
                            "bytes": file_data
                        }
                    }
                })
            elif file_type in [
                "text/plain",
                "text/markdown",
                "text/csv",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                # Text-based documents - extract and include as text
                # For docx, we'll handle extraction in the upload processing
                content.append({
                    "text": f"[File: {file_name}]\n{file.get('extracted_text', '')}"
                })

    # Add the user's text message
    if text:
        content.append({"text": text})

    return {
        "role": "user",
        "content": content
    }
