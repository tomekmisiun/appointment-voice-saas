import pytest

from app.core.domain_errors import BadRequestError
from app.core.file_validation import sniff_content_type, validate_content_sniff


PDF_BYTES = b"%PDF-1.4 test"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"data"


def test_sniff_content_type_detects_pdf():
    assert sniff_content_type(PDF_BYTES) == "application/pdf"


def test_validate_content_sniff_rejects_mismatched_declared_type():
    with pytest.raises(BadRequestError) as exc_info:
        validate_content_sniff("application/pdf", PNG_BYTES)

    assert exc_info.value.status_code == 400
