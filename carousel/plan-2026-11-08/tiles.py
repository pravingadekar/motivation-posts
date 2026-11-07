"""Join two 1307x698 screenshots of a scene shown at 1080x1350 (top at offset 0, bottom at offset 652) into sceneN.png.

    python tiles.py OUT.png TOP.jpg BOTTOM.jpg
"""
import sys

from PIL import Image

out, top, bottom = sys.argv[1:4]
canvas = Image.new("RGB", (1080, 1350))
canvas.paste(Image.open(bottom).convert("RGB").crop((0, 0, 1080, 698)), (0, 652))
canvas.paste(Image.open(top).convert("RGB").crop((0, 0, 1080, 698)), (0, 0))
canvas.save(out)
print(out)
