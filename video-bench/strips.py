"""Frame strips (0,12,24,36,48) of each clip in clips/ stacked in one image."""
from pathlib import Path
from PIL import Image
R = Path(__file__).resolve().parent / "clips"
ks = sorted(p for p in R.iterdir() if p.is_dir())
w, h = 240, 416
sheet = Image.new("RGB", (w * 5, h * len(ks)), "white")
for r, k in enumerate(ks):
    fr = sorted(k.glob("*.png"))
    for c, i in enumerate((0, 12, 24, 36, 48)):
        sheet.paste(Image.open(fr[min(i, len(fr) - 1)]).resize((w, h)), (c * w, r * h))
sheet.save(R.parent / "clips_sheet.png")
print([k.name for k in ks])
