"""Find the walk-cycle period of a matted clip: normalised silhouette (height 128, feet-centred) distance between frames i and i+lag."""
import sys, numpy as np
from pathlib import Path
from PIL import Image
fs = sorted(Path(sys.argv[1]).glob("*.png"))
S = []
for f in fs:
    im = Image.open(f); a = np.asarray(im)
    m = a[..., 3] > 128; ys, xs = np.nonzero(m)
    h = ys.max() - ys.min() + 1
    k = 128 / h
    cx = (xs[ys > ys.max() - 0.1 * h].min() + xs[ys > ys.max() - 0.1 * h].max()) / 2
    # RGB + alpha, scaled to height 128, centred on the feet
    c = im.crop((int(cx - h * 0.6), ys.min(), int(cx + h * 0.6), ys.max() + 1)).resize((int(h * 1.2 * k), 128), Image.BILINEAR)
    z = np.zeros((128, 160, 4), np.float32); w = min(c.width, 160); z[:, 80 - w // 2: 80 - w // 2 + w] = np.asarray(c, np.float32)[:, :w]
    S.append(z)
S = np.array(S)
n = len(S)
print("lag: mean diff (lower = closer to a cycle)")
for lag in range(8, 40):
    d = np.mean([np.abs(S[i] - S[i + lag]).mean() for i in range(0, n - lag)])
    print(lag, round(float(d), 2))
