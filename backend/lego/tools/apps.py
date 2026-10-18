"""Approved Windows application launcher."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lego.tools.registry import ToolResult, tool

_APPS_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "allowed_apps.json"


class OpenAllowedAppArgs(BaseModel):
    """The key of an application in the fixed allowlist."""

    model_config = ConfigDict(extra="forbid")

    app: str = Field(
        default="notepad",
        min_length=1,
        max_length=40,
        pattern=r"^[a-z0-9_]+$",
        description="Lowercase allowlist key, such as 'notepad'.",
    )

    @field_validator("app", mode="before")
    @classmethod
    def normalize_app_key(cls, value: Any) -> Any:
        """Accept natural capitalization while keeping the allowlist key strict."""
        if isinstance(value, str):
            return value.strip().casefold()
        return value


@tool(name="open_allowed_app", risk="low", requires_approval=False)
def open_allowed_app(args: OpenAllowedAppArgs) -> ToolResult:
    """Open an application whose executable is fixed in allowed_apps.json."""
    try:
        configured_apps: Any = json.loads(
            _APPS_CONFIG_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return ToolResult(
            success=False,
            message="The approved application list could not be read.",
            error="Application allowlist unavailable.",
        )

    app_config = configured_apps.get(args.app) if isinstance(configured_apps, dict) else None
    if not isinstance(app_config, dict):
        return ToolResult(
            success=False,
            message="That application is not allowlisted.",
            error="Application not allowed.",
        )

    command = app_config.get("command")
    fixed_args = app_config.get("args")
    if (
        not isinstance(command, str)
        or not command
        or not isinstance(fixed_args, list)
        or any(not isinstance(value, str) for value in fixed_args)
    ):
        return ToolResult(
            success=False,
            message="The approved application entry is invalid.",
            error="Invalid application configuration.",
        )

    try:
        subprocess.Popen([command, *fixed_args], shell=False)
    except OSError:
        return ToolResult(
            success=False,
            message="Windows could not start the approved application.",
            error="Application launch failed.",
        )

    return ToolResult(
        success=True,
        message="Opened the approved application.",
        data={"app": args.app},
    )
