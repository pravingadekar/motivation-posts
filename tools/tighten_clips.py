"""Tighten Veo talk clips: drop dead air at the start/end, shorten long pauses, speed up a little.

Usage: python tools/tighten_clips.py daily/D [--speed 1.08] [--max-gap 0.22] [--keep-gap 0.16]
- Originals are moved once to daily/D/clips_orig/ (re-runs always start from them).
- Speech is found from audio loudness (20 ms frames, threshold = quiet floor + 10 dB), so it works even
  when Whisper misses words. Pauses longer than --max-gap are cut down to --keep-gap (a jump cut on the
  locked close-up; the HyperFrames punch-ins hide it). Each shot keeps 0.08 s before the first word and
  0.35 s after the last (0.7 s on the last shot for the closing smile). Video and audio are sped up together
  (setpts + atempo), so lip-sync stays. Writes daily/D/clips/shotN.mp4 and prints old -> new lengths.
Why: the user said (19 Nov 2026) the host "slow bolti hai aur pause zyada leti hai".
"""
import argparse, shutil, subprocess, sys
from pathlib import Path
import numpy as np

SR = 16000
HOP = 320  # 20 ms


def speech_regions(path):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True).stdout
    a = np.frombuffer(b, np.float32)
    n = len(a) // HOP
    rms = np.sqrt(np.mean(a[:n * HOP].reshape(n, HOP) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = max(np.percentile(db, 10) + 10, -45)
    on = db > thr
    # close tiny holes (<120 ms) and drop blips (<80 ms)
    idx = np.flatnonzero(on)
    regs = []
    for i in idx:
        if regs and i - regs[-1][1] <= 6:
            regs[-1][1] = i
        else:
            regs.append([i, i])
    regs = [(s * 0.02, (e + 1) * 0.02) for s, e in regs if (e - s + 1) >= 4]
    d = len(a) / SR
    # Veo's last ~0.5 s is often a blur/dissolve into another scene: never use it
    regs = [(s, min(e, d - 0.6)) for s, e in regs if s < d - 0.6]
    # a SHORT sound more than 1 s after the speech (breath, mic bump) is not part of the line;
    # but if a lot of sound follows (> 0.6 s), it is the next sentence after a long pause: keep it
    # (24 Nov 2026: "...सब चुप। <1 s pause> वो चुप्पी..." lost its second sentence)
    out = regs[:1]
    for k, (s, e) in enumerate(regs[1:], 1):
        if s - out[-1][1] > 1.0 and sum(b - a for a, b in regs[k:]) < 0.6:
            break
        out.append((s, e))
    return out, d


def keep_segments(regs, dur, last, max_gap, keep_gap):
    if not regs:
        return [(0.0, dur)]
    pad_end = 0.7 if last else 0.35
    segs = [[max(0.0, regs[0][0] - 0.08), regs[0][1]]]
    for s, e in regs[1:]:
        gap = s - segs[-1][1]
        if gap > max_gap:
            half = keep_gap / 2
            segs[-1][1] += half
            segs.append([s - half, e])
        else:
            segs[-1][1] = e
    segs[-1][1] = min(dur - 0.6, segs[-1][1] + pad_end)
    return [(round(a, 3), round(b, 3)) for a, b in segs]


def render(src, dst, segs, speed):
    parts, labels = [], ""
    for i, (a, b) in enumerate(segs):
        fd = min(0.015, (b - a) / 3)
        parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];"
                     f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d={fd},afade=t=out:st={b - a - fd:.3f}:d={fd}[a{i}];")
        labels += f"[v{i}][a{i}]"
    fc = "".join(parts) + f"{labels}concat=n={len(segs)}:v=1:a=1[v][a];[v]setpts=PTS/{speed}[vo];[a]atempo={speed}[ao]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[vo]", "-map", "[ao]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", "24", "-c:a", "aac", "-b:a", "192k",
                    str(dst)], check=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--speed", type=float, default=1.08)
    ap.add_argument("--max-gap", type=float, default=0.22)
    ap.add_argument("--keep-gap", type=float, default=0.16)
    a = ap.parse_args()
    day = Path(a.day)
    clips, orig = day / "clips", day / "clips_orig"
    if not orig.exists():
        shutil.copytree(clips, orig)
    shots = sorted(orig.glob("shot*.mp4"))
    if not shots:
        sys.exit("no clips")
    for k, src in enumerate(shots):
        regs, d = speech_regions(src)
        segs = keep_segments(regs, d, k == len(shots) - 1, a.max_gap, a.keep_gap)
        dst = clips / src.name
        render(src, dst, segs, a.speed)
        print(f"{src.name}: {d:.2f}s -> {dur(dst):.2f}s  keep={segs}")


if __name__ == "__main__":
    main()
