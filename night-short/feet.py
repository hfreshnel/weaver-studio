"""Foot analysis on a matted clip: ground-contact foot x-velocity (px/frame). python feet.py <layers dir>"""
import sys, numpy as np
from pathlib import Path
from PIL import Image
files = sorted(Path(sys.argv[1]).glob("*.png"))
rows, xs = [], []
for f in files:
    a = np.asarray(Image.open(f))[..., 3] > 128
    ys, xx = np.nonzero(a)
    yb = ys.max(); band = ys > yb - 8
    rows.append(yb); xs.append(xx[band].mean())
rows = np.array(rows); xs = np.array(xs)
print("feet row min/max", rows.min(), rows.max(), "| lowest-point x first/last", round(xs[0]), round(xs[-1]))
v = np.diff(xs)
print("lowest-point x velocity per frame (median |v|, max):", round(float(np.median(np.abs(v))), 2), round(float(np.abs(v).max()), 2))
print("net displacement of the body centre (frames 0 -> end):",
      round(float(np.mean([np.nonzero(np.asarray(Image.open(f))[..., 3] > 128)[1].mean() for f in files[-5:]]) -
                  np.mean([np.nonzero(np.asarray(Image.open(f))[..., 3] > 128)[1].mean() for f in files[:5]]), 1)))
