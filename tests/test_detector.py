from __future__ import annotations

from pathlib import Path

from roottrace.db.models import ArtifactKind
from roottrace.ingest.detector import ArtifactDetector


def test_artifact_detector_uses_extension(tmp_path: Path) -> None:
    detector = ArtifactDetector()
    text_file = tmp_path / "notes.txt"
    text_file.write_text("hello", encoding="utf-8")
    kind, mime = detector.detect(text_file)
    assert kind is ArtifactKind.TEXT
    assert mime.startswith("text/")


def test_artifact_detector_pdf_suffix(tmp_path: Path) -> None:
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"%PDF-1.0\n%EOF")
    kind, _ = ArtifactDetector().detect(pdf_file)
    assert kind is ArtifactKind.PDF
