"""Story carousel: किसका पत्थर? scenes/sceneN.png + Hindi text -> slides/slideN.jpg (1080x1350).

Style mix from carousel/references.md: pencil sketch on paper, one red accent, bold title with one red word,
yellow highlighted key words, one short thought per slide, ending in a question. Story, words and art are our own.
Edge renders the text so Devanagari matras are shaped correctly. Run: python build.py
"""
import os
import subprocess
import tempfile
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
W, H = 1080, 1350
HANDLE = "@ai__wala_motivational_guru"

# <r>..</r> red word, <m>..</m> yellow highlight. (lines, size)
SLIDES = [
    (["तुम थके नहीं हो,", "बस किसी और का", "<r>बोझ</r> उठा रहे हो।"], 92),
    (["एक लड़का पहाड़ चढ़ने निकला।", "बस्ता हल्का था,", "<m>सपना बड़ा।</m>"], 70),
    (["पहला पत्थर", "पड़ोसी ने डाला:", "<m>&ldquo;ये तेरे बस का नहीं।&rdquo;</m>"], 72),
    (["फिर रिश्तेदारों ने:", "<m>&ldquo;लोग क्या कहेंगे?&rdquo;</m>", "बस्ता भारी होता गया।"], 72),
    (["एक दिन वो बैठ गया।", "उसे लगा:", "<m>&ldquo;शायद मैं ही कमज़ोर हूँ।&rdquo;</m>"], 70),
    (["एक बूढ़ी अम्मा ने पूछा:", "<m>&ldquo;बेटा, इनमें तेरा अपना</m>", "<m>पत्थर कितना है?&rdquo;</m>"], 68),
    (["उसने बस्ता खोला।", "गौर से देखा।", "<r>एक भी पत्थर उसका नहीं था।</r>"], 70),
    (["पत्थर वहीं छोड़ दिए।", "रास्ता वही था,", "<m>पर चाल बदल गई।</m>"], 72),
    (["आज तुम्हारे बस्ते में", "<r>किसका पत्थर</r> है?"], 84),
]
LAST_NOTE = "कमेंट में लिखो: आज कौन-सा पत्थर छोड़ोगे?"
LAST_SHARE = "उस दोस्त को भेजो जो थक गया है"


def page(n, lines, size):
    bg = os.path.join(HERE, "scenes", f"scene{n}.png").replace("\\", "/")
    total = len(SLIDES)
    rows = "".join(f"<div>{ln}</div>" for ln in lines)
    extra = ""
    if n == total:
        extra = f'<div class="note">{LAST_NOTE}</div><div class="share">{LAST_SHARE}</div>'
    arrow = '<div class="arrow">&#10230;</div>' if n < total else ""
    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@700&display=block" rel="stylesheet">
<style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#efe2c4}}
.bg{{position:absolute;inset:0;background:url('file:///{bg}') center/cover}}
.box{{position:absolute;left:60px;right:60px;top:82px;text-align:center;font:700 {size}px/1.42 Kalam,serif;color:#2b1d12}}
r{{color:#c62828}}
m{{background:linear-gradient(transparent 12%,#ffd23f 12%,#ffd23f 90%,transparent 90%);padding:0 12px;
 -webkit-box-decoration-break:clone;box-decoration-break:clone}}
.note{{margin-top:22px;font-size:48px;line-height:1.4}}
.share{{margin-top:6px;font-size:40px;line-height:1.4;color:#c62828}}
.arrow{{position:absolute;right:50px;top:{H - 110}px;font:700 74px Arial;color:#2b1d12}}
.count{{position:absolute;left:0;right:0;bottom:26px;text-align:center;font:600 26px Arial;color:#2b1d12;
 text-shadow:0 0 8px #efe2c4,0 0 8px #efe2c4}}
</style></head><body><div class="bg"></div>
<div class="box">{rows}{extra}</div>{arrow}<div class="count">{HANDLE}</div></body></html>"""


def main():
    out = os.path.join(HERE, "slides")
    os.makedirs(out, exist_ok=True)
    tmp = os.path.normpath(os.environ.get("CAROUSEL_TMP") or tempfile.mkdtemp())
    os.makedirs(tmp, exist_ok=True)
    for n, (lines, size) in enumerate(SLIDES, start=1):
        html = os.path.join(tmp, f"slide{n}.html")
        png = os.path.join(tmp, f"slide{n}.png")
        if os.path.exists(png):
            os.remove(png)
        with open(html, "w", encoding="utf-8") as f:
            f.write(page(n, lines, size))
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={os.path.join(tmp, 'edge')}", f"--window-size={W},{H}",
                        "--force-device-scale-factor=1", "--allow-file-access-from-files",
                        "--virtual-time-budget=6000", f"--screenshot={png}", "file:///" + html.replace("\\", "/")],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        for _ in range(60):  # Edge can return a moment before the screenshot lands on disk
            if os.path.exists(png) and os.path.getsize(png) > 0:
                break
            time.sleep(.5)
        time.sleep(.5)
        Image.open(png).convert("RGB").save(os.path.join(out, f"slide{n}.jpg"), quality=93)
        print("slide", n)


if __name__ == "__main__":
    main()
