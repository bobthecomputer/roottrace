from __future__ import annotations

from pathlib import Path
from typing import Any

import exifread
from imagehash import phash
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractError, TesseractNotFoundError, image_to_string

from roottrace.extraction.types import DerivedFile, ExtractionResult


def extract_image(path: Path) -> ExtractionResult:
    """Extract OCR text, EXIF metadata and perceptual hash from an image."""

    metadata: dict[str, Any] = {}
    derived: list[DerivedFile] = []

    metadata.update(_collect_exif(path))

    try:
        with Image.open(path) as image:
            metadata["width"], metadata["height"] = image.size
            metadata["format"] = image.format
            metadata["mode"] = image.mode
            metadata["phash"] = str(phash(image))
            text = _try_ocr(image)
    except UnidentifiedImageError:
        text = None

    return ExtractionResult(text=text, metadata=metadata, derived_files=derived)


def _collect_exif(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        tags = exifread.process_file(stream, details=False)
    return {key: str(value) for key, value in tags.items()}


def _try_ocr(image: Image.Image) -> str | None:
    try:
        extracted = image_to_string(image)
    except (TesseractNotFoundError, TesseractError):
        return None
    text = extracted.strip()
    return text or None


__all__ = ["extract_image"]
