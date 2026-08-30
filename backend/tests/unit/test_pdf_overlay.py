from io import BytesIO
from types import SimpleNamespace

from pypdf import PdfReader

from app.services.pdf_overlay import make_blank_pdf, overlay_pdf


def test_overlay_writes_bound_text_onto_pdf() -> None:
    source = make_blank_pdf("Case Worker Visit")
    placeholders = [
        SimpleNamespace(
            binding="member.legal_name",
            page=1,
            x=72,
            y=680,
            width=200,
            height=16,
            font_size=12,
            align="left",
        )
    ]
    result = overlay_pdf(source, placeholders, {"member.legal_name": "Casey Child"})
    assert result.startswith(b"%PDF")
    text = "".join(
        (page.extract_text() or "") for page in PdfReader(BytesIO(result)).pages
    )
    assert "Casey Child" in text
