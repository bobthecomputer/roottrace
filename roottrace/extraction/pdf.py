from __future__ import annotations

from pathlib import Path
from typing import Any

from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser, PDFSyntaxError

from roottrace.extraction.types import ExtractionResult


def extract_pdf(path: Path) -> ExtractionResult:
    """Extract text and metadata from PDF documents."""

    try:
        text = pdf_extract_text(path)
    except PDFSyntaxError:
        text = None
    metadata = _collect_pdf_metadata(path)
    return ExtractionResult(text=text, metadata=metadata)


def _collect_pdf_metadata(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    with path.open("rb") as handle:
        parser = PDFParser(handle)
        document = PDFDocument(parser)
        metadata["is_extractable"] = bool(document.is_extractable)
        if document.info:
            first = document.info[0]
            for key, value in first.items():
                if isinstance(key, bytes):
                    key_text = key.decode("utf-8", "ignore")
                else:
                    key_text = str(key)
                metadata[f"info_{key_text}"] = str(value)
        metadata["pages"] = sum(1 for _ in PDFPage.create_pages(document))
    return metadata


__all__ = ["extract_pdf"]
