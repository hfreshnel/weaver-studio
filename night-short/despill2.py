"""Hue-based despill on matted RGBA frames, in place: desaturate pixels whose hue is within +-28 deg of the background hue.
Complements G=min(G,max(R,B)) (green only) for the aqua background (140,234,188): aqua fringes in hair, shoes and white cloth.
  python despill2.py <layers dir> <bg hue in degrees>
"""
import colorsys, sys
import numpy as np
from pathlib import Path
from PIL import Image
hue0 = float(sys.argv[2]); WID = float(sys.argv[3]) if len(sys.argv) > 3 else 28
for f in sorted(Path(sys.argv[1]).glob("*.png")):
    a = np.asarray(Image.open(f)).copy()
    rgb = a[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(-1), rgb.min(-1); d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = d / (mx + 1e-6)
    dh = np.abs(((h - hue0 + 180) % 360) - 180)
    m = (dh < WID) & (sat > 0.12) & (a[..., 3] > 0)
    w = np.clip(1 - dh / WID, 0, 1) * m                          # 1 at the bg hue, 0 at +-28 deg
    gray = rgb.mean(-1, keepdims=True)
    # move towards the red channel level (keeps dark hair dark, white cloth white) rather than pure grey
    t = r + 0.3 * (gray[..., 0] - r); tgt = np.stack([r, t, t], -1)
    out = rgb * (1 - w[..., None] * 0.9) + tgt * (w[..., None] * 0.9)
    a[..., :3] = np.clip(out * 255, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(f)
print(sys.argv[1], "done")
