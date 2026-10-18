from __future__ import annotations

from pathlib import Path

import pytest

from lego.security.sandbox import SandboxError, load_allowed_root, resolve_allowed_path


def test_load_allowed_root_reads_one_existing_directory(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()
    allowlist = tmp_path / "allowed_folders.txt"
    allowlist.write_text(f"{root}\n", encoding="utf-8")

    assert load_allowed_root(allowlist) == root.resolve()


def test_load_allowed_root_rejects_multiple_directories(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    allowlist = tmp_path / "allowed_folders.txt"
    allowlist.write_text(f"{first}\n{second}\n", encoding="utf-8")

    with pytest.raises(SandboxError, match="exactly one"):
        load_allowed_root(allowlist)


def test_load_allowed_root_rejects_relative_directory(tmp_path: Path) -> None:
    allowlist = tmp_path / "allowed_folders.txt"
    allowlist.write_text("relative-workspace\n", encoding="utf-8")

    with pytest.raises(SandboxError, match="absolute"):
        load_allowed_root(allowlist)


def test_resolve_allowed_path_accepts_relative_file(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()

    assert resolve_allowed_path("notes.txt", allowed_root=root) == root / "notes.txt"


def test_resolve_allowed_path_accepts_absolute_file_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()
    target = root / "notes.txt"

    assert resolve_allowed_path(target, allowed_root=root) == target


def test_resolve_allowed_path_rejects_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()

    with pytest.raises(SandboxError, match="traversal"):
        resolve_allowed_path("../outside.txt", allowed_root=root)


def test_resolve_allowed_path_rejects_absolute_path_outside_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "approved"
    root.mkdir()
    outside = tmp_path / "outside.txt"

    with pytest.raises(SandboxError, match="outside"):
        resolve_allowed_path(outside, allowed_root=root)


def test_resolve_allowed_path_rejects_the_root_itself(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    root.mkdir()

    with pytest.raises(SandboxError, match="outside"):
        resolve_allowed_path(".", allowed_root=root)


def test_resolve_allowed_path_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / "shortcut"

    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"This Windows account cannot create directory symlinks: {exc}")

    with pytest.raises(SandboxError, match="outside"):
        resolve_allowed_path("shortcut/secret.txt", allowed_root=root)
