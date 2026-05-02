from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_with_pymupdf(path: Path) -> str:
    import fitz  # PyMuPDF

    parts: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            parts.append(page.get_text("text"))
    return clean_text("\n".join(parts))


def extract_with_pdfplumber(path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return clean_text("\n".join(parts))


def extract_with_pypdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return clean_text("\n".join(parts))


def extract_with_ocr(path: Path, language: str) -> str:
    from pdf2image import convert_from_path
    import pytesseract

    parts: list[str] = []
    for image in convert_from_path(str(path), dpi=220):
        parts.append(pytesseract.image_to_string(image, lang=language))
    return clean_text("\n".join(parts))


def best_extraction(path: Path, ocr: bool, language: str) -> tuple[str, str]:
    attempts = [
        ("pymupdf", extract_with_pymupdf),
        ("pdfplumber", extract_with_pdfplumber),
        ("pypdf", extract_with_pypdf),
    ]

    best_text = ""
    best_engine = ""
    errors: list[str] = []

    for engine, extractor in attempts:
        try:
            text = extractor(path)
            if len(text) > len(best_text):
                best_text = text
                best_engine = engine
        except Exception as exc:  # noqa: BLE001 - CLI reports all extractor failures.
            errors.append(f"{engine}: {exc}")

    if len(best_text) >= 80:
        return best_text, best_engine

    if ocr:
        try:
            text = extract_with_ocr(path, language)
            if len(text) > len(best_text):
                return text, "ocr"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ocr: {exc}")

    if best_text:
        return best_text, best_engine or "unknown"

    raise RuntimeError("No PDF extractor returned text. " + " | ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--lang", default="por+eng")
    args = parser.parse_args()

    text, engine = best_extraction(args.pdf, args.ocr, args.lang)
    sys.stderr.write(f"engine={engine} chars={len(text)}\n")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
