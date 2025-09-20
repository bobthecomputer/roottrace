from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DerivedFile:
    """File produced during extraction that should be tracked as evidence."""

    label: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractionResult:
    """Structured output from an extractor."""

    text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    derived_files: list[DerivedFile] = field(default_factory=list)


__all__ = ["ExtractionResult", "DerivedFile"]
