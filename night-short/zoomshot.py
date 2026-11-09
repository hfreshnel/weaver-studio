"""Slow camera push-in on a finished shot (uniform zoom about the vanishing point, eased): python zoomshot.py <in dir> <out dir> <z0> <z1>"""
import os, sys
from pathlib import Path
from PIL import Image
from lib import ease, F
src, dst, z0, z1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
fs = sorted(Path(f"frames/{src}").glob("*.png")); os.makedirs(f"frames/{dst}", exist_ok=True)
vx, vy = 381 * F, 685 * F
for i, f in enumerate(fs):
    z = z0 + (z1 - z0) * ease(i / max(len(fs) - 1, 1))
    im = Image.open(f).convert("RGB"); w, h = im.size
    ww, wh = w / z, h / z
    x0 = vx - (vx / w) * ww; y0 = vy - (vy / h) * wh             # keep the vanishing point fixed on screen
    im.transform(im.size, Image.AFFINE, (1 / z, 0, x0, 0, 1 / z, y0), Image.BICUBIC).save(f"frames/{dst}/{i:04d}.png")
print(dst, len(fs))
