"""Long-form 16:9 story video (YouTube): narrated Hindi chapters over illustrated scenes.

    python tools/story_video.py voice CH_DIR    # Sarvam (voice "sarvam:ratan", default) or free Edge TTS -> CH_DIR/voice/NN.mp3
    python tools/story_video.py build CH_DIR    # needs CH_DIR/img/NN.png for each scene segment -> CH_DIR/chapter.mp4
    python tools/story_video.py join OUT.mp4 CH_DIR [CH_DIR ...]   # chapters -> full video

CH_DIR/script.json: {"voice", "rate", "segments": [{"text", "scene"} | {"title"}]}. Segment NN is its 1-based index.
Images: any size, cropped to 1920x1080. A missing image becomes a dark placeholder (for draft builds).
Each scene gets a slow Ken Burns move; title segments are a 3.5 s card. Soft original music under the voice.
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hindi_text as HT  # noqa: E402
import soft_music  # noqa: E402

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001
    FFMPEG = "ffmpeg"

W, H, FPS = 1920, 1080, 30
GAP = 0.45          # silence after each line
TITLE_LEN = 3.5


def load(ch):
    with open(os.path.join(ch, "script.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    t = r.stderr.split("Duration: ")[1].split(",")[0]
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def sarvam_key():
    k = os.environ.get("SARVAM_API_KEY")
    if not k and os.name == "nt":  # set as a Windows user variable but the shell started earlier
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as r:
            k = winreg.QueryValueEx(r, "SARVAM_API_KEY")[0]
    return k


def sarvam_tts(text, mp3, speaker="ratan", model="bulbul:v3", pace=0.9):
    import base64
    import urllib.request
    body = json.dumps({"text": text, "language_code": "hi-IN", "speaker": speaker, "model": model,
                       "pace": pace, "speech_sample_rate": 44100, "output_audio_codec": "mp3"}).encode()
    req = urllib.request.Request("https://api.sarvam.ai/text-to-speech", body,
                                 {"api-subscription-key": sarvam_key(), "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    with open(mp3, "wb") as f:
        f.write(base64.b64decode("".join(r["audios"])))


def voice(ch):
    """script.json "voice": "sarvam:<speaker>" (Sarvam Bulbul v3, needs SARVAM_API_KEY, ~Rs 3 per 1000 chars)
    or an Edge voice name (free)."""
    import edge_tts
    s = load(ch)
    v = s.get("voice", "sarvam:ratan")
    out = os.path.join(ch, "voice")
    os.makedirs(out, exist_ok=True)

    async def go():
        for i, seg in enumerate(s["segments"], 1):
            if "text" not in seg:
                continue
            mp3 = os.path.join(out, f"{i:02d}.mp3")
            if not os.path.exists(mp3):
                if v.startswith("sarvam:"):
                    sarvam_tts(seg["text"], mp3, v.split(":", 1)[1], pace=float(s.get("pace", 0.9)))
                else:
                    await edge_tts.Communicate(seg["text"], v, rate=s.get("rate", "-6%")).save(mp3)
            print(f"{i:02d}: {duration(mp3):.1f}s")
    asyncio.run(go())


def neutral(im, amount=0.6):
    """Pull the colour cast (ChatGPT's yellow/golden tint) toward neutral grey; user asked for no gold haze."""
    from PIL import ImageStat
    r, g, b = ImageStat.Stat(im).mean
    m = (r + g + b) / 3
    gains = [1 + amount * (m / c - 1) for c in (r, g, b)]
    return im.point([min(255, round(i * gains[k])) for k in range(3) for i in range(256)])


def fit(img_path):
    if os.path.exists(img_path):
        im = neutral(Image.open(img_path).convert("RGB"))
        sc = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        l, t = (im.width - W) // 2, (im.height - H) // 2
        return im.crop((l, t, l + W, t + H))
    im = Image.new("RGB", (W, H), (28, 30, 38))
    ImageDraw.Draw(im).text((60, 60), os.path.basename(img_path), fill=(120, 120, 130))
    return im


def title_png(text, path):
    css = (".t{position:absolute;left:0;right:0;top:430px;text-align:center;color:#f6e7c8;font-size:96px;"
           "text-shadow:0 6px 30px rgba(0,0,0,.6)}.l{position:absolute;left:760px;right:760px;top:590px;"
           "height:4px;background:#e0a84a;border-radius:2px}")
    HT.W, HT.H = W, H
    HT._shot(HT.BASE % {"w": W, "h": H, "css": css, "body": f'<div class="t">{text}</div><div class="l"></div>'},
             path)


def build(ch):
    s = load(ch)
    tmp = os.path.join(ch, "tmp")
    os.makedirs(tmp, exist_ok=True)
    parts, t = [], 0.0
    for i, seg in enumerate(s["segments"], 1):
        part = os.path.join(tmp, f"{i:02d}.mp4")
        if "title" in seg:
            png = os.path.join(tmp, f"title{i:02d}.png")
            title_png(seg["title"], png)
            bg = Image.new("RGB", (W, H), (20, 18, 24))
            bg.paste(Image.open(png).convert("RGBA"), (0, 0), Image.open(png).convert("RGBA"))
            bg.save(os.path.join(tmp, f"t{i:02d}.png"))
            run([FFMPEG, "-y", "-loop", "1", "-t", str(TITLE_LEN), "-i", os.path.join(tmp, f"t{i:02d}.png"),
                 "-f", "lavfi", "-t", str(TITLE_LEN), "-i", "anullsrc=r=44100:cl=stereo",
                 "-vf", f"fade=in:0:15,fade=out:st={TITLE_LEN - 0.5}:d=0.5,fps={FPS},format=yuv420p",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", part])
            length = TITLE_LEN
        else:
            mp3 = os.path.join(ch, "voice", f"{i:02d}.mp3")
            length = duration(mp3) + GAP
            src = os.path.join(tmp, f"s{i:02d}.png")
            big = fit(os.path.join(ch, "img", f"{i:02d}.png")).resize((W * 2, H * 2), Image.LANCZOS)
            big.save(src)
            n = int(length * FPS) + 1
            # alternate zoom in / zoom out with a little drift
            if i % 2:
                z = f"min(1+0.08*on/{n},1.08)"
            else:
                z = f"max(1.08-0.08*on/{n},1)"
            dx = "(iw-iw/zoom)/2" + ("+on*0.15" if i % 3 == 0 else "")
            vf = (f"zoompan=z='{z}':x='{dx}':y='(ih-ih/zoom)/2':d={n}:s={W}x{H}:fps={FPS},"
                  f"fade=in:0:9,fade=out:st={length - 0.3:.2f}:d=0.3,format=yuv420p")
            run([FFMPEG, "-y", "-loop", "1", "-i", src, "-i", mp3, "-filter_complex",
                 f"[0:v]{vf}[v];[1:a]apad,atrim=0:{length:.3f},aformat=sample_rates=44100:channel_layouts=stereo[a]",
                 "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", part])
        parts.append(part)
        t += length
        print(f"{i:02d}: {length:.1f}s")
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    joined = os.path.join(tmp, "joined.mp4")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    music = os.path.join(tmp, "music.wav")
    soft_music.main(music, t + 1)
    out = os.path.join(ch, "chapter.mp4")
    run([FFMPEG, "-y", "-i", joined, "-i", music, "-filter_complex",
         "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", out])
    print(f"chapter: {t / 60:.1f} min -> {out}")


def join(out, chs):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for ch in chs:
            f.write(f"file '{os.path.abspath(os.path.join(ch, 'chapter.mp4'))}'\n")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", f.name, "-c", "copy", out])
    print(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "voice":
        voice(sys.argv[2])
    elif cmd == "build":
        build(sys.argv[2])
    elif cmd == "join":
        join(sys.argv[2], sys.argv[3:])
