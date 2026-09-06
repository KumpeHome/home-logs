from __future__ import annotations

from io import BytesIO

from app.core.errors import DomainError

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

_HEIC_BRANDS = (b"heic", b"heif", b"heix", b"heim", b"heis", b"mif1", b"msf1")
_HEIC_UNREADABLE = (
    "This HEIC photo could not be read. Save it as JPEG or PNG and try again."
)
_UNSUPPORTED = "File must be a JPEG, PNG, GIF, WebP, or HEIC image"


def _ftyp_brands(data: bytes) -> bytes:
    if len(data) < 12 or data[4:8] != b"ftyp":
        return b""
    size = int.from_bytes(data[0:4], "big")
    end = size if 16 <= size <= len(data) else min(len(data), 64)
    return data[8:end]


def is_heic(data: bytes) -> bool:
    brands = _ftyp_brands(data)
    if not brands or b"avif" in brands:
        return False
    return any(tag in brands for tag in _HEIC_BRANDS)


def sniff_image_media_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if is_heic(data):
        raise DomainError(_HEIC_UNREADABLE)
    raise DomainError(_UNSUPPORTED)


def convert_heic_to_jpeg(data: bytes) -> bytes:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    with Image.open(BytesIO(data)) as image:
        rgb = image.convert("RGB")
        out = BytesIO()
        rgb.save(out, format="JPEG", quality=90)
        return out.getvalue()


def normalize_image(data: bytes) -> tuple[bytes, str]:
    if is_heic(data):
        try:
            data = convert_heic_to_jpeg(data)
        except Exception as exc:
            raise DomainError(_HEIC_UNREADABLE) from exc
    return data, sniff_image_media_type(data)
