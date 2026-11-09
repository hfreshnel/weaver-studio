"""Contact sheet of a Wan clip: python sheet.py <prefix> <out.jpg> [idx,idx,...]"""
import sys
from pathlib import Path
from PIL import Image
fs = sorted(Path("../comfyui/output").glob(f"{sys.argv[1]}_*.png"))
idx = [int(i) for i in sys.argv[3].split(",")] if len(sys.argv) > 3 else [0, 12, 24, 36, len(fs) - 1]
ims = [Image.open(fs[i]).convert("RGB") for i in idx]
h = 560; ims = [i.resize((round(i.width * h / i.height), h)) for i in ims]
sh = Image.new("RGB", (sum(i.width for i in ims), h)); x = 0
for i in ims: sh.paste(i, (x, 0)); x += i.width
sh.save(sys.argv[2], quality=85); print(len(fs), "frames")
