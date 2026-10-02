from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".json", ".png", ".jpg", ".jpeg", ".webp"}


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:150] or "document"


def infer_document_type(filename: str) -> str:
    lower = filename.lower()
    if "gst" in lower:
        return "gst_certificate"
    if "udyam" in lower or "msme" in lower:
        return "udyam"
    if "bank" in lower or "cheque" in lower:
        return "bank_proof"
    if "quote" in lower or "quotation" in lower:
        return "quotation"
    if "invoice" in lower:
        return "invoice"
    return "other"


def save_upload(supplier_id: int, filename: str, content_type: str | None, stream: BinaryIO) -> tuple[Path, int]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Use PDF, text, CSV, JSON, PNG, JPG, or WEBP.")
    safe = _safe_name(filename)
    folder = Path(settings.upload_dir) / str(supplier_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe
    total = 0
    with path.open("wb") as out:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_mb * 1024 * 1024:
                path.unlink(missing_ok=True)
                raise ValueError(f"File exceeds {settings.max_upload_mb} MB limit.")
            out.write(chunk)
    return path, total


def extract_basic_fields(path: Path, document_type: str) -> tuple[dict[str, str], str, str | None]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".csv", ".json"}:
        text = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        fields: dict[str, str] = {}
        patterns = {
            "legal_name": r"(?:legal[_ ]name|company[_ ]name|supplier[_ ]name|account[_ ]name)\s*[:=]\s*(.+)",
            "address": r"(?:registered[_ ]address|address|principal[_ ]place[_ ]of[_ ]business)\s*[:=]\s*(.+)",
            "gstin": r"(?:gstin|gst[_ ]in)\s*[:=]\s*([0-9A-Z]{15})",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.I)
            if match:
                fields[key] = match.group(1).strip()
        return fields, "text", text[:900]
    return {}, "metadata", None
