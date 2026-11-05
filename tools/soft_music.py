"""Original, copyright-free soft emotional background track (slow piano-like arpeggio over a warm pad).

Pure stdlib. python tools/soft_music.py OUT.wav SECONDS
"""
import array
import math
import random
import sys
import wave

SR = 44100
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # A minor - F - C - G, a common emotional progression
    [220.00, 261.63, 329.63, 440.00],
    [174.61, 220.00, 261.63, 349.23],
    [196.00, 261.63, 329.63, 392.00],
    [196.00, 246.94, 293.66, 392.00],
]
ARP = [0, 1, 2, 3, 2, 1, 2, 3]   # eighth notes per bar


def render(length):
    n = int(length * SR) + 1
    out = [0.0] * n
    rnd = random.Random(11)
    tp = 2 * math.pi
    t0, bar = 0.0, 0
    while t0 < length:
        chord = CHORDS[bar % len(CHORDS)]
        # pad: soft sines with slow attack/release across the bar
        s, e = int(t0 * SR), min(n, int((t0 + BAR) * SR))
        for f in chord[:3]:
            f2 = f / 2
            for i in range(s, e):
                x = (i - s) / SR
                env = min(1.0, x / 0.8) * min(1.0, (BAR - x) / 0.8)
                out[i] += 0.05 * env * math.sin(tp * f2 * x)
        # piano-ish arpeggio: decaying tone with two harmonics
        for k, idx in enumerate(ARP):
            ns = t0 + k * BEAT / 2
            f = chord[idx] * 2
            a = int(ns * SR)
            b = min(n, a + int(1.6 * SR))
            vel = 0.10 + 0.03 * rnd.random()
            for i in range(a, b):
                x = (i - a) / SR
                env = math.exp(-3.2 * x) * min(1.0, x / 0.005)
                out[i] += vel * env * (math.sin(tp * f * x) + 0.35 * math.sin(tp * 2 * f * x)
                                       + 0.12 * math.sin(tp * 3 * f * x))
        t0 += BAR
        bar += 1
    peak = max(1e-9, max(abs(v) for v in out))
    fade = int(1.5 * SR)
    for i in range(n):
        g = min(1.0, i / (0.5 * SR), (n - i) / fade)
        out[i] = out[i] / peak * 0.8 * g
    return out


def main(path, length):
    data = render(float(length))
    pcm = array.array("h", (int(v * 32767) for v in data))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
