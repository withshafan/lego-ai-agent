import httpx
import pytest

import lego.api.app as api_module
from lego.api.app import app
from lego.agent.llm import ChatWithToolsResponse, ModelToolCall, OllamaError
from lego.agent.prompts import CHAT_SYSTEM_PROMPT, TASK_PLANNER_SYSTEM_PROMPT
from lego.tools.registry import ToolResult


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.get(path)


async def _post_json(path: str, payload: dict[str, object]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.post(path, json=payload)


@pytest.mark.asyncio
async def test_home_serves_the_local_frontend_and_relative_assets() -> None:
    response = await _get("/")

    assert response.status_code == 200
    assert 'href="/static/styles.css"' in response.text
    assert 'src="/static/app.js"' in response.text
    assert "http://" not in response.text
    assert "https://" not in response.text


@pytest.mark.asyncio
async def test_frontend_javascript_uses_relative_api_and_safe_text_rendering() -> None:
    response = await _get("/static/app.js")

    assert response.status_code == 200
    assert 'fetch("/chat"' in response.text
    assert 'fetch("/tools"' in response.text
    assert 'fetch("/health"' in response.text
    assert "innerHTML" not in response.text
    assert "127.0.0.1" not in response.text
    assert "localhost" not in response.text


@pytest.mark.asyncio
async def test_health_endpoint_returns_local_backend_status() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "LEGO AI Agent",
        "version": "0.1.0",
    }


@pytest.mark.asyncio
async def test_tools_endpoint_lists_registered_tools_and_approval_metadata() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/tools")

    assert response.status_code == 200
    registered = {item["name"]: item for item in response.json()}
    assert {"open_allowed_app", "create_text_file"}.issubset(registered)
    assert registered["create_text_file"]["requires_approval"] is True
    assert registered["create_text_file"]["risk"] == "medium"


@pytest.mark.asyncio
async def test_tool_dispatch_denies_file_write_without_approval() -> None:
    response = await _post_json(
        "/tools/dispatch",
        {
            "name": "create_text_file",
            "arguments": {"path": "blocked.txt", "content": "not written"},
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["error"] == "Approval required."


@pytest.mark.asyncio
async def test_tool_dispatch_passes_explicit_approval_and_audits_metadata(
    monkeypatch, caplog
) -> None:
    received: list[tuple[str, dict[str, object], bool]] = []

    def fake_dispatch(
        name: str,
        arguments: dict[str, object],
        *,
        approved: bool = False,
    ) -> ToolResult:
        received.append((name, arguments, approved))
        return ToolResult(success=True, message="Approved action ran.")

    monkeypatch.setattr(api_module, "dispatch", fake_dispatch)
    secret_content = "private text must not enter the audit log"
    with caplog.at_level("INFO", logger="lego.audit"):
        response = await _post_json(
            "/tools/dispatch",
            {
                "name": "create_text_file",
                "arguments": {"path": "private.txt", "content": secret_content},
                "approved": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert received == [
        (
            "create_text_file",
            {"path": "private.txt", "content": secret_content},
            True,
        )
    ]
    assert "tool_dispatch name=create_text_file approved=True success=True" in caplog.text
    assert "private.txt" not in caplog.text
    assert secret_content not in caplog.text


@pytest.mark.asyncio
async def test_tool_dispatch_rejects_unexpected_request_fields() -> None:
    response = await _post_json(
        "/tools/dispatch",
        {
            "name": "open_allowed_app",
            "arguments": {"app": "notepad"},
            "command": "not accepted",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_task_returns_text_when_model_proposes_no_tool(monkeypatch) -> None:
    received_messages: list[dict[str, str]] = []
    received_tools: list[dict[str, object]] = []

    async def fake_chat_with_tools(messages, tools) -> ChatWithToolsResponse:
        received_messages.extend(messages)
        received_tools.extend(tools)
        return ChatWithToolsResponse(content="Here is a simple answer.")

    monkeypatch.setattr(api_module, "chat_with_tools", fake_chat_with_tools)
    response = await _post_json("/agent/task", {"message": "What is LEGO?"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered",
        "message": "Here is a simple answer.",
        "action": None,
        "result": None,
    }
    assert received_messages == [
        {"role": "system", "content": TASK_PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": "What is LEGO?"},
    ]
    function_names = {
        item["function"]["name"]  # type: ignore[index]
        for item in received_tools
    }
    assert {"open_allowed_app", "create_text_file"}.issubset(function_names)


@pytest.mark.asyncio
async def test_agent_task_proposes_approval_required_action_without_dispatch(
    monkeypatch,
) -> None:
    dispatch_calls: list[tuple[str, dict[str, object], bool]] = []

    async def fake_chat_with_tools(_messages, _tools) -> ChatWithToolsResponse:
        return ChatWithToolsResponse(
            tool_calls=[
                ModelToolCall(
                    name="create_text_file",
                    arguments={
                        "path": "proposed.txt",
                        "content": "must not be written yet",
                        "overwrite": False,
                    },
                )
            ]
        )

    def fake_dispatch(name, arguments, *, approved=False) -> ToolResult:
        dispatch_calls.append((name, arguments, approved))
        return ToolResult(success=True, message="Unexpected dispatch")

    monkeypatch.setattr(api_module, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(api_module, "dispatch", fake_dispatch)
    response = await _post_json("/agent/task", {"message": "Create a note"})

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "approval_required"
    assert body["action"]["name"] == "create_text_file"
    assert body["action"]["requires_approval"] is True
    assert body["action"]["arguments"]["path"] == "proposed.txt"
    assert body["result"] is None
    assert dispatch_calls == []


@pytest.mark.asyncio
async def test_agent_task_dispatches_only_non_approval_tool(monkeypatch) -> None:
    dispatch_calls: list[tuple[str, dict[str, object], bool]] = []

    async def fake_chat_with_tools(_messages, _tools) -> ChatWithToolsResponse:
        return ChatWithToolsResponse(
            tool_calls=[
                ModelToolCall(
                    name="open_allowed_app",
                    arguments={"app": "Notepad"},
                )
            ]
        )

    def fake_dispatch(name, arguments, *, approved=False) -> ToolResult:
        dispatch_calls.append((name, arguments, approved))
        return ToolResult(success=True, message="Opened the approved application.")

    monkeypatch.setattr(api_module, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(api_module, "dispatch", fake_dispatch)
    response = await _post_json("/agent/task", {"message": "Open Notepad"})

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert dispatch_calls == [
        ("open_allowed_app", {"app": "notepad"}, False)
    ]


@pytest.mark.asyncio
async def test_agent_task_refuses_multiple_proposals_and_unknown_tools(monkeypatch) -> None:
    dispatch_calls: list[bool] = []

    async def two_calls(_messages, _tools) -> ChatWithToolsResponse:
        call = ModelToolCall(name="open_allowed_app", arguments={"app": "notepad"})
        return ChatWithToolsResponse(tool_calls=[call, call])

    monkeypatch.setattr(api_module, "chat_with_tools", two_calls)
    monkeypatch.setattr(
        api_module,
        "dispatch",
        lambda *_args, **_kwargs: dispatch_calls.append(True),
    )
    multiple = await _post_json("/agent/task", {"message": "Do two things"})
    assert multiple.json()["status"] == "clarification"
    assert dispatch_calls == []

    async def unknown_call(_messages, _tools) -> ChatWithToolsResponse:
        return ChatWithToolsResponse(
            tool_calls=[ModelToolCall(name="run_shell", arguments={"command": "dir"})]
        )

    monkeypatch.setattr(api_module, "chat_with_tools", unknown_call)
    unknown = await _post_json("/agent/task", {"message": "Run a command"})
    assert unknown.json()["status"] == "failed"
    assert unknown.json()["result"]["error"] == "Unknown tool."
    assert dispatch_calls == []


@pytest.mark.asyncio
async def test_agent_task_returns_safe_error_when_local_model_fails(monkeypatch) -> None:
    async def failed_chat_with_tools(_messages, _tools):
        raise OllamaError("private local configuration detail")

    monkeypatch.setattr(api_module, "chat_with_tools", failed_chat_with_tools)
    response = await _post_json("/agent/task", {"message": "Open Notepad"})

    assert response.status_code == 503
    assert "private local configuration detail" not in response.text


@pytest.mark.asyncio
async def test_chat_endpoint_uses_the_fixed_system_prompt(monkeypatch) -> None:
    received_messages: list[dict[str, str]] = []

    async def fake_chat(messages: list[dict[str, str]]) -> str:
        received_messages.extend(messages)
        return "Hello from the local model."

    monkeypatch.setattr(api_module, "chat", fake_chat)
    response = await _post_json("/chat", {"message": "  Hello LEGO  "})

    assert response.status_code == 200
    assert response.json() == {"reply": "Hello from the local model."}
    assert received_messages == [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": "Hello LEGO"},
    ]


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_blank_or_oversized_messages() -> None:
    blank = await _post_json("/chat", {"message": "   "})
    oversized = await _post_json("/chat", {"message": "x" * 4001})

    assert blank.status_code == 422
    assert oversized.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_returns_safe_error_when_local_model_fails(
    monkeypatch,
) -> None:
    async def failed_chat(_messages: list[dict[str, str]]) -> str:
        raise OllamaError("private local configuration detail")

    monkeypatch.setattr(api_module, "chat", failed_chat)
    response = await _post_json("/chat", {"message": "Hello"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The local Ollama request failed. Check that Ollama is running."
    }
    assert "private local configuration detail" not in response.text
