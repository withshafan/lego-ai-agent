import httpx
import pytest

import lego.api.app as api_module
from lego.api.app import app
from lego.agent.llm import OllamaError
from lego.agent.prompts import CHAT_SYSTEM_PROMPT


async def _post_json(path: str, payload: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.post(path, json=payload)


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
