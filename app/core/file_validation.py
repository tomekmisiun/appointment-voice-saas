from app.core.config import settings
from app.core.domain_errors import BadRequestError
from app.core.malware_scan import MalwareScanResult, ensure_malware_scan_is_clean
from app.core.upload_metadata import validate_content_type_format
from app.services.malware_scanner import get_malware_scanner


CONTENT_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}


def sniff_content_type(body: bytes) -> str | None:
    for content_type, signatures in CONTENT_SIGNATURES.items():
        if any(body.startswith(signature) for signature in signatures):
            return content_type

    return None


def validate_declared_content_type(content_type: str | None) -> str:
    if content_type is None:
        raise BadRequestError("Unsupported file type")

    normalized_content_type = validate_content_type_format(content_type)
    allowed_content_types = {
        value.strip().lower()
        for value in settings.upload_allowed_content_types.split(",")
        if value.strip()
    }

    if normalized_content_type not in allowed_content_types:
        raise BadRequestError("Unsupported file type")

    return normalized_content_type


def validate_content_sniff(declared_content_type: str, body: bytes) -> None:
    sniffed_content_type = sniff_content_type(body)

    if sniffed_content_type != declared_content_type:
        raise BadRequestError("File content does not match declared content type")


def run_malware_scan(body: bytes, filename: str) -> MalwareScanResult:
    return get_malware_scanner().scan(body, filename)


def scan_uploaded_file(body: bytes, filename: str) -> MalwareScanResult:
    """Backward-compatible wrapper for downstream scanner overrides in tests."""

    return run_malware_scan(body, filename)


__all__ = [
    "MalwareScanResult",
    "ensure_malware_scan_is_clean",
    "run_malware_scan",
    "scan_uploaded_file",
    "sniff_content_type",
    "validate_content_sniff",
    "validate_declared_content_type",
]
