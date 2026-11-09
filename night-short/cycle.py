"""Walk cycle x path (studio technique): loop one cycle of a matted clip and move it along a perspective path.

  python cycle.py <layers dir> <name> --period P --start a --frames N [--start-feet 1150] [--rate r] [--axis-x 381]
The cycle frames [a, a+P) are rescaled to a canonical size (fitted height = K*(feet-h0)), then each output frame t is
placed with the scale of the path: distance Z(t) = Z0 * (1 + rate * t_seconds), ground row = horizon + dy0 / (1 + rate*t).
rate defaults to the clip's own natural speed (how fast the distance grew in the Wan clip).
"""
import argparse, os
import numpy as np
from pathlib import Path
from PIL import Image
import sys; sys.path.insert(0, "../webtoon-layers"); import compose as C
from comp import render
from lib import save_video, Petals, over

ap = argparse.ArgumentParser()
ap.add_argument("layers"); ap.add_argument("name")
ap.add_argument("--period", type=int, required=True); ap.add_argument("--start", type=int, default=0)
ap.add_argument("--frames", type=int, default=144)
ap.add_argument("--start-feet", type=float, default=1150)
ap.add_argument("--petals", type=int, default=0); ap.add_argument("--rate", type=float); ap.add_argument("--axis-x", type=float, default=C.VP_X)
a = ap.parse_args()
files = sorted(Path(a.layers).glob("*.png"))
alpha = [np.asarray(Image.open(f))[..., 3] > 128 for f in files]
feet = np.array([np.nonzero(m.any(1))[0].max() for m in alpha], float)
top = np.array([np.nonzero(m.any(1))[0].min() for m in alpha], float)
K, b = np.polyfit(feet, feet - top, 1); h0 = -b / K
sm = np.convolve(np.pad(feet, 2, mode="edge"), np.ones(5) / 5, mode="valid")
cx = np.median([np.nonzero(m[int(f) - 40:int(f) + 1].any(0))[0].mean() for m, f in zip(alpha, feet)])
dy_first, dy_last = sm[0] - h0, sm[-1] - h0
nat = (dy_first / dy_last - 1) / (len(files) / 24)          # natural speed: fraction of the initial distance per second
rate = a.rate if a.rate is not None else nat
dy0 = a.start_feet - C.HORIZON
print(f"fit K={K:.3f} h0={h0:.0f}; natural speed {nat:.3f}/s, used {rate:.3f}/s")
cyc = list(range(a.start, a.start + a.period))
pet = Petals(n=a.petals, seed=5) if a.petals else None
os.makedirs(f"frames/{a.name}", exist_ok=True)
for t in range(a.frames):
    j = cyc[t % a.period]
    dy = dy0 / (1 + rate * t / 24)
    s = dy / (sm[j] - h0)                                     # sprite scale so that its fitted height matches the path
    yb = round(C.HORIZON + dy); ox = round(a.axis_x - s * cx); oy = round(yb - s * sm[j])
    im = render(Image.open(files[j]), s, ox, oy, yb, round(a.axis_x))
    if pet: im = over(im, pet.frame(t + 100 * (a.start_feet < 1100)))
    im.save(f"frames/{a.name}/{t:04d}.png")
save_video(f"frames/{a.name}", f"{a.name}.mp4")
print("ground row", round(C.HORIZON + dy0), "->", yb)
