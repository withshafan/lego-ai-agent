"""Async HTTPX client for the local Ollama chat API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Mapping, Sequence
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, ValidationError

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_MODEL_CONFIG_PATH = _REPOSITORY_ROOT / "models" / "config.json"
_REQUEST_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


class OllamaError(RuntimeError):
    """A safe, readable error raised when a local Ollama request fails."""


class ModelConfig(BaseModel):
    """Validated settings read from models/config.json."""

    active_model: str = Field(min_length=1)
    ollama_base_url: str
    num_ctx: int = Field(gt=0)
    temperature: float = Field(ge=0.0, le=2.0)
    seed: int


class ChatMessage(BaseModel):
    """A single plain-text chat message accepted by Ollama."""

    role: Literal["system", "user", "assistant"]
    content: str


def _load_model_config() -> ModelConfig:
    try:
        raw_config = json.loads(_MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
        config = ModelConfig.model_validate(raw_config)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise OllamaError(
            f"The model configuration at {_MODEL_CONFIG_PATH} is missing or invalid."
        ) from exc

    parsed_url = urlsplit(config.ollama_base_url)
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname != "127.0.0.1"
        or parsed_url.port != 11434
        or parsed_url.path not in ("", "/")
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise OllamaError(
            "Ollama must use the local URL http://127.0.0.1:11434."
        )

    return config


async def chat(messages: Sequence[Mapping[str, str]]) -> str:
    """Send plain-text conversation messages to the local Ollama model."""
    if not messages:
        raise ValueError("At least one chat message is required.")

    try:
        validated_messages = [
            ChatMessage.model_validate(message).model_dump() for message in messages
        ]
    except ValidationError as exc:
        raise ValueError(
            "Each chat message must contain a valid role and text content."
        ) from exc

    config = _load_model_config()
    payload = {
        "model": config.active_model,
        "messages": validated_messages,
        "stream": False,
        "options": {
            "num_ctx": config.num_ctx,
            "temperature": config.temperature,
            "seed": config.seed,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{config.ollama_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
    except httpx.ConnectError as exc:
        raise OllamaError(
            "Cannot connect to local Ollama. Keep `ollama serve` running and try again."
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaError("The local Ollama request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaError(
            f"Local Ollama returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaError("The local Ollama request failed.") from exc

    try:
        content = response.json()["message"]["content"]
    except (KeyError, TypeError, ValueError) as exc:
        raise OllamaError("Ollama returned an unexpected chat response.") from exc

    if not isinstance(content, str):
        raise OllamaError("Ollama returned a non-text chat response.")

    return content.strip()
