from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from PIL import Image

from roottrace.extraction.image import extract_image
from roottrace.extraction.pdf import extract_pdf
from roottrace.extraction.text import extract_text
from roottrace.extraction.video import extract_video


def test_extract_image_returns_metadata(tmp_path: Path) -> None:
    image_path = tmp_path / "example.png"
    image = Image.new("RGB", (64, 32), color=(255, 0, 0))
    image.save(image_path)

    result = extract_image(image_path)

    assert result.metadata["width"] == 64
    assert "phash" in result.metadata


def test_extract_text(tmp_path: Path) -> None:
    text_path = tmp_path / "note.txt"
    text_path.write_text("hello", encoding="utf-8")

    result = extract_text(text_path)

    assert result.text == "hello"
    assert result.metadata["length"] == 5


def test_extract_pdf_counts_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    image = Image.new("RGB", (10, 10), color=(0, 0, 0))
    image.save(pdf_path, "PDF")

    result = extract_pdf(pdf_path)

    assert result.metadata["pages"] >= 1


def test_extract_video_handles_missing_binaries(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"")

    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = extract_video(video_path, tmp_path / "frames")

    assert result.metadata == {"ffprobe": "unavailable"}
    assert not result.derived_files


def test_extract_video_generates_keyframe(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"")

    def fake_which(name: str) -> str:
        return f"/usr/bin/{name}"

    def fake_run(
        command: Sequence[str],
        capture_output: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        if command[0] == "ffprobe":
            payload = b'{"format": {"duration": "1"}}'
            return subprocess.CompletedProcess(command, 0, stdout=payload, stderr=b"")
        if command[0] == "ffmpeg":
            destination = tmp_path / "frames" / f"{video_path.stem}_keyframe.jpg"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"jpegdata")
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")
        raise AssertionError(f"Unexpected command {command}")

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = extract_video(video_path, tmp_path / "frames")

    assert result.metadata["format"]["duration"] == "1"
    assert result.derived_files and result.derived_files[0].path.exists()
