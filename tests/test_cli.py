from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from roottrace import __version__
from roottrace.cli import app


def test_cli_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_build_exe_dry_run(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["build-exe", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "pyinstaller" in result.stdout.lower()
    assert (tmp_path / "build").exists()
    assert (tmp_path / "spec").exists()


def test_cli_build_exe_execute(tmp_path: Path, monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def fake_run(args: list[str]) -> None:
        recorded["args"] = args

    monkeypatch.setattr("PyInstaller.__main__.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build-exe", "--output-dir", str(tmp_path), "--execute"],
    )
    assert result.exit_code == 0
    assert recorded["args"][-1].endswith("__main__.py")


def test_cli_serve_invokes_uvicorn(monkeypatch: Any) -> None:
    called: dict[str, Any] = {}

    def fake_run(app_path: str, **options: Any) -> None:
        called["app"] = app_path
        called["options"] = options

    monkeypatch.setattr("roottrace.cli.uvicorn.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9001"])
    assert result.exit_code == 0
    assert called["app"] == "roottrace.api.main:app"
    assert called["options"]["port"] == 9001


def test_cli_gui_triggers_desktop(monkeypatch: Any) -> None:
    invoked: dict[str, bool] = {"called": False}

    def fake_run_app() -> None:
        invoked["called"] = True

    monkeypatch.setattr("roottrace.ui.desktop.run_app", fake_run_app)
    runner = CliRunner()
    result = runner.invoke(app, ["gui"])
    assert result.exit_code == 0
    assert invoked["called"] is True
