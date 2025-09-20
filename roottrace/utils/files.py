from __future__ import annotations

import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import IO
from uuid import uuid4

import requests

from roottrace.config import Settings, settings


def timestamped_stem(prefix: str) -> str:
    """Return a safe stem combining prefix, timestamp and a random suffix."""

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"{prefix}-{now}-{uuid4().hex[:8]}"


def resolve_artifact_path(original_name: str | None, directory: Path) -> Path:
    """Return a deterministic path for storing an artifact."""

    extension = Path(original_name or "artifact.bin").suffix
    stem = timestamped_stem("artifact")
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{stem}{extension}"


def save_stream_to_path(stream: IO[bytes], destination: Path) -> Path:
    """Persist a binary stream to the destination path."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        shutil.copyfileobj(stream, handle)
    return destination


def download_url(url: str, destination: Path, config: Settings = settings) -> tuple[Path, str]:
    """Download a URL to the destination path if network access is allowed."""

    if not config.enable_network_fetch:
        msg = "Network fetching disabled by configuration"
        raise RuntimeError(msg)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    content_type = response.headers.get("Content-Type", "application/octet-stream")
    return destination, content_type


def guess_mimetype(path: Path, fallback: str = "application/octet-stream") -> str:
    """Guess mimetype using Python's mimetypes library."""

    guess, _ = mimetypes.guess_type(path)
    return guess or fallback


__all__ = [
    "timestamped_stem",
    "resolve_artifact_path",
    "save_stream_to_path",
    "download_url",
    "guess_mimetype",
]
