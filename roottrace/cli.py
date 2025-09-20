from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import uvicorn

from roottrace import __version__

app = typer.Typer(help="Outil de contrôle RootTrace", add_completion=False)


def _version_callback(
    ctx: typer.Context,
    param: Any,
    value: bool,
) -> bool:
    if value:
        typer.echo(__version__)
        raise typer.Exit()
    return value


@app.callback()
def _main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Afficher la version et quitter.",
    ),
) -> None:
    """Point d'entrée racine."""


@app.command(help="Lancer l'API et l'interface web (FastAPI + UI).")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Adresse d'écoute."),
    port: int = typer.Option(8000, "--port", help="Port HTTP."),
    reload: bool = typer.Option(False, "--reload", help="Activer l'auto-rechargement."),
) -> None:
    uvicorn.run("roottrace.api.main:app", host=host, port=port, reload=reload, factory=False)


@app.command(help="Lancer l'interface graphique Tkinter en local.")
def gui() -> None:
    from roottrace.ui.desktop import run_app

    run_app()


@app.command(help="Construire un exécutable autonome via PyInstaller.")
def build_exe(
    output_dir: Path = typer.Option(Path("dist"), "--output-dir", "-o", help="Dossier dist."),
    onefile: bool = typer.Option(
        True,
        "--onefile/--no-onefile",
        help="Packager en binaire unique.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Afficher la commande PyInstaller sans l'exécuter.",
        show_default=True,
    ),
) -> None:
    entry_point = Path(__file__).resolve().parent / "__main__.py"
    if not entry_point.exists():
        raise typer.BadParameter("Entrypoint __main__.py introuvable pour PyInstaller.")

    build_dir = output_dir / "build"
    spec_dir = output_dir / "spec"
    build_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "--name",
        "RootTrace",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
    ]
    if onefile:
        args.append("--onefile")
    args.append(str(entry_point))

    command_preview = "pyinstaller " + " ".join(args)
    typer.echo(f"Commande PyInstaller: {command_preview}")

    if dry_run:
        typer.echo("Mode dry-run actif : aucune compilation exécutée.")
        return

    try:
        import PyInstaller.__main__ as pyinstaller_main
    except ModuleNotFoundError as exc:  # pragma: no cover - message utilisateur
        raise typer.Exit(code=1) from exc

    pyinstaller_main.run(args)


def main() -> None:  # pragma: no cover - délégué à Typer
    app()


__all__ = ["app", "main"]
