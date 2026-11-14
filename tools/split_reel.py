"""Split-screen "explainer" reel (format asked for by Pravin on 14 Nov 2026, after an ad reel he liked).

    python tools/split_reel.py prompts DIR TEMPLATE  # script.json -> prompts/shotN.txt + prompts/flow_message.txt
    python tools/split_reel.py build DIR            # clips/shotN.mp4 + script.json -> reel.mp4 + check/*.jpg

Layout (1080x1920):
  top 1010 px    host clip (cropped close-up, punch-in jump cuts) or an animated B-roll card,
                 word-chunk captions with the *key* word in orange, hook box, CTA pill at the end
  bottom 910 px  a fixed "poster" (title + 3 steps); the step the host is talking about lights up

Extra script.json keys (on top of the reel.py ones):
  "poster": {"title_small", "title_big", "steps": [{"label", "title", "sub", "on": [shot, frac]}]}
  "cta":    {"text", "on": [shot, frac]}
  shots[i]["broll"]: [{"at": frac, "to": frac, "card": {...}}]   (fractions of that shot's speech window)
  card types: clock {time, thoughts[]}, note {title, lines[]}, checklist {title, items[]},
              chat {title, messages[{from: me|her, text}]}, quote {text}; every card has a "label".
"""
import json
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel  # noqa: E402
import soft_music  # noqa: E402
from reel import FFMPEG, FPS, W, H, chunks, duration, font, load, run, speech_window  # noqa: E402

TOP = 1010
BOT = H - TOP
ORANGE = (255, 106, 26)
DARK = (14, 16, 22)
CREAM = (251, 245, 236)
INK = (32, 30, 36)
GREY = (120, 116, 124)
ON_ACCENT = (255, 255, 255)   # text drawn on the accent colour
GLOW = (120, 50, 20)          # corner glow of the dark card background
GRID = (22, 25, 32)
DOT = (232, 222, 208)         # poster paper dots
ACTIVE_FILL = (255, 233, 216)
DIM_TEXT, DIM_SUB, DIM_DOT, DIM_LINE = (176, 170, 172), (196, 190, 192), (240, 196, 170), (236, 190, 160)
FOOTER = "AI generated video | Motivational guru"
FOOTER_COL = (160, 150, 150)
GREEN, RED = (88, 201, 128), (232, 93, 93)
WIN, WIN_LINE = (24, 27, 35), (52, 57, 70)
THEMES = {
    # Trade With Captain Pravin: navy + gold, like its carousel slides
    "captain": {"ORANGE": (245, 184, 46), "DARK": (5, 13, 30), "CREAM": (12, 27, 54), "INK": (255, 255, 255),
                "GREY": (195, 207, 226), "ON_ACCENT": (5, 13, 30), "GLOW": (30, 60, 110), "GRID": (14, 26, 48),
                "DOT": (24, 42, 74), "ACTIVE_FILL": (22, 48, 90), "DIM_TEXT": (110, 126, 156),
                "DIM_SUB": (90, 106, 136), "DIM_DOT": (110, 96, 60), "DIM_LINE": (60, 70, 90),
                "FOOTER_COL": (150, 165, 190), "WIN": (14, 30, 58), "WIN_LINE": (44, 70, 112)},
}
HOST_CROP_Y = 70          # px from the top of the 1080x1920 host frame
FACE = (540, 360)         # punch-in centre inside the top panel
ZOOMS = [1.0, 1.08]
MUSIC_VOL = 0.15


# ---------- small drawing helpers ----------

def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def tick(d, x, y, s, color, width=7):
    d.line([(x, y + s * 0.5), (x + s * 0.38, y + s * 0.85), (x + s, y + s * 0.1)], fill=color, width=width,
           joint="curve")


def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


# ---------- top panel pieces ----------

def dark_bg():
    img = Image.new("RGB", (W, TOP), DARK)
    glow = Image.new("L", (W, TOP), 0)
    ImageDraw.Draw(glow).ellipse([W - 420, -320, W + 320, 360], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img.paste(Image.new("RGB", (W, TOP), GLOW), (0, 0), glow)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 54):          # faint grid, like a code-editor backdrop
        d.line([(x, 0), (x, TOP)], fill=GRID)
    for y in range(0, TOP, 54):
        d.line([(0, y), (W, y)], fill=GRID)
    return img


def label_pill(text, size=34):
    f = font("ExtraBold", size)
    t = text.upper()
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(tmp.textlength(t, font=f)) + 44
    img = Image.new("RGBA", (w, size + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, size + 29], radius=10, fill=ORANGE)
    d.text((22, 9), t, font=f, fill=ON_ACCENT)
    return img


def window(img, title, box=(70, 150, 1010, 820)):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=26, fill=WIN, outline=WIN_LINE, width=3)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 30 + i * 34, y0 + 26, x0 + 52 + i * 34, y0 + 48], fill=c)
    d.text((x0 + 150, y0 + 20), title, font=font("SemiBold", 28), fill=(150, 156, 170))
    d.line([(x0, y0 + 74), (x1, y0 + 74)], fill=WIN_LINE, width=2)
    return d, (x0 + 50, y0 + 110, x1 - 50, y1 - 40)


def card_frame(card, p, bg):
    """Render a B-roll card at progress p (0..1) as a 1080xTOP RGB image."""
    img = bg.copy()
    kind = card["type"]
    f_body = font("SemiBold", 44)
    if kind == "clock":
        d = ImageDraw.Draw(img)
        f = font("ExtraBold", 190)
        t = card["time"]
        d.text(((W - d.textlength(t, font=f)) / 2, 150), t, font=f, fill=(245, 245, 250))
        sub = "Neend nahi aa rahi..."
        fs = font("SemiBold", 40)
        d.text(((W - d.textlength(sub, font=fs)) / 2, 380), sub, font=fs, fill=(150, 156, 170))
        spots = [(110, 520), (520, 600), (180, 700)]
        for i, th in enumerate(card["thoughts"]):
            q = ease((p - 0.12 - i * 0.22) / 0.12)
            if q <= 0:
                continue
            fb = font("SemiBold", 42)
            w = d.textlength(th, font=fb) + 60
            x, y = spots[i % len(spots)]
            y += int((1 - q) * 30)
            d.rounded_rectangle([x, y, x + w, y + 84], radius=42, fill=(36, 40, 52), outline=ORANGE, width=3)
            d.text((x + 30, y + 16), th, font=fb, fill=(255, 255, 255))
    elif kind == "note":
        d, (x0, y0, x1, y1) = window(img, "notes.txt")
        d.text((x0, y0), card["title"], font=font("ExtraBold", 50), fill=ORANGE)
        total = sum(len(l) for l in card["lines"])
        shown = int(total * ease(p / 0.8))
        y = y0 + 100
        for line in card["lines"]:
            part = line[:max(0, shown)]
            shown -= len(line)
            d.text((x0, y), "- " + part, font=f_body, fill=(235, 236, 240))
            if 0 < len(part) < len(line) or (shown <= 0 < len(part) and p < 0.8):
                cx = x0 + d.textlength("- " + part, font=f_body) + 6
                if int(p * 20) % 2 == 0:
                    d.rectangle([cx, y + 6, cx + 4, y + 54], fill=ORANGE)
            y += 90
            if shown <= 0:
                break
    elif kind == "checklist":
        d, (x0, y0, x1, y1) = window(img, "aaj_ka_kaam")
        d.text((x0, y0), card["title"], font=font("ExtraBold", 50), fill=ORANGE)
        y = y0 + 110
        n = len(card["items"])
        for i, item in enumerate(card["items"]):
            d.rounded_rectangle([x0, y, x0 + 56, y + 56], radius=12, outline=(110, 116, 130), width=4)
            done = p > 0.15 + i * (0.65 / n)
            if done:
                d.rounded_rectangle([x0, y, x0 + 56, y + 56], radius=12, fill=ORANGE)
                tick(d, x0 + 12, y + 14, 32, ON_ACCENT)
            d.text((x0 + 90, y + 2), item, font=f_body, fill=(235, 236, 240) if done else (150, 156, 170))
            y += 105
        d.text((x0, y1 - 50), "Bas ek. Baaki kal.", font=font("SemiBold", 34), fill=(150, 156, 170))
    elif kind == "chat":
        d, (x0, y0, x1, y1) = window(img, card.get("title", "chat"))
        y = y0 + 10
        msgs = card["messages"]
        for i, m in enumerate(msgs):
            start = i * 0.32
            if p < start:
                break
            text = m["text"]
            if i == len(msgs) - 1:
                text = text[:int(len(text) * ease((p - start) / 0.45))]
            lines = wrap(d, m["text"], f_body, 620)
            shown_lines = wrap(d, text, f_body, 620) if text else [""]
            bw = max(d.textlength(l, font=f_body) for l in lines) + 60
            bh = 64 * len(lines) + 34
            if m["from"] == "me":
                bx, fill, col = x1 - bw, (58, 64, 80), (240, 240, 245)
            else:
                bx, fill, col = x0, ORANGE, ON_ACCENT
            d.rounded_rectangle([bx, y, bx + bw, y + bh], radius=30, fill=fill)
            for k, l in enumerate(shown_lines):
                d.text((bx + 30, y + 16 + k * 64), l, font=f_body, fill=col)
            y += bh + 36
    elif kind == "chart":
        # candles appear one by one; optional bubble text pops up at the end
        d, (x0, y0, x1, y1) = window(img, card.get("title", "EURUSD  M5"))
        candles = card.get("candles") or [(0, 1), (1, -1), (0.5, 2), (2.2, -1.5), (1, 1.6), (2.4, -2.2), (0.6, -1),
                                          (-0.2, 1.4), (1, 2), (2.8, -0.8), (2.2, 1.6), (3.6, -2.6), (1.2, 0.9)]
        lo = min(min(o, o + c) for o, c in candles) - 1
        hi = max(max(o, o + c) for o, c in candles) + 1
        ys = lambda v: y1 - 40 - (v - lo) / (hi - lo) * (y1 - y0 - 80)
        n = max(1, int(len(candles) * ease(p / 0.7)))
        cw = (x1 - x0) / len(candles)
        for i, (o, c) in enumerate(candles[:n]):
            col = GREEN if c >= 0 else RED
            cx = x0 + cw * (i + 0.5)
            top, bot = ys(max(o, o + c)), ys(min(o, o + c))
            d.line([(cx, top - 22), (cx, bot + 22)], fill=col, width=4)
            d.rectangle([cx - cw * 0.3, top, cx + cw * 0.3, max(bot, top + 6)], fill=col)
        if card.get("bubble") and p > 0.6:
            fb = font("ExtraBold", 50)
            t = card["bubble"]
            w = d.textlength(t, font=fb) + 70
            d.rounded_rectangle([x1 - w, y0, x1, y0 + 96], radius=48, fill=ORANGE)
            d.text((x1 - w + 35, y0 + 16), t, font=fb, fill=ON_ACCENT)
    elif kind == "trades":
        # trade log rows slide in one by one: [time, pair, result, "red"|"green"]
        d, (x0, y0, x1, y1) = window(img, card.get("title", "trade_log"))
        rows = card["rows"]
        y = y0
        fr = font("SemiBold", 40)
        for i, (tm, pair, res, c) in enumerate(rows):
            if p < 0.05 + i * (0.6 / len(rows)):
                break
            d.rounded_rectangle([x0, y, x1, y + 84], radius=16, fill=WIN, outline=WIN_LINE, width=2)
            d.text((x0 + 24, y + 18), tm, font=fr, fill=GREY)
            d.text((x0 + 210, y + 18), pair, font=fr, fill=(240, 242, 248))
            d.text((x1 - 24 - d.textlength(res, font=fr), y + 18), res, font=font("ExtraBold", 40),
                   fill=GREEN if c == "green" else RED)
            y += 100
        if card.get("note") and p > 0.7:
            d.text((x0, y1 - 46), card["note"], font=font("ExtraBold", 40), fill=ORANGE)
    elif kind == "counter":
        # big number counting up, e.g. trades taken today
        d = ImageDraw.Draw(img)
        v = int(round(card["to"] * ease(p / 0.7)))
        f = font("ExtraBold", 300)
        t = str(v)
        d.text(((W - d.textlength(t, font=f)) / 2, 150), t, font=f, fill=RED if v >= card.get("warn", 10**9) else
               (245, 245, 250))
        fs = font("ExtraBold", 54)
        d.text(((W - d.textlength(card["caption"], font=fs)) / 2, 520), card["caption"], font=fs, fill=GREY)
        if card.get("note") and p > 0.6:
            fb = font("ExtraBold", 48)
            w = d.textlength(card["note"], font=fb) + 70
            d.rounded_rectangle([(W - w) / 2, 640, (W + w) / 2, 732], radius=46, fill=RED)
            d.text(((W - w) / 2 + 35, 655), card["note"], font=fb, fill=(255, 255, 255))
    elif kind == "lots":
        # rising bars: [label, value text, height 0..1]; the risk line turns red
        d, (x0, y0, x1, y1) = window(img, card.get("title", "lot_size"))
        bars = card["bars"]
        bw = (x1 - x0) / (len(bars) * 1.6)
        for i, (lab, val, hgt) in enumerate(bars):
            q = ease((p - 0.08 - i * 0.18) / 0.2)
            if q <= 0:
                continue
            bx = x0 + 40 + i * bw * 1.6
            top = y1 - 70 - (y1 - y0 - 200) * hgt * q
            col = GREEN if i == 0 else (ORANGE if i < len(bars) - 1 else RED)
            d.rounded_rectangle([bx, top, bx + bw, y1 - 70], radius=12, fill=col)
            fv = font("ExtraBold", 40)
            d.text((bx + (bw - d.textlength(val, font=fv)) / 2, top - 54), val, font=fv, fill=(240, 242, 248))
            fl = font("SemiBold", 30)
            d.text((bx + (bw - d.textlength(lab, font=fl)) / 2, y1 - 56), lab, font=fl, fill=GREY)
        if card.get("note") and p > 0.75:
            d.text((x0, y0), card["note"], font=font("ExtraBold", 44), fill=RED)
    elif kind == "quote":
        d = ImageDraw.Draw(img)
        f = font("ExtraBold", 72)
        words = card["text"].split()
        n = max(1, int(len(words) * ease(p / 0.6)))
        lines = wrap(d, " ".join(w.replace("*", "") for w in words), f, 900)
        y = (TOP - len(lines) * 96) / 2
        i = 0
        for l in lines:
            x = (W - d.textlength(l, font=f)) / 2
            for w in l.split():
                if i >= n:
                    break
                hl = "*" in words[i]
                d.text((x, y), w, font=f, fill=ORANGE if hl else (255, 255, 255))
                x += d.textlength(w + " ", font=f)
                i += 1
            y += 96
    # slide-in for the first part of the card
    q = ease(p / 0.08) if p < 0.08 else 1.0
    if q < 1.0:
        img = Image.blend(bg, img, q)
    lab = label_pill(card["label"])
    img.paste(lab, (60, 50), lab)
    return img


def caption_rgba(piece):
    size = 70
    f = font("ExtraBold", size)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while True:
        text = " ".join(w for w, _ in piece)
        if tmp.textlength(text, font=f) <= W - 120 or size <= 50:
            break
        size -= 4
        f = font("ExtraBold", size)
    img = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    space = d.textlength(" ", font=f)
    total = sum(d.textlength(w, font=f) for w, _ in piece) + space * (len(piece) - 1)
    x = (W - total) / 2
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    xs = x
    for w, _ in piece:
        sd.text((xs + 3, 23), w, font=f, fill=(0, 0, 0, 230))
        xs += d.textlength(w, font=f) + space
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(shadow)
    d = ImageDraw.Draw(img)
    for w, hl in piece:
        d.text((x, 18), w, font=f, fill=ORANGE if hl else (255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        x += d.textlength(w, font=f) + space
    return img


def hook_rgba(text):
    f = font("ExtraBold", 54)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = wrap(tmp, text, f, W - 260)
    lh = 70
    bw = int(max(tmp.textlength(l, font=f) for l in lines)) + 70
    img = Image.new("RGBA", (W, lh * len(lines) + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([(W - bw) / 2, 0, (W + bw) / 2, lh * len(lines) + 40], radius=24,
                        fill=(255, 255, 255, 245))
    for i, l in enumerate(lines):
        d.text(((W - d.textlength(l, font=f)) / 2, 16 + i * lh), l, font=f, fill=(20, 20, 26))
    return img


def cta_rgba(text):
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    t = text.upper()
    size = 46
    while tmp.textlength(t, font=font("ExtraBold", size)) + 150 > W - 80 and size > 28:
        size -= 2
    f = font("ExtraBold", size)
    w = int(tmp.textlength(t, font=f)) + 150
    img = Image.new("RGBA", (w, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, 99], radius=50, fill=ORANGE, outline=(255, 255, 255), width=4)
    d.text((44, 50 - size * 0.62), t, font=f, fill=ON_ACCENT)
    ax = w - 72          # small arrow
    d.polygon([(ax, 34), (ax + 30, 50), (ax, 66)], fill=ON_ACCENT)
    return img


def ai_tag():
    f = font("SemiBold", 26)
    t = "AI generated"
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(tmp.textlength(t, font=f)) + 30
    img = Image.new("RGBA", (w, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, 43], radius=22, fill=(0, 0, 0, 120))
    d.text((15, 6), t, font=f, fill=(255, 255, 255, 220))
    return img


# ---------- bottom poster ----------

def poster(pc, active):
    img = Image.new("RGB", (W, BOT), CREAM)
    d = ImageDraw.Draw(img)
    for x in range(30, W, 40):       # dotted paper
        for y in range(30, BOT, 40):
            d.point((x, y), fill=DOT)
    fs, fb = font("SemiBold", 40), font("ExtraBold", 104)
    d.text(((W - d.textlength(pc["title_small"], font=fs)) / 2, 34), pc["title_small"], font=fs, fill=INK)
    d.text(((W - d.textlength(pc["title_big"], font=fb)) / 2, 74), pc["title_big"], font=fb, fill=ORANGE)
    d.line([(W / 2 - 90, 212), (W / 2 + 90, 212)], fill=ORANGE, width=6)

    # emblem with glow rings
    cx, cy = 190, 560
    glow = Image.new("L", (W, BOT), 0)
    gd = ImageDraw.Draw(glow)
    for r, a in [(170, 40), (130, 70), (95, 110)]:
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=a)
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    img.paste(Image.new("RGB", (W, BOT), ORANGE), (0, 0), glow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - 70, cy - 70, cx + 70, cy + 70], radius=34, fill=(255, 255, 255))
    num = "3" if active is None else str(active + 1)
    fn = font("ExtraBold", 96)
    d.text((cx - d.textlength(num, font=fn) / 2, cy - 72), num, font=fn, fill=ORANGE)

    steps = pc["steps"]
    row_y = [248, 444, 640]
    x0 = 400
    for i, st in enumerate(steps):
        y = row_y[i]
        on = active == i
        dim = active is not None and not on
        # connector from emblem to the step dot
        d.line([(cx + 70, cy), (x0 - 70, cy), (x0 - 70, y + 62), (x0 - 40, y + 62)],
               fill=ORANGE if on else DIM_LINE, width=5 if on else 3)
        if on:
            d.rounded_rectangle([x0 - 84, y - 16, W - 36, y + 174], radius=24, fill=ACTIVE_FILL,
                                outline=ORANGE, width=6)
        col_t = INK if not dim else DIM_TEXT
        col_s = GREY if not dim else DIM_SUB
        dot = ORANGE if not dim else DIM_DOT
        d.ellipse([x0 - 40 - 28, y + 34, x0 - 40 + 28, y + 90], fill=dot)
        fl = font("ExtraBold", 26)
        n = f"{i + 1:02d}"
        d.text((x0 - 40 - d.textlength(n, font=fl) / 2, y + 45), n, font=fl, fill=ON_ACCENT)
        d.text((x0 + 10, y), st["label"].upper(), font=font("ExtraBold", 28), fill=ORANGE if not dim else dot)
        d.text((x0 + 10, y + 34), st["title"], font=font("ExtraBold", 52), fill=col_t)
        fsub = font("SemiBold", 29)
        for k, l in enumerate(wrap(d, st["sub"], fsub, W - x0 - 70)[:2]):
            d.text((x0 + 10, y + 98 + k * 36), l, font=fsub, fill=col_s)
    ft = font("SemiBold", 26)
    for k, t in enumerate(reversed(FOOTER.split("|n|"))):
        d.text(((W - d.textlength(t, font=ft)) / 2, BOT - 52 - k * 34), t, font=ft, fill=FOOTER_COL)
    return img


# ---------- build ----------

def at(timings, shot, frac):
    a, b = timings[shot - 1]["speech"]
    return a + (b - a) * frac


def apply_theme(s):
    """script.json "theme": a name from THEMES and/or a dict of overrides; "footer": poster footer text."""
    th = s.get("theme")
    vals = dict(THEMES.get(th, {})) if isinstance(th, str) else dict(th or {})
    for k, v in vals.items():
        globals()[k] = tuple(v) if isinstance(v, list) else v
    if s.get("footer"):
        globals()["FOOTER"] = s["footer"]
    if "host_crop_y" in s:          # where the top panel starts inside the 1080x1920 host frame
        globals()["HOST_CROP_Y"] = int(s["host_crop_y"])
    if "face" in s:                 # punch-in centre inside the top panel
        globals()["FACE"] = tuple(s["face"])


def cmd_build(day):
    s = load(day)
    apply_theme(s)
    n = len(s["shots"])
    clips = [os.path.join(day, "clips", f"shot{i}.mp4") for i in range(1, n + 1)]
    for c in clips:
        if not os.path.exists(c):
            sys.exit(f"missing {c}")
    out = os.path.join(day, "reel.mp4")
    check = os.path.join(day, "check")
    os.makedirs(check, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        # 1. trim each clip to its speech and join (same as reel.py)
        timings, offset, segs = [], 0.0, []
        for i, c in enumerate(clips):
            s0, s1, dur = speech_window(c)
            a, b = max(0.0, s0 - 0.15), min(dur, s1 + 0.35)
            seg = os.path.join(tmp, f"seg{i}.mp4")
            r = run(["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", c,
                     "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
                     "-af", "aresample=44100,aformat=channel_layouts=stereo",
                     "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "192k", seg])
            if r.returncode:
                sys.exit(r.stderr[-1500:])
            L = duration(seg)
            timings.append({"shot": i + 1, "offset": offset, "speech": [offset + s0 - a, offset + s1 - a],
                            "trim": [a, b], "len": L})
            offset += L
            segs.append(seg)
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in segs)
        joined = os.path.join(tmp, "joined.mp4")
        r = run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
        if r.returncode:
            sys.exit(r.stderr[-1500:])
        total = duration(joined)
        nframes = int(total * FPS)

        # 2. audio: voice + soft music
        music = os.path.join(tmp, "music.wav")
        soft_music.main(music, total + 0.5)
        mix = os.path.join(tmp, "mix.m4a")
        r = run(["-i", joined, "-i", music, "-filter_complex",
                 f"[0:a]volume=1.0[va];[1:a]volume={s.get('music_vol', MUSIC_VOL)}[ma];"
                 f"[va][ma]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                 "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", mix])
        if r.returncode:
            sys.exit(r.stderr[-1500:])

        # 3. timeline
        caps = []
        for shot, t in zip(s["shots"], timings):
            pieces = chunks(shot["dialogue"])
            a, b = t["speech"]
            weights = [sum(len(w) for w, _ in p) + 2 for p in pieces]
            cur = a
            for p, wgt in zip(pieces, weights):
                dd = (b - a) * wgt / sum(weights)
                caps.append((cur, cur + dd, caption_rgba(p)))
                cur += dd
        brolls = []
        for i, shot in enumerate(s["shots"], start=1):
            for br in shot.get("broll", []):
                t0, t1 = at(timings, i, br["at"]), at(timings, i, br["to"])
                if br["to"] >= 1.0:
                    t1 = timings[i - 1]["offset"] + timings[i - 1]["len"]
                if br["at"] <= 0.0:
                    t0 = timings[i - 1]["offset"]
                brolls.append((t0, t1, br["card"]))
        pc = s["poster"]
        step_on = [at(timings, *st["on"]) for st in pc["steps"]]
        posters = {k: poster(pc, k) for k in [None] + list(range(len(pc["steps"])))}
        cta = s.get("cta")
        cta_t = at(timings, *cta["on"]) if cta else None
        cta_img = cta_rgba(cta["text"]) if cta else None
        hook = hook_rgba(s["hook"])
        tag = ai_tag()
        bg = dark_bg()
        cut_times = sorted([t["offset"] for t in timings[1:]] + [b[1] for b in brolls])

        def active_step(t):
            k = None
            for i, t0 in enumerate(step_on):
                if t >= t0:
                    k = i
            return k

        # 4. frames: decode host, composite, encode
        dec = subprocess.Popen([FFMPEG, "-v", "error", "-i", joined, "-vf",
                                f"crop={W}:{TOP}:0:{HOST_CROP_Y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               stdout=subprocess.PIPE)
        enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix,
                                "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                                "-t", f"{total:.3f}", out], stdin=subprocess.PIPE)
        fsize = W * TOP * 3
        prev_k, k_change = None, -10.0
        for fi in range(nframes):
            t = fi / FPS
            raw = dec.stdout.read(fsize)
            if len(raw) < fsize:
                break
            host = Image.frombytes("RGB", (W, TOP), raw)
            card = next((b for b in brolls if b[0] <= t < b[1]), None)
            if card:
                top = card_frame(card[2], (t - card[0]) / max(0.1, card[1] - card[0]), bg)
            else:
                z = ZOOMS[sum(1 for c in cut_times if c <= t) % 2]
                if z != 1.0:
                    cw, ch = W / z, TOP / z
                    x0 = min(max(0, FACE[0] - cw / 2), W - cw)
                    y0 = min(max(0, FACE[1] - ch / 2), TOP - ch)
                    host = host.resize((W, TOP), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
                top = host
            frame = Image.new("RGB", (W, H))
            frame.paste(top, (0, 0))
            frame = frame.convert("RGBA")
            if t < 2.8 and not card:
                frame.alpha_composite(hook, (0, 60))
            frame.alpha_composite(tag, (W - tag.width - 30, 30 if (t >= 2.8 or card) else TOP - 70))
            cap = next((c for c in caps if c[0] <= t < c[1]), None)
            if cap:
                frame.alpha_composite(cap[2], (0, TOP - 175))
            if cta_img is not None and t >= cta_t and not card:
                sc = 1.0 + 0.05 * math.sin((t - cta_t) * 2 * math.pi * 1.2)
                im = cta_img.resize((int(cta_img.width * sc), int(cta_img.height * sc)), Image.BILINEAR)
                frame.alpha_composite(im, ((W - im.width) // 2, TOP - 330 - (im.height - cta_img.height) // 2))
            frame = frame.convert("RGB")
            k = active_step(t)
            if k != prev_k:
                k_change, last_k, prev_k = t, prev_k, k
            pimg = posters[k]
            if t - k_change < 0.25 and fi > 0:
                pimg = Image.blend(posters[last_k], posters[k], (t - k_change) / 0.25)
            frame.paste(pimg, (0, TOP))
            ImageDraw.Draw(frame).rectangle([0, TOP - 3, W, TOP + 3], fill=ORANGE)
            enc.stdin.write(frame.tobytes())
        enc.stdin.close()
        enc.wait()
        dec.stdout.close()
        dec.wait()
        if enc.returncode:
            sys.exit("encode failed")

    # check frames: hook, every card middle, every shot middle, CTA
    marks = [("hook", 1.0)]
    for i, b in enumerate(brolls):
        marks.append((f"card{i + 1}", (b[0] + b[1]) / 2 + 0.3))
    for t in timings:
        marks.append((f"shot{t['shot']}", (t["speech"][0] + t["speech"][1]) / 2))
    if cta_t:
        marks.append(("cta", min(total - 0.3, cta_t + 1.0)))
    for name, tt in marks:
        run(["-ss", f"{tt:.2f}", "-i", out, "-frames:v", "1", "-q:v", "3", os.path.join(check, f"{name}.jpg")])
    with open(os.path.join(day, "timings.json"), "w") as f:
        json.dump(timings, f, indent=1)
    print(f"built {out}: {total:.1f}s, {n} shots, {len(caps)} caption pieces, {len(brolls)} cards")
    for t in timings:
        print(f"  shot{t['shot']}: speech {t['speech'][1] - t['speech'][0]:.1f}s of {t['len']:.1f}s")


FLOW_ASK = ("Please generate {n} separate videos, one per prompt below. For each: Veo 3.1 Lite, 9:16 vertical, "
            "8 seconds, with audio, use the attached image as the START FRAME (image-to-video), and use the prompt "
            "text exactly as written, do not rewrite or translate the Hindi line. ")


def cmd_prompts(day, template):
    """script.json + a template with {line} -> prompts/shotN.txt and prompts/flow_message.txt (one line for the
    Flow agent chat; pressing Enter there submits, so it must not contain newlines)."""
    s = load(day)
    with open(template, encoding="utf-8") as f:
        tpl = f.read()
    os.makedirs(os.path.join(day, "prompts"), exist_ok=True)
    parts = []
    for i, shot in enumerate(s["shots"], start=1):
        line = reel.spoken(shot.get("dialogue_hi") or shot["dialogue"])
        if '"' in line:
            sys.exit(f"shot{i}: no double quotes inside dialogue")
        p = tpl.replace("{line}", line)
        with open(os.path.join(day, "prompts", f"shot{i}.txt"), "w", encoding="utf-8") as f:
            f.write(p)
        parts.append(f"VIDEO {i} PROMPT: " + " ".join(p.split()))
    msg = FLOW_ASK.format(n=len(parts)) + " ".join(parts)
    with open(os.path.join(day, "prompts", "flow_message.txt"), "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(f"wrote {len(parts)} prompts + flow_message.txt ({len(msg)} chars)")


if __name__ == "__main__":
    if sys.argv[1] == "prompts":
        cmd_prompts(sys.argv[2].rstrip("/\\"), sys.argv[3])
    else:
        {"build": cmd_build}[sys.argv[1]](sys.argv[2].rstrip("/\\"))
