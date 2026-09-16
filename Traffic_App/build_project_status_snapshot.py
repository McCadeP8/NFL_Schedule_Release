"""Build a two-page project status PDF for the traffic app."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "data" / "traffic_data.sqlite"
OUTPUT_PATH = ROOT / "output" / "pdf" / "traffic_app_status_snapshot.pdf"

BLUE = colors.HexColor("#2596BE")
GOLD = colors.HexColor("#FBAD41")
NAVY = colors.HexColor("#213F57")
INK = colors.HexColor("#243642")
MUTED = colors.HexColor("#607080")
LINE = colors.HexColor("#D8E2E8")
SOFT = colors.HexColor("#F4F8FA")


def _table_count(table: str) -> int:
    with sqlite3.connect(DATABASE_PATH) as connection:
        return connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def _sources() -> list[tuple[str, str, str, int]]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            'SELECT dataset, years, refreshed_at, records FROM "data_sources" ORDER BY rowid'
        ).fetchall()
    return [(dataset, years, refreshed_at[:10], int(records)) for dataset, years, refreshed_at, records in rows]


def _status_counts() -> tuple[int, int, int]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        automated = connection.execute(
            'SELECT COUNT(*) FROM "all_crash_source_status" WHERE status = "Automated"'
        ).fetchone()[0]
        tracked = connection.execute('SELECT COUNT(*) FROM "all_crash_source_status"').fetchone()[0]
        rows = connection.execute(
            'SELECT COUNT(DISTINCT state) FROM "all_state_crashes"'
        ).fetchone()[0]
    return int(automated), int(tracked), int(rows)


def _states() -> str:
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            'SELECT DISTINCT state FROM "all_state_crashes" ORDER BY state'
        ).fetchall()
    return ", ".join(row[0] for row in rows)


def _make_bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), bulletColor=BLUE) for item in items],
        bulletType="bullet",
        leftIndent=14,
        bulletFontName="Helvetica-Bold",
        bulletFontSize=7,
    )


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(doc.leftMargin, height - 0.42 * inch, "Traffic App Status Snapshot")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - doc.rightMargin, height - 0.42 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 0.52 * inch, width - doc.rightMargin, 0.52 * inch)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.34 * inch, "Generated from local project files and data/traffic_data.sqlite")
    canvas.restoreState()


def build_pdf() -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleLarge",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=27,
            textColor=NAVY,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Kicker",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=BLUE,
            uppercase=True,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12,
            textColor=INK,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Cell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellHead",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="RightNote",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
            alignment=TA_RIGHT,
        )
    )

    doc = BaseDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="snapshot", frames=[frame], onPage=_header_footer)])

    counts = {
        "fars": _table_count("fars_crashes"),
        "utah": _table_count("utah_crashes"),
        "all_state": _table_count("all_state_crashes"),
        "county": _table_count("county_marketing_analytics"),
        "tracked": _table_count("all_crash_source_status"),
    }
    automated, tracked, automated_states = _status_counts()
    source_rows = _sources()
    generated = datetime.now().strftime("%B %d, %Y")

    story = [
        Paragraph("CURRENT POSITION", styles["Kicker"]),
        Paragraph("Traffic App Project Snapshot", styles["TitleLarge"]),
        Paragraph(
            f"Generated {generated}. This is where the project stands after the June 17 data refresh.",
            styles["BodySmall"],
        ),
        Spacer(1, 4),
    ]

    metric_data = [
        [
            Paragraph("Nationwide fatal crashes", styles["CellHead"]),
            Paragraph("All-severity state crashes", styles["CellHead"]),
            Paragraph("County market rows", styles["CellHead"]),
            Paragraph("Tracked source states", styles["CellHead"]),
        ],
        [
            Paragraph(f"{counts['fars']:,}<br/>FARS 2019-2023", styles["Cell"]),
            Paragraph(f"{counts['all_state']:,}<br/>{_states()} 2019-2024", styles["Cell"]),
            Paragraph(f"{counts['county']:,}<br/>county-year FARS plus market context", styles["Cell"]),
            Paragraph(f"{tracked:,}<br/>{automated} automated, {tracked - automated} pending/review", styles["Cell"]),
        ],
    ]
    metrics = Table(metric_data, colWidths=[1.75 * inch] * 4)
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, 1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 7)])

    story.extend(
        [
            Paragraph("What We Have", styles["Section"]),
            _make_bullets(
                [
                    "A working Streamlit dashboard in app.py branded for Astrix Law Traffic Accident Intelligence.",
                    "A reproducible ingestion pipeline in ingest.py that downloads and normalizes government crash, population, and business datasets.",
                    "A local SQLite database plus compressed deployment CSVs, so the app can run locally with full tables or on Streamlit Cloud with a compact bundle.",
                    "Four UI areas: Executive Overview, Accident Trends, Risk Factors, and Geographic Analysis, with state/year filters and source-status disclosure.",
                    "A data provenance memo already exists, though it still uses older Elysium wording while the app now says Astrix Law.",
                ],
                styles["BodySmall"],
            ),
            Paragraph("What You Can Tell People", styles["Section"]),
            _make_bullets(
                [
                    "We can compare fatal crash exposure nationally using NHTSA FARS for 2019-2023.",
                    "We have all-reported crash detail for Utah and Virginia for completed years 2019-2024, plus Oklahoma fatal/injury KAB crash detail for 2019-2021.",
                    "We join crash outcomes to county population and Census County Business Patterns for target industries: specialty trade contractors, truck transportation, couriers/messengers, and landscaping services.",
                    "The tool is for aggregate market intelligence, not identifying individual crash victims or proving a specific crash was work-related.",
                ],
                styles["BodySmall"],
            ),
        ]
    )

    story.append(PageBreak())
    story.extend(
        [
            Paragraph("WHERE THINGS ARE", styles["Kicker"]),
            Paragraph("Files, Data, and Next Moves", styles["TitleLarge"]),
            Paragraph("Project map", styles["Section"]),
        ]
    )

    file_rows = [
        ["File or folder", "What it does"],
        ["app.py", "Streamlit UI, navigation, filters, metrics, charts, and map views."],
        ["data.py", "App-facing loaders. Reads SQLite first, then data/deploy CSV fallbacks."],
        ["ingest.py", "Full refresh pipeline: downloads raw sources, builds SQLite, exports analysis files."],
        ["build_deployment_data.py", "Creates compact compressed CSVs for Streamlit Cloud."],
        ["eda_data.py", "New Python EDA helper with get_data_* functions for each loaded dataset."],
        ["data/traffic_data.sqlite", "Full local analytical database with ten tables."],
        ["data/deploy/", "Committed compact app bundle, one compressed CSV per deployed table."],
        ["data/exports/", "Wider analysis CSVs for R/Python notebooks and ad hoc exploration."],
        ["analysis/DATA_DICTIONARY.md", "Definitions and EDA caveats for the analysis tables."],
    ]
    file_table = Table(
        [[Paragraph(cell, styles["CellHead"] if i == 0 else styles["Cell"]) for cell in row] for i, row in enumerate(file_rows)],
        colWidths=[1.9 * inch, 5.1 * inch],
    )
    file_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    story.extend([file_table, Spacer(1, 5)])

    data_rows = [["Dataset", "Years", "Records", "Refreshed"]]
    data_rows.extend([[dataset, years, f"{records:,}", refreshed] for dataset, years, refreshed, records in source_rows])
    source_table = Table(
        [[Paragraph(str(cell), styles["CellHead"] if i == 0 else styles["Cell"]) for cell in row] for i, row in enumerate(data_rows)],
        colWidths=[2.55 * inch, 1.1 * inch, 1.2 * inch, 1.25 * inch],
    )
    source_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )

    story.extend(
        [
            Paragraph("Loaded Data", styles["Section"]),
            source_table,
            Spacer(1, 5),
            KeepTogether(
                [
                    Paragraph("Runbook", styles["Section"]),
                    _make_bullets(
                        [
                            "Launch the app: streamlit run app.py",
                            "Refresh full local data: python ingest.py",
                            "Rebuild Streamlit deployment files: python build_deployment_data.py",
                            "Start Python EDA: from eda_data import get_data_catalog, get_data_utah_crashes",
                        ],
                        styles["BodySmall"],
                    ),
                ]
            ),
            Paragraph("Open Decisions", styles["Section"]),
            _make_bullets(
                [
                    "Resolve client/brand naming: older provenance memo says Elysium; current README and app say Astrix Law.",
                    "Decide which pending states are worth source negotiation next; Florida and Texas likely need portal or credential work.",
                    "Choose whether the dashboard should remain market-intelligence only or add recommendation scoring later.",
                ],
                styles["BodySmall"],
            ),
        ]
    )

    doc.build(story)
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_pdf())
