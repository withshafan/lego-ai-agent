from __future__ import annotations

from pathlib import Path

import pytest

import lego.security.sandbox as sandbox_module
from lego.tools.registry import dispatch


@pytest.fixture

def approved_workspace(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "approved"
    root.mkdir()
    allowlist = tmp_path / "allowed_folders.txt"
    allowlist.write_text(f"{root}\n", encoding="utf-8")
    monkeypatch.setattr(sandbox_module, "_DEFAULT_ALLOWLIST", allowlist)
    return root


def test_create_text_file_requires_approval(approved_workspace: Path) -> None:
    result = dispatch(
        "create_text_file",
        {"path": "note.txt", "content": "hello"},
    )

    assert result.success is False
    assert result.error == "Approval required."
    assert not (approved_workspace / "note.txt").exists()


def test_create_text_file_writes_atomically_inside_approved_folder(
    approved_workspace: Path,
) -> None:
    result = dispatch(
        "create_text_file",
        {"path": "note.txt", "content": "hello, LEGO", "overwrite": False},
        approved=True,
    )

    assert result.success is True
    assert (approved_workspace / "note.txt").read_text(encoding="utf-8") == "hello, LEGO"
    assert [path.name for path in approved_workspace.iterdir()] == ["note.txt"]
    assert result.data["characters"] == len("hello, LEGO")


def test_create_text_file_rejects_content_over_2000_characters(
    approved_workspace: Path,
) -> None:
    result = dispatch(
        "create_text_file",
        {"path": "too-long.txt", "content": "x" * 2001},
        approved=True,
    )

    assert result.success is False
    assert result.error == "Argument validation failed."
    assert not (approved_workspace / "too-long.txt").exists()


def test_create_text_file_rejects_parent_traversal(approved_workspace: Path) -> None:
    result = dispatch(
        "create_text_file",
        {"path": "../outside.txt", "content": "blocked"},
        approved=True,
    )

    assert result.success is False
    assert result.error == "Path rejected by the workspace sandbox."
    assert not (approved_workspace.parent / "outside.txt").exists()


def test_create_text_file_requires_explicit_overwrite(
    approved_workspace: Path,
) -> None:
    target = approved_workspace / "note.txt"
    target.write_text("original", encoding="utf-8")

    denied = dispatch(
        "create_text_file",
        {"path": "note.txt", "content": "replacement"},
        approved=True,
    )

    assert denied.success is False
    assert denied.error == "File already exists."
    assert target.read_text(encoding="utf-8") == "original"

    approved = dispatch(
        "create_text_file",
        {"path": "note.txt", "content": "replacement", "overwrite": True},
        approved=True,
    )

    assert approved.success is True
    assert target.read_text(encoding="utf-8") == "replacement"


def test_create_text_file_does_not_create_missing_parent(
    approved_workspace: Path,
) -> None:
    result = dispatch(
        "create_text_file",
        {"path": "missing/note.txt", "content": "blocked"},
        approved=True,
    )

    assert result.success is False
    assert result.error == "Parent folder unavailable."
    assert not (approved_workspace / "missing").exists()


def test_create_text_file_rejects_symlink_escape(
    approved_workspace: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = approved_workspace / "shortcut"

    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"This Windows account cannot create directory symlinks: {exc}")

    result = dispatch(
        "create_text_file",
        {"path": "shortcut/secret.txt", "content": "blocked"},
        approved=True,
    )

    assert result.success is False
    assert result.error == "Path rejected by the workspace sandbox."
    assert not (outside / "secret.txt").exists()
