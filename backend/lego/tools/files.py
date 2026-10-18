"""Approval-gated atomic text-file creation inside the approved folder."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lego.security.sandbox import SandboxError, resolve_allowed_path
from lego.tools.registry import ToolResult, tool


class CreateTextFileArgs(BaseModel):
    """Validated input for creating one approved text file."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=2000)
    overwrite: bool = False


@tool(name="create_text_file", risk="medium", requires_approval=True)
def create_text_file(args: CreateTextFileArgs) -> ToolResult:
    """Create a UTF-8 text file under the single approved folder."""
    try:
        target = resolve_allowed_path(args.path)
    except SandboxError:
        return ToolResult(
            success=False,
            message="The requested path is not allowed.",
            error="Path rejected by the workspace sandbox.",
        )

    if not target.parent.is_dir():
        return ToolResult(
            success=False,
            message="The parent folder must already exist inside the approved workspace.",
            error="Parent folder unavailable.",
        )

    if target.exists() and not target.is_file():
        return ToolResult(
            success=False,
            message="The requested path is not a regular file.",
            error="Target is not a file.",
        )

    if target.exists() and not args.overwrite:
        return ToolResult(
            success=False,
            message="The file already exists; overwrite must be explicitly approved.",
            error="File already exists.",
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(args.content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if args.overwrite:
            os.replace(temporary_path, target)
            temporary_path = None
        else:
            # Hard-link creation is atomic and fails rather than overwriting an existing path.
            os.link(temporary_path, target)
            temporary_path.unlink()
            temporary_path = None
    except FileExistsError:
        return ToolResult(
            success=False,
            message="The file already exists; overwrite must be explicitly approved.",
            error="File already exists.",
        )
    except OSError:
        return ToolResult(
            success=False,
            message="Windows could not safely create the text file.",
            error="Atomic file write failed.",
        )
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

    return ToolResult(
        success=True,
        message="The approved text file was created.",
        data={"path": str(target), "characters": len(args.content)},
    )
