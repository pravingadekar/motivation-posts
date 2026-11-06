"""Story carousel: farmer and the bamboo seed. scenes/sceneN.png + Hindi text -> slides/slideN.jpg (1080x1350).

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

# (heading, body, text position, footer)
SLIDES = [
    ("5 साल तक कुछ नहीं उगा।", "फिर भी वो रोज़ पानी देता रहा...", "top", "पूरी कहानी पढ़ो  &#8594;"),
    ("पहला साल", "एक किसान ने बाँस का बीज बोया। रोज़ पानी दिया। ज़मीन से कुछ नहीं निकला।", "top", ""),
    ("दूसरा और तीसरा साल", "अब भी कुछ नहीं। लोग हँसने लगे: &ldquo;पागल है, खाली ज़मीन को पानी देता है।&rdquo;", "top", ""),
    ("चौथा साल", "बारिश आई, धूप आई, साथ वाले भी छोड़ गए। पर वो नहीं रुका।", "top", ""),
    ("पाँचवाँ साल", "एक सुबह मिट्टी से छोटा-सा हरा अंकुर निकला।", "top", ""),
    ("फिर कुछ ही हफ़्तों में...", "बाँस आसमान छूने लगा। जो हँसते थे, अब हैरान खड़े थे।", "top", ""),
    ("वो 5 साल बेकार नहीं थे।", "नीचे जड़ें बन रही थीं। तुम्हारी मेहनत भी अभी जड़ें बना रही है। रुकना मत।", "bottom",
     "सेव करो  |  उस दोस्त को भेजो जिसे आज ये चाहिए"),
]


def page(n, heading, body, place, footer):
    bg = os.path.join(HERE, "scenes", f"scene{n}.png").replace("\\", "/")
    dots = "".join(f'<i class="{"on" if i == n else ""}"></i>' for i in range(1, len(SLIDES) + 1))
    if place == "top":
        shade = "linear-gradient(180deg,rgba(8,6,4,.86) 0%,rgba(8,6,4,.62) 32%,rgba(8,6,4,0) 56%)"
        pos = "top:84px"
    else:
        shade = "linear-gradient(0deg,rgba(8,6,4,.72) 0%,rgba(8,6,4,.5) 30%,rgba(8,6,4,0) 50%)"
        pos = "bottom:150px"
    foot = f'<div class="foot">{footer}</div>' if footer else ""
    return f"""<!doctype html><html lang="hi"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&display=block" rel="stylesheet">
<style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
.bg{{position:absolute;inset:0;background:url('file:///{bg}') center/cover}}
.sh{{position:absolute;inset:0;background:{shade}}}
.box{{position:absolute;left:70px;right:70px;{pos};text-align:center;font-family:'Tiro Devanagari Hindi',serif}}
h1{{margin:0;font-weight:400;font-size:84px;line-height:1.4;color:#ffd166;text-shadow:0 3px 14px rgba(0,0,0,.75)}}
.bar{{width:130px;height:6px;background:#ffd166;margin:14px auto 22px}}
p{{margin:0;font-size:56px;line-height:1.5;color:#fff;text-shadow:0 3px 12px rgba(0,0,0,.85)}}
.foot{{margin-top:22px;font-size:40px;line-height:1.5;color:#ffd166;text-shadow:0 2px 10px rgba(0,0,0,.85)}}
.base{{position:absolute;left:0;right:0;bottom:30px;text-align:center;font:500 27px Arial;color:#fff;
 text-shadow:0 2px 8px #000}}
.dots{{margin-bottom:12px}}
.dots i{{display:inline-block;width:13px;height:13px;margin:0 6px;border-radius:50%;background:rgba(255,255,255,.5)}}
.dots i.on{{background:#ffd166}}
</style></head><body><div class="bg"></div><div class="sh"></div>
<div class="box"><h1>{heading}</h1><div class="bar"></div><p>{body}</p>{foot}</div>
<div class="base"><div class="dots">{dots}</div>{HANDLE}</div></body></html>"""


def main():
    out = os.path.join(HERE, "slides")
    os.makedirs(out, exist_ok=True)
    tmp = os.path.normpath(os.environ.get("CAROUSEL_TMP") or tempfile.mkdtemp())
    for n, slide in enumerate(SLIDES, start=1):
        html = os.path.join(tmp, f"slide{n}.html")
        png = os.path.join(tmp, f"slide{n}.png")
        with open(html, "w", encoding="utf-8") as f:
            f.write(page(n, *slide))
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
