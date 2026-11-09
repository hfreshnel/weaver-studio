"""Contact sheet: python3 sheet.py <out.png> <cols> <img...>  (each tile 640 wide, filename caption)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(p).convert("RGB") for p in paths]
W = 640
tiles = [im.resize((W, round(im.height * W / im.width))) for im in ims]
H = max(t.height for t in tiles)
rows = (len(tiles) + cols - 1) // cols
sh = Image.new("RGB", (cols * W, rows * H), "black")
for i, (t, p) in enumerate(zip(tiles, paths)):
    x, y = (i % cols) * W, (i // cols) * H
    sh.paste(t, (x, y))
    ImageDraw.Draw(sh).text((x + 6, y + 4), Path(p).stem, fill="yellow")
sh.save(out)
