from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("the_colosseum_one_pager.png")

W, H = 1200, 2500
BG = "#F3EEE4"
INK = "#151515"
NAVY = "#102A43"
LIGHT_SANDSTONE = "#D7B77A"
DARK_SANDSTONE = "#8C6239"
PANEL = "#FFF9ED"
PANEL_2 = "#E8DDCA"
BORDER = "#9A8368"
PARCHMENT = "#E1D1B7"
BRONZE = "#A86F32"
GOLD = "#C29545"
CRIMSON = "#8C1D18"
RED = "#C2412D"
TEAL = "#216E6A"
TEXT = "#201815"
MUTED = "#675A4E"
SILVER = "#B9B6AE"
BLUE = "#1D4F7A"

QB = "#D62828"
RB = "#F77F00"
WR = "#FFD60A"
RWT = "#A7E8FF"
TE = "#00A86B"
K = "#D45087"
DST = "#1D4ED8"


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
    "title": font(76, True),
    "subtitle": font(32, False),
    "section": font(34, True),
    "body": font(25, False),
    "body_bold": font(25, True),
    "small": font(21, False),
    "small_bold": font(21, True),
    "tiny": font(16, True),
    "stat": font(30, True),
    "stat_sub": font(21, True),
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


def stat_card(draw, x, y, w, h, title, subtitle):
    rounded(draw, (x, y, x + w, y + h), PANEL, BRONZE, 14, 2)
    tw, _ = text_size(draw, title, F["stat"])
    draw.text((x + (w - tw) / 2, y + 22), title, font=F["stat"], fill=GOLD)
    for i, line in enumerate(wrap(draw, subtitle, F["stat_sub"], w - 34)):
        tw, _ = text_size(draw, line, F["stat_sub"])
        draw.text((x + (w - tw) / 2, y + 70 + i * 28), line, font=F["stat_sub"], fill=MUTED)


def colosseum_mark(draw, x, y, w):
    cx = x + w / 2
    draw.polygon([(cx - 315, y + 18), (cx + 315, y + 18), (cx + 270, y + 142), (cx - 270, y + 142)], fill=PANEL, outline=BORDER)
    for idx in range(8):
        px = cx - 210 + idx * 60
        draw.rectangle((px, y + 42, px + 26, y + 130), fill=PARCHMENT, outline=BORDER, width=2)
        draw.arc((px - 4, y + 22, px + 30, y + 58), 180, 360, fill=BORDER, width=2)
    draw.rectangle((cx - 175, y + 73, cx + 175, y + 105), fill=NAVY)
    centered(draw, y + 72, "GRIDIRON GLADIATORS", F["small_bold"], "#FFFFFF")
    draw.line((cx - 250, y + 142, cx + 250, y + 142), fill=BRONZE, width=5)
    return y + 178


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
    rounded(draw, (x, y, x + w, y + 165), PANEL, BORDER, 16, 2)
    draw.rectangle((x, y, x + 9, y + 165), fill=accent)
    draw.text((x + 28, y + 22), title, font=F["section"], fill=accent)
    draw_wrapped(draw, (x + 28, y + 72), body, F["body"], TEXT, w - 56)
    return y + 185


def divisions_visual(draw, x, y, w):
    draw.text((x, y), "NFL-STYLE DIVISIONS", font=F["section"], fill=NAVY)
    y += 52
    conf_gap = 18
    conf_w = (w - conf_gap) / 2
    div_names = ["North", "South", "East", "West"]
    for conf_idx, (conf, prefix, color) in enumerate([("PRAETORIAN", "P", LIGHT_SANDSTONE), ("GLADIATOR", "G", DARK_SANDSTONE)]):
        cx = x + conf_idx * (conf_w + conf_gap)
        rounded(draw, (cx, y, cx + conf_w, y + 318), PANEL, color, 16, 3)
        draw.rectangle((cx, y, cx + conf_w, y + 42), fill=color)
        tw, _ = text_size(draw, conf, F["body_bold"])
        header_fill = INK if color == LIGHT_SANDSTONE else "#FFFFFF"
        draw.text((cx + (conf_w - tw) / 2, y + 8), conf, font=F["body_bold"], fill=header_fill)
        div_w = (conf_w - 42) / 2
        for idx, div in enumerate(div_names):
            dx = cx + 14 + (idx % 2) * (div_w + 14)
            dy = y + 58 + (idx // 2) * 122
            rounded(draw, (dx, dy, dx + div_w, dy + 104), PANEL_2, BORDER, 10, 2)
            draw.text((dx + 12, dy + 10), div.upper(), font=F["tiny"], fill=INK if color == LIGHT_SANDSTONE else color)
            for t in range(4):
                tx = dx + 12 + (t % 2) * ((div_w - 34) / 2 + 10)
                ty = dy + 42 + (t // 2) * 27
                twid = (div_w - 34) / 2
                draw.rounded_rectangle((tx, ty, tx + twid, ty + 20), radius=4, fill="#FFFFFF", outline=BORDER, width=1)
                label = f"{prefix}{idx + 1}-{t + 1}"
                lw, _ = text_size(draw, label, F["tiny"])
                draw.text((tx + (twid - lw) / 2, ty + 2), label, font=F["tiny"], fill=INK)
    return y + 346


def playoff_visual(draw, x, y, w):
    draw.text((x, y), "14-TEAM NFL-STYLE PLAYOFF", font=F["section"], fill=NAVY)
    y += 52
    rounded(draw, (x, y, x + w, y + 238), PANEL, BORDER, 16, 2)
    row_y = [y + 42, y + 112]
    for row, (conf, color) in enumerate([("PRAET.", LIGHT_SANDSTONE), ("GLAD.", DARK_SANDSTONE)]):
        draw.text((x + 24, row_y[row] + 14), conf, font=F["small_bold"], fill=color)
        slot_w = 72
        gap = 12
        start_x = x + 104
        labels = ["1 BYE", "2", "3", "4", "5", "6", "7"]
        for idx, label in enumerate(labels):
            sx = start_x + idx * (slot_w + gap)
            fill = color if idx == 0 else "#FFFFFF"
            tfill = INK if color == LIGHT_SANDSTONE else "#FFFFFF" if idx == 0 else INK
            draw.rounded_rectangle((sx, row_y[row], sx + slot_w, row_y[row] + 52), radius=8, fill=fill, outline=BORDER, width=2)
            tw, _ = text_size(draw, label, F["tiny"])
            draw.text((sx + (slot_w - tw) / 2, row_y[row] + 17), label, font=F["tiny"], fill=tfill)
    draw_wrapped(
        draw,
        (x + 28, y + 168),
        "Seven teams per conference qualify. Each conference's 1-seed gets the bye, just like the modern NFL playoff shape.",
        F["small"],
        TEXT,
        w - 56,
        5,
    )
    return y + 264


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 12), fill=CRIMSON)
    draw.rectangle((0, 12, W, 19), fill=GOLD)
    draw.rectangle((0, 0, 16, H), fill=NAVY)

    centered(draw, 44, "DISCORD FANTASY RULES", F["eyebrow"], NAVY)
    centered(draw, 88, "THE COLOSSEUM", F["title"], GOLD)
    centered(draw, 174, "NFL-style fantasy with duplicate-player strategy.", F["subtitle"], MUTED)
    y = colosseum_mark(draw, 70, 235, W - 140)

    margin = 70
    gap = 18
    card_w = (W - margin * 2 - gap * 2) / 3
    stat_card(draw, margin, y + 10, card_w, 120, "32", "TEAMS")
    stat_card(draw, margin + card_w + gap, y + 10, card_w, 120, "$20", "ENTRY FEE")
    stat_card(draw, margin + (card_w + gap) * 2, y + 10, card_w, 120, "2x", "DUPLICATE PLAYERS")

    y += 165
    y = lineup(draw, margin, y, W - margin * 2)

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "LEAGUE STRUCTURE",
        "A 32-team league structured like the NFL: 8 divisions of 4 teams, a 17-game regular season, and a 14-team playoff after the regular season.",
        BRONZE,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "SCORING SNAPSHOT",
        "Same starters and same scoring foundation: standard PPR, 6-point touchdowns, yardage scoring, return-yard bonuses, sack penalties, turnover penalties, and meaningful DST scoring.",
        TEAL,
    )

    y = divisions_visual(draw, margin, y, W - margin * 2)
    y = playoff_visual(draw, margin, y, W - margin * 2)

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "SCHEDULE TWIST",
        "Weeks 1, 4, and 12 are double-matchup weeks. That keeps the regular season at 17 games while adding a few high-pressure Sundays.",
        RED,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "WHY $20?",
        "A bigger, NFL-style league with more structure and a deeper playoff race. Discord leaders take $0; entry money supports hosting, prizes, league operations, or champion rewards.",
        GOLD,
    )

    rounded(draw, (margin, H - 145, W - margin, H - 62), PANEL_2, GOLD, 18, 2)
    centered(draw, H - 121, "Thirty-two teams. Seventeen games. Fourteen playoff spots.", F["body_bold"], TEXT)
    centered(draw, H - 88, "Win your division. Survive the bracket. Rule the Colosseum.", F["body_bold"], GOLD)

    img.save(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    build()
