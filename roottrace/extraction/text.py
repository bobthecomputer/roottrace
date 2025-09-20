from __future__ import annotations

from pathlib import Path

from roottrace.extraction.types import ExtractionResult


def extract_text(path: Path) -> ExtractionResult:
    """Extract plain text content from text-like files."""

    content = path.read_text(encoding="utf-8", errors="ignore")
    metadata = {"length": len(content)}
    return ExtractionResult(text=content, metadata=metadata)


__all__ = ["extract_text"]
