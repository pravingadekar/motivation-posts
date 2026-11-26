"""Seamless looping background animation (soft floating dust / bokeh lights) on black, for screen-blending
over long-form videos.  python tools/bg_particles.py OUT.mp4 [seconds=12]

Every particle drifts upward a whole number of screen heights per loop and sways with a whole number of
cycles, so the last frame flows into the first. Original, procedural: no copyright issues.
"""
import subprocess
import sys

import numpy as np

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001
    FFMPEG = "ffmpeg"

W, H, FPS = 960, 540, 30          # rendered at half size, scaled up (soft anyway)


def main(out, seconds=12.0, n=95, seed=7):
    rng = np.random.default_rng(seed)
    frames = int(seconds * FPS)
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    laps = rng.integers(1, 3, n)                    # screen heights per loop (speed)
    sway_amp, sway_cyc = rng.uniform(5, 25, n), rng.integers(1, 3, n)
    size = rng.uniform(2.0, 9.0, n)
    bright = rng.uniform(0.45, 1.0, n)
    tw_cyc, tw_ph = rng.integers(1, 4, n), rng.uniform(0, 2 * np.pi, n)
    yy, xx = np.mgrid[0:H, 0:W]
    proc = subprocess.Popen([FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-vf", "scale=1920:1080:flags=bicubic,format=yuv420p",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18", out], stdin=subprocess.PIPE)
    for f in range(frames):
        p = f / frames
        img = np.zeros((H, W), np.float32)
        ys = (y0 - laps * H * p) % H
        xs = (x0 + sway_amp * np.sin(2 * np.pi * sway_cyc * p + y0)) % W
        tw = 0.6 + 0.4 * np.sin(2 * np.pi * tw_cyc * p + tw_ph)
        for x, y, s, b in zip(xs, ys, size, bright * tw):
            x1, x2 = int(max(0, x - 4 * s)), int(min(W, x + 4 * s))
            y1, y2 = int(max(0, y - 4 * s)), int(min(H, y + 4 * s))
            if x2 <= x1 or y2 <= y1:
                continue
            d2 = (xx[y1:y2, x1:x2] - x) ** 2 + (yy[y1:y2, x1:x2] - y) ** 2
            img[y1:y2, x1:x2] += b * np.exp(-d2 / (2 * s * s))
        img = np.clip(img, 0, 1)
        rgb = np.stack([img * 255, img * 245, img * 225], -1).astype(np.uint8)   # slightly warm white
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 12.0)
