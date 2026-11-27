"""Book-summary video in the "cover + typing captions" style (one static scene for the whole video):
dark background with a warm glow, the book cover on the left (gently floating), orange embers flying,
big Hindi captions on the right that appear word by word (*key* words in a magenta box), and a white
voice waveform bottom right. Plus a matching 1280x720 thumbnail.

    python tools/book_video.py voice DIR     # Sarvam TTS per segment -> DIR/voice/NN.mp3  (~Rs 3 per 1000 chars)
    python tools/book_video.py build DIR     # -> DIR/video.mp4 (+ DIR/check/*.jpg)
    python tools/book_video.py thumb DIR     # -> DIR/thumbnail.jpg

DIR/script.json:
  {"book_en": "UNWINDING ANXIETY", "author_en": "JUDSON BREWER", "tagline_en": "...", "voice": "sarvam:anand_hi_documentary",
   "model": "bulbul:v4-flash", "pace": 1.1, "thumb": ["line 1 (yellow)", "line 2 (white)", "line 3 (cyan)"],
   "segments": [{"text": "देवनागरी लाइन, *ख़ास* शब्द सितारों में"}, ...]}
  Optional DIR/cover.jpg (the real cover); without it a cover is drawn from book_en / author_en / tagline_en.
Hindi is shaped by Chrome (Playwright with the installed Chrome), since Pillow here has no libraqm.
"""
import html
import json
import math
import os
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from story_video import sarvam_tts, duration  # noqa: E402

W, H, FPS, SR = 1920, 1080, 30, 44100
GAP = 0.35                      # silence between segments
CAP_BOX = (990, 300, 880, 430)  # x, y, w, h of the caption area
WAVE_BOX = (1330, 930, 420, 90)
COVER_H = 700
FONT = "'Nirmala UI','Noto Sans Devanagari',sans-serif"


def load(d):
    return json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))


def run(cmd):
    subprocess.run(cmd, check=True)


def clean(t):
    return t.replace("*", "")


# ---------------------------------------------------------------- voice
def voice(d):
    s = load(d)
    out = os.path.join(d, "voice")
    os.makedirs(out, exist_ok=True)
    spk = s.get("voice", "sarvam:anand_hi_documentary").split(":", 1)[1]
    for i, seg in enumerate(s["segments"], 1):
        mp3 = os.path.join(out, f"{i:02d}.mp3")
        if not os.path.exists(mp3):
            sarvam_tts(clean(seg["text"]), mp3, spk, model=s.get("model", "bulbul:v4-flash"), pace=float(s.get("pace", 1.1)))
        print(f"{i:02d}: {duration(mp3):.1f}s")


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def speech_span(a):
    """first/last sample above a quiet threshold (seconds)."""
    env = np.convolve(np.abs(a), np.ones(441) / 441, "same")
    idx = np.where(env > 0.02)[0]
    return (idx[0] / SR, idx[-1] / SR) if idx.size else (0, a.size / SR)


def word_times(text, t0, t1):
    """spread the segment's speech span over its words by length; punctuation adds pause weight."""
    words = text.split()
    wts = []
    for w in words:
        c = len(clean(w).strip(",.?!।"))
        p = 5 if re.search(r"[।?!.]$", w) else 3 if w.endswith(",") or w.endswith(":") else 0
        wts.append((c + 1.5, p))
    tot = sum(a + b for a, b in wts)
    acc, out = t0, []
    for w, (a, b) in zip(words, wts):
        d = (t1 - t0) * a / tot
        out.append([w, round(acc, 3), round(acc + d, 3)])
        acc += d + (t1 - t0) * b / tot
    return out


# ---------------------------------------------------------------- images (Chrome)
class Painter:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.p = sync_playwright().start()
        self.b = self.p.chromium.launch(channel="chrome")
        self.pg = self.b.new_page(viewport={"width": W, "height": H})

    def shot(self, doc, png, w, h, transparent=True):
        self.pg.set_viewport_size({"width": w, "height": h})
        src = os.path.abspath(png) + ".html"          # a file page, so file:/// images load
        with open(src, "w", encoding="utf-8") as f:
            f.write(doc)
        self.pg.goto("file:///" + src.replace(os.sep, "/"))
        os.remove(src)
        self.pg.wait_for_timeout(30)
        self.pg.screenshot(path=png, omit_background=transparent)

    def close(self):
        self.b.close()
        self.p.stop()


def page(css, body):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>*{{margin:0;padding:0;box-sizing:border-box}}"
            f"html,body{{background:transparent;overflow:hidden}}{css}</style></head><body>{body}</body></html>")


COVER_SVG = """<svg viewBox="0 0 500 420" width="100%" height="100%" preserveAspectRatio="xMidYMax slice">
<defs><radialGradient id="sun" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff7d6"/>
<stop offset=".45" stop-color="#ffe27a" stop-opacity=".9"/><stop offset="1" stop-color="#ffcc33" stop-opacity="0"/></radialGradient></defs>
<circle cx="300" cy="200" r="120" fill="url(#sun)"/>
<path d="M0 250 L70 205 L130 235 L200 180 L270 228 L340 190 L420 232 L500 200 L500 420 L0 420Z" fill="#d99a22" opacity=".55"/>
<path d="M0 290 L90 250 L160 280 L240 240 L320 285 L400 255 L500 285 L500 420 L0 420Z" fill="#a86b14" opacity=".75"/>
<path d="M0 330 L110 300 L190 322 L270 296 L360 330 L440 310 L500 325 L500 420 L0 420Z" fill="#6e4410" opacity=".9"/>
<path d="M0 420 L0 345 Q60 330 120 338 L170 300 Q200 292 215 300 L245 330 Q300 345 340 360 L500 380 L500 420Z" fill="#2b1a08"/>
<g fill="#1a1006"><circle cx="192" cy="262" r="9"/><path d="M180 274 Q192 268 204 274 L209 300 L176 300Z"/>
<path d="M176 298 L209 298 L218 304 L170 304Z"/></g></svg>"""


def cover_png(painter, s, path):
    """the book as a 3D-ish object with spine and shadow, transparent PNG."""
    cw, ch = int(COVER_H * 0.68), COVER_H
    real = os.path.join(os.path.dirname(path), "cover.jpg")
    if os.path.exists(real):
        face = f"<img src='file:///{os.path.abspath(real).replace(os.sep, '/')}' style='width:100%;height:100%;object-fit:cover'>"
    else:
        t = s["book_en"].split()
        title = "<br>".join(html.escape(x) for x in t)
        face = (f"<div class='tag'>{html.escape(s.get('tagline_en', ''))}</div>"
                f"<div class='title'>{title}</div><div class='rule'></div>"
                f"<div class='art'>{COVER_SVG}</div><div class='auth'>{html.escape(s['author_en'])}</div>")
    css = f"""
body{{width:{cw + 120}px;height:{ch + 120}px}}
.book{{position:absolute;left:60px;top:40px;width:{cw}px;height:{ch}px;border-radius:4px 10px 10px 4px;overflow:hidden;
 background:linear-gradient(180deg,#ffd84a 0%,#ffc928 45%,#f0a81c 100%);
 box-shadow:-14px 26px 40px rgba(0,0,0,.65),0 0 60px rgba(255,190,40,.25)}}
.spine{{position:absolute;left:0;top:0;bottom:0;width:26px;background:linear-gradient(90deg,rgba(0,0,0,.35),rgba(255,255,255,.25) 60%,rgba(0,0,0,.15));z-index:3}}
.gloss{{position:absolute;inset:0;background:linear-gradient(115deg,rgba(255,255,255,.18),rgba(255,255,255,0) 40%);z-index:3}}
.tag{{position:absolute;top:22px;left:40px;right:14px;text-align:center;font:700 13px Arial;letter-spacing:1px;color:#3a2606}}
.title{{position:absolute;top:66px;left:40px;right:14px;text-align:center;font:900 60px/1.02 'Arial Black',Arial;color:#20160a;letter-spacing:1px}}
.rule{{position:absolute;top:232px;left:120px;right:94px;height:3px;background:#20160a}}
.art{{position:absolute;left:26px;right:0;bottom:0;height:420px}}
.auth{{position:absolute;bottom:22px;left:40px;right:14px;text-align:center;font:800 20px Arial;letter-spacing:3px;color:#fff3c4;z-index:2}}
"""
    painter.shot(page(css, f"<div class='book'><div class='spine'></div><div class='gloss'></div>{face}</div>"),
                 path, cw + 120, ch + 120)


def background_png(path, w=W, h=H, glow=(470, 540), r=760):
    """black with a warm gold glow behind the cover and a faint floor line."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - glow[0]) / 1.25) ** 2 + (yy - glow[1]) ** 2) / r
    g = np.clip(1 - d, 0, 1) ** 2.2
    floor = np.exp(-((yy - h * 0.86) / (h * 0.05)) ** 2) * np.clip(1 - np.abs(xx - glow[0]) / (w * 0.6), 0, 1) * 0.35
    v = np.clip(g * 0.85 + floor, 0, 1)
    rgb = np.stack([v * 255 * 1.0, v * 255 * 0.70, v * 255 * 0.12], -1) + 6
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path)


def embers(out, seconds=10.0, n=55, seed=3):
    """seamless loop of orange embers flying up-right, black background (screen-blended later)."""
    w, h = 960, 540
    rng = np.random.default_rng(seed)
    frames = int(seconds * FPS)
    x0, y0 = rng.uniform(0, w, n), rng.uniform(0, h, n)
    laps = rng.integers(1, 3, n)
    drift = rng.uniform(0.2, 0.6, n)           # rightward per upward unit
    size = rng.uniform(0.8, 2.4, n)
    bright = rng.uniform(0.4, 1.0, n)
    tw = rng.integers(1, 4, n)
    ph = rng.uniform(0, 2 * np.pi, n)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                             "-r", str(FPS), "-i", "-", "-vf", f"scale={W}:{H}:flags=bicubic,format=yuv420p",
                             "-c:v", "libx264", "-crf", "20", "-preset", "fast", out], stdin=subprocess.PIPE)
    for f in range(frames):
        p = f / frames
        im = Image.new("RGB", (w, h))
        dr = ImageDraw.Draw(im)
        dy = laps * h * p
        ys = (y0 - dy) % h
        xs = (x0 + drift * dy * (w / h) * 0.6) % w
        b = bright * (0.55 + 0.45 * np.sin(2 * np.pi * tw * p + ph))
        for x, y, s, bb, dz in zip(xs, ys, size, b, drift):
            ln = 2 + 3 * s
            c = (int(255 * bb), int(140 * bb), int(40 * bb))
            dr.line([(x, y), (x - ln * dz, y + ln)], fill=c, width=max(1, int(s + 0.5)))
            dr.ellipse([x - s, y - s, x + s, y + s], fill=(255, int(200 * bb), int(90 * bb)))
        glow = np.asarray(im.filter(ImageFilter.GaussianBlur(5))).astype(np.float32)
        arr = np.asarray(im).astype(np.float32) * 0.9 + glow * 2.2
        proc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()


def caption_states(painter, chunks, outdir):
    """one transparent PNG per (chunk, words shown). Returns [(png, start, end)]."""
    x, y, w, h = CAP_BOX
    css = f"""body{{width:{w}px;height:{h}px;display:flex;align-items:center;justify-content:center}}
.c{{width:{w}px;text-align:center;font-family:{FONT};font-weight:700;font-size:90px;line-height:1.3;color:#fff;
 text-shadow:0 4px 14px rgba(0,0,0,.8)}}
.w{{display:inline-block;margin:0 9px}} .h{{background:#c3178f;border-radius:10px;padding:0 12px;margin:0 6px}}
.x{{visibility:hidden}}"""
    states = []
    for ci, ch in enumerate(chunks):
        for k in range(1, len(ch["words"]) + 1):
            spans = "".join(
                f"<span class='w{' h' if '*' in wd else ''}{' x' if j >= k else ''}'>{html.escape(clean(wd))}</span>"
                for j, (wd, a, b) in enumerate(ch["words"]))
            png = os.path.join(outdir, f"c{ci:04d}_{k:02d}.png")
            painter.shot(page(css, f"<div class='c'>{spans}</div>"), png, w, h)
            st = ch["words"][k - 1][1]
            en = ch["words"][k][1] if k < len(ch["words"]) else ch["end"]
            states.append((png, st, en))
    return states


def chunks_of(words_by_seg, seg_ends, maxc=44):
    """per segment: clauses (split at , । ? !) packed up to maxc chars; a long clause is cut into even parts."""
    L = lambda ws: sum(len(clean(w[0])) + 1 for w in ws)  # noqa: E731
    chunks = []
    for words, end in zip(words_by_seg, seg_ends):
        clauses, cur = [], []
        for wd in words:
            cur.append(wd)
            if re.search(r"[,।?!:]$", wd[0]):
                clauses.append(cur)
                cur = []
        if cur:
            clauses.append(cur)
        packed = []
        for cl in clauses:
            if packed and L(packed[-1]) + L(cl) <= maxc:
                packed[-1] = packed[-1] + cl
            elif L(cl) > maxc:
                k = math.ceil(L(cl) / maxc)
                per, part, acc = L(cl) / k, [], 0
                for wd in cl:
                    if part and acc >= per and len(packed) < 10 ** 6:
                        packed.append(part)
                        part, acc = [], 0
                    part.append(wd)
                    acc += len(clean(wd[0])) + 1
                packed.append(part)
            else:
                packed.append(cl)
        for p in packed:
            chunks.append({"words": p, "seg_end": end})
    for i, c in enumerate(chunks):
        last = i + 1 == len(chunks) or chunks[i + 1]["seg_end"] != c["seg_end"]
        nxt = chunks[i + 1]["words"][0][1] if i + 1 < len(chunks) else c["seg_end"] + 1.0
        c["end"] = min(nxt, c["seg_end"] + 0.3) if last else nxt
        c["end"] = max(c["end"], c["words"][-1][2])
    return chunks


# ---------------------------------------------------------------- build
def build(d):
    s = load(d)
    tmp = os.path.join(d, "tmp")
    capdir = os.path.join(tmp, "cap")
    os.makedirs(capdir, exist_ok=True)
    os.makedirs(os.path.join(d, "check"), exist_ok=True)

    # voice track + word times
    lead = 0.8
    parts, words_by_seg, seg_ends, t = [], [], [], lead
    parts_at = []
    for i, seg in enumerate(s["segments"], 1):
        a = decode(os.path.join(d, "voice", f"{i:02d}.mp3"))
        s0, s1 = speech_span(a)
        words_by_seg.append(word_times(seg["text"], t + s0, t + s1))
        if seg.get("part"):
            parts_at.append((seg["part"], 0.0 if not parts_at else t))
        seg_ends.append(t + s1)
        parts.append(a)
        t += a.size / SR + GAP
    total = round(t + 1.6, 2)
    n = int(total * SR)
    vo = np.zeros(n, np.float32)
    j = int(lead * SR)
    for a in parts:
        vo[j:j + a.size] += a
        j += a.size + int(GAP * SR)
    vo_path = os.path.join(tmp, "voice.wav")
    write_wav(vo_path, vo)

    mus_path = os.path.join(tmp, "music.wav")
    run([sys.executable, os.path.join(os.path.dirname(__file__), "soft_music.py"), mus_path, str(math.ceil(total) + 1)])
    mus = decode(mus_path)[:n]
    mus = np.pad(mus, (0, n - mus.size)) * (0.10 / max(np.abs(mus).max(), 1e-6))
    fade = np.minimum(1, np.minimum(np.arange(n) / SR / 1.0, (n - np.arange(n)) / SR / 1.5))
    mix = vo * 0.95 + mus * fade
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    mix_path = os.path.join(tmp, "mix.wav")
    write_wav(mix_path, mix)

    # images
    painter = Painter()
    try:
        cover = os.path.join(tmp, "cover.png")
        cover_png(painter, s, cover)
        chunks = chunks_of(words_by_seg, seg_ends)
        states = caption_states(painter, chunks, capdir)
    finally:
        painter.close()
    bg = os.path.join(tmp, "bg.png")
    background_png(bg)
    emb = os.path.join(tmp, "embers.mp4")
    if not os.path.exists(emb):
        embers(emb)
    blank = os.path.join(capdir, "blank.png")
    Image.new("RGBA", (CAP_BOX[2], CAP_BOX[3])).save(blank)

    # caption track as an ffconcat image sequence
    lst = os.path.join(capdir, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        cur = 0.0
        for png, st, en in states:
            if st > cur + 0.01:
                f.write(f"file '{os.path.abspath(blank)}'\nduration {st - cur:.3f}\n")
            f.write(f"file '{os.path.abspath(png)}'\nduration {max(en - st, 0.04):.3f}\n")
            cur = en
        f.write(f"file '{os.path.abspath(blank)}'\nduration {max(total - cur, 0.1):.3f}\n")
        f.write(f"file '{os.path.abspath(blank)}'\n")

    cx, cy = 470 - Image.open(cover).width // 2, 540 - Image.open(cover).height // 2 - 10
    wx, wy, ww, wh = WAVE_BOX
    x, y = CAP_BOX[:2]
    fc = (
        f"[0:v]format=gbrp[bg];"
        f"[1:v]format=gbrp[em];[bg][em]blend=all_mode=screen,format=rgb24[b1];"
        f"[2:v]format=rgba[cv];[b1][cv]overlay=x={cx}:y='{cy}+7*sin(t*0.9)':eval=frame[b2];"
        f"[4:a]volume=2,showwaves=s={ww}x{wh}:mode=cline:rate={FPS}:colors=white:scale=sqrt:draw=full,format=rgba,"
        f"colorchannelmixer=aa=0.9[wv];[b2][wv]overlay=x={wx}:y={wy}[b3];"
        f"[3:v]fps={FPS},format=rgba[cp];[b3][cp]overlay=x={x}:y={y}:format=auto,"
        f"fade=t=in:st=0:d=0.8,fade=t=out:st={total - 1.0:.2f}:d=1.0,format=yuv420p[v]"
    )
    out = os.path.join(d, "video.mp4")
    run(["ffmpeg", "-v", "error", "-y",
         "-loop", "1", "-framerate", str(FPS), "-i", bg,
         "-stream_loop", "-1", "-i", emb,
         "-loop", "1", "-framerate", str(FPS), "-i", cover,
         "-f", "concat", "-safe", "0", "-i", lst,
         "-i", vo_path, "-i", mix_path,
         "-filter_complex", fc, "-map", "[v]", "-map", "5:a", "-t", f"{total}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    for k, tt in enumerate([1.5, total * 0.3, total * 0.55, total * 0.8]):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tt:.2f}", "-i", out, "-frames:v", "1", "-vf", "scale=960:-1",
             os.path.join(d, "check", f"frame_{k + 1}.jpg")])
    json.dump([c["words"] for c in chunks], open(os.path.join(tmp, "chunks.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    with open(os.path.join(d, "chapters.txt"), "w", encoding="utf-8") as f:
        for name, at in parts_at:
            f.write(f"{int(at // 60)}:{int(at % 60):02d} {name}\n")
    print(f"{out}: {duration(out):.1f}s, {len(chunks)} caption chunks, {len(states)} caption states")


def write_wav(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- thumbnail
def thumb(d):
    s = load(d)
    tmp = os.path.join(d, "tmp")
    os.makedirs(tmp, exist_ok=True)
    tw, th = 1280, 720
    bg = os.path.join(tmp, "thumb_bg.png")
    background_png(bg, tw, th, glow=(300, 380), r=560)
    painter = Painter()
    try:
        cover = os.path.join(tmp, "cover.png")
        cover_png(painter, s, cover)
        l1, l2, l3 = (html.escape(x) for x in s["thumb"])
        css = f"""body{{width:{tw}px;height:{th}px;position:relative;
 background:url('file:///{os.path.abspath(bg).replace(os.sep, '/')}')}}
.cv{{position:absolute;left:18px;top:105px;height:560px}}
.t{{position:absolute;left:520px;right:20px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;
 align-items:center;text-align:center;font-family:{FONT};font-weight:700;line-height:1.12;
 text-shadow:0 6px 18px rgba(0,0,0,.9)}}
.a{{font-size:124px;color:#ffe500}} .b{{font-size:84px;color:#fff;margin-top:14px}} .c{{font-size:84px;color:#3ee6ff;margin-top:22px}}"""
        body = (f"<img class='cv' src='file:///{os.path.abspath(cover).replace(os.sep, '/')}'>"
                f"<div class='t'><div class='a'>{l1}</div><div class='b'>{l2}</div><div class='c'>{l3}</div></div>")
        png = os.path.join(tmp, "thumb.png")
        painter.shot(page(css, body), png, tw, th, transparent=False)
    finally:
        painter.close()
    Image.open(png).convert("RGB").save(os.path.join(d, "thumbnail.jpg"), quality=92)
    print(os.path.join(d, "thumbnail.jpg"))


if __name__ == "__main__":
    {"voice": voice, "build": build, "thumb": thumb}[sys.argv[1]](sys.argv[2])
