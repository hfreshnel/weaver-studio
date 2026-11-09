"""Composite a matted walking clip on the street decor with a fixed perspective-consistent transform.

  python shot.py <layers dir> <out name> --start-feet 1150 [--frames N] [--skip a,b] [--decor2]
Fits height = K * (feet_row - h0) on the clip (implied horizon h0), maps h0 onto the decor horizon (685) and her
walking axis onto the vanishing point (381): one transform for the whole clip (no foot sliding), scale chosen so the
first frame has her feet at --start-feet. Light: shade on the lower road, sun band y 880-970 (warm tint + cast shadow).
"""
import argparse, os, sys
import numpy as np
from pathlib import Path
from PIL import Image
sys.path.insert(0, "../webtoon-layers")
import compose as C
from lib import save_video

ap = argparse.ArgumentParser()
ap.add_argument("layers"); ap.add_argument("name")
ap.add_argument("--start-feet", type=float, default=1150)
ap.add_argument("--frames", type=int); ap.add_argument("--first", type=int, default=0)
ap.add_argument("--axis-x", type=float, default=C.VP_X); ap.add_argument("--petals", type=int, default=0)
a = ap.parse_args()
files = sorted(Path(a.layers).glob("*.png"))[a.first:]
if a.frames: files = files[:a.frames]
alpha = [np.asarray(Image.open(f))[..., 3] > 128 for f in files]
feet = np.array([np.nonzero(m.any(1))[0].max() for m in alpha], float)
top = np.array([np.nonzero(m.any(1))[0].min() for m in alpha], float)
hgt = feet - top
K, b = np.polyfit(feet, hgt, 1)          # height = K*feet + b  -> horizon h0 = -b/K
h0 = -b / K
r2 = 1 - ((hgt - (K * feet + b)) ** 2).sum() / ((hgt - hgt.mean()) ** 2).sum()
cx = np.median([np.nonzero(m[int(f) - 40:int(f) + 1].any(0))[0].mean() for m, f in zip(alpha, feet)])
sm = np.convolve(np.pad(feet, 2, mode="edge"), np.ones(5) / 5, mode="valid")
s = (a.start_feet - C.HORIZON) / (sm[0] - h0)
ox, oy = round(a.axis_x - s * cx), round(C.HORIZON - s * h0)
print(f"fit: K={K:.3f} h0={h0:.0f} R2={r2:.3f} axis cx={cx:.0f} | scale {s:.3f} offset ({ox},{oy}) | feet in decor {a.start_feet:.0f} -> {C.HORIZON + s * (sm[-1] - h0):.0f}")

from comp import render
from lib import Petals, over
pet = Petals(n=a.petals, seed=5) if a.petals else None
os.makedirs(f"frames/{a.name}", exist_ok=True)
for i, f in enumerate(files):
    yb = round(C.HORIZON + s * (sm[i] - h0)); fx = round(ox + s * cx)
    im = render(Image.open(f), s, ox, oy, yb, fx)
    if pet: im = over(im, pet.frame(i + 100))
    im.save(f"frames/{a.name}/{i:04d}.png")
save_video(f"frames/{a.name}", f"{a.name}.mp4")
print("frames", len(files))
