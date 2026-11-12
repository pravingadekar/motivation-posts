"""Drawing kit for Golu Bandar Kids cartoons (skia-python, soft 3D-look shading).

All characters are drawn in local coordinates with the origin at the feet (ground contact).
"""
import math
import random

import skia

W, H = 1920, 1080
GROUND = 900


# ---------------------------------------------------------------- helpers
def rgb(h, a=255):
    h = h.lstrip("#")
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, f):
    """Mix two '#rrggbb' strings."""
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(round(x + (y - x) * f)):02x}" for x, y in zip(a, b))


def light(c, f=0.35):
    return mix(c, "#ffffff", f)


def dark(c, f=0.3):
    return mix(c, "#000000", f)


def paint(color="#000000", alpha=255, stroke=None, cap=True, blur=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor(rgb(color, alpha) if isinstance(color, str) else color)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def shade_paint(cx, cy, r, base, alpha=255, hi=0.45, lo=0.28):
    """Radial gradient with the light from the top-left: gives a soft 3D ball look."""
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(
        skia.Point(cx - 0.35 * r, cy - 0.45 * r), 1.55 * r,
        [rgb(light(base, hi), alpha), rgb(base, alpha), rgb(dark(base, lo), alpha)], [0.0, 0.45, 1.0]))
    return p


def ball(c, x, y, r, base, alpha=255, hi=0.45, lo=0.28):
    c.drawCircle(x, y, r, shade_paint(x, y, r, base, alpha, hi, lo))


def oval(c, x, y, rx, ry, base, alpha=255, shaded=True, hi=0.45, lo=0.28):
    rect = skia.Rect.MakeLTRB(x - rx, y - ry, x + rx, y + ry)
    p = shade_paint(x, y, max(rx, ry), base, alpha, hi, lo) if shaded else paint(base, alpha)
    c.drawOval(rect, p)


def rrect(c, l, t, r, b, rad, base, alpha=255, shaded=True):
    p = shade_paint((l + r) / 2, (t + b) / 2, max(r - l, b - t) / 2, base, alpha) if shaded else paint(base, alpha)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t, r, b), rad, rad), p)


def limb(c, pts, width, color):
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    c.drawPath(path, paint(dark(color, 0.12), stroke=width + 3))
    c.drawPath(path, paint(color, stroke=width))
    # soft highlight stripe
    hp = skia.Path()
    hp.moveTo(pts[0][0] - width * 0.18, pts[0][1] - width * 0.1)
    for p in pts[1:]:
        hp.lineTo(p[0] - width * 0.18, p[1] - width * 0.1)
    c.drawPath(hp, paint(light(color, 0.35), alpha=90, stroke=width * 0.3))


def shadow(c, x, y, rx, alpha=70):
    c.drawOval(skia.Rect.MakeLTRB(x - rx, y - rx * 0.16, x + rx, y + rx * 0.16), paint("#1f3d12", alpha, blur=8))


def arm_points(sx, sy, side, a1, a2, l1, l2):
    """side=+1 right (screen), -1 left. Angles in degrees from straight down, positive = outward/up."""
    d1 = math.radians(a1)
    ex, ey = sx + side * l1 * math.sin(d1), sy + l1 * math.cos(d1)
    d2 = math.radians(a1 + a2)
    hx, hy = ex + side * l2 * math.sin(d2), ey + l2 * math.cos(d2)
    return (sx, sy), (ex, ey), (hx, hy)


# ---------------------------------------------------------------- props
def mango(c, x, y, s=1.0, rot=0.0, ripe=1.0, alpha=255, glow=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    if glow > 0:
        c.drawCircle(0, 0, 40, paint("#fff3a0", int(120 * glow), blur=16))
    base = mix("#7fbf3a", "#ffb21e", ripe)
    rect = skia.Rect.MakeLTRB(-20, -26, 20, 26)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(-8, -10), 40,
                                               [rgb(light(base, 0.5), alpha), rgb(base, alpha),
                                                rgb(mix(base, "#e2571b" if ripe > 0.5 else "#4f8a1e", 0.55), alpha)],
                                               [0, 0.45, 1]))
    path = skia.Path()
    path.moveTo(0, -26)
    path.cubicTo(18, -26, 24, -2, 18, 14)
    path.cubicTo(12, 30, -14, 30, -19, 12)
    path.cubicTo(-24, -6, -16, -26, 0, -26)
    c.drawPath(path, p)
    c.drawPath(path, paint(dark(base, 0.35), alpha, stroke=1.5))
    c.drawCircle(-7, -12, 4, paint("#ffffff", int(alpha * 0.55)))
    # stem + leaf
    c.drawLine(0, -26, 2, -34, paint("#6b4423", alpha, stroke=3))
    leaf = skia.Path()
    leaf.moveTo(2, -32)
    leaf.quadTo(16, -44, 26, -34)
    leaf.quadTo(14, -26, 2, -32)
    c.drawPath(leaf, paint("#3f9b35", alpha))
    c.restore()


def sparkle(c, x, y, r, alpha=255, color="#fff7b0"):
    path = skia.Path()
    path.moveTo(x, y - r)
    path.quadTo(x, y, x + r, y)
    path.quadTo(x, y, x, y + r)
    path.quadTo(x, y, x - r, y)
    path.quadTo(x, y, x, y - r)
    c.drawCircle(x, y, r * 0.6, paint(color, int(alpha * 0.35), blur=r * 0.4))
    c.drawPath(path, paint(color, alpha))


def heart(c, x, y, r, alpha=255, color="#ff5d8f"):
    path = skia.Path()
    path.moveTo(x, y + r)
    path.cubicTo(x - 1.6 * r, y - 0.2 * r, x - 0.8 * r, y - 1.4 * r, x, y - 0.5 * r)
    path.cubicTo(x + 0.8 * r, y - 1.4 * r, x + 1.6 * r, y - 0.2 * r, x, y + r)
    c.drawPath(path, paint(color, alpha))
    c.drawCircle(x - 0.45 * r, y - 0.55 * r, r * 0.18, paint("#ffffff", int(alpha * 0.6)))


def note(c, x, y, s, alpha=255, color="#8a4dff"):
    c.drawOval(skia.Rect.MakeXYWH(x - 13 * s, y - 9 * s, 24 * s, 18 * s), paint(color, alpha))
    c.drawLine(x + 9 * s, y - 2 * s, x + 9 * s, y - 46 * s, paint(color, alpha, stroke=5 * s))
    c.drawLine(x + 9 * s, y - 46 * s, x + 26 * s, y - 34 * s, paint(color, alpha, stroke=5 * s))


def drop(c, x, y, s, color="#5ab8ff", alpha=255):
    path = skia.Path()
    path.moveTo(x, y - 14 * s)
    path.cubicTo(x + 10 * s, y, x + 9 * s, y + 9 * s, x, y + 9 * s)
    path.cubicTo(x - 9 * s, y + 9 * s, x - 10 * s, y, x, y - 14 * s)
    c.drawPath(path, paint(color, alpha))
    c.drawCircle(x - 3 * s, y + 2 * s, 2.2 * s, paint("#ffffff", int(alpha * 0.7)))


def puff(c, x, y, age, alpha=255):
    """Dust cloud, age 0..1."""
    if age < 0 or age > 1:
        return
    a = int(alpha * (1 - age))
    rnd = random.Random(int(x * 7 + y))
    for i in range(7):
        ang = rnd.uniform(math.pi, 2 * math.pi) if i < 5 else rnd.uniform(0, math.pi)
        d = 40 + 90 * age
        r = 26 + 22 * age + rnd.uniform(-6, 6)
        ball(c, x + math.cos(ang) * d, y + math.sin(ang) * d * 0.35 - 10, r, "#e8dcc4", a, hi=0.5, lo=0.15)


def dizzy_stars(c, x, y, t, alpha=255):
    for i in range(3):
        a = t * 4 + i * 2 * math.pi / 3
        sparkle(c, x + math.cos(a) * 70, y + math.sin(a) * 18, 16, alpha, "#ffd84a")


class Fonts:
    _cache = {}

    @classmethod
    def get(cls, size):
        if size not in cls._cache:
            import os
            here = os.path.dirname(os.path.abspath(__file__))
            tf = skia.Typeface.MakeFromFile(os.path.join(here, "..", "brand", "fonts", "Poppins-ExtraBold.ttf"))
            cls._cache[size] = skia.Font(tf, size)
        return cls._cache[size]


def comic_word(c, text, x, y, size, age, fill="#ffdd33", outline="#d6331d", rot=-8):
    """Pop-in sound word (Latin letters only). age in seconds since start; visible ~1.2 s."""
    if age < 0 or age > 1.3:
        return
    pop = min(1.0, age / 0.18)
    sc = 0.4 + 0.75 * pop - 0.15 * max(0, min(1, (age - 0.18) / 0.2))
    a = 255 if age < 1.0 else int(255 * (1.3 - age) / 0.3)
    font = Fonts.get(size)
    w = font.measureText(text)
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    c.drawString(text, -w / 2 + 6, size * 0.35 + 6, font, paint("#5a1a0a", int(a * 0.5)))
    c.drawString(text, -w / 2, size * 0.35, font, paint(outline, a, stroke=size * 0.16))
    c.drawString(text, -w / 2, size * 0.35, font, paint(fill, a))
    c.restore()


# ---------------------------------------------------------------- monkey (Golu / Pinky)
GOLU = dict(fur="#9a5b2e", face="#f2c9a0", shirt="#e53935", shorts="#2f6fd6", girl=False)
PINKY = dict(fur="#b9784a", face="#f7d4b4", shirt="#ff6fae", shorts="#ff6fae", girl=True)


def eye(c, x, y, rx, ry, look, blink, expr, side):
    if expr == "sour" or expr == "squeeze":
        path = skia.Path()  # > <  shapes
        d = side
        path.moveTo(x + 14 * d, y - 12)
        path.lineTo(x - 10 * d, y)
        path.lineTo(x + 14 * d, y + 12)
        c.drawPath(path, paint("#3a2213", stroke=6))
        return
    if expr == "joy" or blink > 0.85:
        path = skia.Path()
        if expr == "joy":
            path.moveTo(x - rx, y + 4)
            path.quadTo(x, y - ry * 1.1, x + rx, y + 4)
        else:
            path.moveTo(x - rx, y)
            path.quadTo(x, y + ry * 0.5, x + rx, y)
        c.drawPath(path, paint("#3a2213", stroke=6))
        return
    ry2 = ry * (1 - blink)
    c.drawOval(skia.Rect.MakeLTRB(x - rx - 2, y - ry2 - 2, x + rx + 2, y + ry2 + 2), paint("#5b3317"))
    c.drawOval(skia.Rect.MakeLTRB(x - rx, y - ry2, x + rx, y + ry2), paint("#ffffff"))
    c.save()
    c.clipRRect(skia.RRect.MakeOval(skia.Rect.MakeLTRB(x - rx, y - ry2, x + rx, y + ry2)), doAntiAlias=True)
    ix, iy = x + look[0] * rx * 0.35, y + 3 + look[1] * ry * 0.25
    ir = rx * 0.68
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(ix, iy + ir * 0.4), ir,
                                               [rgb("#a8642b"), rgb("#5a2e10"), rgb("#2a1205")], [0, 0.6, 1]))
    c.drawCircle(ix, iy, ir, p)
    c.drawCircle(ix, iy, ir * 0.5, paint("#120600"))
    c.drawCircle(ix - ir * 0.38, iy - ir * 0.42, ir * 0.36, paint("#ffffff"))
    c.drawCircle(ix + ir * 0.35, iy + ir * 0.3, ir * 0.16, paint("#ffffff", 220))
    c.restore()
    if expr == "sad":
        # sad brows drawn by caller; small lid line
        pass


def mouth(c, x, y, m, expr, w=36):
    if expr in ("sad", "worried") and m < 0.15:
        path = skia.Path()
        path.moveTo(x - w * 0.5, y + 8)
        path.quadTo(x, y - 10, x + w * 0.5, y + 8)
        c.drawPath(path, paint("#5a2210", stroke=5))
        return
    if expr == "sour" and m < 0.15:
        path = skia.Path()
        path.moveTo(x - w * 0.6, y)
        for i in range(1, 7):
            path.lineTo(x - w * 0.6 + i * w * 1.2 / 6, y + (7 if i % 2 else -7))
        c.drawPath(path, paint("#5a2210", stroke=5))
        return
    if m < 0.08 and expr not in ("joy", "surprised"):
        path = skia.Path()
        path.moveTo(x - w * 0.55, y - 4)
        path.quadTo(x, y + 18, x + w * 0.55, y - 4)
        c.drawPath(path, paint("#5a2210", stroke=5))
        return
    if expr == "surprised":
        m = max(m, 0.55)
        hh = 10 + 26 * m
        c.drawOval(skia.Rect.MakeLTRB(x - 14 - 4 * m, y - hh / 2, x + 14 + 4 * m, y + hh / 2), paint("#6b1a14"))
        return
    if expr == "joy":
        m = max(m, 0.45)
    hh = 8 + 30 * m
    path = skia.Path()
    path.moveTo(x - w * 0.6, y - 6)
    path.quadTo(x, y - 2 + 4 * m, x + w * 0.6, y - 6)
    path.cubicTo(x + w * 0.5, y + hh, x - w * 0.5, y + hh, x - w * 0.6, y - 6)
    c.drawPath(path, paint("#7a1c18"))
    c.save()
    c.clipPath(path, doAntiAlias=True)
    c.drawOval(skia.Rect.MakeLTRB(x - w * 0.35, y + hh * 0.35, x + w * 0.35, y + hh * 1.2), paint("#ff7b86"))
    c.drawRect(skia.Rect.MakeLTRB(x - w * 0.4, y - 10, x + w * 0.4, y - 1 + 2 * m), paint("#ffffff"))
    c.restore()


def monkey(c, st, look=None):
    """st: dict(x, y, s, cfg, arms=(la,le,ra,re), mouth, expr, blink, look, tilt, sit, hold, flip, squash)."""
    cfg = st.get("cfg", GOLU)
    fur, face = cfg["fur"], cfg["face"]
    x, y, s = st["x"], st["y"], st.get("s", 1.0)
    shadow(c, x, y + 2, 85 * s, 60)
    c.save()
    c.translate(x, y)
    sq = st.get("squash", 0.0)
    c.scale(s * (1 + sq * 0.15) * (-1 if st.get("flip") else 1), s * (1 - sq * 0.15))
    c.rotate(st.get("tilt", 0))
    sit = st.get("sit", 0)
    t = st.get("t", 0)
    breathe = 1 + 0.012 * math.sin(t * 2.6)
    la, le, ra, re = st.get("arms", (12, 10, 12, 10))
    # tail
    tail = skia.Path()
    wag = math.sin(t * 2.0) * 12
    tail.moveTo(30, -95 + sit * 50)
    tail.cubicTo(110, -70 + sit * 50, 140 + wag, -170, 100 + wag, -200)
    tail.cubicTo(80 + wag, -215, 62 + wag, -195, 78 + wag, -182)
    c.drawPath(tail, paint(dark(fur, 0.15), stroke=17))
    c.drawPath(tail, paint(fur, stroke=13))
    # legs
    if sit:
        oval(c, -38, -22, 36, 22, fur)
        oval(c, 38, -22, 36, 22, fur)
        oval(c, -62, -16, 22, 15, face)
        oval(c, 62, -16, 22, 15, face)
        dy = 55
    else:
        step = st.get("step", 0.0)
        lk = 14 * math.sin(step)
        limb(c, [(-22, -82), (-26 - lk, -40), (-30 - lk, -14)], 22, fur)
        limb(c, [(22, -82), (26 + lk, -40), (30 + lk, -14)], 22, fur)
        oval(c, -34 - lk, -10, 24, 13, face)
        oval(c, 34 + lk, -10, 24, 13, face)
        dy = 0
    c.translate(0, dy)
    # body
    if cfg["girl"]:
        dress = skia.Path()
        dress.moveTo(-40, -200)
        dress.lineTo(40, -200)
        dress.lineTo(66, -88)
        dress.quadTo(0, -74, -66, -88)
        dress.close()
        p = shade_paint(0, -140, 90, cfg["shirt"])
        c.drawPath(dress, p)
        for i in range(-2, 3):
            c.drawCircle(i * 22, -100, 5, paint("#ffffff", 200))
    else:
        rrect(c, -46, -122, 46, -72, 22, cfg["shorts"])
        c.save()
        c.scale(1, breathe)
        rrect(c, -54, -205, 54, -98, 44, cfg["shirt"])
        c.restore()
        star = skia.Path()  # little yellow star on the shirt
        for k in range(10):
            r = 20 if k % 2 == 0 else 9
            a = -math.pi / 2 + k * math.pi / 5
            (star.moveTo if k == 0 else star.lineTo)(r * math.cos(a), -152 + r * math.sin(a))
        star.close()
        c.drawPath(star, paint("#ffd54a"))
    # belly patch
    oval(c, 0, -150, 30, 36, face, 90, shaded=False)
    # arms
    sh = -182
    lpts = arm_points(-46, sh, -1, la, le, 52, 48)
    rpts = arm_points(46, sh, 1, ra, re, 52, 48)
    hold_back = []
    for pts in (lpts, rpts):
        limb(c, list(pts), 19, fur)
        ball(c, pts[2][0], pts[2][1], 15, face)
    if st.get("hold"):
        hx, hy = rpts[2]
        mango(c, hx + 4, hy - 14, 1.0, 10, st.get("hold_ripe", 1.0), glow=st.get("hold_glow", 0))
        if st.get("bitten"):
            c.drawCircle(hx + 20, hy - 30, 11, paint("#fff3c4"))
    if st.get("hold_left"):
        hx, hy = lpts[2]
        mango(c, hx - 4, hy - 14, 1.0, -10, 1.0)
    # head
    hb = st.get("headbob", 0)
    c.translate(0, hb)
    turn = st.get("turn", 0.0)
    hx0 = turn * 10
    # ears
    for sd in (-1, 1):
        ball(c, sd * 80 + hx0 * 0.3, -272, 27, fur)
        ball(c, sd * 80 + hx0 * 0.3, -272, 16, face, hi=0.3, lo=0.15)
    ball(c, hx0 * 0.3, -268, 80, fur)
    # tuft
    tuft = skia.Path()
    tuft.moveTo(-14, -342)
    tuft.quadTo(-4, -372, 8, -346)
    tuft.quadTo(18, -366, 22, -340)
    c.drawPath(tuft, paint(fur))
    # face mask
    fx = hx0
    p = shade_paint(fx, -262, 70, face, hi=0.35, lo=0.15)
    mask = skia.Path()
    mask.addCircle(fx - 27, -284, 33)
    mask.addCircle(fx + 27, -284, 33)
    mask.addOval(skia.Rect.MakeLTRB(fx - 56, -278, fx + 56, -200))
    mask.setFillType(skia.PathFillType.kWinding)
    c.drawPath(mask, p)
    expr = st.get("expr", "happy")
    lk = st.get("look", (0, 0))
    blink = st.get("blink", 0)
    eye(c, fx - 26, -286, 19, 24, lk, blink, expr, -1)
    eye(c, fx + 26, -286, 19, 24, lk, blink, expr, 1)
    # brows
    bp = paint(dark(fur, 0.35), stroke=6)
    if expr in ("sad", "worried"):
        c.drawLine(fx - 40, -316, fx - 14, -324, bp)
        c.drawLine(fx + 40, -316, fx + 14, -324, bp)
    elif expr == "sneaky":
        c.drawLine(fx - 42, -322, fx - 12, -314, bp)
        c.drawLine(fx + 42, -322, fx + 12, -314, bp)
    elif expr == "surprised":
        c.drawLine(fx - 40, -330, fx - 14, -334, bp)
        c.drawLine(fx + 40, -330, fx + 14, -334, bp)
    else:
        path = skia.Path()
        path.moveTo(fx - 40, -318)
        path.quadTo(fx - 27, -328, fx - 14, -320)
        path.moveTo(fx + 40, -318)
        path.quadTo(fx + 27, -328, fx + 14, -320)
        c.drawPath(path, bp)
    if expr == "sneaky":  # half-lids
        for sd in (-1, 1):
            ex = fx + sd * 26
            c.save()
            c.clipRRect(skia.RRect.MakeOval(skia.Rect.MakeLTRB(ex - 22, -312, ex + 22, -260)), doAntiAlias=True)
            c.drawRect(skia.Rect.MakeLTRB(ex - 23, -313, ex + 23, -288), paint(dark(face, 0.08)))
            c.restore()
            c.drawLine(ex - 19, -288, ex + 19, -288, paint("#3a2213", stroke=4))
    # nose
    c.drawCircle(fx - 7, -252, 4, paint("#5a3018"))
    c.drawCircle(fx + 7, -252, 4, paint("#5a3018"))
    # cheeks
    c.drawCircle(fx - 50, -240, 13, paint("#ff8fa0", 120, blur=3))
    c.drawCircle(fx + 50, -240, 13, paint("#ff8fa0", 120, blur=3))
    mouth(c, fx, -230, st.get("mouth", 0), expr)
    if expr == "sour":
        c.drawCircle(fx, -270, 70, paint("#9be15d", 50, blur=10))
    if cfg["girl"]:
        # bow
        for sd in (-1, 1):
            bow = skia.Path()
            bow.moveTo(40, -338)
            bow.lineTo(40 + sd * 34, -362)
            bow.lineTo(40 + sd * 30, -316)
            bow.close()
            c.drawPath(bow, shade_paint(40 + sd * 20, -340, 30, "#ff3d8b"))
        ball(c, 40, -338, 11, "#ff3d8b")
        # lashes
        for sd in (-1, 1):
            c.drawLine(fx + sd * 40, -300, fx + sd * 48, -308, paint("#3a2213", stroke=4))
    c.restore()
    return lpts, rpts


# ---------------------------------------------------------------- Haathi Dada
ELE = "#9aa6b8"


def elephant(c, st):
    x, y, s, t = st["x"], st["y"], st.get("s", 1.0), st.get("t", 0)
    shadow(c, x, y + 2, 170 * s, 70)
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    sit = st.get("sit", 0)
    step = st.get("step", 0)
    # back legs
    for lx in (-118, 82):
        rrect(c, lx, -120 + sit * 40, lx + 46, -2, 22, dark(ELE, 0.12))
    # body
    oval(c, 0, -175 + sit * 40, 150, 118, ELE)
    # tail
    c.drawLine(-145, -190 + sit * 40, -175, -130 + sit * 40 + 6 * math.sin(t * 3), paint(dark(ELE, 0.2), stroke=8))
    # front legs
    for i, lx in enumerate((-75, 30)):
        lift = max(0, 14 * math.sin(step + i * math.pi))
        if sit:
            oval(c, lx + 22, -30, 40, 28, ELE)
            oval(c, lx + 22, -22, 30, 12, "#e9e3d6", shaded=False)
        else:
            rrect(c, lx, -125, lx + 48, -2 - lift, 22, ELE)
            for k in range(3):
                c.drawCircle(lx + 10 + k * 14, -8 - lift, 6, paint("#efe8db"))
    # scarf
    scarf = skia.Path()
    scarf.moveTo(-90, -258 + sit * 40)
    scarf.quadTo(0, -205 + sit * 40, 90, -258 + sit * 40)
    c.drawPath(scarf, paint("#ff9f1c", stroke=26))
    c.drawPath(scarf, paint("#ffd166", stroke=6))
    c.translate(0, sit * 40 + st.get("headbob", 0))
    # ears
    flap = math.sin(t * 1.7) * 4
    for sd in (-1, 1):
        c.save()
        c.translate(sd * 110, -320)
        c.rotate(sd * flap)
        oval(c, sd * 20, 0, 78, 96, ELE)
        oval(c, sd * 24, 4, 52, 70, "#e9a6b4", hi=0.3, lo=0.2)
        c.restore()
    # head
    ball(c, 0, -320, 102, ELE)
    # cheeks
    c.drawCircle(-58, -282, 16, paint("#ff8fa0", 110, blur=4))
    c.drawCircle(58, -282, 16, paint("#ff8fa0", 110, blur=4))
    # mouth (behind trunk)
    m = st.get("mouth", 0)
    expr = st.get("expr", "happy")
    if m > 0.08:
        hh = 10 + 26 * m
        c.drawOval(skia.Rect.MakeLTRB(-40, -262, 40, -262 + hh * 1.4), paint("#7a1c18"))
        c.drawOval(skia.Rect.MakeLTRB(-22, -262 + hh * 0.6, 22, -262 + hh * 1.35), paint("#ff7b86"))
    else:
        path = skia.Path()
        if expr in ("tired", "sad"):
            path.moveTo(-44, -248)
            path.quadTo(0, -262, 44, -248)
        else:
            path.moveTo(-46, -262)
            path.quadTo(0, -232, 46, -262)
        c.drawPath(path, paint("#4a3a3a", stroke=5))
    # trunk
    curl = st.get("trunk", 0.0)  # 0 down, 1 raised curl
    sway = math.sin(t * 1.3) * 10
    tr = skia.Path()
    tr.moveTo(0, -300)
    ex, ey = 20 + sway + 60 * curl, -150 - 140 * curl
    tr.cubicTo(-10, -240, -5 + sway, -190 + -40 * curl, ex, ey)
    c.drawPath(tr, paint(dark(ELE, 0.12), stroke=50))
    c.drawPath(tr, paint(ELE, stroke=44))
    hl = skia.Path()
    hl.moveTo(-12, -295)
    hl.cubicTo(-20, -240, -16 + sway, -190 - 40 * curl, ex - 12, ey - 4)
    c.drawPath(hl, paint(light(ELE, 0.4), 120, stroke=8))
    for k in range(4):
        yy = -270 + k * 26
        c.drawLine(-14, yy, 14, yy + 2, paint(dark(ELE, 0.25), 140, stroke=3))
    c.drawCircle(ex, ey, 22, paint(dark(ELE, 0.15)))
    c.drawCircle(ex, ey, 17, paint(ELE))
    if st.get("trunk_mango"):
        mango(c, ex + 14, ey - 30, 1.0, 20)
    # eyes
    blink = st.get("blink", 0)
    for sd in (-1, 1):
        ex2 = sd * 40
        if blink > 0.85 or expr == "joy":
            path = skia.Path()
            path.moveTo(ex2 - 15, -338)
            path.quadTo(ex2, -352 if expr == "joy" else -328, ex2 + 15, -338)
            c.drawPath(path, paint("#2b2b2b", stroke=5))
        else:
            ry = 18 * (1 - blink) * (0.7 if expr == "tired" else 1)
            c.drawOval(skia.Rect.MakeLTRB(ex2 - 14, -340 - ry, ex2 + 14, -340 + ry), paint("#ffffff"))
            c.drawCircle(ex2 + 2, -338, 9, paint("#2b1a10"))
            c.drawCircle(ex2 - 1, -342, 3.5, paint("#ffffff"))
        # spectacles
        c.drawCircle(ex2, -340, 27, paint("#6b3f1f", stroke=5))
        c.drawCircle(ex2, -340, 25, paint("#ffffff", 30))
        # bushy brows
        c.drawLine(ex2 - 22, -378 + (6 if expr in ("tired", "sad") and sd * 1 else 0), ex2 + 22,
                   -378 - (6 if expr in ("tired", "sad") else 0) * sd, paint("#f2f2f2", stroke=9))
    c.drawLine(-13, -342, 13, -342, paint("#6b3f1f", stroke=5))
    c.restore()


# ---------------------------------------------------------------- magic mango tree
TREE_MANGOES = [(-230, -520), (-150, -430), (-60, -610), (40, -470), (130, -580), (210, -450), (260, -560),
                (-260, -630), (-20, -720), (110, -700), (-120, -540), (190, -660), (0, -560), (-200, -730)]
CANOPY = [(-250, -560, 150), (250, -560, 150), (0, -700, 170), (-140, -700, 150), (150, -700, 150),
          (-120, -470, 150), (120, -470, 150), (0, -520, 160), (-300, -480, 110), (300, -480, 110)]


def tree(c, st):
    x, y, s, t = st["x"], st["y"], st.get("s", 1.0), st.get("t", 0)
    glow = st.get("glow", 1.0)
    sad = st.get("sad", 0.0)
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    shadow(c, 0, 0, 330, 80)
    if glow > 0:
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeRadial(skia.Point(0, -520), 520,
                                                   [rgb("#fff6a8", int(200 * glow)), rgb("#ffe066", int(90 * glow)),
                                                    rgb("#ffe066", 0)], [0, 0.5, 1]))
        c.drawCircle(0, -520, 520, p)
    # trunk
    bark = mix("#8a5a33", "#6e6259", sad * 0.6)
    tp = skia.Path()
    tp.moveTo(-95, 0)
    tp.cubicTo(-70, -120, -60, -260, -55, -380)
    tp.lineTo(55, -380)
    tp.cubicTo(60, -260, 70, -120, 95, 0)
    tp.quadTo(0, 18, -95, 0)
    c.drawPath(tp, shade_paint(0, -190, 200, bark))
    # roots
    for sd in (-1, 1):
        rp = skia.Path()
        rp.moveTo(sd * 70, -40)
        rp.quadTo(sd * 120, -5, sd * 150, 4)
        c.drawPath(rp, paint(dark(bark, 0.1), stroke=26))
    # branches
    for sd in (-1, 1):
        bp = skia.Path()
        bp.moveTo(sd * 30, -360)
        bp.quadTo(sd * 120, -430, sd * 210, -470)
        c.drawPath(bp, paint(dark(bark, 0.05), stroke=34))
    # bark lines
    for k in range(5):
        c.drawLine(-30 + k * 15, -60 - k * 20, -26 + k * 15, -110 - k * 20, paint(dark(bark, 0.25), 120, stroke=4))
    # canopy
    leaf = mix(mix("#3fae3a", "#6fcf4b", glow * 0.5), "#6f7d4a", sad * 0.7)
    droop = sad * 25
    for i, (cx, cy, r) in enumerate(CANOPY):
        ball(c, cx, cy + droop, r * 1.04, dark(leaf, 0.25))
    for i, (cx, cy, r) in enumerate(CANOPY):
        ball(c, cx, cy + droop - 6, r * 0.92, leaf, hi=0.4, lo=0.18)
    # leaf texture
    rnd = random.Random(5)
    for k in range(40):
        lx, ly = rnd.uniform(-330, 330), rnd.uniform(-820, -400) + droop
        c.drawOval(skia.Rect.MakeXYWH(lx, ly, 18, 9), paint(light(leaf, 0.25), 120))
    # mangoes
    ripe = st.get("ripe", 1.0)
    hidden = st.get("picked", 0)
    for k, (mx, my) in enumerate(TREE_MANGOES):
        if k < hidden:
            continue
        sw = math.sin(t * 2 + k) * 4
        mango(c, mx, my + droop, 1.15, sw, ripe, glow=glow * (0.5 + 0.5 * math.sin(t * 3 + k)))
    # face on trunk
    fy = -230
    blink = st.get("blink", 0)
    awake = st.get("awake", 1.0)
    for sd in (-1, 1):
        ex = sd * 32
        if awake < 0.5 or blink > 0.85:
            path = skia.Path()
            path.moveTo(ex - 16, fy)
            path.quadTo(ex, fy + 10, ex + 16, fy)
            c.drawPath(path, paint("#3a2010", stroke=6))
        else:
            ry = 22 * (1 - blink) * min(1, (awake - 0.5) * 2)
            c.drawOval(skia.Rect.MakeLTRB(ex - 17, fy - ry, ex + 17, fy + ry), paint("#fffaf0"))
            c.drawCircle(ex, fy + 3, 10, paint("#3a2010"))
            c.drawCircle(ex - 3, fy - 1, 4, paint("#ffffff"))
        if sad > 0.3:
            c.drawLine(ex - 18 * sd, fy - 34, ex + 14 * sd, fy - 26, paint("#3a2010", stroke=5))
    m = st.get("mouth", 0)
    if m > 0.08:
        hh = 8 + 28 * m
        c.drawOval(skia.Rect.MakeLTRB(-26, fy + 42, 26, fy + 42 + hh), paint("#5a1d12"))
    else:
        path = skia.Path()
        if sad > 0.3:
            path.moveTo(-28, fy + 58)
            path.quadTo(0, fy + 40, 28, fy + 58)
        else:
            path.moveTo(-30, fy + 44)
            path.quadTo(0, fy + 66, 30, fy + 44)
        c.drawPath(path, paint("#3a2010", stroke=6))
    c.drawCircle(-50, fy + 30, 12, paint("#ff9f8a", 90, blur=3))
    c.drawCircle(50, fy + 30, 12, paint("#ff9f8a", 90, blur=3))
    # sparkles
    if glow > 0.05:
        rnd = random.Random(9)
        for k in range(14):
            px, py = rnd.uniform(-380, 380), rnd.uniform(-850, -300)
            ph = rnd.uniform(0, 6.28)
            a = 0.5 + 0.5 * math.sin(t * 3 + ph)
            sparkle(c, px, py - (t * 20 + ph * 30) % 60, 10 + 8 * a, int(255 * glow * a))
    c.restore()


# ---------------------------------------------------------------- background
def background(c, t, cam, sunset=0.0, heat=0.0):
    """Sky (fixed) + parallax layers. cam = (cx, cy, zoom)."""
    top = mix("#5bbcff", "#ff8a5c", sunset)
    bot = mix("#d6f4ff", "#ffd59a", sunset)
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)], [rgb(top), rgb(bot)]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    # sun
    sx, sy = (300, 170) if sunset < 0.5 else (960, 560)
    sun = mix("#fff4a8", "#ffb347", sunset)
    c.drawCircle(sx, sy, 190 + 20 * heat, paint(sun, 80 + int(60 * heat), blur=60))
    c.drawCircle(sx, sy, 85, paint(sun))
    # clouds
    for k, (cx0, cy, sc) in enumerate([(200, 150, 1.0), (900, 110, 1.3), (1500, 200, 0.9), (2100, 130, 1.1)]):
        cx = (cx0 + t * (12 + 4 * k)) % 2400 - 250
        for dx, dy, r in [(-60, 10, 45), (0, -15, 60), (60, 8, 48), (110, 18, 34), (-110, 20, 32)]:
            ball(c, cx + dx * sc, cy + dy * sc, r * sc, mix("#ffffff", "#ffd1b3", sunset), 235, hi=0.1, lo=0.08)

    def layer(depth, fn):
        c.save()
        cx, cy, z = cam
        f = depth
        zz = 1 + (z - 1) * f
        c.translate(W / 2, H / 2)
        c.scale(zz, zz)
        c.translate(-(W / 2 + (cx - W / 2) * f), -(H / 2 + (cy - H / 2) * f))
        fn()
        c.restore()

    def hills():
        for k, (hx, r, col) in enumerate([(100, 520, "#8fd4a0"), (800, 600, "#7cc98f"), (1600, 560, "#8fd4a0"),
                                           (2300, 600, "#7cc98f")]):
            oval(c, hx, 900, r, 330, mix(col, "#c98a6b", sunset * 0.4), shaded=True, hi=0.2, lo=0.1)

    def far_trees():
        rnd = random.Random(3)
        for k in range(14):
            tx = -300 + k * 190 + rnd.uniform(-40, 40)
            th = rnd.uniform(200, 300)
            col = mix("#3b9a4c", "#7a6a50", sunset * 0.5)
            c.drawRect(skia.Rect.MakeLTRB(tx - 12, 860 - th * 0.5, tx + 12, 880), paint(mix("#7a5232", "#5a3a2a", sunset)))
            for dx, dy, r in [(-50, 0, 70), (50, 0, 70), (0, -50, 85)]:
                ball(c, tx + dx, 860 - th * 0.55 + dy, r, col, hi=0.3, lo=0.2)

    def ground():
        g = skia.Paint()
        g.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 840), skia.Point(0, 1300)],
                                                   [rgb(mix("#7fd35a", "#c5a560", sunset * 0.4)),
                                                    rgb(mix("#3f9a32", "#8a6a3a", sunset * 0.4))]))
        path = skia.Path()
        path.moveTo(-1200, 870)
        for k in range(0, 4400, 200):
            path.quadTo(-1200 + k + 100, 850 + 12 * math.sin(k), -1200 + k + 200, 870)
        path.lineTo(3200, 1800)
        path.lineTo(-1200, 1800)
        path.close()
        c.drawPath(path, g)
        rnd = random.Random(8)
        for k in range(70):
            gx, gy = rnd.uniform(-400, 2400), rnd.uniform(890, 1250)
            c.drawLine(gx, gy, gx + rnd.uniform(-6, 6), gy - 18, paint("#2f7d2a", 160, stroke=4))
        for k in range(16):
            fx, fy = rnd.uniform(-300, 2300), rnd.uniform(930, 1200)
            col = ["#ff5d8f", "#ffd23f", "#ffffff", "#b388ff"][k % 4]
            for a in range(5):
                ang = a * 2 * math.pi / 5 + t * 0.3
                c.drawCircle(fx + 9 * math.cos(ang), fy + 9 * math.sin(ang), 7, paint(col))
            c.drawCircle(fx, fy, 5, paint("#ff9f1c"))

    layer(0.25, hills)
    layer(0.5, far_trees)
    layer(1.0, ground)


def bushes(c, sunset=0.0):
    """Foreground bushes (drawn in camera space after characters)."""
    for bx, by, r in [(-120, 1130, 170), (2050, 1120, 170), (1760, 1190, 120)]:
        col = mix("#2e8b3e", "#6a5a3a", sunset * 0.4)
        for dx, dy, rr in [(-70, 10, 0.7), (60, 0, 0.8), (0, -40, 1.0)]:
            ball(c, bx + dx, by + dy, r * rr, col, hi=0.3, lo=0.2)
