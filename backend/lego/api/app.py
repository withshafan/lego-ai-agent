"""Local FastAPI entry point for LEGO AI Agent."""

import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from lego import APP_NAME, __version__
from lego.agent.llm import OllamaError, chat, chat_with_tools
from lego.agent.prompts import CHAT_SYSTEM_PROMPT, TASK_PLANNER_SYSTEM_PROMPT
from lego.tools.registry import (
    ToolResult,
    dispatch,
    prepare,
    schemas as tool_schemas,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_ROOT = _REPOSITORY_ROOT / "frontend"

app = FastAPI(title=APP_NAME, version=__version__)
app.mount(
    "/static",
    StaticFiles(directory=str(_FRONTEND_ROOT / "static")),
    name="static",
)
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


class AgentTaskAction(BaseModel):
    """A registered, validated action proposal shown before execution."""

    name: str
    description: str
    arguments: dict[str, Any]
    risk: Literal["low", "medium", "high"]
    requires_approval: bool


class AgentTaskResponse(BaseModel):
    """Result of planning and safely handling one user task request."""

    status: Literal[
        "answered", "completed", "approval_required", "clarification", "failed"
    ]
    message: str
    action: AgentTaskAction | None = None
    result: ToolResult | None = None


class ToolDispatchRequest(BaseModel):
    """Request one registered tool; approval is false unless explicitly set."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Serve the local desktop web interface from the project frontend folder."""
    return FileResponse(_FRONTEND_ROOT / "index.html")


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


@app.post("/agent/task", response_model=AgentTaskResponse, tags=["agent"])
async def agent_task_endpoint(request: ChatRequest) -> AgentTaskResponse:
    """Plan one task with registered tools and execute only no-approval actions."""
    messages = [
        {"role": "system", "content": TASK_PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": request.message},
    ]
    ollama_tools = [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"],
            },
        }
        for schema in tool_schemas()
    ]

    try:
        plan = await chat_with_tools(messages, ollama_tools)
    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail="The local Ollama request failed. Check that Ollama is running.",
        ) from exc

    if not plan.tool_calls:
        reply = plan.content or "I could not form a task or answer. Please rephrase."
        _audit_logger.info("agent_task status=answered tool_calls=0")
        return AgentTaskResponse(status="answered", message=reply)

    if len(plan.tool_calls) != 1:
        _audit_logger.info(
            "agent_task status=clarification tool_calls=%s", len(plan.tool_calls)
        )
        return AgentTaskResponse(
            status="clarification",
            message="The planner proposed multiple actions, so none were run. "
            "Please make one request at a time.",
        )

    proposed_call = plan.tool_calls[0]
    prepared = prepare(proposed_call.name, proposed_call.arguments)
    if isinstance(prepared, ToolResult):
        _audit_logger.info(
            "agent_task status=failed tool=%s reason=invalid_proposal",
            proposed_call.name,
        )
        return AgentTaskResponse(
            status="failed",
            message=prepared.message,
            result=prepared,
        )

    spec = prepared.spec
    action = AgentTaskAction(
        name=spec.name,
        description=spec.description,
        arguments=prepared.arguments.model_dump(mode="json"),
        risk=spec.risk,
        requires_approval=spec.requires_approval,
    )

    if spec.requires_approval:
        _audit_logger.info(
            "agent_task status=approval_required tool=%s", spec.name
        )
        return AgentTaskResponse(
            status="approval_required",
            message="Review the proposed action and its arguments before running it.",
            action=action,
        )

    result = dispatch(
        spec.name,
        prepared.arguments.model_dump(mode="python"),
        approved=False,
    )
    status = "completed" if result.success else "failed"
    _audit_logger.info(
        "agent_task status=%s tool=%s approved=false success=%s",
        status,
        spec.name,
        result.success,
    )
    return AgentTaskResponse(
        status=status,
        message=result.message,
        action=action,
        result=result,
    )


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
