"""Join left/right zoom captures of an image shown full-height in the browser into one PNG.

    python tools/join_tiles.py OUT.png LEFT.png RIGHT.png SPLIT_FRAME_X FRAME_W
LEFT covers frame x 0..A, RIGHT covers frame x B..FRAME_W (overlap allowed). SPLIT_FRAME_X = B.
Scale (file px per frame px) comes from LEFT's height vs the viewport frame height (744).
"""
import sys

from PIL import Image

out, left, right, bx, fw = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
L, R = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
s = L.height / 744
W = round(fw * s)
canvas = Image.new("RGB", (W, L.height))
canvas.paste(R, (round(bx * s), 0))
canvas.paste(L, (0, 0))
canvas.save(out)
print(out, canvas.size)
