"""Render the Elysium data-provenance memorandum directly to PDF."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).parent
SOURCE = ROOT / "DATA_PROVENANCE_MEMO.md"
OUTPUT = ROOT / "Elysium_Data_Provenance_Memo.pdf"

NAVY = colors.HexColor("#213F57")
AQUA = colors.HexColor("#31D5D0")
INK = colors.HexColor("#172C3D")
MUTED = colors.HexColor("#6D8290")
LIGHT = colors.HexColor("#EDF8F8")
LINE = colors.HexColor("#DCE6EB")


def inline_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<link href="{m.group(2)}" color="#168F8C"><u>{m.group(1)}</u></link>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    return text


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(AQUA)
    canvas.setLineWidth(0.7)
    canvas.line(0.78 * inch, height - 0.54 * inch, width - 0.78 * inch, height - 0.54 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(0.78 * inch, height - 0.43 * inch, "ELYSIUM WEALTH MANAGEMENT")
    canvas.drawRightString(width - 0.78 * inch, height - 0.43 * inch, "DATA PROVENANCE MEMORANDUM")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.78 * inch, 0.42 * inch, "Prepared by McCade Pearson")
    canvas.drawRightString(width - 0.78 * inch, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build() -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.6,
        leading=12.1,
        textColor=INK,
        spaceAfter=5,
        alignment=TA_LEFT,
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        fontSize=9.3,
        leading=11.7,
        spaceAfter=3,
        leftIndent=0,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=NAVY,
        spaceBefore=11,
        spaceAfter=6,
        keepWithNext=True,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        textColor=NAVY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    code = ParagraphStyle(
        "Code",
        parent=body,
        fontName="Courier",
        fontSize=8.5,
        textColor=NAVY,
        backColor=colors.HexColor("#F4F8F9"),
        borderPadding=7,
        spaceAfter=6,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.78 * inch,
        rightMargin=0.78 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.68 * inch,
        title="Elysium Wealth Management - Data Provenance Memorandum",
        author="McCade Pearson",
    )
    story = []
    story.append(Spacer(1, 10))
    story.append(Paragraph('<font color="#31D5D0"><b>DATA GOVERNANCE MEMORANDUM</b></font>', ParagraphStyle("Kicker", parent=body, fontSize=8.5, leading=10, spaceAfter=3)))
    story.append(Paragraph("Traffic Accident Intelligence", ParagraphStyle("Title", parent=h1, fontSize=25, leading=28, spaceBefore=0, spaceAfter=10)))

    metadata = [
        [Paragraph("<b>TO</b>", body), Paragraph("Leadership Team, Elysium Wealth Management", body)],
        [Paragraph("<b>FROM</b>", body), Paragraph('McCade Pearson  |  <link href="mailto:mccade.pearson@gmail.com" color="#168F8C">mccade.pearson@gmail.com</link>', body)],
        [Paragraph("<b>DATE</b>", body), Paragraph("June 13, 2026", body)],
        [Paragraph("<b>SUBJECT</b>", body), Paragraph("Data sources, methodology, limitations, and appropriate use", body)],
    ]
    meta = Table(metadata, colWidths=[0.75 * inch, 5.65 * inch])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, LINE),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.extend([meta, Spacer(1, 10)])

    callout = Table(
        [[Paragraph("<b>Purpose:</b> Document the authoritative government sources and analytical methods used by Elysium's Traffic Accident Intelligence application.", body)]],
        colWidths=[6.4 * inch],
    )
    callout.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.8, AQUA),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([callout, Spacer(1, 5)])

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    started = False
    in_code = False
    code_lines: list[str] = []
    pending_bullets: list[ListItem] = []

    def flush_bullets() -> None:
        nonlocal pending_bullets
        if pending_bullets:
            story.append(
                ListFlowable(
                    pending_bullets,
                    bulletType="bullet",
                    start="circle",
                    leftIndent=16,
                    bulletFontName="Helvetica",
                    bulletFontSize=6,
                    bulletColor=AQUA,
                    spaceAfter=4,
                )
            )
            pending_bullets = []

    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped == "## Purpose":
                started = True
            else:
                continue
        if stripped.startswith("```"):
            flush_bullets()
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(x) for x in code_lines), code))
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_bullets()
            continue
        if stripped.startswith("## "):
            flush_bullets()
            story.append(Paragraph(inline_markdown(stripped[3:]), h1))
        elif stripped.startswith("### "):
            flush_bullets()
            story.append(Paragraph(inline_markdown(stripped[4:]), h2))
        elif stripped.startswith("- "):
            pending_bullets.append(ListItem(Paragraph(inline_markdown(stripped[2:]), bullet)))
        else:
            flush_bullets()
            story.append(Paragraph(inline_markdown(stripped), body))
    flush_bullets()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()

