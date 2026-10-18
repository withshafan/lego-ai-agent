from __future__ import annotations

import json
from pathlib import Path

import lego.tools.apps as apps_module
from lego.tools.registry import dispatch


def _write_apps_config(path: Path, app_config: object) -> None:
    path.write_text(json.dumps({"notepad": app_config}), encoding="utf-8")


def test_open_allowed_app_uses_only_fixed_allowlisted_arguments(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "allowed_apps.json"
    _write_apps_config(config_path, {"command": "notepad.exe", "args": []})
    monkeypatch.setattr(apps_module, "_APPS_CONFIG_PATH", config_path)
    calls: list[tuple[list[str], bool]] = []

    def fake_popen(command: list[str], *, shell: bool) -> None:
        calls.append((command, shell))

    monkeypatch.setattr(apps_module.subprocess, "Popen", fake_popen)
    result = dispatch("open_allowed_app", {"app": "notepad"})

    assert result.success is True
    assert calls == [(["notepad.exe"], False)]


def test_open_allowed_app_rejects_unlisted_application(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "allowed_apps.json"
    _write_apps_config(config_path, {"command": "notepad.exe", "args": []})
    monkeypatch.setattr(apps_module, "_APPS_CONFIG_PATH", config_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        apps_module.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append(command),
    )

    result = dispatch("open_allowed_app", {"app": "calculator"})

    assert result.success is False
    assert result.error == "Application not allowed."
    assert calls == []


def test_open_allowed_app_does_not_accept_user_controlled_arguments() -> None:
    result = dispatch(
        "open_allowed_app",
        {"app": "notepad", "args": ["unexpected.exe"]},
    )

    assert result.success is False
    assert result.error == "Argument validation failed."


def test_open_allowed_app_returns_safe_error_when_launch_fails(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "allowed_apps.json"
    _write_apps_config(config_path, {"command": "notepad.exe", "args": []})
    monkeypatch.setattr(apps_module, "_APPS_CONFIG_PATH", config_path)

    def fail_to_launch(command: list[str], *, shell: bool) -> None:
        raise OSError("private operating-system detail")

    monkeypatch.setattr(apps_module.subprocess, "Popen", fail_to_launch)
    result = dispatch("open_allowed_app", {"app": "notepad"})

    assert result.success is False
    assert result.error == "Application launch failed."
    assert "private operating-system detail" not in result.message
