from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.exports.pdfs import _styles, _table_style, initials_cell
from app.forms.catalog import BELONGING_CATEGORIES


def _footer_number(number: str, *, right: bool = False):
    def _draw(painter, doc) -> None:
        painter.saveState()
        painter.setFont("Helvetica", 8)
        y = 0.4 * inch
        if right:
            painter.drawRightString(float(doc.pagesize[0]) - 0.5 * inch, y, number)
        else:
            painter.drawString(0.5 * inch, y, number)
        painter.restoreState()

    return _draw


_WEEKDAYS = (
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
)

_WEEKLY_GRID_STYLE = TableStyle(
    [
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 1), 7),
        ("FONTSIZE", (0, 2), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("SPAN", (4, 0), (5, 0)),
        ("SPAN", (6, 0), (7, 0)),
        ("SPAN", (8, 0), (9, 0)),
        ("SPAN", (10, 0), (11, 0)),
        ("SPAN", (12, 0), (13, 0)),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
)


def _weekly_grid(med: dict) -> Table:
    header_row: list[str] = []
    sub_row: list[str] = []
    for day in _WEEKDAYS:
        header_row.extend([day, ""])
        sub_row.extend(["TIME", "INITIAL"])
    data = [header_row, sub_row]
    doses = med.get("days") or {}
    for row_index in range(2):
        row: list = []
        for day_index in range(7):
            entries = doses.get(day_index) or []
            time_val, initial = (
                entries[row_index] if row_index < len(entries) else ("", "")
            )
            row.extend(
                [
                    str(time_val),
                    initials_cell(
                        str(initial or ""),
                        width=0.55 * inch,
                        height=0.20 * inch,
                    ),
                ]
            )
        data.append(row)
    table = Table(data, colWidths=[0.72 * inch] * 14, rowHeights=[14, 12, 22, 22])
    table.setStyle(_WEEKLY_GRID_STYLE)
    return table


def weekly_med_chart_pdf(
    pages: list[tuple[str, str, str, list[dict]]],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = _styles()
    title = ParagraphStyle(
        "WeeklyTitle",
        parent=styles["Title"],
        alignment=1,
        fontSize=14,
    )
    story: list = []
    if not pages:
        pages = [("", "", "", [])]
    for index, (child_name, start, end, meds) in enumerate(pages):
        if index:
            story.append(PageBreak())
        story.append(Paragraph("Weekly Medication Chart", title))
        story.append(Spacer(1, 6))
        header = Table(
            [
                [
                    Paragraph(
                        f"Name: {child_name or '________________'}", styles["Normal"]
                    ),
                    Paragraph(f"DATES: {start} - {end}", styles["Normal"]),
                ]
            ],
            colWidths=[5.0 * inch, 5.0 * inch],
        )
        story.append(header)
        story.append(Spacer(1, 8))
        slots = list(meds[:4]) + [{}] * (4 - len(meds[:4]))
        for med in slots:
            name = med.get("name") or "________________"
            dose = med.get("dose") or "________________"
            frequency = med.get("frequency") or "________________"
            story.append(
                Paragraph(
                    f"Medication: {name}&nbsp;&nbsp;&nbsp;"
                    f"Dose: {dose}&nbsp;&nbsp;&nbsp;"
                    f"Frequency: {frequency}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 3))
            story.append(_weekly_grid(med))
            story.append(Spacer(1, 8))
    number = _footer_number("CFS-372 (03/2021)", right=True)
    doc.build(story, onFirstPage=number, onLaterPages=number)
    return buffer.getvalue()


def journal_entries_pdf(pages: list[tuple[str, list[tuple[str, str, str]]]]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = _styles()
    title = ParagraphStyle(
        "JournalTitle",
        parent=styles["Title"],
        alignment=1,
        fontSize=16,
        leading=20,
    )
    body = ParagraphStyle(
        "JournalBody", parent=styles["Normal"], alignment=0, leading=13
    )
    story: list = []
    sheets: list[tuple[str, list[tuple[str, str, str]]]] = []
    if not pages:
        pages = [("", [])]
    for child_name, rows in pages:
        filled = list(rows) or [("", "", "")]
        for start in range(0, len(filled), 8):
            chunk = list(filled[start : start + 8])
            while len(chunk) < 8:
                chunk.append(("", "", ""))
            sheets.append((child_name, chunk))
    for index, (child_name, filled) in enumerate(sheets):
        if index:
            story.append(PageBreak())
        story.append(Paragraph("<u>Journal Entries</u>", title))
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "Please use this form to document incidents that involve bruises, "
                "scrapes, cuts, etc. on a child; medication changes that impact the "
                "child behavior; unusual behaviors in the child, etc.",
                body,
            )
        )
        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                f"Child's Name: {child_name or '________________________________'}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))
        data = [["Date", "Time", "Incident"]]
        data.extend([list(row) for row in filled])
        table = Table(
            data,
            colWidths=[1.2 * inch, 1.1 * inch, 4.8 * inch],
            rowHeights=[18] + [36] * len(filled),
        )
        table.setStyle(_table_style())
        story.append(table)
    doc.build(story)
    return buffer.getvalue()


_BELONGING_LAYOUT: tuple[tuple[str, int], ...] = (
    ("Shoes", 4),
    ("Pairs of Socks", 1),
    ("Underwear", 1),
    ("Bras", 1),
    ("Pantyhose", 1),
    ("Dress Slip", 1),
    ("T-Shirts", 1),
    ("Tank Top", 1),
    ("Sweat Shirts/Hoodies", 1),
    ("Dress Shirts", 1),
    ("Jeans", 1),
    ("Dress Pants", 1),
    ("Dresses", 1),
    ("Skirts", 1),
    ("Shorts", 1),
    ("", 1),
    ("Belts", 1),
    ("Scarfs", 1),
    ("Hats", 1),
    ("Gloves", 1),
    ("Coats", 1),
    ("Jackets", 1),
    ("", 1),
    ("Other", 4),
)

_BELONGING_TABLE_STYLE = TableStyle(
    [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.90, 0.90, 0.90)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
)

BelongingItem = tuple[str, str, str, str, str]


def _belonging_cell(category: str, index: int, item: BelongingItem | None) -> str:
    label = category if index == 0 and category else ""
    description = item[1] if item else ""
    if category == "Other" and index == 0:
        return (
            "Other (list any other personal possessions such as makeup, "
            "wallets, electronics, bedding): "
            f"{description}"
        ).rstrip()
    if label and description:
        return f"{label}: {description}"
    if label:
        return f"{label}:"
    return description


def _fill_belonging_page(
    items: list[BelongingItem], tiny: ParagraphStyle
) -> tuple[list[list], list[BelongingItem]]:
    by_category: dict[str, list[BelongingItem]] = {
        category: [] for category in BELONGING_CATEGORIES
    }
    leftover: list[BelongingItem] = []
    for item in items:
        category = item[0]
        if category in by_category:
            by_category[category].append(item)
        else:
            leftover.append(item)
    by_category["Other"].extend(leftover)
    leftover = []
    header = [
        Paragraph(
            "Item(s) <font size='7'>(can list description, condition, size for "
            "tracking and for demonstrating need for clothing vouchers using "
            "separate sheet as necessary)</font>",
            tiny,
        ),
        Paragraph("Quantity", tiny),
        Paragraph("Date/Initials", tiny),
        Paragraph(
            "Disposition, (thrown away, donated, outgrown) Purchases /Date",
            tiny,
        ),
    ]
    data: list[list] = [header]
    for category, slots in _BELONGING_LAYOUT:
        rows = list(by_category.get(category) or [])
        if category == "":
            data.append(["", "", "", ""])
            leftover.extend(rows)
            continue
        used = min(len(rows), max(slots, 1))
        for index in range(max(slots, 1)):
            item = rows[index] if index < len(rows) else None
            data.append(
                [
                    _belonging_cell(category, index, item),
                    item[2] if item else "",
                    item[3] if item else "",
                    item[4] if item else "",
                ]
            )
        leftover.extend(rows[used:])
    return data, leftover


def personal_belonging_pdf(
    child_name: str, items: list[tuple[str, str, str, str, str]]
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = _styles()
    center = ParagraphStyle("Center", parent=styles["Normal"], alignment=1, fontSize=11)
    title = ParagraphStyle(
        "BelongTitle", parent=styles["Title"], alignment=1, fontSize=14
    )
    tiny = ParagraphStyle("Tiny", parent=styles["Normal"], fontSize=7, leading=8)
    remaining = list(items)
    story: list = []
    page_index = 0
    while True:
        data, remaining = _fill_belonging_page(remaining, tiny)
        if page_index:
            story.append(PageBreak())
        story.extend(
            [
                Paragraph("Division of Children and Family Services", center),
                Spacer(1, 4),
                Paragraph("Personal Belonging Inventory Log", title),
                Spacer(1, 6),
                Paragraph(
                    f"Child: {child_name or '________________________'}",
                    center,
                ),
                Spacer(1, 8),
            ]
        )
        table = Table(
            data,
            colWidths=[3.4 * inch, 0.85 * inch, 1.15 * inch, 1.8 * inch],
            rowHeights=[36] + [14.5] * (len(data) - 1),
        )
        table.setStyle(_BELONGING_TABLE_STYLE)
        story.append(table)
        page_index += 1
        if not remaining:
            break
    number = _footer_number("CFS-350 (01/2021)")
    doc.build(story, onFirstPage=number, onLaterPages=number)
    return buffer.getvalue()


def foster_home_log_pdf(
    month_name: str,
    trainings: list[str],
    drills: list[str],
    visits: list[tuple[str, str, str]],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = _styles()
    heading = ParagraphStyle(
        "FosterTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        alignment=1,
        fontSize=18,
        spaceAfter=4,
    )
    month = ParagraphStyle(
        "FosterMonth",
        parent=styles["Title"],
        fontName="Times-Bold",
        alignment=1,
        fontSize=14,
        spaceAfter=18,
    )
    section = ParagraphStyle(
        "FosterSection",
        parent=styles["Normal"],
        fontName="Times-Bold",
        fontSize=11,
        spaceBefore=14,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        "FosterBody",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15,
    )
    story: list = [
        Paragraph("FOSTER HOME LOG", heading),
        Paragraph(month_name.upper(), month),
        Paragraph("TRAINING:", section),
    ]
    if trainings:
        for line in trainings:
            story.append(Paragraph(line, body))
    else:
        story.append(Spacer(1, 48))
    story.append(
        Paragraph(
            "FIRE DRILLS: (DATE, TIME, WHO PARTICIPATED AND HOW LONG IT TOOK "
            "TO EVACUATE)",
            section,
        )
    )
    if drills:
        for line in drills:
            story.append(Paragraph(line, body))
    else:
        story.append(Spacer(1, 48))
    story.append(Paragraph("WORKER VISITS:", section))
    blocks = list(visits) or [("", "", "")]
    while len(blocks) < 2:
        blocks.append(("", "", ""))
    for child, when, worker in blocks:
        story.append(
            KeepTogether(
                [
                    Paragraph(f"CHILD VISITED: {child}", body),
                    Paragraph(f"DATE: {when}", body),
                    Paragraph(f"WORKER'S NAME: {worker}", body),
                    Spacer(1, 14),
                ]
            )
        )
    doc.build(story)
    return buffer.getvalue()
