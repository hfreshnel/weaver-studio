"""Contact sheet of kf/: rows = prompts, columns = models (zimage | klein | wan)."""
from pathlib import Path
from PIL import Image
R = Path(__file__).resolve().parent / "kf"
ms, ps, w, h = ["zimage", "klein", "wan"], ["portrait", "walk", "anime"], 400, 694
sheet = Image.new("RGB", (w * 3, h * 3), "white")
for r, p in enumerate(ps):
    for c, m in enumerate(ms):
        f = R / m / f"{p}_s101.png"
        if f.exists():
            sheet.paste(Image.open(f).resize((w, h)), (c * w, r * h))
sheet.save(R.parent / "kf_sheet.png")
