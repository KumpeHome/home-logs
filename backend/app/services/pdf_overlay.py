from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def overlay_pdf(source: bytes, placeholders: Iterable, values: dict[str, str]) -> bytes:
    writer = PdfWriter()
    writer.append(BytesIO(source))
    for index, page in enumerate(writer.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        overlay = canvas.Canvas(packet, pagesize=(width, height))
        for placeholder in placeholders:
            if int(placeholder.page) != index + 1:
                continue
            text = values.get(placeholder.binding, "")
            overlay.setFont("Helvetica", int(placeholder.font_size or 10))
            overlay.drawString(
                float(placeholder.x), float(placeholder.y), str(text)[:180]
            )
        overlay.save()
        packet.seek(0)
        overlay_page = PdfReader(packet).pages[0]
        page.merge_page(overlay_page)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_blank_pdf(text: str = "Agency Form") -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
