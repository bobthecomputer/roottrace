from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from roottrace.config import Settings, build_sqlite_url
from roottrace.db.session import get_sessionmaker, session_scope
from roottrace.scraper.manager import ScraperManager
from roottrace.utils.audit import AuditTrail
from roottrace.utils.files import download_url, guess_mimetype, resolve_artifact_path


def test_audit_trail_redacts_sensitive_fields(tmp_path: Path) -> None:
    trail = AuditTrail(tmp_path)
    trail.record("info", "test", email="analyste@example.com", phone="+33612345678")
    stored = trail.events[0].to_dict()

    assert "***@" in stored["details"]["email"]
    assert stored["details"]["phone"].startswith("+***")


def test_scraper_manager_requires_legal_note(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        proof_dir=tmp_path / "proof",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "db.sqlite3",
        scraper_platform="instagram",
        scraper_tool="instaloader",
        legal_note="",
    )
    manager = ScraperManager(config=settings)

    with pytest.raises(PermissionError):
        manager.build_plan()

    settings.legal_note = "DPIA-OK"
    plan = manager.build_plan()
    assert plan is not None
    assert plan.platform == "instagram"


def test_resolve_artifact_path_keeps_extension(tmp_path: Path) -> None:
    path = resolve_artifact_path("evidence.pdf", tmp_path)
    assert path.suffix == ".pdf"
    assert path.parent == tmp_path


def test_guess_mimetype(tmp_path: Path) -> None:
    sample = tmp_path / "note.txt"
    sample.write_text("hello", encoding="utf-8")
    assert guess_mimetype(sample).startswith("text/")


def test_download_url_requires_network_enabled(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        proof_dir=tmp_path / "proof",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "db.sqlite3",
        enable_network_fetch=False,
    )
    with pytest.raises(RuntimeError):
        download_url("https://example.com/file.txt", tmp_path / "file.txt", config=settings)


def test_build_sqlite_url_handles_suffix(tmp_path: Path) -> None:
    db_file = tmp_path / "audit.db"
    url = build_sqlite_url(db_file)
    assert url.startswith("sqlite+")
    alt_url = build_sqlite_url(tmp_path)
    assert alt_url.startswith("sqlite:///")


def test_session_scope_reuses_sessionmaker(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        proof_dir=tmp_path / "proof",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "db.sqlite3",
    )
    factory = get_sessionmaker(settings)
    assert get_sessionmaker(settings) is factory
    with session_scope(settings) as session:
        session.execute(text("SELECT 1"))
