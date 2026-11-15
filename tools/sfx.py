"""Small original sound effects + audio decode helper (numpy, 44.1 kHz mono floats)."""
import subprocess

import numpy as np

SR = 44100


def decode(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def pop(dur=0.09, f0=900):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * (f0 + 600 * t / dur) * t) * np.exp(-t * 45) * 0.35


def whoosh(dur=0.5):
    n = int(dur * SR)
    noise = np.convolve(np.random.default_rng(3).standard_normal(n), np.ones(40) / 40, "same")
    return noise * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.5


def ding():
    t = np.arange(int(0.6 * SR)) / SR
    return (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 1980 * t)) * np.exp(-t * 7) * 0.18
