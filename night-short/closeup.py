"""Close / medium shot: matted x2 clip over a blurred crop of the decor canopy (depth-of-field background), petals in front.

  python closeup.py <layers dir> <name> [--blur 14] [--pingpong] [--hold N] [--crop x0,y0,x1,y1] [--petals N]
Frames sequence: forward; with --pingpong then (after --hold repeats of the last frame) backwards.
"""
import argparse, os
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter
from lib import *

ap = argparse.ArgumentParser()
ap.add_argument("layers"); ap.add_argument("name")
ap.add_argument("--blur", type=float, default=14)
ap.add_argument("--crop", default="400,40,810,640")
ap.add_argument("--pingpong", action="store_true"); ap.add_argument("--hold", type=int, default=0)
ap.add_argument("--petals", type=int, default=0)
ap.add_argument("--last", type=int)
a = ap.parse_args()
files = sorted(Path(a.layers).glob("*.png"))[: a.last]
seq = list(range(len(files)))
if a.pingpong:
    seq += [len(files) - 1] * a.hold + list(range(len(files) - 2, 0, -1))
d2 = Image.open(DECOR2).convert("RGB")
x0, y0, x1, y1 = [float(v) for v in a.crop.split(",")]
pet = Petals(n=a.petals, seed=9) if a.petals else None
os.makedirs(f"frames/{a.name}", exist_ok=True)
for o, k in enumerate(seq):
    t = o / max(len(seq) - 1, 1)
    dx, dy = 10 * t, 14 * t                                   # slow drift of the background (parallax vs the figure)
    bg = d2.resize((W, H), Image.LANCZOS, box=((x0 + dx) * 2, (y0 + dy) * 2, (x1 + dx) * 2, (y1 + dy) * 2))
    bg = bg.filter(ImageFilter.GaussianBlur(a.blur * F))
    ch = Image.open(files[k]); ch = ch.resize((W, H), Image.LANCZOS)
    rgba = np.asarray(ch, np.float32); al = rgba[..., 3:4] / 255
    fg = np.clip(rgba[..., :3] * np.array([1.0, 0.985, 0.96]), 0, 255)       # slight warm tint, same sun as the street
    out = fg * al + np.asarray(bg, np.float32) * (1 - al)
    im = Image.fromarray(out.astype(np.uint8))
    if pet: im = over(im, pet.frame(o))
    im.save(f"frames/{a.name}/{o:04d}.png")
save_video(f"frames/{a.name}", f"{a.name}.mp4")
print(a.name, len(seq), "frames")
