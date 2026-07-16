"""Amazon Bedrock client wrapper for Claude invocations."""

import json
import os
from typing import Optional

import boto3


# Default model - Claude 3.5 Sonnet
DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

_client = None


def _get_client():
    """Get or initialize the Bedrock Runtime client (singleton)."""
    global _client
    if _client is None:
        region = os.environ.get("AWS_REGION", "us-east-1")
        _client = boto3.client("bedrock-runtime", region_name=region)
    return _client


def invoke_claude(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> str:
    """Invoke Claude via Bedrock and return the response text.

    Args:
        prompt: The user message.
        system: Optional system prompt.
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature.
        json_mode: If True, instructs the model to respond in JSON.

    Returns:
        The model's text response.
    """
    client = _get_client()
    model_id = os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)

    messages = [{"role": "user", "content": prompt}]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    if system:
        body["system"] = system

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    response_body = json.loads(response["body"].read())
    # Extract text from Claude's response format
    content = response_body.get("content", [])
    text_parts = [block["text"] for block in content if block.get("type") == "text"]
    return "\n".join(text_parts)
