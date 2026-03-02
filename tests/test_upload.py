import pytest

from app.core.errors import BadRequestError
from app.utils.file_utils import ensure_pdf


def test_ensure_pdf_accepts_valid_pdf() -> None:
    ensure_pdf("policy.pdf", "application/pdf")


def test_ensure_pdf_rejects_non_pdf_extension() -> None:
    with pytest.raises(BadRequestError):
        ensure_pdf("policy.txt", "text/plain")
