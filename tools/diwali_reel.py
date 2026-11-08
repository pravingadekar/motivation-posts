"""Brand-free Diwali wishes reel: night sky, fireworks synced to the original tune, glowing diyas, Hindi wishes.

    python tools/diwali_reel.py OUT_DIR

Writes OUT_DIR/music.wav, OUT_DIR/cards/*.png (text rendered by Edge so Devanagari matras are shaped right),
OUT_DIR/reel.mp4 and OUT_DIR/check/*.jpg. No logo, handle or brand name anywhere.
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import diwali_music as M  # noqa: E402

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001
    FFMPEG = "ffmpeg"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
W, H, FPS = 1080, 1920, 30
B = M.BEAT

# (start beat, end beat, html). <g> = gold highlight.
CARDS = [
    (4, 12, '<div class="big">शुभ दीपावली</div><div class="en">Happy Diwali</div>'),
    (12, 20, '<div>दीयों की रोशनी से</div><div>जगमगाए आपका <g>घर-आँगन</g></div>'),
    (20, 28, '<div><g>खुशियाँ</g>, सेहत और समृद्धि</div><div>आपके हर दिन में रहें</div>'),
    (28, 36, '<div>आपको और पूरे परिवार को</div><div><g>दीपावली की हार्दिक</g></div><div><g>शुभकामनाएँ</g></div>'),
    (36, 46, '<div class="big2">Happy Diwali</div><div class="cta">ये शुभकामना अपनों को भेजें</div>'),
]
CSS = """<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&family=Yatra+One&family=Cinzel+Decorative:wght@700&display=block" rel="stylesheet">
<style>html,body{margin:0;width:1080px;height:1920px;background:transparent;overflow:hidden}
.box{position:absolute;left:50px;right:50px;top:620px;text-align:center;color:#fff6e0;
 font:400 86px/1.45 'Yatra One','Nirmala UI',serif;
 text-shadow:0 0 18px rgba(255,170,60,.85),0 0 4px rgba(0,0,0,.9),0 4px 14px rgba(0,0,0,.8)}
g{color:#ffd45c}
.big{font-size:150px;line-height:1.25;color:#ffd45c;
 text-shadow:0 0 30px rgba(255,150,30,.95),0 0 8px rgba(120,40,0,.9),0 6px 18px rgba(0,0,0,.8)}
.en{margin-top:18px;font:700 76px 'Cinzel Decorative',serif;color:#fff1cc;letter-spacing:2px}
.big2{font:700 112px/1.2 'Cinzel Decorative',serif;color:#ffd45c;margin-top:40px;
 text-shadow:0 0 30px rgba(255,150,30,.95),0 6px 18px rgba(0,0,0,.8)}
.cta{margin-top:70px;display:inline-block;font-size:60px;padding:14px 40px;border-radius:60px;
 background:rgba(60,10,30,.55);border:3px solid rgba(255,212,92,.8);text-shadow:0 0 8px rgba(0,0,0,.8)}
</style>"""


def render_cards(out):
    os.makedirs(out, exist_ok=True)
    paths = []
    for i, (_, _, html) in enumerate(CARDS, start=1):
        src = os.path.join(out, f"card{i}.html")
        png = os.path.join(out, f"card{i}.png")
        with open(src, "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><meta charset=utf-8>{CSS}<div class=box>{html}</div>")
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--default-background-color=00000000", "--virtual-time-budget=8000",
                        f"--window-size={W},{H}", f"--screenshot={os.path.abspath(png)}",
                        "file:///" + os.path.abspath(src).replace("\\", "/")],
                       check=True, capture_output=True, timeout=120)
        paths.append(png)
    return [Image.open(p).convert("RGBA").resize((W, H)) for p in paths]


def glow_sprite(r, sharp=2.2):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(x * x + y * y) / r
    return (np.exp(-(d * sharp) ** 2) + .9 * np.exp(-(d * sharp * 4) ** 2)).astype(np.float32)


SPR = {r: glow_sprite(r) for r in (5, 8, 12)}
BIG = glow_sprite(150, 2.0)


def splat(img, x, y, col, inten, spr):
    r = spr.shape[0] // 2
    xi, yi = int(x), int(y)
    x0, y0, x1, y1 = xi - r, yi - r, xi + r + 1, yi + r + 1
    if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = spr.shape[1] - max(0, x1 - W), spr.shape[0] - max(0, y1 - H)
    img[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] += spr[sy0:sy1, sx0:sx1, None] * (np.asarray(col) * inten)


PALETTES = [((1, .78, .3), (1, .5, .15)), ((1, .35, .45), (1, .8, .5)), ((.55, .85, 1), (1, 1, .8)),
            ((.75, 1, .45), (1, .85, .3)), ((1, .55, 1), (1, .9, .6)), ((1, .9, .55), (1, .6, .2))]


class Firework:
    def __init__(self, t0, rnd, big=False):
        self.t0 = t0
        self.cx = rnd.uniform(170, W - 170)
        self.cy = rnd.uniform(230, 620)
        self.rise = .55
        n = 190 if big else 120
        ang = rnd.uniform(0, 2 * np.pi, n)
        spd = rnd.uniform(.55, 1, n) * (500 if big else 380)
        self.vx, self.vy = np.cos(ang) * spd, np.sin(ang) * spd
        pal = PALETTES[rnd.integers(len(PALETTES))]
        mix = rnd.random(n) < .35
        self.col = np.where(mix[:, None], pal[1], pal[0])
        self.tw = rnd.uniform(0, 6, n)

    def draw(self, img, t):
        dt = t - self.t0
        if dt < 0:
            return
        if dt < self.rise:                      # rocket trail going up
            k = dt / self.rise
            y = H - 420 - (H - 420 - self.cy) * (1 - (1 - k) ** 2)
            for j in range(6):
                splat(img, self.cx, y + j * 14, (1, .75, .4), .55 * (1 - j / 6), SPR[5])
            return
        a = dt - self.rise
        if a > 2.2:
            return
        drag = (1 - np.exp(-2.2 * a)) / 2.2
        xs = self.cx + self.vx * drag
        ys = self.cy + self.vy * drag + 60 * a * a
        fade = max(0.0, 1 - a / 2.2) ** 1.6
        flick = .65 + .35 * np.sin(self.tw + a * 30)
        if a < .12:
            splat(img, self.cx, self.cy, (1, .95, .8), 4 * (1 - a / .12), SPR[12])
        for i in range(len(xs)):
            splat(img, xs[i], ys[i], self.col[i], 1.7 * fade * flick[i], SPR[8])
            if a < 1.2:   # short trail
                splat(img, xs[i] - self.vx[i] * .018, ys[i] - self.vy[i] * .018, self.col[i], .7 * fade, SPR[5])


def background():
    y = np.linspace(0, 1, H)[:, None, None]
    top, mid, low = np.array([.025, .02, .09]), np.array([.13, .04, .16]), np.array([.32, .09, .06])
    g = np.where(y < .6, top + (mid - top) * (y / .6), mid + (low - mid) * ((y - .6) / .4))
    bg = np.repeat(g, W, axis=1).astype(np.float32)
    return bg


DIYA_X = [140, 340, 540, 740, 940]
DIYA_Y = 1700


def diya_layer():
    """clay diyas with painted dots on a dark ledge, drawn once (RGBA)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, DIYA_Y + 55, W, H], fill=(40, 14, 10, 255))
    d.rectangle([0, DIYA_Y + 50, W, DIYA_Y + 62], fill=(90, 35, 20, 255))
    for x in DIYA_X:
        d.ellipse([x - 82, DIYA_Y - 30, x + 82, DIYA_Y + 62], fill=(150, 62, 25, 255))
        d.chord([x - 82, DIYA_Y - 70, x + 82, DIYA_Y + 62], 0, 180, fill=(196, 88, 32, 255))
        d.ellipse([x - 82, DIYA_Y - 30, x + 82, DIYA_Y + 4], fill=(120, 45, 18, 255))
        d.ellipse([x - 70, DIYA_Y - 24, x + 70, DIYA_Y - 2], fill=(70, 30, 12, 255))
        for k in range(7):
            px = x - 60 + k * 20
            d.ellipse([px - 6, DIYA_Y + 22, px + 6, DIYA_Y + 34], fill=(255, 210, 90, 255))
        d.polygon([(x + 70, DIYA_Y - 18), (x + 100, DIYA_Y - 30), (x + 82, DIYA_Y - 2)], fill=(196, 88, 32, 255))
    return im


def flame(t, i):
    """flame RGBA image for diya i at time t (drawn small, then blurred)."""
    fl = 1 + .12 * math.sin(t * 13 + i * 2.1) + .07 * math.sin(t * 23 + i)
    sway = 4 * math.sin(t * 7 + i * 1.3)
    im = Image.new("RGBA", (120, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    h = 95 * fl
    pts_o = [(60 + sway * (1 - k / 20) + 26 * math.sin(math.pi * k / 20) ** 1.3 * (1 if s else -1),
              180 - h * (k / 20)) for s in (1, 0) for k in (range(21) if s else range(20, -1, -1))]
    d.polygon(pts_o, fill=(255, 150, 30, 235))
    pts_i = [(60 + sway * .5 * (1 - k / 20) + 13 * math.sin(math.pi * k / 20) * (1 if s else -1),
              180 - .62 * h * (k / 20)) for s in (1, 0) for k in (range(21) if s else range(20, -1, -1))]
    d.polygon(pts_i, fill=(255, 245, 200, 255))
    return im.filter(ImageFilter.GaussianBlur(2.2)), fl


def main(out):
    out = os.path.abspath(out)
    os.makedirs(os.path.join(out, "check"), exist_ok=True)
    wav = os.path.join(out, "music.wav")
    M.main(wav)
    cards = render_cards(os.path.join(out, "cards"))
    length = M.LENGTH + 1.0
    nfr = int(length * FPS)
    rnd = np.random.default_rng(2026)
    fireworks = []
    for b in M.BURST_BEATS:
        t = b * B - .55                     # explode on the beat
        fireworks.append(Firework(t, rnd, big=True))
        fireworks.append(Firework(t + B, rnd))
        if b >= 28:
            fireworks.append(Firework(t + 2 * B, rnd))
    fireworks += [Firework(.3 + k * .45, rnd) for k in range(3)]
    bg = background()
    stars = [(rnd.uniform(0, W), rnd.uniform(0, 1100), rnd.uniform(.1, .45), rnd.uniform(0, 6)) for _ in range(140)]
    embers = [(rnd.choice(DIYA_X) + rnd.uniform(-30, 30), rnd.uniform(0, 6), rnd.uniform(60, 140), rnd.uniform(-25, 25))
              for _ in range(70)]
    diyas = diya_layer()
    proc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                             os.path.join(out, "reel.mp4")], stdin=subprocess.PIPE)
    checks = {int(s * FPS) for s in (2.0, 5.5, 9.0, 13.5, 17.5, 22.0)}
    for fi in range(nfr):
        t = fi / FPS
        img = bg.copy()
        for x, y, a, ph in stars:
            splat(img, x, y, (1, .95, .85), a * (.6 + .4 * math.sin(t * 3 + ph)), SPR[5])
        for fw in fireworks:
            fw.draw(img, t)
        lit = [i for i in range(5) if t >= .25 + i * .38]
        for i in lit:
            k = min(1, (t - .25 - i * .38) / .3)
            splat(img, DIYA_X[i], DIYA_Y - 80, (1, .55, .2), .35 * k * (1 + .08 * math.sin(t * 11 + i)), BIG)
        for x0, ph, sp, dx in embers:
            age = (t * sp / 600 + ph) % 1
            if len(lit) == 5:
                splat(img, x0 + dx * age + 8 * math.sin(age * 9 + ph), DIYA_Y - 110 - age * 700,
                      (1, .7, .3), .6 * (1 - age), SPR[5])
        frame = Image.fromarray((np.clip(img, 0, 1) ** (1 / 1.1) * 255).astype(np.uint8), "RGB").convert("RGBA")
        frame.alpha_composite(diyas)
        for i in lit:
            fl, _ = flame(t, i)
            frame.alpha_composite(fl, (DIYA_X[i] - 60, DIYA_Y - 205))
        for ci, (sb, eb, _) in enumerate(CARDS):
            s, e = sb * B, min(eb * B, length - .2)
            if s - .05 <= t <= e:
                a = min(1, (t - s) / .45, (e - t) / .3)
                if a <= 0:
                    continue
                sc = .9 + .1 * min(1, (t - s) / .45) ** .5
                card = cards[ci]
                if sc < .999:
                    cw, ch = int(W * sc), int(H * sc)
                    card = Image.new("RGBA", (W, H))
                    card.alpha_composite(cards[ci].resize((cw, ch)), ((W - cw) // 2, (H - ch) // 2))
                if a < 1:
                    card = card.copy()
                    card.putalpha(card.getchannel("A").point(lambda v, a=a: int(v * a)))
                frame.alpha_composite(card)
        rgb = frame.convert("RGB")
        if fi in checks:
            rgb.save(os.path.join(out, "check", f"t{fi / FPS:04.1f}s.jpg"), quality=88)
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    proc.wait()
    print("reel:", os.path.join(out, "reel.mp4"), f"{length:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
