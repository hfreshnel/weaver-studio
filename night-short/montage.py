"""Assemble shots: python montage.py <out name> dir[:start:end][~dissolve_frames] ...   (hard cuts unless ~N is given)"""
import os, shutil, sys
from pathlib import Path
from PIL import Image
from lib import save_video
name = sys.argv[1]
out = Path(f"frames/{name}"); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
n = 0
prev_tail = None
for spec in sys.argv[2:]:
    dis = 0
    if "~" in spec: spec, d = spec.split("~"); dis = int(d)
    parts = spec.split(":"); d_ = Path("frames") / parts[0]
    fs = sorted(d_.glob("*.png")); s = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    e = int(parts[2]) if len(parts) > 2 and parts[2] else len(fs)
    fs = fs[s:e]
    for i, f in enumerate(fs):
        im = Image.open(f).convert("RGB")
        if dis and prev_tail is not None and i < dis:
            im = Image.blend(prev_tail, im, (i + 1) / (dis + 1))
        im.save(out / f"{n:04d}.png"); n += 1
    prev_tail = Image.open(fs[-1]).convert("RGB")
# fade in (6 frames) and out (12 frames) to black
import numpy as np
fin, fout = 6, 12
for i in range(fin):
    f = out / f"{i:04d}.png"; im = Image.open(f).convert("RGB"); Image.fromarray((np.asarray(im) * ((i + 1) / (fin + 1))).astype(np.uint8)).save(f)
for k in range(fout):
    i = n - 1 - k; f = out / f"{i:04d}.png"; im = Image.open(f).convert("RGB")
    Image.fromarray((np.asarray(im) * ((k + 1) / (fout + 1))).astype(np.uint8)).save(f)
save_video(str(out), f"{name}.mp4")
print(name, n, "frames", round(n / 24, 1), "s")
