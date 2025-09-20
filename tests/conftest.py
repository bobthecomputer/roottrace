from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from roottrace.api.main import app, get_graph_service, get_ingest_service  # noqa: E402
from roottrace.config import Settings  # noqa: E402
from roottrace.db.base import Base  # noqa: E402
from roottrace.db.session import get_sessionmaker  # noqa: E402
from roottrace.graph.service import GraphService  # noqa: E402
from roottrace.ingest.service import IngestService  # noqa: E402


@pytest.fixture()
def temp_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "artifacts",
        proof_dir=tmp_path / "proofs",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "test.db",
        enable_network_fetch=False,
        legal_note="",
    )


@pytest.fixture()
def session_factory(temp_settings: Settings) -> Iterator[sessionmaker[Session]]:
    factory = get_sessionmaker(temp_settings)
    with factory() as session:
        bind = session.get_bind()
        if bind is not None:
            Base.metadata.create_all(bind=bind)
    yield factory
    with factory() as session:
        bind = session.get_bind()
        if bind is not None:
            Base.metadata.drop_all(bind=bind)


@pytest.fixture()
def ingest_service(
    temp_settings: Settings,
    session_factory: sessionmaker[Session],
) -> IngestService:
    return IngestService(config=temp_settings)


@pytest.fixture()
def graph_service(
    temp_settings: Settings,
    session_factory: sessionmaker[Session],
) -> GraphService:
    return GraphService(config=temp_settings)


@pytest.fixture()
def client(
    temp_settings: Settings,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setattr("roottrace.api.main.get_sessionmaker", lambda: session_factory)
    app.dependency_overrides[get_ingest_service] = lambda: IngestService(
        config=temp_settings
    )
    app.dependency_overrides[get_graph_service] = lambda: GraphService(
        config=temp_settings
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
