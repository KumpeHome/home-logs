from __future__ import annotations

from pathlib import Path

from app.core.errors import DomainError
from app.storage.images import IMAGE_EXTENSIONS, is_heic, normalize_image

PDF_TYPE = "application/pdf"
_UNSUPPORTED_CERTIFICATE = (
    "Certificate must be a PDF or a JPEG, PNG, GIF, WebP, or HEIC image"
)


def is_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF")


def normalize_certificate(filename: str, data: bytes) -> tuple[bytes, str, str]:
    stem = Path(filename).stem or "certificate"
    if is_pdf(data):
        return data, PDF_TYPE, f"{stem}.pdf"
    try:
        data, media_type = normalize_image(data)
    except DomainError:
        if is_heic(data):
            raise
        raise DomainError(_UNSUPPORTED_CERTIFICATE) from None
    return data, media_type, f"{stem}{IMAGE_EXTENSIONS[media_type]}"
