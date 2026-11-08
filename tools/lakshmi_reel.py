"""Brand-free Lakshmi ji + Kuber ji Diwali wishes reel: slow zoom on the artwork, coin rain, glowing halos,
fireworks, Hindi wishes, original music and a Hindi voice (free Microsoft Edge neural TTS, hi-IN-SwaraNeural).

    python tools/lakshmi_reel.py OUT_DIR      # needs OUT_DIR/art.png (9:16) and OUT_DIR/voice/v1..v5.mp3
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import diwali_music as M  # noqa: E402
import diwali_reel as R  # noqa: E402

W, H, FPS = R.W, R.H, R.FPS
B = M.BEAT
# longer arrangement for the voice: 60 beats
M.MELODY = M.INTRO + M.A + M.B + M.A + M.B + M.A + M.C + M.OUTRO
M.BEATS = sum(d for _, d in M.MELODY)
M.LENGTH = M.BEATS * B
M.BURST_BEATS = [4, 12, 20, 28, 36, 44, 50, 52, 54, 56]
VOICE_BEATS = [4, 9, 24, 36, 50]          # v1..v5 start beats
CARDS = [
    (4, 9, '<div class="big">शुभ दीपावली</div>'),
    (9, 24, '<div>माँ लक्ष्मी और कुबेर जी की कृपा से</div><div>आपका घर <g>धन-धान्य</g> से भरा रहे</div>'),
    (24, 36, '<div><g>सुख, समृद्धि</g> और खुशियाँ</div><div>हर दिन आपके साथ रहें</div>'),
    (36, 50, '<div>आपको और पूरे परिवार को</div><div><g>दीपावली की हार्दिक शुभकामनाएँ</g></div>'),
    (50, 61, '<div class="big2">Happy Diwali</div><div class="cta">ये शुभकामना अपनों को भेजें</div>'),
]
R.CARDS = CARDS
R.CSS = R.CSS.replace("top:620px", "top:95px").replace("font:400 86px/1.45", "font:400 70px/1.4") \
    .replace(".big{font-size:150px", ".big{font-size:140px").replace("margin-top:40px", "margin-top:0")
# halos / light in artwork pixel coords (944x1680)
GLOWS = [((268, 450), (1, .8, .4), .45), ((690, 470), (1, .8, .4), .4), ((470, 60), (1, .9, .6), .6),
         ((340, 1180), (1, .78, .3), .35)]


def coin_sprites():
    out = []
    for k in range(10):
        w = max(4, int(34 * abs(math.cos(k * math.pi / 10))))
        im = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([20 - w // 2, 3, 20 + w // 2, 37], fill=(214, 156, 32, 255), outline=(255, 226, 120, 255), width=3)
        if w > 14:
            d.ellipse([20 - w // 4, 11, 20 + w // 4, 29], outline=(255, 236, 150, 200), width=2)
        out.append(im)
    return out


def main(out):
    out = os.path.abspath(out)
    os.makedirs(os.path.join(out, "check"), exist_ok=True)
    music = os.path.join(out, "music.wav")
    M.main(music)
    cards = R.render_cards(os.path.join(out, "cards"))
    art = Image.open(os.path.join(out, "art.png")).convert("RGB")
    aw, ah = art.size
    length = M.LENGTH + 0.8
    nfr = int(length * FPS)
    rnd = np.random.default_rng(81)
    fireworks = []
    for b in M.BURST_BEATS:
        fw = R.Firework(b * B - .55, rnd, big=b >= 50)
        fw.cy = rnd.uniform(120, 380)
        fireworks.append(fw)
    coins = coin_sprites()
    rain = [(rnd.uniform(0, W), rnd.uniform(0, 1), rnd.uniform(.18, .32), rnd.integers(10), rnd.uniform(.6, 1.1))
            for _ in range(46)]
    twinkles = [(rnd.uniform(0, aw), rnd.uniform(ah * .55, ah), rnd.uniform(0, 6), rnd.uniform(2, 5)) for _ in range(60)]
    top_shade = np.linspace(.62, 0, 700, dtype=np.float32)[:, None, None]
    # voice + music mix
    vfiles = [os.path.join(out, "voice", f"v{i}.mp3") for i in range(1, 6)]
    inputs, filt = ["-i", music], []
    for i, (vf, b) in enumerate(zip(vfiles, VOICE_BEATS), start=1):
        inputs += ["-i", vf]
        ms = int(b * B * 1000)
        filt.append(f"[{i}:a]aresample=44100,volume=1.9,adelay={ms}|{ms}[v{i}]")
    filt.append("[0:a]volume=0.42[m]")
    filt.append("[m]" + "".join(f"[v{i}]" for i in range(1, 6)) +
                "amix=inputs=6:normalize=0:duration=first,alimiter=limit=0.95[a]")
    mix = os.path.join(out, "mix.wav")
    subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[a]", mix], check=True)
    proc = subprocess.Popen([R.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix,
                             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                             os.path.join(out, "reel.mp4")], stdin=subprocess.PIPE)
    checks = {int(s * FPS) for s in (1.0, 3.5, 8.0, 15.0, 22.0, 28.5)}
    for fi in range(nfr):
        t = fi / FPS
        z = 1.0 + .10 * (t / length)                              # slow push-in
        s = H / ah * z
        sw, sh = int(aw * s), int(ah * s)
        ox, oy = (sw - W) / 2, (sh - H) * .45
        frame_img = art.resize((sw, sh), Image.BILINEAR).crop((int(ox), int(oy), int(ox) + W, int(oy) + H))
        img = np.asarray(frame_img, dtype=np.float32) / 255
        img[:700] *= (1 - top_shade)                              # darker sky band for the text
        for (gx, gy), col, a in GLOWS:
            R.splat(img, gx * s - ox, gy * s - oy, col, a * (.75 + .25 * math.sin(t * 2.4 + gx)), R.BIG)
        for x, y, ph, sp in twinkles:
            v = max(0.0, math.sin(t * sp + ph)) ** 6
            if v > .05:
                R.splat(img, x * s - ox, y * s - oy, (1, .95, .7), 1.6 * v, R.SPR[8])
        for fw in fireworks:
            fw.draw(img, t)
        fade = min(1.0, t / .8)
        frame = Image.fromarray((np.clip(img * fade, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
        if t > 1.2:                                                # coin rain
            for x, ph, sp, k, sc in rain:
                y = ((t * sp + ph) % 1) * (H + 80) - 40
                c = coins[(k + int(t * 12)) % 10]
                if sc != 1:
                    c = c.resize((int(40 * sc), int(40 * sc)))
                frame.alpha_composite(c, (int(x + 25 * math.sin(t + ph * 6)), int(y)))
        for ci, (sb, eb, _) in enumerate(CARDS):
            st, e = sb * B, min(eb * B, length - .2)
            if st - .05 <= t <= e:
                a = min(1, (t - st) / .45, (e - t) / .3)
                if a <= 0:
                    continue
                card = cards[ci]
                if a < 1:
                    card = card.copy()
                    card.putalpha(card.getchannel("A").point(lambda v, a=a: int(v * a)))
                frame.alpha_composite(card)
        rgb = frame.convert("RGB")
        if fi in checks:
            rgb.save(os.path.join(out, "check", f"t{fi / FPS:04.1f}s.jpg"), quality=88)
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    proc.wait()
    print("reel:", os.path.join(out, "reel.mp4"), f"{length:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
