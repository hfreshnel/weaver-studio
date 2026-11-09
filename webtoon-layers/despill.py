"""Remove green spill baked into the character colours: G = min(G, max(R, B)) on opaque pixels.

  python -I despill.py isnet-anime   # matte_isnet-anime/ -> matte_isnet-anime+despill/
"""
import sys, time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
src = ROOT / f"matte_{sys.argv[1]}"
dst = ROOT / f"matte_{sys.argv[1]}+despill"
dst.mkdir(exist_ok=True)
t0 = time.time()
files = sorted(src.glob("*.png"))
for f in files:
    a = np.asarray(Image.open(f)).copy()
    rgb = a[..., :3].astype(np.int16)
    rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]))
    a[..., :3] = rgb.astype(np.uint8)
    Image.fromarray(a, "RGBA").save(dst / f.name)
print(f"despill {sys.argv[1]}: {len(files)} frames, {(time.time() - t0) / len(files):.3f} s/frame")
