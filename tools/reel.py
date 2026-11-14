"""Daily AI podcast motivation reel: prompts -> Gemini Omni clips (lip-synced Hindi speech) -> captioned 9:16 reel.

    python tools/reel.py prompts daily/DATE      # script.json -> prompts/shotN.txt (validates line lengths)
    python tools/reel.py clips   daily/DATE      # generate missing clips/shotN.mp4 via tools/genai.py (GEMINI_API_KEY)
    python tools/reel.py build   daily/DATE      # clips -> reel.mp4 + check/*.jpg frames to look at

script.json:
{
  "date": "YYYY-MM-DD", "topic": "...",
  "hook": "short on-screen hook, Hinglish, max 7 words",
  "emotion": "calm and intense" (optional),
  "shots": [ {"dialogue": "Hinglish line, *key* words in stars", "dialogue_hi": "same line in Devanagari (spoken)",
              "camera": "optional camera note"}, ... ]
}
Dialogue is spoken exactly (stars removed); the same text with stars becomes the burned-in captions.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import soft_music  # noqa: E402

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001
    FFMPEG = "ffmpeg"

W, H, FPS = 1080, 1920, 30
HOST = os.path.join(ROOT, "character", "host_natural_v2.png")  # natural look, approved 14 Nov 2026
HANDLE = "@ai__wala_motivational_guru"
MAX_WORDS = 22          # per 10-second clip
MUSIC_VOL = 0.17        # soft background music under the voice (user asked for a bit more, 5 Nov)
RES = "720p"
# Natural "girl next door" look (user, 14 Nov 2026): ONE locked close-up for all 3 shots, start frame
# character/host_natural_v2.png, so the reel feels like one phone-recorded take.
CAMERAS = [
    "locked close-up, same framing as the start frame, very slight natural handheld feel. No cuts, no zoom.",
]
PROMPT = """Vertical 9:16 photorealistic video that looks like a real phone-recorded Hindi talk reel. The young Indian woman from <IMAGE_REF_0> (exactly the same face, hairstyle, kurta, earrings and cozy home background) sits close to the camera and talks to the viewer, with the black foam microphone at the bottom-left.
Camera: {camera}
She speaks in Hindi, {emotion}, with clear natural lip movement matching every word: "{line}"
Voice: her own natural speaking voice, a young North Indian woman in her early twenties, casual everyday Hindi like recording a voice note for her best friend on her phone. Soft, slightly slow, a gentle smile in her voice, small natural pauses and a light breath between phrases. Not an announcer, not a speech, not dramatic, not sing-song, not robotic. Same voice in every clip.
Acting: calm, kind eye contact, normal blinking, small natural head nods, minimal hand movement, no exaggerated mouth or eyebrow movement.
Audio: only her voice and a very faint quiet-room tone. No music, no sound effects.
Look: keep the soft warm indoor light, muted natural colours and real skin texture of the start frame.
She finishes the whole line, then holds a soft smile for about half a second.
IMPORTANT: absolutely no captions, subtitles or on-screen text of any kind, no logos, no writing anywhere. Clean video frame only."""


def load(day):
    with open(os.path.join(day, "script.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def spoken(text):
    return re.sub(r"\s+", " ", text.replace("*", "")).strip()


def cmd_prompts(day):
    s = load(day)
    os.makedirs(os.path.join(day, "prompts"), exist_ok=True)
    for i, shot in enumerate(s["shots"], start=1):
        # Veo pronounces Hindi far more naturally from Devanagari than from Roman Hinglish,
        # so speak "dialogue_hi" when it is given; the Roman "dialogue" stays for the captions.
        line = spoken(shot.get("dialogue_hi") or shot["dialogue"])
        n = len(line.split())
        if n > MAX_WORDS:
            sys.exit(f"shot{i}: {n} words, max {MAX_WORDS}; shorten the line")
        if '"' in line:
            sys.exit(f"shot{i}: no double quotes inside dialogue")
        p = PROMPT.format(camera=shot.get("camera") or CAMERAS[(i - 1) % len(CAMERAS)],
                          emotion=s.get("emotion", "softly and warmly, like talking to a close friend"), line=line)
        with open(os.path.join(day, "prompts", f"shot{i}.txt"), "w", encoding="utf-8") as f:
            f.write(p + "\n")
    print(f"wrote {len(s['shots'])} prompts")


def cmd_clips(day):
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set")
    if not os.path.exists(HOST):
        sys.exit("character/host.png missing")
    s = load(day)
    os.makedirs(os.path.join(day, "clips"), exist_ok=True)
    for i in range(1, len(s["shots"]) + 1):
        out = os.path.join(day, "clips", f"shot{i}.mp4")
        if os.path.exists(out):
            print("exists", out)
            continue
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "genai.py"), "video",
                        os.path.join(day, "prompts", f"shot{i}.txt"), out,
                        "--ref", HOST, "--aspect", "9:16", "--res", RES], check=True)


# ---------- build ----------

def run(args):
    return subprocess.run([FFMPEG, "-y", "-hide_banner", *args], capture_output=True, text=True)


def duration(path):
    r = run(["-i", path])
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def speech_window(path):
    """(start, end) of speech, from ffmpeg silencedetect."""
    dur = duration(path)
    r = run(["-i", path, "-vn", "-af", "silencedetect=n=-38dB:d=0.35", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    s0, s1 = 0.0, dur
    if starts and starts[0] < 0.05 and ends:
        s0 = ends[0]
    if starts and (len(ends) < len(starts) or ends[-1] >= dur - 0.05) and starts[-1] > s0 + 1:
        s1 = starts[-1]
    if s1 - s0 < 1.0:   # silent clip (still fallback) or detection failed: keep the whole clip
        s0, s1 = 0.0, dur
    return s0, s1, dur


def font(weight, size):
    return ImageFont.truetype(os.path.join(ROOT, "brand", "fonts", f"Poppins-{weight}.ttf"), size)


def chunks(caption):
    """Split a caption into 1-3 word pieces, breaking at punctuation. Each word keeps its *highlight* flag."""
    words = [(w.replace("*", ""), "*" in w) for w in caption.split()]
    out, cur = [], []
    for w, hl in words:
        cur.append((w, hl))
        if len(cur) == 3 or re.search(r"[,.!?…।]$", w):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def caption_png(piece, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = 88
    while True:
        f = font("ExtraBold", size)
        text = " ".join(w for w, _ in piece).upper()
        if d.textlength(text, font=f) <= W - 120 or size <= 52:
            break
        size -= 4
    space = d.textlength(" ", font=f)
    total = sum(d.textlength(w.upper(), font=f) for w, _ in piece) + space * (len(piece) - 1)
    x, y = (W - total) / 2, 1230
    for w, hl in piece:
        d.text((x, y), w.upper(), font=f, fill=(255, 214, 0) if hl else (255, 255, 255),
               stroke_width=9, stroke_fill=(0, 0, 0))
        x += d.textlength(w.upper(), font=f) + space
    img.save(path)


def hook_png(text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font("ExtraBold", 66)
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > W - 200 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    lh, y0 = 84, 250
    box_w = max(d.textlength(l, font=f) for l in lines) + 70
    d.rounded_rectangle([(W - box_w) / 2, y0 - 22, (W + box_w) / 2, y0 + lh * len(lines) + 12],
                        radius=28, fill=(255, 214, 0, 240))
    for i, l in enumerate(lines):
        d.text(((W - d.textlength(l, font=f)) / 2, y0 + i * lh), l, font=f, fill=(15, 15, 15))
    img.save(path)


def handle_png(path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font("SemiBold", 34)
    d.text(((W - d.textlength(HANDLE, font=f)) / 2, 150), HANDLE, font=f, fill=(255, 255, 255, 170),
           stroke_width=2, stroke_fill=(0, 0, 0, 120))
    img.save(path)


def cmd_build(day):
    s = load(day)
    n = len(s["shots"])
    clips = [os.path.join(day, "clips", f"shot{i}.mp4") for i in range(1, n + 1)]
    for c in clips:
        if not os.path.exists(c):
            sys.exit(f"missing {c}")
    out = os.path.join(day, "reel.mp4")
    check = os.path.join(day, "check")
    os.makedirs(check, exist_ok=True)
    timings, offset = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        segs = []
        for i, c in enumerate(clips):
            s0, s1, dur = speech_window(c)
            a, b = max(0.0, s0 - 0.2), min(dur, s1 + 0.45)
            seg = os.path.join(tmp, f"seg{i}.mp4")
            r = run(["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", c,
                     "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
                     "-af", "aresample=44100,aformat=channel_layouts=stereo",
                     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "192k", seg])
            if r.returncode:
                sys.exit(r.stderr[-1500:])
            seg_len = duration(seg)
            timings.append({"shot": i + 1, "offset": offset, "speech": [offset + s0 - a, offset + s1 - a],
                            "trim": [a, b], "len": seg_len})
            offset += seg_len
            segs.append(seg)
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in segs)
        joined = os.path.join(tmp, "joined.mp4")
        r = run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
        if r.returncode:
            sys.exit(r.stderr[-1500:])
        total = duration(joined)

        # overlays: handle (whole reel), hook (first 3 s), caption pieces timed across each shot's speech
        overlays = []   # no @handle watermark (user asked to remove it)
        hp = os.path.join(tmp, "hook.png")
        hook_png(s["hook"], hp)
        overlays.append((hp, 0, 3.0))
        k = 0
        for shot, t in zip(s["shots"], timings):
            pieces = chunks(shot["dialogue"])
            a, b = t["speech"]
            weights = [sum(len(w) for w, _ in p) + 2 for p in pieces]
            cur = a
            for p, wgt in zip(pieces, weights):
                d = (b - a) * wgt / sum(weights)
                path = os.path.join(tmp, f"cap{k}.png")
                caption_png(p, path)
                overlays.append((path, cur, cur + d))
                cur += d
                k += 1

        music = os.path.join(tmp, "music.wav")
        soft_music.main(music, total + 0.5)

        args = ["-i", joined, "-i", music]
        for p, _, _ in overlays:
            args += ["-i", p]
        fc, last = [], "[0:v]"
        for j, (_, t0, t1) in enumerate(overlays):
            lbl = f"[v{j}]"
            fc.append(f"{last}[{j + 2}:v]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})'{lbl}")
            last = lbl
        fc.append(f"[0:a]volume=1.0[va];[1:a]volume={s.get('music_vol', MUSIC_VOL)}[ma];"
                  f"[va][ma]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        r = run(args + ["-filter_complex", ";".join(fc), "-map", last, "-map", "[a]",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart",
                        "-t", f"{total:.3f}", out])
        if r.returncode:
            sys.exit(r.stderr[-2000:])

    for t in timings:
        mid = (t["speech"][0] + t["speech"][1]) / 2
        run(["-ss", f"{mid:.2f}", "-i", out, "-frames:v", "1", "-q:v", "3",
             os.path.join(check, f"shot{t['shot']}.jpg")])
    run(["-ss", "1.0", "-i", out, "-frames:v", "1", "-q:v", "3", os.path.join(check, "hook.jpg")])
    with open(os.path.join(day, "timings.json"), "w") as f:
        json.dump(timings, f, indent=1)
    print(f"built {out}: {total:.1f}s, {n} shots, {k} caption pieces")
    for t in timings:
        print(f"  shot{t['shot']}: speech {t['speech'][1] - t['speech'][0]:.1f}s of {t['len']:.1f}s")


def cmd_still(day):
    """Fallback without GEMINI_API_KEY: slow push-in on character/host.png per shot (silent), then build with music."""
    s = load(day)
    s.setdefault("music_vol", 0.6)
    with open(os.path.join(day, "script.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(day, "clips"), exist_ok=True)
    for i, shot in enumerate(s["shots"], start=1):
        dur = round(0.45 * len(spoken(shot["dialogue"]).split()) + 1.0, 2)
        frames = int(dur * FPS)
        z0, z1 = (1.0, 1.12) if i % 2 else (1.12, 1.0)
        zexpr = f"{z0}+({z1}-{z0})*on/{frames}"
        r = run(["-i", HOST, "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=44100:cl=stereo",
                 "-filter_complex",
                 f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                 f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[v]",
                 "-map", "[v]", "-map", "1:a", "-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", os.path.join(day, "clips", f"shot{i}.mp4")])
        if r.returncode:
            sys.exit(r.stderr[-1500:])
    cmd_build(day)


if __name__ == "__main__":
    {"prompts": cmd_prompts, "clips": cmd_clips, "build": cmd_build, "still": cmd_still}[sys.argv[1]](sys.argv[2].rstrip("/\\"))
