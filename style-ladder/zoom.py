"""Zoom sheets: native-resolution crop of face + hands, one per style -> sheets/zoom_<style>.jpg (comfy env python)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MODELS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["juggernaut", "wan", "klein", "zimage"]
FONT = ImageFont.load_default(size=20)
H = 560

style = sys.argv[1]
cells = []
for m in MODELS:
    for p in sorted((ROOT / "out" / m).glob(f"{style}_s*.png")):
        im = Image.open(p).convert("RGB")
        w, h = im.size
        c = im.crop((int(w * .18), int(h * .12), int(w * .82), int(h * .62)))  # head to hands
        c = c.resize((int(c.width * H / c.height), H))
        cells.append((f"{m} {p.stem.split('_')[-1]}", c))
sheet = Image.new("RGB", (sum(c.width for _, c in cells), H + 30), "white")
d, x = ImageDraw.Draw(sheet), 0
for label, c in cells:
    sheet.paste(c, (x, 30)); d.text((x + 6, 4), label, fill="black", font=FONT); x += c.width
sheet.save(ROOT / "sheets" / f"zoom_{style}.jpg", quality=90)
