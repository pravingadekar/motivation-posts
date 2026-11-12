"""Render the Golu Bandar story-01 cartoon (frames + audio) from golu/story-01/script.json and voice/*.wav.

    python tools/golu_story.py golu/story-01 [--frames 10,200,...] [--jobs 4]

Writes <dir>/build/video_noaudio.mp4, <dir>/build/audio.wav, <dir>/timeline.json, then muxes <dir>/video.mp4.
With --frames, only writes those frame numbers as JPGs into <dir>/check/ (quick look).
"""
import json
import math
import os
import random
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golu_draw as G  # noqa: E402

FPS = 24
SR = 48000
W, H = G.W, G.H
GY = G.GROUND
TX = 1500          # tree x
INTRO, OUTRO = 4.0, 5.5
LEAD, GAP, TAIL = 0.6, 0.45, 0.8
EXTRA = {1: 0.3, 2: 0.9, 4: 0.6, 6: 1.0, 9: 0.6, 12: 0.8, 13: 1.6, 15: 0.6, 16: 1.2, 17: 0.6}
HERE = os.path.dirname(os.path.abspath(__file__))
POPPINS = os.path.join(HERE, "..", "brand", "fonts", "Poppins-ExtraBold.ttf")
D = None  # story dir


# ------------------------------------------------------------------ timeline + audio analysis
def read_wav(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
        assert w.getframerate() == SR, path
    return a


def envelope(a):
    hop = SR // FPS
    n = len(a) // hop + 1
    e = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)])
    e = e / (np.percentile(e, 92) + 1e-6)
    e = np.clip((e - 0.12) * 1.25, 0, 1)
    # syllable flutter so the mouth opens and closes
    return e


def build_timeline(d):
    script = json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))
    t = INTRO
    scenes = []
    for sc in script["scenes"]:
        start = t
        t += LEAD
        lines = []
        for k, ln in enumerate(sc["lines"]):
            f = os.path.join(d, "voice", f"s{sc['id']:02d}_l{k}.wav")
            a = read_wav(f)
            dur = len(a) / SR
            lines.append(dict(who=ln["who"], hi=ln["hi"], start=round(t - start, 3), dur=round(dur, 3), file=f,
                              abs=round(t, 3)))
            t += dur + GAP
        t += TAIL - GAP + EXTRA.get(sc["id"], 0)
        scenes.append(dict(id=sc["id"], start=round(start, 3), dur=round(t - start, 3), lines=lines))
    total = t + OUTRO
    return dict(scenes=scenes, total=round(total, 3), intro=INTRO, outro_start=round(t, 3))


TL = None
ENV = {}


def load(d):
    global D, TL
    D = d
    TL = build_timeline(d)
    for sc in TL["scenes"]:
        for ln in sc["lines"]:
            ENV[ln["file"]] = envelope(read_wav(ln["file"]))


def mouth_for(who, T):
    """Mouth openness for a character at absolute time T."""
    for sc in TL["scenes"]:
        if not (sc["start"] <= T < sc["start"] + sc["dur"]):
            continue
        for ln in sc["lines"]:
            if ln["who"] == who or (ln["who"] == "chorus" and who in ("golu", "pinky", "haathi")):
                if ln["abs"] <= T < ln["abs"] + ln["dur"]:
                    e = ENV[ln["file"]]
                    i = int((T - ln["abs"]) * FPS)
                    v = e[min(i, len(e) - 1)]
                    return float(v * (0.75 + 0.25 * math.sin(T * 26)))
    return 0.0


def talking(who, T):
    for sc in TL["scenes"]:
        for ln in sc["lines"]:
            if (ln["who"] == who or (ln["who"] == "chorus" and who in ("golu", "pinky", "haathi"))) \
                    and ln["abs"] <= T < ln["abs"] + ln["dur"]:
                return True
    return False


# ------------------------------------------------------------------ small animation helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, f):
    return a + (b - a) * f


def blink(T, seed):
    ph = (T + seed * 1.37) % (3.1 + seed * 0.4)
    return 1.0 if ph < 0.11 else 0.0


def word_time(ln, needle, nth=0):
    """Approximate time (scene-local) at which a word is spoken, by character position."""
    txt = ln["hi"]
    idx = -1
    for _ in range(nth + 1):
        idx = txt.find(needle, idx + 1)
    if idx < 0:
        idx = 0
    return ln["start"] + ln["dur"] * idx / max(1, len(txt))


def arc(p0, p1, f, h=180):
    f = clamp(f)
    return lerp(p0[0], p1[0], f), lerp(p0[1], p1[1], f) - h * 4 * f * (1 - f)


def fall_y(t, y0, y1, dur=0.55):
    """Fall from y0 to y1 with a little bounce; t from 0."""
    if t <= 0:
        return y0
    if t < dur:
        return y0 + (y1 - y0) * (t / dur) ** 2
    b = t - dur
    return y1 - max(0, 40 * math.sin(min(math.pi, b * 8)) * math.exp(-b * 3)) if b < 0.4 else y1


def talk_arms(T, seed=0, base=(14, 12, 14, 12)):
    la, le, ra, re = base
    return (la + 18 * max(0, math.sin(T * 5 + seed)), le + 25 * max(0, math.sin(T * 4 + seed)),
            ra + 22 * max(0, math.sin(T * 4.4 + seed + 1)), re + 20 * max(0, math.sin(T * 5.2 + seed)))


def wave_arm(T):
    return (14, 10, 140, -15 + 28 * math.sin(T * 11))


# ------------------------------------------------------------------ scenes
PILE = [(-75, 0), (-25, 0), (25, 0), (75, 0), (-50, -42), (0, -42), (50, -42), (-25, -84), (25, -84), (0, -126)]


def draw_pile(c, x, y, n, ripe=1.0):
    for k in range(min(n, len(PILE))):
        dx, dy = PILE[k]
        G.mango(c, x + dx, y + dy - 22, 1.15, (k * 37) % 40 - 20, ripe)


def golu(T, **kw):
    st = dict(x=900, y=GY + 20, s=1.0, cfg=G.GOLU, t=T, mouth=mouth_for("golu", T), blink=blink(T, 1),
              arms=talk_arms(T) if talking("golu", T) else (14, 12, 14, 12),
              headbob=3 * math.sin(T * 9) if talking("golu", T) else 0)
    st.update(kw)
    return ("monkey", st)


def pinky(T, **kw):
    st = dict(x=620, y=GY + 25, s=0.82, cfg=G.PINKY, t=T + 1.3, mouth=mouth_for("pinky", T), blink=blink(T, 2),
              arms=talk_arms(T, 2) if talking("pinky", T) else (10, 10, 10, 10), flip=True,
              headbob=3 * math.sin(T * 9) if talking("pinky", T) else 0)
    st.update(kw)
    return ("monkey", st)


def haathi(T, **kw):
    st = dict(x=360, y=GY + 15, s=0.95, t=T, mouth=mouth_for("haathi", T), blink=blink(T, 3),
              headbob=3 * math.sin(T * 6) if talking("haathi", T) else 0)
    st.update(kw)
    return ("elephant", st)


def ped(T, **kw):
    st = dict(x=TX, y=GY - 10, s=0.95, t=T, glow=0.6, mouth=mouth_for("ped", T), blink=blink(T, 4), awake=1.0)
    st.update(kw)
    return ("tree", st)


def scene_state(sid, t, T, sc):
    """Returns cam, actors, fx, bg."""
    L = sc["lines"]
    fx = []
    bg = dict(sunset=0.0, heat=0.0)
    actors = []
    cam = (960, 540, 1.0)
    if sid == 1:
        land = L[2]["start"] - 0.5
        cam = (lerp(780, 880, ease(t / sc["dur"])), 620, lerp(1.28, 1.34, t / sc["dur"]))
        actors.append(ped(T, awake=0.0, glow=0.0, mouth=0))
        if t < land:
            ang = 38 * math.cos(t * 1.7) * (0.6 + 0.4 * (1 - t / land))
            ax, ay, ln = 900, -260, 900
            px = ax + ln * math.sin(math.radians(ang))
            py = ay + ln * math.cos(math.radians(ang))
            fx.append(("vine", ax, ay, px, py - 330))
            f = clamp((t - (land - 0.45)) / 0.45)
            actors.append(golu(T, x=lerp(px, 900, f), y=lerp(py + 40, GY + 20, f), tilt=-ang * (1 - f) * 0.6,
                               arms=(168, 5, 168, 5), expr="joy"))
        else:
            sq = max(0, 1 - (t - land) / 0.25)
            arms = wave_arm(T) if t > L[2]["start"] - 0.2 else (14, 12, 14, 12)
            actors.append(golu(T, squash=sq, arms=arms, expr="joy" if talking("golu", T) else "happy"))
    elif sid == 2:
        dh = word_time(L[0], "धप्प")
        cam = (lerp(820, 1200, ease((t - dh) / 2.0)), 600, lerp(1.22, 1.1, ease((t - dh) / 2.0)))
        actors.append(ped(T, awake=0.0, glow=lerp(0.0, 0.9, ease((t - dh - 0.4) / 1.5)), mouth=0))
        if t < dh - 0.5:
            ang = 34 * math.cos(t * 1.9)
            ax, ay, ln = 820, -260, 880
            px = ax + ln * math.sin(math.radians(ang))
            py = ay + ln * math.cos(math.radians(ang))
            fx.append(("vine", ax, ay, px, py - 330))
            actors.append(golu(T, x=px, y=py + 40, tilt=-ang * 0.6, arms=(168, 5, 168, 5), expr="joy"))
        elif t < dh:
            f = (t - (dh - 0.5)) / 0.5
            actors.append(golu(T, x=lerp(980, 1060, f), y=lerp(GY - 380, GY + 20, f * f), tilt=f * 200,
                               arms=(150, 20, 150, 20), expr="surprised"))
        else:
            k = t - dh
            fx.append(("puff", 1060, GY + 20, k / 0.9))
            fx.append(("word", "DHAPP!", 1040, GY - 470, k, 120))
            if k < 1.8:
                fx.append(("dizzy", 1060, GY - 380, T))
            look = (0.7, -0.6) if k > 1.0 else (0, 0)
            actors.append(golu(T, x=1060, sit=1, squash=max(0, 1 - k / 0.25), look=look,
                               expr="surprised" if talking("golu", T) or k > 1.2 else "happy",
                               arms=(40, 60, 150, -10) if talking("golu", T) else (30, 20, 30, 20)))
    elif sid == 3:
        cam = (1300, 520, 1.15)
        aw = ease(t / 0.8)
        actors.append(ped(T, awake=0.5 + aw * 0.5, glow=0.9))
        actors.append(golu(T, x=1020, look=(0.8, -0.5), expr="surprised" if t < 2.5 else "joy",
                           arms=(25, 20, 25, 20) if t < 2.5 else (60, 40, 60, 40)))
        for k in range(5):
            fx.append(("sparkle_rise", TX + (k - 2) * 120, GY - 300, T + k))
    elif sid == 4:
        cam = (1180, 580, 1.15)
        tap = L[1]["start"] + 0.1
        land = tap + 0.6
        actors.append(ped(T, picked=1 if t > tap else 0, glow=1.0))
        sing = talking("golu", T) and t < L[1]["start"]
        if t < land:
            bounce = abs(math.sin(T * 6)) * 22 if sing else 0
            cl = 0.5 + 0.5 * math.sin(T * 12)
            arms = (lerp(0, 22, cl), lerp(-62, -20, cl), lerp(0, 22, cl), lerp(-62, -20, cl)) if sing else (25, 20, 150, -20)
            actors.append(golu(T, x=1050, y=GY + 20 - bounce, arms=arms, expr="joy" if sing else "happy",
                               look=(0.6, -0.8) if t > tap else (0, 0)))
            if sing:
                fx.append(("notes", 1050, GY - 380, T))
            if t > tap:
                f = (t - tap) / 0.6
                mx0, my0 = TX - 230 * 0.95, GY - 10 - 520 * 0.95
                fx.append(("mango", lerp(mx0, 1110, f), lerp(my0, GY - 330, f * f), t * 400, 1.1))
        else:
            k = t - land
            jump = max(0, math.sin(min(math.pi, k * 4))) * 90 if t > L[2]["start"] - 0.2 else 0
            actors.append(golu(T, x=1050, y=GY + 20 - jump, hold=True, hold_glow=0.8, arms=(30, 20, 150, 30),
                               expr="joy"))
        if t > tap:
            fx.append(("word", "TAPAK!", 1330, GY - 640, t - tap, 100))
    elif sid == 5:
        cam = (1000, 640, 1.75)
        actors.append(ped(T, picked=1, glow=0.8))
        sneaky_t = word_time(L[0], "अब")
        bite = t > 0.5
        expr = "joy" if t < sneaky_t else "sneaky"
        look = (0, 0) if t < sneaky_t else (math.sin(T * 3), 0)
        arm_y = 150 + 10 * math.sin(T * 3)
        actors.append(golu(T, x=1000, hold=True, bitten=bite, expr=expr, look=look,
                           arms=(20, 15, 140 + 6 * math.sin(T * 3), -170)))
        if 0.5 < t < 1.3:
            fx.append(("word", "NOM!", 1150, GY - 470, t - 0.5, 80))
    elif sid == 6:
        cam = (1200, 570, 1.12)
        n = int(clamp((t - 0.4) / (L[0]["dur"] + 0.8)) * 10)
        actors.append(ped(T, picked=1 + n, glow=0.7))
        fx.append(("pile", 1020, GY + 25, n))
        # flying mango
        ph = ((t - 0.4) * 10 / (L[0]["dur"] + 0.8)) % 1
        if n < 10 and t > 0.4:
            k = 1 + n
            mx, my = G.TREE_MANGOES[k % len(G.TREE_MANGOES)]
            x, y = arc((TX + mx * 0.95, GY - 10 + my * 0.95), (1020, GY - 60), ph, 120)
            fx.append(("mango", x, y, ph * 360, 1.1))
        if t < L[1]["start"] - 0.3:
            reach = abs(math.sin(T * 5))
            actors.append(golu(T, x=1210, arms=(30, 10, lerp(120, 170, reach), 0), look=(0.7, -0.7),
                               expr="joy"))
        else:
            k = t - (L[1]["start"] - 0.3)
            f = ease(k / 0.5)
            actors.append(golu(T, x=lerp(1210, 1020, f), y=GY + 20 - 110 * f - 60 * math.sin(f * math.pi), sit=1 if f > 0.9 else 0,
                               arms=(-5, -55, -5, -55) if f > 0.9 else (150, 0, 150, 0), expr="sneaky" if f > 0.9 else "joy"))
    elif sid in (7, 8):
        cam = (860, 640, 1.3) if sid == 7 else (720, 640, 1.25)
        actors.append(ped(T, picked=11, glow=0.5))
        fx.append(("pile", 1020, GY + 25, 10))
        if sid == 7:
            f = ease(t / 1.4)
            px = lerp(-120, 640, f)
            sad = t > L[1]["start"] + 0.3
            actors.append(pinky(T, x=px, step=T * 9 if f < 1 else 0, expr="sad" if sad else "happy",
                                arms=(10, 10, 60, 70) if talking("pinky", T) else (10, 10, 10, 10)))
            if sad:
                fx.append(("tears", px, GY + 25 - 0.82 * 286, T))
            gol_expr = "sneaky"
            head = 0.8 * math.sin(T * 14) if talking("golu", T) else 0
            actors.append(golu(T, x=1020, y=GY - 85, sit=1, arms=(-5, -55, -5, -55), expr=gol_expr, turn=head,
                               headbob=0))
        else:
            hx = lerp(-300, 330, ease(t / 2.2))
            walking = t < 2.2
            sit = L[2]["start"] + 0.8 < t
            bg["heat"] = 1.0
            actors.append(haathi(T, x=hx, step=T * 5 if walking else 0, expr="tired", sit=1 if sit else 0))
            fx.append(("sweat", hx, GY - 380, T))
            actors.append(pinky(T, x=640, expr="sad"))
            head = 0.8 * math.sin(T * 14) if talking("golu", T) else 0
            actors.append(golu(T, x=1020, y=GY - 85, sit=1, arms=(-5, -55, -5, -55), expr="sneaky", turn=head))
    elif sid == 9:
        cam = (1020, 600, 1.55)
        actors.append(ped(T, picked=11, glow=0.3))
        fx.append(("pile", 1020, GY + 25, 9))
        bites = [L[1]["start"] - 0.25, word_time(L[2], "दूसरा") + 0.1, word_time(L[2], "तीसरा") + 0.1]
        last = max([b for b in bites if b <= t], default=None)
        sour = last is not None and t - last < 1.6
        shake = 0.9 * math.sin(T * 22) * max(0, 1 - (t - last) / 1.2) if last is not None else 0
        actors.append(golu(T, x=1020, y=GY - 85, sit=1, hold=True, bitten=last is not None, hold_ripe=0.6,
                           arms=(20, 15, 140, -170), expr="sour" if sour else "worried" if last else "sneaky",
                           turn=shake, tilt=shake * 4))
        for i, b in enumerate(bites):
            fx.append(("word", ["THOO!", "KHATTA!", "CHHEE!"][i], 1180 if i != 1 else 860, GY - 560, t - b, 90))
    elif sid == 10:
        cam = (1250, 560, 1.1)
        f = ease(t / 1.6)
        actors.append(ped(T, picked=11, glow=lerp(0.3, 0.0, f), sad=f, ripe=lerp(1, 0, f)))
        fx.append(("pile", 1020, GY + 25, 9, lerp(1, 0.2, f)))
        actors.append(golu(T, x=1020, y=GY - 85, sit=1, expr="worried", look=(0.7, -0.4)))
        if t > L[1]["start"]:
            fx.append(("word", "?", 1090, GY - 520, min(t - L[1]["start"], 0.9), 130))
    elif sid == 11:
        a, b = L[0]["start"], L[1]["start"]
        if t < b - 0.3:
            f = ease((t - a) / 1.5)
            cam = (lerp(1020, 520, f), lerp(560, 600, f), lerp(1.3, 1.25, f))
        else:
            cam = (1020, 580, 1.45)
        actors.append(ped(T, picked=11, glow=0.0, sad=1, ripe=0))
        fx.append(("pile", 1020, GY + 25, 9, 0.2))
        actors.append(haathi(T, x=330, sit=1, expr="tired"))
        actors.append(pinky(T, x=640, expr="sad"))
        fx.append(("tears", 640, GY + 25 - 0.82 * 286, T))
        actors.append(golu(T, x=1020, y=GY - 85, sit=1, expr="sad", look=(-0.8, 0.3)))
    elif sid == 12:
        cam = (700, 630, 1.25)
        give1 = word_time(L[0], "ये लो")
        give2 = word_time(L[0], "आप भी")
        actors.append(ped(T, picked=11, glow=lerp(0, 0.4, ease((t - give2) / 2)), sad=lerp(1, 0.3, ease((t - give2) / 2)),
                          ripe=lerp(0, 1, ease((t - give2) / 2))))
        fx.append(("pile", 1020, GY + 25, 7))
        gx = lerp(1020, 820, ease(t / 0.7))
        gy = GY + 20 - (0 if t > 0.7 else 120 * math.sin(t / 0.7 * math.pi))
        happy_p = t > give1 + 0.5
        happy_h = t > give2 + 0.5
        hug = t > L[1]["start"] + 0.6
        actors.append(haathi(T, x=330, sit=0 if happy_h else 1, expr="joy" if happy_h else "tired",
                             trunk=0.9 if hug else (0.5 if happy_h else 0), trunk_mango=happy_h and not hug))
        actors.append(pinky(T, x=620, expr="joy" if happy_p else "sad", hold=happy_p, arms=(10, 10, 150, 30) if happy_p else (10, 10, 10, 10)))
        if not happy_p:
            fx.append(("tears", 620, GY + 25 - 0.82 * 286, T))
        actors.append(golu(T, x=gx, y=gy, expr="joy" if hug else "happy", step=T * 10 if t < 0.7 else 0,
                           arms=(40, 20, 100, -10) if talking("golu", T) else (30, 20, 30, 20), hold=t < give1))
        for i, (g0, dst) in enumerate([(give1, (650, GY - 230)), (give2, (470, GY - 300))]):
            if g0 < t < g0 + 0.5:
                x, y = arc((gx + 60, GY - 150), dst, (t - g0) / 0.5, 120)
                fx.append(("mango", x, y, (t - g0) * 500, 1.0))
        if hug:
            fx.append(("hearts", 560, GY - 420, t - L[1]["start"] - 0.6))
    elif sid == 13:
        cam = (lerp(1000, 1100, ease(t / 3)), 560, lerp(1.08, 1.02, t / sc["dur"]))
        g = ease(t / 1.0)
        actors.append(ped(T, glow=lerp(0.4, 1.6, g), sad=0, picked=0))
        fx.append(("rays", TX, GY - 520, T, g))
        actors.append(haathi(T, x=330, expr="joy", trunk=0.6))
        actors.append(pinky(T, x=640, expr="joy", look=(0.5, -1), arms=(150, 10, 150, 10)))
        actors.append(golu(T, x=860, expr="joy", look=(0.6, -1), arms=(165, 5, 165, 5),
                           y=GY + 20 - abs(math.sin(T * 5)) * 30))
        rnd = random.Random(4)
        drops = [word_time(L[0], "धप्प", i) for i in range(3)]
        for i in range(16):
            t0 = 1.0 + i * 0.32
            mx = TX + rnd.uniform(-300, 300) - rnd.uniform(0, 500) * (i % 3 == 0)
            y = fall_y(t - t0, GY - 700, GY + 10 + rnd.uniform(0, 60))
            if t > t0:
                fx.append(("mango", mx, y, rnd.uniform(-40, 40), 1.1))
        for i, dt in enumerate(drops):
            fx.append(("word", "DHAPP!", [1180, 1480, 1780][i], GY - [620, 720, 600][i], t - dt, 100))
    elif sid in (14, 15, 16, 17):
        sunset = 1.0 if sid == 16 else 0.0
        bg["sunset"] = sunset
        actors.append(ped(T, glow=0.9 if sid != 16 else 0.6, picked=3))
        fx.append(("ground_mangoes",))
        beat = abs(math.sin(T * math.pi * 2.0))
        if sid == 14:
            cam = (660, 640, 1.3)
            pj = max(0, math.sin(min(math.pi, (t - L[0]["start"]) * 4))) * 80 if t > L[0]["start"] else 0
            actors.append(haathi(T, x=330, expr="joy", trunk=0.9, trunk_mango=True))
            actors.append(pinky(T, x=620, y=GY + 25 - pj, expr="joy", hold=True, arms=(10, 10, 150, 30), bitten=True))
            actors.append(golu(T, x=880, expr="joy" if not talking("golu", T) else "happy", hold=True, bitten=True,
                               arms=(30, 20, 140, -170)))
            fx.append(("hearts", 600, GY - 450, t))
        elif sid == 15:
            cam = (660, 640, 1.28)
            dance = t > L[0]["start"] + L[0]["dur"]
            b = beat * 40 if dance else 0
            sw = math.sin(T * math.pi * 2.0)
            arms = (lerp(30, 150, (sw + 1) / 2), 10, lerp(150, 30, (sw + 1) / 2), 10) if dance else (30, 20, 150, -10)
            actors.append(haathi(T, x=330, expr="joy", trunk=0.5 + 0.5 * beat if dance else 0.3,
                                 y=GY + 15 - b * 0.4))
            actors.append(pinky(T, x=620, y=GY + 25 - b, expr="joy", arms=arms, tilt=sw * 6 if dance else 0))
            actors.append(golu(T, x=880, y=GY + 20 - b, arms=arms, tilt=-sw * 6 if dance else 0,
                               expr="joy" if not talking("golu", T) else "happy"))
            if dance:
                fx.append(("notes", 620, GY - 420, T))
                fx.append(("notes", 900, GY - 460, T + 1.3))
        elif sid == 16:
            cam = (680, 650, lerp(1.3, 1.4, t / sc["dur"]))
            actors.append(haathi(T, x=420, sit=1, expr="joy"))
            actors.append(pinky(T, x=660, y=GY + 25, sit=1, expr="happy", flip=False))
            actors.append(golu(T, x=860, sit=1, expr="happy"))
            fx.append(("hearts", 760, GY - 380, t))
        else:
            cam = (980, 560, lerp(1.6, 1.75, t / sc["dur"]))
            sub = word_time(L[0], "सब्सक्राइब") - 0.3
            actors.append(golu(T, x=900, arms=wave_arm(T) if t > 0.3 else (14, 12, 14, 12), expr="joy" if talking("golu", T) else "happy"))
            if t > sub:
                fx.append(("subscribe", 1300, 420, t - sub))
    return cam, actors, fx, bg


# ------------------------------------------------------------------ text (Devanagari via PIL/raqm)
_TXT = {}


def text_image(text, size, fill=(255, 255, 255), stroke=(0, 0, 0), sw=8):
    key = (text, size, fill, stroke, sw)
    if key not in _TXT:
        font = ImageFont.truetype(POPPINS, size, layout_engine=ImageFont.Layout.RAQM)
        box = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=font, stroke_width=sw)
        im = Image.new("RGBA", (box[2] - box[0] + 20, box[3] - box[1] + 30), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.text((10 - box[0] + 5, 10 - box[1] + 7), text, font=font, fill=(0, 0, 0, 90), stroke_width=sw,
                stroke_fill=(0, 0, 0, 90))
        dr.text((10 - box[0], 10 - box[1]), text, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)
        arr = np.ascontiguousarray(np.array(im))
        _TXT[key] = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)
    return _TXT[key]


def draw_text(c, text, x, y, size, **kw):
    img = text_image(text, size, **kw)
    c.drawImage(img, x - img.width() / 2, y - img.height() / 2, skia.SamplingOptions(skia.FilterMode.kLinear))


# ------------------------------------------------------------------ fx drawing
def draw_fx(c, f, t_scene):
    kind = f[0]
    if kind == "vine":
        _, ax, ay, px, py = f
        path = skia.Path()
        path.moveTo(ax, ay)
        path.quadTo((ax + px) / 2 + 30, (ay + py) / 2, px, py)
        c.drawPath(path, G.paint("#2f7d2a", stroke=14))
        for k in range(1, 6):
            fx_, fy_ = lerp(ax, px, k / 6), lerp(ay, py, k / 6)
            leaf = skia.Path()
            leaf.moveTo(fx_, fy_)
            leaf.quadTo(fx_ + 30, fy_ - 20, fx_ + 44, fy_ + 4)
            leaf.quadTo(fx_ + 20, fy_ + 12, fx_, fy_)
            c.drawPath(leaf, G.paint("#49b04a"))
    elif kind == "puff":
        G.puff(c, f[1], f[2], f[3])
    elif kind == "word":
        _, txt, x, y, age, size = f
        G.comic_word(c, txt, x, y, size, age)
    elif kind == "dizzy":
        G.dizzy_stars(c, f[1], f[2], f[3])
    elif kind == "mango":
        G.mango(c, f[1], f[2], f[4], f[3])
    elif kind == "pile":
        draw_pile(c, f[1], f[2], f[3], f[4] if len(f) > 4 else 1.0)
    elif kind == "notes":
        _, x, y, T = f
        for k in range(3):
            ph = (T * 0.6 + k / 3) % 1
            G.note(c, x + 120 * math.sin(ph * 6 + k) + (k - 1) * 90, y - ph * 260, 1.1,
                   int(255 * math.sin(ph * math.pi)), ["#8a4dff", "#ff4d8d", "#2fa8ff"][k])
    elif kind == "sparkle_rise":
        _, x, y, T = f
        ph = (T * 0.4) % 1
        G.sparkle(c, x + 30 * math.sin(T * 2), y - ph * 400, 18, int(255 * math.sin(ph * math.pi)))
    elif kind == "tears":
        _, x, y, T = f
        for k in range(2):
            ph = (T * 1.3 + k * 0.5) % 1
            for sd in (-1, 1):
                G.drop(c, x + sd * (40 + 6 * ph), y + 10 + ph * 70, 1.0, alpha=int(255 * (1 - ph)))
    elif kind == "sweat":
        _, x, y, T = f
        ph = (T * 0.9) % 1
        G.drop(c, x + 90, y - 30 + ph * 60, 1.4, alpha=int(255 * (1 - ph)))
        G.drop(c, x - 95, y - 10 + ((ph + 0.5) % 1) * 60, 1.2, alpha=int(255 * (1 - (ph + 0.5) % 1)))
    elif kind == "hearts":
        _, x, y, age = f
        if age < 0:
            return
        for k in range(5):
            ph = (age * 0.45 + k / 5) % 1
            G.heart(c, x + (k - 2) * 90 + 25 * math.sin(age * 2 + k), y - ph * 280, 22 + 6 * k % 3,
                    int(255 * math.sin(ph * math.pi)))
    elif kind == "rays":
        _, x, y, T, g = f
        c.save()
        c.translate(x, y)
        c.rotate(T * 12)
        for k in range(12):
            c.rotate(30)
            path = skia.Path()
            path.moveTo(0, 0)
            path.lineTo(-60, -900)
            path.lineTo(60, -900)
            path.close()
            c.drawPath(path, G.paint("#fff6b0", int(70 * g), blur=12))
        c.restore()
    elif kind == "ground_mangoes":
        rnd = random.Random(21)
        for k in range(9):
            G.mango(c, 1050 + rnd.uniform(0, 800), GY + 15 + rnd.uniform(0, 70), 1.05, rnd.uniform(-60, 60))
    elif kind == "subscribe":
        _, x, y, age = f
        sc = min(1.0, age / 0.25) * (1 + 0.06 * math.sin(age * 6))
        c.save()
        c.translate(x, y)
        c.scale(sc, sc)
        G.rrect(c, -215, -58, 215, 58, 58, "#ff2d2d")
        font = G.Fonts.get(56)
        w = font.measureText("SUBSCRIBE")
        c.drawString("SUBSCRIBE", -w / 2 + 32, 20, font, G.paint("#ffffff"))
        # little bell
        bell = skia.Path()
        bell.moveTo(-190, 20)
        bell.quadTo(-190, -24, -168, -24)
        bell.quadTo(-146, -24, -146, 20)
        bell.close()
        c.drawPath(bell, G.paint("#ffd54a"))
        c.drawCircle(-168, 26, 7, G.paint("#ffd54a"))
        c.restore()
        if age > 0.6:
            hand_t = (age - 0.6) % 2.0
            G.ball(c, x + 60 - 20 * min(1, hand_t * 3), y + 60 - 20 * min(1, hand_t * 3), 22, "#f2c9a0")


# ------------------------------------------------------------------ cards
def card(c, T, outro=False):
    t = T - (TL["outro_start"] if outro else 0)
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), 1200,
                                               [G.rgb("#fff3a8"), G.rgb("#ffb72b"), G.rgb("#ff7a2b")], [0, 0.55, 1]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
    c.save()
    c.translate(W / 2, H / 2)
    c.rotate(t * 10)
    for k in range(16):
        c.rotate(360 / 16)
        path = skia.Path()
        path.moveTo(0, 0)
        path.lineTo(-90, -1400)
        path.lineTo(90, -1400)
        path.close()
        c.drawPath(path, G.paint("#ffffff", 45))
    c.restore()
    rnd = random.Random(2)
    for k in range(10):
        x = rnd.uniform(80, W - 80)
        y = (rnd.uniform(0, H) + t * rnd.uniform(60, 140)) % (H + 100) - 50
        G.mango(c, x, y, 1.4, t * 60 + k * 30)
    pop = ease(t / 0.5)
    if not outro:
        G.monkey(c, dict(x=470, y=1010, s=1.65 * (0.6 + 0.4 * pop), cfg=G.GOLU, t=T, arms=wave_arm(T), expr="joy",
                         mouth=0, blink=blink(T, 1)))
        c.save()
        c.translate(1210, 300)
        c.scale(pop, pop)
        draw_text(c, "Golu Bandar Kids", 0, 0, 120, fill=(255, 255, 255), stroke=(214, 51, 29), sw=12)
        c.restore()
        if t > 0.6:
            a = ease((t - 0.6) / 0.5)
            c.save()
            c.translate(1210, 560)
            c.scale(a, a)
            draw_text(c, "गोलू और", 0, -70, 100, fill=(255, 255, 255), stroke=(43, 110, 214), sw=10)
            draw_text(c, "जादुई आम का पेड़", 0, 80, 110, fill=(255, 236, 80), stroke=(43, 110, 214), sw=10)
            c.restore()
    else:
        G.elephant(c, dict(x=360, y=1040, s=1.0, t=T, expr="joy", trunk=0.6 + 0.3 * math.sin(T * 3), blink=blink(T, 3)))
        G.monkey(c, dict(x=1500, y=1040, s=1.25, cfg=G.GOLU, t=T, arms=wave_arm(T), expr="joy", blink=blink(T, 1)))
        G.monkey(c, dict(x=1740, y=1040, s=1.0, cfg=G.PINKY, t=T + 1, arms=wave_arm(T + 0.3), expr="joy",
                         blink=blink(T, 2), flip=True))
        c.save()
        c.translate(960, 300)
        c.scale(pop, pop)
        draw_text(c, "फिर मिलेंगे!", 0, 0, 130, fill=(255, 255, 255), stroke=(214, 51, 29), sw=12)
        c.restore()
        if t > 0.5:
            c.save()
            c.translate(960, 560)
            c.scale(1.4, 1.4)
            draw_fx(c, ("subscribe", 0, 0, t - 0.5), t)
            c.restore()
            draw_text(c, "Golu Bandar Kids", 960, 720, 70, fill=(255, 255, 255), stroke=(43, 110, 214), sw=8)


# ------------------------------------------------------------------ frame
def render_frame(c, n):
    T = n / FPS
    if T < INTRO:
        card(c, T)
        fade = 1 - clamp((INTRO - T) / 0.3)
        if fade > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), G.paint("#ffffff", int(255 * fade * 0.9)))
        return
    if T >= TL["outro_start"]:
        card(c, T, outro=True)
        fi = 1 - clamp((T - TL["outro_start"]) / 0.4)
        if fi > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), G.paint("#ffffff", int(255 * fi * 0.9)))
        fo = clamp((T - (TL["total"] - 0.6)) / 0.6)
        if fo > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), G.paint("#000000", int(255 * fo)))
        return
    sc = next(s for s in TL["scenes"] if s["start"] <= T < s["start"] + s["dur"])
    t = T - sc["start"]
    cam, actors, fx, bg = scene_state(sc["id"], t, T, sc)
    G.background(c, T, cam, **bg)
    c.save()
    cx, cy, z = cam
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-cx, -cy)
    order = {"tree": 0, "elephant": 1, "monkey": 2}
    front_fx = []
    for f in fx:
        if f[0] in ("pile", "ground_mangoes", "rays", "vine"):
            draw_fx(c, f, t) if f[0] == "rays" else None
    for kind, st in sorted(actors, key=lambda a: order[a[0]]):
        if kind == "tree":
            G.tree(c, st)
            for f in fx:
                if f[0] in ("pile", "ground_mangoes", "vine"):
                    draw_fx(c, f, t)
        elif kind == "elephant":
            G.elephant(c, st)
        else:
            G.monkey(c, st)
    for f in fx:
        if f[0] not in ("pile", "ground_mangoes", "rays", "vine", "subscribe"):
            front_fx.append(f)
    for f in front_fx:
        draw_fx(c, f, t)
    G.bushes(c, bg["sunset"])
    c.restore()
    for f in fx:
        if f[0] == "subscribe":
            draw_fx(c, f, t)
    # soft cut: brief white-ish dip at scene start
    a = 1 - clamp(t / 0.25)
    if a > 0 and sc["id"] != 1:
        c.drawRect(skia.Rect.MakeWH(W, H), G.paint("#ffffff", int(110 * a)))


def frame_rgb(n):
    s = skia.Surface(W, H)
    c = s.getCanvas()
    render_frame(c, n)
    return s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]


def render_range(args):
    d, a, b, out = args
    load(d)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(a, b):
        p.stdin.write(np.ascontiguousarray(frame_rgb(n)).tobytes())
    p.stdin.close()
    p.wait()
    return out


# ------------------------------------------------------------------ audio
def synth_sfx(name):
    t = np.arange(int(SR * 0.8)) / SR
    if name == "thud":
        f = 160 * np.exp(-t * 6) + 50
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
        x += 0.3 * np.random.default_rng(1).normal(size=len(t)) * np.exp(-t * 30)
    elif name == "pop":
        t = t[: int(SR * 0.25)]
        f = 500 + 900 * t / 0.25
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
    elif name == "chime":
        t = np.arange(int(SR * 2.0)) / SR
        x = sum(np.sin(2 * np.pi * fr * t) * np.exp(-(t - i * 0.09).clip(0) * 3) * (t > i * 0.09)
                for i, fr in enumerate([1046.5, 1318.5, 1568.0, 2093.0]))
        x *= 0.35
    elif name == "boing":
        t = np.arange(int(SR * 0.6)) / SR
        f = 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    elif name == "pluck":
        t = t[: int(SR * 0.3)]
        x = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 20)
    else:
        x = np.zeros(10)
    return (x / (np.abs(x).max() + 1e-9) * 0.6).astype(np.float32)


def sfx_events():
    ev = []
    for sc in TL["scenes"]:
        s0, L = sc["start"], sc["lines"]
        sid = sc["id"]
        if sid == 2:
            ev += [(s0 + word_time(L[0], "धप्प"), "thud"), (s0 + word_time(L[0], "धप्प") + 1.0, "chime")]
        if sid == 3:
            ev.append((s0 + 0.2, "chime"))
        if sid == 4:
            ev += [(s0 + L[1]["start"] + 0.1, "pop"), (s0 + L[1]["start"] + 0.7, "boing")]
        if sid == 6:
            for k in range(10):
                ev.append((s0 + 0.4 + (k + 1) * (L[0]["dur"] + 0.8) / 10, "pluck"))
        if sid == 9:
            for b in [L[1]["start"] - 0.25, word_time(L[2], "दूसरा") + 0.1, word_time(L[2], "तीसरा") + 0.1]:
                ev.append((s0 + b, "boing"))
        if sid == 12:
            ev.append((s0 + word_time(L[0], "ये लो"), "pop"))
            ev.append((s0 + word_time(L[0], "आप भी"), "pop"))
        if sid == 13:
            ev.append((s0 + 0.1, "chime"))
            for i in range(3):
                ev.append((s0 + word_time(L[0], "धप्प", i), "thud"))
            for i in range(16):
                ev.append((s0 + 1.0 + i * 0.32 + 0.55, "pluck"))
        if sid == 17:
            ev.append((s0 + word_time(L[0], "सब्सक्राइब") - 0.3, "pop"))
    ev.append((TL["outro_start"] + 0.5, "pop"))
    ev.append((0.3, "chime"))
    return ev


def build_audio(d, music_path):
    n = int(TL["total"] * SR) + SR
    voice = np.zeros(n, np.float32)
    for sc in TL["scenes"]:
        for ln in sc["lines"]:
            a = read_wav(ln["file"])
            i = int(ln["abs"] * SR)
            voice[i:i + len(a)] += a * 0.95
    sfx = np.zeros(n, np.float32)
    cache = {}
    for tm, name in sfx_events():
        x = cache.setdefault(name, synth_sfx(name))
        i = int(tm * SR)
        sfx[i:i + len(x)] += x[: max(0, n - i)] * 0.45
    m = read_wav(music_path)
    music = np.zeros(n, np.float32)
    music[: min(n, len(m))] = m[:n]
    # duck music under speech
    act = np.zeros(n, np.float32)
    for sc in TL["scenes"]:
        for ln in sc["lines"]:
            i, j = int((ln["abs"] - 0.15) * SR), int((ln["abs"] + ln["dur"] + 0.2) * SR)
            act[i:j] = 1
    k = int(0.25 * SR)
    act = np.convolve(act, np.ones(k) / k, mode="same")
    gain = 0.55 - 0.33 * act
    fade = np.ones(n, np.float32)
    end = int(TL["total"] * SR)
    fade[end - int(1.5 * SR):end] = np.linspace(1, 0, int(1.5 * SR))
    fade[end:] = 0
    mix = voice + sfx + music * gain * fade
    mix = mix / max(1.0, np.abs(mix).max() / 0.97)
    out = os.path.join(d, "build", "audio.wav")
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    return out


def main():
    d = sys.argv[1].rstrip("/")
    load(d)
    os.makedirs(os.path.join(d, "build"), exist_ok=True)
    json.dump(TL, open(os.path.join(d, "timeline.json"), "w"), indent=1, ensure_ascii=False)
    nframes = int(TL["total"] * FPS)
    print(f"total {TL['total']:.1f}s, {nframes} frames")
    if "--frames" in sys.argv:
        os.makedirs(os.path.join(d, "check"), exist_ok=True)
        spec = sys.argv[sys.argv.index("--frames") + 1]
        if spec == "scenes":
            ns = [int(FPS * 2)] + [int((s["start"] + s["dur"] * 0.6) * FPS) for s in TL["scenes"]] + \
                 [int((TL["outro_start"] + 2) * FPS)]
        else:
            ns = [int(x) for x in spec.split(",")]
        for n in ns:
            Image.fromarray(frame_rgb(n)).save(os.path.join(d, "check", f"f{n:05d}.jpg"), quality=85)
            print("frame", n, f"{n / FPS:.1f}s")
        return
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
    step = math.ceil(nframes / jobs)
    parts = [(d, i, min(nframes, i + step), os.path.join(d, "build", f"part{k}.mp4"))
             for k, i in enumerate(range(0, nframes, step))]
    with Pool(len(parts)) as pool:
        outs = pool.map(render_range, parts)
    lst = os.path.join(d, "build", "parts.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(o)}'\n" for o in outs))
    vid = os.path.join(d, "build", "video_noaudio.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid],
                   check=True)
    music = os.path.join(d, "build", "music.wav")
    subprocess.run([sys.executable, os.path.join(HERE, "kids_music.py"), music, str(TL["total"] + 1)], check=True)
    aud = build_audio(d, music)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", aud, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", os.path.join(d, "video.mp4")], check=True)
    print("done", os.path.join(d, "video.mp4"))


if __name__ == "__main__":
    main()
