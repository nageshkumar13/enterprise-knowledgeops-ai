import os
import re

from app.core.errors import BadRequestError


PDF_MIME_TYPES = {"application/pdf"}


def normalize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return sanitized.strip("._") or "document.pdf"


def ensure_pdf(filename: str, content_type: str | None) -> None:
    lower_name = filename.lower()
    if not lower_name.endswith(".pdf"):
        raise BadRequestError("Only PDF files are supported.")
    if content_type and content_type not in PDF_MIME_TYPES:
        raise BadRequestError("Invalid content type. Expected application/pdf.")
