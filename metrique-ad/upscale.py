"""Resample a 48 fps RIFE clip to 30 fps, upscale x4 (4x-UltraSharp) and fit to 1080x1920.

Run with the ComfyUI env (torch + spandrel):
  ~/miniconda3/envs/comfy/bin/python upscale.py clips/P03_1003 P03 [--trim-start S] [--trim-end S]
"""
import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent
MODEL = Path("/home/freshnel/dev/git/comfyui/models/upscale_models/4x-UltraSharp.pth")
W, H = 1080, 1920


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("name")
    ap.add_argument("--src-fps", type=float, default=48)
    ap.add_argument("--trim-start", type=float, default=0.0, help="seconds dropped at the head")
    ap.add_argument("--trim-end", type=float, default=0.0, help="seconds dropped at the tail")
    a = ap.parse_args()
    frames = sorted((ROOT / a.src).glob("*.png"))
    first = int(a.trim_start * a.src_fps)
    frames = frames[:len(frames) - int(a.trim_end * a.src_fps)]
    n_out = int((len(frames) - first) / a.src_fps * 30)
    picks = [frames[min(first + round(i * a.src_fps / 30), len(frames) - 1)] for i in range(n_out)]

    model = ModelLoader().load_from_file(str(MODEL)).cuda().eval().half()
    dst = ROOT / "clips_final" / a.name
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.png"):
        old.unlink()
    for i, f in enumerate(picks):
        im = Image.open(f).convert("RGB")
        cw = int(im.height * 9 / 16)
        x0 = (im.width - cw) // 2
        im = im.crop((x0, 0, x0 + cw, im.height))
        x = torch.from_numpy(np.asarray(im)).permute(2, 0, 1)[None].float().div(255).cuda().half()
        with torch.no_grad():
            y = model(x).clamp(0, 1)[0].permute(1, 2, 0).float().cpu().numpy()
        out = Image.fromarray((y * 255).round().astype(np.uint8)).resize((W, H), Image.LANCZOS)
        out.save(dst / f"{i:04d}.png")
    print(f"{a.name}: {len(picks)} frames @30fps -> {dst}")


if __name__ == "__main__":
    main()
