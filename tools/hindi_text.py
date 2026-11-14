"""Render Hindi (Devanagari) caption / hook overlays as transparent 1080x1920 PNGs with headless Chrome.

Pillow here has no libraqm, so it cannot join Devanagari matras and conjuncts; Chrome shapes Hindi correctly.
Font: Nirmala UI (ships with Windows), bold.
"""
import html
import os
import subprocess
import tempfile

W, H = 1080, 1920
CHROME = next((p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"] if os.path.exists(p)),
              "chrome")

BASE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:%(w)dpx;height:%(h)dpx;background:transparent;overflow:hidden}
body{font-family:'Nirmala UI','Noto Sans Devanagari',sans-serif;font-weight:700}
%(css)s</style></head><body>%(body)s</body></html>"""


def _shot(page, png):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "p.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(page)
        url = "file:///" + src.replace("\\", "/")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        "--default-background-color=00000000", f"--user-data-dir={os.path.join(tmp, 'prof')}",
                        f"--window-size={W},{H}", "--virtual-time-budget=2000",
                        f"--screenshot={os.path.abspath(png)}", url],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def caption_png(piece, path, y=1560, size=96):
    """piece: [(word, highlight)]. Text centred, top of the line at y px."""
    words = " ".join(
        f'<span class="{"hl" if hl else ""}">{html.escape(w)}</span>' for w, hl in piece)
    css = (f".c{{position:absolute;left:40px;right:40px;top:{y}px;text-align:center;font-size:{size}px;"
           "line-height:1.25;color:#fff;font-weight:900;-webkit-text-stroke:10px #000;paint-order:stroke fill;"
           "text-shadow:0 6px 18px rgba(0,0,0,.8)}.hl{color:#ffd600}")
    _shot(BASE % {"w": W, "h": H, "css": css, "body": f'<div class="c">{words}</div>'}, path)


def hook_png(text, path, y=110, size=54):
    css = (f".b{{position:absolute;left:0;right:0;margin:0 auto;width:fit-content;top:{y}px;max-width:860px;"
           f"background:rgba(255,214,0,.95);color:#111;font-size:{size}px;line-height:1.3;"
           "padding:18px 36px;border-radius:28px;text-align:center}")
    _shot(BASE % {"w": W, "h": H, "css": css, "body": f'<div class="b">{html.escape(text)}</div>'}, path)
