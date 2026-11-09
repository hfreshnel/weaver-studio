"""Frame-to-frame change of a composited shot; flag spikes (jumps, seams, flicker). python jumps.py <frames dir>"""
import sys, numpy as np
from pathlib import Path
from PIL import Image
fs = sorted(Path(sys.argv[1]).glob("*.png"))
d = []
prev = None
for f in fs:
    a = np.asarray(Image.open(f).convert("L").resize((208, 304)), np.float32)
    if prev is not None: d.append(np.abs(a - prev).mean())
    prev = a
d = np.array(d); med = np.median(d[d > 0]) if (d > 0).any() else 0
print(sys.argv[1], "frames", len(fs), "median diff", round(float(med), 3), "| zero-diff (held) frames", int((d < 0.01).sum()))
for i, v in enumerate(d):
    if med and v > 3 * med: print("  spike at", i, "->", i + 1, round(float(v), 2))
