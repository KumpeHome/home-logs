from app.storage.images import sniff_image_media_type


def test_sniff_detects_png_magic() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert sniff_image_media_type(png) == "image/png"


def test_sniff_rejects_plain_text() -> None:
    try:
        sniff_image_media_type(b"hello world")
    except Exception as exc:
        assert "image" in str(exc).lower()
        return
    raise AssertionError("expected rejection")
