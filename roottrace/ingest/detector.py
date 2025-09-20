from __future__ import annotations

from pathlib import Path

import filetype

from roottrace.db.models import ArtifactKind
from roottrace.utils.files import guess_mimetype


class ArtifactDetector:
    """Determine artifact kind using mime detection and heuristics."""

    def detect(self, path: Path, override_mime: str | None = None) -> tuple[ArtifactKind, str]:
        """Return the artifact kind and mime type."""

        kind = filetype.guess(path)
        mime = override_mime or (kind.mime if kind else None)
        if mime is None:
            mime = guess_mimetype(path)
        artifact_kind = self._map_mime_to_kind(mime, path)
        return artifact_kind, mime

    def _map_mime_to_kind(self, mime: str, path: Path) -> ArtifactKind:
        lowered = mime.lower()
        if lowered.startswith("image/"):
            return ArtifactKind.IMAGE
        if lowered.startswith("video/"):
            return ArtifactKind.VIDEO
        if lowered in {"application/pdf", "application/x-pdf"}:
            return ArtifactKind.PDF
        if lowered.startswith("text/"):
            return ArtifactKind.TEXT
        if path.suffix.lower() == ".pdf":
            return ArtifactKind.PDF
        if path.suffix.lower() in {".txt", ".md", ".csv", ".log"}:
            return ArtifactKind.TEXT
        return ArtifactKind.TEXT


__all__ = ["ArtifactDetector"]
