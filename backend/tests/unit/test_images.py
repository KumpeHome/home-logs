from io import BytesIO

import pytest

from app.core.errors import DomainError
from app.storage.images import normalize_image, sniff_image_media_type

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _heic_ftyp() -> bytes:
    return (
        (24).to_bytes(4, "big")
        + b"ftyp"
        + b"heic"
        + b"\x00\x00\x00\x00"
        + b"mif1"
        + b"heic"
        + b"not-a-real-heic-payload"
    )


def _sample_heic() -> bytes:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (200, 10, 10)).save(buffer, format="HEIF")
    return buffer.getvalue()


def test_sniff_detects_png_magic() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert sniff_image_media_type(png) == "image/png"


def test_sniff_rejects_plain_text() -> None:
    with pytest.raises(DomainError, match="JPEG, PNG, GIF, WebP, or HEIC"):
        sniff_image_media_type(b"hello world")


def test_broken_heic_explains_the_format() -> None:
    with pytest.raises(DomainError, match="HEIC"):
        normalize_image(_heic_ftyp())


def test_normalize_image_converts_heic_to_jpeg() -> None:
    data, media_type = normalize_image(_sample_heic())
    assert media_type == "image/jpeg"
    assert data.startswith(b"\xff\xd8")


def test_normalize_image_passes_through_png() -> None:
    data, media_type = normalize_image(PNG_1X1)
    assert media_type == "image/png"
    assert data == PNG_1X1
