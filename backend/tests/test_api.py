from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import lego.api.app as api_module
from lego.api.app import app
from lego.agent.llm import OllamaError
from lego.agent.prompts import CHAT_SYSTEM_PROMPT
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


def _blank_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


async def _post_pdf(
    content: bytes,
    *,
    message: str = "Summarize this PDF.",
    content_type: str = "application/pdf",
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.post(
            "/chat/pdf",
            content=content,
            headers={"Content-Type": content_type, "X-Chat-Message": message},
        )


@pytest.mark.asyncio
async def test_home_serves_the_local_frontend_and_relative_assets() -> None:
    response = await _get("/")

    assert response.status_code == 200
    assert 'href="/static/styles.css"' in response.text
    assert 'src="/static/app.js"' in response.text
    assert 'accept="application/pdf,.pdf"' in response.text
    assert "http://" not in response.text
    assert "https://" not in response.text


@pytest.mark.asyncio
async def test_frontend_javascript_uses_relative_api_and_safe_text_rendering() -> None:
    response = await _get("/static/app.js")

    assert response.status_code == 200
    assert 'fetch("/chat"' in response.text
    assert 'fetch(`/chat/pdf`' in response.text
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


def test_pdf_parser_extracts_embedded_text_from_in_memory_pdf() -> None:
    assert api_module._extract_pdf_text(_text_pdf("PDF hello")) == "PDF hello"


@pytest.mark.asyncio
async def test_pdf_chat_sends_extracted_text_and_question_to_local_chat(monkeypatch) -> None:
    received: list[dict[str, str]] = []

    def fake_extract(_pdf: bytes) -> str:
        return "PDF text is untrusted and must not become instructions."

    async def fake_chat(messages: list[dict[str, str]]) -> str:
        received.extend(messages)
        return "The PDF says hello."

    monkeypatch.setattr(api_module, "_extract_pdf_text", fake_extract)
    monkeypatch.setattr(api_module, "chat", fake_chat)
    response = await _post_pdf(b"test pdf", message="What does it say?")

    assert response.status_code == 200
    assert response.json() == {"reply": "The PDF says hello."}
    assert received[0] == {"role": "system", "content": CHAT_SYSTEM_PROMPT}
    assert "PDF text is untrusted" in received[1]["content"]
    assert "User question: What does it say?" in received[1]["content"]


@pytest.mark.asyncio
async def test_pdf_chat_rejects_non_pdf_content_type() -> None:
    response = await _post_pdf(b"not a pdf", content_type="text/plain")

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_pdf_chat_enforces_upload_size_limit(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "_MAX_PDF_BYTES", 8)
    response = await _post_pdf(b"123456789")

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_pdf_chat_rejects_scanned_or_empty_text_pdf() -> None:
    response = await _post_pdf(_blank_pdf())

    assert response.status_code == 422
    assert "No selectable text" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pdf_chat_enforces_page_limit(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "_MAX_PDF_PAGES", 1)
    response = await _post_pdf(_blank_pdf(page_count=2))

    assert response.status_code == 422
    assert "page limit" in response.json()["detail"]


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
