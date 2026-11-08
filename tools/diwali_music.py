"""Original, copyright-free festive Diwali tune (santoor-like pluck melody, dhol/tabla groove, bells, tanpura drone).

Composed note by note here, so no licence or credit is needed.   python tools/diwali_music.py OUT.wav
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 112
BEAT = 60 / BPM
SA = 293.66                      # D4 = Sa
# (semitones from Sa or None for rest, beats). 44 beats = 11 bars.
INTRO = [(0, 1), (4, 1), (7, 1), (12, 1)]
A = [(7, .5), (7, .5), (9, .5), (7, .5), (4, 1), (2, .5), (4, .5),
     (7, 1.5), (4, .5), (2, 1), (0, 1)]
B = [(4, .5), (7, .5), (9, .5), (12, .5), (14, 1), (12, 1),
     (9, .5), (7, .5), (4, .5), (2, .5), (4, 2)]
C = [(7, .5), (9, .5), (12, 1), (9, .5), (7, .5), (4, 1),
     (2, .5), (4, .5), (2, .5), (0, .5), (0, 2)]
OUTRO = [(12, .5), (9, .5), (7, .5), (9, .5), (12, 2), (None, 4)]
MELODY = INTRO + A + B + A + C + OUTRO
BEATS = sum(d for _, d in MELODY)
LENGTH = BEATS * BEAT
# groove on the 8th-note grid of one bar: D = deep dhol, n = bright tabla "na", t = soft tap
GROOVE = "D.nD n.Dn"


def hz(semi):
    return SA * 2 ** (semi / 12)


def add(out, start, sig):
    a = int(start * SR)
    if a >= len(out):
        return
    b = min(len(out), a + len(sig))
    out[a:b] += sig[:b - a]


def pluck(f, dur, vel):
    """Santoor-like: bright partials with fast decay and a quick double strike."""
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, amp in enumerate([1, .55, .35, .22, .12, .07], start=1):
        s += amp * np.sin(2 * np.pi * f * k * 1.0015 ** (k - 1) * t) * np.exp(-t * (2.6 + 1.6 * k))
    s *= np.minimum(1, t / .003)
    rep = np.zeros(n)
    d = int(.075 * SR)
    rep[d:] = .45 * s[:-d]
    return vel * (s + rep)


def flute(f, dur):
    n = int((dur + .25) * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / .06) * np.clip((dur + .25 - t) / .25, 0, 1)
    vib = 1 + .004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / .3)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    return env * (np.sin(ph) + .18 * np.sin(2 * ph) + .06 * np.sin(3 * ph))


def dhol(t0, out, rnd):
    n = int(.45 * SR)
    t = np.arange(n) / SR
    f = 62 + 70 * np.exp(-t * 28)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    slap = rnd.standard_normal(n) * np.exp(-t * 90) * .25
    add(out, t0, .9 * boom + slap)


def tabla_na(t0, out, rnd, vel=1.0):
    n = int(.3 * SR)
    t = np.arange(n) / SR
    ring = np.sin(2 * np.pi * 740 * t) * np.exp(-t * 16) + .4 * np.sin(2 * np.pi * 1480 * t) * np.exp(-t * 26)
    click = rnd.standard_normal(n) * np.exp(-t * 160) * .5
    add(out, t0, vel * .38 * (ring + click))


def bell(t0, out, f=2349.3, vel=.22):
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dcy)
            for r, a, dcy in [(1, 1, 1.6), (2.76, .5, 2.8), (5.4, .25, 4.5), (8.93, .12, 6)])
    add(out, t0, vel * s * np.minimum(1, t / .002))


def sparkle(t0, out, rnd, vel=.07):
    """soft firework crackle under the music"""
    n = int(1.1 * SR)
    t = np.arange(n) / SR
    s = rnd.standard_normal(n) * (rnd.random(n) < .02) * np.exp(-t * 3)
    s = np.convolve(s, np.ones(6) / 6, mode="same")
    add(out, t0, vel * 6 * s)


def render():
    rnd = np.random.default_rng(8)
    n = int((LENGTH + 1.5) * SR)
    mus = np.zeros(n)
    drm = np.zeros(n)
    # tanpura drone: Pa - Sa' - Sa' - Sa (low), re-plucked every bar
    for bar in range(int(BEATS // 4)):
        for k, semi in enumerate([-5, 0, 0, -12]):
            add(mus, bar * 4 * BEAT + k * BEAT, .22 * pluck(hz(semi), 3.5, .5) * .6)
    # melody: santoor pluck + soft bansuri an octave up from the first hook on
    t = 0.0
    for semi, d in MELODY:
        if semi is not None:
            add(mus, t, pluck(hz(semi), d, .42))
            if t >= 4 * BEAT:
                add(mus, t, .10 * flute(hz(semi + 12), d * BEAT))
        t += d * BEAT
    # drums from bar 2, with a small fill before each new phrase
    bars = int(BEATS // 4)
    for bar in range(1, bars - 1):
        for k, ch in enumerate(GROOVE.replace(" ", "")):
            tt = (bar * 4 + k * .5) * BEAT
            if ch == "D":
                dhol(tt, drm, rnd)
            elif ch == "n":
                tabla_na(tt, drm, rnd)
        if bar % 2 == 0:
            for j in range(4):
                tabla_na((bar * 4 + 3 + j * .25) * BEAT, drm, rnd, .6 + .1 * j)
    dhol((bars - 1) * 4 * BEAT, drm, rnd)
    # bells and sparkles on every phrase start (the video bursts fireworks here)
    for b in BURST_BEATS:
        bell(b * BEAT, mus)
        sparkle(b * BEAT + .35, mus, rnd)
    out = mus + .8 * drm
    out /= max(1e-9, np.abs(out).max())
    out = np.tanh(out * 1.4) / np.tanh(1.4)          # gentle glue
    fade_in = np.minimum(1, np.arange(n) / (.15 * SR))
    end = int(LENGTH * SR)
    tail = np.ones(n)
    tail[end:] = np.linspace(1, 0, n - end)
    return .85 * out * fade_in * tail


BURST_BEATS = [4, 8, 12, 16, 20, 24, 28, 32, 36, 38, 40]


def main(path):
    data = render()
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{path}: {len(data) / SR:.1f}s, {BEATS} beats at {BPM} BPM")


if __name__ == "__main__":
    main(sys.argv[1])
