"""Contact sheets: one per style (models x seeds side by side) -> sheets/<style>.jpg. Run with the comfy env's python (Pillow)."""
import re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MODELS = ["animagine", "juggernaut", "wan", "klein", "zimage"]
TW, TH = 416, 608  # thumbnail box (half of 832x1216)
FONT = ImageFont.load_default(size=22)


def times():
    """Per-image seconds from gen.log (last run wins)."""
    t = {}
    for line in (ROOT / "gen.log").read_text().splitlines():
        m = re.search(r" (\w+) (\d_\w+) seeds=.*\((\d+)s/img\)", line)
        if m:
            t[(m[1], m[2])] = int(m[3])
    return t


def main(styles):
    t = times()
    (ROOT / "sheets").mkdir(exist_ok=True)
    for style in styles:
        cells = [(m, p) for m in MODELS for p in sorted((ROOT / "out" / m).glob(f"{style}_s*.png"))]
        if not cells:
            continue
        sheet = Image.new("RGB", (TW * len(cells), TH + 40), "white")
        d = ImageDraw.Draw(sheet)
        for i, (m, p) in enumerate(cells):
            im = Image.open(p).convert("RGB")
            im.thumbnail((TW, TH))
            sheet.paste(im, (i * TW + (TW - im.width) // 2, 40))
            d.text((i * TW + 8, 8), f"{m} {p.stem.split('_')[-1]} ({t.get((m, style), '?')}s)", fill="black", font=FONT)
        sheet.save(ROOT / "sheets" / f"{style}.jpg", quality=88)
        print(ROOT / "sheets" / f"{style}.jpg")


if __name__ == "__main__":
    main(sys.argv[1:] or ["1_flat", "2_anime", "3_bd", "4_3d", "5_paint", "6_semi", "7_cine", "8_photo"])
