"""Block C2: 4x-UltraSharp (+Lanczos down) vs plain Lanczos, 480x832 -> 1080x1920 (9:16 crop), on one clip.

Usage: ~/miniconda3/envs/comfy/bin/python up.py zimage_walk   -> up/<clip>_{lanczos,ultrasharp}/NNNN.png + metrics
"""
import sys, time
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageFilter
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent
MODEL = Path("/home/freshnel/dev/git/comfyui/models/upscale_models/4x-UltraSharp.pth")
W, H = 1080, 1920
clip = sys.argv[1]
frames = sorted((ROOT / "clips" / clip).glob("*.png"))
model = ModelLoader().load_from_file(str(MODEL)).cuda().eval().half()
outs = {k: ROOT / "up" / f"{clip}_{k}" for k in ("lanczos", "ultrasharp")}
for d in outs.values():
    d.mkdir(parents=True, exist_ok=True)
t_us = 0.0
for i, f in enumerate(frames):
    im = Image.open(f).convert("RGB")
    cw = int(im.height * 9 / 16)
    x0 = (im.width - cw) // 2
    im = im.crop((x0, 0, x0 + cw, im.height))
    im.resize((W, H), Image.LANCZOS).save(outs["lanczos"] / f"{i:04d}.png")
    t0 = time.time()
    x = torch.from_numpy(np.asarray(im)).permute(2, 0, 1)[None].float().div(255).cuda().half()
    with torch.no_grad():
        y = model(x).clamp(0, 1)[0].permute(1, 2, 0).float().cpu().numpy()
    Image.fromarray((y * 255).round().astype(np.uint8)).resize((W, H), Image.LANCZOS).save(outs["ultrasharp"] / f"{i:04d}.png")
    t_us += time.time() - t0
print(f"ultrasharp {t_us / len(frames):.2f}s/frame")


def gray(p):
    return np.asarray(Image.open(p).convert("L"), dtype=np.float32)


def hp(a):
    b = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    return a - b


for k, d in outs.items():
    ps = sorted(d.glob("*.png"))
    H_ = [hp(gray(p)) for p in ps]
    sharp = np.mean([np.abs(h).mean() for h in H_])
    flick = np.mean([np.abs(H_[i + 1] - H_[i]).mean() for i in range(len(H_) - 1)])
    print(f"{k:11s} detail energy {sharp:.3f}  hp temporal diff {flick:.3f}  ratio {flick / sharp:.3f}")
# side-by-side crop (face/jacket area) of frame 24
a, b = Image.open(outs["lanczos"] / "0024.png"), Image.open(outs["ultrasharp"] / "0024.png")
box = (380, 700, 700, 1100)
s = Image.new("RGB", (640 * 2 + 10, 800), "white")
s.paste(a.crop(box).resize((640, 800), Image.NEAREST), (0, 0))
s.paste(b.crop(box).resize((640, 800), Image.NEAREST), (650, 0))
s.save(ROOT / "up" / f"{clip}_crop.png")
