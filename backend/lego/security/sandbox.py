"""Path validation for the one approved LEGO AI Agent workspace."""

from __future__ import annotations

from pathlib import Path

_DEFAULT_ALLOWLIST = Path(__file__).resolve().parents[1] / "config" / "allowed_folders.txt"


class SandboxError(ValueError):
    """Raised when a path is outside the approved workspace."""


def load_allowed_root(config_path: Path | None = None) -> Path:
    """Load and resolve the single approved directory from the allowlist."""
    allowlist = config_path or _DEFAULT_ALLOWLIST
    try:
        entries = [
            line.strip()
            for line in allowlist.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError as exc:
        raise SandboxError("Could not read the approved-folder allowlist.") from exc

    if len(entries) != 1:
        raise SandboxError("The allowlist must contain exactly one approved folder.")

    configured_root = Path(entries[0])
    if not configured_root.is_absolute():
        raise SandboxError("The approved folder path must be absolute.")

    try:
        root = configured_root.resolve(strict=True)
    except OSError as exc:
        raise SandboxError("The approved folder does not exist or cannot be resolved.") from exc

    if not root.is_dir():
        raise SandboxError("The approved path must be a directory.")

    return root


def resolve_allowed_path(
    path: str | Path,
    *,
    allowed_root: Path | None = None,
) -> Path:
    """Resolve a user path and reject traversal or symlink escapes."""
    raw_path = str(path)
    if not raw_path.strip():
        raise SandboxError("A non-empty file path is required.")

    requested = Path(raw_path)
    if ".." in requested.parts:
        raise SandboxError("Parent-directory traversal is not allowed.")
    if not requested.is_absolute() and requested.drive:
        raise SandboxError("Drive-relative paths are not allowed.")

    root = (allowed_root or load_allowed_root()).resolve(strict=True)
    if not root.is_dir():
        raise SandboxError("The approved path must be a directory.")

    candidate = requested if requested.is_absolute() else root / requested
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise SandboxError("The requested path cannot be resolved safely.") from exc

    if resolved == root or not resolved.is_relative_to(root):
        raise SandboxError("The requested path is outside the approved folder.")

    return resolved
