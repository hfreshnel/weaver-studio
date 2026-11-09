"""Stance-foot speed of an in-place walk cycle (sprite pixels per frame). python foot.py <layers dir>
Per frame the grounded foot = the lowest foot blob (bottom 8 % of the silhouette); contact runs are stretches where that
blob is within 3 px of the lowest row seen on the clip. A planted foot of a walker standing still in the frame moves backwards
at ground speed: that speed is the scroll speed a background must have for the feet not to slide."""
import sys, numpy as np
from pathlib import Path
from PIL import Image
fs = sorted(Path(sys.argv[1]).glob("*.png"))
rows, xs = [], []
for f in fs:
    m = np.asarray(Image.open(f))[..., 3] > 128
    ys, xx = np.nonzero(m); yb = ys.max(); h = yb - ys.min()
    band = ys > yb - 0.08 * h
    bx, by = xx[band], ys[band]
    # grounded foot: pixels within 6 px of the lowest row
    low = by > yb - 6
    rows.append(yb); xs.append(bx[low].mean())
rows, xs = np.array(rows), np.array(xs)
ground = np.percentile(rows, 90)
contact = rows >= ground - 3
print("ground row", ground, "| frames in contact", contact.sum(), "of", len(rows))
v = []
i = 0
while i < len(rows):
    if contact[i]:
        j = i
        while j + 1 < len(rows) and contact[j + 1] and abs(xs[j + 1] - xs[j]) < 25: j += 1
        if j - i >= 4:
            k = np.polyfit(np.arange(i, j + 1), xs[i:j + 1], 1)[0]
            print(f"  stance frames {i}-{j}: x {xs[i]:.0f} -> {xs[j]:.0f}  speed {k:.2f} px/frame")
            v.append(k)
        i = j + 1
    else: i += 1
if v: print("median stance speed", round(float(np.median(v)), 2), "px/frame (negative = backwards, i.e. leftwards)")
print("torso x drift: see body centre")
body = [np.nonzero(np.asarray(Image.open(f))[..., 3] > 128)[1].mean() for f in fs]
print("body centre first/last", round(body[0]), round(body[-1]), "| net", round(body[-1] - body[0]), "px over", len(fs), "frames")
