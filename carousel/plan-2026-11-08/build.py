"""Render carousels from content.py: ../<date>/scenes/sceneN.png + Hindi text -> ../<date>/slides/slideN.jpg (1080x1350).

    python build.py 2026-11-08 2026-11-09

Edge renders the text so Devanagari matras are shaped correctly. Styles mix the looks in ../references.md.
"""
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image

from content import CAROUSELS

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
W, H = 1080, 1350
HANDLE = "@ai__wala_motivational_guru"

BASE = """html,body{margin:0;width:1080px;height:1350px;overflow:hidden}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
r{color:VAR_RED}
m{background:linear-gradient(transparent 12%,#ffd23f 12%,#ffd23f 90%,transparent 90%);padding:0 12px;color:#2b1d12;
 -webkit-box-decoration-break:clone;box-decoration-break:clone}
.note{margin-top:20px;font-size:44px;line-height:1.4}
.arrow{position:absolute;right:50px;top:1240px;font:700 74px Arial}
.handle{position:absolute;left:50%;transform:translateX(-50%);bottom:22px;font:600 26px Arial;white-space:nowrap;
 padding:5px 18px;border-radius:20px;background:rgba(20,12,6,.72);color:#fff !important;text-shadow:none !important}
.chapter{font-size:40px;line-height:1.4;opacity:.8;margin-bottom:6px}
"""
STYLES = {
    # text on the blank paper at the top of the scene
    "kraft": BASE.replace("VAR_RED", "#a31515") + """
.box{position:absolute;left:60px;right:60px;top:70px;text-align:center;font:700 72px/1.42 Kalam,serif;color:#23160c}
.arrow,.handle{color:#23160c}""",
    "sketch": BASE.replace("VAR_RED", "#c62828") + """
.box{position:absolute;left:60px;right:60px;top:82px;text-align:center;font:700 72px/1.42 Kalam,serif;color:#2b1d12}
.arrow,.handle{color:#2b1d12}.handle{text-shadow:0 0 8px #efe2c4,0 0 8px #efe2c4}""",
    "colour": BASE.replace("VAR_RED", "#d32f2f") + """
.box{position:absolute;left:60px;right:60px;top:82px;text-align:center;font:700 74px/1.4 'Tiro Devanagari Hindi',serif;color:#2b1d12}
.arrow,.handle{color:#2b1d12}.handle{text-shadow:0 0 8px #fff,0 0 8px #fff}""",
    # full scene with a soft caption box low on the slide, inspired by the fable reference
    "dark": BASE.replace("VAR_RED", "#d32f2f") + """
.box{position:absolute;left:50px;right:50px;bottom:110px;text-align:center;font:700 58px/1.42 Kalam,serif;color:#1c120a;
 background:rgba(250,244,230,.93);border-radius:22px;padding:24px 26px;box-shadow:0 0 34px rgba(255,250,235,.55)}
.arrow{top:60px;color:#fff;text-shadow:0 2px 10px #000}.handle{color:#fff;text-shadow:0 2px 8px #000}""",
}
LINK = ('<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@700'
        '&family=Tiro+Devanagari+Hindi&display=block" rel="stylesheet">')


def page(date, n, spec):
    bg = os.path.join(HERE, "..", date, "scenes", f"scene{n}.png")
    bg = os.path.normpath(bg).replace("\\", "/")
    lines = spec["slides"][n - 1]
    total = len(spec["slides"])
    rows = "".join(f"<div>{ln}</div>" for ln in lines)
    chapter = f'<div class="chapter">अध्याय {n - 1}</div>' if spec["style"] == "kraft" and n > 1 else ""
    note = f'<div class="note">{spec["note"]}</div>' if n == total else ""
    top = spec.get("box_top", {}).get(n)  # move the caption box when it would hide the point of the scene
    box_style = f' style="top:{top}px;bottom:auto"' if top else ""
    arrow = '<div class="arrow">&#10230;</div>' if n < total else ""
    return (f'<!doctype html><html lang="hi"><head><meta charset="utf-8">{LINK}<style>{STYLES[spec["style"]]}</style></head>'
            f"<body><div class=\"bg\" style=\"background-image:url('file:///{bg}')\"></div>"
            f'<div class="box"{box_style}>{chapter}{rows}{note}</div>{arrow}<div class="handle">{HANDLE}</div></body></html>')


def main():
    tmp = os.path.normpath(os.environ.get("CAROUSEL_TMP") or tempfile.mkdtemp())
    os.makedirs(tmp, exist_ok=True)
    for date in sys.argv[1:]:
        spec = CAROUSELS[date]
        out = os.path.join(HERE, "..", date, "slides")
        os.makedirs(out, exist_ok=True)
        for n in range(1, len(spec["slides"]) + 1):
            html = os.path.join(tmp, f"{date}_{n}.html")
            png = os.path.join(tmp, f"{date}_{n}.png")
            if os.path.exists(png):
                os.remove(png)
            with open(html, "w", encoding="utf-8") as f:
                f.write(page(date, n, spec))
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={os.path.join(tmp, 'edge')}", f"--window-size={W},{H}",
                            "--force-device-scale-factor=1", "--allow-file-access-from-files",
                            "--virtual-time-budget=6000", f"--screenshot={png}",
                            "file:///" + html.replace("\\", "/")],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            for _ in range(60):  # Edge can return a moment before the screenshot lands on disk
                if os.path.exists(png) and os.path.getsize(png) > 0:
                    break
                time.sleep(.5)
            time.sleep(.5)
            Image.open(png).convert("RGB").save(os.path.join(out, f"slide{n}.jpg"), quality=93)
        print("done", date)


if __name__ == "__main__":
    main()
