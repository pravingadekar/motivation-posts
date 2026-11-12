"""Original, copyright-free cheerful kids background loop (ukulele-like plucks, soft bass, light shaker).

python tools/kids_music.py OUT.wav SECONDS   (48 kHz mono, numpy)
"""
import sys
import wave

import numpy as np

SR = 48000
BPM = 104
BEAT = 60 / BPM
# C - G - Am - F  (bright, simple)
CHORDS = [[261.63, 329.63, 392.00], [246.94, 293.66, 392.00], [220.00, 261.63, 329.63], [220.00, 261.63, 349.23]]
BASS = [130.81, 98.00, 110.00, 87.31]
MELODY = [  # (beat offset in bar, semitone from C5, length beats) per bar, cycles
    [(0, 4, 1), (1, 7, 1), (2, 9, 0.5), (2.5, 7, 0.5), (3, 4, 1)],
    [(0, 2, 1), (1, 7, 1), (2, 11, 1), (3, 7, 1)],
    [(0, 0, 1), (1, 4, 0.5), (1.5, 7, 0.5), (2, 9, 1.5)],
    [(0, 5, 1), (1, 9, 1), (2, 7, 1), (3, 5, 0.5), (3.5, 4, 0.5)],
]


def pluck(f, dur, amp):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 5.5) * np.minimum(1, t / 0.004)
    return amp * env * (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) + 0.18 * np.sin(6 * np.pi * f * t))


def render(seconds):
    n = int(SR * seconds) + SR
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)
    bar_len = 4 * BEAT
    t0, bar = 0.0, 0
    while t0 < seconds:
        ch, bs, mel = CHORDS[bar % 4], BASS[bar % 4], MELODY[bar % 4]
        for k in range(8):  # strum pattern on eighths
            s = int((t0 + k * BEAT / 2) * SR)
            amp = 0.10 if k % 2 == 0 else 0.06
            for j, f in enumerate(ch):
                x = pluck(f, 0.9, amp)
                a = s + j * 120
                out[a:a + len(x)] += x[: max(0, n - a)]
        for k in (0, 2):
            s = int((t0 + k * BEAT) * SR)
            t = np.arange(int(SR * BEAT * 1.8)) / SR
            x = 0.16 * np.sin(2 * np.pi * bs * t) * np.exp(-t * 2.2) * np.minimum(1, t / 0.01)
            out[s:s + len(x)] += x[: max(0, n - s)]
        if bar >= 4 and (bar // 8) % 2 == 0:  # melody comes and goes
            for off, semi, ln in mel:
                f = 523.25 * 2 ** (semi / 12)
                s = int((t0 + off * BEAT) * SR)
                x = pluck(f, ln * BEAT + 0.3, 0.09) * 0.9
                out[s:s + len(x)] += x[: max(0, n - s)]
        for k in range(8):  # shaker
            s = int((t0 + k * BEAT / 2 + BEAT / 4) * SR)
            ln = int(0.05 * SR)
            x = rng.normal(size=ln) * np.exp(-np.arange(ln) / SR * 80) * 0.025
            out[s:s + ln] += x[: max(0, n - s)]
        t0 += bar_len
        bar += 1
    # simple low-pass smoothing for warmth
    out = np.convolve(out, np.ones(4) / 4, mode="same")
    out[:SR] *= np.linspace(0, 1, SR)
    return out / (np.abs(out).max() + 1e-9) * 0.8


def main(path, seconds):
    x = render(seconds)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print("music", path, f"{seconds:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
