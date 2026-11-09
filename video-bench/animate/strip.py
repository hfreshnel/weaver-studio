"""Strip: driving frames (top) vs generated frames (bottom) for a label. Usage: strip.py <label>"""
import sys
from pathlib import Path
from PIL import Image
R = Path(__file__).resolve().parent
lab = sys.argv[1]
drv = sorted((R / "pre").glob("drv_*.png"))
gen = sorted((R / "out").glob(f"gen_{lab}_*.png"))
idx = (0, 5, 10, 15, 20)
w, h = 240, 432
s = Image.new("RGB", (w * 5, h * 2))
for c, i in enumerate(idx):
    s.paste(Image.open(drv[min(i, len(drv) - 1)]).convert("RGB").resize((w, h)), (c * w, 0))
    s.paste(Image.open(gen[min(i, len(gen) - 1)]).convert("RGB").resize((w, h)), (c * w, h))
s.save(R / f"strip_{lab}.png")
print(len(gen), "frames")
