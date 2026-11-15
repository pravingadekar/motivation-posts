"""HyperFrames edit of the daily talking-host reel (3 Flow clips with the host's own voice).

python tools/edit_hf.py daily/D        # full run: project in daily/D/hf, render, daily/D/reel.mp4 replaced
                                        # (the plain build is kept as daily/D/reel_basic.mp4)
python tools/edit_hf.py DAY_DIR PROJECT_DIR [extras.json]   # only write the project
The on-screen copy comes from script.json "edit" (same shape as extras.json below).
  DAY_DIR: motivation-posts/daily/<D> with script.json + clips/shot1..3.mp4
  extras.json (optional): {"steps": [{"text": "...", "emoji": "✍️", "word": "पहला"}, ...],
                           "cta": ["उस दोस्त को भेजो", "💌"], "follow": "फ़ॉलो करो, कल एक और सच"}
then: cd PROJECT_DIR && npx hyperframes check --json && npx hyperframes render --quality delivery -o out.mp4

Adds: hook card on frame 0, karaoke captions from faster-whisper word times (cached in PROJECT/words.json),
punch-ins on *key* words, flash + whoosh on shot cuts, step cards, share CTA card, progress bar,
soft music ducked under the voice, AI label. Text stays inside the 168-1330 px band.
"""
import html
import json
import math
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import sfx as cr  # noqa: E402  (decode, pop, whoosh, ding)

W, H, SR = 1080, 1920, 44100
ACC, KEY, HL = "#fde047", "#34d399", "#f472b6"


def esc(s):
    return html.escape(s, quote=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def words_for(day, proj, s, starts):
    cache = os.path.join(proj, "words.json")
    if os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    out = []
    for i, sh in enumerate(s["shots"]):
        words = sh["dialogue_hi"].split()
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(day, "clips", f"shot{i + 1}.mp4"), "-ac", "1",
                              "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        segs, _ = model.transcribe(a, language="hi", word_timestamps=True)
        ww = [w for sg in segs for w in sg.words]
        if len(ww) == len(words):
            times = [(w.start, w.end) for w in ww]
            how = "whisper"
        else:
            lo, hi = (ww[0].start, ww[-1].end) if ww else (0.2, 7.5)
            lens = [len(w.replace("*", "")) + 1 for w in words]
            acc, times = lo, []
            for L in lens:
                d = (hi - lo) * L / sum(lens)
                times.append((acc, acc + d))
                acc += d
            how = f"spread ({len(ww)} vs {len(words)})"
        print(f"shot {i + 1}: {how}")
        out.append([[w, round(starts[i] + t0, 3), round(starts[i] + t1, 3)] for w, (t0, t1) in zip(words, times)])
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def bed_audio(path, day, starts, total, cuts, pops, chimes):
    """Music (ducked under the clips' speech) + sound effects, as one track under the clips' own audio."""
    n = int(total * SR)
    speech = np.zeros(n, np.float32)
    for i, st in enumerate(starts):
        a = cr.decode(os.path.join(day, "clips", f"shot{i + 1}.mp4"))
        j = int(st * SR)
        speech[j:j + a.size] += a[:max(0, n - j)]
    sfx = np.zeros(n, np.float32)

    def add(sound, at, g=1.0):
        j = max(int(at * SR), 0)
        k = min(j + sound.size, n)
        sfx[j:k] += sound[:k - j] * g

    for t in cuts:
        add(cr.whoosh(0.45), t - 0.22, 0.9)
    for t in pops:
        add(cr.pop(0.08, 1100), t, 0.7)
    for t in chimes:
        add(cr.ding(), t, 0.8)
    mw = path + ".m.wav"
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "soft_music.py"), mw,
                    str(math.ceil(total) + 1)], check=True)
    music = cr.decode(mw)[:n]
    os.remove(mw)
    music = np.pad(music, (0, n - music.size))
    music *= 0.13 / max(np.abs(music).max(), 1e-6)
    env = np.convolve((np.abs(speech) > 0.03).astype(np.float32), np.ones(int(0.3 * SR)) / int(0.3 * SR), "same")
    music *= 1 - 0.6 * np.clip(env * 3, 0, 1)
    fade = np.minimum(1, np.minimum(np.arange(n) / SR / 0.5, (n - np.arange(n)) / SR / 1.0))
    m = music * fade + sfx * 0.5
    m /= max(1.0, np.abs(m).max() / 0.9)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((m * 32767).astype(np.int16).tobytes())


def build(day, proj, extras_path=None):
    s = json.load(open(os.path.join(day, "script.json"), encoding="utf-8"))
    ex = json.load(open(extras_path, encoding="utf-8")) if extras_path else s.get("edit", {})
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
    lens, starts, t = [], [], 0.0
    for i in range(len(s["shots"])):
        src = os.path.join(day, "clips", f"shot{i + 1}.mp4")
        shutil.copy(src, os.path.join(proj, "assets", f"shot{i + 1}.mp4"))
        d = round(dur(src), 3)
        starts.append(round(t, 3))
        lens.append(d)
        t += d
    TAIL = 0.3                                # Veo blurs the very last frames of a clip
    lens[-1] = round(lens[-1] - TAIL, 3)
    vid_end = round(t - TAIL, 3)
    total = round(vid_end + 1.6, 2)          # hold the last frame under the CTA
    words = words_for(day, proj, s, starts)
    flat = [w for line in words for w in line]
    cuts = starts[1:]
    cta_word = ex.get("cta_word", "भेजो")
    cta_t = next((t0 for w, t0, t1 in flat if cta_word in w), flat[-1][1])

    el, js = [], []
    T = lambda v: f"{v:.3f}"  # noqa: E731

    # ---- video clips in a camera wrapper (punch-ins tween the wrapper, never the video)
    vids = "".join(
        f'<video id="v{i + 1}" class="clip vid" src="assets/shot{i + 1}.mp4" data-start="{starts[i]}" '
        f'data-duration="{lens[i]}" data-track-index="{i + 1}" data-has-audio="true" playsinline></video>'
        for i in range(len(starts)))
    # last frame hold: a muted copy of shot 3's tail would need seeking; instead keep a still of the final frame
    still = os.path.join(proj, "assets", "last.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", f"-{TAIL + 0.05}", "-i",
                    os.path.join(day, "clips", f"shot{len(starts)}.mp4"), "-frames:v", "1", "-q:v", "2", still], check=True)
    vids += (f'<img id="vlast" class="clip vid" src="assets/last.jpg" data-start="{vid_end - 0.04:.3f}" '
             f'data-duration="{total - vid_end + 0.04:.3f}" data-track-index="4">')
    # punch-ins: each *key* word steps the camera in; every cut resets with a settle
    for i, st in enumerate(starts):
        js.append(f'tl.fromTo("#cam",{{scale:{1.1 if i else 1.0}}},{{scale:1.0,duration:0.4,ease:"expo.out"}},{T(st)});')
    for w, t0, t1 in flat:
        if "*" in w:
            js.append(f'tl.to("#cam",{{scale:1.09,duration:0.18,ease:"power3.out"}},{T(t0)});')
            js.append(f'tl.to("#cam",{{scale:1.0,duration:0.5,ease:"power2.inOut"}},{T(t1 + 0.35)});')
    for c in cuts:
        js.append(f'tl.fromTo("#flash",{{opacity:0}},{{opacity:0.55,duration:0.05}},{T(c - 0.03)});')
        js.append(f'tl.to("#flash",{{opacity:0,duration:0.25,ease:"power2.out"}},{T(c + 0.03)});')

    # ---- top: progress bar + AI label
    el.append('<div id="prog"><div id="progfill"></div></div>')
    js.append(f'tl.fromTo("#progfill",{{scaleX:0}},{{scaleX:1,duration:{total},ease:"none"}},0);')
    if ex.get("ai_label"):   # off by default: the AI label lives in the post caption + platform AI flag
        el.append('<div id="ailabel">AI generated video</div>')

    # ---- hook card (on screen at frame 0 = thumbnail)
    hook = ex.get("hook") or s.get("hook_hi") or s["hook"]     # extras hook may mark *key* words
    hw = hook.split()
    key_hook = {k for k, w in enumerate(hw) if "*" in w} or set(range(max(0, len(hw) - 2), len(hw)))
    hw = [w.replace("*", "") for w in hw]
    sub = ex.get("hook_sub", "")
    el.append('<div id="hook"><div id="hookin">' + " ".join(
        f'<span id="hk{k}" class="hkw{" hkey" if k in key_hook else ""}">{esc(w)}</span>' for k, w in enumerate(hw))
        + (f'<div id="hooksub">{esc(sub)}</div>' if sub else "") + '</div></div>')
    if sub:
        js.append('tl.fromTo("#hooksub",{opacity:0,y:14},{opacity:1,y:0,duration:0.35,ease:"expo.out"},0.9);')
    for k in sorted(key_hook):
        js.append(f'tl.fromTo("#hk{k}",{{scale:1}},{{scale:1.15,duration:0.18,ease:"back.out(3)",yoyo:true,repeat:1}},'
                  f'{T(0.5 + 0.12 * (k - min(key_hook)))});')
    hook_out = starts[1] - 0.45
    js.append(f'tl.to("#hook",{{opacity:0,y:-24,filter:"blur(8px)",duration:0.22,ease:"power2.in"}},{T(hook_out)});')

    # ---- step cards (one at a time, with a step counter)
    steps = ex.get("steps", [])
    step_t = []
    used = 0
    for k, st in enumerate(steps):
        at = next((t0 for idx, (w, t0, t1) in enumerate(flat) if idx >= used and st["word"] in w.replace("*", "")), None)
        if at is None:
            continue
        used = next(idx for idx, (w, t0, t1) in enumerate(flat) if t0 == at) + 1
        step_t.append(at)
        el.append(f'<div id="st{k}" class="step"><div class="stnum">कदम {k + 1}/{len(steps)}</div>'
                  f'<div class="sttxt"><span class="stemo">{esc(st.get("emoji", ""))}</span>{esc(st["text"])}</div></div>')
    for k, at in enumerate(step_t):
        end = step_t[k + 1] if k + 1 < len(step_t) else cta_t
        js.append(f'tl.fromTo("#st{k}",{{opacity:0,x:-80,scale:0.9}},{{opacity:1,x:0,scale:1,duration:0.45,'
                  f'ease:"back.out(1.6)"}},{T(at - 0.05)});')
        js.append(f'tl.to("#st{k}",{{opacity:0,x:60,duration:0.2,ease:"power2.in"}},{T(end - 0.25)});')

    # ---- karaoke captions
    for i, line in enumerate(words):
        groups, cur = [], []
        for wd in line:
            cur.append(wd)
            if len(cur) >= 3 or wd[0].rstrip("*").endswith((",", "।", "?", "!")):
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        for g, grp in enumerate(groups):
            gid = f"cap{i}_{g}"
            el.append(f'<div id="{gid}" class="cap">' + " ".join(
                f'<span id="{gid}_{k}" class="cw">{esc(w.replace("*", ""))}</span>' for k, (w, a, b) in enumerate(grp))
                + "</div>")
            g0 = grp[0][1] - 0.05
            if g + 1 < len(groups):
                nxt = groups[g + 1][0][1] - 0.05
            elif i + 1 < len(words):
                nxt = words[i + 1][0][1] - 0.05
            else:
                nxt = vid_end
            g1 = max(min(nxt, grp[-1][2] + 0.5), grp[-1][2])
            if g0 >= cta_t - 0.05:
                continue
            g1 = min(g1, cta_t)
            js.append(f'tl.fromTo("#{gid}",{{opacity:0,y:22,scale:0.94}},{{opacity:1,y:0,scale:1,duration:0.14,'
                      f'ease:"back.out(2)"}},{T(g0)});')
            for k, (w, a, b) in enumerate(grp):
                key = "*" in w
                js.append(f'tl.to("#{gid}_{k}",{{color:"{KEY if key else ACC}",scale:1.12,duration:0.07,'
                          f'ease:"power2.out"}},{T(a)});')
                if not key:
                    js.append(f'tl.to("#{gid}_{k}",{{color:"#ffffff",scale:1,duration:0.12}},{T(max(b, a + 0.1))});')
            js.append(f'tl.to("#{gid}",{{opacity:0,duration:0.1}},{T(g1 - 0.1)});')
            js.append(f'tl.set("#{gid}",{{opacity:0,visibility:"hidden"}},{T(g1)});')

    # ---- share CTA card + follow pill
    cta = ex.get("cta", ["उस दोस्त को भेजो", "💌"])
    el.append(f'<div id="cta"><div id="ctaemo">{esc(cta[1])}</div><div id="ctatxt">{esc(cta[0])}</div>'
              f'<div id="ctasub">{esc(ex.get("cta_sub", "शेयर बटन दबाओ ➜"))}</div></div>')
    el.append(f'<div id="follow">{esc(ex.get("follow", "फ़ॉलो करो, कल एक और सच"))}</div>')
    js.append(f'tl.fromTo("#cta",{{opacity:0,y:60,scale:0.6}},{{opacity:1,y:0,scale:1,duration:0.6,'
              f'ease:"elastic.out(1,0.6)"}},{T(cta_t)});')
    js.append(f'tl.fromTo("#ctaemo",{{rotation:-25,scale:0.4}},{{rotation:0,scale:1,duration:0.7,'
              f'ease:"elastic.out(1,0.5)"}},{T(cta_t + 0.1)});')
    js.append(f'tl.fromTo("#follow",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.4,ease:"expo.out"}},'
              f'{T(vid_end - 0.6)});')

    bed_audio(os.path.join(proj, "assets", "bed.wav"), day, starts, total, cuts,
              pops=[a - 0.05 for a in step_t], chimes=[cta_t])

    css = f"""
@font-face{{font-family:'HindiUI';src:local('Nirmala UI Bold'),local('NirmalaUI-Bold'),local('Nirmala UI');font-weight:700 900}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#000}}
#root{{position:relative;width:100%;height:100%;overflow:hidden;font-family:'Poppins','HindiUI',sans-serif}}
#cam{{position:absolute;inset:0;transform-origin:540px 620px}}
.vid{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover}}
#shade{{position:absolute;left:0;right:0;bottom:0;height:900px;
 background:linear-gradient(180deg,rgba(0,0,0,0) 0%,rgba(0,0,0,.45) 55%,rgba(0,0,0,.6) 100%)}}
#flash{{position:absolute;inset:0;background:#fff;opacity:0}}
#prog{{position:absolute;left:80px;right:80px;top:214px;height:6px;border-radius:6px;background:rgba(255,255,255,.3)}}
#progfill{{width:100%;height:100%;border-radius:6px;background:{ACC};transform-origin:0 50%}}
#ailabel{{position:absolute;right:80px;top:232px;font:600 28px 'Poppins';color:rgba(255,255,255,.85);
 background:rgba(0,0,0,.35);padding:4px 12px;border-radius:12px}}
#hook{{position:absolute;left:0;right:0;top:286px;text-align:center}}
#hookin{{display:inline-block;max-width:960px;padding:22px 38px;border-radius:30px;background:rgba(15,23,42,.82);
 font-family:'HindiUI';font-weight:900;font-size:60px;line-height:1.3;color:#fff;box-shadow:0 16px 40px rgba(0,0,0,.35)}}
.hkw{{display:inline-block;margin:0 4px}}
.hkey{{color:{ACC}}}
#hooksub{{font-size:40px;font-weight:800;color:#a7f3d0;margin-top:6px}}
.step{{position:absolute;left:0;right:0;top:1300px;text-align:center;opacity:0}}
.stnum{{display:inline-block;font-family:'HindiUI';font-weight:800;font-size:30px;color:#0f172a;background:{ACC};
 padding:4px 18px;border-radius:20px;margin-bottom:8px}}
.sttxt{{display:block;width:max-content;max-width:900px;margin:0 auto;padding:14px 34px;border-radius:26px;
 background:rgba(255,255,255,.95);color:#0f172a;font-family:'HindiUI';font-weight:900;font-size:56px;
 box-shadow:0 14px 34px rgba(0,0,0,.3)}}
.stemo{{margin-right:14px}}
.cap{{position:absolute;left:90px;right:90px;top:1470px;text-align:center;font-family:'HindiUI';font-weight:900;font-size:72px;
 line-height:1.3;color:#fff;opacity:0;-webkit-text-stroke:9px #000;paint-order:stroke fill;
 text-shadow:0 6px 18px rgba(0,0,0,.7)}}
.cw{{display:inline-block;margin:0 4px}}
#cta{{position:absolute;left:0;right:0;top:1250px;margin:auto;width:max-content;max-width:920px;padding:24px 50px 26px;
 border-radius:34px;background:#fff;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.4);border:6px solid {HL};opacity:0}}
#ctaemo{{font-size:84px;line-height:1}}
#ctatxt{{font-family:'HindiUI';font-weight:900;font-size:54px;color:#0f172a}}
#ctasub{{font-family:'HindiUI';font-weight:700;font-size:34px;color:#9d174d}}
#follow{{position:absolute;left:0;right:0;top:1566px;margin:auto;width:max-content;padding:12px 34px;border-radius:40px;
 background:{ACC};color:#0f172a;font-family:'HindiUI';font-weight:900;font-size:44px;opacity:0}}
"""
    doc = f"""<!doctype html>
<html lang="hi">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>{css}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
<div id="cam">{vids}</div>
<div id="stage" class="clip" data-start="0" data-duration="{total}" data-track-index="5" style="position:absolute;inset:0">
<div id="shade"></div><div id="flash"></div>
{chr(10).join(el)}
</div>
<audio id="bed" class="clip" src="assets/bed.wav" data-start="0" data-duration="{total}" data-track-index="6" data-volume="1"></audio>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""
    with open(os.path.join(proj, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {proj}/index.html ({total}s, {len(js)} tweens)")


def npx(args, cwd, timeout=900):
    exe = shutil.which("npx") or shutil.which("npx.cmd") or "npx"
    return subprocess.run([exe, "--yes", "hyperframes@0.9.52"] + args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def full(day):
    """Build, check, snapshot and render; on success daily/D/reel.mp4 becomes the edited reel."""
    proj = os.path.join(day, "hf")
    os.makedirs(proj, exist_ok=True)
    build(day, proj)
    r = npx(["check", "--json"], proj)
    try:
        if json.loads(r.stdout[r.stdout.index("{"):]).get("lint", {}).get("errorCount", 0):
            sys.exit("hyperframes check: lint errors, see " + proj)
    except ValueError:
        pass
    total = float(open(os.path.join(proj, "index.html"), encoding="utf-8").read().split('data-duration="')[1].split('"')[0])
    marks = [0.0, 3.0, total * 0.35, total * 0.6, total * 0.8, total - 0.3]
    r = npx(["snapshot", "--at", ",".join(f"{m:.1f}" for m in marks)], proj, 600)
    snaps = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().endswith(".png")]
    os.makedirs(os.path.join(day, "check"), exist_ok=True)
    for k, sp in enumerate(snaps):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", sp, "-vf", "scale=540:-1",
                        os.path.join(day, "check", f"hf_{k + 1}.jpg")], check=False)
    out = os.path.join(proj, "out.mp4")
    r = npx(["render", "--quality", "delivery", "-o", "out.mp4"], proj, 1200)
    if not os.path.exists(out) or abs(dur(out) - total) > 0.5:
        sys.exit("render failed: " + r.stdout[-1500:] + r.stderr[-1500:])
    reel, basic = os.path.join(day, "reel.mp4"), os.path.join(day, "reel_basic.mp4")
    if os.path.exists(reel) and not os.path.exists(basic):
        shutil.copy(reel, basic)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "libx264", "-crf", "21", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", reel], check=True)
    print(f"edited reel: {reel} ({dur(reel):.1f}s); plain build kept as {basic}; review {day}/check/hf_*.jpg")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        full(sys.argv[1])
    else:
        build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
