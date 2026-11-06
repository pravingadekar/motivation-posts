"""Join two 1122x855 tiles (top at offset 0, bottom at offset 547) into a 1080x1350 scene.

    python stitch.py OUT.png TOP.png BOTTOM.png
"""
import sys

from PIL import Image

out, top, bottom = sys.argv[1:4]
canvas = Image.new("RGB", (1122, 1402))
canvas.paste(Image.open(top).convert("RGB"), (0, 0))
canvas.paste(Image.open(bottom).convert("RGB"), (0, 547))
canvas.resize((1080, 1350), Image.LANCZOS).save(out)
print(out)
