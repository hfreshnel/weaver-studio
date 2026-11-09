"""Retained matting path for a new clip: isnet-anime (rembg) then despill G = min(G, max(R, B)).

  python -I layer.py <comfyui output prefix> <out dir>     # e.g. i2v_front_s11 layers/front_s11
"""
import sys, time
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent
COMFY_OUT = ROOT.parent / "comfyui" / "output"
prefix, dst = sys.argv[1], ROOT / sys.argv[2]
dst.mkdir(parents=True, exist_ok=True)
frames = sorted(COMFY_OUT.glob(f"{prefix}_*.png"))
session = new_session("isnet-anime")
t0 = time.time()
for i, f in enumerate(frames):
    a = np.asarray(remove(Image.open(f).convert("RGB"), session=session)).copy()
    rgb = a[..., :3].astype(np.int16)
    rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]))
    a[..., :3] = rgb.astype(np.uint8)
    Image.fromarray(a, "RGBA").save(dst / f"{i:04d}.png")
print(f"{prefix}: {len(frames)} frames -> {dst} ({(time.time() - t0) / max(len(frames), 1):.2f} s/frame)")
