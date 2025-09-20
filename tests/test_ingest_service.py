from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from roottrace.graph.service import GraphService
from roottrace.ingest.service import IngestService


def write_text_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_ingest_text_file_generates_entities_and_proof(
    tmp_path: Path,
    ingest_service: IngestService,
) -> None:
    text_path = write_text_file(
        tmp_path / "statement.txt",
        "Email: agent@example.org\nMontant: 999,00 €\nBulletin de salaire",
    )

    job = ingest_service.ingest_path(text_path)

    assert job.summary["entities"] >= 2
    assert "proof_archive" in job.summary
    archive = Path(job.summary["proof_archive"])
    assert archive.exists()
    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        assert "ingest.json" in names
        assert "audit.jsonl" in names


def test_graph_service_builds_nodes(tmp_path: Path, ingest_service: IngestService) -> None:
    text_path = write_text_file(tmp_path / "doc.txt", "Contact support@example.com")
    job = ingest_service.ingest_path(text_path)

    graph = GraphService(config=ingest_service.config).build_graph()
    node_ids = {node["id"] for node in graph["nodes"]}

    assert f"job:{job.id}" in node_ids
