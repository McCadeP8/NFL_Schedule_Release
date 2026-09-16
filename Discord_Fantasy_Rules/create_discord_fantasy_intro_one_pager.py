from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("discord_fantasy_intro_one_pager.png")

W, H = 1200, 1840
BG = "#101114"
PANEL = "#181B20"
PANEL_2 = "#20242B"
BORDER = "#3A414D"
NEON = "#A8FF3E"
SIGNAL = "#24D8FF"
GOLD = "#E7C46A"
ORANGE = "#FF8A3D"
SAND = "#D7B77A"
TEXT = "#F5F7FA"
MUTED = "#B8C0CC"
INK = "#090A0C"

QB = "#D62828"
RB = "#F77F00"
WR = "#FFD60A"
TE = "#00A86B"
RWT = "#A7E8FF"
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
    "eyebrow": font(24, True),
    "brand": font(46, True),
    "title": font(70, True),
    "subtitle": font(30, False),
    "section": font(32, True),
    "body": font(24, False),
    "body_bold": font(24, True),
    "small": font(20, False),
    "small_bold": font(20, True),
    "tiny": font(15, True),
    "date": font(26, True),
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


def header_visual(draw):
    for x in range(70, W - 70, 88):
        draw.line((x, 42, x + 38, 42), fill=BORDER, width=2)
        draw.line((x + 50, 42, x + 66, 42), fill=NEON, width=3)
    rounded(draw, (190, 82, W - 190, 160), PANEL, NEON, 22, 3)
    centered(draw, 98, "SCHEDULE LEAK FANTASY", F["brand"], NEON)
    centered(draw, 168, "Built by the Discord that sees kickoff coming.", F["subtitle"], MUTED)


def lineup(draw, x, y, w):
    draw.text((x, y), "SHARED LINEUP", font=F["section"], fill=GOLD)
    y += 50
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
        rounded(draw, (cx, y, cx + cw, y + 82), color, "#000000", 10, 2)
        fill = "#06100B" if name in {"WR", "RWT"} else "#FFFFFF"
        tw, _ = text_size(draw, name, F["small_bold"])
        draw.text((cx + (cw - tw) / 2, y + 12), name, font=F["small_bold"], fill=fill)
        tw, _ = text_size(draw, count, F["body_bold"])
        draw.text((cx + (cw - tw) / 2, y + 43), count, font=F["body_bold"], fill=fill)
    return y + 110


def section(draw, x, y, w, title, body, accent=NEON, h=170):
    rounded(draw, (x, y, x + w, y + h), PANEL, BORDER, 16, 2)
    draw.rectangle((x, y, x + 9, y + h), fill=accent)
    draw.text((x + 28, y + 22), title, font=F["section"], fill=accent)
    draw_wrapped(draw, (x + 28, y + 70), body, F["body"], TEXT, w - 56)
    return y + h + 16


def draw_arena_preview(draw, x, y, w):
    cx = x + w / 2
    draw.ellipse((cx - 95, y + 18, cx + 95, y + 67), outline="#D93025", width=4)
    draw.ellipse((cx - 62, y + 27, cx + 62, y + 58), outline="#F5A623", width=2)
    for idx in range(7):
        px = cx - 48 + idx * 16
        draw.line((px, y + 27, px, y + 58), fill=BORDER, width=2)


def draw_colosseum_preview(draw, x, y, w):
    cx = x + w / 2
    draw.polygon([(cx - 108, y + 11), (cx + 108, y + 11), (cx + 95, y + 72), (cx - 95, y + 72)], fill="#2D241C", outline="#D7B77A")
    for idx in range(8):
        px = cx - 74 + idx * 21
        draw.rectangle((px, y + 25, px + 10, y + 66), fill="#D7B77A", outline="#8C6239")


def draw_pyramid_preview(draw, x, y, w):
    cx = x + w / 2
    colors = ["#8EEBFF", "#D8B62E", "#C7CDD3", "#C8843E", "#B80F0A", "#00A86B", "#1657B7", "#575B60"]
    top = 55
    for idx, color in enumerate(colors):
        layer_w = top + idx * 22
        ly = y + 8 + idx * 9
        draw.rectangle((cx - layer_w / 2, ly, cx + layer_w / 2, ly + 7), fill=color)


def release_card(draw, x, y, w, name, date, accent, preview):
    rounded(draw, (x, y, x + w, y + 182), PANEL, accent, 16, 2)
    preview(draw, x + 16, y + 16, w - 32)
    draw.text((x + 22, y + 96), name, font=F["body_bold"], fill=accent)
    draw.text((x + 22, y + 132), date, font=F["date"], fill=TEXT)


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 12), fill=NEON)
    draw.rectangle((0, 12, W, 19), fill=SIGNAL)
    draw.rectangle((0, 0, 16, H), fill=PANEL_2)
    header_visual(draw)

    margin = 70
    y = 250
    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "THREE LOW-STAKES LEAGUES",
        "We are excited to host three unique fantasy leagues as this Discord grows. They are simple enough for a beginner to play in, but layered enough that experienced fantasy players will still find extra strategy to chase.",
        SIGNAL,
        190,
    )
    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "COMMUNITY FIRST",
        "Low buy-ins help promote activity without turning this into a pure cash-league grind. Discord leaders take $0. Entry money helps cover Fantrax and website services, league tools, trophies, merch, champion rewards, and maybe cash prizes if pools get large enough.",
        NEON,
        220,
    )
    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "PLAY FOR MORE THAN PROFIT",
        "Champions and standout managers can earn special Discord roles, titles, and bragging rights. If you only want to turn a profit, there are other leagues for that. This is for people who want something active, fresh, and memorable.",
        GOLD,
        205,
    )

    y = lineup(draw, margin, y + 4, W - margin * 2)
    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "SHARED SCORING",
        "All three leagues use the same familiar scoring foundation: standard PPR, 6-point touchdowns, yardage scoring, return-yard bonuses, sack penalties, turnover penalties, and meaningful DST scoring.",
        ORANGE,
        160,
    )

    draw.text((margin, y + 4), "RELEASE WINDOWS", font=F["section"], fill=NEON)
    y += 58
    gap = 18
    card_w = (W - margin * 2 - gap * 2) / 3
    release_card(draw, margin, y, card_w, "THE PYRAMID", "JULY 18 - 9 PM ET", SIGNAL, draw_pyramid_preview)
    release_card(draw, margin + card_w + gap, y, card_w, "THE COLOSSEUM", "JULY 25 - 9 PM ET", SAND, draw_colosseum_preview)
    release_card(draw, margin + (card_w + gap) * 2, y, card_w, "THE ARENA", "AUG. 1 - 9 PM ET", RED := "#D93025", draw_arena_preview)
    y += 220

    rounded(draw, (margin, y, W - margin, y + 190), PANEL_2, NEON, 20, 2)
    centered(draw, y + 30, "THE INVITE", F["section"], NEON)
    draw_wrapped(
        draw,
        (margin + 36, y + 84),
        "Jump in for the format that fits you best. Try something new. Chase a title. Earn a role. Talk football with people who are paying attention every week.",
        F["body"],
        TEXT,
        W - margin * 2 - 72,
        8,
    )

    img.save(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    build()
