from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CFS400_TEMPLATE = (
    Path(__file__).resolve().parent
    / "templates"
    / "ar_dcfs"
    / "sibling_contact_log.pdf"
)
CFS400_ROWS_PER_PAGE = 6


def initials_cell(value: str) -> Any:
    text = (value or "").strip()
    if not text.startswith("data:image"):
        return text
    try:
        _header, encoded = text.split(",", 1)
        raw = base64.b64decode(encoded)
    except (ValueError, OSError):
        return ""
    return Image(BytesIO(raw), width=0.7 * inch, height=0.32 * inch)


def _styles():
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 16
    styles["Normal"].fontName = "Helvetica"
    styles["Normal"].fontSize = 10
    return styles


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.90, 0.90, 0.90)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def quarterly_drills_pdf(rows: list[tuple[str, str, str]]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = _styles()
    data = [
        [
            "Date and Time drill was completed",
            "Participants",
            "Time it took to clear the home",
        ]
    ]
    if rows:
        data.extend([list(row) for row in rows])
    else:
        data.append(["", "", ""])
    table = Table(data, colWidths=[3.2 * inch, 4.4 * inch, 2.2 * inch])
    table.setStyle(_table_style())
    doc.build(
        [
            Paragraph("Quarterly Fire/Tornado Drills", styles["Title"]),
            Spacer(1, 8),
            Paragraph(
                "Fire and Tornado drills should be completed in a timely manner "
                "after receiving each new placement and then quarterly.",
                styles["Normal"],
            ),
            Spacer(1, 14),
            table,
        ]
    )
    return buffer.getvalue()


def medication_log_pdf(
    pages: list[tuple[str, list[tuple[Any, ...]]]],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = _styles()
    story: list = []
    if not pages:
        pages = [("", [])]
    for index, (child_name, rows) in enumerate(pages):
        if index:
            story.append(PageBreak())
        story.append(Paragraph("MEDICATION DOSAGE LOGS", styles["Title"]))
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                f"Childs Name: {child_name or '________________'}", styles["Normal"]
            )
        )
        story.append(Spacer(1, 12))
        data = [
            [
                "MEDICATION NAME",
                "DOSAGE",
                "DATE GIVEN",
                "TIME GIVEN",
                "FP INITIAL",
                "FC INITIAL (If age appropriate)",
            ]
        ]
        if rows:
            data.extend([list(row) for row in rows])
        else:
            data.append(["", "", "", "", "", ""])
        table = Table(
            data,
            colWidths=[
                1.5 * inch,
                1.0 * inch,
                1.1 * inch,
                1.0 * inch,
                0.9 * inch,
                1.7 * inch,
            ],
        )
        table.setStyle(_table_style())
        story.append(table)
    doc.build(story)
    return buffer.getvalue()


def _cfs400_row_fields(page) -> dict[int, list[str]]:
    rows: dict[int, list[tuple[float, str]]] = {}
    for annot in page.get("/Annots") or []:
        obj = annot.get_object()
        name = str(obj.get("/T") or "")
        if not name.endswith(("Row1", "Row2", "Row3", "Row4", "Row5")):
            continue
        row = int(name[-1])
        rows.setdefault(row, []).append((float(obj["/Rect"][0]), name))
    return {row: [name for _, name in sorted(cols)] for row, cols in rows.items()}


def _cfs400_row_rects(page) -> list[list[list[float]]]:
    field_rects: dict[str, list[float]] = {}
    for annot in page.get("/Annots") or []:
        obj = annot.get_object()
        name = str(obj.get("/T") or "")
        field_rects[name] = [float(value) for value in obj["/Rect"]]
    columns = _cfs400_row_fields(page)
    field_rows: list[list[list[float]]] = []
    for index in range(1, 6):
        rects = [
            field_rects[name]
            for name in columns.get(index) or []
            if name in field_rects
        ]
        if rects:
            field_rows.append(rects)
    if not field_rows:
        return []
    first = field_rows[0]
    height = first[0][3] - first[0][1]
    gap = first[0][1] - field_rows[1][0][3] if len(field_rows) > 1 else 2.0
    lifted = [
        [rect[0], rect[3] + gap, rect[2], rect[3] + gap + height] for rect in first
    ]
    return [lifted, *field_rows]


def _wrap_lines(painter: canvas.Canvas, text: str, width: float) -> list[str]:
    words = str(text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if painter.stringWidth(trial) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_boxed(
    painter: canvas.Canvas, text: str, rect: list[float], size: float = 8
) -> None:
    x0, y0, x1, y1 = rect
    width = x1 - x0 - 6
    height = y1 - y0 - 4
    painter.setFont("Helvetica", size)
    lines = _wrap_lines(painter, text, width)
    leading = size + 1.5
    max_lines = max(1, int(height // leading))
    top = y1 - size - 2
    for index, line in enumerate(lines[:max_lines]):
        painter.drawString(x0 + 3, top - index * leading, line)


def _cfs400_overlay(
    page, home_line: str, rows: list[tuple[str, str, str, str]]
) -> bytes:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    packet = BytesIO()
    painter = canvas.Canvas(packet, pagesize=(width, height))
    field_rects: dict[str, list[float]] = {}
    for annot in page.get("/Annots") or []:
        obj = annot.get_object()
        name = str(obj.get("/T") or "")
        field_rects[name] = [float(value) for value in obj["/Rect"]]
    home_rect = field_rects.get("Foster Home Name and Provider ID")
    if home_rect and home_line:
        _draw_boxed(painter, home_line, home_rect, size=10)
    for rects, row in zip(
        _cfs400_row_rects(page), rows[:CFS400_ROWS_PER_PAGE], strict=False
    ):
        for rect, value in zip(rects, row, strict=False):
            if value:
                _draw_boxed(painter, value, rect)
    painter.save()
    return packet.getvalue()


def _fill_cfs400_page(home_line: str, rows: list[tuple[str, str, str, str]]) -> bytes:
    reader = PdfReader(CFS400_TEMPLATE)
    writer = PdfWriter()
    writer.append(reader)
    page = writer.pages[0]
    overlay = PdfReader(BytesIO(_cfs400_overlay(page, home_line, rows)))
    page.merge_page(overlay.pages[0])
    if NameObject("/Annots") in page:
        del page[NameObject("/Annots")]
    if NameObject("/AcroForm") in writer._root_object:
        del writer._root_object[NameObject("/AcroForm")]
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def sibling_contact_pdf(home_line: str, rows: list[tuple[str, str, str, str]]) -> bytes:
    chunks = [
        rows[index : index + CFS400_ROWS_PER_PAGE]
        for index in range(0, max(len(rows), 1), CFS400_ROWS_PER_PAGE)
    ]
    if not rows:
        chunks = [[]]
    writer = PdfWriter()
    for chunk in chunks:
        writer.append(BytesIO(_fill_cfs400_page(home_line, chunk)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
