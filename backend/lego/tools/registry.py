"""Fixed tool registry with schema validation and an approval gate."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal, get_type_hints

from pydantic import BaseModel, Field, ValidationError

ToolRisk = Literal["low", "medium", "high"]
ToolFunction = Callable[[BaseModel], "ToolResult"]


class ToolResult(BaseModel):
    """Safe, structured result returned by every registered tool."""

    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    """Immutable metadata for a single registered tool."""

    name: str
    risk: ToolRisk
    requires_approval: bool
    description: str
    args_model: type[BaseModel]
    function: ToolFunction


_REGISTRY: dict[str, ToolSpec] = {}


def tool(*, name: str, risk: ToolRisk, requires_approval: bool) -> Callable:
    """Register a tool that accepts one Pydantic argument model."""
    if not name or not name.replace("_", "").isalnum() or not name[0].isalpha():
        raise ValueError("Tool names must contain only letters, numbers, and underscores.")
    if risk not in {"low", "medium", "high"}:
        raise ValueError("Tool risk must be low, medium, or high.")
    if not isinstance(requires_approval, bool):
        raise ValueError("requires_approval must be a boolean.")

    def register(function: ToolFunction) -> ToolFunction:
        if name in _REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered.")

        parameters = list(inspect.signature(function).parameters.values())
        if len(parameters) != 1:
            raise TypeError("A registered tool must accept exactly one argument model.")

        try:
            args_model = get_type_hints(function)[parameters[0].name]
        except (KeyError, NameError, TypeError) as exc:
            raise TypeError("A registered tool must annotate its argument model.") from exc

        if not isinstance(args_model, type) or not issubclass(args_model, BaseModel):
            raise TypeError("A registered tool argument must be a Pydantic model.")

        _REGISTRY[name] = ToolSpec(
            name=name,
            risk=risk,
            requires_approval=requires_approval,
            description=inspect.getdoc(function) or "",
            args_model=args_model,
            function=function,
        )
        return function

    return register


def schemas() -> list[dict[str, Any]]:
    """Return JSON-schema descriptions for the registered tools."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.args_model.model_json_schema(),
            "risk": spec.risk,
            "requires_approval": spec.requires_approval,
        }
        for spec in _REGISTRY.values()
    ]


def dispatch(
    name: str,
    args: dict[str, Any],
    *,
    approved: bool = False,
) -> ToolResult:
    """Validate and dispatch one registered tool without leaking exceptions."""
    spec = _REGISTRY.get(name)
    if spec is None:
        return ToolResult(
            success=False,
            message="The requested tool is not registered.",
            error="Unknown tool.",
        )

    if spec.requires_approval and not approved:
        return ToolResult(
            success=False,
            message="This action requires approval before it can run.",
            error="Approval required.",
        )

    try:
        validated_args = spec.args_model.model_validate(args)
    except (ValidationError, TypeError):
        return ToolResult(
            success=False,
            message="The tool arguments are invalid.",
            error="Argument validation failed.",
        )

    try:
        result = spec.function(validated_args)
    except Exception:
        return ToolResult(
            success=False,
            message="The tool could not complete the requested action.",
            error="Tool execution failed.",
        )

    if not isinstance(result, ToolResult):
        return ToolResult(
            success=False,
            message="The tool returned an invalid result.",
            error="Invalid tool result.",
        )

    return result
