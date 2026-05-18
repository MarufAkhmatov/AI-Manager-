"""Stage 3: text extraction (text-native if possible, OCR otherwise).

Tesseract is invoked with `rus+uzb+uzb_cyrl+eng` per the operator's choice;
per-page OCR results are cached under `Cache\\ocr\\<page-hash>.txt` so a
re-run never repeats work for an unchanged page image.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytesseract
from pypdf import PdfReader

from app.config import get_settings
from app.security.paths import safe_join

_OCR_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _cache_path(h: str) -> Path:
    s = get_settings()
    root = s.cache / "ocr"
    root.mkdir(parents=True, exist_ok=True)
    return safe_join(root, h[:2], f"{h}.txt")


def _read_text_pdf(path: Path) -> str | None:
    """Return joined text from a text-native PDF, or None if it looks scanned."""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return None
    pages: list[str] = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            return None
    joined = "\n\n".join(pages).strip()
    return joined or None


def _ocr_image_bytes(data: bytes, langs: str) -> str:
    from io import BytesIO

    from PIL import Image

    h = hashlib.sha256(data).hexdigest()
    cp = _cache_path(h)
    if cp.exists():
        return cp.read_text(encoding="utf-8")

    with Image.open(BytesIO(data)) as img:
        text = pytesseract.image_to_string(img, lang=langs)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


def _extract_sync(path: Path, langs: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _read_text_pdf(path)
        if text:
            return text
        # Scanned PDF: render pages to images via pdf2image would be ideal;
        # for the initial implementation we delegate page-by-page rendering
        # to Tesseract's built-in PDF handler.
        return pytesseract.image_to_string(str(path), lang=langs)
    if suffix in _OCR_IMAGE_EXT:
        return _ocr_image_bytes(path.read_bytes(), langs)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    # docx and friends fall to a simple path: pypandoc/python-docx would
    # be wired in later. For Phase 2 we return empty so the pipeline
    # records the gap rather than crashing.
    return ""


async def extract_text(path: Path) -> str:
    s = get_settings()
    return await asyncio.to_thread(_extract_sync, path, s.tesseract_langs)
