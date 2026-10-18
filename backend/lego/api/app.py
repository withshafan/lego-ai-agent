"""Local FastAPI entry point for LEGO AI Agent."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from lego import APP_NAME, __version__
from lego.agent.llm import OllamaError, chat
from lego.agent.prompts import CHAT_SYSTEM_PROMPT
from lego.tools.registry import ToolResult, dispatch, schemas as tool_schemas

app = FastAPI(title=APP_NAME, version=__version__)
_audit_logger = logging.getLogger("lego.audit")
_audit_logger.setLevel(logging.INFO)
if not _audit_logger.handlers:
    _audit_handler = logging.StreamHandler()
    _audit_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    _audit_logger.addHandler(_audit_handler)
_audit_logger.propagate = False


class ChatRequest(BaseModel):
    """One bounded plain-text user message for a local model request."""

    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_and_check_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value


class ChatResponse(BaseModel):
    """Plain-text response from the configured local Ollama model."""

    reply: str


class ToolDispatchRequest(BaseModel):
    """Request one registered tool; approval is false unless explicitly set."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the local backend process is responding."""
    return {"status": "ok", "app": APP_NAME, "version": __version__}


@app.get("/tools", tags=["tools"])
def list_tools() -> list[dict[str, Any]]:
    """Return schemas and safety metadata for explicitly registered tools."""
    return tool_schemas()


@app.post("/tools/dispatch", response_model=ToolResult, tags=["tools"])
def dispatch_tool(request: ToolDispatchRequest) -> ToolResult:
    """Dispatch only a registered tool; approval-required calls default to denied."""
    result = dispatch(
        request.name,
        request.arguments,
        approved=request.approved,
    )
    # Audit metadata only: never include arguments, file content, or secrets.
    _audit_logger.info(
        "tool_dispatch name=%s approved=%s success=%s",
        request.name,
        request.approved,
        result.success,
    )
    return result


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Send one user message to the configured local Ollama model."""
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": request.message},
    ]
    try:
        reply = await chat(messages)
    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail="The local Ollama request failed. Check that Ollama is running.",
        ) from exc

    return ChatResponse(reply=reply)
