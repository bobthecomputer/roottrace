from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from roottrace.extraction.types import DerivedFile, ExtractionResult


def extract_video(path: Path, work_dir: Path) -> ExtractionResult:
    """Extract minimal metadata and a representative keyframe from a video file."""

    metadata = _probe_video(path)
    derived: list[DerivedFile] = []
    keyframe = _extract_keyframe(path, work_dir)
    if keyframe is not None:
        derived.append(keyframe)
    return ExtractionResult(text=None, metadata=metadata, derived_files=derived)


def _probe_video(path: Path) -> dict[str, Any]:
    if shutil.which("ffprobe") is None:
        return {"ffprobe": "unavailable"}
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_entries",
        "format=duration,size:format_name:stream=codec_name,width,height",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, check=False)  # noqa: S603
    if result.returncode != 0:
        return {"ffprobe_error": result.stderr.decode("utf-8", errors="ignore")}
    try:
        payload = json.loads(result.stdout.decode("utf-8"))
    except json.JSONDecodeError:
        return {"ffprobe_error": "invalid_json"}
    if isinstance(payload, dict):
        return payload
    return {"ffprobe_error": "unexpected_format"}


def _extract_keyframe(path: Path, work_dir: Path) -> DerivedFile | None:
    if shutil.which("ffmpeg") is None:
        return None
    work_dir.mkdir(parents=True, exist_ok=True)
    destination = work_dir / f"{path.stem}_keyframe.jpg"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-vf",
        "select=eq(n\\,0)",
        "-q:v",
        "2",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)  # noqa: S603
    if result.returncode != 0:
        return None
    metadata = {"source": "ffmpeg", "filter": "select=eq(n,0)"}
    return DerivedFile(label="keyframe", path=destination, metadata=metadata)


__all__ = ["extract_video"]
