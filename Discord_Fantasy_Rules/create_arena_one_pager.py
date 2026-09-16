from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).with_name("the_arena_one_pager.png")

W, H = 1200, 1980
BG = "#080D0A"
PANEL = "#101A14"
PANEL_2 = "#162319"
BORDER = "#2A3E2B"
GOLD = "#F5A623"
SAND = "#C5A572"
RED = "#D93025"
GREEN = "#2ECC71"
TEXT = "#F2F5F2"
MUTED = "#A7B5A7"
STEEL = "#C0C0C8"
BLUE = "#4A90E2"

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
    "title": font(86, True),
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
    tw, th = text_size(draw, title, F["stat"])
    draw.text((x + (w - tw) / 2, y + 22), title, font=F["stat"], fill=GOLD)
    for i, line in enumerate(wrap(draw, subtitle, F["stat_sub"], w - 34)):
        tw, _ = text_size(draw, line, F["stat_sub"])
        draw.text((x + (w - tw) / 2, y + 70 + i * 28), line, font=F["stat_sub"], fill=STEEL)


def section(draw, x, y, w, title, body, accent=GOLD):
    rounded(draw, (x, y, x + w, y + 175), PANEL, BORDER, 16, 2)
    draw.rectangle((x, y, x + 9, y + 175), fill=accent)
    draw.text((x + 28, y + 22), title, font=F["section"], fill=accent)
    draw_wrapped(draw, (x + 28, y + 72), body, F["body"], TEXT, w - 56)
    return y + 195


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


def mode_card(draw, x, y, w, num, title, body, accent):
    rounded(draw, (x, y, x + w, y + 128), PANEL, BORDER, 15, 2)
    draw.rectangle((x, y, x + 72, y + 128), fill=PANEL_2)
    draw.text((x + 20, y + 38), num, font=F["mode_num"], fill=accent)
    draw.text((x + 95, y + 20), title, font=F["body_bold"], fill=accent)
    draw_wrapped(draw, (x + 95, y + 58), body, F["small"], TEXT, w - 120, 5)
    return y + 145


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 12), fill=RED)
    draw.rectangle((0, 12, W, 19), fill=GOLD)
    draw.rectangle((0, 0, 16, H), fill="#1E301E")

    centered(draw, 44, "DISCORD FANTASY RULES", F["eyebrow"], GREEN)
    centered(draw, 88, "THE ARENA", F["title"], GOLD)
    centered(draw, 180, "No draft. No repeats. Three ways to win.", F["subtitle"], STEEL)

    cx, cy = W // 2, 292
    draw.ellipse((cx - 255, cy - 70, cx + 255, cy + 70), outline=RED, width=5)
    draw.ellipse((cx - 195, cy - 45, cx + 195, cy + 45), outline=GOLD, width=3)
    for i in range(9):
        x = cx - 150 + i * 37
        draw.line((x, cy - 43, x, cy + 43), fill=BORDER, width=3)
    centered(draw, 278, "SURVIVE THE SUNDAY CROWD", F["small_bold"], GOLD)

    y = 405
    margin = 70
    gap = 18
    card_w = (W - margin * 2 - gap * 2) / 3
    stat_card(draw, margin, y, card_w, 120, "2-300", "TEAMS")
    stat_card(draw, margin + card_w + gap, y, card_w, 120, "$10", "ENTRY FEE")
    stat_card(draw, margin + (card_w + gap) * 2, y, card_w, 120, "180", "UNIQUE SLOTS")

    y += 155
    y = lineup(draw, margin, y, W - margin * 2)

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "THE CORE STRUCTURE",
        "Each week you set the full lineup above. Once your team uses a player, that same team cannot use him again all season. Ten starters across 18 weeks equals 180 unique player decisions.",
        GREEN,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "SCORING SNAPSHOT",
        "Standard PPR foundation with 6-point touchdowns, points for yardage, return-yard bonuses, sack penalties, turnover penalties, and meaningful DST scoring. The goal is familiar fantasy scoring with enough tweaks to reward smart weekly choices.",
        BLUE,
    )

    y = section(
        draw,
        margin,
        y,
        W - margin * 2,
        "WHY $10?",
        "Low enough that almost anyone can join, meaningful enough that managers stay active. Discord leaders take $0. Entry money supports hosting, prizes, league operations, or champion rewards.",
        GOLD,
    )

    draw.text((margin, y + 4), "THREE WAYS TO WIN", font=F["section"], fill=GOLD)
    y += 58
    y = mode_card(draw, margin, y, W - margin * 2, "01", "SWISS H2H TOURNAMENT", "Weekly head-to-head pairings by record. Win matchups, build seeding, and survive the bracket pressure.", BLUE)
    y = mode_card(draw, margin, y, W - margin * 2, "02", "TOTAL POINTS", "Every point across the season counts. Highest cumulative score wins the pure leaderboard race.", GOLD)
    y = mode_card(draw, margin, y, W - margin * 2, "03", "GUILLOTINE", "The lowest weekly scores are eliminated as the field shrinks. Multiple managers can be cut each week.", RED)

    rounded(draw, (margin, H - 145, W - margin, H - 62), PANEL_2, GOLD, 18, 2)
    centered(draw, H - 121, "No draft room. No waiver grind. Just 18 weeks of decisions.", F["body_bold"], TEXT)
    centered(draw, H - 88, "Can you be the last manager standing?", F["body_bold"], GREEN)

    img.save(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    build()
