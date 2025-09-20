from __future__ import annotations

from pathlib import Path

from roottrace.ingest.service import IngestService
from roottrace.ui.desktop import RootTraceController


def test_controller_ingest_path(tmp_path: Path, ingest_service: IngestService) -> None:
    sample = tmp_path / "memo.txt"
    sample.write_text("Contact: agent@example.org")
    controller = RootTraceController(service=ingest_service)
    result = controller.ingest_path(sample)
    assert result["job"]["artifact_kind"] == "text"
    assert any(entity["kind"] == "email" for entity in result["entities"])


def test_controller_list_jobs(tmp_path: Path, ingest_service: IngestService) -> None:
    sample = tmp_path / "note.txt"
    sample.write_text("montant 1200 EUR")
    controller = RootTraceController(service=ingest_service)
    controller.ingest_path(sample)
    jobs = controller.list_jobs()
    assert jobs
    assert jobs[0]["job"]["id"] >= 1
