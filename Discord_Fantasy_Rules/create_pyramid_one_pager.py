from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("the_pyramid_one_pager.png")

W, H = 1200, 2100
BG = "#000814"
NAVY = "#001D3D"
PANEL = "#0A1628"
PANEL_2 = "#0F1E33"
BORDER = "#1A2F4D"
GOLD = "#C5A572"
CYAN = "#00B4D8"
GREEN = "#00A86B"
RED = "#B80F0A"
TEXT = "#F8F9FA"
STEEL = "#C0C0C8"

QB = "#D62828"
RB = "#F77F00"
WR = "#FFD60A"
RWT = "#A7E8FF"
TE = "#00A86B"
K = "#D45087"
DST = "#1D4ED8"

TIERS = [
    ("DIAMOND", "#8EEBFF"),
    ("GOLD", "#D8B62E"),
    ("SILVER", "#C7CDD3"),
    ("BRONZE", "#C8843E"),
    ("CRIMSON", "#B80F0A"),
    ("EMERALD", "#00A86B"),
    ("SAPPHIRE", "#1657B7"),
    ("IRON", "#575B60"),
]


def font(size, bold=False):
    names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = {
    "eyebrow": font(28, True),
    "title": font(82, True),
    "subtitle": font(34, False),
    "section": font(34, True),
    "body": font(25, False),
    "body_bold": font(25, True),
    "small": font(21, False),
    "small_bold": font(21, True),
    "stat": font(30, True),
    "stat_sub": font(21, True),
    "mode_num": font(38, True),
}


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = word if not line else f"{line} {word}"
        if text_size(draw, test, fnt)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_wrapped(draw, xy, text, fnt, fill, max_width, line_gap=7):
    x, y = xy
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_size(draw, line, fnt)[1] + line_gap
    return y


def rounded(draw, box, fill, outline=BORDER, radius=18, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def centered(draw, y, text, fnt, fill):
    tw, _ = text_size(draw, text, fnt)
    draw.text(((W - tw) / 2, y), text, font=fnt, fill=fill)


def stat_card(draw, x, y, w, h, title, subtitle, fill=PANEL):
    rounded(draw, (x, y, x + w, y + h), fill, GOLD, 14, 2)
    tw, _ = text_size(draw, title, F["stat"])
    draw.text((x + (w - tw) / 2, y + 22), title, font=F["stat"], fill=GOLD)
    for i, line in enumerate(wrap(draw, subtitle, F["stat_sub"], w - 34)):
        tw, _ = text_size(draw, line, F["stat_sub"])
        draw.text((x + (w - tw) / 2, y + 70 + i * 28), line, font=F["stat_sub"], fill=STEEL)


def pyramid_mark(draw, x, y, w):
    top_width = 250
    row_h = 26
    for idx, (label, color) in enumerate(TIERS):
        layer_w = top_width + idx * 56
        lx = x + (w - layer_w) / 2
        ly = y + idx * row_h
        draw.rectangle((lx, ly, lx + layer_w, ly + row_h - 3), fill=color, outline="#000814", width=2)
        fill = "#000814" if label not in {"CRIMSON", "SAPPHIRE", "IRON"} else "#FFFFFF"
        tw, _ = text_size(draw, label, F["small_bold"])
        draw.text((x + (w - tw) / 2, ly + 3), label, font=F["small_bold"], fill=fill)
    return y + len(TIERS) * row_h + 12


def lineup(draw, x, y, w):
    draw.text((x, y), "STARTING LINEUP", font=F["section"], fill=GOLD)
    y += 52
    cells = [
        ("QB", "1", QB),
        ("RB", "2", RB),
        ("WR", "2", WR),
        ("TE", "1", TE),
        ("RWT", "2", RWT),
        ("K", "1", K),
        ("DST", "1", DST),
    ]
    gap = 9
    cw = (w - gap * (len(cells) - 1)) / len(cells)
    for idx, (name, count, color) in enumerate(cells):
        cx = x + idx * (cw + gap)
        rounded(draw, (cx, y, cx + cw, y + 92), color, "#000000", 10, 2)
        name_fill = "#06100B" if name in {"WR", "RWT"} else "#FFFFFF"
        tw, _ = text_size(draw, name, F["small_bold"])
        draw.text((cx + (cw - tw) / 2, y + 18), name, font=F["small_bold"], fill=name_fill)
        tw, _ = text_size(draw, count, F["stat"])
        draw.text((cx + (cw - tw) / 2, y + 48), count, font=F["stat"], fill=name_fill)
    return y + 122


def section(draw, x, y, w, title, body, accent=GOLD):
    rounded(draw, (x, y, x + w, y + 175), PANEL, BORDER, 16, 2)
    draw.rectangle((x, y, x + 9, y + 175), fill=accent)
    draw.text((x + 28, y + 22), title, font=F["section"], fill=accent)
    draw_wrapped(draw, (x + 28, y + 72), body, F["body"], TEXT, w - 56)
    return y + 195


def phase_card(draw, x, y, w, num, title, body, accent):
    rounded(draw, (x, y, x + w, y + 128), PANEL, BORDER, 15, 2)
    draw.rectangle((x, y, x + 72, y + 128), fill=PANEL_2)
    draw.text((x + 18, y + 38), num, font=F["mode_num"], fill=accent)
    draw.text((x + 95, y + 20), title, font=F["body_bold"], fill=accent)
    draw_wrapped(draw, (x + 95, y + 58), body, F["small"], TEXT, w - 120, 5)
    return y + 145


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 12), fill=GOLD)
    draw.rectangle((0, 12, W, 19), fill=STEEL)
    draw.rectangle((0, 0, 16, H), fill=NAVY)

    centered(draw, 44, "DISCORD FANTASY RULES", F["eyebrow"], CYAN)
    centered(draw, 88, "THE PYRAMID", F["title"], GOLD)
    centered(draw, 176, "Two 9-week sessions. Promotion. Relegation. Prestige.", F["subtitle"], STEEL)

    y = pyramid_mark(draw, 70, 240, W - 140)

    margin = 70
    gap = 18
    card_w = (W - margin * 2 - gap * 2) / 3
    stat_card(draw, margin, y + 20, card_w, 120, "10-300", "TEAMS")
    stat_card(draw, margin + card_w + gap, y + 20, card_w, 120, "$10", "ENTRY FEE")
    stat_card(draw, margin + (card_w + gap) * 2, y + 20, card_w, 120, "2 x 9", "WEEK SESSIONS")

    y += 175
    y = lineup(draw, margin, y, W - margin * 2)

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "THE CORE STRUCTURE",
        "Every team starts in a 10-team draft room. Weeks 1-9 are your draft-room season. Weeks 10-18 reorganize teams by results into prestige divisions where managers climb, hold, or fight off relegation.",
        CYAN,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "SCORING SNAPSHOT",
        "Standard PPR foundation with 6-point touchdowns, points for yardage, return-yard bonuses, sack penalties, turnover penalties, and meaningful DST scoring. Same familiar scoring feel as The Arena.",
        GREEN,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "WHY $10?",
        "Low barrier to entry, but enough buy-in to keep people active. Discord leaders take $0. Entry money supports hosting, prizes, league operations, or champion rewards.",
        GOLD,
    )

    draw.text((margin, y + 4), "THE TWO-SEASON LADDER", font=F["section"], fill=GOLD)
    y += 58
    y = phase_card(draw, margin, y, W - margin * 2, "01", "WEEKS 1-9: DRAFT-ROOM SEASON", "Single round-robin inside your 10-team draft division. Waivers stay inside the division.", CYAN)
    y = phase_card(draw, margin, y, W - margin * 2, "02", "WEEKS 10-18: PRESTIGE SEASON", "No new draft. Rosters continue, but opponents change as teams are sorted into prestige divisions.", GOLD)
    y = phase_card(draw, margin, y, W - margin * 2, "03", "NEXT YEAR: PRESTIGE CARRIES", "Players reset with no keepers, but earned prestige carries into the next NFL season.", GREEN)

    rounded(draw, (margin, H - 145, W - margin, H - 62), PANEL_2, GOLD, 18, 2)
    centered(draw, H - 121, "Start in the draft room. Climb the ladder. Defend your prestige.", F["body_bold"], TEXT)
    centered(draw, H - 88, "Everyone starts somewhere. The Pyramid gives every manager a place to climb.", F["body_bold"], CYAN)

    img.save(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    build()
