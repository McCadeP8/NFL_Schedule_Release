from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


DARK_BG = HexColor("#000814")
NAVY_DEEP = HexColor("#001D3D")
SILVER_SHINE = HexColor("#C0C0C8")
GOLD_ELITE = HexColor("#C5A572")
ACCENT_CYAN = HexColor("#00B4D8")
WHITE_TEXT = HexColor("#F8F9FA")
GRAY_MID = HexColor("#6C757D")
CARD_BG = HexColor("#0A1628")
CARD_BORDER = HexColor("#1A2F4D")
DIVIDER = HexColor("#162842")
PROMOTE_GREEN = HexColor("#00A86B")
RELEGATE_RED = HexColor("#B80F0A")
IRON_GRAY = HexColor("#575B60")
WHITE = colors.white

QB = HexColor("#D62828")
RB = HexColor("#F77F00")
WR = HexColor("#FFD60A")
RWT = HexColor("#A7E8FF")
TE = HexColor("#00A86B")
K = HexColor("#D45087")
DST = HexColor("#1D4ED8")
BENCH = HexColor("#8D99AE")
IR = HexColor("#8B5E34")

DIVISION_COLORS = {
    "Diamond": HexColor("#8EEBFF"),
    "Gold": HexColor("#D8B62E"),
    "Silver": HexColor("#C7CDD3"),
    "Bronze": HexColor("#C8843E"),
    "Crimson": HexColor("#B80F0A"),
    "Emerald": HexColor("#00A86B"),
    "Sapphire": HexColor("#1657B7"),
    "Iron": HexColor("#575B60"),
}


def draw_page(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = letter
    canvas_obj.setFillColor(DARK_BG)
    canvas_obj.rect(0, 0, w, h, fill=1, stroke=0)
    canvas_obj.setFillColor(GOLD_ELITE)
    canvas_obj.rect(0, h - 3, w, 3, fill=1, stroke=0)
    canvas_obj.setFillColor(SILVER_SHINE)
    canvas_obj.rect(0, h - 6, w, 3, fill=1, stroke=0)
    canvas_obj.setFillColor(NAVY_DEEP)
    canvas_obj.rect(0, 0, 8, h, fill=1, stroke=0)
    canvas_obj.setFillColor(HexColor("#00050A"))
    canvas_obj.rect(0, 0, w, 36, fill=1, stroke=0)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(GRAY_MID)
    canvas_obj.drawCentredString(w / 2, 13, "The Pyramid  -  Discord Fantasy Rules")
    canvas_obj.drawRightString(w - 36, 13, f"Page {doc.page}")
    canvas_obj.restoreState()


def styles():
    return {
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=38,
            textColor=GOLD_ELITE,
            alignment=TA_CENTER,
            leading=42,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=14,
            textColor=SILVER_SHINE,
            alignment=TA_CENTER,
            leading=18,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=GOLD_ELITE,
            leading=18,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "sub": ParagraphStyle(
            "sub",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=SILVER_SHINE,
            leading=14,
            spaceBefore=7,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9.6,
            textColor=WHITE_TEXT,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "body_left": ParagraphStyle(
            "body_left",
            fontName="Helvetica",
            fontSize=9.4,
            textColor=WHITE_TEXT,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=8.3,
            textColor=SILVER_SHINE,
            leading=11,
            alignment=TA_CENTER,
        ),
        "small_dark": ParagraphStyle(
            "small_dark",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=DARK_BG,
            leading=10,
            alignment=TA_CENTER,
        ),
        "pyramid_label": ParagraphStyle(
            "pyramid_label",
            fontName="Helvetica-Bold",
            fontSize=8.8,
            textColor=DARK_BG,
            leading=10,
            alignment=TA_CENTER,
        ),
        "section_top": ParagraphStyle(
            "section_top",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=GOLD_ELITE,
            leading=18,
            spaceBefore=0,
            spaceAfter=8,
        ),
        "callout": ParagraphStyle(
            "callout",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=GOLD_ELITE,
            alignment=TA_CENTER,
            leading=18,
        ),
    }


def hr(width, before=8, after=8):
    return HRFlowable(width=width, thickness=0.5, color=DIVIDER, spaceBefore=before, spaceAfter=after)


def stat_table(width):
    rows = [
        ["10-300 TEAMS", "$10 ENTRY", "GROUPS OF 10", "TWO SEASONS"],
        ["Built to include everyone", "Low barrier, real buy-in", "16-round drafts", "Promotion and relegation"],
    ]
    col = width / 4
    table = Table(rows, colWidths=[col] * 4, rowHeights=[24, 38])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_DEEP),
                ("BACKGROUND", (0, 1), (-1, 1), CARD_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), GOLD_ELITE),
                ("TEXTCOLOR", (0, 1), (-1, 1), SILVER_SHINE),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1.5, GOLD_ELITE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, CARD_BORDER),
            ]
        )
    )
    return table


def pyramid_logo(style_map, width):
    layers = [
        ("Diamond", "DIAMOND"),
        ("Gold", "GOLD"),
        ("Silver", "SILVER"),
        ("Bronze", "BRONZE"),
        ("Crimson", "CRIMSON"),
        ("Emerald", "EMERALD"),
        ("Sapphire", "SAPPHIRE"),
        ("Iron", "IRON"),
    ]
    rows = []
    commands = [
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]
    total_cols = 25
    top_width = 9
    for row_idx, (prestige, label) in enumerate(layers):
        layer_width = top_width + (row_idx * 2)
        start = (total_cols - layer_width) // 2
        end = start + layer_width - 1
        row = [""] * total_cols
        row[start] = Paragraph(label, style_map["pyramid_label"])
        rows.append(row)
        commands.extend(
            [
                ("SPAN", (start, row_idx), (end, row_idx)),
                ("BACKGROUND", (start, row_idx), (end, row_idx), DIVISION_COLORS[prestige]),
                ("BOX", (start, row_idx), (end, row_idx), 0.7, DARK_BG),
                ("LINEBELOW", (start, row_idx), (end, row_idx), 0.45, HexColor("#F8F9FA")),
                ("TOPPADDING", (start, row_idx), (end, row_idx), 3),
                ("BOTTOMPADDING", (start, row_idx), (end, row_idx), 3),
            ]
        )
    table = Table(rows, colWidths=[width / total_cols] * total_cols, rowHeights=[0.2 * inch] * len(rows))
    table.setStyle(TableStyle(commands))
    return table


def fine_print_rules(style_map, width):
    rules = [
        ("Prize Percentages", "Exact payout percentages will be announced once the final number of teams is locked."),
        ("Tiebreakers", "Promotion, relegation, and payout ties are broken by head-to-head record, then total points, then max points."),
        ("Trades", "Trades are always allowed. During Weeks 1-9, trades are only within your draft division. During Weeks 10-18, trades can happen among all teams. The commissioner has final say on fairness to prevent collusion."),
        ("Inactive Managers", "Teams that quit or fail to set lineups will be relegated and may be removed from the league."),
        ("Expansion Teams", "New expansion teams always start at the very bottom, with the possibility of more aggressive upside for winning a new conference league."),
        ("Fantrax Flexibility", "Any rule listed here may be adjusted if Fantrax settings, software behavior, or platform limitations do not play nice with the intended format."),
    ]
    rows = [[Paragraph(f"<b>{title}:</b> {body}", style_map["body_left"])] for title, body in rules]
    table = Table(rows, colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 1.2, CARD_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, DIVIDER),
            ]
        )
    )
    return table


def roster_grid(style_map, width):
    cells = [
        ("QB", "1", QB),
        ("RB", "2", RB),
        ("WR", "2", WR),
        ("RWT", "2", RWT),
        ("TE", "1", TE),
        ("K", "1", K),
        ("DST", "1", DST),
        ("BENCH", "6", BENCH),
        ("IR", "2", IR),
    ]
    row = [[Paragraph(f"<b>{name}</b><br/>{count}", style_map["small_dark"]) for name, count, _ in cells]]
    table = Table(row, colWidths=[width / len(cells)] * len(cells), rowHeights=[0.46 * inch])
    commands = [
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1.2, CARD_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, DARK_BG),
    ]
    for idx, (_, _, color) in enumerate(cells):
        commands.append(("BACKGROUND", (idx, 0), (idx, 0), color))
    table.setStyle(TableStyle(commands))
    return table


def info_card(number, title, body, style_map, width, color=GOLD_ELITE):
    row = [
        [
            Paragraph(f"<font size=22><b>{number}</b></font>", ParagraphStyle("n", alignment=TA_CENTER, textColor=color)),
            [Paragraph(title, style_map["sub"]), Paragraph(body, style_map["body_left"])],
        ]
    ]
    table = Table(row, colWidths=[0.62 * inch, width - 0.82 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 1.2, CARD_BORDER),
                ("LINEAFTER", (0, 0), (0, -1), 2, color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 6)])


def division_example(style_map, width):
    headers = ["Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron"]
    matrix = [
        [1, 8, 10, 10, 10, 10, 10, 10],
        [2, 9, 8, 8, 8, 8, 8, 8],
        [3, 3, 9, 9, 9, 9, 9, 9],
        [4, 4, 4, 4, 4, 4, 4, 10],
        [5, 5, 5, 5, 5, 5, 5, 5],
        [6, 6, 6, 6, 6, 6, 6, 6],
        [7, 7, 7, 7, 7, 7, 7, 7],
        [1, 2, 2, 2, 2, 2, 2, 8],
        [2, 3, 3, 3, 3, 3, 3, 9],
        [1, 1, 1, 1, 1, 1, 4, 10],
    ]
    destinations = [
        ["Diamond", "Diamond", "Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald"],
        ["Diamond", "Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire"],
        ["Diamond", "Gold", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire"],
        ["Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Sapphire"],
        ["Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron"],
        ["Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron"],
        ["Diamond", "Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron"],
        ["Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron", "Iron"],
        ["Gold", "Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron", "Iron"],
        ["Silver", "Bronze", "Crimson", "Emerald", "Sapphire", "Iron", "Iron", "Iron"],
    ]
    prestige_order = {name: idx for idx, name in enumerate(headers)}
    sorted_matrix = [[None for _ in headers] for _ in range(10)]
    sorted_destinations = [[None for _ in headers] for _ in range(10)]
    for col in range(len(headers)):
        cells = [(matrix[row][col], destinations[row][col]) for row in range(10)]
        cells.sort(key=lambda cell: (cell[0], prestige_order[cell[1]]))
        for row, (slot, destination) in enumerate(cells):
            sorted_matrix[row][col] = slot
            sorted_destinations[row][col] = destination
    matrix = sorted_matrix
    destinations = sorted_destinations

    def place_label(value):
        suffix = "th"
        if value % 100 not in {11, 12, 13}:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix} Place"

    data = [headers] + [[place_label(x) for x in row] for row in matrix]
    table = Table(data, colWidths=[width / 8] * 8, rowHeights=[0.24 * inch] + [0.2 * inch] * 10)
    commands = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("FONTSIZE", (0, 1), (-1, -1), 6.2),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ]
    for col, name in enumerate(headers):
        commands.append(("BACKGROUND", (col, 0), (col, 0), DIVISION_COLORS[name]))
    for row in range(1, 11):
        for col, name in enumerate(headers):
            destination = destinations[row - 1][col]
            bg = DIVISION_COLORS[destination]
            commands.append(("BACKGROUND", (col, row), (col, row), bg))
            commands.append(("TEXTCOLOR", (col, row), (col, row), WHITE if destination in {"Crimson", "Sapphire", "Iron"} else DARK_BG))
    commands.append(("TEXTCOLOR", (0, 0), (-1, -1), colors.black))
    commands.append(("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"))
    table.setStyle(TableStyle(commands))
    return table


def build():
    out = Path(__file__).with_name("the_pyramid.pdf")
    doc = BaseDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.65 * inch,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="bg", frames=frame, onPage=draw_page)])

    s = styles()
    story = []
    w = doc.width

    story.append(Spacer(1, 0.1 * inch))
    story.append(pyramid_logo(s, w))
    story.append(Spacer(1, 0.12 * inch))
    story.append(HRFlowable(width=w * 0.22, thickness=2, color=GOLD_ELITE, hAlign="CENTER", spaceAfter=16))
    story.append(Paragraph("THE PYRAMID", s["title"]))
    story.append(Paragraph("Our most basic fantasy league, built so everyone can be included.", s["subtitle"]))
    story.append(Paragraph("10 to 300 teams  -  $10 entry  -  two fantasy seasons every NFL season", s["subtitle"]))
    story.append(HRFlowable(width=w * 0.22, thickness=2, color=GOLD_ELITE, hAlign="CENTER", spaceBefore=10, spaceAfter=18))
    story.append(stat_table(w))
    story.append(Spacer(1, 0.16 * inch))

    story.append(Paragraph("WHAT THIS LEAGUE IS", s["section"]))
    story.append(
        Paragraph(
            "The Pyramid is the welcome mat for the Discord fantasy ecosystem. It keeps the price low, the rules familiar, "
            "and the league size flexible enough to include almost anyone who wants to play. Every team starts in a 10-team "
            "draft room, then the league gradually sorts itself into prestige divisions. Prestige is earned, carried forward, "
            "and defended over time.",
            s["body"],
        )
    )
    story.append(
        Paragraph(
            "The Discord Admins do not take a single penny. The first $130 pays Fantrax hosting. Everything after that goes "
            "toward champion pools or league operations such as merchandise for champions.",
            s["body"],
        )
    )

    story.append(hr(w))
    story.append(Paragraph("DRAFT AND ROSTERS", s["section"]))
    story.append(
        Paragraph(
            "Drafts start on August 1. Drafts run in groups of 10, and anytime a new division fills up, that division will begin drafting through a slow draft on Fantrax software. Each draft is 16 rounds: 10 starters and 6 bench spots.",
            s["body"],
        )
    )
    story.append(roster_grid(s, w))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Starting lineup: 1 QB, 2 RB, 2 WR, 2 RWT flex, 1 TE, 1 K, and 1 DST. Each team also has 2 IR slots. Players on bye are IR eligible.",
            s["body"],
        )
    )

    story.append(PageBreak())
    story.append(
        KeepTogether(
            [
                Paragraph("SCORING AND WAIVERS", s["section_top"]),
                Paragraph(
                    "Scoring is standard PPR with a few intentional tweaks. Return yards receive small yardage bonuses because if your player is "
                    "on the field, they deserve the chance to score points. Passing touchdowns are worth 6 points, while sacks cost QB points to "
                    "keep quarterback scoring closer to normal. Whenever possible, scoring is continuous instead of discrete. Full scoring lives on Fantrax.",
                    s["body"],
                ),
                Paragraph(
                    "Waivers process Thursday mornings at 10:00 AM ET. The league uses FAAB with a $100 season budget. Minimum bid follows the Fantrax league setting.",
                    s["body"],
                ),
            ]
        )
    )

    story.append(Paragraph("THE TWO-SEASON LADDER", s["section_top"]))
    story.append(
        Paragraph(
            "The Pyramid does something most fantasy leagues cannot: it turns a giant league into a ladder. The first half of the NFL season "
            "is about proving yourself inside your draft room. The second half is where the walls come down and the league reorganizes by results. "
            "That creates a simple rhythm: qualify, climb, defend your prestige, and make room for new players at the base. "
            "Prestige does not reset every year; only the players do.",
            s["body"],
        )
    )
    story.append(info_card("Y0", "2026 Weeks 1-9: Draft-Room Season", "Single round-robin within your 10-team draft division. Waivers are handled inside each individual division, as if each draft room is its own standalone league.", s, w, ACCENT_CYAN))
    story.append(info_card("Y1", "2026 Weeks 10-18: Prestige Season", "There is no new draft between Weeks 9 and 10. Your roster continues, but your opponents change as teams are separated into tiered prestige divisions. You can now face teams from other drafts, including teams that may roster the same NFL players you do. New drafters can enter through the entry league at the bottom.", s, w, GOLD_ELITE))
    story.append(info_card("Y2", "2027 Weeks 1-9: Prestige Carries, Players Reset", "No keepers. Your earned prestige from 2026 Season 1 carries into the 2027 NFL season, then new 10-team drafts are created within each prestige level. Year 0 only exists for the first launch and for new expansion entrants.", s, w, PROMOTE_GREEN))

    story.append(hr(w))
    story.append(Paragraph("GLOBAL WAIVERS IN PRESTIGE PLAY", s["section"]))
    story.append(
        Paragraph(
            "Once teams are sorted into prestige divisions, waivers process across the full player pool for that level. If four versions of a player "
            "are available, the top four valid FAAB bids win that player. It keeps duplicate-player fantasy workable while still rewarding aggressive, thoughtful bidding.",
            s["body"],
        )
    )

    story.append(hr(w))
    story.append(PageBreak())
    story.append(Paragraph("EIGHT-DIVISION EXAMPLE", s["section"]))
    story.append(
        Paragraph(
            "Example flow with eight 10-team divisions. The header is your current prestige. Each row represents where a team finishes in that prestige, "
            "and the cell color shows the prestige destination for the next round. The number inside the cell is the landing slot within that destination.",
            s["body"],
        )
    )
    story.append(division_example(s, w))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Diamond is the top of the Pyramid. Iron is the entry point. Every half-season gives teams a reason to care: climb, hold, or fight off relegation. "
            "Payouts exist in every division, but are weighted by prestige.",
            s["body"],
        )
    )

    story.append(Paragraph("PAYOUTS, ADMIN, AND FINE PRINT", s["section"]))
    story.append(info_card("$", "Entry Fee Philosophy", "$10 is meant to create enough buy-in that people actually play without pricing out anyone who wants to participate.", s, w, GOLD_ELITE))
    story.append(info_card("0", "Admin Take", "Discord Admins take zero dollars. Hosting comes first, then prizes or league operations for champions and league merchandise.", s, w, PROMOTE_GREEN))
    story.append(info_card("P", "Payout Weighting", "All divisions can receive payouts, but payouts are weighted by prestige. Higher divisions carry higher rewards because the climb matters.", s, w, ACCENT_CYAN))
    story.append(info_card("F", "Final Rules", "All other league rules are listed on Fantrax or handled at the discretion of the Discord Admins.", s, w, SILVER_SHINE))

    story.append(hr(w, before=10, after=8))
    story.append(Paragraph("FINAL RULE NOTES", s["section"]))
    story.append(fine_print_rules(s, w))

    story.append(hr(w, before=10, after=10))
    invite = (
        '<a href="https://www.fantrax.com/fantasy/league/bq663faompbqd2n5/join">'
        '<font color="#00B4D8"><b>Click here to start your journey climbing The Pyramid</b></font></a>'
    )
    closing = [[Paragraph(f"Everyone starts somewhere.<br/>The Pyramid gives every manager a place to climb.<br/><br/>{invite}", s["callout"])]]
    close_table = Table(closing, colWidths=[w])
    close_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY_DEEP),
                ("BOX", (0, 0), (-1, -1), 2, GOLD_ELITE),
                ("TOPPADDING", (0, 0), (-1, -1), 22),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
            ]
        )
    )
    story.append(close_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("- Discord Fantasy Rules Draft -", s["callout"]))

    doc.build(story)
    print(f"PDF saved to {out}")


if __name__ == "__main__":
    build()
