"""Compare matte_<method>/ outputs: edge close-ups on magenta, alpha stability, composite over the street decor.

  python -I evaluate.py decor.png chroma isnet-anime birefnet-general
"""
import subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
decor_path, methods = Path(sys.argv[1]), sys.argv[2:]
OUT = ROOT / "eval"
OUT.mkdir(exist_ok=True)

# Close-ups: head/ribbon and right hand of the frame with the widest arm gesture, 2x nearest-neighbour.
CROPS = [(150, 0, 400, 180), (330, 140, 512, 320)]
FRAME = "wan_green_00049_.png"
tiles = []
for m in methods:
    im = Image.open(ROOT / f"matte_{m}" / FRAME)
    row = []
    for box in CROPS:
        bg = Image.new("RGBA", im.size, (255, 0, 255, 255))
        c = Image.alpha_composite(bg, im).crop(box)
        row.append(c.resize((c.width * 2, c.height * 2), Image.NEAREST))
    tiles.append(row)
cw = sum(t.width for t in tiles[0])
ch = max(t.height for t in tiles[0])
sheet = Image.new("RGB", (cw, ch * len(methods)), "white")
for r, row in enumerate(tiles):
    x = 0
    for t in row:
        sheet.paste(t.convert("RGB"), (x, r * ch))
        x += t.width
sheet.save(OUT / "edges.png")

# Alpha stability: mean |alpha_t - alpha_t-1| in the edge band (0 < alpha < 1 in either frame), and fraction of
# "hard" pixels whose alpha flips by > 0.5 between consecutive frames. Same motion for every method, so the
# numbers are comparable between methods, not in absolute terms.
for m in methods:
    files = sorted((ROOT / f"matte_{m}").glob("*.png"))
    al = [np.asarray(Image.open(f))[..., 3].astype(np.float32) / 255 for f in files]
    band, flips = [], []
    for a, b in zip(al, al[1:]):
        mask = ((a > 0.02) & (a < 0.98)) | ((b > 0.02) & (b < 0.98))
        band.append(np.abs(a - b)[mask].mean() if mask.any() else 0)
        flips.append((np.abs(a - b) > 0.5).mean())
    soft = np.mean([((a > 0.02) & (a < 0.98)).mean() for a in al])
    print(f"{m:18s} edge-band dAlpha={np.mean(band):.3f}  flips={np.mean(flips) * 100:.2f}%  soft-px={soft * 100:.2f}%")

# Composite over the decor: character scaled to 80% of the decor height, feet near the bottom, centred.
decor = Image.open(decor_path).convert("RGBA")
DW, DH = decor.size
for m in methods:
    d = OUT / f"comp_{m}"
    d.mkdir(exist_ok=True)
    for i, f in enumerate(sorted((ROOT / f"matte_{m}").glob("*.png"))):
        ch_im = Image.open(f)
        s = DH * 0.8 / ch_im.height
        ch_im = ch_im.resize((round(ch_im.width * s), round(ch_im.height * s)), Image.LANCZOS)
        frame = decor.copy()
        frame.alpha_composite(ch_im, ((DW - ch_im.width) // 2, DH - ch_im.height - 20))
        frame.convert("RGB").save(d / f"{i:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(d / "%04d.png"),
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(OUT / f"comp_{m}.mp4")], check=True)
print("written:", OUT)
