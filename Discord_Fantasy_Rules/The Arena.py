from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


DARK_BG = HexColor("#090D0A")
ARENA_GREEN = HexColor("#1E301E")
CARD_BG = HexColor("#101A14")
CARD_ALT = HexColor("#162319")
CARD_BORDER = HexColor("#2A3E2B")
DIVIDER = HexColor("#1A2A1A")
EMBER_RED = HexColor("#D93025")
TORCH_GOLD = HexColor("#F5A623")
SAND_GOLD = HexColor("#C5A572")
VICTORY_GREEN = HexColor("#2ECC71")
STEEL = HexColor("#C0C0C8")
WHITE_TEXT = HexColor("#F2F5F2")
MUTED_TEXT = HexColor("#8A9A8A")
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


def draw_page(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = letter
    canvas_obj.setFillColor(DARK_BG)
    canvas_obj.rect(0, 0, w, h, fill=1, stroke=0)
    canvas_obj.setFillColor(EMBER_RED)
    canvas_obj.rect(0, h - 5, w, 5, fill=1, stroke=0)
    canvas_obj.setFillColor(TORCH_GOLD)
    canvas_obj.rect(0, h - 8, w, 3, fill=1, stroke=0)
    canvas_obj.setFillColor(ARENA_GREEN)
    canvas_obj.rect(0, 0, 8, h, fill=1, stroke=0)
    canvas_obj.setFillColor(HexColor("#080F09"))
    canvas_obj.rect(0, 0, w, 36, fill=1, stroke=0)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MUTED_TEXT)
    canvas_obj.drawCentredString(w / 2, 13, "The Arena  -  Discord Fantasy Rules")
    canvas_obj.drawRightString(w - 36, 13, f"Page {doc.page}")
    canvas_obj.restoreState()


def styles():
    return {
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=38,
            textColor=TORCH_GOLD,
            alignment=TA_CENTER,
            leading=42,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=13.5,
            textColor=STEEL,
            alignment=TA_CENTER,
            leading=18,
            spaceAfter=7,
        ),
        "kicker": ParagraphStyle(
            "kicker",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=VICTORY_GREEN,
            alignment=TA_CENTER,
            leading=12,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=TORCH_GOLD,
            leading=18,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "section_top": ParagraphStyle(
            "section_top",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=TORCH_GOLD,
            leading=18,
            spaceBefore=0,
            spaceAfter=8,
        ),
        "sub": ParagraphStyle(
            "sub",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=STEEL,
            leading=14,
            spaceBefore=6,
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
            fontSize=9.3,
            textColor=WHITE_TEXT,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=8.1,
            textColor=STEEL,
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
        "callout": ParagraphStyle(
            "callout",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TORCH_GOLD,
            alignment=TA_CENTER,
            leading=18,
        ),
    }


def hr(width, before=8, after=8):
    return HRFlowable(width=width, thickness=0.5, color=DIVIDER, spaceBefore=before, spaceAfter=after)


class ArenaEmblem(Flowable):
    def __init__(self, width, height=0.95 * inch):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        w = self.width
        h = self.height
        c.saveState()
        c.setStrokeColor(EMBER_RED)
        c.setLineWidth(2)
        c.ellipse(w * 0.17, h * 0.14, w * 0.83, h * 0.86, stroke=1, fill=0)
        c.setStrokeColor(TORCH_GOLD)
        c.setLineWidth(1.4)
        c.ellipse(w * 0.23, h * 0.24, w * 0.77, h * 0.76, stroke=1, fill=0)
        c.setStrokeColor(CARD_BORDER)
        c.setLineWidth(0.8)
        for idx in range(9):
            x = w * (0.3 + idx * 0.05)
            c.line(x, h * 0.28, x, h * 0.72)
        c.setFillColor(ARENA_GREEN)
        c.rect(w * 0.28, h * 0.18, w * 0.44, h * 0.11, fill=1, stroke=0)
        c.setFillColor(EMBER_RED)
        c.rect(w * 0.36, h * 0.44, w * 0.28, h * 0.14, fill=1, stroke=0)
        c.setFillColor(TORCH_GOLD)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(w / 2, h * 0.48, "SURVIVE THE SUNDAY CROWD")
        c.restoreState()


def stat_table(width):
    rows = [
        ["NO DRAFT", "$10 ENTRY", "18 WEEKS", "2-300 TEAMS"],
        ["Set lineups weekly", "Low buy-in, real stakes", "180 unique player slots", "Built for any room size"],
    ]
    col = width / 4
    table = Table(rows, colWidths=[col] * 4, rowHeights=[24, 40])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), EMBER_RED),
                ("BACKGROUND", (0, 1), (-1, 1), CARD_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("TEXTCOLOR", (0, 1), (-1, 1), TORCH_GOLD),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1.5, TORCH_GOLD),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, CARD_BORDER),
            ]
        )
    )
    return table


def info_card(number, title, body, style_map, width, color=TORCH_GOLD):
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


def lineup_table(style_map, width):
    cells = [
        ("QB", "1 per week", "18", "1 x 18 = 18 total", QB),
        ("RB", "2 per week", "36", "2 x 18 = 36 total", RB),
        ("WR", "2 per week", "36", "2 x 18 = 36 total", WR),
        ("RWT", "2 per week", "36", "2 x 18 = 36 total", RWT),
        ("TE", "1 per week", "18", "1 x 18 = 18 total", TE),
        ("K", "1 per week", "18", "1 x 18 = 18 total", K),
        ("DST", "1 per week", "18", "1 x 18 = 18 total", DST),
    ]
    data = [
        [Paragraph(name, style_map["small_dark"]) for name, _, _, _, _ in cells],
        [Paragraph(per_week, style_map["small"]) for _, per_week, _, _, _ in cells],
        [Paragraph(f"<font color='#F5A623'><b>{total}</b></font>", style_map["callout"]) for _, _, total, _, _ in cells],
        [Paragraph(note, style_map["small"]) for _, _, _, note, _ in cells],
    ]
    table = Table(data, colWidths=[width / 7] * 7, rowHeights=[0.3 * inch, 0.28 * inch, 0.38 * inch, 0.32 * inch])
    commands = [
        ("BACKGROUND", (0, 1), (-1, -1), CARD_BG),
        ("BOX", (0, 0), (-1, -1), 1.2, CARD_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, DARK_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for idx, (_, _, _, _, color) in enumerate(cells):
        commands.append(("BACKGROUND", (idx, 0), (idx, 0), color))
    table.setStyle(TableStyle(commands))
    return table


def mode_card(number, title, subtitle, body, style_map, width, color):
    row = [
        [
            Paragraph(f"<b>{number}</b>", ParagraphStyle("mode_num", fontName="Helvetica-Bold", fontSize=20, textColor=color, alignment=TA_CENTER)),
            [Paragraph(f"<font color='{color.hexval()}'><b>{title}</b></font>", style_map["sub"]), Paragraph(subtitle, style_map["small"]), Paragraph(body, style_map["body_left"])],
        ]
    ]
    table = Table(row, colWidths=[0.5 * inch, width - 0.7 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 1, CARD_BORDER),
                ("LINEAFTER", (0, 0), (0, -1), 2, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 7)])


def bullet_panel(title, bullets, style_map, width, color=TORCH_GOLD):
    rows = [[Paragraph(f"<b>{title}</b>", style_map["sub"])]]
    rows.extend([[Paragraph(f"- {bullet}", style_map["body_left"])] for bullet in bullets])
    table = Table(rows, colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ARENA_GREEN),
                ("BACKGROUND", (0, 1), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 1.2, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build():
    out = Path(__file__).with_name("the_arena.pdf")
    doc = BaseDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.65 * inch,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="arena", frames=frame, onPage=draw_page)])

    s = styles()
    story = []
    w = doc.width

    story.append(Spacer(1, 0.1 * inch))
    story.append(ArenaEmblem(w))
    story.append(Spacer(1, 0.12 * inch))
    story.append(HRFlowable(width=w * 0.22, thickness=2, color=EMBER_RED, hAlign="CENTER", spaceAfter=16))
    story.append(Paragraph("THE ARENA", s["title"]))
    story.append(Paragraph("Survivor Fantasy Football, built for weekly decisions and season-long pressure.", s["subtitle"]))
    story.append(Paragraph("No drafts  -  180 player decisions  -  three ways to win", s["subtitle"]))
    story.append(Paragraph("A Discord Fantasy department for managers who want every Sunday to matter.", s["kicker"]))
    story.append(HRFlowable(width=w * 0.22, thickness=2, color=EMBER_RED, hAlign="CENTER", spaceBefore=8, spaceAfter=16))
    story.append(stat_table(w))
    story.append(Spacer(1, 0.14 * inch))

    story.append(Paragraph("EXECUTIVE SUMMARY", s["section"]))
    story.append(
        Paragraph(
            "The Arena strips away the barrier that keeps most people out of fantasy sports: the draft. There is no snake draft to schedule and no auction to master. Instead, managers set a full Pyramid-style lineup every single week of the NFL season with one pressure rule: you can never use the same player twice all season.",
            s["body"],
        )
    )
    story.append(
        Paragraph(
            "The result is a no-draft fantasy department that rewards deep football knowledge, creative roster construction, and clean week-to-week engagement from Week 1 through the final whistle of Week 18.",
            s["body"],
        )
    )

    story.append(hr(w))
    story.append(Paragraph("LEAGUE PRIORITIES", s["section"]))
    story.append(info_card("1", "Maximum Participation", "No draft means no scheduling headache and no barrier to entry. Anyone can join at any time, even mid-season with admin approval, and immediately be competitive.", s, w, TORCH_GOLD))
    story.append(info_card("2", "Engagement and Publicity", "Weekly lineup decisions drive weekly conversation. Every manager has something to talk about, debate, and show off every single matchday.", s, w, EMBER_RED))
    story.append(info_card("3", "Accessible but Accountable", "$10 keeps the league open to everyone while making sure players are genuinely invested. Multiple-team ownership creates even more skin in the game.", s, w, VICTORY_GREEN))
    story.append(info_card("4", "Unique, Balanced and Fun", "The never-repeat-a-player rule is simple to explain but deep in strategy: elite-player timing, bye-week planning, and late-season survival all matter.", s, w, STEEL))

    story.append(Paragraph("HOW IT WORKS", s["section_top"]))
    story.append(
        bullet_panel(
            "The Core Rule",
            [
                "Every week, you set the same starting lineup shape used in The Pyramid.",
                "Every week, you pick different players.",
                "By Week 18, each team will have used 180 unique player slots.",
                "Players used on one team do not block other teams; every team manages its own list.",
            ],
            s,
            w,
            TORCH_GOLD,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("WEEKLY LINEUP SLOTS x 18 WEEKS", s["section"]))
    story.append(
        Paragraph(
            "Each manager sets the following lineup every week. Multiply those slots by 18 weeks and you get the total unique player budget for the season.",
            s["body"],
        )
    )
    story.append(lineup_table(s, w))
    story.append(Spacer(1, 8))
    story.append(info_card("180", "Season Total", "Each team uses 180 unique player slots across 18 weeks. Once a player has been used by that team, that player cannot be used again by that same team for the rest of the season.", s, w, TORCH_GOLD))
    story.append(info_card("MT", "Multiple Team Ownership", "One person can own multiple teams. Each team operates independently with its own player pool, which lets the format scale cleanly from 2 teams to 300 without structural changes.", s, w, VICTORY_GREEN))

    story.append(hr(w))
    story.append(Paragraph("SCORING AND ROSTER DETAILS", s["section"]))
    story.append(
        Paragraph(
            "Scoring matches The Pyramid: standard PPR with return-yard bonuses, 6-point passing touchdowns, and QB sack penalties to keep quarterback scoring closer to normal. Whenever possible, scoring is continuous instead of discrete. Full scoring lives on Fantrax.",
            s["body"],
        )
    )
    story.append(
        Paragraph(
            "The weekly lineup is 1 QB, 2 RB, 2 WR, 2 RWT flex, 1 TE, 1 K, and 1 DST. The Arena uses the same roster language and scoring foundation as The Pyramid, then changes the strategy by removing drafts and requiring every selected player to be unique for that team.",
            s["body"],
        )
    )

    story.append(hr(w))
    story.append(Paragraph("THE TRIFECTA: THREE WAYS TO WIN", s["section_top"]))
    story.append(
        Paragraph(
            "The Arena can crown winners through three clean competitive tracks. A season can emphasize one track or run the trifecta together so managers have multiple reasons to care every week.",
            s["body"],
        )
    )
    story.append(mode_card("01", "TOTAL POINTS", "Pure Leaderboard", "Every point scored by every player across all 18 weeks is cumulative. The manager with the highest season total wins. Simple, transparent, and perfect for a first season where everyone is learning the format.", s, w, TORCH_GOLD))
    story.append(mode_card("02", "HEAD-TO-HEAD SWISS", "Weekly Matchups", "Managers are paired head-to-head based on record. Win your matchup, improve your record, and build toward playoff seeding. This adds rivalries and upset potential to a no-draft format.", s, w, HexColor("#4A90E2")))
    story.append(mode_card("03", "GUILLOTINE", "Multiple Weekly Eliminations", "Multiple managers can be eliminated each week based on the lowest weekly scores. Surviving managers carry their used-player list forward, making late-season decisions more dangerous as the player pool tightens.", s, w, EMBER_RED))

    story.append(Paragraph("ENTRY FEE AND OPERATIONS", s["section_top"]))
    story.append(info_card("$", "$10 Per Team Entry", "Cheap enough that anyone can play. Meaningful enough that everyone cares. Players who own multiple teams pay $10 per team, creating more engagement and a larger prize pool.", s, w, TORCH_GOLD))
    story.append(
        bullet_panel(
            "Prize Pool Options",
            [
                "Total payout to season leaderboard finishers.",
                "Weekly bounty prizes for top scorer in guillotine mode.",
                "League merchandise or custom trophies for champions.",
                "Charity donation of the winner's choosing.",
            ],
            s,
            w,
            SAND_GOLD,
        )
    )
    story.append(Spacer(1, 10))
    story.append(
        bullet_panel(
            "Operations",
            [
                "No draft software needed; lineup submission can run through a simple form, sheet, or bot.",
                "Scales from 2 teams to 300 with zero structural changes.",
                "New entrants can join between seasons or, with admin approval, mid-season.",
                "Any rules listed here can be adjusted if platform behavior or admin tooling does not play nice.",
            ],
            s,
            w,
            EMBER_RED,
        )
    )

    story.append(hr(w, before=14, after=12))
    closing = [[Paragraph("No drafts. No excuses.<br/>Just 18 weeks of football, 180 decisions, and three ways to win.<br/><br/><font color='#2ECC71'>Who will be the last one standing?</font>", s["callout"])]]
    close_table = Table(closing, colWidths=[w])
    close_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_ALT),
                ("BOX", (0, 0), (-1, -1), 2, TORCH_GOLD),
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
