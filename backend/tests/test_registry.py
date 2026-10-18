from __future__ import annotations

from pydantic import BaseModel

from lego.tools.registry import ToolResult, dispatch, schemas, tool


class EchoArgs(BaseModel):
    text: str


class ApprovedArgs(BaseModel):
    text: str


@tool(name="registry_test_echo", risk="low", requires_approval=False)
def _echo(args: EchoArgs) -> ToolResult:
    """Return the provided text for registry testing."""
    return ToolResult(success=True, message="Echoed.", data={"text": args.text})


_approved_calls: list[str] = []


@tool(name="registry_test_approved", risk="medium", requires_approval=True)
def _approved(args: ApprovedArgs) -> ToolResult:
    """Record a call after approval for registry testing."""
    _approved_calls.append(args.text)
    return ToolResult(success=True, message="Approved action ran.")


@tool(name="registry_test_failure", risk="low", requires_approval=False)
def _failure(args: EchoArgs) -> ToolResult:
    """Raise an internal error to test safe failure results."""
    raise RuntimeError("private detail must not escape")


def test_schemas_expose_registered_tool_metadata() -> None:
    registered = {item["name"]: item for item in schemas()}

    assert "registry_test_echo" in registered
    assert registered["registry_test_echo"]["parameters"]["properties"]["text"]
    assert registered["registry_test_echo"]["risk"] == "low"
    assert registered["registry_test_echo"]["requires_approval"] is False


def test_dispatch_validates_and_calls_registered_tool() -> None:
    result = dispatch("registry_test_echo", {"text": "hello"})

    assert result.success is True
    assert result.data == {"text": "hello"}


def test_dispatch_rejects_unknown_tool() -> None:
    result = dispatch("not_registered", {})

    assert result.success is False
    assert result.error == "Unknown tool."


def test_dispatch_rejects_invalid_arguments() -> None:
    result = dispatch("registry_test_echo", {"wrong": "value"})

    assert result.success is False
    assert result.error == "Argument validation failed."


def test_dispatch_enforces_approval_before_execution() -> None:
    _approved_calls.clear()
    result = dispatch("registry_test_approved", {"text": "write"})

    assert result.success is False
    assert result.error == "Approval required."
    assert _approved_calls == []


def test_dispatch_executes_after_explicit_approval() -> None:
    result = dispatch("registry_test_approved", {"text": "write"}, approved=True)

    assert result.success is True
    assert _approved_calls == ["write"]


def test_dispatch_returns_safe_error_without_leaking_exception() -> None:
    result = dispatch("registry_test_failure", {"text": "x"})

    assert result.success is False
    assert result.error == "Tool execution failed."
    assert "private detail" not in result.message
    assert "private detail" not in (result.error or "")
